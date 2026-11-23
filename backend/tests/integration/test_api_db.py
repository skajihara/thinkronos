"""ヘルスチェックの API が、アプリのロールで DB につないで応答する（受け入れ条件）。"""

import httpx
import pytest

from thinkronos import bootstrap

pytestmark = pytest.mark.integration


async def _get(app_url: str, monkeypatch: pytest.MonkeyPatch) -> httpx.Response:
    monkeypatch.setenv("DATABASE_URL", app_url)
    monkeypatch.setenv("TELEMETRY_EXPORT", "false")
    monkeypatch.setenv("OTEL_SERVICE_NAME", "api-test")
    bootstrap.settings.cache_clear()
    try:
        app = bootstrap.create_api()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.get("/healthz")
    finally:
        bootstrap.settings.cache_clear()


async def test_healthz_connects_to_db(migrated: str, app_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    res = await _get(app_url, monkeypatch)
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "database": "ok"}


async def test_healthz_503_with_wrong_password(migrated: str, app_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    res = await _get(app_url.replace(":app-test-password@", ":wrong@"), monkeypatch)
    assert res.status_code == 503
    assert res.json()["database"] == "unreachable"
