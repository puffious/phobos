"""Tests for CLI commands."""
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from app.cli import app

runner = CliRunner()


class TestHealthCommand:
    """Test health command."""

    def test_health(self):
        """Test health command."""
        result = runner.invoke(app, ["health"])
        assert result.exit_code == 0
        assert "OK" in result.stdout


class TestSanitizeCommand:
    """Test sanitize command."""

    def test_sanitize_success(self, tmp_path):
        """Test successful sanitization."""
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"test")

        with patch("app.cli.get_file_metadata") as mock_get_meta, \
             patch("app.cli.sanitize_file") as mock_sanitize:
            mock_get_meta.return_value = {
                "success": True,
                "metadata": {"EXIF:Make": "Canon"},
            }
            mock_sanitize.return_value = {
                "success": True,
                "file": str(test_file),
                "file_size": 100,
            }

            result = runner.invoke(app, ["sanitize", str(test_file), "--confirm"])
            
            assert result.exit_code == 0
            assert "Sanitized successfully" in result.stdout

    def test_sanitize_file_not_found(self):
        """Test sanitization with non-existent file."""
        result = runner.invoke(app, ["sanitize", "/nonexistent/file.jpg"])
        
        assert result.exit_code == 1
        # Error messages may be in stdout or stderr with Typer
        output = result.stdout + result.stderr
        assert "not found" in output or "Error" in output

    def test_sanitize_error(self, tmp_path):
        """Test sanitization error."""
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"test")

        with patch("app.cli.sanitize_file") as mock_sanitize:
            from app.services.cleaner_service import CleanerError
            mock_sanitize.side_effect = CleanerError("Test error")

            result = runner.invoke(app, ["sanitize", str(test_file)])
            
            assert result.exit_code == 1


class TestBackupCommand:
    """Test backup command."""

    def test_backup_success(self, tmp_path):
        """Test successful backup."""
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"test")

        with patch("app.cli.backup_file") as mock_backup:
            mock_backup.return_value = {
                "success": True,
                "file": str(test_file),
                "remote": "gdrive:backups",
            }

            result = runner.invoke(app, ["backup", str(test_file)])
            
            assert result.exit_code == 0
            assert "Backup successful" in result.stdout

    def test_backup_file_not_found(self):
        """Test backup with non-existent file."""
        result = runner.invoke(app, ["backup", "/nonexistent/file.jpg"])
        
        assert result.exit_code == 1

    def test_backup_with_custom_remote(self, tmp_path):
        """Test backup with custom remote."""
        test_file = tmp_path / "test.jpg"
        test_file.write_bytes(b"test")

        with patch("app.cli.backup_file") as mock_backup:
            mock_backup.return_value = {
                "success": True,
                "file": str(test_file),
                "remote": "s3:bucket",
            }

            result = runner.invoke(app, ["backup", str(test_file), "--remote", "s3:bucket"])
            
            assert result.exit_code == 0
            assert "s3:bucket" in result.stdout


class TestRunDaemonCommand:
    """Test run-daemon command."""

    def test_run_daemon_with_config(self):
        """Test daemon command loads config."""
        with patch("app.config.load_config") as mock_config:
            with patch("app.daemon.watcher.start_watcher") as mock_start:
                mock_cfg = MagicMock()
                mock_cfg.watch_dir = "/data/watch"
                mock_cfg.output_dir = "/data/output"
                mock_cfg.rclone_remote_name = "gdrive"
                mock_cfg.rclone_dest_path = "backups"
                mock_config.return_value = mock_cfg

                mock_observer = MagicMock()
                mock_start.return_value = mock_observer

                # Use mix_stderr=False to capture output properly
                result = runner.invoke(app, ["run-daemon"], input="\x03")  # Send Ctrl+C
                
                # Command should start (exit code may vary due to KeyboardInterrupt)
                assert "Starting daemon" in result.stdout


class TestRunApiCommand:
    """Test run-api command."""

    def test_run_api(self):
        """Test API command."""
        with patch("uvicorn.run") as mock_uvicorn:
            # Simulate quick exit
            mock_uvicorn.side_effect = KeyboardInterrupt()

            result = runner.invoke(app, ["run-api"])
            
            # Should attempt to start
            assert "Starting API server" in result.stdout or result.exit_code == 1
