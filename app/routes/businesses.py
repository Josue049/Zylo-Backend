from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_business
from ..models import AvailabilityBlock, Booking, Business, Service
from ..schemas import AvailabilityBlockCreateRequest, ServiceCreateRequest
from ..serializers import business_payload, service_payload
from ..utils import make_id

router = APIRouter(prefix="/businesses", tags=["businesses"])

CATEGORIES = [
    {"id": "salon", "name": "Salón"},
    {"id": "spa", "name": "Spa"},
    {"id": "barber", "name": "Barbería"},
    {"id": "fitness", "name": "Fitness"},
]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def category_name(category_id: str | None) -> str | None:
    if not category_id:
        return None
    match = next((item for item in CATEGORIES if item["id"] == category_id), None)
    return match["name"] if match else category_id


def business_counts(db: Session, business_id: str) -> tuple[int, int]:
    services_count = db.scalar(select(func.count()).select_from(Service).where(Service.business_id == business_id)) or 0
    active_services_count = db.scalar(select(func.count()).select_from(Service).where(Service.business_id == business_id, Service.active.is_(True))) or 0
    return services_count, active_services_count


def serialize_business(db: Session, business: Business) -> dict:
    services_count, active_services_count = business_counts(db, business.id)
    return business_payload(
        business,
        services_count=services_count,
        active_services_count=active_services_count,
        category_name=category_name(business.category_id),
    )


