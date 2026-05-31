from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_business
from ..models import Service
from ..schemas import ServiceUpdateRequest
from ..serializers import service_payload

router = APIRouter(prefix="/services", tags=["services"])


@router.patch("/{service_id}")
def update_service(service_id: str, payload: ServiceUpdateRequest, current_business=Depends(get_current_business), db: Session = Depends(get_db)):
    service = db.get(Service, service_id)
    if not service or service.business_id != current_business.id:
        raise HTTPException(status_code=404, detail="Service not found")
    team_member_ids = {member.get("id") for member in (current_business.team or []) if isinstance(member, dict) and member.get("id")}
    for field_name in ["name", "description", "duration_minutes", "price", "active", "weekly_hours"]:
        value = getattr(payload, field_name)
        if value is not None:
            setattr(service, field_name, value)
    if payload.professionals is not None:
        if not payload.professionals:
            raise HTTPException(status_code=400, detail="At least one professional is required")
        for professional in payload.professionals:
            if professional.get("id") not in team_member_ids:
                raise HTTPException(status_code=400, detail="Each professional must exist in the business team")
        service.professionals = payload.professionals
    db.commit()
    db.refresh(service)
    return {"service": service_payload(service)}


@router.delete("/{service_id}")
def delete_service(service_id: str, current_business=Depends(get_current_business), db: Session = Depends(get_db)):
    service = db.get(Service, service_id)
    if not service or service.business_id != current_business.id:
        raise HTTPException(status_code=404, detail="Service not found")
    db.delete(service)
    db.commit()
    return {"message": "Service deleted"}
