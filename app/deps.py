from __future__ import annotations

from collections.abc import Mapping

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from .db import get_db
from .models import Business, SessionToken, User


authorization_key = APIKeyHeader(name="Authorization", auto_error=False)


def _normalize_session_token(value: str | None) -> str | None:
    if not value:
        return None
    token = value.strip().strip('"').strip("'")
    lowered = token.lower()
    for prefix in ("bearer ", "token ", "jwt "):
        if lowered.startswith(prefix):
            token = token.split(" ", 1)[1].strip()
            break
    return token or None


def _extract_session_token(headers: Mapping[str, str]) -> str | None:
    return _normalize_session_token(
        headers.get("authorization")
        or headers.get("x-access-token")
        or headers.get("x-auth-token")
        or headers.get("token")
    )


def get_current_user(
    request: Request,
    authorization: str | None = Security(authorization_key),
    db: Session = Depends(get_db),
) -> User:
    token = _extract_session_token(request.headers)
    if not token and authorization:
        token = _normalize_session_token(authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    session = db.get(SessionToken, token)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    user = db.get(User, session.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    session.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    return user


def get_current_business(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Business:
    if user.role != "business_owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Business owner access required")
    business = db.scalar(select(Business).where(Business.owner_user_id == user.id))
    if not business:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Business profile not found")
    return business
