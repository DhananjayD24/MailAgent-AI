import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    google_sub: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Fernet-encrypted Google refresh token. Access tokens are never stored.
    encrypted_refresh_token: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    followups: Mapped[list["FollowUp"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class FollowUp(Base):
    """One generated follow-up draft. Doubles as the follow-up history."""

    __tablename__ = "followups"
    __table_args__ = (Index("ix_followups_user_thread", "user_id", "thread_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    thread_id: Mapped[str] = mapped_column(String(64))
    category: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    to_email: Mapped[str] = mapped_column(String(320))
    subject: Mapped[str] = mapped_column(String(998))
    body: Mapped[str] = mapped_column(Text)

    # Threading headers captured when the draft was generated
    in_reply_to: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    references_header: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    regeneration_count: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft | sent
    gmail_message_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="followups")
