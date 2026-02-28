import os
import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from dotenv import load_dotenv
load_dotenv()

SUPABASE_URL        = os.getenv("SUPABASE_URL")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
bearer_scheme       = HTTPBearer()


def _get_jwks():
    """Fetch Supabase public keys for ES256 verification."""
    url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    res = requests.get(url, timeout=5)
    res.raise_for_status()
    return res.json()


def verify_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> dict:
    """
    Verifies Supabase JWT token from Authorization: Bearer <token> header.
    Tries ES256 via JWKS first (Supabase default), falls back to HS256 secret.
    Returns the decoded token payload if valid.
    Raises 401 if invalid or expired.
    """
    token = credentials.credentials
    try:
        # Primary: ES256 with JWKS (Supabase current default)
        jwks = _get_jwks()
        payload = jwt.decode(
            token,
            jwks,
            algorithms   = ["ES256", "HS256"],
            options      = {"verify_aud": False},
        )
        return payload
    except JWTError:
        try:
            # Fallback: HS256 with JWT secret (older Supabase projects)
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms   = ["HS256"],
                options      = {"verify_aud": False},
            )
            return payload
        except JWTError:
            raise HTTPException(
                status_code = status.HTTP_401_UNAUTHORIZED,
                detail      = "Invalid or expired token.",
                headers     = {"WWW-Authenticate": "Bearer"},
            )


def require_admin(payload: dict = Depends(verify_jwt)) -> dict:
    """
    Extends verify_jwt — additionally checks the user has admin role.
    Role is stored in Supabase user_metadata.
    """
    role = payload.get("user_metadata", {}).get("role")
    if role != "admin":
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "Admin access required.",
        )
    return payload