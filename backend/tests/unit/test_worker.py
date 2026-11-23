"""ワーカー（G-22）。memory:// のブローカーで、本物のワーカーをスレッドで起動して試す。"""

import asyncio
import io
import json
import logging
from collections.abc import Iterator
from uuid import UUID, uuid4

import pytest
from celery import Celery
from celery.contrib.testing.worker import start_worker

from thinkronos.adapters.observability import celery_signals, telemetry
from thinkronos.application.workspaces import RenameWorkspaceCommand, WorkspaceNotFound, WorkspaceView
from thinkronos.worker.app import RENAME_WORKSPACE, WorkerServices, create_celery
from thinkronos.worker.async_runner import AsyncMode, PerProcessLoop, PerTaskLoop, create_runner


class FlakyRename:
    """最初の fail_times 回は接続の失敗、それ以降は成功する。呼ばれたループも記録する。"""

    def __init__(self, fail_times: int = 0) -> None:
        self.fail_times = fail_times
        self.calls = 0
        self.loops: list[asyncio.AbstractEventLoop] = []  # 参照を持つので id は再利用されない

    async def __call__(self, command: RenameWorkspaceCommand) -> WorkspaceView:
        self.calls += 1
        self.loops.append(asyncio.get_running_loop())
        await asyncio.sleep(0)
        if self.calls <= self.fail_times:
            raise ConnectionError("db down")
        if command.workspace_id not in command.workspace_ids:
            raise WorkspaceNotFound(str(command.workspace_id))
        return WorkspaceView(id=command.workspace_id, name=command.name)


def _app(rename: FlakyRename, mode: AsyncMode) -> Celery:
    app = create_celery(
        lambda: WorkerServices(rename_workspace=rename),
        create_runner(mode),
        broker_url="memory://",
        result_backend="cache+memory://",
        retry_backoff=False,
        retry_delay=0,
    )
    celery_signals.connect()
    return app


@pytest.fixture
def log_lines() -> Iterator[io.StringIO]:
    telemetry.setup("worker-test", export=False)
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(telemetry.JsonFormatter("worker-test"))
    telemetry.get_logger().handlers = [handler]
    yield buf
    telemetry.request_id_var.set("-")


def _args(ws: UUID, name: str, member: bool = True) -> list[object]:
    return [str(uuid4()), [str(ws)] if member else [], str(ws), name]


@pytest.mark.parametrize("mode", ["run", "runner"])
def test_runs_async_use_case_in_worker(mode: AsyncMode, log_lines: io.StringIO) -> None:
    rename = FlakyRename()
    app = _app(rename, mode)
    ws = uuid4()
    token = telemetry.request_id_var.set("req-from-api")
    try:
        with start_worker(app, pool="solo", perform_ping_check=False):
            results = [app.send_task(RENAME_WORKSPACE, args=_args(ws, f"名前{i}")).get(timeout=10) for i in range(10)]
    finally:
        telemetry.request_id_var.reset(token)
    assert results[-1] == {"id": str(ws), "name": "名前9"}
    assert rename.calls == 10
    # A 案はタスクごとに別のループ、B 案は同じループを使い回す
    # A 案はタスクごとに別のループを作って閉じる。B 案は1つのループを使い回す
    unique = {id(loop) for loop in rename.loops}
    if mode == "run":
        assert len(unique) == 10
        assert all(loop.is_closed() for loop in rename.loops)
    else:
        assert len(unique) == 1
        assert not rename.loops[0].is_closed()
    # request_id がメッセージのヘッダでワーカーに引き継がれ、ログに出る
    records = [json.loads(line) for line in log_lines.getvalue().splitlines()]
    finished = [r for r in records if r["message"] == "task finished"]
    assert len(finished) == 10
    assert {r["request_id"] for r in finished} == {"req-from-api"}
    assert finished[0]["task"]["state"] == "SUCCESS"


def test_transient_errors_are_retried(log_lines: io.StringIO) -> None:
    rename = FlakyRename(fail_times=2)
    app = _app(rename, "run")
    ws = uuid4()
    with start_worker(app, pool="solo", perform_ping_check=False):
        result = app.send_task(RENAME_WORKSPACE, args=_args(ws, "x"))
        assert result.get(timeout=10)["name"] == "x"
    assert rename.calls == 3
    # リクエストの外から投入したタスクは、タスクIDを request_id にする
    records = [json.loads(line) for line in log_lines.getvalue().splitlines()]
    assert {r["request_id"] for r in records if r["message"] == "task finished"} == {result.id}


def test_not_found_is_not_retried(log_lines: io.StringIO) -> None:
    rename = FlakyRename()
    app = _app(rename, "run")
    with start_worker(app, pool="solo", perform_ping_check=False):
        result = app.send_task(RENAME_WORKSPACE, args=_args(uuid4(), "x", member=False))
        with pytest.raises(WorkspaceNotFound):
            result.get(timeout=10, propagate=True)
    assert rename.calls == 1


def test_runner_helpers() -> None:
    async def answer() -> int:
        return 42

    assert PerTaskLoop().run(answer()) == 42
    loop = PerProcessLoop()
    assert loop.run(answer()) == 42
    loop.close()
    loop.close()  # 2回閉じてもよい
    with pytest.raises(ValueError, match="unknown"):
        create_runner("threads")  # type: ignore[arg-type]
