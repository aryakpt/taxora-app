from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncIterator[AsyncSession]:
    """One transaction per request: commit on success, roll back on any error."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise


# scope="function" runs the commit before the response is sent, so a failed commit
# surfaces as an error instead of a false success. Always use this alias rather than a
# bare Depends(get_session): the scope is part of FastAPI's dependency cache key, and
# mixing both forms would open two separate sessions within one request.
SessionDep = Annotated[AsyncSession, Depends(get_session, scope="function")]
