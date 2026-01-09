"""Tests for the metadata cleaner service."""
from unittest.mock import MagicMock, patch

import pytest

from app.services.cleaner_service import (
    SUPPORTED_EXTENSIONS,
    CleanerError,
    get_file_metadata,
    sanitize_file,
)


@pytest.fixture
def temp_image(tmp_path):
    """Create a temporary image file."""
    test_file = tmp_path / "test.jpg"
    test_file.write_bytes(b"fake image data")
    return str(test_file)


@pytest.fixture
def temp_pdf(tmp_path):
    """Create a temporary PDF file."""
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"fake pdf data")
    return str(test_file)


class TestSanitizeFile:
    """Test the sanitize_file function."""

    def test_sanitize_file_success_jpg(self, temp_image):
        """Test successful sanitization of JPG file."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="1 image files updated",
                stderr="",
            )

            result = sanitize_file(temp_image)

            assert result["success"] is True
            assert result["file"] == temp_image
            assert result["extension"] == ".jpg"
            assert result["exit_code"] == 0
            assert "fake image data" in result.get("output", "") or result["output"] == "1 image files updated"

            # Verify the command structure
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == "exiftool"
            assert "-all=" in call_args
            assert "-overwrite_original" in call_args
            assert temp_image in call_args

    def test_sanitize_file_success_png(self, tmp_path):
        """Test successful sanitization of PNG file."""
        test_file = tmp_path / "test.png"
        test_file.write_bytes(b"fake png data")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="1 image files updated",
                stderr="",
            )

            result = sanitize_file(str(test_file))

            assert result["success"] is True
            assert result["extension"] == ".png"

    def test_sanitize_file_success_pdf(self, temp_pdf):
        """Test successful sanitization of PDF file."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="1 document updated",
                stderr="",
            )

            result = sanitize_file(temp_pdf)

            assert result["success"] is True
            assert result["extension"] == ".pdf"

    def test_sanitize_file_not_found(self):
        """Test sanitization with non-existent file."""
        with pytest.raises(FileNotFoundError, match="File not found"):
            sanitize_file("/nonexistent/file.jpg")

    def test_sanitize_file_is_directory(self, tmp_path):
        """Test sanitization when path is a directory."""
        dir_path = tmp_path / "somedir"
        dir_path.mkdir()

        with pytest.raises(CleanerError, match="Path is not a file"):
            sanitize_file(str(dir_path))

    def test_sanitize_file_unsupported_extension(self, tmp_path):
        """Test sanitization with unsupported file extension."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        with pytest.raises(CleanerError, match="Unsupported file extension"):
            sanitize_file(str(test_file))

    def test_sanitize_file_unsupported_extension_shows_supported(self, tmp_path):
        """Test that error message lists supported extensions."""
        test_file = tmp_path / "test.docm"
        test_file.write_bytes(b"fake doc")

        with pytest.raises(CleanerError) as exc_info:
            sanitize_file(str(test_file))

        error_msg = str(exc_info.value)
        assert "Unsupported" in error_msg
        assert ".jpg" in error_msg or ".png" in error_msg

    def test_sanitize_file_exiftool_not_found(self, temp_image):
        """Test when exiftool is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("exiftool not found")

            with pytest.raises(CleanerError, match="exiftool not found in PATH"):
                sanitize_file(temp_image)

    def test_sanitize_file_exiftool_fails(self, temp_image):
        """Test when exiftool command fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="Permission denied",
            )

            with pytest.raises(CleanerError, match="Metadata removal failed"):
                sanitize_file(temp_image)

    def test_sanitize_file_all_supported_extensions(self, tmp_path):
        """Test that all supported extensions are handled."""
        for ext in SUPPORTED_EXTENSIONS:
            test_file = tmp_path / f"test{ext}"
            test_file.write_bytes(b"test data")

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout="1 files updated",
                    stderr="",
                )

                result = sanitize_file(str(test_file))

                assert result["success"] is True
                assert result["extension"] == ext

    def test_sanitize_file_case_insensitive_extension(self, tmp_path):
        """Test that extension matching is case-insensitive."""
        test_file = tmp_path / "test.JPG"
        test_file.write_bytes(b"test data")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="1 image files updated",
                stderr="",
            )

            result = sanitize_file(str(test_file))

            assert result["success"] is True
            assert result["extension"] == ".jpg"

    def test_sanitize_file_with_special_characters(self, tmp_path):
        """Test sanitization of file with special characters in name."""
        test_file = tmp_path / "my photo (1).jpg"
        test_file.write_bytes(b"fake image")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="1 image files updated",
                stderr="",
            )

            result = sanitize_file(str(test_file))

            assert result["success"] is True

    def test_sanitize_file_includes_file_size(self, temp_image):
        """Test that result includes file size."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="",
                stderr="",
            )

            result = sanitize_file(temp_image)

            assert "file_size" in result
            assert result["file_size"] > 0

    def test_sanitize_file_empty_stderr_on_failure(self, temp_image):
        """Test handling failure with empty stderr."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="",
            )

            with pytest.raises(CleanerError, match="exiftool command failed"):
                sanitize_file(temp_image)

    def test_supported_extensions_contain_required(self):
        """Test that all required extensions are in SUPPORTED_EXTENSIONS."""
        required = {".jpg", ".png", ".pdf", ".mp4", ".mov"}
        assert required.issubset(SUPPORTED_EXTENSIONS)

    def test_jpeg_extension_supported(self, tmp_path):
        """Test that .jpeg extension (alternative to .jpg) is supported."""
        test_file = tmp_path / "test.jpeg"
        test_file.write_bytes(b"test data")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="",
                stderr="",
            )

            result = sanitize_file(str(test_file))

            assert result["success"] is True
            assert result["extension"] == ".jpeg"


class TestGetFileMetadata:
    """Test the get_file_metadata function."""

    def test_get_file_metadata_success(self, temp_image):
        """Test successful metadata retrieval for a file."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='[{"SourceFile": "file.jpg", "ISO": 100, "Make": "Canon"}]',
                stderr="",
            )

            result = get_file_metadata(temp_image)

            assert result["success"] is True
            assert result["metadata"]["ISO"] == 100
            assert "SourceFile" not in result["metadata"]

            call_args = mock_run.call_args[0][0]
            assert call_args[0] == "exiftool"
            assert "-json" in call_args
            assert temp_image in call_args

    def test_get_file_metadata_exiftool_not_found(self, temp_image):
        """Test metadata retrieval when exiftool is missing."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("exiftool not found")

            with pytest.raises(CleanerError, match="exiftool not found in PATH"):
                get_file_metadata(temp_image)

    def test_get_file_metadata_fails(self, temp_image):
        """Test metadata retrieval failure returns helpful error."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="Permission denied",
            )

            with pytest.raises(CleanerError, match="Metadata read failed"):
                get_file_metadata(temp_image)

    def test_get_file_metadata_bad_json(self, temp_image):
        """Test metadata retrieval handles invalid JSON output."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="not-json",
                stderr="",
            )

            with pytest.raises(CleanerError, match="Failed to parse metadata"):
                get_file_metadata(temp_image)

    def test_get_file_metadata_grouped(self, temp_image):
        """Test grouped metadata includes group prefixes and uses -G1 flag."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='[{"SourceFile": "file.jpg", "EXIF:Make": "Canon", "File:FileName": "test.jpg"}]',
                stderr="",
            )

            result = get_file_metadata(temp_image, grouped=True)

            assert result["success"] is True
            assert result["metadata"].get("EXIF:Make") == "Canon"
            assert "SourceFile" not in result["metadata"]

            call_args = mock_run.call_args[0][0]
            assert "-G1" in call_args
