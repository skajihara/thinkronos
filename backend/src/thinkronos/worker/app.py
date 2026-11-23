"""Celery のアプリとタスク。組み立ては thinkronos.bootstrap で行う。

worker は application だけを import する（実装規約 3.1、.importlinter）。
タスクは薄いアダプター：引数（JSON）をコマンドに直し、async のユースケースを実行する。
"""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from celery import Celery

from thinkronos.application.workspaces import (
    InvalidWorkspaceName,
    RenameWorkspaceCommand,
    WorkspaceNotFound,
    WorkspaceView,
)
from thinkronos.worker.async_runner import AsyncRunner

RENAME_WORKSPACE = "workspaces.rename"

# 一時的な障害（接続の失敗など）だけ再試行する。入力の誤りや見えない行は再試行しない
RETRYABLE: tuple[type[BaseException], ...] = (ConnectionError, OSError, TimeoutError)
NOT_RETRYABLE: tuple[type[BaseException], ...] = (WorkspaceNotFound, InvalidWorkspaceName)


@dataclass(frozen=True, slots=True)
class WorkerServices:
    rename_workspace: Callable[[RenameWorkspaceCommand], Coroutine[Any, Any, WorkspaceView]]


def create_celery(
    services: Callable[[], WorkerServices],
    runner: AsyncRunner,
    *,
    broker_url: str,
    result_backend: str | None,
    max_retries: int = 3,
    retry_backoff: bool | int = True,
    retry_delay: int = 1,
) -> Celery:
    """services はプロセスの中で最初のタスクのときに呼ばれる（fork の後に接続を作るため）。"""
    app = Celery("thinkronos", broker=broker_url, backend=result_backend)
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        broker_connection_retry_on_startup=True,
        result_expires=3600,
        timezone="UTC",
        enable_utc=True,
        # 標準出力を Celery のロガーに回さない（回すと1行1JSONのログに「WARNING/ForkPoolWorker」が前置される）
        worker_redirect_stdouts=False,
    )

    @app.task(  # type: ignore[untyped-decorator]
        name=RENAME_WORKSPACE,
        shared=False,  # このアプリにだけ登録する（既定ではプロセス内のすべての Celery アプリに共有される）
        autoretry_for=RETRYABLE,
        dont_autoretry_for=NOT_RETRYABLE,
        retry_backoff=retry_backoff,
        retry_jitter=False,
        default_retry_delay=retry_delay,  # retry_backoff が False のときの待ち時間（秒）
        max_retries=max_retries,
    )
    def rename_workspace(user_id: str, workspace_ids: list[str], workspace_id: str, name: str) -> dict[str, Any]:
        command = RenameWorkspaceCommand(
            user_id=UUID(user_id),
            workspace_ids=frozenset(UUID(w) for w in workspace_ids),
            workspace_id=UUID(workspace_id),
            name=name,
        )
        view = runner.run(services().rename_workspace(command))
        return {"id": str(view.id), "name": view.name}

    return app
