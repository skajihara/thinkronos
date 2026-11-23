"""ワークスペースのユースケース。

api・worker は domain と ports を直接 import しないので、入力はコマンド、
出力は WorkspaceView（どちらもこのモジュールの型）でやり取りする。
"""

from dataclasses import dataclass
from uuid import UUID

from thinkronos.domain.actor import Actor
from thinkronos.domain.workspace import InvalidWorkspaceName, Workspace
from thinkronos.ports.unit_of_work import UnitOfWorkFactory

__all__ = [
    "CreateWorkspace",
    "CreateWorkspaceCommand",
    "InvalidWorkspaceName",
    "RenameWorkspace",
    "RenameWorkspaceCommand",
    "WorkspaceAlreadyExists",
    "WorkspaceNotFound",
    "WorkspaceView",
]


class WorkspaceNotFound(LookupError):
    """ワークスペースが無い、または操作する人から見えない（RLS で絞られた）。"""


class WorkspaceAlreadyExists(Exception):
    """同じ ID のワークスペースが既にある。"""


@dataclass(frozen=True, slots=True)
class WorkspaceView:
    id: UUID
    name: str

    @classmethod
    def of(cls, workspace: Workspace) -> "WorkspaceView":
        return cls(id=workspace.id, name=workspace.name)


@dataclass(frozen=True, slots=True)
class CreateWorkspaceCommand:
    user_id: UUID
    workspace_ids: frozenset[UUID]
    workspace_id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class RenameWorkspaceCommand:
    user_id: UUID
    workspace_ids: frozenset[UUID]
    workspace_id: UUID
    name: str


class CreateWorkspace:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    async def __call__(self, command: CreateWorkspaceCommand) -> WorkspaceView:
        workspace = Workspace(id=command.workspace_id, name=command.name)
        async with self._uow(Actor(command.user_id, command.workspace_ids)) as uow:
            if await uow.workspaces.get(workspace.id) is not None:
                raise WorkspaceAlreadyExists(str(workspace.id))
            await uow.workspaces.add(workspace)
        return WorkspaceView.of(workspace)


class RenameWorkspace:
    """名前を変える。ワーカーで非同期に実行する最初のユースケース（G-22 の確認用）。"""

    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    async def __call__(self, command: RenameWorkspaceCommand) -> WorkspaceView:
        async with self._uow(Actor(command.user_id, command.workspace_ids)) as uow:
            current = await uow.workspaces.get(command.workspace_id)
            if current is None:
                raise WorkspaceNotFound(str(command.workspace_id))
            renamed = current.renamed(command.name)
            await uow.workspaces.save(renamed)
        return WorkspaceView.of(renamed)
