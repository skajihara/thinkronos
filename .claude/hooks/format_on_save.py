"""PostToolUse フック（Edit|Write）：保存したファイルを整える。

共通の整形：末尾空白の除去（Markdown は行末の半角スペース2つを残す）、末尾に改行1つ、改行をLFに。
言語ごとの整形ツールは FORMATTERS に足す。コマンドが未導入なら黙って飛ばす。
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

# 拡張子 -> 整形コマンド（{file} を置き換える）。ツールを入れたらここに足す。
# 例：".py": ["ruff", "format", "{file}"], ".ts": ["npx", "--no-install", "prettier", "--write", "{file}"]
FORMATTERS = {}

TEXT_EXT = {".md", ".yml", ".yaml", ".json", ".py", ".sql", ".toml", ".ts", ".tsx", ".js", ".css", ".html"}


def basic_format(path):
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    keep_break = path.suffix == ".md"
    out = []
    for line in lines:
        if keep_break and line.endswith("  ") and line.strip():
            out.append(line.rstrip() + "  ")
        else:
            out.append(line.rstrip())
    result = "\n".join(out).rstrip("\n") + "\n"
    if result.encode("utf-8") != raw:
        path.write_bytes(result.encode("utf-8"))


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    file_path = (data.get("tool_input") or {}).get("file_path")
    if not file_path:
        return 0
    path = Path(file_path)
    if not path.is_file() or path.suffix not in TEXT_EXT:
        return 0
    basic_format(path)
    cmd = FORMATTERS.get(path.suffix)
    if cmd and shutil.which(cmd[0]):
        subprocess.run([c.replace("{file}", str(path)) for c in cmd], capture_output=True, timeout=60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
