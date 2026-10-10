"""Bearer-token authentication for the tool endpoints."""

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import Settings, get_settings

# auto_error=False so we can return a uniform 401 with a WWW-Authenticate header.
bearer_scheme = HTTPBearer(auto_error=False, description="Static API key shared with Open WebUI")


def require_api_key(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> None:
    expected = settings.tool_api_key.get_secret_value().encode()
    supplied = (creds.credentials if creds else "").encode()
    # Constant-time comparison to avoid leaking the key via timing.
    if not creds or not secrets.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
