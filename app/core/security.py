"""
Firebase Authentication & JWT Security verification for FastAPI backend on Google Cloud Run.
"""

import logging
import os
from typing import Any, Dict, Optional

import firebase_admin
from firebase_admin import auth, credentials
from firebase_admin.exceptions import FirebaseError
from fastapi import Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.concurrency import run_in_threadpool

from app.core.config import settings

logger = logging.getLogger("maths_dd.security")

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="FirebaseBearerAuth",
    description=(
        "Firebase ID Token (`Bearer <token>`). "
        # ⚠️ TODO(PRODUCTION-CLEANUP): Remove dev shortcut token description before production release.
        "In local development (`ENVIRONMENT=development`), shortcut tokens "
        "`dev-student`, `dev-admin`, `dev-editor`, and `dev-auditor` are also supported."
    ),
)

# ==============================================================================
# 🚨 TODO(PRODUCTION-CLEANUP) / REMOVE BEFORE PRODUCTION 🚨
# පහත `_DEV_SHORTCUT_TOKENS` යොදා ඇත්තේ Development අවධියේදී (Swagger UI / Postman)
# පහසුවෙන් API පරීක්ෂා කිරීම සඳහා පමණි.
# Production යැවීමට පෙර මෙම `_DEV_SHORTCUT_TOKENS` dictionary එක සහ `get_current_user`
# තුළ ඇති `is_dev_mode` bypass කොටස සම්පූර්ණයෙන්ම ඉවත් කරන්න!
# ==============================================================================
_DEV_SHORTCUT_TOKENS: Dict[str, Dict[str, Any]] = {
    "dev-admin": {
        "uid": "admin_master_001",
        "email": "admin@mathsdd.lk",
        "name": "Super Admin",
        "role": "ADMIN",
    },
    "admin": {
        "uid": "admin_master_001",
        "email": "admin@mathsdd.lk",
        "name": "Super Admin",
        "role": "ADMIN",
    },
    "dev-student": {
        "uid": "dev_student_001",
        "email": "student@mathsdd.lk",
        "name": "Dev Student",
        "role": "USER",
    },
    "dev-user": {
        "uid": "dev_student_001",
        "email": "student@mathsdd.lk",
        "name": "Dev Student",
        "role": "USER",
    },
    "student": {
        "uid": "dev_student_001",
        "email": "student@mathsdd.lk",
        "name": "Dev Student",
        "role": "USER",
    },
    "dev-editor": {
        "uid": "dev_editor_001",
        "email": "editor@mathsdd.lk",
        "name": "Dev Editor",
        "role": "EDITOR",
    },
    "editor": {
        "uid": "dev_editor_001",
        "email": "editor@mathsdd.lk",
        "name": "Dev Editor",
        "role": "EDITOR",
    },
    "dev-auditor": {
        "uid": "dev_auditor_001",
        "email": "audit@mathsdd.lk",
        "name": "Dev Auditor",
        "role": "ACCOUNT_AUDIT",
    },
    "auditor": {
        "uid": "dev_auditor_001",
        "email": "audit@mathsdd.lk",
        "name": "Dev Auditor",
        "role": "ACCOUNT_AUDIT",
    },
}


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
    ),
    bearer_creds: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> Dict[str, Any]:
    """Verifies a Firebase ID token from the Authorization header or Swagger Authorize dialog."""
    if not authorization and isinstance(bearer_creds, HTTPAuthorizationCredentials):
        authorization = f"{bearer_creds.scheme} {bearer_creds.credentials}"

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

    # 🚨 TODO(PRODUCTION-CLEANUP): Remove this dev-mode token bypass block before production deployment!
    # Production යැවීමට පෙර මෙම `is_dev_mode` සහ `_DEV_SHORTCUT_TOKENS` කොටස ඉවත් කරන්න.
    is_dev_mode = (
        settings.ENVIRONMENT.lower() in ("development", "dev", "local", "test")
        or settings.ALLOW_DEV_AUTH_BYPASS
    )
    if is_dev_mode and id_token in _DEV_SHORTCUT_TOKENS:
        return dict(_DEV_SHORTCUT_TOKENS[id_token])

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
