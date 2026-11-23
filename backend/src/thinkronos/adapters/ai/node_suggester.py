"""NodeSuggester の Strands Agents 実装（Ollama、qwen3:8b、思考なし。ADR 0032）。

- 接続先は compose のサービス名（http://ollama:11434）。127.0.0.1 ではない。
- 出力は構造化出力（Pydantic のモデル）で受け取る。
- 日付は扱わせない（ADR 0032：相対的な日付は LLM に計算させない）。

OllamaModel の引数は strands-agents 1.65.0 のソース（strands/models/ollama.py）で確かめた：
host、model_id、temperature、keep_alive、additional_args（リクエストの最上位に足される）。
思考を切るのは Ollama の `think: false` を additional_args で渡す。
"""

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, Field
from strands import Agent
from strands.models.ollama import OllamaModel

SYSTEM_PROMPT = (
    "あなたはマインドマップの作成を手伝う。与えられたテーマの子ノードになる短いタイトルを、"
    "指定された件数だけ日本語で返す。各タイトルは20文字以内。日付や期限は含めない。"
)


class ChildNodeSuggestions(BaseModel):
    titles: list[str] = Field(description="子ノードのタイトル")


def create_ollama_model(host: str, model_id: str) -> OllamaModel:
    return OllamaModel(
        host=host,
        model_id=model_id,
        temperature=0,
        additional_args={"think": False},
    )


class StrandsNodeSuggester:
    def __init__(self, model: Any) -> None:
        # Strands の Model（OllamaModel など）。テストでは偽のモデルを渡す
        self._model = model

    async def suggest_children(self, theme: str, *, count: int) -> Sequence[str]:
        # Agent は会話の履歴を持つので、呼び出しごとに作る
        agent = Agent(model=self._model, system_prompt=SYSTEM_PROMPT, callback_handler=None)
        result = await agent.invoke_async(
            f"テーマ：{theme}\n件数：{count}",
            structured_output_model=ChildNodeSuggestions,
        )
        output = result.structured_output
        if not isinstance(output, ChildNodeSuggestions):
            return []
        return output.titles
