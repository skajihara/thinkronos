"""api / worker / scheduler の仮プロセス。/healthz に応答し、テレメトリ（トレース・メトリクス・ログ）を送る。
本体の土台（Issue「バックエンドの土台を作る」）ができたら置き換える。telemetry.py はそのまま使える。"""
import os
import time
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

import telemetry

SERVICE = os.environ.get("SERVICE_NAME", "stub")
logger, tracer, meter = telemetry.setup(SERVICE)
requests_total = meter.create_counter("http.server.requests", description="受け付けたリクエスト数")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        ok = self.path == "/healthz"
        body = f"ok {SERVICE}\n".encode() if ok else b"not found\n"
        # コンテナのヘルスチェック（5秒ごと）はテレメトリを送らない
        if self.headers.get("X-Healthcheck"):
            return self._reply(200 if ok else 404, body, "-")
        rid = self.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = telemetry.request_id_var.set(rid)
        start = time.perf_counter()
        try:
            with tracer.start_as_current_span(f"GET {self.path}", attributes={"http.request.method": "GET", "url.path": self.path, "request.id": rid}):
                status = 200 if ok else 404
                self._reply(status, body, rid)
                ms = round((time.perf_counter() - start) * 1000, 2)
                requests_total.add(1, {"http.response.status_code": status})
                logger.info("request finished", extra={"fields": {"http": {"method": "GET", "path": self.path, "status": status, "duration_ms": ms}}})
        finally:
            telemetry.request_id_var.reset(token)

    def _reply(self, status, body, rid):
        self.send_response(status)
        self.send_header("X-Request-ID", rid)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


with tracer.start_as_current_span("startup"):
    requests_total.add(0)
    logger.info("started")
HTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8000"))), Handler).serve_forever()
