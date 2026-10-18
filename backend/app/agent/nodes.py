import uuid

from langgraph.types import interrupt
from sqlalchemy import select

from app.agent.state import FollowUpState
from app.database import SessionLocal
from app.models import FollowUp, User
from app.services.classifier import Category, classify
from app.services.gmail import GmailClient
from app.services.gmail_parsing import ParsedThread
from app.services.google_oauth import get_access_token
from app.services.llm import generate_followup_body
from app.services.reply_utils import (
    EmptyThreadError,
    NoRecipientError,
    build_raw_reply,
    reply_references,
    reply_subject,
    reply_target,
)
from datetime import datetime, timezone


async def _load_full_thread(user: User, thread_id: str) -> ParsedThread:
    token = await get_access_token(user)
    async with GmailClient(token, user.email) as gmail:
        thread = await gmail.get_thread(thread_id, full=True)
    if not thread.messages:
        raise EmptyThreadError()
    return thread


async def draft_followup(state: FollowUpState) -> dict:
    """Create the draft (first pass) or write a new version of it (after 'regenerate')."""
    followup_id = uuid.UUID(state["followup_id"])
    async with SessionLocal() as db:
        user = await db.get(User, uuid.UUID(state["user_id"]))
        if user is None:
            raise ValueError("user_not_found")
        fu = await db.get(FollowUp, followup_id)

        thread = await _load_full_thread(user, state["gmail_thread_id"])

        to_email = None
        if fu is None:
            to_email = reply_target(thread, user.email)
            if not to_email:
                raise NoRecipientError()  # fail before spending LLM tokens

        category, _ = classify(thread.subject, " ".join(m.body or m.snippet for m in thread.messages))
        body = await generate_followup_body(
            thread=thread,
            user_name=user.name,
            user_email=user.email,
            category=category,
            instructions=state.get("instructions"),
            previous_draft=fu.body if fu else None,
        )

        if fu is None:
            in_reply_to, refs = reply_references(thread)
            db.add(
                FollowUp(
                    id=followup_id,
                    user_id=user.id,
                    thread_id=thread.id,
                    category=category.value if isinstance(category, Category) else None,
                    to_email=to_email,
                    subject=reply_subject(thread.subject),
                    body=body,
                    in_reply_to=in_reply_to,
                    references_header=refs,
                    instructions=state.get("instructions"),
                )
            )
        else:
            fu.body = body
            fu.instructions = state.get("instructions")
            fu.regeneration_count += 1
        await db.commit()
    return {}


async def human_review(state: FollowUpState) -> dict:
    """Pause the graph until a human decides. No side effects here: on resume, LangGraph
    re-runs this node from the top and interrupt() returns the human's decision."""
    decision = interrupt({"kind": "review_followup", "followup_id": state["followup_id"]})
    update: dict = {"decision": decision}
    if decision.get("action") == "regenerate":
        update["instructions"] = decision.get("instructions") or state.get("instructions")
    return update


async def send_followup(state: FollowUpState) -> dict:
    """Runs only after an explicit 'approve'. Applies any edits, then sends via Gmail."""
    decision = state.get("decision") or {}
    async with SessionLocal() as db:
        # Row lock + status check: safe against double-submits and node retries.
        fu = (
            await db.execute(
                select(FollowUp)
                .where(FollowUp.id == uuid.UUID(state["followup_id"]), FollowUp.user_id == uuid.UUID(state["user_id"]))
                .with_for_update()
            )
        ).scalar_one()
        if fu.status == "sent":
            return {"outcome": "sent"}

        for field in ("subject", "to_email", "body"):
            if decision.get(field):
                setattr(fu, field, decision[field])

        user = await db.get(User, fu.user_id)
        raw = build_raw_reply(
            from_email=user.email,
            to_email=fu.to_email,
            subject=fu.subject,
            body=fu.body,
            in_reply_to=fu.in_reply_to,
            references=fu.references_header,
        )
        token = await get_access_token(user)
        async with GmailClient(token, user.email) as gmail:
            sent = await gmail.send_raw(raw, fu.thread_id)

        fu.status = "sent"
        fu.gmail_message_id = sent.get("id")
        fu.sent_at = datetime.now(timezone.utc)
        await db.commit()
    return {"outcome": "sent"}


async def discard_followup(state: FollowUpState) -> dict:
    async with SessionLocal() as db:
        fu = await db.get(FollowUp, uuid.UUID(state["followup_id"]))
        if fu is not None and fu.status == "draft":
            fu.status = "rejected"
            await db.commit()
    return {"outcome": "rejected"}
