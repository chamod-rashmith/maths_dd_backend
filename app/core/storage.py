"""
Google Cloud Storage (Firebase Storage) client helper for Google Cloud Run.
Supports both Service Account JSON keys and Cloud Run IAM signBlob (Compute Engine ADC).
"""

import datetime
import logging
import os
from typing import Optional
import google.auth
from google.auth.transport import requests as google_auth_requests
from google.cloud import storage

from app.core.config import settings

logger = logging.getLogger("maths_dd.storage")

_storage_client: Optional[storage.Client] = None


def get_storage_client() -> Optional[storage.Client]:
    """
    Returns Google Cloud Storage client authenticated via Cloud Run ADC or Service Account JSON.
    """
    global _storage_client
    if _storage_client is not None:
        return _storage_client

    try:
        cred_path = settings.GOOGLE_APPLICATION_CREDENTIALS
        if cred_path and os.path.exists(cred_path):
            _storage_client = storage.Client.from_service_account_json(cred_path)
        else:
            _storage_client = storage.Client(project=settings.FIREBASE_PROJECT_ID)
        return _storage_client
    except Exception as exc:
        logger.warning(
            "GCS Storage client initialization failed: %s",
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
    Generates a secure, short-lived v4 signed URL for downloading/viewing a file on Cloud Run.
    Automatically uses IAM signBlob (service_account_email + access_token) when running on
    Cloud Run with Compute Engine Application Default Credentials.
    """
    if not storage_path or not storage_path.strip():
        return ""

    cleaned_path = storage_path.strip()

    # If it's already a full HTTP/HTTPS URL, return as-is
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

            creds = client._credentials
            sign_kwargs = {
                "version": "v4",
                "expiration": datetime.timedelta(minutes=expiration_minutes),
                "method": "GET",
            }

            # On Cloud Run, Compute Engine credentials do not hold a local private key;
            # pass service_account_email and access_token to sign via IAM Credentials API.
            if not hasattr(creds, "sign_bytes"):
                auth_req = google_auth_requests.Request()
                if not creds.valid or not creds.token:
                    creds.refresh(auth_req)
                sa_email = getattr(creds, "service_account_email", None)
                if sa_email and creds.token:
                    sign_kwargs["service_account_email"] = sa_email
                    sign_kwargs["access_token"] = creds.token

            return blob.generate_signed_url(**sign_kwargs)
        except Exception as exc:
            logger.warning(
                "Failed to generate GCS signed URL for '%s': %s", cleaned_path, exc
            )

    bucket_name = settings.STORAGE_BUCKET_NAME.replace("gs://", "").strip()
    return f"https://storage.googleapis.com/{bucket_name}/{cleaned_path}?X-Goog-Expires={expiration_minutes * 60}&signed=true"


def generate_signed_upload_url(
    storage_path: str, content_type: str = "image/jpeg", expiration_minutes: int = 15
) -> str:
    """
    Generates a secure, short-lived v4 signed URL allowing client to PUT an upload directly into GCS.
    Bypasses backend server memory & bandwidth overhead.
    """
    if not storage_path or not storage_path.strip():
        return ""

    cleaned_path = storage_path.strip().lstrip("/")
    if cleaned_path.startswith("gs://"):
        parts = cleaned_path.replace("gs://", "").split("/", 1)
        cleaned_path = parts[1] if len(parts) > 1 else parts[0]

    client = get_storage_client()
    if client:
        try:
            bucket_name = settings.STORAGE_BUCKET_NAME.replace("gs://", "").strip()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(cleaned_path)

            creds = client._credentials
            sign_kwargs = {
                "version": "v4",
                "expiration": datetime.timedelta(minutes=expiration_minutes),
                "method": "PUT",
                "content_type": content_type,
            }

            if not hasattr(creds, "sign_bytes"):
                auth_req = google_auth_requests.Request()
                if not creds.valid or not creds.token:
                    creds.refresh(auth_req)
                sa_email = getattr(creds, "service_account_email", None)
                if sa_email and creds.token:
                    sign_kwargs["service_account_email"] = sa_email
                    sign_kwargs["access_token"] = creds.token

            return blob.generate_signed_url(**sign_kwargs)
        except Exception as exc:
            logger.warning(
                "Failed to generate GCS signed upload URL for '%s': %s", cleaned_path, exc
            )

    bucket_name = settings.STORAGE_BUCKET_NAME.replace("gs://", "").strip()
    return f"https://storage.googleapis.com/{bucket_name}/{cleaned_path}?X-Goog-Expires={expiration_minutes * 60}&signed=true&method=PUT"
