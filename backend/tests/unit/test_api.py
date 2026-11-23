import io
import json
import logging
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from thinkronos.adapters.observability import telemetry
from thinkronos.adapters.observability.http import RequestTelemetryMiddleware
from thinkronos.api import openapi
from thinkronos.api.app import ApiServices, create_app
from thinkronos.application.health import HealthStatus

REPO_ROOT = Path(__file__).resolve().parents[3]


def _app(db_ok: bool) -> FastAPI:
    async def check() -> HealthStatus:
        return HealthStatus(database=db_ok)

    app = create_app(ApiServices(check_health=check))
    app.add_middleware(RequestTelemetryMiddleware, service="test")
    return app


@pytest.fixture
def log_lines() -> io.StringIO:
    telemetry.setup("test", export=False)
    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(telemetry.JsonFormatter("test"))
    telemetry.get_logger().handlers = [handler]
    return buf


async def _get(app: FastAPI, path: str, headers: dict[str, str] | None = None) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(path, headers=headers)


async def test_healthz_ok_and_request_id_is_echoed(log_lines: io.StringIO) -> None:
    res = await _get(_app(True), "/healthz", {"X-Request-ID": "req-123"})
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "database": "ok"}
    assert res.headers["X-Request-ID"] == "req-123"
    record = json.loads(log_lines.getvalue().splitlines()[-1])
    assert record["message"] == "request finished"
    assert record["request_id"] == "req-123"
    assert record["http"]["status"] == 200


async def test_healthz_unavailable_when_db_is_down(log_lines: io.StringIO) -> None:
    res = await _get(_app(False), "/healthz")
    assert res.status_code == 503
    assert res.json() == {"status": "unavailable", "database": "unreachable"}
    assert len(res.headers["X-Request-ID"]) == 36  # 無ければ UUIDv4 を作る


async def test_bad_request_id_is_replaced(log_lines: io.StringIO) -> None:
    res = await _get(_app(True), "/healthz", {"X-Request-ID": "a" * 200})
    assert res.headers["X-Request-ID"] != "a" * 200


async def test_container_healthcheck_is_quiet(log_lines: io.StringIO) -> None:
    res = await _get(_app(True), "/healthz", {"X-Healthcheck": "1"})
    assert res.status_code == 200
    assert "X-Request-ID" in res.headers
    assert log_lines.getvalue() == ""


async def test_not_found_is_logged(log_lines: io.StringIO) -> None:
    res = await _get(_app(True), "/nope")
    assert res.status_code == 404
    assert json.loads(log_lines.getvalue().splitlines()[-1])["http"]["status"] == 404


def test_openapi_json_is_up_to_date() -> None:
    """リポジトリ直下の openapi.json が、今のコードから作ったものと同じ（C-28。CI の openapi ジョブと同じ確認）。"""
    assert (REPO_ROOT / "openapi.json").read_text(encoding="utf-8") == openapi.render()


def test_openapi_main(tmp_path: Path) -> None:
    out = tmp_path / "openapi.json"
    assert openapi.main([str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["paths"]["/healthz"]
    assert openapi.main([]) == 2
