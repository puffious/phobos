"""File watcher daemon for monitoring and processing files."""
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Optional

from watchdog.events import FileSystemEventHandler, FileCreatedEvent
from watchdog.observers import Observer

from app.services.backup_service import backup_file, BackupError
from app.services.cleaner_service import sanitize_file, CleanerError, SUPPORTED_EXTENSIONS
from app.services.db_service import log_file_event, DatabaseError

logger = logging.getLogger(__name__)


class FileProcessingHandler(FileSystemEventHandler):
    """Handler for file creation events."""

    def __init__(self, watch_dir: str, output_dir: str, rclone_remote: str):
        """
        Initialize the file processing handler.

        Args:
            watch_dir: Directory to watch for new files
            output_dir: Directory to move processed files to
            rclone_remote: Rclone remote destination (e.g., 'gdrive:backups')
        """
        self.watch_dir = Path(watch_dir)
        self.output_dir = Path(output_dir)
        self.rclone_remote = rclone_remote

        # Ensure directories exist
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def on_created(self, event: FileCreatedEvent):
        """Handle file creation events."""
        if event.is_directory:
            return

        # Ignore temporary/hidden files
        file_path = Path(event.src_path)
        if file_path.name.startswith('.') or file_path.name.startswith('~'):
            logger.debug(f"Ignoring temporary file: {file_path.name}")
            return

        # Check if file extension is supported
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            logger.warning(f"Skipping unsupported file type: {file_path.name}")
            return

        # Small delay to ensure file is fully written
        time.sleep(0.5)

        logger.info(f"Processing new file: {file_path.name}")
        self.process_file(str(file_path))

    def process_file(self, file_path: str):
        """
        Process a single file: backup, sanitize, move, and log.

        Args:
            file_path: Path to the file to process
        """
        file_obj = Path(file_path)
        filename = file_obj.name
        file_type = file_obj.suffix.lower().lstrip('.')

        backed_up = False
        sanitized = False
        error_msg = None

        try:
            # Step 1: Backup to cloud
            logger.info(f"Backing up {filename}...")
            backup_result = backup_file(file_path, self.rclone_remote)
            backed_up = backup_result.get('success', False)
            logger.info(f"Backup successful: {filename}")

        except (BackupError, FileNotFoundError) as e:
            error_msg = f"Backup failed: {e}"
            logger.error(error_msg)

        try:
            # Step 2: Sanitize metadata
            logger.info(f"Sanitizing {filename}...")
            sanitize_result = sanitize_file(file_path)
            sanitized = sanitize_result.get('success', False)
            logger.info(f"Sanitization successful: {filename}")

        except (CleanerError, FileNotFoundError) as e:
            error_msg = f"Sanitization failed: {e}"
            logger.error(error_msg)

        try:
            # Step 3: Move to output directory
            if sanitized:
                dest_path = self.output_dir / filename
                # Handle name conflicts
                counter = 1
                while dest_path.exists():
                    stem = file_obj.stem
                    suffix = file_obj.suffix
                    dest_path = self.output_dir / f"{stem}_{counter}{suffix}"
                    counter += 1

                shutil.move(str(file_obj), str(dest_path))
                logger.info(f"Moved to {dest_path}")

        except Exception as e:
            error_msg = f"Failed to move file: {e}"
            logger.error(error_msg)

        try:
            # Step 4: Log to database
            additional_data = {
                'sanitized': sanitized,
                'error': error_msg,
            }
            log_file_event(
                filename=filename,
                original_backed_up=backed_up,
                file_type=file_type,
                additional_data=additional_data,
            )
            logger.info(f"Logged event for {filename}")

        except DatabaseError as e:
            logger.error(f"Failed to log event: {e}")


def start_watcher(watch_dir: str, output_dir: str, rclone_remote: str) -> Observer:
    """
    Start the file watcher daemon.

    Args:
        watch_dir: Directory to watch for new files
        output_dir: Directory to move processed files to
        rclone_remote: Rclone remote destination

    Returns:
        Observer: The watchdog observer instance
    """
    event_handler = FileProcessingHandler(watch_dir, output_dir, rclone_remote)
    observer = Observer()
    observer.schedule(event_handler, str(watch_dir), recursive=False)
    observer.start()
    logger.info(f"Watcher started on {watch_dir}")
    return observer


def stop_watcher(observer: Observer):
    """
    Stop the file watcher daemon.

    Args:
        observer: The watchdog observer instance to stop
    """
    observer.stop()
    observer.join()
    logger.info("Watcher stopped")
