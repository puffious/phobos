"""Rclone backup service for uploading files to cloud storage."""
import json
import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class BackupError(Exception):
    """Raised when backup operation fails."""


def backup_file(local_path: str, remote_dest: str) -> dict:
    """
    Backup a file to cloud storage using rclone.

    Args:
        local_path: Path to the local file to backup
        remote_dest: Remote destination (e.g., 'gdrive:backups')

    Returns:
        dict: Result metadata from backup operation

    Raises:
        BackupError: If the file doesn't exist or rclone command fails
        FileNotFoundError: If the local file doesn't exist
    """
    local_file = Path(local_path)
    logger.debug(f"Starting backup for {local_path} to {remote_dest}")

    # Validate local file exists
    if not local_file.exists():
        logger.error(f"Local file not found: {local_path}")
        raise FileNotFoundError(f"Local file not found: {local_path}")

    if not local_file.is_file():
        logger.error(f"Path is not a file: {local_path}")
        raise BackupError(f"Path is not a file: {local_path}")

    # Build rclone copy command (without --json, not supported for copy)
    cmd = [
        "rclone",
        "copy",
        str(local_file),
        remote_dest,
    ]
    logger.debug(f"Running rclone command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as e:
        logger.error(f"rclone not found in PATH: {e}")
        raise BackupError(f"rclone not found in PATH: {e}")

    # Parse output
    output_lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
    errors = result.stderr.strip().split("\n") if result.stderr.strip() else []

    # Check exit code
    if result.returncode != 0:
        error_msg = " ".join(errors) if errors else "rclone command failed"
        logger.error(f"Backup failed for {local_path}: {error_msg} (exit code: {result.returncode})")
        raise BackupError(f"Backup failed: {error_msg} (exit code: {result.returncode})")

    logger.info(f"Backup successful for {local_path} to {remote_dest}")

    # Parse the output - rclone may output multiple JSON objects
    parsed_output = {
        "success": True,
        "file": local_path,
        "remote": remote_dest,
        "output": output_lines,
        "exit_code": result.returncode,
        "json_output": None,
    }

    # Try to parse each line as JSON if available
    if output_lines:
        try:
            parsed_output["json_output"] = [
                json.loads(line) for line in output_lines if line.strip()
            ]
        except json.JSONDecodeError:
            # If JSON parsing fails, just store raw output
            parsed_output["json_output"] = None

    return parsed_output


def generate_remote_link(remote_path: str) -> str:
    """Generate a shareable link for a file on the remote using rclone link."""
    logger.debug(f"Generating link for {remote_path}")
    cmd = ["rclone", "link", remote_path]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as e:
        logger.error(f"rclone not found in PATH: {e}")
        raise BackupError(f"rclone not found in PATH: {e}")

    if result.returncode != 0:
        error_msg = result.stderr.strip() if result.stderr.strip() else "rclone link failed"
        logger.error(f"Failed to generate link for {remote_path}: {error_msg}")
        raise BackupError(f"Failed to generate link: {error_msg} (exit code: {result.returncode})")

    link = result.stdout.strip()
    if not link:
        logger.error(f"rclone link returned empty output for {remote_path}")
        raise BackupError("rclone link returned empty output")

    logger.info(f"Generated link for {remote_path}")
    return link
