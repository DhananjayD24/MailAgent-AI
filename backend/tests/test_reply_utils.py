import base64
from datetime import datetime, timezone
from email import message_from_bytes

import pytest

from app.services.gmail_parsing import ParsedMessage, ParsedThread
from app.services.reply_utils import (
    InvalidEmailHeaders,
    build_raw_reply,
    reply_references,
    reply_subject,
    reply_target,
)

ME = "me@example.com"


def msg(mid, sender, to, from_me, reply_to=None, refs=None):
    return ParsedMessage(
        id=mid, thread_id="t", sender_name="", sender_email=sender, to_emails=to, cc_emails=[],
        reply_to=reply_to, subject="Hello", date=datetime.now(timezone.utc), snippet="", body="",
        message_id_header=f"<{mid}@mail>", references=refs, label_ids=[], is_from_me=from_me,
    )


def test_target_when_other_party_spoke_last_prefers_reply_to():
    t = ParsedThread("t", [msg("1", "jane@acme.com", [ME], False, reply_to="jobs@acme.com")])
    assert reply_target(t, ME) == "jobs@acme.com"


def test_target_when_user_spoke_last_is_original_recipient():
    t = ParsedThread("t", [msg("1", ME, ["jane@acme.com"], True)])
    assert reply_target(t, ME) == "jane@acme.com"


def test_subject_prefix_not_doubled():
    assert reply_subject("Interview") == "Re: Interview"
    assert reply_subject("RE: Interview") == "RE: Interview"


def test_references_chain():
    t = ParsedThread("t", [msg("2", "jane@acme.com", [ME], False, refs="<1@mail>")])
    in_reply_to, refs = reply_references(t)
    assert in_reply_to == "<2@mail>" and refs == "<1@mail> <2@mail>"


def test_build_raw_reply_roundtrip():
    raw = build_raw_reply(from_email=ME, to_email="jane@acme.com", subject="Re: Hi", body="Thanks!",
                          in_reply_to="<2@mail>", references="<1@mail> <2@mail>")
    parsed = message_from_bytes(base64.urlsafe_b64decode(raw))
    assert parsed["To"] == "jane@acme.com" and parsed["In-Reply-To"] == "<2@mail>"
    assert "Thanks!" in parsed.get_payload(decode=True).decode()


def test_header_injection_rejected():
    with pytest.raises(InvalidEmailHeaders):
        build_raw_reply(from_email=ME, to_email="a@b.com", subject="x\nBcc: evil@x.com", body="hi",
                        in_reply_to=None, references=None)
