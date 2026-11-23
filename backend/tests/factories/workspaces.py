"""テストデータのファクトリ（D-08、ADR 0035）。

factory_boy はオブジェクト（domain のエンティティ）を作るだけにする。
保存は UoW を通す（RLS の文脈を必ず通すため。factory_boy の SQLAlchemy 連携は async に対応しない）。
factory_boy は型が付いていないので、テストからは型付きの関数（new_workspace など）で使う。
"""

from typing import Any
from uuid import uuid4

import factory

from thinkronos.domain.actor import Actor
from thinkronos.domain.workspace import Workspace
from thinkronos.ports.unit_of_work import UnitOfWorkFactory


class WorkspaceFactory(factory.Factory[Workspace]):
    class Meta:
        model = Workspace

    id = factory.LazyFunction(uuid4)
    name = factory.Sequence(lambda n: f"ワークスペース{n}")


class ActorFactory(factory.Factory[Actor]):
    class Meta:
        model = Actor

    user_id = factory.LazyFunction(uuid4)
    workspace_ids: frozenset[Any] = frozenset()


def new_workspace(**overrides: Any) -> Workspace:
    return WorkspaceFactory.build(**overrides)


def new_actor(**overrides: Any) -> Actor:
    return ActorFactory.build(**overrides)


def actor_for(*workspaces: Workspace) -> Actor:
    """指定したワークスペースに所属する人。"""
    return new_actor(workspace_ids=frozenset(w.id for w in workspaces))


async def persist(uow: UnitOfWorkFactory, *workspaces: Workspace) -> None:
    """ワークスペースを保存する。所属する人の文脈で UoW を通す。"""
    async with uow(actor_for(*workspaces)) as u:
        for w in workspaces:
            await u.workspaces.add(w)
