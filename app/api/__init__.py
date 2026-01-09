"""FastAPI application for CleanSlate."""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel

from app.services.backup_service import backup_file, BackupError
from app.services.cleaner_service import sanitize_file, CleanerError
from app.services.db_service import log_file_event, DatabaseError

logger = logging.getLogger(__name__)

app = FastAPI(title="CleanSlate", version="0.0.1", description="Privacy tool for metadata removal")


class SanitizeRequest(BaseModel):
    """Request model for sanitize endpoint."""
    file_path: str


class SanitizeResponse(BaseModel):
    """Response model for sanitize endpoint."""
    success: bool
    message: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None


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
async def sanitize_endpoint(request: SanitizeRequest):
    """
    Sanitize a file by removing metadata.
    
    Args:
        request: Contains file_path to sanitize
        
    Returns:
        SanitizeResponse with result
    """
    file_path = request.file_path
    
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    
    try:
        result = sanitize_file(file_path)
        return {
            "success": True,
            "message": "File sanitized successfully",
            "file_path": result.get("file"),
            "file_size": result.get("file_size"),
        }
    except CleanerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during sanitization: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


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
