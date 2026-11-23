"""ユニットテスト用の偽のアダプター。RLS の振る舞い（所属するワークスペースだけ見える）を真似る。"""

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from uuid import UUID

from thinkronos.domain.actor import Actor
from thinkronos.domain.workspace import Workspace


class InMemoryWorkspaceRepository:
    def __init__(self, rows: dict[UUID, Workspace], actor: Actor) -> None:
        self._rows = rows
        self._actor = actor

    def _visible(self, workspace_id: UUID) -> bool:
        return workspace_id in self._actor.workspace_ids

    async def add(self, workspace: Workspace) -> None:
        if not self._visible(workspace.id):
            raise PermissionError("row-level security")
        self._rows[workspace.id] = workspace

    async def get(self, workspace_id: UUID) -> Workspace | None:
        return self._rows.get(workspace_id) if self._visible(workspace_id) else None

    async def list(self) -> Sequence[Workspace]:
        return [w for w in self._rows.values() if self._visible(w.id)]

    async def save(self, workspace: Workspace) -> None:
        if self._visible(workspace.id) and workspace.id in self._rows:
            self._rows[workspace.id] = workspace


class InMemoryUnitOfWork:
    def __init__(self, repo: InMemoryWorkspaceRepository) -> None:
        self._repo = repo

    @property
    def workspaces(self) -> InMemoryWorkspaceRepository:
        return self._repo


class InMemoryUnitOfWorkFactory:
    """コミットは正常に抜けたときだけ反映する（例外ならロールバック）。"""

    def __init__(self) -> None:
        self.rows: dict[UUID, Workspace] = {}
        self.actors: list[Actor] = []

    @asynccontextmanager
    async def __call__(self, actor: Actor) -> AsyncIterator[InMemoryUnitOfWork]:
        self.actors.append(actor)
        staged = dict(self.rows)
        yield InMemoryUnitOfWork(InMemoryWorkspaceRepository(staged, actor))
        self.rows = staged


class StubProbe:
    def __init__(self, ok: bool) -> None:
        self.ok = ok

    async def ping(self) -> bool:
        return self.ok


class StubSuggester:
    def __init__(self, titles: Sequence[str]) -> None:
        self.titles = titles
        self.calls: list[tuple[str, int]] = []

    async def suggest_children(self, theme: str, *, count: int) -> Sequence[str]:
        self.calls.append((theme, count))
        return self.titles
