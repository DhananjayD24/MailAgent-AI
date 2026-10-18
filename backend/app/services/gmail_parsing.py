"""Pure helpers for turning Gmail API payloads into clean, LLM-friendly objects (stdlib only)."""
import base64
import html as htmllib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import getaddresses, parseaddr
from html.parser import HTMLParser
from typing import Optional

NOREPLY_RE = re.compile(
    r"(no[-_.]?reply|do[-_.]?not[-_.]?reply|mailer-daemon|postmaster@|notifications?@)", re.I
)


@dataclass
class ParsedMessage:
    id: str
    thread_id: str
    sender_name: str
    sender_email: str
    to_emails: list[str]
    cc_emails: list[str]
    reply_to: Optional[str]
    subject: str
    date: datetime
    snippet: str
    body: str
    message_id_header: Optional[str]
    references: Optional[str]
    label_ids: list[str]
    is_from_me: bool

    @property
    def is_noreply(self) -> bool:
        return bool(NOREPLY_RE.search(self.sender_email or ""))


@dataclass
class ParsedThread:
    id: str
    messages: list[ParsedMessage]

    @property
    def subject(self) -> str:
        for m in self.messages:
            if m.subject:
                return m.subject
        return "(no subject)"

    @property
    def last(self) -> ParsedMessage:
        return self.messages[-1]


def has_human_participation(thread: ParsedThread) -> bool:
    """False for threads that are purely automated mail (nobody to actually follow up with)."""
    return any(m.is_from_me or not m.is_noreply for m in thread.messages)


# ---------- body extraction ----------

def _b64decode(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


class _TextExtractor(HTMLParser):
    _BLOCK = {"br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
        elif tag in self._BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1
        elif tag in self._BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return "".join(parser.parts)


def _walk_parts(part: dict, plain: list[str], html: list[str]) -> None:
    if part.get("filename"):  # attachment
        return
    mime = part.get("mimeType", "")
    data = part.get("body", {}).get("data")
    if data and mime == "text/plain":
        plain.append(_b64decode(data))
    elif data and mime == "text/html":
        html.append(_b64decode(data))
    for sub in part.get("parts") or []:
        _walk_parts(sub, plain, html)


_QUOTE_HEADER_RES = [
    re.compile(r"\n[ \t]*On .{5,300}?wrote:[ \t]*\n", re.S),
    re.compile(r"\n[ \t]*-{2,}[ \t]*Original Message[ \t]*-{2,}", re.I),
    re.compile(r"\n[ \t]*From:.*\n[ \t]*Sent:", re.I),
    re.compile(r"\n[ \t]*_{10,}\s*\n"),
]


def strip_quoted(text: str) -> str:
    """Remove quoted earlier messages so each message contributes only its new text."""
    text = "\n" + text.replace("\r\n", "\n").replace("\r", "\n")
    for pattern in _QUOTE_HEADER_RES:
        m = pattern.search(text)
        if m:
            text = text[: m.start()]
    lines = [ln for ln in text.split("\n") if not ln.lstrip().startswith(">")]
    text = "\n".join(lines)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_body(payload: dict) -> str:
    plain: list[str] = []
    html: list[str] = []
    _walk_parts(payload, plain, html)
    text = "\n".join(plain) if plain else html_to_text("\n".join(html))
    return strip_quoted(text)


# ---------- message / thread parsing ----------

def parse_message(raw: dict, my_email: str, with_body: bool) -> ParsedMessage:
    payload = raw.get("payload", {})
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
    name, addr = parseaddr(headers.get("from", ""))
    labels = raw.get("labelIds", [])
    internal_ms = int(raw.get("internalDate", 0) or 0)

    return ParsedMessage(
        id=raw["id"],
        thread_id=raw.get("threadId", ""),
        sender_name=name,
        sender_email=addr,
        to_emails=[a for _, a in getaddresses([headers.get("to", "")]) if a],
        cc_emails=[a for _, a in getaddresses([headers.get("cc", "")]) if a],
        reply_to=parseaddr(headers.get("reply-to", ""))[1] or None,
        subject=headers.get("subject", ""),
        date=datetime.fromtimestamp(internal_ms / 1000, tz=timezone.utc),
        snippet=htmllib.unescape(raw.get("snippet", "")),
        body=extract_body(payload) if with_body else "",
        message_id_header=headers.get("message-id"),
        references=headers.get("references"),
        label_ids=labels,
        is_from_me=("SENT" in labels) or (addr.lower() == my_email.lower()),
    )


def parse_thread(raw: dict, my_email: str, with_body: bool) -> ParsedThread:
    messages = [
        parse_message(m, my_email, with_body)
        for m in raw.get("messages", [])
        if "DRAFT" not in m.get("labelIds", [])
    ]
    messages.sort(key=lambda m: m.date)
    return ParsedThread(id=raw["id"], messages=messages)
