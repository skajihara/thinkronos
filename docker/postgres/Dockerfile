# syntax=docker/dockerfile:1
# PostgreSQL 18 + pgvector + pg_bigm（ADR 0033）
# compose・Testcontainers・CI で同じイメージを使う（thinkronos/postgres:18）
ARG PGVECTOR_TAG=0.8.7-pg18-bookworm

FROM pgvector/pgvector:${PGVECTOR_TAG} AS build
ARG PG_BIGM_VERSION=v1.2-20261118
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential curl ca-certificates postgresql-server-dev-18 \
 && curl -fsSL "https://github.com/pgbigm/pg_bigm/archive/refs/tags/${PG_BIGM_VERSION}.tar.gz" | tar -xz -C /tmp \
 && cd /tmp/pg_bigm-* \
 && make USE_PGXS=1 \
 && make USE_PGXS=1 install DESTDIR=/out

FROM pgvector/pgvector:${PGVECTOR_TAG}
COPY --from=build /out/ /
COPY initdb/ /docker-entrypoint-initdb.d/
