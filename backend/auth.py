from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Cookie, Depends
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.db import get_db
from backend.models import User

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30


def create_access_token(sub: str) -> str:
    settings = get_settings()
    if not settings.jwt_secret_key:
        raise RuntimeError("JWT signing is unavailable when SSO is disabled")
    expire = datetime.now(timezone.utc) + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    return jwt.encode({"sub": sub, "exp": expire}, settings.jwt_secret_key, algorithm=ALGORITHM)


async def get_current_user(
    session_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if not session_token:
        return None
    try:
        settings = get_settings()
        payload = jwt.decode(session_token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        sub: Optional[str] = payload.get("sub")
        if not sub:
            return None
        result = await db.execute(select(User).where(User.id == sub))
        return result.scalar_one_or_none()
    except JWTError:
        return None


async def require_user(user: Optional[User] = Depends(get_current_user)) -> User:
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
