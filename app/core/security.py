"""
Firebase Authentication & JWT Security verification for FastAPI backend.
Uses `starlette.concurrency.run_in_threadpool` to prevent blocking the asyncio event loop.
"""

import os
import logging
from typing import Dict, Any, Optional
import firebase_admin
from firebase_admin import auth, credentials
from fastapi import Header, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.core.config import settings

logger = logging.getLogger("maths_dd.security")


def init_firebase() -> None:
    """Initializes the Firebase Admin SDK idempotently."""
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
                "Firebase Admin SDK initialized with default project credentials."
            )


init_firebase()


async def get_current_user(
    authorization: Optional[str] = Header(
        None, description="Bearer <Firebase_ID_Token>"
    )
) -> Dict[str, Any]:
    """
    FastAPI dependency to verify Firebase ID Token from Authorization header.
    Offloads synchronous `auth.verify_id_token` to a worker threadpool so the
    main asyncio event loop never blocks during network JWKS/certificate checks.
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
