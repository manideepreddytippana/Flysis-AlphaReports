import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.db.models import User

logger = logging.getLogger(__name__)

# Empty router to avoid import errors in main.py if still referenced
router = APIRouter(prefix="/auth", tags=["auth"])

DEV_USER = {
    "union_id": "dev-local-user",
    "name": "Dev User",
    "email": "dev@filysis.local",
    "role": "admin",
}


async def ensure_dev_user(db: AsyncSession) -> User:
    """Ensure the single dev user exists in the database."""
    result = await db.execute(select(User).where(User.union_id == DEV_USER["union_id"]))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            union_id=DEV_USER["union_id"],
            name=DEV_USER["name"],
            email=DEV_USER["email"],
            role=DEV_USER["role"],
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info(f"Created dev user: {user.name} (id={user.id})")
    return user

async def get_current_user(db: AsyncSession = Depends(get_db)) -> User:
    """Mock auth: always return the dev user."""
    result = await db.execute(select(User).where(User.union_id == DEV_USER["union_id"]))
    user = result.scalar_one_or_none()
    if not user:
        user = await ensure_dev_user(db)
    return user

async def get_optional_user(db: AsyncSession = Depends(get_db)) -> User:
    """Mock auth: always return the dev user."""
    return await get_current_user(db)
