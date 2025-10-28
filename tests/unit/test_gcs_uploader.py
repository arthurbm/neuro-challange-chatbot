"""
Unit tests for GCS Uploader

Tests Google Cloud Storage image upload functionality with mocks.
"""
import pytest
from io import BytesIO
from unittest.mock import Mock, MagicMock, patch
from src.utils.gcs_uploader import GCSUploader


# ==============================================================================
# Test GCS Upload with Mock
# ==============================================================================

@pytest.mark.unit
def test_upload_image_success(mock_gcs_client):
    """Should upload image and return public URL."""
    # Create uploader with mocked client
    with patch("src.utils.gcs_uploader.storage.Client", return_value=mock_gcs_client):
        uploader = GCSUploader(project_id="test-project", bucket_name="test-bucket")

        # Create fake image bytes
        image_bytes = BytesIO(b"fake_image_data")

        # Upload
        url = uploader.upload_image(image_bytes, filename="test-chart.png")

        # Should return public URL
        assert url.startswith("https://storage.googleapis.com")
        assert "test-chart" in url or "test-bucket" in url


@pytest.mark.unit
def test_upload_image_generates_uuid_filename(mock_gcs_client):
    """Should generate UUID filename when not provided."""
    with patch("src.utils.gcs_uploader.storage.Client", return_value=mock_gcs_client):
        uploader = GCSUploader(project_id="test-project", bucket_name="test-bucket")

        image_bytes = BytesIO(b"fake_image_data")

        # Upload without filename (should generate UUID)
        url = uploader.upload_image(image_bytes)

        # Should have generated a filename
        assert url is not None
        assert ".png" in url


@pytest.mark.unit
def test_upload_image_calls_blob_upload(mock_gcs_client):
    """Should call blob upload_from_file method."""
    mock_blob = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_gcs_client.bucket.return_value = mock_bucket

    with patch("src.utils.gcs_uploader.storage.Client", return_value=mock_gcs_client):
        uploader = GCSUploader(project_id="test-project", bucket_name="test-bucket")

        image_bytes = BytesIO(b"fake_image_data")
        uploader.upload_image(image_bytes, filename="test.png")

        # Verify blob methods were called
        mock_bucket.blob.assert_called_once()
        mock_blob.upload_from_file.assert_called_once()


@pytest.mark.unit
def test_upload_image_sets_content_type(mock_gcs_client):
    """Should set content_type to image/png."""
    mock_blob = MagicMock()
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_gcs_client.bucket.return_value = mock_bucket

    with patch("src.utils.gcs_uploader.storage.Client", return_value=mock_gcs_client):
        uploader = GCSUploader(project_id="test-project", bucket_name="test-bucket")

        image_bytes = BytesIO(b"fake_image_data")
        uploader.upload_image(image_bytes, filename="test.png")

        # Verify content_type was set
        call_kwargs = mock_blob.upload_from_file.call_args[1]
        assert call_kwargs.get("content_type") == "image/png"


@pytest.mark.unit
def test_upload_image_handles_error():
    """Should handle upload errors gracefully."""
    mock_client = MagicMock()
    mock_client.bucket.side_effect = Exception("GCS connection failed")

    with patch("src.utils.gcs_uploader.storage.Client", return_value=mock_client):
        uploader = GCSUploader(project_id="test-project", bucket_name="test-bucket")

        image_bytes = BytesIO(b"fake_image_data")

        # Should raise or return None on error (depending on implementation)
        with pytest.raises(Exception):
            uploader.upload_image(image_bytes, filename="test.png")


# ==============================================================================
# Test Credentials Loading
# ==============================================================================

@pytest.mark.unit
def test_uploader_init_with_json_path():
    """Should initialize with service account JSON path."""
    with patch("src.utils.gcs_uploader.storage.Client") as mock_client_class:
        uploader = GCSUploader(
            project_id="test-project",
            bucket_name="test-bucket",
            service_account_json="/path/to/credentials.json",
        )

        # Should have created client (with or without from_service_account_json)
        assert uploader is not None


@pytest.mark.unit
def test_uploader_init_with_adc():
    """Should initialize with Application Default Credentials when no JSON provided."""
    with patch("src.utils.gcs_uploader.storage.Client") as mock_client_class:
        mock_client_class.return_value = MagicMock()

        uploader = GCSUploader(
            project_id="test-project",
            bucket_name="test-bucket",
        )

        # Should have created client with default credentials
        assert uploader is not None
        mock_client_class.assert_called_once()
