from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User, UserRole


class _RedirectException(Exception):
    def __init__(self, url: str):
        self.url = url


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def require_student(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    user = await get_current_user(request, db)
    if user is None:
        request.session.clear()
        raise _RedirectException(f"/login?next={request.url.path}")
    if user.role != UserRole.student:
        raise _RedirectException("/admin/dashboard")
    return user


async def require_admin(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    user = await get_current_user(request, db)
    if user is None:
        request.session.clear()
        raise _RedirectException(f"/login?next={request.url.path}")
    if user.role != UserRole.administrator:
        raise _RedirectException("/student/dashboard")
    return user
