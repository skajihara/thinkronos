"""結合テストの共通の準備（Testcontainers、thinkronos/postgres:18）。

イメージは先に作っておく：docker build -t thinkronos/postgres:18 docker/postgres（CI も同じ）。
所有者のロール（owner）でマイグレーションし、アプリはテーブルの所有者ではない thinkronos_app で接続する。
"""

import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine
from testcontainers.community.postgres import PostgresContainer

from thinkronos.adapters.db.engine import create_engine
from thinkronos.adapters.db.unit_of_work import SqlAlchemyUnitOfWorkFactory
from thinkronos.bootstrap import build_uow

BACKEND = Path(__file__).resolve().parents[2]
IMAGE = "thinkronos/postgres:18"
APP_PASSWORD = "app-test-password"


@pytest.fixture(scope="session")
def postgres() -> Iterator[PostgresContainer]:
    with PostgresContainer(IMAGE, username="owner", password="owner-test-password", dbname="thinkronos") as pg:
        yield pg


@pytest.fixture(scope="session")
def owner_url(postgres: PostgresContainer) -> str:
    return postgres.get_connection_url(driver="asyncpg")


@pytest.fixture(scope="session")
def app_url(owner_url: str) -> str:
    url = make_url(owner_url).set(username="thinkronos_app", password=APP_PASSWORD)
    return url.render_as_string(hide_password=False)


def alembic_config(url: str) -> Config:
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return config


@pytest.fixture(scope="session")
def migrated(owner_url: str) -> str:
    os.environ["APP_DB_PASSWORD"] = APP_PASSWORD
    command.upgrade(alembic_config(owner_url), "head")
    return owner_url


@pytest.fixture(scope="session")
async def app_engine(migrated: str, app_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(app_url)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
async def owner_engine(migrated: str) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(migrated)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
def uow(app_engine: AsyncEngine) -> SqlAlchemyUnitOfWorkFactory:
    return build_uow(app_engine)
