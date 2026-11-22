# 0033 PostgreSQLのメジャーバージョン（D-18）

## 状態

承認済み、2026-11-23

## 背景

ローカル・Testcontainers・CIで使うPostgreSQLのメジャーバージョンを決める必要があった（D-18、NF-04、C-01）。条件は次のとおり。

- 15以上（列を指定した `ON DELETE SET NULL` を使う）
- pgvector と pg_bigm が使える
- 会社のAWS（RDS／Aurora PostgreSQL）に載せ替えられる

## 比べた選択肢

| 案 | 特徴 |
|---|---|
| 17 | 実績が多い。`uuidv7()` が標準に無く、アプリ側で生成が要る |
| 18 | `uuidv7()` が標準で使える。15以上の条件も満たす |

## 決定

**PostgreSQL 18** を使う。イメージは `thinkronos/postgres:18`（`docker/postgres/`、pgvector 0.8.7 ＋ pg_bigm 1.2-20261118）。

## 理由

一次情報で確かめた（2026-11-23）。

- pg_bigm：公式リポジトリの動作確認環境に PostgreSQL 18 が載っている（`docs/pg_bigm.md`、REL1_2_STABLE）。最新リリースは v1.2-20261118（2026-11-17）。
- pgvector：Docker Hub の `pgvector/pgvector` に `0.8.7-pg18-bookworm` などの18向けタグがある。
- AWS：RDS for PostgreSQL と Aurora PostgreSQL の拡張一覧の PostgreSQL 18 の節に、pgvector 0.8.2、pg_bigm 1.2_20250903 が載っている（[RDS](https://docs.aws.amazon.com/AmazonRDS/latest/PostgreSQLReleaseNotes/postgresql-extensions.html)、[Aurora](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraPostgreSQLReleaseNotes/AuroraPostgreSQL.Extensions.html)）。Auroraの18対応は2026-06（[AWS](https://aws.amazon.com/about-aws/whats-new/2026/06/amazon-aurora-postgresql-major-version-18)）。
- 動作確認：イメージを作り、`CREATE EXTENSION vector; CREATE EXTENSION pg_bigm;` と `uuidv7()` が通った（PostgreSQL 18.7）。

## 影響

- ローカルは pgvector 0.8.7・pg_bigm 1.2-20261118、AWSは pgvector 0.8.2・pg_bigm 1.2_20250903 と版が異なる。本番で使う機能は両方の版で使えるものに限る。
- 拡張一覧の表は、行がどのエンジン版（18.x）に対応するかを読み取り切れていない。本番のAWSで使うエンジン版が決まったら、`describe-db-engine-versions` で確認する。
- 会社のAWSアカウント・リージョンで18が選べるかは未確認。
- 18ではデータの置き場所が `/var/lib/postgresql` になった（compose のボリュームもこれに合わせた）。
- pg_bigm の不具合修正（途中で切れたマルチバイト文字の読み取り）を有効にするには、PostgreSQL 18.2以降のヘッダでビルドする必要がある。現在のイメージは18.7でビルドしている。

## 参照

- Issue #9
- [ADR 0032](0032-local-llm-and-embedding.md)
