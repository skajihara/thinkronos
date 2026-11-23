"""手元で使うコマンド（デモ用のシード、エージェントとワーカーの確認）。

  python -m thinkronos.cli seed                         デモ用のシードを入れる（D-08。何度実行してもよい）
  python -m thinkronos.cli suggest [テーマ]             エージェントで子ノードを提案する（make agent-smoke）
  python -m thinkronos.cli rename <id> <名前>           ワーカーで名前を変える（非同期のユースケースの確認）

cli は bootstrap と application だけを import する（.importlinter）。
"""

import argparse
import asyncio
import json
import sys
from uuid import UUID

from thinkronos import bootstrap
from thinkronos.application.workspaces import CreateWorkspaceCommand, WorkspaceAlreadyExists

# デモ用のシード。テスト用のデータ（tests/factories）とは別に持つ（D-08）
DEMO_USER_ID = UUID("00000000-0000-7000-8000-000000000001")
DEMO_WORKSPACES = {
    UUID("00000000-0000-7000-8000-0000000000a1"): "個人",
    UUID("00000000-0000-7000-8000-0000000000a2"): "チーム",
}
DEFAULT_THEME = "週末の旅行の計画"


async def seed() -> list[str]:
    create = bootstrap.build_create_workspace(bootstrap.settings())
    ids = frozenset(DEMO_WORKSPACES)
    lines = []
    for workspace_id, name in DEMO_WORKSPACES.items():
        try:
            await create(CreateWorkspaceCommand(DEMO_USER_ID, ids, workspace_id, name))
            lines.append(f"created {workspace_id} {name}")
        except WorkspaceAlreadyExists:
            lines.append(f"exists  {workspace_id} {name}")
    return lines


async def suggest(theme: str) -> list[str]:
    return list(await bootstrap.build_suggest_child_nodes(bootstrap.settings())(theme))


def rename(workspace_id: str, name: str) -> object:
    from thinkronos.worker.app import RENAME_WORKSPACE

    app = bootstrap.celery_app
    ids = [str(w) for w in DEMO_WORKSPACES]
    result = app.send_task(RENAME_WORKSPACE, args=[str(DEMO_USER_ID), ids, workspace_id, name])
    return result.get(timeout=60)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="thinkronos.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed")
    p_suggest = sub.add_parser("suggest")
    p_suggest.add_argument("theme", nargs="?", default=DEFAULT_THEME)
    p_rename = sub.add_parser("rename")
    p_rename.add_argument("workspace_id")
    p_rename.add_argument("name")
    args = parser.parse_args(argv)

    if args.command == "seed":
        print("\n".join(asyncio.run(seed())))
    elif args.command == "suggest":
        print(json.dumps({"theme": args.theme, "titles": asyncio.run(suggest(args.theme))}, ensure_ascii=False))
    else:
        print(json.dumps(rename(args.workspace_id, args.name), ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
