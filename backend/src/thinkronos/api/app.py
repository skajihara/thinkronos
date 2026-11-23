"""FastAPI のアプリ。組み立て（アダプターとの結び付け）は thinkronos.bootstrap で行う。

api は application だけを import する（実装規約 3.1、.importlinter）。
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import FastAPI, Request, Response, status

from thinkronos.api.schemas import HealthResponse
from thinkronos.application.health import HealthStatus

API_TITLE = "Thinkronos API"
API_VERSION = "0.1.0"


@dataclass(frozen=True, slots=True)
class ApiServices:
    check_health: Callable[[], Awaitable[HealthStatus]]


def _services(request: Request) -> ApiServices:
    services: ApiServices = request.app.state.services
    return services


def create_app(services: ApiServices) -> FastAPI:
    app = FastAPI(title=API_TITLE, version=API_VERSION)
    app.state.services = services

    @app.get(
        "/healthz",
        response_model=HealthResponse,
        responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthResponse}},
        tags=["health"],
        summary="死活確認（DBにつないで応答する）",
    )
    async def healthz(request: Request, response: Response) -> HealthResponse:
        result = await _services(request).check_health()
        if not result.ok:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse.of(result)

    return app
