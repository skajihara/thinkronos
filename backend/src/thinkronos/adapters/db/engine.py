"""エンジンとセッションの作成、DB の死活確認。"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


def create_engine(url: str, *, pooled: bool = True) -> AsyncEngine:
    """pooled=False は NullPool（接続を使い回さない）。

    ワーカーでタスクごとに asyncio.run する方式（ADR 0005 の A 案）では、asyncpg の接続が
    作られたイベントループに結び付くため、ループをまたいで接続を使い回せない。
    """
    if pooled:
        return create_async_engine(url, pool_pre_ping=True)
    return create_async_engine(url, poolclass=NullPool)


def create_sessions(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


class SqlAlchemyDatabaseProbe:
    def __init__(self, engine: AsyncEngine, *, timeout_seconds: float = 3.0) -> None:
        self._engine = engine
        self._timeout = timeout_seconds

    async def ping(self) -> bool:
        try:
            async with asyncio.timeout(self._timeout), self._engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception:
            return False
        return True
