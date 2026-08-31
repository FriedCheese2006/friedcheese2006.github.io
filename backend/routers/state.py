import datetime
import json
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import require_user
from backend.db import get_db
from backend.models import User, UserState

router = APIRouter(prefix="/api", tags=["state"])


class StatePayload(BaseModel):
    tabs: Any
    settings: Any


@router.get("/state")
async def get_state(
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserState).where(UserState.user_id == user.id))
    state = result.scalar_one_or_none()
    if state is None:
        return {"tabs": None, "settings": None}
    return {
        "tabs": json.loads(state.tabs) if state.tabs else None,
        "settings": json.loads(state.settings) if state.settings else None,
    }


@router.put("/state")
async def put_state(
    payload: StatePayload,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(UserState).where(UserState.user_id == user.id))
    state = result.scalar_one_or_none()
    if state is None:
        state = UserState(user_id=user.id)
        db.add(state)
    state.tabs = json.dumps(payload.tabs)
    state.settings = json.dumps(payload.settings)
    state.updated_at = datetime.datetime.now(datetime.UTC)
    await db.commit()
    return {"ok": True}
