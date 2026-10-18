"""
 START -> draft_followup -> human_review --approve----> send_followup -> END
              ^                  |
              |                  +--reject-----> discard_followup -> END
              +---regenerate-----+
"""
from langgraph.graph import END, START, StateGraph

from app.agent.nodes import discard_followup, draft_followup, human_review, send_followup
from app.agent.routing import DISCARD, REDRAFT, SEND, route_after_review
from app.agent.state import FollowUpState


def build_graph(checkpointer):
    builder = StateGraph(FollowUpState)
    builder.add_node("draft_followup", draft_followup)
    builder.add_node("human_review", human_review)
    builder.add_node("send_followup", send_followup)
    builder.add_node("discard_followup", discard_followup)

    builder.add_edge(START, "draft_followup")
    builder.add_edge("draft_followup", "human_review")
    builder.add_conditional_edges(
        "human_review", route_after_review, {SEND: "send_followup", REDRAFT: "draft_followup", DISCARD: "discard_followup"}
    )
    builder.add_edge("send_followup", END)
    builder.add_edge("discard_followup", END)

    return builder.compile(checkpointer=checkpointer)
