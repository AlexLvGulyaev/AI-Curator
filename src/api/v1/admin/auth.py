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

    @property
    def is_demo(self) -> bool:
        return self.user_role == "demo"


def _identity_from_token(token: str) -> AdminIdentity:
    """Return the identity matching a configured admin or demo token."""
    if token == settings.admin_console_token:
        return AdminIdentity(user_id="admin", user_name="admin", user_role="admin")
    if settings.admin_console_demo_token and token == settings.admin_console_demo_token:
        return AdminIdentity(user_id="demo", user_name="demo", user_role="demo")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid admin token",
    )


async def admin_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> AdminIdentity:
    """Require a valid admin or demo bearer token if ADMIN_CONSOLE_TOKEN is configured.

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

    return _identity_from_token(credentials.credentials)


def require_admin(admin: AdminIdentity = Depends(admin_auth)) -> AdminIdentity:
    """Require a full admin role; reject demo sessions for mutating endpoints."""
    if admin.is_demo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo access is read-only",
        )
    return admin
