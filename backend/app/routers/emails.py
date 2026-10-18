from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models import FollowUp, User
from app.schemas import EmailThreadSummary, MessageOut, ThreadDetail
from app.services.classifier import Category, classify
from app.services.gmail import GmailClient
from app.services.gmail_parsing import has_human_participation
from app.services.google_oauth import get_access_token

router = APIRouter(prefix="/emails", tags=["emails"])


@router.get("", response_model=list[EmailThreadSummary])
async def list_relevant_emails(
    category: Optional[Category] = None,
    awaiting_reply: Optional[bool] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EmailThreadSummary]:
    """Threads from the last N days (default 5) that look career-related, newest first."""
    s = get_settings()
    token = await get_access_token(user)
    async with GmailClient(token, user.email) as gmail:
        ids = await gmail.list_recent_thread_ids(s.email_lookback_days, s.max_threads, s.exclude_promotions)
        threads = await gmail.get_threads_metadata(ids)

    rows = (
        await db.execute(
            select(FollowUp.thread_id, FollowUp.status).where(
                FollowUp.user_id == user.id, FollowUp.thread_id.in_([t.id for t in threads])
            )
        )
    ).all()
    has_followup = {r.thread_id for r in rows}
    followup_sent = {r.thread_id for r in rows if r.status == "sent"}

    out: list[EmailThreadSummary] = []
    for t in threads:
        if not has_human_participation(t):
            continue
        cat, _score = classify(t.subject, " ".join(m.snippet for m in t.messages))
        if cat is None:
            continue
        if category and cat != category:
            continue
        last = t.last
        if awaiting_reply is not None and last.is_from_me != awaiting_reply:
            continue
        out.append(
            EmailThreadSummary(
                thread_id=t.id,
                subject=t.subject,
                sender_name=last.sender_name,
                sender_email=last.sender_email,
                date=last.date,
                snippet=last.snippet,
                category=cat,
                message_count=len(t.messages),
                awaiting_reply=last.is_from_me,
                has_followup=t.id in has_followup,
                followup_sent=t.id in followup_sent,
            )
        )
    out.sort(key=lambda e: e.date, reverse=True)
    return out


@router.get("/{thread_id}", response_model=ThreadDetail)
async def get_thread(thread_id: str, user: User = Depends(get_current_user)) -> ThreadDetail:
    token = await get_access_token(user)
    async with GmailClient(token, user.email) as gmail:
        t = await gmail.get_thread(thread_id, full=True)
    cat, _ = classify(t.subject, " ".join(m.body or m.snippet for m in t.messages))
    return ThreadDetail(
        thread_id=t.id,
        subject=t.subject,
        category=cat,
        messages=[
            MessageOut(
                id=m.id,
                sender_name=m.sender_name,
                sender_email=m.sender_email,
                to=m.to_emails,
                date=m.date,
                body=m.body or m.snippet,
                is_from_me=m.is_from_me,
            )
            for m in t.messages
        ],
    )
