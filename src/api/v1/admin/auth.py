"""Admin console authentication dependency."""

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from config import settings

bearer_scheme = HTTPBearer(auto_error=False)


class AdminIdentity(BaseModel):
    """Identity of an authenticated admin console user."""

    user_id: str
    user_name: str
    user_role: str = "admin"


async def admin_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> AdminIdentity:
    """Require a valid admin bearer token if ADMIN_CONSOLE_TOKEN is configured.

    Returns an AdminIdentity for downstream audit logging. When auth is disabled
    (e.g. in tests), a fallback identity is returned so audit records still have
    a stable actor.
    """
    if not settings.admin_auth_enabled:
        return AdminIdentity(user_id="admin", user_name="admin")

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

    # TODO: extract real identity from a signed token or admin user store once
    # multi-user RBAC is introduced. For now the single token maps to the admin
    # account.
    return AdminIdentity(user_id="admin", user_name="admin")
