"""Metadata removal service using exiftool."""
import subprocess
from pathlib import Path


class CleanerError(Exception):
    """Raised when metadata removal operation fails."""


# Supported file extensions for metadata removal
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".docx", ".pdf", ".mp4", ".mov"}


def sanitize_file(file_path: str) -> dict:
    """
    Remove metadata from a file using exiftool.

    Args:
        file_path: Path to the file to sanitize

    Returns:
        dict: Result metadata including success status and file info

    Raises:
        CleanerError: If the file extension is not supported, file doesn't exist, or exiftool fails
        FileNotFoundError: If the file doesn't exist
    """
    file_obj = Path(file_path)

    # Validate file exists
    if not file_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not file_obj.is_file():
        raise CleanerError(f"Path is not a file: {file_path}")

    # Validate file extension
    file_ext = file_obj.suffix.lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise CleanerError(
            f"Unsupported file extension '{file_ext}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    # Build exiftool command to remove all metadata
    cmd = [
        "exiftool",
        "-all=",
        "-overwrite_original",
        str(file_obj),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as e:
        raise CleanerError(f"exiftool not found in PATH: {e}")

    # Check exit code
    if result.returncode != 0:
        error_msg = result.stderr.strip() if result.stderr.strip() else "exiftool command failed"
        raise CleanerError(
            f"Metadata removal failed for {file_path}: {error_msg} (exit code: {result.returncode})"
        )

    # Return success metadata
    return {
        "success": True,
        "file": file_path,
        "extension": file_ext,
        "file_size": file_obj.stat().st_size,
        "exit_code": result.returncode,
        "output": result.stdout.strip(),
    }
