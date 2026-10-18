"""Google OAuth 2.0 (authorization-code flow) implemented directly over httpx."""
import time
import uuid
from urllib.parse import urlencode

import httpx

from app.config import get_settings
from app.models import User
from app.security import decrypt

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

GMAIL_READONLY = "https://www.googleapis.com/auth/gmail.readonly"
GMAIL_SEND = "https://www.googleapis.com/auth/gmail.send"
SCOPES = ["openid", "email", "profile", GMAIL_READONLY, GMAIL_SEND]
REQUIRED_GMAIL_SCOPES = {GMAIL_READONLY, GMAIL_SEND}


class ReauthRequired(Exception):
    """The stored refresh token is no longer valid; the user must sign in again."""


class GoogleAuthError(Exception):
    pass


def build_auth_url(state: str) -> str:
    s = get_settings()
    params = {
        "client_id": s.google_client_id,
        "redirect_uri": s.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",  # we need a refresh token
        "prompt": "consent",  # force Google to return the refresh token every time
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


async def exchange_code(code: str) -> dict:
    s = get_settings()
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": s.google_client_id,
                "client_secret": s.google_client_secret,
                "redirect_uri": s.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    if r.status_code != 200:
        raise GoogleAuthError(f"token exchange failed: {r.text[:300]}")
    return r.json()


async def fetch_userinfo(access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
    if r.status_code != 200:
        raise GoogleAuthError(f"userinfo failed: {r.text[:300]}")
    return r.json()


# Short-lived in-process cache of access tokens: user_id -> (token, expires_at_epoch)
_access_cache: dict[uuid.UUID, tuple[str, float]] = {}


def cache_access_token(user_id: uuid.UUID, token: str, expires_in: int) -> None:
    _access_cache[user_id] = (token, time.time() + int(expires_in) - 60)


def forget_access_token(user_id: uuid.UUID) -> None:
    _access_cache.pop(user_id, None)


async def get_access_token(user: User) -> str:
    cached = _access_cache.get(user.id)
    if cached and cached[1] > time.time():
        return cached[0]

    s = get_settings()
    try:
        refresh_token = decrypt(user.encrypted_refresh_token)
    except Exception as exc:  # key rotated / corrupted
        raise ReauthRequired() from exc

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            TOKEN_URL,
            data={
                "client_id": s.google_client_id,
                "client_secret": s.google_client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
    if r.status_code in (400, 401) and "invalid_grant" in r.text:
        raise ReauthRequired()
    if r.status_code != 200:
        raise GoogleAuthError(f"token refresh failed: {r.text[:300]}")

    data = r.json()
    cache_access_token(user.id, data["access_token"], data.get("expires_in", 3600))
    return data["access_token"]
