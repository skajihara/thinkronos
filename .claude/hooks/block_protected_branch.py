"""PreToolUse フック（Bash）：main / develop 上の git commit / push / merge を止める。

終了コード2で止め、理由を標準エラーに出す。判断できないときは止めない。
"""
import json
import re
import subprocess
import sys

PROTECTED = {"main", "develop"}
WRITE_CMD = re.compile(r"\bgit\b(?:\s+-\S+(?:\s+\S+)?)*\s+(commit|push|merge)\b")
PUSH_TO_PROTECTED = re.compile(r"\bgit\s+push\b[^;&|\n]*[\s:](main|develop)\b")


def current_branch(cwd):
    try:
        out = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=cwd or None, capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip()
    except Exception:
        return ""


def main():
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    command = (data.get("tool_input") or {}).get("command", "")
    if not WRITE_CMD.search(command):
        return 0
    branch = current_branch(data.get("cwd"))
    if branch in PROTECTED or PUSH_TO_PROTECTED.search(command):
        print(
            f"main/develop は直接変更しない規則です（現在のブランチ：'{branch}'）。"
            "PRを通してのみ変更できます。"
            "feature/<Issue番号>-<名前> のブランチを切ってから作業してください。",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
