"""Celery の同期タスクから async のユースケースを実行する方法（G-22、ADR 0005）。

- "run"（A 案、既定）：タスクごとに asyncio.run で新しいイベントループを作って閉じる。
  DB の接続はループに結び付くので、エンジンは NullPool にする（bootstrap が選ぶ）。
- "runner"（B 案）：ワーカーのプロセスごとに asyncio.Runner を1つ持ち、ループを使い回す。
  接続をプールで使い回せる。ループは最初のタスクで作る（prefork の fork の後）。
"""

import asyncio
import threading
from collections.abc import Coroutine
from typing import Any, Literal, Protocol, TypeVar

T = TypeVar("T")
AsyncMode = Literal["run", "runner"]


class AsyncRunner(Protocol):
    def run(self, coro: Coroutine[Any, Any, T]) -> T: ...


class PerTaskLoop:
    """A 案。"""

    def run(self, coro: Coroutine[Any, Any, T]) -> T:
        return asyncio.run(coro)


class PerProcessLoop:
    """B 案。同じプロセスの中では1つのループを使い回す。"""

    def __init__(self) -> None:
        self._runner: asyncio.Runner | None = None
        self._lock = threading.Lock()

    def run(self, coro: Coroutine[Any, Any, T]) -> T:
        with self._lock:  # 1つのループに同時に2つの run は入れない
            if self._runner is None:
                self._runner = asyncio.Runner()
            return self._runner.run(coro)

    def close(self) -> None:
        with self._lock:
            if self._runner is not None:
                self._runner.close()
                self._runner = None


def create_runner(mode: AsyncMode) -> PerTaskLoop | PerProcessLoop:
    if mode == "run":
        return PerTaskLoop()
    if mode == "runner":
        return PerProcessLoop()
    raise ValueError(f"unknown async mode: {mode}")
