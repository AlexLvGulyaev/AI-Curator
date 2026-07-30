"""Admin console authentication dependency."""

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import settings

bearer_scheme = HTTPBearer(auto_error=False)


async def admin_auth(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> None:
    """Require a valid admin bearer token if ADMIN_CONSOLE_TOKEN is configured."""
    if not settings.admin_auth_enabled:
        return

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.credentials != settings.admin_console_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin token",
        )
