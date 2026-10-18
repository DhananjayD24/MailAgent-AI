import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.services.classifier import Category


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: Optional[str]


class EmailThreadSummary(BaseModel):
    thread_id: str
    subject: str
    sender_name: str
    sender_email: str
    date: datetime
    snippet: str
    category: Category
    message_count: int
    awaiting_reply: bool  # last message was sent by the user
    has_followup: bool
    followup_sent: bool


class MessageOut(BaseModel):
    id: str
    sender_name: str
    sender_email: str
    to: list[str]
    date: datetime
    body: str
    is_from_me: bool


class ThreadDetail(BaseModel):
    thread_id: str
    subject: str
    category: Optional[Category]
    messages: list[MessageOut]


class FollowUpCreate(BaseModel):
    thread_id: str = Field(min_length=1, max_length=64)
    instructions: Optional[str] = Field(default=None, max_length=1000)


class ReviewAction(str, Enum):
    approve = "approve"  # send (optionally with edits)
    regenerate = "regenerate"  # new draft, optionally with new instructions
    reject = "reject"  # discard, send nothing


class ReviewRequest(BaseModel):
    action: ReviewAction
    # Edits, used with action=approve
    subject: Optional[str] = Field(default=None, min_length=1, max_length=300, pattern=r"^[^\r\n]+$")
    to_email: Optional[EmailStr] = None
    body: Optional[str] = Field(default=None, min_length=1, max_length=20000)
    # Used with action=regenerate
    instructions: Optional[str] = Field(default=None, max_length=1000)


class FollowUpOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    thread_id: str
    category: Optional[str]
    to_email: str
    subject: str
    body: str
    instructions: Optional[str]
    regeneration_count: int
    status: str  # draft (awaiting review) | sent | rejected
    gmail_message_id: Optional[str]
    sent_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
