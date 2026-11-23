"""マイグレーション（D-07）。上げる・戻す・もう一度上げるが通ること。ロールの作成が冪等であること。"""

import asyncio

import pytest
from alembic import command
from sqlalchemy import text

from tests.integration.conftest import alembic_config
from thinkronos.adapters.db.engine import create_engine

pytestmark = pytest.mark.integration


async def _run(url: str, sql: str) -> object:
    engine = create_engine(url, pooled=False)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text(sql))
            return result.scalar() if result.returns_rows else None
    finally:
        await engine.dispose()


def _scalar(url: str, sql: str) -> object:
    return asyncio.run(_run(url, sql))


def test_downgrade_and_upgrade_again(migrated: str) -> None:
    config = alembic_config(migrated)
    command.downgrade(config, "base")
    assert _scalar(migrated, "SELECT to_regclass('workspaces')") is None
    assert _scalar(migrated, "SELECT count(*) FROM pg_roles WHERE rolname = 'thinkronos_app'") == 0
    command.upgrade(config, "head")
    assert _scalar(migrated, "SELECT to_regclass('workspaces')::text") == "workspaces"


def test_role_creation_is_idempotent(migrated: str) -> None:
    """ロールが既にあっても（別のDBで作られた場合など）0001 が通る。"""
    config = alembic_config(migrated)
    command.downgrade(config, "0001")
    command.downgrade(config, "base")
    _scalar(migrated, "CREATE ROLE thinkronos_app LOGIN PASSWORD 'old'")
    command.upgrade(config, "head")
    assert _scalar(migrated, "SELECT count(*) FROM pg_roles WHERE rolname = 'thinkronos_app'") == 1


def test_password_is_not_left_in_settings(migrated: str) -> None:
    value = _scalar(migrated, "SELECT current_setting('thinkronos.app_db_password', true)")
    assert value in (None, "")
