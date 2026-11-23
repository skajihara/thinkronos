"""openapi.json を書き出す（make gen-openapi、C-28）。DB などには接続しない。

使い方：python -m thinkronos.api.openapi <出力先>
"""

import json
import sys
from pathlib import Path
from typing import Any

from thinkronos.api.app import ApiServices, create_app
from thinkronos.application.health import HealthStatus


async def _unavailable() -> HealthStatus:  # pragma: no cover - スキーマの生成だけで、呼ばれない
    raise RuntimeError("openapi の生成専用")


def build_schema() -> dict[str, Any]:
    return create_app(ApiServices(check_health=_unavailable)).openapi()


def render() -> str:
    # 差分を安定させるため、キーの順序を固定し、末尾に改行を1つ付ける
    return json.dumps(build_schema(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: python -m thinkronos.api.openapi <output>", file=sys.stderr)
        return 2
    Path(argv[0]).write_text(render(), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
