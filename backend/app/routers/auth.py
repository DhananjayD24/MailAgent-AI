import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import UserOut
from app.security import (
    SESSION_COOKIE,
    STATE_COOKIE,
    create_session_token,
    encrypt,
)
from app.services.google_oauth import (
    REQUIRED_GMAIL_SCOPES,
    build_auth_url,
    cache_access_token,
    exchange_code,
    fetch_userinfo,
    forget_access_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _frontend_redirect(path_or_query: str) -> RedirectResponse:
    return RedirectResponse(get_settings().frontend_url + path_or_query)


@router.get("/login")
async def login() -> RedirectResponse:
    """Send the browser here (full-page navigation) to start Google sign-in."""
    s = get_settings()
    state = secrets.token_urlsafe(32)
    resp = RedirectResponse(build_auth_url(state))
    resp.set_cookie(STATE_COOKIE, state, max_age=600, httponly=True, samesite="lax", secure=s.cookie_secure)
    return resp


@router.get("/callback")
async def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    s = get_settings()
    if error:
        return _frontend_redirect(f"/?auth_error={error}")

    cookie_state = request.cookies.get(STATE_COOKIE)
    if not code or not state or not cookie_state or not secrets.compare_digest(state, cookie_state):
        raise HTTPException(status_code=400, detail="invalid_oauth_state")

    tokens = await exchange_code(code)

    granted = set(tokens.get("scope", "").split())
    if not REQUIRED_GMAIL_SCOPES <= granted:
        return _frontend_redirect("/?auth_error=missing_gmail_permissions")

    info = await fetch_userinfo(tokens["access_token"])
    refresh = tokens.get("refresh_token")

    user = (await db.execute(select(User).where(User.google_sub == info["sub"]))).scalar_one_or_none()
    if user is None:
        if not refresh:
            return _frontend_redirect("/?auth_error=no_refresh_token")
        user = User(
            google_sub=info["sub"],
            email=info["email"],
            name=info.get("name"),
            encrypted_refresh_token=encrypt(refresh),
        )
        db.add(user)
    else:
        user.email = info["email"]
        user.name = info.get("name")
        if refresh:
            user.encrypted_refresh_token = encrypt(refresh)
    await db.commit()

    cache_access_token(user.id, tokens["access_token"], tokens.get("expires_in", 3600))

    resp = _frontend_redirect(s.post_login_path)
    resp.set_cookie(
        SESSION_COOKIE,
        create_session_token(str(user.id)),
        max_age=s.session_ttl_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=s.cookie_secure,
    )
    resp.delete_cookie(STATE_COOKIE)
    return resp


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/logout", status_code=204)
async def logout(response: Response, user: User = Depends(get_current_user)) -> Response:
    forget_access_token(user.id)
    response.delete_cookie(SESSION_COOKIE)
    response.status_code = 204
    return response
