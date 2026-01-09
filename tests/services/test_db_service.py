"""Tests for Firestore file event logging."""
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.services.db_service import DatabaseError, log_file_event, reset_db_client


class TestLogFileEvent:
    """Test file event logging to Firestore."""

    def teardown_method(self):
        """Reset the db client after each test."""
        reset_db_client()

    def test_log_file_event_success(self):
        """Test successful file event logging."""
        with patch("app.services.db_service.get_db_client") as mock_get_db:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_doc_ref = MagicMock()
            mock_write_result = MagicMock()
            mock_write_result.id = "doc123"

            mock_db.collection.return_value = mock_collection
            mock_collection.add.return_value = (mock_doc_ref, mock_write_result)
            mock_get_db.return_value = mock_db

            timestamp = datetime(2026, 1, 9, 12, 0, 0)
            doc_id = log_file_event(
                "photo.jpg",
                original_backed_up=True,
                timestamp=timestamp,
                file_type="jpg",
            )

            assert doc_id == "doc123"
            mock_db.collection.assert_called_once_with("file_events")
            mock_collection.add.assert_called_once()

    def test_log_file_event_defaults(self):
        """Test logging with default timestamp."""
        with patch("app.services.db_service.get_db_client") as mock_get_db:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_doc_ref = MagicMock()
            mock_write_result = MagicMock()
            mock_write_result.id = "doc456"

            mock_db.collection.return_value = mock_collection
            mock_collection.add.return_value = (mock_doc_ref, mock_write_result)
            mock_get_db.return_value = mock_db

            doc_id = log_file_event("document.pdf", original_backed_up=False)

            assert doc_id == "doc456"
            # Check that data was passed
            call_args = mock_collection.add.call_args[0][0]
            assert call_args["filename"] == "document.pdf"
            assert call_args["original_backed_up"] is False
            assert "timestamp" in call_args
            assert call_args["file_type"] is None

    def test_log_file_event_with_additional_data(self):
        """Test logging with additional metadata."""
        with patch("app.services.db_service.get_db_client") as mock_get_db:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_doc_ref = MagicMock()
            mock_write_result = MagicMock()
            mock_write_result.id = "doc789"

            mock_db.collection.return_value = mock_collection
            mock_collection.add.return_value = (mock_doc_ref, mock_write_result)
            mock_get_db.return_value = mock_db

            additional = {"file_size": 2048, "sanitized": True}
            doc_id = log_file_event(
                "video.mp4",
                original_backed_up=True,
                file_type="mp4",
                additional_data=additional,
            )

            assert doc_id == "doc789"
            call_args = mock_collection.add.call_args[0][0]
            assert call_args["file_size"] == 2048
            assert call_args["sanitized"] is True

    def test_log_file_event_database_error(self):
        """Test logging fails when get_db_client raises DatabaseError."""
        with patch("app.services.db_service.get_db_client") as mock_get_db:
            mock_get_db.side_effect = DatabaseError("DB connection failed")

            with pytest.raises(DatabaseError, match="Cannot log file event"):
                log_file_event("file.txt", original_backed_up=True)

    def test_log_file_event_disabled(self):
        """Test logging is skipped when FIREBASE_ENABLED=false."""
        with patch.dict(os.environ, {"FIREBASE_ENABLED": "false"}):
            with patch("app.services.db_service.get_db_client") as mock_get_db:
                doc_id = log_file_event("file.txt", original_backed_up=True)

                assert doc_id == "firebase_disabled"
                mock_get_db.assert_not_called()

    def test_log_file_event_firestore_write_fails(self):
        """Test logging fails when Firestore write fails."""
        with patch("app.services.db_service.get_db_client") as mock_get_db:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_collection.add.side_effect = Exception("Write failed")

            mock_db.collection.return_value = mock_collection
            mock_get_db.return_value = mock_db

            with pytest.raises(DatabaseError, match="Failed to log file event"):
                log_file_event("file.jpg", original_backed_up=True)

    def test_log_file_event_collection_name(self):
        """Test that events are logged to 'file_events' collection."""
        with patch("app.services.db_service.get_db_client") as mock_get_db:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_doc_ref = MagicMock()
            mock_write_result = MagicMock()
            mock_write_result.id = "doc_xyz"

            mock_db.collection.return_value = mock_collection
            mock_collection.add.return_value = (mock_doc_ref, mock_write_result)
            mock_get_db.return_value = mock_db

            log_file_event("test.pdf", original_backed_up=True)

            mock_db.collection.assert_called_once_with("file_events")

    def test_log_file_event_stores_all_fields(self):
        """Test that all provided fields are stored."""
        with patch("app.services.db_service.get_db_client") as mock_get_db:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_doc_ref = MagicMock()
            mock_write_result = MagicMock()
            mock_write_result.id = "doc_all"

            mock_db.collection.return_value = mock_collection
            mock_collection.add.return_value = (mock_doc_ref, mock_write_result)
            mock_get_db.return_value = mock_db

            timestamp = datetime(2026, 1, 9, 15, 30, 45)
            log_file_event(
                filename="photo.jpg",
                original_backed_up=True,
                timestamp=timestamp,
                file_type="jpg",
            )

            call_args = mock_collection.add.call_args[0][0]
            assert call_args["filename"] == "photo.jpg"
            assert call_args["original_backed_up"] is True
            assert call_args["timestamp"] == timestamp
            assert call_args["file_type"] == "jpg"

    def test_log_file_event_with_none_values(self):
        """Test logging with None values for optional fields."""
        with patch("app.services.db_service.get_db_client") as mock_get_db:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_doc_ref = MagicMock()
            mock_write_result = MagicMock()
            mock_write_result.id = "doc_none"

            mock_db.collection.return_value = mock_collection
            mock_collection.add.return_value = (mock_doc_ref, mock_write_result)
            mock_get_db.return_value = mock_db

            log_file_event("file.bin", original_backed_up=False, file_type=None, additional_data=None)

            call_args = mock_collection.add.call_args[0][0]
            assert call_args["file_type"] is None

    def test_log_file_event_additional_data_overwrites(self):
        """Test that additional_data can add/update fields."""
        with patch("app.services.db_service.get_db_client") as mock_get_db:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_doc_ref = MagicMock()
            mock_write_result = MagicMock()
            mock_write_result.id = "doc_upd"

            mock_db.collection.return_value = mock_collection
            mock_collection.add.return_value = (mock_doc_ref, mock_write_result)
            mock_get_db.return_value = mock_db

            additional = {
                "extra_field": "value",
                "processed_at": datetime.now(),
                "metadata": {"key": "value"},
            }
            log_file_event(
                "file.txt",
                original_backed_up=True,
                additional_data=additional,
            )

            call_args = mock_collection.add.call_args[0][0]
            assert call_args["extra_field"] == "value"
            assert "processed_at" in call_args
            assert call_args["metadata"] == {"key": "value"}

    def test_log_file_event_returns_document_id(self):
        """Test that function returns the document ID."""
        with patch("app.services.db_service.get_db_client") as mock_get_db:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_doc_ref = MagicMock()
            mock_write_result = MagicMock()

            test_doc_id = "unique_doc_id_12345"
            mock_write_result.id = test_doc_id

            mock_db.collection.return_value = mock_collection
            mock_collection.add.return_value = (mock_doc_ref, mock_write_result)
            mock_get_db.return_value = mock_db

            returned_id = log_file_event("file.jpg", original_backed_up=True)

            assert returned_id == test_doc_id

    def test_log_file_event_multiple_calls(self):
        """Test logging multiple events creates separate documents."""
        with patch("app.services.db_service.get_db_client") as mock_get_db:
            mock_db = MagicMock()
            mock_collection = MagicMock()

            doc_ids = ["doc1", "doc2", "doc3"]
            mock_results = []
            for doc_id in doc_ids:
                mock_doc_ref = MagicMock()
                mock_write_result = MagicMock()
                mock_write_result.id = doc_id
                mock_results.append((mock_doc_ref, mock_write_result))

            mock_collection.add.side_effect = mock_results
            mock_db.collection.return_value = mock_collection
            mock_get_db.return_value = mock_db

            id1 = log_file_event("file1.jpg", original_backed_up=True)
            id2 = log_file_event("file2.pdf", original_backed_up=False)
            id3 = log_file_event("file3.mp4", original_backed_up=True)

            assert id1 == "doc1"
            assert id2 == "doc2"
            assert id3 == "doc3"
            assert mock_collection.add.call_count == 3
