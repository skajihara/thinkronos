"""HTTP のリクエストごとの計測（ASGI ミドルウェア）。docker/stub/server.py と同じ形を保つ。

- X-Request-ID を受け取り（無ければ UUIDv4 を作り）、レスポンスヘッダにも返す。
- スパン・メトリクス（http.server.requests）・構造化ログ（request finished）を出す。
- コンテナの死活確認（X-Healthcheck ヘッダ付き）は、テレメトリを送らない。
"""

import time
import uuid

from opentelemetry import metrics, trace
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from thinkronos.adapters.observability.telemetry import get_logger, request_id_var

REQUEST_ID_HEADER = "x-request-id"
_MAX_REQUEST_ID_LENGTH = 128


def _request_id(headers: Headers) -> str:
    rid = headers.get(REQUEST_ID_HEADER, "")
    # ログに入る値なので、長さと文字を制限する（改行などでログを壊されないように）
    if rid and len(rid) <= _MAX_REQUEST_ID_LENGTH and rid.isprintable():
        return rid
    return str(uuid.uuid4())


class RequestTelemetryMiddleware:
    def __init__(self, app: ASGIApp, *, service: str) -> None:
        self.app = app
        self.tracer = trace.get_tracer(service)
        self.requests_total = metrics.get_meter(service).create_counter(
            "http.server.requests", description="受け付けたリクエスト数"
        )
        self.logger = get_logger()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        rid = _request_id(headers)
        quiet = bool(headers.get("x-healthcheck"))
        status = 500

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                MutableHeaders(scope=message).append("X-Request-ID", rid)
            await send(message)

        if quiet:
            await self.app(scope, receive, send_with_id)
            return

        method, path = scope["method"], scope["path"]
        token = request_id_var.set(rid)
        start = time.perf_counter()
        try:
            attributes = {"http.request.method": method, "url.path": path, "request.id": rid}
            with self.tracer.start_as_current_span(f"{method} {path}", attributes=attributes) as span:
                try:
                    await self.app(scope, receive, send_with_id)
                finally:
                    span.set_attribute("http.response.status_code", status)
                    ms = round((time.perf_counter() - start) * 1000, 2)
                    self.requests_total.add(1, {"http.response.status_code": status})
                    self.logger.info(
                        "request finished",
                        extra={
                            "fields": {"http": {"method": method, "path": path, "status": status, "duration_ms": ms}}
                        },
                    )
        finally:
            request_id_var.reset(token)
