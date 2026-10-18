# AI Email Follow-up Agent — Backend

FastAPI backend: Google OAuth → Gmail (last 5 days) → career-email detection → **LangGraph agent with human-in-the-loop** → send via Gmail.
Stack: FastAPI · LangGraph · async SQLAlchemy + PostgreSQL · Gmail REST API (httpx) · Anthropic API. No vector DB.
Requires **Python 3.11+** (LangGraph's `interrupt()` needs it inside async nodes).

## Quick start

```bash
cp .env.example .env            # fill in the values (see below)
docker compose up -d db         # PostgreSQL
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload   # http://localhost:8000/docs
pytest                          # pure-python tests (no network/DB needed)
```

Or run everything in Docker: `docker compose up --build`.

## Google Cloud setup (one time)

1. Create a project → enable the **Gmail API**.
2. OAuth consent screen: External, add yourself under **Test users**.
3. Add scopes: `gmail.readonly`, `gmail.send` (plus openid/email/profile).
4. Credentials → **OAuth client ID** → *Web application*.
   Authorized redirect URI: `http://localhost:8000/auth/callback`
5. Put the client ID/secret in `.env`.

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"                               # SECRET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # TOKEN_ENCRYPTION_KEY
```

> Gmail read/send are **restricted scopes**. In "Testing" mode (up to 100 test users) this just works;
> a public launch requires Google's OAuth verification and security assessment.

## The agent (LangGraph + human-in-the-loop)

```
START -> draft_followup -> human_review --approve----> send_followup -> END
              ^                 |  (graph PAUSES here)
              |                 +--reject-----> discard_followup -> END
              +--regenerate-----+
```

- `POST /followups` runs the graph until `human_review`, where `interrupt()` pauses it. **Nothing is sent.**
- The paused run is saved by LangGraph's Postgres checkpointer (`thread_id` = follow-up id), so it survives restarts and can wait for days.
- `POST /followups/{id}/review` resumes it with the human's decision: `approve` (send, optionally with edits), `regenerate` (loops back to drafting), or `reject`.
- The send step only exists on the `approve` branch, and an unknown decision raises instead of falling through to sending.
- State is kept small: the draft lives in the `followups` table; inbox email contents are never put in checkpoints (the text of edits you submit on approve is).

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/auth/login` | Navigate the browser here to start Google sign-in |
| GET | `/auth/callback` | Google redirects here; sets the session cookie, redirects to the frontend |
| GET | `/auth/me` | Current user |
| POST | `/auth/logout` | Clear session |
| GET | `/emails?category=&awaiting_reply=` | Career-related threads from the last 5 days |
| GET | `/emails/{thread_id}` | Full thread (cleaned message bodies) |
| POST | `/followups` `{thread_id, instructions?}` | Agent drafts a follow-up and pauses (status `draft`) |
| POST | `/followups/{id}/review` `{action, body?, subject?, to_email?, instructions?}` | Human decision: `approve` \| `regenerate` \| `reject` |
| GET | `/followups?thread_id=&status=` | History (`draft` \| `sent` \| `rejected`) |
| GET | `/followups/{id}` | One follow-up |

Examples:
```jsonc
// send as written, or with edits
{ "action": "approve", "body": "Hi Jane, ... (edited text)" }
// try again with guidance
{ "action": "regenerate", "instructions": "shorter and more casual" }
// discard
{ "action": "reject" }
```

Errors the frontend should handle: `401 not_authenticated` / `401 reauth_required` (send to `/auth/login`),
`409 followup_already_resolved` / `no_pending_review`, `422 no_reply_recipient_found` / `invalid_email_headers`, `502 gmail_error` / `llm_error`.

### Frontend integration notes
- Auth is an httpOnly cookie (`session`). Call the API with `fetch(url, { credentials: "include" })`.
- Run frontend and API on the same site (both on `localhost`, or `app.x.com` + `api.x.com`) so the cookie is sent.
- `FRONTEND_URL` is the only allowed CORS origin. Login failures redirect to `FRONTEND_URL/?auth_error=<code>`.

## How the rest works

- **Scanning**: `newer_than:5d` thread search (promotions/social excluded), one metadata call per thread. No-reply-only threads are skipped.
- **Detection**: weighted keyword rules in `app/services/classifier.py` (subject hits count double).
- **Drafting**: full thread cleaned (quoted history and attachments dropped), budgeted to ~20k chars newest-first, sent to the LLM. Thread text is treated as untrusted data in the prompt.
- **Sending**: threaded reply (`In-Reply-To`/`References` + Gmail `threadId`). Row-locked and idempotent.
- **Security**: refresh tokens Fernet-encrypted at rest; access tokens only in memory.

## Known v1 limits / next steps
- The LangGraph wiring has **not been run against a live Postgres/Gmail yet** (only the pure helpers are unit-tested). Try one full draft → regenerate → approve cycle first.
- Tables are created on startup; add **Alembic** before real deployments. LangGraph creates its own checkpoint tables via `setup()`.
- Abandoned paused runs are never cleaned up automatically (LangGraph has no TTL); add a cleanup job later.
- No rate limiting on `/followups` (each call costs LLM tokens).
