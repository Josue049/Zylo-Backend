from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_business, get_current_user
from ..models import Business, Conversation, Message, User
from ..schemas import ConversationCreateRequest, MessageCreateRequest
from ..serializers import conversation_payload, message_payload
from ..utils import make_id

router = APIRouter(prefix="/conversations", tags=["conversations"])


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def conversation_visible_to_user(conversation: Conversation, user: User, db: Session) -> bool:
    if user.role == "business_owner":
        business = db.scalar(select(Business).where(Business.owner_user_id == user.id))
        return bool(business and conversation.business_id == business.id)
    return conversation.user_id == user.id


@router.get("")
def list_conversations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role == "business_owner":
        business = db.scalar(select(Business).where(Business.owner_user_id == current_user.id))
        conversations = list(db.scalars(select(Conversation).where(Conversation.business_id == business.id).order_by(Conversation.updated_at.desc()))) if business else []
    else:
        conversations = list(db.scalars(select(Conversation).where(Conversation.user_id == current_user.id).order_by(Conversation.updated_at.desc())))
    return {"items": [conversation_payload(conversation, db, current_user) for conversation in conversations]}


@router.post("")
def create_or_open_conversation(payload: ConversationCreateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role == "business_owner":
        raise HTTPException(status_code=403, detail="Business owners can view conversations but not open them from this endpoint")
    business = db.get(Business, payload.business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    existing = db.scalar(select(Conversation).where(Conversation.business_id == payload.business_id, Conversation.user_id == current_user.id))
    if existing:
        return {"conversation": conversation_payload(existing, db, current_user)}
    conversation = Conversation(
        id=make_id("conv"),
        user_id=current_user.id,
        business_id=payload.business_id,
        subject=payload.subject,
        last_read_at_client=utcnow(),
        last_read_at_business=utcnow(),
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return {"conversation": conversation_payload(conversation, db, current_user)}


@router.get("/{conversation_id}/messages")
def list_messages(conversation_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation = db.get(Conversation, conversation_id)
    if not conversation or not conversation_visible_to_user(conversation, current_user, db):
        raise HTTPException(status_code=404, detail="Conversation not found")
    items = list(db.scalars(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc())))
    return {"items": [message_payload(message) for message in items]}


@router.post("/{conversation_id}/messages")
def send_message(conversation_id: str, payload: MessageCreateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation = db.get(Conversation, conversation_id)
    if not conversation or not conversation_visible_to_user(conversation, current_user, db):
        raise HTTPException(status_code=404, detail="Conversation not found")
    message = Message(id=make_id("msg"), conversation_id=conversation_id, sender_user_id=current_user.id, content=payload.content)
    db.add(message)
    conversation.updated_at = utcnow()
    db.commit()
    db.refresh(message)
    return {"message": message_payload(message)}


@router.patch("/{conversation_id}/read")
def mark_conversation_read(conversation_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation = db.get(Conversation, conversation_id)
    if not conversation or not conversation_visible_to_user(conversation, current_user, db):
        raise HTTPException(status_code=404, detail="Conversation not found")
    if current_user.role == "business_owner":
        conversation.last_read_at_business = utcnow()
    else:
        conversation.last_read_at_client = utcnow()
    conversation.updated_at = utcnow()
    db.commit()
    return {"message": "Conversation marked as read"}
