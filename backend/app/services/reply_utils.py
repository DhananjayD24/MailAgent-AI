"""Pure helpers for building a threaded reply (stdlib + parsed-thread types only)."""
import base64
import re
from email.message import EmailMessage
from typing import Optional

from app.services.gmail_parsing import ParsedThread


class FollowUpError(Exception):
    status_code = 400
    code = "followup_error"


class NoRecipientError(FollowUpError):
    status_code = 422
    code = "no_reply_recipient_found"


class EmptyThreadError(FollowUpError):
    status_code = 404
    code = "thread_empty"


class InvalidEmailHeaders(FollowUpError):
    status_code = 422
    code = "invalid_email_headers"


def reply_target(thread: ParsedThread, my_email: str) -> Optional[str]:
    last = thread.last
    if not last.is_from_me:
        return last.reply_to or last.sender_email or None
    # The user spoke last: follow up with whoever they wrote to.
    for addr in last.to_emails:
        if addr.lower() != my_email.lower():
            return addr
    for m in reversed(thread.messages):
        if not m.is_from_me:
            return m.reply_to or m.sender_email or None
    return None


def reply_subject(subject: str) -> str:
    subject = subject.strip() or "(no subject)"
    return subject if re.match(r"(?i)^re:", subject) else f"Re: {subject}"


def reply_references(thread: ParsedThread) -> tuple[Optional[str], Optional[str]]:
    """Return (In-Reply-To, References) headers for replying to the last message."""
    last = thread.last
    refs = " ".join(x for x in (last.references, last.message_id_header) if x) or None
    return last.message_id_header, refs


def build_raw_reply(
    *,
    from_email: str,
    to_email: str,
    subject: str,
    body: str,
    in_reply_to: Optional[str],
    references: Optional[str],
) -> str:
    """Return the base64url-encoded RFC 2822 message Gmail's send endpoint expects."""
    msg = EmailMessage()
    try:
        msg["To"] = to_email
        msg["From"] = from_email
        msg["Subject"] = subject
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
        if references:
            msg["References"] = references
    except ValueError as exc:  # newline/header injection or invalid header value
        raise InvalidEmailHeaders() from exc
    msg.set_content(body)
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()
