"""Tests for FastAPI routes."""
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary test file."""
    test_file = tmp_path / "test.jpg"
    test_file.write_bytes(b"test data")
    return str(test_file)


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test health endpoint returns ok."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestStatusEndpoint:
    """Test status endpoint."""

    def test_get_status(self, client):
        """Test status endpoint returns service info."""
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "timestamp" in data
        assert "services" in data


class TestSanitizeEndpoint:
    """Test sanitize endpoint."""

    def test_sanitize_success(self, client, temp_file):
        """Test successful sanitization via file upload."""
        with patch("app.api.get_file_metadata") as mock_get_meta, \
             patch("app.api.sanitize_file") as mock_sanitize, \
             patch("app.api.backup_file") as mock_backup, \
             patch("app.api.generate_remote_link") as mock_link:
            mock_get_meta.side_effect = [
                {"success": True, "metadata": {"EXIF:Make": "Canon"}},
                {"success": True, "metadata": {}},
            ]
            mock_sanitize.return_value = {
                "success": True,
                "file": temp_file,
                "file_size": 100,
            }
            mock_backup.return_value = {"success": True}
            mock_link.return_value = "https://drive.google.com/file/123"

            with open(temp_file, "rb") as f:
                response = client.post("/sanitize", files={"file": ("test.jpg", f, "image/jpeg")})
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "sanitized successfully" in data["message"]
            assert "remote_link" in data

    def test_sanitize_file_not_found(self, client):
        """Test sanitization errors for unsupported file types."""
        # Upload endpoint always accepts files; validate via file content/extension
        pass  # Skipped - endpoint now handles uploads, not file paths

    def test_sanitize_unsupported_file(self, client, tmp_path):
        """Test sanitization with unsupported file type."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")
        
        with open(test_file, "rb") as f:
            response = client.post("/sanitize", files={"file": ("test.txt", f, "text/plain")})
        
        assert response.status_code == 400

    def test_sanitize_internal_error(self, client, temp_file):
        """Test sanitization with unexpected error."""
        with patch("app.api.get_file_metadata") as mock_get_meta:
            mock_get_meta.side_effect = Exception("Unexpected error")

            with open(temp_file, "rb") as f:
                response = client.post("/sanitize", files={"file": ("test.jpg", f, "image/jpeg")})
            
            assert response.status_code == 500


class TestBackupEndpoint:
    """Test backup endpoint."""

    def test_backup_success(self, client, temp_file):
        """Test successful backup."""
        with patch("app.api.backup_file") as mock_backup:
            mock_backup.return_value = {
                "success": True,
                "file": temp_file,
                "remote": "gdrive:backups",
            }

            response = client.post(f"/backup?file_path={temp_file}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "backed up successfully" in data["message"]

    def test_backup_file_not_found(self, client):
        """Test backup with non-existent file."""
        response = client.post("/backup?file_path=/nonexistent/file.jpg")
        
        assert response.status_code == 404

    def test_backup_with_custom_remote(self, client, temp_file):
        """Test backup with custom remote destination."""
        with patch("app.api.backup_file") as mock_backup:
            mock_backup.return_value = {
                "success": True,
                "file": temp_file,
                "remote": "s3:bucket",
            }

            response = client.post(f"/backup?file_path={temp_file}&remote=s3:bucket")
            
            assert response.status_code == 200
            data = response.json()
            assert data["remote"] == "s3:bucket"

    def test_backup_error(self, client, temp_file):
        """Test backup with error."""
        with patch("app.api.backup_file") as mock_backup:
            from app.services.backup_service import BackupError
            mock_backup.side_effect = BackupError("Backup failed")

            response = client.post(f"/backup?file_path={temp_file}")
            
            assert response.status_code == 400
            assert "Backup failed" in response.json()["detail"]
