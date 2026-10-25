"""
Firebase Authentication & JWT Security verification for FastAPI backend.
"""

import os
import logging
from typing import Dict, Any, Optional
import firebase_admin
from firebase_admin import auth, credentials
from fastapi import Header, HTTPException, status, Depends

logger = logging.getLogger("maths_dd.auth")

# Initialize Firebase Admin SDK idempotently
if not firebase_admin._apps:
    cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if cred_path and os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized with Service Account credentials.")
    else:
        # Default initialization (uses Google Application Default Credentials or Project ID)
        project_id = os.environ.get("FIREBASE_PROJECT_ID", "math-master-981fe")
        firebase_admin.initialize_app(options={"projectId": project_id})
        logger.info("Firebase Admin SDK initialized with default credentials.")


async def get_current_user(
    authorization: Optional[str] = Header(None, description="Bearer <Firebase_ID_Token>")
) -> Dict[str, Any]:
    """
    FastAPI dependency to verify Firebase ID Token from Authorization header.
    Returns decoded token dictionary with user info (uid, email, name, etc.).
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
        # Verify the ID token using Firebase Admin SDK
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase ID token has expired. Please refresh the token on client-side.",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        )
    except auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase ID token has been revoked.",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        )
    except auth.InvalidIdTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Firebase ID token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        )
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
