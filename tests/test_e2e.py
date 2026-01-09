"""End-to-end smoke tests for CleanSlate."""
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestE2ESmoke:
    """End-to-end smoke tests."""

    def test_backup_sanitize_log_workflow(self, tmp_path):
        """Test the full workflow: backup → sanitize → log."""
        # Create a test file
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"fake image data with metadata")

        with patch("app.services.backup_service.subprocess.run") as mock_backup_run:
            with patch("app.services.cleaner_service.subprocess.run") as mock_clean_run:
                with patch("app.services.db_service.get_db_client") as mock_db:
                    # Mock successful backup
                    mock_backup_run.return_value = MagicMock(
                        returncode=0,
                        stdout='{"status":"ok"}',
                        stderr="",
                    )

                    # Mock successful sanitization
                    mock_clean_run.return_value = MagicMock(
                        returncode=0,
                        stdout="1 image files updated",
                        stderr="",
                    )

                    # Mock Firestore logging
                    mock_firestore = MagicMock()
                    mock_collection = MagicMock()
                    mock_doc_ref = MagicMock()
                    mock_write_result = MagicMock()
                    mock_write_result.id = "doc123"

                    mock_firestore.collection.return_value = mock_collection
                    mock_collection.add.return_value = (mock_doc_ref, mock_write_result)
                    mock_db.return_value = mock_firestore

                    # Execute workflow
                    from app.services.backup_service import backup_file
                    from app.services.cleaner_service import sanitize_file
                    from app.services.db_service import log_file_event

                    # Step 1: Backup
                    backup_result = backup_file(str(test_file), "gdrive:backups")
                    assert backup_result["success"] is True

                    # Step 2: Sanitize
                    sanitize_result = sanitize_file(str(test_file))
                    assert sanitize_result["success"] is True

                    # Step 3: Log
                    doc_id = log_file_event(
                        filename="test.jpg",
                        original_backed_up=True,
                        file_type="jpg",
                    )
                    assert doc_id == "doc123"

    def test_watcher_integration(self, tmp_path):
        """Test file watcher integration."""
        watch_dir = tmp_path / "watch"
        output_dir = tmp_path / "output"
        watch_dir.mkdir()
        output_dir.mkdir()

        test_file = watch_dir / "test.jpg"
        test_file.write_bytes(b"test data")

        with patch("app.daemon.watcher.backup_file") as mock_backup:
            with patch("app.daemon.watcher.sanitize_file") as mock_sanitize:
                with patch("app.daemon.watcher.log_file_event") as mock_log:
                    mock_backup.return_value = {"success": True}
                    mock_sanitize.return_value = {"success": True}

                    from app.daemon.watcher import FileProcessingHandler

                    handler = FileProcessingHandler(
                        str(watch_dir),
                        str(output_dir),
                        "gdrive:backups"
                    )

                    # Process the file
                    handler.process_file(str(test_file))

                    # Verify all steps were called
                    mock_backup.assert_called_once()
                    mock_sanitize.assert_called_once()
                    mock_log.assert_called_once()

                    # File should be moved
                    assert not test_file.exists()
                    assert (output_dir / "test.jpg").exists()

    def test_api_endpoints_integration(self):
        """Test API endpoints work together."""
        from fastapi.testclient import TestClient
        from app.api import app

        client = TestClient(app)

        # Test health check
        response = client.get("/health")
        assert response.status_code == 200

        # Test status endpoint
        response = client.get("/status")
        assert response.status_code == 200
        assert response.json()["status"] == "running"

    def test_cli_commands_integration(self, tmp_path):
        """Test CLI commands work."""
        from typer.testing import CliRunner
        from app.cli import app

        runner = CliRunner()

        # Test health
        result = runner.invoke(app, ["health"])
        assert result.exit_code == 0

        # Test sanitize with mocked service
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"test")

        with patch("app.cli.sanitize_file") as mock_sanitize:
            mock_sanitize.return_value = {
                "success": True,
                "file": str(test_file),
                "file_size": 100,
            }

            result = runner.invoke(app, ["sanitize", str(test_file)])
            assert result.exit_code == 0

    def test_config_loading(self):
        """Test configuration loading."""
        with patch.dict("os.environ", {
            "DAEMON_MODE": "true",
            "WATCH_DIR": "/test/watch",
            "OUTPUT_DIR": "/test/output",
            "RCLONE_REMOTE_NAME": "gdrive",
            "RCLONE_DEST_PATH": "backups",
        }):
            from app.config import load_config

            config = load_config()

            assert config.daemon_mode is True
            assert str(config.watch_dir) == "/test/watch"
            assert str(config.output_dir) == "/test/output"
            assert config.rclone_remote_name == "gdrive"
            assert config.rclone_dest_path == "backups"

    def test_error_handling_resilience(self, tmp_path):
        """Test that errors in one step don't block others."""
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"test")

        with patch("app.services.backup_service.subprocess.run") as mock_backup:
            with patch("app.services.cleaner_service.subprocess.run") as mock_clean:
                with patch("app.services.db_service.get_db_client") as mock_db:
                    # Backup fails
                    mock_backup.return_value = MagicMock(
                        returncode=1,
                        stdout="",
                        stderr="Backup error",
                    )

                    # Sanitize succeeds
                    mock_clean.return_value = MagicMock(
                        returncode=0,
                        stdout="1 image files updated",
                        stderr="",
                    )

                    # Mock Firestore
                    mock_firestore = MagicMock()
                    mock_collection = MagicMock()
                    mock_doc_ref = MagicMock()
                    mock_write_result = MagicMock()
                    mock_write_result.id = "doc_error"

                    mock_firestore.collection.return_value = mock_collection
                    mock_collection.add.return_value = (mock_doc_ref, mock_write_result)
                    mock_db.return_value = mock_firestore

                    from app.services.cleaner_service import sanitize_file
                    from app.services.db_service import log_file_event

                    # Sanitize should still work
                    result = sanitize_file(str(test_file))
                    assert result["success"] is True

                    # And logging should work
                    doc_id = log_file_event(
                        filename="test.jpg",
                        original_backed_up=False,
                        file_type="jpg",
                    )
                    assert doc_id == "doc_error"
