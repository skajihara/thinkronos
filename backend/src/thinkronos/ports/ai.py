"""LLM のポート（AI-01 の最小形）。日付は扱わない（ADR 0032）。"""

from collections.abc import Sequence
from typing import Protocol


class NodeSuggester(Protocol):
    async def suggest_children(self, theme: str, *, count: int) -> Sequence[str]:
        """テーマから、子ノードのタイトルの候補を返す。"""
        ...