def overlaps(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    return start_a < end_b and end_a > start_b


def business_is_available(db: Session, business_id: str, start_at: datetime, end_at: datetime, ignore_booking_id: str | None = None) -> bool:
    blocks = db.scalars(select(AvailabilityBlock).where(AvailabilityBlock.business_id == business_id)).all()
    for block in blocks:
        if overlaps(start_at, end_at, block.start_at, block.end_at):
            return False

    bookings = db.scalars(select(Booking).where(Booking.business_id == business_id)).all()
    for booking in bookings:
        if ignore_booking_id and booking.id == ignore_booking_id:
            continue
        if booking.status in {"canceled", "rejected"}:
            continue
        if overlaps(start_at, end_at, booking.start_at, booking.end_at):
            return False
    return True


def business_owned_by_current_user(current_business: Business) -> Business:
    return current_business


@router.get("")
def list_businesses(
    search: str | None = Query(default=None),
    category: str | None = Query(default=None),
    featured: bool | None = Query(default=None),
    available: bool | None = Query(default=None),
    db: Session = Depends(get_db),
):
    businesses = list(db.scalars(select(Business).order_by(Business.created_at.desc())))
    if search:
        term = search.lower()
        businesses = [business for business in businesses if term in business.name.lower() or term in (business.description or "").lower()]
    if category:
        businesses = [business for business in businesses if business.category_id == category]
    if featured is not None:
        businesses = [business for business in businesses if business.featured == featured]
    if available is not None:
        businesses = [business for business in businesses if business.availability_status == available]
    return {"items": [serialize_business(db, business) for business in businesses]}


@router.get("/categories")
def list_categories():
    return {"items": CATEGORIES}


@router.get("/featured")
def featured_businesses(db: Session = Depends(get_db)):
    businesses = list(db.scalars(select(Business).where(Business.featured.is_(True)).order_by(Business.created_at.desc())))
    return {"items": [serialize_business(db, business) for business in businesses]}


@router.get("/me/services")
def list_my_services(current_business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    items = list(db.scalars(select(Service).where(Service.business_id == current_business.id).order_by(Service.created_at.desc())))
    return {"items": [service_payload(service) for service in items]}


@router.post("/me/services")
def create_my_service(payload: ServiceCreateRequest, current_business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    service = Service(
        id=make_id("srv"),
        business_id=current_business.id,
        name=payload.name,
        description=payload.description,
        duration_minutes=payload.duration_minutes,
        price=payload.price,
        active=payload.active,
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    return {"service": service_payload(service)}


@router.get("/me/bookings")
def list_my_business_bookings(current_business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    items = list(db.scalars(select(Booking).where(Booking.business_id == current_business.id).order_by(Booking.start_at.desc())))
    return {
        "items": [
            {
                "id": booking.id,
                "user_id": booking.user_id,
                "business_id": booking.business_id,
                "service_id": booking.service_id,
                "start_at": booking.start_at,
                "end_at": booking.end_at,
                "notes": booking.notes,
                "status": booking.status,
                "price": booking.price,
                "created_at": booking.created_at,
                "updated_at": booking.updated_at,
            }
            for booking in items
        ]
    }


@router.get("/me/dashboard-summary")
def dashboard_summary(current_business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    bookings = list(db.scalars(select(Booking).where(Booking.business_id == current_business.id)))
    today = utcnow().date()
    todays_bookings = [booking for booking in bookings if booking.start_at.date() == today]
    summary = {
        "today_bookings": len(todays_bookings),
        "total_bookings": len(bookings),
        "pending": sum(1 for booking in bookings if booking.status == "pending"),
        "accepted": sum(1 for booking in bookings if booking.status == "accepted"),
        "rejected": sum(1 for booking in bookings if booking.status == "rejected"),
        "canceled": sum(1 for booking in bookings if booking.status == "canceled"),
        "revenue_estimate": sum(booking.price for booking in bookings if booking.status in {"accepted", "completed"}),
    }
    return {"summary": summary}


@router.get("/me/weekly-agenda")
def weekly_agenda(current_business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    start = utcnow().date()
    end = start + timedelta(days=7)
    agenda = defaultdict(list)
    for booking in db.scalars(select(Booking).where(Booking.business_id == current_business.id)):
        booking_date = booking.start_at.date()
        if start <= booking_date < end:
            agenda[str(booking_date)].append(booking.__dict__)
    return {"agenda": dict(agenda)}


@router.get("/me/stats")
def business_stats(current_business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    bookings = list(db.scalars(select(Booking).where(Booking.business_id == current_business.id)))
    by_service = defaultdict(int)
    by_status = defaultdict(int)
    for booking in bookings:
        by_service[booking.service_id] += 1
        by_status[booking.status] += 1
    return {"by_service": dict(by_service), "by_status": dict(by_status), "total": len(bookings)}


@router.get("/{business_id}/services")
def business_services(business_id: str, db: Session = Depends(get_db)):
    business = db.get(Business, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    items = list(db.scalars(select(Service).where(Service.business_id == business_id).order_by(Service.created_at.desc())))
    return {"items": [service_payload(service) for service in items]}


@router.get("/{business_id}/team")
def business_team(business_id: str, db: Session = Depends(get_db)):
    business = db.get(Business, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return {"items": business.team or []}


@router.get("/{business_id}/gallery")
def business_gallery(business_id: str, db: Session = Depends(get_db)):
    business = db.get(Business, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return {"items": business.gallery or []}


@router.get("/{business_id}/availability")
def business_availability(business_id: str, db: Session = Depends(get_db)):
    business = db.get(Business, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    blocks = list(db.scalars(select(AvailabilityBlock).where(AvailabilityBlock.business_id == business_id)))
    bookings = list(db.scalars(select(Booking).where(Booking.business_id == business_id, ~Booking.status.in_(["canceled", "rejected"]))))
    return {
        "business_id": business_id,
        "blocks": [
            {"id": block.id, "business_id": block.business_id, "start_at": block.start_at, "end_at": block.end_at, "reason": block.reason, "created_at": block.created_at}
            for block in blocks
        ],
        "bookings": [
            {"id": booking.id, "user_id": booking.user_id, "business_id": booking.business_id, "service_id": booking.service_id, "start_at": booking.start_at, "end_at": booking.end_at, "notes": booking.notes, "status": booking.status, "price": booking.price, "created_at": booking.created_at, "updated_at": booking.updated_at}
            for booking in bookings
        ],
        "weekly_hours": business.weekly_hours or {},
    }


@router.get("/{business_id}")
def business_detail(business_id: str, db: Session = Depends(get_db)):
    business = db.get(Business, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return {"business": serialize_business(db, business)}


@router.post("/{business_id}/availability-blocks")
def add_availability_block(business_id: str, payload: AvailabilityBlockCreateRequest, current_business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    if current_business.id != business_id:
        raise HTTPException(status_code=403, detail="You can only manage your own business")
    block = AvailabilityBlock(
        id=make_id("block"),
        business_id=business_id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        reason=payload.reason,
    )
    db.add(block)
    db.commit()
    db.refresh(block)
    return {"block": block.__dict__}


@router.delete("/{business_id}/availability-blocks/{block_id}")
def remove_availability_block(business_id: str, block_id: str, current_business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    if current_business.id != business_id:
        raise HTTPException(status_code=403, detail="You can only manage your own business")
    block = db.get(AvailabilityBlock, block_id)
    if not block or block.business_id != business_id:
        raise HTTPException(status_code=404, detail="Block not found")
    db.delete(block)
    db.commit()
    return {"message": "Bloque eliminado"}


def check_business_availability_for_booking(business_id: str, start_at: datetime, duration_minutes: int, db: Session, ignore_booking_id: str | None = None) -> tuple[bool, datetime]:
    end_at = start_at + timedelta(minutes=duration_minutes)
    return business_is_available(db, business_id, start_at, end_at, ignore_booking_id=ignore_booking_id), end_at
