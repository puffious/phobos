"""FastAPI application for CleanSlate."""
import logging
import shutil
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel

from app.config import load_config
from app.services.backup_service import backup_file, BackupError, generate_remote_link
from app.services.cleaner_service import sanitize_file, CleanerError, get_file_metadata
from app.services.db_service import log_file_event, DatabaseError

logger = logging.getLogger(__name__)

app = FastAPI(title="CleanSlate", version="0.0.1", description="Privacy tool for metadata removal")


class SanitizeResponse(BaseModel):
    """Response model for sanitize endpoint."""
    success: bool
    message: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    metadata_before: Optional[dict] = None
    metadata_after: Optional[dict] = None
    removed_metadata: Optional[dict] = None
    remote_link: Optional[str] = None


class StatusResponse(BaseModel):
    """Response model for status endpoint."""
    status: str
    timestamp: datetime
    services: dict


@app.get("/health")
async def health_check():
    """Healthcheck endpoint."""
    return {"status": "ok", "service": "cleanslate"}


@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get service status and information."""
    return {
        "status": "running",
        "timestamp": datetime.now(),
        "services": {
            "backup": "available",
            "sanitize": "available",
            "database": "available",
        }
    }


@app.post("/sanitize", response_model=SanitizeResponse)
async def sanitize_endpoint(file: UploadFile = File(...)):
    """Upload, sanitize, and return metadata plus remote link for the sanitized file."""
    config = load_config()
    remote_base = f"{config.rclone_remote_name}:{config.rclone_dest_path}".rstrip("/")

    suffix = Path(file.filename or "").suffix
    temp_dir = Path(tempfile.gettempdir()) / "cleanslate_uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{uuid.uuid4().hex}{suffix}"

    try:
        with temp_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Collect metadata before sanitization
        before = get_file_metadata(str(temp_path), grouped=True).get("metadata", {})

        # Sanitize in place
        sanitize_result = sanitize_file(str(temp_path))

        # Collect metadata after sanitization
        after = get_file_metadata(str(temp_path), grouped=True).get("metadata", {})

        # Compute removed/changed metadata
        removed = {}
        for key, value in before.items():
            after_value = after.get(key)
            if key not in after or after_value != value:
                removed[key] = {"before": value, "after": after_value}

        # Upload sanitized file to remote
        safe_name = Path(file.filename or temp_path.name).name
        remote_path = f"{remote_base}/{safe_name}"
        backup_file(str(temp_path), remote_path)

        # Generate shareable link
        remote_link = generate_remote_link(remote_path)

        return {
            "success": True,
            "message": "File sanitized successfully",
            "file_path": sanitize_result.get("file"),
            "file_size": sanitize_result.get("file_size"),
            "metadata_before": before,
            "metadata_after": after,
            "removed_metadata": removed,
            "remote_link": remote_link,
        }
    except CleanerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BackupError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during sanitization: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        # Cleanup temporary file
        try:
            temp_path.unlink(missing_ok=True)
        except Exception:
            logger.warning(f"Failed to remove temp file {temp_path}")


@app.post("/backup")
async def backup_endpoint(file_path: str, remote: str = "gdrive:backups"):
    """
    Backup a file to cloud storage.
    
    Args:
        file_path: Path to the file to backup
        remote: Rclone remote destination
        
    Returns:
        Backup result
    """
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    
    try:
        result = backup_file(file_path, remote)
        return {
            "success": True,
            "message": "File backed up successfully",
            "file": result.get("file"),
            "remote": result.get("remote"),
        }
    except BackupError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during backup: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
