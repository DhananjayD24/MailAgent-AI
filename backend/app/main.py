from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.agent.graph import build_graph
from app.config import get_settings
from app.database import Base, engine
from app.routers import auth, emails, followups
from app.services.gmail import GmailError
from app.services.google_oauth import GoogleAuthError, ReauthRequired
from app.services.llm import LLMError
from app.services.reply_utils import FollowUpError


@asynccontextmanager
async def lifespan(app: FastAPI):
    # v1: create tables on startup. Switch to Alembic migrations before production.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # LangGraph persists paused runs in Postgres (it creates its own checkpoint tables).
    async with AsyncPostgresSaver.from_conn_string(get_settings().checkpoint_db_url) as saver:
        await saver.setup()
        app.state.graph = build_graph(saver)
        yield
    await engine.dispose()


app = FastAPI(title="AI Email Follow-up Agent", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().frontend_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(auth.router)
app.include_router(emails.router)
app.include_router(followups.router)


@app.exception_handler(ReauthRequired)
async def _reauth(_: Request, __: ReauthRequired):
    return JSONResponse({"detail": "reauth_required"}, status_code=401)


@app.exception_handler(GmailError)
async def _gmail_error(_: Request, exc: GmailError):
    status = 404 if exc.status == 404 else 502
    return JSONResponse({"detail": "gmail_error", "gmail_status": exc.status}, status_code=status)


@app.exception_handler(GoogleAuthError)
async def _google_error(_: Request, __: GoogleAuthError):
    return JSONResponse({"detail": "google_auth_error"}, status_code=502)


@app.exception_handler(LLMError)
async def _llm_error(_: Request, __: LLMError):
    return JSONResponse({"detail": "llm_error"}, status_code=502)


@app.exception_handler(FollowUpError)
async def _followup_error(_: Request, exc: FollowUpError):
    return JSONResponse({"detail": exc.code}, status_code=exc.status_code)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
