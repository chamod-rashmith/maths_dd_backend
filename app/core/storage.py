"""
Google Cloud Storage (Firebase Storage) client helper.
Handles client authentication and short-lived v4 signed URL generation.
"""

import datetime
import logging
from typing import Optional
from google.cloud import storage

from app.core.config import settings

logger = logging.getLogger("maths_dd.storage")

_storage_client: Optional[storage.Client] = None


def get_storage_client() -> Optional[storage.Client]:
    """
    Returns Google Cloud Storage client authenticated via ADC or Service Account.
    Returns None gracefully if credentials are not configured in local environment.
    """
    global _storage_client
    if _storage_client is not None:
        return _storage_client

    try:
        if settings.GOOGLE_APPLICATION_CREDENTIALS:
            _storage_client = storage.Client.from_service_account_json(
                settings.GOOGLE_APPLICATION_CREDENTIALS
            )
        else:
            _storage_client = storage.Client()
        return _storage_client
    except Exception as exc:
        logger.warning(
            "GCS Storage client initialization failed (running offline/dev fallback): %s",
            exc,
        )
        return None


def get_storage_bucket() -> Optional[storage.Bucket]:
    """Returns the configured Firebase Storage bucket instance if client is available."""
    client = get_storage_client()
    if not client:
        return None
    bucket_name = settings.STORAGE_BUCKET_NAME.replace("gs://", "").strip()
    return client.bucket(bucket_name)


def generate_signed_download_url(
    storage_path: str, expiration_minutes: int = 60
) -> str:
    """
    Generates a secure, short-lived v4 signed URL for downloading/viewing a file.
    
    If storage_path is already a full external URL (e.g. mock or public CDN), returns as-is.
    If running locally without GCS credentials, generates a deterministic development signed link.
    """
    if not storage_path or not storage_path.strip():
        return ""

    cleaned_path = storage_path.strip()

    # If it's already a full HTTP/HTTPS URL, don't attempt to re-sign
    if cleaned_path.startswith("http://") or cleaned_path.startswith("https://"):
        return cleaned_path

    # Remove leading slashes or 'gs://<bucket>/' if present
    if cleaned_path.startswith("gs://"):
        parts = cleaned_path.replace("gs://", "").split("/", 1)
        cleaned_path = parts[1] if len(parts) > 1 else parts[0]
    cleaned_path = cleaned_path.lstrip("/")

    client = get_storage_client()
    if client:
        try:
            bucket_name = settings.STORAGE_BUCKET_NAME.replace("gs://", "").strip()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(cleaned_path)
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=datetime.timedelta(minutes=expiration_minutes),
                method="GET",
            )
            return signed_url
        except Exception as exc:
            logger.warning("Failed to generate GCS signed URL for '%s': %s", cleaned_path, exc)

    # Local development fallback when ADC is not configured
    bucket_name = settings.STORAGE_BUCKET_NAME.replace("gs://", "").strip()
    return f"https://storage.googleapis.com/{bucket_name}/{cleaned_path}?X-Goog-Expires={expiration_minutes * 60}&signed=true"
