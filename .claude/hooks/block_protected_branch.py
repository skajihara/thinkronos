"""PreToolUse hook (Bash): block direct changes to main/develop, merges and issue closing.

- Blocks git commit / push / merge on main or develop.
- Blocks merging a PR and closing an issue (gh pr merge, gh issue close, and the
  equivalent gh api calls). These happen only after Shingo has reviewed the PR.

Exits with code 2 and writes the reason to stderr. Lets the command through when unsure.
"""
import json
import re
import subprocess
import sys

PROTECTED = {"main", "develop"}
WRITE_CMD = re.compile(r"\bgit\b(?:\s+-\S+(?:\s+\S+)?)*\s+(commit|push|merge)\b")
PUSH_TO_PROTECTED = re.compile(r"\bgit\s+push\b[^;&|\n]*[\s:](main|develop)\b")
MERGE_OR_CLOSE = [
    re.compile(r"\bgh\s+pr\s+merge\b"),
    re.compile(r"\bgh\s+issue\s+close\b"),
    re.compile(r"\bgh\s+api\b[^;&|\n]*/pulls/\d+/merge\b"),
    re.compile(r"\bgh\s+api\b[^;&|\n]*/issues/\d+\b[^;&|\n]*\bstate=closed\b"),
]


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
    if any(p.search(command) for p in MERGE_OR_CLOSE):
        print(
            "PRのマージとIssueのクローズは行わない規則です（CLAUDE.md）。"
            "PRを作ったら「## 結果」をIssueにコメントして止まってください。",
            file=sys.stderr,
        )
        return 2
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
