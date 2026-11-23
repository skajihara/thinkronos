from uuid import uuid4

import pytest

from tests.factories.workspaces import new_workspace
from tests.fakes import InMemoryUnitOfWorkFactory, StubProbe, StubSuggester
from thinkronos.application.health import CheckHealth
from thinkronos.application.suggestions import MAX_SUGGESTIONS, SuggestChildNodes
from thinkronos.application.workspaces import (
    CreateWorkspace,
    CreateWorkspaceCommand,
    InvalidWorkspaceName,
    RenameWorkspace,
    RenameWorkspaceCommand,
    WorkspaceAlreadyExists,
    WorkspaceNotFound,
)
from thinkronos.domain.workspace import NAME_MAX_LENGTH, Workspace


class TestWorkspace:
    def test_name_is_trimmed(self) -> None:
        assert Workspace(id=uuid4(), name="  個人  ").name == "個人"

    @pytest.mark.parametrize("name", ["", "   ", "a" * (NAME_MAX_LENGTH + 1)])
    def test_invalid_names(self, name: str) -> None:
        with pytest.raises(InvalidWorkspaceName):
            Workspace(id=uuid4(), name=name)

    def test_renamed_keeps_id_and_validates(self) -> None:
        w = new_workspace()
        assert w.renamed("新しい名前") == Workspace(id=w.id, name="新しい名前")
        with pytest.raises(InvalidWorkspaceName):
            w.renamed(" ")


async def test_check_health() -> None:
    assert (await CheckHealth(StubProbe(True))()).ok
    assert not (await CheckHealth(StubProbe(False))()).ok


class TestWorkspaceUseCases:
    async def test_create_then_rename(self) -> None:
        uow = InMemoryUnitOfWorkFactory()
        user, ws = uuid4(), uuid4()
        created = await CreateWorkspace(uow)(CreateWorkspaceCommand(user, frozenset({ws}), ws, "個人"))
        renamed = await RenameWorkspace(uow)(RenameWorkspaceCommand(user, frozenset({ws}), ws, "仕事"))
        assert (created.name, renamed.name) == ("個人", "仕事")
        assert uow.rows[ws].name == "仕事"
        assert {a.user_id for a in uow.actors} == {user}  # UoW には必ず actor が渡る

    async def test_create_twice(self) -> None:
        uow = InMemoryUnitOfWorkFactory()
        user, ws = uuid4(), uuid4()
        command = CreateWorkspaceCommand(user, frozenset({ws}), ws, "個人")
        await CreateWorkspace(uow)(command)
        with pytest.raises(WorkspaceAlreadyExists):
            await CreateWorkspace(uow)(command)

    async def test_rename_invisible_workspace(self) -> None:
        uow = InMemoryUnitOfWorkFactory()
        user, ws = uuid4(), uuid4()
        await CreateWorkspace(uow)(CreateWorkspaceCommand(user, frozenset({ws}), ws, "個人"))
        with pytest.raises(WorkspaceNotFound):
            await RenameWorkspace(uow)(RenameWorkspaceCommand(user, frozenset({uuid4()}), ws, "仕事"))
        assert uow.rows[ws].name == "個人"

    async def test_invalid_name_rolls_back(self) -> None:
        uow = InMemoryUnitOfWorkFactory()
        user, ws = uuid4(), uuid4()
        await CreateWorkspace(uow)(CreateWorkspaceCommand(user, frozenset({ws}), ws, "個人"))
        with pytest.raises(InvalidWorkspaceName):
            await RenameWorkspace(uow)(RenameWorkspaceCommand(user, frozenset({ws}), ws, ""))
        assert uow.rows[ws].name == "個人"


class TestSuggestChildNodes:
    async def test_cleans_llm_output(self) -> None:
        suggester = StubSuggester([" 宿 ", "交通", "宿", "", "予算", "持ち物"])
        titles = await SuggestChildNodes(suggester)(" 旅行 ", count=3)
        assert titles == ["宿", "交通", "予算"]
        assert suggester.calls == [("旅行", 3)]

    async def test_count_is_clamped(self) -> None:
        suggester = StubSuggester([])
        await SuggestChildNodes(suggester)("旅行", count=100)
        await SuggestChildNodes(suggester)("旅行", count=0)
        assert [c for _, c in suggester.calls] == [MAX_SUGGESTIONS, 1]

    async def test_empty_theme(self) -> None:
        with pytest.raises(ValueError, match="テーマ"):
            await SuggestChildNodes(StubSuggester([]))("  ")
