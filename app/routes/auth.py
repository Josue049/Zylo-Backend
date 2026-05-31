from __future__ import annotations

from datetime import timedelta, timezone, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import _extract_session_token, get_current_user
from ..models import Business, PasswordResetToken, SessionToken, User
from ..schemas import ForgotPasswordRequest, GenericMessageOut, LoginRequest, RegisterRequest, ResetPasswordRequest
from ..security import create_reset_token, create_session_token, hash_password, verify_password
from ..serializers import user_payload
from ..utils import make_id

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if payload.account_type == "business" and not payload.business_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="business_name is required for business accounts")

    email = payload.email.strip().lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already registered")

    user = User(
        id=make_id("user"),
        name=payload.name,
        email=email,
        password_hash=hash_password(payload.password),
        phone=payload.phone,
        location=payload.location,
        role="business_owner" if payload.account_type == "business" else "client",
    )
    db.add(user)
    db.flush()

    if payload.account_type == "business":
        business = Business(
            id=make_id("biz"),
            owner_user_id=user.id,
            name=payload.business_name,
            category_id=payload.category_id or "salon",
            description=payload.description,
            featured=False,
            availability_status=True,
            weekly_hours={
                "monday": ["09:00", "18:00"],
                "tuesday": ["09:00", "18:00"],
                "wednesday": ["09:00", "18:00"],
                "thursday": ["09:00", "18:00"],
                "friday": ["09:00", "18:00"],
                "saturday": ["10:00", "15:00"],
                "sunday": [],
            },
            team=[],
            gallery=[],
        )
        db.add(business)
        db.flush()
        user.business_id = business.id

    token = create_session_token()
    db.add(SessionToken(token=token, user_id=user.id, last_seen_at=datetime.now(timezone.utc)))
    db.commit()
    db.refresh(user)
    return {"token": token, "user": user_payload(user, business_id=user.business_id)}


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = create_session_token()
    db.add(SessionToken(token=token, user_id=user.id, last_seen_at=datetime.now(timezone.utc)))
    db.commit()
    return {"token": token, "user": user_payload(user, business_id=user.business_id)}


@router.post("/logout", response_model=GenericMessageOut)
def logout(request: Request, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    del current_user
    token = _extract_session_token(request.headers)
    if token:
        session = db.get(SessionToken, token)
        if session:
            db.delete(session)
            db.commit()
    return {"message": "Sesión cerrada"}


@router.get("/me")
def me(current_user=Depends(get_current_user)):
    return {"user": user_payload(current_user, business_id=current_user.business_id)}


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    token = create_reset_token()
    if user:
        db.add(PasswordResetToken(token=token, user_id=user.id, expires_at=datetime.now(timezone.utc) + timedelta(hours=1)))
        db.commit()
    return {
        "message": "Si la cuenta existe, se envió un enlace de recuperación",
        "reset_token": token,
        "user_found": bool(user),
    }


@router.post("/reset-password", response_model=GenericMessageOut)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    reset_token = db.get(PasswordResetToken, payload.token)
    now = datetime.now(timezone.utc)
    if not reset_token or reset_token.expires_at < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    user = db.get(User, reset_token.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    user.password_hash = hash_password(payload.new_password)
    db.delete(reset_token)
    db.commit()
    return {"message": "Contraseña actualizada"}
