from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

if __package__ in {None, ""}:
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from app.bootstrap import seed_demo_data
    from app.db import SessionLocal, engine
    from app.models import Base
    from app.routes.auth import router as auth_router
    from app.routes.bookings import router as bookings_router
    from app.routes.businesses import router as businesses_router
    from app.routes.conversations import router as conversations_router
    from app.routes.notifications import router as notifications_router
    from app.routes.services import router as services_router
    from app.routes.users import router as users_router
else:
    from .bootstrap import seed_demo_data
    from .db import SessionLocal, engine
    from .models import Base
    from .routes.auth import router as auth_router
    from .routes.bookings import router as bookings_router
    from .routes.businesses import router as businesses_router
    from .routes.conversations import router as conversations_router
    from .routes.notifications import router as notifications_router
    from .routes.services import router as services_router
    from .routes.users import router as users_router


app = FastAPI(title="Zylo API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(businesses_router)
app.include_router(bookings_router)
app.include_router(services_router)
app.include_router(conversations_router)
app.include_router(notifications_router)


def ensure_service_schema() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    statements: list[str] = []

    if "services" in table_names:
        service_columns = {column["name"] for column in inspector.get_columns("services")}
        if "weekly_hours" not in service_columns:
            statements.append("ALTER TABLE services ADD COLUMN weekly_hours JSON")
        if "professionals" not in service_columns:
            statements.append("ALTER TABLE services ADD COLUMN professionals JSON")

    if "bookings" in table_names:
        booking_columns = {column["name"] for column in inspector.get_columns("bookings")}
        if "professional_id" not in booking_columns:
            statements.append("ALTER TABLE bookings ADD COLUMN professional_id VARCHAR(32)")

    if statements:
        with engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_service_schema()
    with SessionLocal() as db:
        seed_demo_data(db)


@app.get("/")
def healthcheck():
    return {"status": "ok", "service": "Zylo API", "docs": "/docs"}
