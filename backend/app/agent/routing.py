"""Routing after the human-review step (stdlib only, so it is trivially testable)."""
from typing import Any, Mapping

SEND = "send_followup"
REDRAFT = "draft_followup"
DISCARD = "discard_followup"

_ROUTES = {"approve": SEND, "regenerate": REDRAFT, "reject": DISCARD}


def route_after_review(state: Mapping[str, Any]) -> str:
    action = (state.get("decision") or {}).get("action")
    try:
        return _ROUTES[action]
    except KeyError:
        # Never fall through to sending on an unknown decision.
        raise ValueError(f"unknown review action: {action!r}") from None
