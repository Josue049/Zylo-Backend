from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


AccountType = Literal["user", "business"]


class RegisterRequest(BaseModel):
    account_type: AccountType = Field(default="user")
    name: str
    email: str
    password: str
    phone: Optional[str] = None
    location: Optional[str] = None
    business_name: Optional[str] = None
    category_id: Optional[str] = None
    description: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None


class TeamMemberRequest(BaseModel):
    id: str
    name: str
    role: str


class TeamUpdateRequest(BaseModel):
    items: list[TeamMemberRequest]


class ServiceCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    duration_minutes: int = Field(gt=0)
    price: float = Field(ge=0)
    active: bool = True
    weekly_hours: dict[str, list[str]] | None = None
    professionals: list[dict[str, str]] | None = None


class ServiceUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = Field(default=None, gt=0)
    price: Optional[float] = Field(default=None, ge=0)
    active: Optional[bool] = None
    weekly_hours: dict[str, list[str]] | None = None
    professionals: list[dict[str, str]] | None = None


class BookingCreateRequest(BaseModel):
    business_id: str
    service_id: str
    professional_id: str
    start_at: datetime
    notes: Optional[str] = None


class BookingRescheduleRequest(BaseModel):
    start_at: datetime


class BookingStatusRequest(BaseModel):
    status: Literal["accepted", "rejected"]


class BusinessReviewRequest(BaseModel):
    rating: float = Field(ge=1, le=5)
    comment: Optional[str] = None


class AvailabilityBlockCreateRequest(BaseModel):
    start_at: datetime
    end_at: datetime
    reason: Optional[str] = None


class ConversationCreateRequest(BaseModel):
    business_id: str
    subject: Optional[str] = None


class MessageCreateRequest(BaseModel):
    content: str


class NotificationCreateRequest(BaseModel):
    recipient_user_id: str
    type: str
    title: str
    message: str


class GenericMessageOut(BaseModel):
    message: str
