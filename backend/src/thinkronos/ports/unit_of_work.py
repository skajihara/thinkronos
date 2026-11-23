"""Unit of Work とリポジトリのポート（D-19）。

`async with uow_factory(actor) as uow:` の中が1つのトランザクションになる。
実装は、トランザクションの最初に actor（user_id と所属ワークスペースの一覧）を
DB のセッションに設定し、RLS がそれを使って行を絞る。
ブロックを正常に抜けるとコミット、例外で抜けるとロールバックする。
"""

from collections.abc import Sequence
from contextlib import AbstractAsyncContextManager
from typing import Protocol
from uuid import UUID

from thinkronos.domain.actor import Actor
from thinkronos.domain.workspace import Workspace


class WorkspaceRepository(Protocol):
    async def add(self, workspace: Workspace) -> None: ...

    async def get(self, workspace_id: UUID) -> Workspace | None: ...

    async def list(self) -> Sequence[Workspace]: ...

    async def save(self, workspace: Workspace) -> None: ...


class UnitOfWork(Protocol):
    @property
    def workspaces(self) -> WorkspaceRepository: ...


class UnitOfWorkFactory(Protocol):
    def __call__(self, actor: Actor) -> AbstractAsyncContextManager[UnitOfWork]: ...
