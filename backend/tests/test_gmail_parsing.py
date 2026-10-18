import base64

from app.services.gmail_parsing import (
    extract_body,
    has_human_participation,
    html_to_text,
    parse_thread,
    strip_quoted,
)


def b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


def raw_msg(mid, sender, body, ms, labels=(), to="me@example.com", subject="Hello"):
    return {
        "id": mid,
        "threadId": "t1",
        "internalDate": str(ms),
        "labelIds": list(labels),
        "snippet": body[:40],
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "From", "value": sender},
                {"name": "To", "value": to},
                {"name": "Subject", "value": subject},
                {"name": "Message-ID", "value": f"<{mid}@mail>"},
            ],
            "parts": [{"mimeType": "text/plain", "body": {"data": b64(body)}}],
        },
    }


def test_strip_quoted_removes_gmail_style_quote():
    text = "Thanks, I'll send it over.\n\nOn Mon, Oct 12, 2026 at 5:00 PM Jane <jane@x.com> wrote:\n> old stuff\n> more"
    assert strip_quoted(text) == "Thanks, I'll send it over."


def test_strip_quoted_drops_gt_lines():
    assert strip_quoted("Hi\n> quoted\nBye") == "Hi\nBye"


def test_html_fallback_and_attachment_skipped():
    payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {"mimeType": "text/html", "body": {"data": b64("<p>Hello<br>world</p><style>x{}</style>")}},
            {"mimeType": "text/plain", "filename": "cv.txt", "body": {"data": b64("SECRET ATTACHMENT")}},
        ],
    }
    body = extract_body(payload)
    assert "Hello" in body and "world" in body
    assert "SECRET" not in body and "x{}" not in body


def test_html_to_text_basic():
    assert "a" in html_to_text("<div>a</div>")


def test_parse_thread_orders_flags_and_drops_drafts():
    raw = {
        "id": "t1",
        "messages": [
            raw_msg("m2", "Recruiter <jane@acme.com>", "Please send availability", 2000, to="me@example.com"),
            raw_msg("m1", "Me <me@example.com>", "Applying for the role", 1000, labels=["SENT"], to="jane@acme.com"),
            raw_msg("m3", "Me <me@example.com>", "draft text", 3000, labels=["DRAFT"]),
        ],
    }
    t = parse_thread(raw, "me@example.com", with_body=True)
    assert [m.id for m in t.messages] == ["m1", "m2"]
    assert t.messages[0].is_from_me and not t.messages[1].is_from_me
    assert t.last.sender_email == "jane@acme.com"
    assert has_human_participation(t)


def test_noreply_only_thread_is_not_human():
    raw = {"id": "t1", "messages": [raw_msg("m1", "Acme <no-reply@acme.com>", "Application received", 1000)]}
    t = parse_thread(raw, "me@example.com", with_body=False)
    assert not has_human_participation(t)
