"""Celery のタスクへの request_id の引き継ぎと、タスクの構造化ログ。

- タスクを投入するとき、今の request_id をメッセージのヘッダ（x_request_id）に入れる。
- ワーカーでタスクを始めるとき、ヘッダの値を request_id_var に入れる。ログに出る。
"""

import time
from typing import Any

from celery import signals

from thinkronos.adapters.observability import telemetry

HEADER = "x_request_id"
_started: dict[str, float] = {}


def _on_publish(headers: dict[str, Any] | None = None, **_: Any) -> None:
    rid = telemetry.request_id_var.get()
    # リクエストの外（CLI・beat）から投入したときは付けない。ワーカーでタスクIDを使う
    if headers is not None and HEADER not in headers and rid != "-":
        headers[HEADER] = rid


def _on_prerun(task_id: str, task: Any, **_: Any) -> None:
    rid = getattr(task.request, HEADER, None) or (task.request.headers or {}).get(HEADER) or task_id
    telemetry.request_id_var.set(str(rid))
    _started[task_id] = time.perf_counter()
    telemetry.get_logger().info("task started", extra={"fields": {"task": {"name": task.name, "id": task_id}}})


def _on_postrun(task_id: str, task: Any, state: str | None = None, **_: Any) -> None:
    started = _started.pop(task_id, None)
    ms = None if started is None else round((time.perf_counter() - started) * 1000, 2)
    telemetry.get_logger().info(
        "task finished",
        extra={"fields": {"task": {"name": task.name, "id": task_id, "state": state, "duration_ms": ms}}},
    )
    telemetry.request_id_var.set("-")


def connect() -> None:
    """シグナルにつなぐ（何度呼んでも1回だけつながる。weak=False で関数を保持する）。"""
    signals.before_task_publish.connect(_on_publish, weak=False, dispatch_uid="thinkronos.publish")
    signals.task_prerun.connect(_on_prerun, weak=False, dispatch_uid="thinkronos.prerun")
    signals.task_postrun.connect(_on_postrun, weak=False, dispatch_uid="thinkronos.postrun")
