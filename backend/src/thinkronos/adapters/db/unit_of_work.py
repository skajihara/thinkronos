"""Unit of Work の SQLAlchemy 実装（D-19、D-14）。

トランザクションの最初に `set_config(..., is_local => true)` で
`app.user_id` と `app.workspace_ids` を設定する。is_local が true なので、値は
そのトランザクションの間だけ有効で、接続をプールで使い回しても次に漏れない。
RLS のポリシー（migrations/）はこの値を読む。

接続するロールはテーブルの所有者ではない専用のロール（thinkronos_app）にする。
所有者・スーパーユーザー・BYPASSRLS のロールでは RLS が効かないため。
"""

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from thinkronos.adapters.db.models import WorkspaceRow
from thinkronos.domain.actor import Actor
from thinkronos.domain.workspace import Workspace
from thinkronos.ports.unit_of_work import UnitOfWork

_SET_CONTEXT = text(
    "SELECT set_config('app.user_id', :user_id, true), set_config('app.workspace_ids', :workspace_ids, true)"
)


def _to_domain(row: WorkspaceRow) -> Workspace:
    return Workspace(id=row.id, name=row.name)


class SqlAlchemyWorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, workspace: Workspace) -> None:
        self._session.add(WorkspaceRow(id=workspace.id, name=workspace.name))
        await self._session.flush()

    async def get(self, workspace_id: UUID) -> Workspace | None:
        row = await self._session.get(WorkspaceRow, workspace_id)
        return None if row is None else _to_domain(row)

    async def list(self) -> Sequence[Workspace]:
        rows = await self._session.scalars(select(WorkspaceRow).order_by(WorkspaceRow.created_at, WorkspaceRow.id))
        return [_to_domain(r) for r in rows]

    async def save(self, workspace: Workspace) -> None:
        await self._session.execute(
            update(WorkspaceRow)
            .where(WorkspaceRow.id == workspace.id)
            .values(name=workspace.name)
            .execution_options(synchronize_session="fetch")
        )


class SqlAlchemyUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._workspaces = SqlAlchemyWorkspaceRepository(session)

    @property
    def workspaces(self) -> SqlAlchemyWorkspaceRepository:
        return self._workspaces


class SqlAlchemyUnitOfWorkFactory:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    @asynccontextmanager
    async def __call__(self, actor: Actor) -> AsyncIterator[UnitOfWork]:
        async with self._sessions() as session, session.begin():
            await session.execute(
                _SET_CONTEXT,
                {
                    "user_id": str(actor.user_id),
                    # 区切りは「,」。並びを固定して、ログやテストで比べやすくする
                    "workspace_ids": ",".join(sorted(str(w) for w in actor.workspace_ids)),
                },
            )
            yield SqlAlchemyUnitOfWork(session)
