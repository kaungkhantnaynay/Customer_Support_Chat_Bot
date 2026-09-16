import hashlib
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.core.config import settings

basic = HTTPBasic(auto_error=False)


def require_admin(
    credentials: Annotated[HTTPBasicCredentials | None, Depends(basic)],
) -> None:
    if not settings.admin_password:
        raise HTTPException(status_code=503, detail="Admin access is not configured.")
    if credentials is None or not (
        secrets.compare_digest(credentials.username.encode(), settings.admin_username.encode())
        and secrets.compare_digest(credentials.password.encode(), settings.admin_password.encode())
    ):
        raise HTTPException(
            status_code=401,
            detail="Admin authentication required.",
            headers={"WWW-Authenticate": "Basic"},
        )


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
