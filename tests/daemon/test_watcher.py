"""Tests for the file watcher daemon."""
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.daemon.watcher import FileProcessingHandler, start_watcher, stop_watcher


@pytest.fixture
def temp_dirs(tmp_path):
    """Create temporary watch and output directories."""
    watch_dir = tmp_path / "watch"
    output_dir = tmp_path / "output"
    watch_dir.mkdir()
    output_dir.mkdir()
    return str(watch_dir), str(output_dir)


class TestFileProcessingHandler:
    """Test the file processing handler."""

    def test_handler_init_creates_dirs(self, tmp_path):
        """Test that handler creates directories if they don't exist."""
        watch_dir = tmp_path / "new_watch"
        output_dir = tmp_path / "new_output"

        handler = FileProcessingHandler(
            str(watch_dir),
            str(output_dir),
            "gdrive:backups"
        )

        assert watch_dir.exists()
        assert output_dir.exists()

    def test_process_file_success(self, temp_dirs):
        """Test successful file processing."""
        watch_dir, output_dir = temp_dirs
        test_file = Path(watch_dir) / "test.jpg"
        test_file.write_bytes(b"fake image")

        with patch("app.daemon.watcher.backup_file") as mock_backup:
            with patch("app.daemon.watcher.sanitize_file") as mock_sanitize:
                with patch("app.daemon.watcher.log_file_event") as mock_log:
                    mock_backup.return_value = {"success": True}
                    mock_sanitize.return_value = {"success": True}

                    handler = FileProcessingHandler(watch_dir, output_dir, "gdrive:backups")
                    handler.process_file(str(test_file))

                    mock_backup.assert_called_once()
                    mock_sanitize.assert_called_once()
                    mock_log.assert_called_once()

                    # File should be moved
                    assert not test_file.exists()
                    assert (Path(output_dir) / "test.jpg").exists()

    def test_process_file_ignores_unsupported_extension(self, temp_dirs):
        """Test that unsupported files are skipped."""
        watch_dir, output_dir = temp_dirs
        test_file = Path(watch_dir) / "test.txt"
        test_file.write_text("test")

        with patch("app.daemon.watcher.backup_file") as mock_backup:
            handler = FileProcessingHandler(watch_dir, output_dir, "gdrive:backups")

            # Create event for unsupported file
            event = MagicMock()
            event.is_directory = False
            event.src_path = str(test_file)

            handler.on_created(event)

            # Should not attempt backup
            mock_backup.assert_not_called()

    def test_process_file_handles_backup_failure(self, temp_dirs):
        """Test handling of backup failures."""
        watch_dir, output_dir = temp_dirs
        test_file = Path(watch_dir) / "test.jpg"
        test_file.write_bytes(b"fake image")

        with patch("app.daemon.watcher.backup_file") as mock_backup:
            with patch("app.daemon.watcher.sanitize_file") as mock_sanitize:
                with patch("app.daemon.watcher.log_file_event") as mock_log:
                    from app.services.backup_service import BackupError
                    mock_backup.side_effect = BackupError("Backup failed")
                    mock_sanitize.return_value = {"success": True}

                    handler = FileProcessingHandler(watch_dir, output_dir, "gdrive:backups")
                    handler.process_file(str(test_file))

                    # Should still attempt sanitization and logging
                    mock_sanitize.assert_called_once()
                    mock_log.assert_called_once()

                    # Check that backed_up is False in log
                    call_kwargs = mock_log.call_args[1]
                    assert call_kwargs['original_backed_up'] is False

    def test_process_file_handles_name_conflicts(self, temp_dirs):
        """Test handling of filename conflicts."""
        watch_dir, output_dir = temp_dirs
        
        # Create existing file
        existing = Path(output_dir) / "test.jpg"
        existing.write_bytes(b"existing")

        test_file = Path(watch_dir) / "test.jpg"
        test_file.write_bytes(b"new file")

        with patch("app.daemon.watcher.backup_file") as mock_backup:
            with patch("app.daemon.watcher.sanitize_file") as mock_sanitize:
                with patch("app.daemon.watcher.log_file_event"):
                    mock_backup.return_value = {"success": True}
                    mock_sanitize.return_value = {"success": True}

                    handler = FileProcessingHandler(watch_dir, output_dir, "gdrive:backups")
                    handler.process_file(str(test_file))

                    # Should create test_1.jpg
                    assert (Path(output_dir) / "test_1.jpg").exists()
                    assert existing.exists()

    def test_ignores_temporary_files(self, temp_dirs):
        """Test that temporary/hidden files are ignored."""
        watch_dir, output_dir = temp_dirs

        with patch("app.daemon.watcher.backup_file") as mock_backup:
            handler = FileProcessingHandler(watch_dir, output_dir, "gdrive:backups")

            for temp_name in [".hidden.jpg", "~temp.jpg"]:
                temp_file = Path(watch_dir) / temp_name
                temp_file.write_bytes(b"temp")

                event = MagicMock()
                event.is_directory = False
                event.src_path = str(temp_file)

                handler.on_created(event)

            # Should not process any
            mock_backup.assert_not_called()

    def test_ignores_directories(self, temp_dirs):
        """Test that directories are ignored."""
        watch_dir, output_dir = temp_dirs

        with patch("app.daemon.watcher.backup_file") as mock_backup:
            handler = FileProcessingHandler(watch_dir, output_dir, "gdrive:backups")

            event = MagicMock()
            event.is_directory = True
            event.src_path = watch_dir

            handler.on_created(event)

            mock_backup.assert_not_called()


class TestWatcherFunctions:
    """Test watcher start/stop functions."""

    def test_start_watcher(self, temp_dirs):
        """Test starting the watcher."""
        watch_dir, output_dir = temp_dirs

        observer = start_watcher(watch_dir, output_dir, "gdrive:backups")

        assert observer.is_alive()
        
        stop_watcher(observer)

    def test_stop_watcher(self, temp_dirs):
        """Test stopping the watcher."""
        watch_dir, output_dir = temp_dirs

        observer = start_watcher(watch_dir, output_dir, "gdrive:backups")
        stop_watcher(observer)

        assert not observer.is_alive()
