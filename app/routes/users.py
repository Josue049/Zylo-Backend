from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..cloudinary_api import upload_image_bytes
from ..db import get_db, settings
from ..deps import get_current_user
from ..models import Booking, Business, Favorite, Service, User
from ..schemas import UpdateUserRequest
from ..serializers import business_payload, booking_payload, user_payload

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
def me(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    favorites_count = db.scalar(select(func.count()).select_from(Favorite).where(Favorite.user_id == current_user.id)) or 0
    return {"user": user_payload(current_user, business_id=current_user.business_id, favorites_count=favorites_count)}


@router.patch("/me")
def update_me(payload: UpdateUserRequest, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    for field_name in ["name", "phone", "location", "bio"]:
        value = getattr(payload, field_name)
        if value is not None:
            setattr(current_user, field_name, value)
    db.commit()
    favorites_count = db.scalar(select(func.count()).select_from(Favorite).where(Favorite.user_id == current_user.id)) or 0
    return {"user": user_payload(current_user, business_id=current_user.business_id, favorites_count=favorites_count)}


@router.post("/me/photo")
async def upload_photo(photo: UploadFile = File(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not photo.content_type or not photo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    contents = await photo.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file")

    if not settings.cloudinary_cloud_name or not settings.cloudinary_api_key or not settings.cloudinary_api_secret:
        raise HTTPException(status_code=500, detail="Cloudinary is not configured")

    try:
        result = upload_image_bytes(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
            folder=settings.cloudinary_upload_folder,
            file_name=photo.filename or "photo",
            file_bytes=contents,
            content_type=photo.content_type,
            public_id=current_user.id,
            timeout_seconds=settings.cloudinary_timeout_seconds,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    current_user.photo_url = result["secure_url"]
    db.commit()
    favorites_count = db.scalar(select(func.count()).select_from(Favorite).where(Favorite.user_id == current_user.id)) or 0
    return {"user": user_payload(current_user, business_id=current_user.business_id, favorites_count=favorites_count), "photo_url": current_user.photo_url}


@router.get("/me/favorites")
def list_favorites(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    favorites = list(db.scalars(select(Favorite).where(Favorite.user_id == current_user.id)))
    businesses = []
    for favorite in favorites:
        business = db.get(Business, favorite.business_id)
        if not business:
            continue
        services_count = db.scalar(select(func.count()).select_from(Service).where(Service.business_id == business.id)) or 0
        active_services_count = db.scalar(select(func.count()).select_from(Service).where(Service.business_id == business.id, Service.active.is_(True))) or 0
        businesses.append(business_payload(business, services_count=services_count or 0, active_services_count=active_services_count or 0))
    return {"items": businesses}


@router.post("/me/favorites/{business_id}")
def add_favorite(business_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    business = db.get(Business, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    existing = db.scalar(select(Favorite).where(Favorite.user_id == current_user.id, Favorite.business_id == business_id))
    if not existing:
        db.add(Favorite(user_id=current_user.id, business_id=business_id))
        db.commit()
    return {"message": "Agregado a favoritos"}


@router.delete("/me/favorites/{business_id}")
def remove_favorite(business_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    favorite = db.scalar(select(Favorite).where(Favorite.user_id == current_user.id, Favorite.business_id == business_id))
    if favorite:
        db.delete(favorite)
        db.commit()
    return {"message": "Eliminado de favoritos"}


@router.get("/me/bookings")
def list_my_bookings(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    bookings = list(db.scalars(select(Booking).where(Booking.user_id == current_user.id).order_by(Booking.start_at.desc())))
    return {"items": [booking_payload(booking, db) for booking in bookings]}
