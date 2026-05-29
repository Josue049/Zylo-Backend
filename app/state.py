from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any
from uuid import uuid4

from .security import create_reset_token, create_session_token, hash_password, verify_password


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


@dataclass
class AppState:
    lock: Lock = field(default_factory=Lock)
    users: dict[str, dict[str, Any]] = field(default_factory=dict)
    sessions: dict[str, dict[str, Any]] = field(default_factory=dict)
    businesses: dict[str, dict[str, Any]] = field(default_factory=dict)
    services: dict[str, dict[str, Any]] = field(default_factory=dict)
    bookings: dict[str, dict[str, Any]] = field(default_factory=dict)
    availability_blocks: dict[str, dict[str, Any]] = field(default_factory=dict)
    favorites: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    conversations: dict[str, dict[str, Any]] = field(default_factory=dict)
    messages: dict[str, dict[str, Any]] = field(default_factory=dict)
    notifications: dict[str, dict[str, Any]] = field(default_factory=dict)
    password_reset_tokens: dict[str, dict[str, Any]] = field(default_factory=dict)
    categories: list[dict[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._seed()

    def _seed(self) -> None:
        self.categories = [
            {"id": "salon", "name": "Salón"},
            {"id": "spa", "name": "Spa"},
            {"id": "barber", "name": "Barbería"},
            {"id": "fitness", "name": "Fitness"},
        ]

        business_owner = self.create_user(
            {
                "name": "Demo Business",
                "email": "business@zylo.test",
                "password": "Demo1234!",
                "phone": "+1 555 0100",
                "location": "Centro",
                "role": "business_owner",
            }
        )
        client = self.create_user(
            {
                "name": "Demo Client",
                "email": "client@zylo.test",
                "password": "Demo1234!",
                "phone": "+1 555 0110",
                "location": "Norte",
                "role": "client",
            }
        )

        business = self.create_business(
            owner_user_id=business_owner["id"],
            payload={
                "name": "Zylo Studio",
                "category_id": "salon",
                "description": "Servicios premium con reserva online.",
                "phone": "+1 555 0100",
                "address": "Av. Principal 123",
                "city": "Ciudad Central",
                "featured": True,
                "availability_status": True,
                "team": [
                    {"id": make_id("member"), "name": "Ana", "role": "Estilista"},
                    {"id": make_id("member"), "name": "Luis", "role": "Barbero"},
                ],
                "gallery": [
                    {"id": make_id("img"), "url": "https://images.unsplash.com/photo-1519014816548-bf5fe059798b?auto=format&fit=crop&w=1200&q=80", "alt": "Interior"},
                    {"id": make_id("img"), "url": "https://images.unsplash.com/photo-1521590832167-7bcbfaa6381f?auto=format&fit=crop&w=1200&q=80", "alt": "Equipo"},
                ],
            },
        )

        self.add_service(
            business["id"],
            {
                "name": "Corte de cabello",
                "description": "Corte profesional y lavado.",
                "duration_minutes": 45,
                "price": 18.0,
                "active": True,
            },
        )
        self.add_service(
            business["id"],
            {
                "name": "Barba",
                "description": "Perfilado y acabado.",
                "duration_minutes": 30,
                "price": 12.0,
                "active": True,
            },
        )

        self.favorites[client["id"]].add(business["id"])

    def create_user(self, payload: dict[str, Any]) -> dict[str, Any]:
        email = payload["email"].strip().lower()
        if any(user["email"] == email for user in self.users.values()):
            raise ValueError("email already registered")

        user_id = make_id("user")
        user = {
            "id": user_id,
            "name": payload["name"],
            "email": email,
            "password_hash": hash_password(payload["password"]),
            "phone": payload.get("phone"),
            "location": payload.get("location"),
            "photo_url": payload.get("photo_url"),
            "bio": payload.get("bio"),
            "role": payload.get("role", "client"),
            "business_id": payload.get("business_id"),
            "created_at": utcnow(),
            "updated_at": utcnow(),
        }
        self.users[user_id] = user
        return user

    def create_business(self, owner_user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        business_id = make_id("biz")
        business = {
            "id": business_id,
            "owner_user_id": owner_user_id,
            "name": payload["name"],
            "category_id": payload.get("category_id", "salon"),
            "description": payload.get("description"),
            "phone": payload.get("phone"),
            "email": payload.get("email"),
            "address": payload.get("address"),
            "city": payload.get("city"),
            "featured": payload.get("featured", False),
            "availability_status": payload.get("availability_status", True),
            "rating": payload.get("rating", 4.8),
            "reviews_count": payload.get("reviews_count", 120),
            "image_url": payload.get("image_url", "https://images.unsplash.com/photo-1522337660859-02fbefca4702?auto=format&fit=crop&w=1200&q=80"),
            "team": payload.get("team", []),
            "gallery": payload.get("gallery", []),
            "weekly_hours": payload.get(
                "weekly_hours",
                {
                    "monday": ["09:00", "18:00"],
                    "tuesday": ["09:00", "18:00"],
                    "wednesday": ["09:00", "18:00"],
                    "thursday": ["09:00", "18:00"],
                    "friday": ["09:00", "18:00"],
                    "saturday": ["10:00", "15:00"],
                    "sunday": [],
                },
            ),
            "created_at": utcnow(),
            "updated_at": utcnow(),
        }
        self.businesses[business_id] = business
        self.users[owner_user_id]["business_id"] = business_id
        return business

    def add_service(self, business_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        service_id = make_id("srv")
        service = {
            "id": service_id,
            "business_id": business_id,
            "name": payload["name"],
            "description": payload.get("description"),
            "duration_minutes": payload.get("duration_minutes", 30),
            "price": payload.get("price", 0.0),
            "active": payload.get("active", True),
            "created_at": utcnow(),
            "updated_at": utcnow(),
        }
        self.services[service_id] = service
        return service

    def authenticate(self, email: str, password: str) -> dict[str, Any] | None:
        normalized = email.strip().lower()
        user = next((item for item in self.users.values() if item["email"] == normalized), None)
        if not user or not verify_password(password, user["password_hash"]):
            return None
        return user

    def create_session(self, user_id: str) -> str:
        token = create_session_token()
        self.sessions[token] = {"user_id": user_id, "created_at": utcnow(), "last_seen_at": utcnow()}
        return token

    def get_user_by_session(self, token: str) -> dict[str, Any] | None:
        session = self.sessions.get(token)
        if not session:
            return None
        user = self.users.get(session["user_id"])
        if user:
            session["last_seen_at"] = utcnow()
        return user

    def create_password_reset_token(self, email: str) -> tuple[str, dict[str, Any] | None]:
        user = next((item for item in self.users.values() if item["email"] == email.strip().lower()), None)
        if not user:
            return create_reset_token(), None
        token = create_reset_token()
        self.password_reset_tokens[token] = {"user_id": user["id"], "created_at": utcnow(), "expires_at": utcnow() + timedelta(hours=1)}
        return token, user

    def reset_password(self, token: str, new_password: str) -> bool:
        entry = self.password_reset_tokens.get(token)
        if not entry or entry["expires_at"] < utcnow():
            return False
        user = self.users.get(entry["user_id"])
        if not user:
            return False
        user["password_hash"] = hash_password(new_password)
        user["updated_at"] = utcnow()
        del self.password_reset_tokens[token]
        return True

    def business_for_user(self, user_id: str) -> dict[str, Any] | None:
        user = self.users.get(user_id)
        business_id = user.get("business_id") if user else None
        return self.businesses.get(business_id) if business_id else None


state = AppState()
