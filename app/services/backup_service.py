"""Rclone backup service for uploading files to cloud storage."""
import json
import subprocess
from pathlib import Path
from typing import Optional


class BackupError(Exception):
    """Raised when backup operation fails."""


def backup_file(local_path: str, remote_dest: str) -> dict:
    """
    Backup a file to cloud storage using rclone.

    Args:
        local_path: Path to the local file to backup
        remote_dest: Remote destination (e.g., 'gdrive:backups')

    Returns:
        dict: Parsed JSON output from rclone command

    Raises:
        BackupError: If the file doesn't exist or rclone command fails
        FileNotFoundError: If the local file doesn't exist
    """
    local_file = Path(local_path)

    # Validate local file exists
    if not local_file.exists():
        raise FileNotFoundError(f"Local file not found: {local_path}")

    if not local_file.is_file():
        raise BackupError(f"Path is not a file: {local_path}")

    # Build rclone copy command
    cmd = [
        "rclone",
        "copy",
        str(local_file),
        remote_dest,
        "--json",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as e:
        raise BackupError(f"rclone not found in PATH: {e}")

    # Parse JSON output
    output_lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
    errors = result.stderr.strip().split("\n") if result.stderr.strip() else []

    # Check exit code
    if result.returncode != 0:
        error_msg = " ".join(errors) if errors else "rclone command failed"
        raise BackupError(f"Backup failed: {error_msg} (exit code: {result.returncode})")

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
    cmd = ["rclone", "link", remote_path]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as e:
        raise BackupError(f"rclone not found in PATH: {e}")

    if result.returncode != 0:
        error_msg = result.stderr.strip() if result.stderr.strip() else "rclone link failed"
        raise BackupError(f"Failed to generate link: {error_msg} (exit code: {result.returncode})")

    link = result.stdout.strip()
    if not link:
        raise BackupError("rclone link returned empty output")

    return link
