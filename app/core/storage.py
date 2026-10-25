"""
Google Cloud Storage (Firebase Storage) client helper.
"""

from google.cloud import storage

from app.core.config import settings


def get_storage_client() -> storage.Client:
    """Returns Google Cloud Storage client authenticated via Application Default Credentials (ADC)."""
    return storage.Client()


def get_storage_bucket() -> storage.Bucket:
    """Returns the configured Firebase Storage bucket instance."""
    client = get_storage_client()
    bucket_name = settings.STORAGE_BUCKET_NAME.replace("gs://", "").strip()
    return client.bucket(bucket_name)
