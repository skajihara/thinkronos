"""組み立て場所（実装規約 3.1）。すべての層を import してよい唯一の場所。

役割は「環境変数を読み、ポートにアダプターを結び付ける」ことに限る。業務の処理は書かない。

起動の入口：
- API：     uvicorn thinkronos.bootstrap:create_api --factory
- ワーカー：celery -A thinkronos.bootstrap:celery_app worker
- 定期実行：celery -A thinkronos.bootstrap:celery_app beat
"""

from functools import cache
from typing import Any

from celery import Celery, signals
from fastapi import FastAPI
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncEngine

from thinkronos.adapters.ai.node_suggester import StrandsNodeSuggester, create_ollama_model
from thinkronos.adapters.db.engine import SqlAlchemyDatabaseProbe, create_engine, create_sessions
from thinkronos.adapters.db.unit_of_work import SqlAlchemyUnitOfWorkFactory
from thinkronos.adapters.observability import celery_signals, telemetry
from thinkronos.adapters.observability.http import RequestTelemetryMiddleware
from thinkronos.api.app import ApiServices, create_app
from thinkronos.application.health import CheckHealth
from thinkronos.application.suggestions import SuggestChildNodes
from thinkronos.application.workspaces import CreateWorkspace, RenameWorkspace
from thinkronos.worker.app import WorkerServices, create_celery
from thinkronos.worker.async_runner import AsyncMode, create_runner


class Settings(BaseSettings):
    """環境変数（compose の environment、.env.example）。"""

    model_config = SettingsConfigDict(extra="ignore")

    database_url: str = Field(description="アプリのロール（thinkronos_app）の接続先。postgresql+asyncpg://…")
    redis_url: str = "redis://redis:6379/0"
    ollama_host: str = "http://ollama:11434"
    ollama_model: str = "qwen3:8b"
    worker_async_mode: AsyncMode = "run"
    otel_service_name: str = "thinkronos"
    telemetry_export: bool = True


@cache
def settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # 値は環境変数から入る


def setup_telemetry(s: Settings) -> None:
    telemetry.setup(s.otel_service_name, export=s.telemetry_export)


def build_uow(engine: AsyncEngine) -> SqlAlchemyUnitOfWorkFactory:
    return SqlAlchemyUnitOfWorkFactory(create_sessions(engine))


def build_suggest_child_nodes(s: Settings) -> SuggestChildNodes:
    return SuggestChildNodes(StrandsNodeSuggester(create_ollama_model(s.ollama_host, s.ollama_model)))


def build_create_workspace(s: Settings) -> CreateWorkspace:
    return CreateWorkspace(build_uow(create_engine(s.database_url, pooled=False)))


# --- API ---------------------------------------------------------------------------------------


def create_api() -> FastAPI:
    s = settings()
    setup_telemetry(s)
    engine = create_engine(s.database_url)
    app = create_app(ApiServices(check_health=CheckHealth(SqlAlchemyDatabaseProbe(engine))))
    app.add_middleware(RequestTelemetryMiddleware, service=s.otel_service_name)
    return app


# --- ワーカー -------------------------------------------------------------------------------------


def build_worker_services(s: Settings) -> WorkerServices:
    # A 案（run）はタスクごとにループが変わるので接続を使い回さない（NullPool）。B 案（runner）はプールを使う
    engine = create_engine(s.database_url, pooled=s.worker_async_mode == "runner")
    return WorkerServices(rename_workspace=RenameWorkspace(build_uow(engine)))


_telemetry_ready = False


def _setup_worker_telemetry(**_: Any) -> None:
    global _telemetry_ready
    if not _telemetry_ready:  # プロセスごとに1回
        setup_telemetry(settings())
        _telemetry_ready = True


def create_worker_celery(s: Settings) -> Celery:
    app = create_celery(
        cache(lambda: build_worker_services(s)),  # プロセスの中で最初のタスクのときに作る
        create_runner(s.worker_async_mode),
        broker_url=s.redis_url,
        result_backend=s.redis_url,
    )
    celery_signals.connect()
    # prefork の子プロセス（fork の後）、solo などの単一プロセス、beat のそれぞれで監視を設定する
    signals.worker_process_init.connect(_setup_worker_telemetry, weak=False, dispatch_uid="thinkronos.otel.child")
    signals.worker_ready.connect(_setup_worker_telemetry, weak=False, dispatch_uid="thinkronos.otel.ready")
    signals.beat_init.connect(_setup_worker_telemetry, weak=False, dispatch_uid="thinkronos.otel.beat")
    return app


@cache
def _celery_app() -> Celery:
    return create_worker_celery(settings())


def __getattr__(name: str) -> Any:
    # celery -A thinkronos.bootstrap:celery_app は属性を参照する。API の起動では作らないよう、参照されたときに作る
    if name == "celery_app":
        return _celery_app()
    raise AttributeError(name)
