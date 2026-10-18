import uuid

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.security import SESSION_COOKIE, decode_session_token


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()

    user_id = decode_session_token(token) if token else None
    if not user_id:
        raise HTTPException(status_code=401, detail="not_authenticated")
    try:
        user = await db.get(User, uuid.UUID(user_id))
    except ValueError:
        user = None
    if user is None:
        raise HTTPException(status_code=401, detail="not_authenticated")
    return user
