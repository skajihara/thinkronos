"""Strands のエージェント（adapters/ai）。偽のモデルで、構造化出力のツール呼び出しを返す。"""

import json
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any

import pytest
from strands.models.model import Model

from thinkronos.adapters.ai.node_suggester import StrandsNodeSuggester, create_ollama_model
from thinkronos.application.suggestions import SuggestChildNodes


class FakeModel(Model):
    """渡されたツール（構造化出力のツール）を、決まった引数で呼ぶ応答を返す。"""

    def __init__(self, titles: list[str]) -> None:
        self.titles = titles
        self.prompts: list[Any] = []

    def update_config(self, **model_config: Any) -> None:
        pass

    def get_config(self) -> Any:
        return {}

    def structured_output(self, *args: Any, **kwargs: Any) -> AsyncGenerator[Any]:  # pragma: no cover
        raise NotImplementedError

    async def stream(
        self, messages: Any, tool_specs: Any = None, system_prompt: Any = None, **kwargs: Any
    ) -> AsyncIterator[Any]:
        self.prompts.append(messages)
        tool = tool_specs[0]["name"]
        yield {"messageStart": {"role": "assistant"}}
        yield {"contentBlockStart": {"start": {"toolUse": {"name": tool, "toolUseId": "t1"}}}}
        yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps({"titles": self.titles})}}}}
        yield {"contentBlockStop": {}}
        yield {"messageStop": {"stopReason": "tool_use"}}


async def test_suggests_children_with_structured_output() -> None:
    model = FakeModel(["宿", "交通", "予算"])
    titles = await SuggestChildNodes(StrandsNodeSuggester(model))("旅行", count=3)
    assert titles == ["宿", "交通", "予算"]
    assert "旅行" in json.dumps(model.prompts[0], ensure_ascii=False)


def test_ollama_model_config() -> None:
    model = create_ollama_model("http://ollama:11434", "qwen3:8b")
    config = model.get_config()
    assert config["model_id"] == "qwen3:8b"
    assert config["temperature"] == 0
    assert config["additional_args"] == {"think": False}
    request = model.format_request([{"role": "user", "content": [{"text": "x"}]}])
    assert request["think"] is False


@pytest.mark.ollama
async def test_real_ollama() -> None:  # pragma: no cover - 手元で pytest -m ollama で実行する
    import os

    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11435")
    titles = await SuggestChildNodes(StrandsNodeSuggester(create_ollama_model(host, "qwen3:8b")))("旅行", count=3)
    assert 1 <= len(titles) <= 3
