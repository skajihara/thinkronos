"""OpenTelemetry の共通設定（トレース・メトリクス・ログ）。docker/stub/telemetry.py から移した。

設定は OTEL_* の環境変数だけで決める。送信先を変える（otel-lgtm → AWS の ADOT）ときも、
環境変数を変えるだけでコードは変えない。
  OTEL_SERVICE_NAME, OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_EXPORTER_OTLP_PROTOCOL,
  OTEL_RESOURCE_ATTRIBUTES, OTEL_METRIC_EXPORT_INTERVAL
形は docs/observability.md を参照。
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

LOGGER_NAME = "thinkronos"


def _add_request_id(record: logging.LogRecord) -> bool:
    record.request_id = request_id_var.get()
    return True


class JsonFormatter(logging.Formatter):
    """1行1JSON。リクエストIDと、有効なスパンがあればトレースID・スパンIDを入れる。"""

    def __init__(self, service: str) -> None:
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        ctx = trace.get_current_span().get_span_context()
        out: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "service": self.service,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        if ctx.is_valid:
            out["trace_id"] = format(ctx.trace_id, "032x")
            out["span_id"] = format(ctx.span_id, "016x")
        out.update(getattr(record, "fields", {}))
        if record.exc_info:
            out["exception"] = self.formatException(record.exc_info)
        return json.dumps(out, ensure_ascii=False)


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def setup(service: str, *, export: bool = True) -> logging.Logger:
    """プロバイダを作り、ロガーを返す。エンドポイント等は環境変数から読まれる。

    export=False は送信しない（テスト用）。標準出力への JSON ログだけ出す。
    ワーカー（prefork）では、fork の後の子プロセスで呼ぶ（送信のスレッドは fork を越えない）。
    """
    if export:
        resource = Resource.create({"service.name": service})  # OTEL_SERVICE_NAME / OTEL_RESOURCE_ATTRIBUTES が優先

        tp = TracerProvider(resource=resource)
        tp.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(tp)

        reader = PeriodicExportingMetricReader(OTLPMetricExporter())
        metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[reader]))

        lp = LoggerProvider(resource=resource)
        lp.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
        set_logger_provider(lp)

    logger = get_logger()
    logger.setLevel(logging.INFO)
    logger.propagate = False
    for handler in list(logger.handlers):  # 2回呼ばれても二重に出さない
        logger.removeHandler(handler)
    for f in list(logger.filters):
        logger.removeFilter(f)
    logger.addFilter(_add_request_id)  # OTLPのログ属性にも request_id を入れる（Loki で絞り込める）
    stdout = logging.StreamHandler(sys.stdout)
    stdout.setFormatter(JsonFormatter(service))
    logger.addHandler(stdout)
    if export:
        logger.addHandler(LoggingHandler(level=logging.INFO, logger_provider=lp))  # トレースIDは自動で付く
    return logger
