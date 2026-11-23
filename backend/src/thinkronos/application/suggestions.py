"""子ノードの提案（AI-01 の最小形）。"""

from collections.abc import Sequence

from thinkronos.ports.ai import NodeSuggester

MAX_SUGGESTIONS = 10


class SuggestChildNodes:
    def __init__(self, suggester: NodeSuggester) -> None:
        self._suggester = suggester

    async def __call__(self, theme: str, *, count: int = 5) -> Sequence[str]:
        theme = theme.strip()
        if not theme:
            raise ValueError("テーマが空です")
        count = max(1, min(count, MAX_SUGGESTIONS))
        titles = await self._suggester.suggest_children(theme, count=count)
        # LLM の出力は信用しない：空白を除き、重複と空を落とし、件数を揃える
        seen: list[str] = []
        for title in (t.strip() for t in titles):
            if title and title not in seen:
                seen.append(title)
        return seen[:count]
