from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Booking, Business, Favorite, Notification, PasswordResetToken, Service, SessionToken, User
from .security import hash_password
from .utils import make_id


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def seed_demo_data(db: Session) -> None:
    if db.scalar(select(func.count()).select_from(User)):
        return

    business_owner = User(
        id=make_id("user"),
        name="Demo Business",
        email="business@zylo.test",
        password_hash=hash_password("Demo1234!"),
        phone="+1 555 0100",
        location="Centro",
        role="business_owner",
    )
    client = User(
        id=make_id("user"),
        name="Demo Client",
        email="client@zylo.test",
        password_hash=hash_password("Demo1234!"),
        phone="+1 555 0110",
        location="Norte",
        role="client",
    )
    db.add_all([business_owner, client])
    db.flush()

    business = Business(
        id=make_id("biz"),
        owner_user_id=business_owner.id,
        name="Zylo Studio",
        category_id="salon",
        description="Servicios premium con reserva online.",
        phone="+1 555 0100",
        email="business@zylo.test",
        address="Av. Principal 123",
        city="Ciudad Central",
        featured=True,
        availability_status=True,
        rating=4.8,
        reviews_count=120,
        image_url="https://images.unsplash.com/photo-1522337660859-02fbefca4702?auto=format&fit=crop&w=1200&q=80",
        team=[{"id": make_id("member"), "name": "Ana", "role": "Estilista"}, {"id": make_id("member"), "name": "Luis", "role": "Barbero"}],
        gallery=[
            {"id": make_id("img"), "url": "https://images.unsplash.com/photo-1519014816548-bf5fe059798b?auto=format&fit=crop&w=1200&q=80", "alt": "Interior"},
            {"id": make_id("img"), "url": "https://images.unsplash.com/photo-1521590832167-7bcbfaa6381f?auto=format&fit=crop&w=1200&q=80", "alt": "Equipo"},
        ],
        weekly_hours={
            "monday": ["09:00", "18:00"],
            "tuesday": ["09:00", "18:00"],
            "wednesday": ["09:00", "18:00"],
            "thursday": ["09:00", "18:00"],
            "friday": ["09:00", "18:00"],
            "saturday": ["10:00", "15:00"],
            "sunday": [],
        },
    )
    db.add(business)
    db.flush()

    business_owner.business_id = business.id

    db.add_all(
        [
            Service(
                id=make_id("srv"),
                business_id=business.id,
                name="Corte de cabello",
                description="Corte profesional y lavado.",
                duration_minutes=45,
                price=18.0,
                active=True,
                weekly_hours={
                    "monday": ["09:00", "13:00"],
                    "tuesday": ["09:00", "13:00"],
                    "wednesday": ["09:00", "13:00"],
                    "thursday": ["09:00", "13:00"],
                    "friday": ["09:00", "13:00"],
                    "saturday": ["10:00", "14:00"],
                    "sunday": [],
                },
                professionals=[
                    {"id": "ana", "name": "Ana", "role": "Estilista"},
                    {"id": "luis", "name": "Luis", "role": "Barbero"},
                ],
            ),
            Service(
                id=make_id("srv"),
                business_id=business.id,
                name="Barba",
                description="Perfilado y acabado.",
                duration_minutes=30,
                price=12.0,
                active=True,
                weekly_hours={
                    "monday": ["13:00", "18:00"],
                    "tuesday": ["13:00", "18:00"],
                    "wednesday": ["13:00", "18:00"],
                    "thursday": ["13:00", "18:00"],
                    "friday": ["13:00", "18:00"],
                    "saturday": ["10:00", "15:00"],
                    "sunday": [],
                },
                professionals=[
                    {"id": "luis", "name": "Luis", "role": "Barbero"},
                ],
            ),
            Favorite(user_id=client.id, business_id=business.id),
            SessionToken(token="demo-internal-token", user_id=client.id, last_seen_at=utcnow()),
            PasswordResetToken(token="demo-reset-token", user_id=client.id, expires_at=utcnow() + timedelta(hours=1)),
        ]
    )
    db.commit()
