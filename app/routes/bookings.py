from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_business, get_current_user
from ..models import Booking, Business, Notification, Service, User
from ..schemas import BookingCreateRequest, BookingRescheduleRequest, BookingStatusRequest
from ..serializers import booking_payload
from ..utils import make_id
from .businesses import check_business_availability_for_booking, service_allows_slot

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("")
def create_booking(payload: BookingCreateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "client":
        raise HTTPException(status_code=403, detail="Only client users can create bookings")

    business = db.get(Business, payload.business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    service = db.get(Service, payload.service_id)
    if not service or service.business_id != payload.business_id:
        raise HTTPException(status_code=404, detail="Service not found")
    professionals = service.professionals or []
    if not professionals:
        raise HTTPException(status_code=400, detail="Service has no professionals configured")
    available_professionals = {item.get("id") for item in professionals if item.get("id")}
    if payload.professional_id not in available_professionals:
        raise HTTPException(status_code=400, detail="Invalid professional for this service")

    available, end_at = check_business_availability_for_booking(payload.business_id, payload.start_at, service.duration_minutes, db)
    if not available:
        raise HTTPException(status_code=409, detail="Business is not available in that time slot")
    if not service_allows_slot(service, business, payload.start_at, end_at):
        raise HTTPException(status_code=409, detail="Service is not available in that time slot")

    booking = Booking(
        id=make_id("book"),
        user_id=current_user.id,
        business_id=payload.business_id,
        service_id=payload.service_id,
        professional_id=payload.professional_id,
        start_at=payload.start_at,
        end_at=end_at,
        notes=payload.notes,
        status="pending",
        price=service.price,
    )
    db.add(booking)

    owner = db.get(User, business.owner_user_id)
    if owner:
        notification = Notification(
            id=make_id("note"),
            recipient_user_id=owner.id,
            type="booking_created",
            title="Nueva reserva",
            message=f"Tienes una nueva reserva para {service.name}",
            read=False,
        )
        db.add(notification)

    db.commit()
    db.refresh(booking)
    return {"booking": booking_payload(booking, db)}


@router.get("/{booking_id}")
def booking_detail(booking_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    business = db.get(Business, booking.business_id)
    is_owner = business and business.owner_user_id == current_user.id
    is_client = booking.user_id == current_user.id
    if not (is_owner or is_client):
        raise HTTPException(status_code=403, detail="Not allowed to view this booking")
    return {"booking": booking_payload(booking, db)}


@router.patch("/{booking_id}/cancel")
def cancel_booking(booking_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    business = db.get(Business, booking.business_id)
    is_owner = business and business.owner_user_id == current_user.id
    is_client = booking.user_id == current_user.id
    if not (is_owner or is_client):
        raise HTTPException(status_code=403, detail="Not allowed")
    booking.status = "canceled"
    db.commit()
    return {"booking": booking_payload(booking, db)}


@router.patch("/{booking_id}/reschedule")
def reschedule_booking(booking_id: str, payload: BookingRescheduleRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    business = db.get(Business, booking.business_id)
    is_owner = business and business.owner_user_id == current_user.id
    is_client = booking.user_id == current_user.id
    if not (is_owner or is_client):
        raise HTTPException(status_code=403, detail="Not allowed")
    service = db.get(Service, booking.service_id)
    available, end_at = check_business_availability_for_booking(booking.business_id, payload.start_at, service.duration_minutes, db, ignore_booking_id=booking.id)
    if not available:
        raise HTTPException(status_code=409, detail="Business is not available in that time slot")
    if not service_allows_slot(service, business, payload.start_at, end_at):
        raise HTTPException(status_code=409, detail="Service is not available in that time slot")
    booking.start_at = payload.start_at
    booking.end_at = end_at
    db.commit()
    return {"booking": booking_payload(booking, db)}


@router.patch("/{booking_id}/status")
def update_booking_status(booking_id: str, payload: BookingStatusRequest, current_business=Depends(get_current_business), db: Session = Depends(get_db)):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.business_id != current_business.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    booking.status = payload.status
    notification = Notification(
        id=make_id("note"),
        recipient_user_id=booking.user_id,
        type="booking_status",
        title="Estado de reserva actualizado",
        message=f"Tu reserva fue {payload.status}",
        read=False,
    )
    db.add(notification)
    db.commit()
    return {"booking": booking_payload(booking, db)}
