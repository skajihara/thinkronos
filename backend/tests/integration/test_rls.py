"""Unit of Work と RLS（D-19、D-14、I-01）。別のワークスペースの行が見えないこと。"""

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.factories.workspaces import actor_for, new_actor, new_workspace, persist
from thinkronos.adapters.db.unit_of_work import SqlAlchemyUnitOfWorkFactory
from thinkronos.adapters.db.unit_of_work import SqlAlchemyWorkspaceRepository as Repo
from thinkronos.domain.actor import Actor

pytestmark = pytest.mark.integration


async def test_only_own_workspaces_are_visible(uow: SqlAlchemyUnitOfWorkFactory) -> None:
    a, b = new_workspace(), new_workspace()
    await persist(uow, a)
    await persist(uow, b)

    async with uow(actor_for(a)) as u:
        assert [w.id for w in await u.workspaces.list()] == [a.id]
        assert await u.workspaces.get(a.id) == a
        assert await u.workspaces.get(b.id) is None  # ①② B は見えない

    async with uow(actor_for(a, b)) as u:  # 両方に所属していれば両方見える
        assert {w.id for w in await u.workspaces.list()} >= {a.id, b.id}


async def test_cannot_update_other_workspace(uow: SqlAlchemyUnitOfWorkFactory, owner_engine: AsyncEngine) -> None:
    a, b = new_workspace(), new_workspace(name="元の名前")
    await persist(uow, a)
    await persist(uow, b)

    async with uow(actor_for(a)) as u:
        await u.workspaces.save(b.renamed("書き換え"))  # ② 見えない行は更新されない（0行）

    async with uow(actor_for(b)) as u:
        current = await u.workspaces.get(b.id)
    assert current is not None
    assert current.name == "元の名前"


async def test_cannot_insert_into_other_workspace(uow: SqlAlchemyUnitOfWorkFactory) -> None:
    a, other = new_workspace(), new_workspace()
    with pytest.raises(DBAPIError, match="row-level security"):  # ② WITH CHECK で拒否される
        async with uow(actor_for(a)) as u:
            await u.workspaces.add(other)


async def test_no_context_sees_nothing(uow: SqlAlchemyUnitOfWorkFactory, app_engine: AsyncEngine) -> None:
    a = new_workspace()
    await persist(uow, a)
    async with uow(new_actor()) as u:  # 所属なし
        assert await u.workspaces.list() == []
    async with app_engine.connect() as conn:  # ③ UoW を通さない（文脈が未設定）
        assert (await conn.execute(text("SELECT count(*) FROM workspaces"))).scalar_one() == 0


async def test_context_does_not_leak_between_transactions(app_engine: AsyncEngine) -> None:
    """④ is_local なので、同じ接続を使い回しても次のトランザクションに設定が残らない。"""
    a = new_workspace()
    async with app_engine.connect() as conn:
        async with conn.begin():
            await conn.execute(
                text("SELECT set_config('app.workspace_ids', :w, true)"),
                {"w": str(a.id)},
            )
            inside = (await conn.execute(text("SELECT current_setting('app.workspace_ids', true)"))).scalar_one()
        after = (await conn.execute(text("SELECT current_setting('app.workspace_ids', true)"))).scalar_one()
    assert inside == str(a.id)
    assert after in (None, "")  # 一度設定された名前は、未設定のとき空文字になる（PostgreSQL の仕様）


async def test_uow_sets_actor_context(uow: SqlAlchemyUnitOfWorkFactory) -> None:
    w1, w2 = uuid4(), uuid4()
    actor = Actor(user_id=uuid4(), workspace_ids=frozenset({w1, w2}))
    async with uow(actor) as u:
        assert isinstance(u.workspaces, Repo)
        session = u.workspaces._session
        row = (
            await session.execute(text("SELECT app_current_user_id(), app_current_workspace_ids(), current_user"))
        ).one()
    assert row[0] == actor.user_id
    assert set(row[1]) == {w1, w2}
    assert row[2] == "thinkronos_app"


async def test_app_role_is_not_owner_and_cannot_bypass(owner_engine: AsyncEngine) -> None:
    """⑤ アプリのロールはテーブルの所有者ではなく、RLS をバイパスできない。"""
    async with owner_engine.connect() as conn:
        owner = (
            await conn.execute(text("SELECT tableowner FROM pg_tables WHERE tablename = 'workspaces'"))
        ).scalar_one()
        role = (
            await conn.execute(
                text("SELECT rolsuper, rolbypassrls, rolcreaterole FROM pg_roles WHERE rolname = 'thinkronos_app'")
            )
        ).one()
        rls = (
            await conn.execute(
                text("SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = 'workspaces'")
            )
        ).one()
    assert owner != "thinkronos_app"
    assert tuple(role) == (False, False, False)
    assert tuple(rls) == (True, True)
