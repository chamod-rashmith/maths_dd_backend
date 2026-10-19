"""
Google Cloud Storage (Firebase Storage) client helper.
"""

import os
from google.cloud import storage

BUCKET_NAME = os.environ.get(
    "STORAGE_BUCKET_NAME",
    "math-master-981fe.firebasestorage.app",
)


def get_storage_client() -> storage.Client:
    """Returns Google Cloud Storage client authenticated via Application Default Credentials (ADC)."""
    return storage.Client()


def get_storage_bucket() -> storage.Bucket:
    """Returns the configured Firebase Storage bucket instance."""
    client = get_storage_client()
    # Support both full URL and bucket ID
    bucket_name = BUCKET_NAME.replace("gs://", "").strip()
    return client.bucket(bucket_name)
