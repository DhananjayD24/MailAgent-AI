import pytest

from app.agent.routing import DISCARD, REDRAFT, SEND, route_after_review


def test_routes():
    assert route_after_review({"decision": {"action": "approve"}}) == SEND
    assert route_after_review({"decision": {"action": "regenerate"}}) == REDRAFT
    assert route_after_review({"decision": {"action": "reject"}}) == DISCARD


@pytest.mark.parametrize("state", [{}, {"decision": {}}, {"decision": {"action": "send_now"}}])
def test_unknown_or_missing_decision_never_sends(state):
    with pytest.raises(ValueError):
        route_after_review(state)
