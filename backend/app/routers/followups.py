import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from langgraph.types import Command
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models import FollowUp, User
from app.schemas import FollowUpCreate, FollowUpOut, ReviewRequest

router = APIRouter(prefix="/followups", tags=["followups"])


def get_graph(request: Request):
    return request.app.state.graph


def _config(followup_id: uuid.UUID) -> dict:
    # One LangGraph thread per follow-up; the thread_id is how a paused run is resumed.
    return {"configurable": {"thread_id": str(followup_id)}}


async def _get_owned(db: AsyncSession, user: User, followup_id: uuid.UUID) -> FollowUp:
    stmt = (
        select(FollowUp)
        .where(FollowUp.id == followup_id, FollowUp.user_id == user.id)
        .execution_options(populate_existing=True)  # graph nodes write via their own sessions
    )
    fu = (await db.execute(stmt)).scalar_one_or_none()
    if fu is None:
        raise HTTPException(status_code=404, detail="followup_not_found")
    return fu


@router.post("", response_model=FollowUpOut, status_code=201)
async def create_followup(
    payload: FollowUpCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    graph=Depends(get_graph),
) -> FollowUp:
    """Start the agent. It drafts a follow-up, then PAUSES for human review. Nothing is sent."""
    followup_id = uuid.uuid4()
    await graph.ainvoke(
        {
            "followup_id": str(followup_id),
            "user_id": str(user.id),
            "gmail_thread_id": payload.thread_id,
            "instructions": payload.instructions,
        },
        _config(followup_id),
    )
    return await _get_owned(db, user, followup_id)


@router.post("/{followup_id}/review", response_model=FollowUpOut)
async def review_followup(
    followup_id: uuid.UUID,
    payload: ReviewRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    graph=Depends(get_graph),
) -> FollowUp:
    """The human decision. approve = send (optionally with edits), regenerate = new draft, reject = discard."""
    fu = await _get_owned(db, user, followup_id)
    if fu.status != "draft":
        raise HTTPException(status_code=409, detail="followup_already_resolved")

    config = _config(followup_id)
    snapshot = await graph.aget_state(config)
    if not snapshot.next:
        raise HTTPException(status_code=409, detail="no_pending_review")

    if "human_review" in snapshot.next:
        decision = payload.model_dump(mode="json", exclude_none=True)
        await graph.ainvoke(Command(resume=decision), config)
    else:
        # A previous approve failed part-way (e.g. Gmail error) after the decision was
        # recorded; re-run the failed step. Edits in this request are ignored on retry.
        await graph.ainvoke(None, config)

    return await _get_owned(db, user, followup_id)


@router.get("", response_model=list[FollowUpOut])
async def list_followups(
    thread_id: Optional[str] = None,
    status: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FollowUp]:
    """Follow-up history, newest first. Filter by thread or status (draft|sent|rejected)."""
    stmt = select(FollowUp).where(FollowUp.user_id == user.id).order_by(FollowUp.created_at.desc())
    if thread_id:
        stmt = stmt.where(FollowUp.thread_id == thread_id)
    if status:
        stmt = stmt.where(FollowUp.status == status)
    return list((await db.execute(stmt.limit(200))).scalars())


@router.get("/{followup_id}", response_model=FollowUpOut)
async def get_followup(
    followup_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> FollowUp:
    return await _get_owned(db, user, followup_id)
