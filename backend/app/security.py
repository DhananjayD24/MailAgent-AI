import time
from functools import lru_cache
from typing import Optional

import jwt
from cryptography.fernet import Fernet

from app.config import get_settings

SESSION_COOKIE = "session"
STATE_COOKIE = "oauth_state"


@lru_cache
def _fernet() -> Fernet:
    return Fernet(get_settings().token_encryption_key.encode())


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return _fernet().decrypt(value.encode()).decode()


def create_session_token(user_id: str) -> str:
    s = get_settings()
    now = int(time.time())
    payload = {"sub": user_id, "iat": now, "exp": now + s.session_ttl_hours * 3600}
    return jwt.encode(payload, s.secret_key, algorithm="HS256")


def decode_session_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    return payload.get("sub")
