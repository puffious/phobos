"""Tests for the rclone backup service."""
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.backup_service import BackupError, backup_file, generate_remote_link


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary test file."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")
    return str(test_file)


class TestBackupFile:
    """Test the backup_file function."""

    def test_backup_file_success(self, temp_file):
        """Test successful backup."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"status":"ok"}',
                stderr="",
            )

            result = backup_file(temp_file, "gdrive:backups")

            assert result["success"] is True
            assert result["file"] == temp_file
            assert result["remote"] == "gdrive:backups"
            assert result["exit_code"] == 0
            mock_run.assert_called_once()

            # Verify the command structure
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == "rclone"
            assert call_args[1] == "copy"
            assert call_args[2] == temp_file
            assert call_args[3] == "gdrive:backups"
            # --json flag removed, not supported by rclone copy

    def test_backup_file_not_found(self):
        """Test backup with non-existent file."""
        with pytest.raises(FileNotFoundError, match="Local file not found"):
            backup_file("/nonexistent/file.txt", "gdrive:backups")

    def test_backup_file_is_directory(self, tmp_path):
        """Test backup when path is a directory."""
        dir_path = tmp_path / "somedir"
        dir_path.mkdir()

        with pytest.raises(BackupError, match="Path is not a file"):
            backup_file(str(dir_path), "gdrive:backups")

    def test_backup_file_rclone_not_found(self, temp_file):
        """Test when rclone is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("rclone not found")

            with pytest.raises(BackupError, match="rclone not found in PATH"):
                backup_file(temp_file, "gdrive:backups")

    def test_backup_file_rclone_fails(self, temp_file):
        """Test when rclone command fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="Permission denied",
            )

            with pytest.raises(BackupError, match="Backup failed"):
                backup_file(temp_file, "gdrive:backups")

    def test_backup_file_json_parsing(self, temp_file):
        """Test JSON output parsing."""
        json_output = '{"status": "ok", "transferred": 1}'

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json_output,
                stderr="",
            )

            result = backup_file(temp_file, "gdrive:backups")

            assert result["json_output"] is not None
            assert result["json_output"][0]["status"] == "ok"

    def test_backup_file_multiple_json_lines(self, temp_file):
        """Test parsing multiple JSON output lines."""
        json_output = '{"status": "ok"}\n{"transferred": 1}'

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=json_output,
                stderr="",
            )

            result = backup_file(temp_file, "gdrive:backups")

            assert len(result["json_output"]) == 2
            assert result["json_output"][0]["status"] == "ok"
            assert result["json_output"][1]["transferred"] == 1

    def test_backup_file_empty_output(self, temp_file):
        """Test handling empty rclone output."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="",
                stderr="",
            )

            result = backup_file(temp_file, "gdrive:backups")

            assert result["success"] is True
            assert result["output"] == []
            assert result["json_output"] is None

    def test_backup_file_invalid_json_in_output(self, temp_file):
        """Test handling invalid JSON in output."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="not valid json",
                stderr="",
            )

            result = backup_file(temp_file, "gdrive:backups")

            assert result["success"] is True
            assert result["json_output"] is None  # Invalid JSON is ignored

    def test_backup_file_with_special_characters(self, tmp_path):
        """Test backup with special characters in filename."""
        test_file = tmp_path / "test file (1).txt"
        test_file.write_text("test")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="",
                stderr="",
            )

            result = backup_file(str(test_file), "gdrive:backups")

            assert result["success"] is True
            assert result["file"] == str(test_file)


class TestGenerateRemoteLink:
    """Test the generate_remote_link helper."""

    def test_generate_remote_link_success(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="https://drive.google.com/some/link\n",
                stderr="",
            )

            link = generate_remote_link("gdrive:backups/file.jpg")
            assert link == "https://drive.google.com/some/link"

            call_args = mock_run.call_args[0][0]
            assert call_args[:2] == ["rclone", "link"]

    def test_generate_remote_link_rclone_missing(self):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("rclone not found")

            with pytest.raises(BackupError, match="rclone not found"):
                generate_remote_link("gdrive:backups/file.jpg")

    def test_generate_remote_link_failure_exit_code(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="boom",
            )

            with pytest.raises(BackupError, match="Failed to generate link"):
                generate_remote_link("gdrive:backups/file.jpg")

    def test_generate_remote_link_empty_output(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="",
                stderr="",
            )

            with pytest.raises(BackupError, match="returned empty output"):
                generate_remote_link("gdrive:backups/file.jpg")
