from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from .db import get_db
from .models import Business, SessionToken, User


def get_current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
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
