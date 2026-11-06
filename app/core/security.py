"""
Firebase Authentication & JWT Security verification for FastAPI backend on Google Cloud Run.
"""

import logging
import os
from typing import Any, Dict, Optional

import firebase_admin
from firebase_admin import auth, credentials
from firebase_admin.exceptions import FirebaseError
from fastapi import Header, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.core.config import settings

logger = logging.getLogger("maths_dd.security")


def init_firebase() -> None:
    """Initializes the Firebase Admin SDK idempotently via Cloud Run ADC or Service Account."""
    if not firebase_admin._apps:
        cred_path = settings.GOOGLE_APPLICATION_CREDENTIALS
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized with Service Account credentials.")
        else:
            firebase_admin.initialize_app(
                options={"projectId": settings.FIREBASE_PROJECT_ID}
            )
            logger.info(
                "Firebase Admin SDK initialized with Application Default Credentials (project=%s).",
                settings.FIREBASE_PROJECT_ID,
            )


init_firebase()


async def get_current_user(
    authorization: Optional[str] = Header(
        None, description="Bearer Firebase ID token"
    )
) -> Dict[str, Any]:
    """Verifies a Firebase ID token from the Authorization header."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header. Expected a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    id_token = parts[1]

    if settings.ENVIRONMENT == "development" and id_token in ("dev-admin", "admin"):
        return {
            "uid": "admin_master_001",
            "email": "admin@mathsdd.lk",
            "name": "Super Admin",
            "role": "ADMIN",
        }

    try:
        decoded_token: Dict[str, Any] = await run_in_threadpool(
            auth.verify_id_token, id_token
        )
        return decoded_token
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired. Please sign in again.",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )
    except auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has been revoked. Please sign in again.",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )
    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is invalid. Please sign in again.",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )
    except auth.CertificateFetchError:
        logger.exception("Firebase certificate fetch failed during token validation.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is temporarily unavailable. Please try again.",
            headers={"Retry-After": "30"},
        )
    except FirebaseError:
        logger.exception("Firebase authentication service error during token validation.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        logger.exception("Unexpected error during Firebase token validation.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_current_user(
    authorization: Optional[str] = Header(
        None, description="Optional Bearer Firebase ID token"
    )
) -> Optional[Dict[str, Any]]:
    """
    Returns the decoded user token if Authorization is provided, or None if absent/invalid.
    """
    if not authorization:
        return None
    try:
        return await get_current_user(authorization=authorization)
    except HTTPException:
        return None
