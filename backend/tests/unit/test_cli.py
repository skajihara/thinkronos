"""手元のコマンド（thinkronos.cli）。bootstrap の組み立てを偽物に差し替えて試す。"""

import json
from typing import Any

import pytest

from tests.fakes import InMemoryUnitOfWorkFactory, StubSuggester
from thinkronos import bootstrap, cli
from thinkronos.application.suggestions import SuggestChildNodes
from thinkronos.application.workspaces import CreateWorkspace


@pytest.fixture(autouse=True)
def _settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bootstrap, "settings", lambda: bootstrap.Settings(database_url="postgresql+asyncpg://x/y"))


def test_seed_is_idempotent(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    uow = InMemoryUnitOfWorkFactory()
    monkeypatch.setattr(bootstrap, "build_create_workspace", lambda s: CreateWorkspace(uow))
    assert cli.main(["seed"]) == 0
    assert cli.main(["seed"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert [line.split()[0] for line in out] == ["created", "created", "exists", "exists"]
    assert {w.name for w in uow.rows.values()} == set(cli.DEMO_WORKSPACES.values())


def test_suggest(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    suggester = StubSuggester(["宿", "交通"])
    monkeypatch.setattr(bootstrap, "build_suggest_child_nodes", lambda s: SuggestChildNodes(suggester))
    assert cli.main(["suggest"]) == 0
    assert json.loads(capsys.readouterr().out) == {"theme": cli.DEFAULT_THEME, "titles": ["宿", "交通"]}


def test_rename_sends_task(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    sent: list[tuple[str, list[Any]]] = []

    class Result:
        def get(self, timeout: int) -> dict[str, str]:
            return {"id": "w", "name": "n"}

    class App:
        def send_task(self, name: str, args: list[Any]) -> Result:
            sent.append((name, args))
            return Result()

    monkeypatch.setattr(bootstrap, "_celery_app", lambda: App())
    assert cli.main(["rename", "w", "n"]) == 0
    assert json.loads(capsys.readouterr().out) == {"id": "w", "name": "n"}
    assert sent[0][0] == "workspaces.rename"
    assert sent[0][1][2:] == ["w", "n"]


def test_bootstrap_unknown_attribute() -> None:
    with pytest.raises(AttributeError):
        bootstrap.__getattr__("nope")
