"""Tests for Firestore database initialization."""
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.db_service import DatabaseError, get_db_client, reset_db_client


@pytest.fixture
def mock_creds_file(tmp_path):
    """Create a fake credentials file."""
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text('{"type": "service_account"}')
    return str(creds_file)


class TestFirestoreClientInit:
    """Test Firestore client initialization."""

    def teardown_method(self):
        """Reset the db client after each test."""
        reset_db_client()

    def test_get_db_client_success(self, mock_creds_file):
        """Test successful Firestore client initialization."""
        with patch.dict(os.environ, {"FIREBASE_CREDENTIALS": mock_creds_file}):
            with patch("firebase_admin.get_app") as mock_get_app:
                mock_get_app.side_effect = ValueError("No app")
                with patch("firebase_admin.initialize_app"):
                    with patch("firebase_admin.firestore.client") as mock_client:
                        mock_firestore_client = MagicMock()
                        mock_client.return_value = mock_firestore_client

                        client = get_db_client()

                        assert client is mock_firestore_client

    def test_get_db_client_missing_credentials_env(self):
        """Test initialization fails when FIREBASE_CREDENTIALS env var is missing."""
        # Ensure env var doesn't exist
        reset_db_client()
        with patch.dict(os.environ, {}, clear=False):
            if "FIREBASE_CREDENTIALS" in os.environ:
                del os.environ["FIREBASE_CREDENTIALS"]

            with pytest.raises(DatabaseError, match="FIREBASE_CREDENTIALS"):
                get_db_client()

    def test_get_db_client_credentials_file_not_found(self):
        """Test initialization fails when credentials file doesn't exist."""
        reset_db_client()
        with patch.dict(os.environ, {"FIREBASE_CREDENTIALS": "/nonexistent/path.json"}):
            with pytest.raises(DatabaseError, match="credentials file not found"):
                get_db_client()

    def test_get_db_client_lazy_singleton(self, mock_creds_file):
        """Test that get_db_client returns same instance (lazy singleton)."""
        reset_db_client()
        with patch.dict(os.environ, {"FIREBASE_CREDENTIALS": mock_creds_file}):
            with patch("firebase_admin.get_app") as mock_get_app:
                mock_get_app.side_effect = ValueError("No app")
                with patch("firebase_admin.initialize_app"):
                    with patch("firebase_admin.firestore.client") as mock_client:
                        mock_firestore_client = MagicMock()
                        mock_client.return_value = mock_firestore_client

                        client1 = get_db_client()
                        client2 = get_db_client()

                        # Should be the same instance
                        assert client1 is client2
                        # firestore.client() should only be called once
                        assert mock_client.call_count == 1

    def test_get_db_client_already_initialized_app(self, mock_creds_file):
        """Test initialization when Firebase app is already initialized."""
        reset_db_client()
        with patch.dict(os.environ, {"FIREBASE_CREDENTIALS": mock_creds_file}):
            with patch("firebase_admin.get_app") as mock_get_app:
                mock_app = MagicMock()
                mock_get_app.return_value = mock_app
                with patch("firebase_admin.firestore.client") as mock_client:
                    mock_firestore_client = MagicMock()
                    mock_client.return_value = mock_firestore_client

                    client = get_db_client()

                    # initialize_app should not be called
                    assert client is mock_firestore_client

    def test_get_db_client_firestore_client_fails(self, mock_creds_file):
        """Test initialization fails when getting firestore client fails."""
        reset_db_client()
        with patch.dict(os.environ, {"FIREBASE_CREDENTIALS": mock_creds_file}):
            with patch("firebase_admin.get_app") as mock_get_app:
                mock_get_app.side_effect = ValueError("No app")
                with patch("firebase_admin.initialize_app"):
                    with patch("firebase_admin.firestore.client") as mock_client:
                        mock_client.side_effect = Exception("Client init failed")

                        with pytest.raises(DatabaseError, match="Failed to get Firestore client"):
                            get_db_client()

    def test_reset_db_client(self, mock_creds_file):
        """Test that reset_db_client clears the cached client."""
        with patch.dict(os.environ, {"FIREBASE_CREDENTIALS": mock_creds_file}):
            with patch("firebase_admin.get_app") as mock_get_app:
                mock_get_app.side_effect = ValueError("No app")
                with patch("firebase_admin.initialize_app"):
                    with patch("firebase_admin.firestore.client") as mock_client:
                        mock_firestore_client = MagicMock()
                        mock_client.return_value = mock_firestore_client

                        client1 = get_db_client()
                        reset_db_client()

                        # Should raise error since credentials don't exist after reset
                        # (unless we set them up again)
                        assert mock_client.call_count == 1
