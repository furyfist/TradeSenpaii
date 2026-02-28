import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from dotenv import load_dotenv
load_dotenv()

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
bearer_scheme = HTTPBearer()


def verify_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> dict:
    """
    Verifies Supabase JWT token from Authorization: Bearer <token> header.
    Returns the decoded token payload if valid.
    Raises 401 if invalid or expired.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms   = ["HS256"],
            options      = {"verify_aud": False},
        )
        return payload
    except JWTError as e:
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