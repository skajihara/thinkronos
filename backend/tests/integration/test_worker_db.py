"""ワーカーで async のユースケースを本物の DB に対して実行する（G-22、ADR 0005 の A 案と B 案の比較）。

ブローカーは memory://（Redis を使う確認は compose で行う）。
"""

import asyncio
from uuid import uuid4

import pytest
from celery.contrib.testing.worker import start_worker
from sqlalchemy import text

from tests.integration.conftest import APP_PASSWORD
from thinkronos.adapters.db.engine import create_engine
from thinkronos.application.workspaces import CreateWorkspace, CreateWorkspaceCommand
from thinkronos.bootstrap import Settings, build_uow, build_worker_services
from thinkronos.worker.app import RENAME_WORKSPACE, create_celery
from thinkronos.worker.async_runner import AsyncMode, PerProcessLoop, create_runner

pytestmark = pytest.mark.integration

COUNT_APP_CONNECTIONS = (
    "SELECT count(*) FROM pg_stat_activity WHERE usename = 'thinkronos_app' AND pid <> pg_backend_pid()"
)


async def _query(url: str, sql: str) -> object:
    engine = create_engine(url, pooled=False)
    try:
        async with engine.connect() as conn:
            return (await conn.execute(text(sql))).scalar()
    finally:
        await engine.dispose()


async def _create(app_url: str, user: object, ws: object) -> None:
    engine = create_engine(app_url, pooled=False)
    try:
        cmd = CreateWorkspaceCommand(user, frozenset({ws}), ws, "元の名前")  # type: ignore[arg-type]
        await CreateWorkspace(build_uow(engine))(cmd)
    finally:
        await engine.dispose()


@pytest.mark.parametrize("mode", ["run", "runner"])
def test_rename_in_worker_against_db(mode: AsyncMode, migrated: str, app_url: str) -> None:
    assert APP_PASSWORD in app_url
    user, ws = uuid4(), uuid4()
    asyncio.run(_create(app_url, user, ws))
    before = asyncio.run(_query(migrated, COUNT_APP_CONNECTIONS))

    settings = Settings(database_url=app_url, worker_async_mode=mode, telemetry_export=False)
    services = build_worker_services(settings)
    runner = create_runner(mode)
    app = create_celery(lambda: services, runner, broker_url="memory://", result_backend="cache+memory://")
    args = [str(user), [str(ws)], str(ws)]
    with start_worker(app, pool="solo", perform_ping_check=False):
        results = [app.send_task(RENAME_WORKSPACE, args=[*args, f"名前{i}"]).get(timeout=30) for i in range(10)]
        during = asyncio.run(_query(migrated, COUNT_APP_CONNECTIONS))

    assert results[-1] == {"id": str(ws), "name": "名前9"}
    # 名前が本当に DB に入った（所有者は superuser なので RLS をバイパスして読める）
    assert asyncio.run(_query(migrated, f"SELECT name FROM workspaces WHERE id = '{ws}'")) == "名前9"
    assert isinstance(before, int)
    assert isinstance(during, int)
    if mode == "run":
        # A 案：NullPool なので、タスクが終われば接続は残らない（漏れない）
        assert during == before
    else:
        # B 案：プールの接続を使い回す（10件流しても増えるのは1本まで）
        assert during - before <= 1
        assert isinstance(runner, PerProcessLoop)
        runner.close()
