"""OpenTelemetry の共通設定（トレース・メトリクス・ログ）。
本物のAPI／worker／scheduler でもそのまま使えるように、設定は OTEL_* の環境変数だけで決める。
送信先を変える（otel-lgtm → AWS の ADOT）ときも、環境変数を変えるだけでコードは変えない。
  OTEL_SERVICE_NAME, OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_EXPORTER_OTLP_PROTOCOL,
  OTEL_RESOURCE_ATTRIBUTES, OTEL_METRIC_EXPORT_INTERVAL
形は docs/observability.md を参照。"""
import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

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


def _add_request_id(record: logging.LogRecord) -> bool:
    record.request_id = request_id_var.get()
    return True


class JsonFormatter(logging.Formatter):
    """1行1JSON。リクエストIDと、有効なスパンがあればトレースID・スパンIDを入れる。"""

    def __init__(self, service: str):
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        ctx = trace.get_current_span().get_span_context()
        out = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "service": self.service,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        if ctx.is_valid:
            out["trace_id"] = format(ctx.trace_id, "032x")
            out["span_id"] = format(ctx.span_id, "016x")
        out.update(getattr(record, "fields", {}))
        return json.dumps(out, ensure_ascii=False)


def setup(service: str):
    """プロバイダを作り、(logger, tracer, meter) を返す。エンドポイント等は環境変数から読まれる。"""
    resource = Resource.create({"service.name": service})  # OTEL_SERVICE_NAME / OTEL_RESOURCE_ATTRIBUTES が優先される

    tp = TracerProvider(resource=resource)
    tp.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tp)

    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[PeriodicExportingMetricReader(OTLPMetricExporter())]))

    lp = LoggerProvider(resource=resource)
    lp.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
    set_logger_provider(lp)

    logger = logging.getLogger(service)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.addFilter(_add_request_id)  # OTLPのログ属性にも request_id を入れる（Loki で絞り込める）
    stdout = logging.StreamHandler(sys.stdout)
    stdout.setFormatter(JsonFormatter(service))
    logger.addHandler(stdout)
    logger.addHandler(LoggingHandler(level=logging.INFO, logger_provider=lp))  # OTLPでも送る（トレースIDは自動で付く）
    return logger, trace.get_tracer(service), metrics.get_meter(service)
