"""Firestore database service for logging file processing events."""
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore


class DatabaseError(Exception):
    """Raised when database operation fails."""


# Global Firestore client (lazy singleton)
_db_client: Optional[firestore.client.Client] = None


_TRUTHY = {"1", "true", "yes", "on", "y", "t"}
_FALSY = {"0", "false", "no", "off", "n", "f"}


def _firebase_enabled() -> bool:
    """Return whether Firebase logging is enabled via env flag."""
    raw = os.getenv("FIREBASE_ENABLED", "true").strip().lower()
    if raw in _TRUTHY:
        return True
    if raw in _FALSY:
        return False
    # default to False on invalid input to fail safe
    return False


def get_db_client() -> firestore.client.Client:
    """
    Get or initialize the Firestore client (lazy singleton pattern).

    The client is initialized using FIREBASE_CREDENTIALS environment variable,
    which should point to a service account JSON file.

    Returns:
        firestore.client.Client: The Firestore database client

    Raises:
        DatabaseError: If Firebase credentials are not found or invalid
    """
    if not _firebase_enabled():
        raise DatabaseError("Firebase disabled via FIREBASE_ENABLED=false")

    global _db_client

    if _db_client is not None:
        return _db_client

    # Get credentials path from environment
    creds_path = os.getenv("FIREBASE_CREDENTIALS")
    if not creds_path:
        raise DatabaseError(
            "FIREBASE_CREDENTIALS environment variable is not set. "
            "Point it to your Firebase service account JSON file."
        )

    # Validate credentials file exists
    creds_file = Path(creds_path)
    if not creds_file.exists():
        raise DatabaseError(f"Firebase credentials file not found: {creds_path}")

    try:
        # Initialize Firebase app if not already initialized
        if not firebase_admin.get_app():
            cred = credentials.Certificate(str(creds_file))
            firebase_admin.initialize_app(cred)
    except ValueError:
        # App already initialized
        pass
    except Exception as e:
        raise DatabaseError(f"Failed to initialize Firebase: {e}")

    # Get Firestore client
    try:
        _db_client = firestore.client()
    except Exception as e:
        raise DatabaseError(f"Failed to get Firestore client: {e}")

    return _db_client


def log_file_event(
    filename: str,
    original_backed_up: bool,
    timestamp: Optional[datetime] = None,
    file_type: Optional[str] = None,
    additional_data: Optional[dict] = None,
) -> str:
    """
    Log a file processing event to Firestore.

    Args:
        filename: Name of the file processed
        original_backed_up: Whether the original file was successfully backed up
        timestamp: When the event occurred (defaults to now)
        file_type: Type/extension of the file (e.g., 'jpg', 'pdf')
        additional_data: Any additional metadata to store

    Returns:
        str: The document ID of the logged event

    Raises:
        DatabaseError: If the logging operation fails
    """
    if not _firebase_enabled():
        # Skip logging entirely when disabled; return a sentinel ID
        return "firebase_disabled"

    if timestamp is None:
        timestamp = datetime.now()

    try:
        db = get_db_client()
    except DatabaseError as e:
        raise DatabaseError(f"Cannot log file event: {e}")

    # Build document data
    doc_data = {
        "filename": filename,
        "original_backed_up": original_backed_up,
        "timestamp": timestamp,
        "file_type": file_type,
    }

    # Add any additional data
    if additional_data:
        doc_data.update(additional_data)

    try:
        # Add document to 'file_events' collection
        doc_ref = db.collection("file_events").add(doc_data)
        # Return the document ID from the returned tuple (ref, write_result)
        return doc_ref[1].id if isinstance(doc_ref, tuple) else str(doc_ref.id)
    except Exception as e:
        raise DatabaseError(f"Failed to log file event: {e}")


def reset_db_client():
    """
    Reset the global Firestore client (useful for testing).

    This function should only be used in tests.
    """
    global _db_client
    _db_client = None
