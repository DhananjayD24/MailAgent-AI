from typing import Optional, TypedDict


class FollowUpState(TypedDict, total=False):
    """Graph state. Deliberately small: the draft itself lives in the `followups` table,
    and inbox email contents are never put in the checkpoint."""

    followup_id: str
    user_id: str
    gmail_thread_id: str
    instructions: Optional[str]
    decision: dict  # latest human decision: {"action": ..., optional edits}
    outcome: str  # "sent" | "rejected"
