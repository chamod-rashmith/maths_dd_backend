"""
Firebase Authentication & JWT Security verification for FastAPI backend on Google Cloud Run.
"""

import logging
import os
from typing import Any, Dict, Optional
import firebase_admin
from firebase_admin import auth, credentials
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
        None, description="Bearer <Firebase_ID_Token>"
    )
) -> Dict[str, Any]:
    """
    FastAPI dependency to verify Firebase ID Token from Authorization header.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required (Bearer <Firebase_ID_Token>)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected: Bearer <Firebase_ID_Token>",
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
            detail="Firebase ID token has expired. Please refresh the token on client-side.",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )
    except auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase ID token has been revoked.",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )
    except auth.InvalidIdTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Firebase ID token: {str(exc)}",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )
    except Exception as exc:
        logger.error("Error validating token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_current_user(
    authorization: Optional[str] = Header(
        None, description="Optional Bearer <Firebase_ID_Token>"
    )
) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency that returns decoded user token if Authorization header is provided,
    or None if absent.
    """
    if not authorization:
        return None
    try:
        return await get_current_user(authorization=authorization)
    except HTTPException:
        return None
