# 0035 バックエンドの土台（Python、層、マイグレーション、テストデータ）

## 状態

承認済み、2026-11-23

## 背景

APIとワーカーの土台を作るにあたり、次を決める必要があった（D-07、D-08、D-14、D-19、NF-15、Issue #13）。

- Python の版と、パッケージ名・層の配置（ADR 0034 で仮決めした Python 3.13 を確定する）
- マイグレーションの方針（D-07）
- テストデータとシードの作り方（D-08）
- RLS の文脈（user_id と所属ワークスペース）をどこで設定するか（D-19）と、接続するロール（D-14）

## 比べた選択肢

| 項目 | 案 |
|---|---|
| Python | 3.13 ／ 3.14 |
| 配置 | `backend/src/thinkronos/`（src 配置）／ フラット |
| マイグレーション（D-07） | Alembic（async の env.py）／ SQLAlchemy の `create_all` |
| テストデータ（D-08） | factory_boy ／ polyfactory ／ 手書きの関数 |
| アプリのロールの作り方 | マイグレーションで作る ／ initdb のスクリプトで作る |
| 非同期ドライバ | asyncpg ／ psycopg 3 |
| SQLAlchemy | 2.1 ／ 2.0 |

## 決定

- **Python 3.13**、uv（`backend/pyproject.toml`、`backend/uv.lock`）。パッケージは `backend/src/thinkronos/`。
- 層は実装規約 3.1 に従う：`domain`、`ports`、`application`、`adapters`、`api`、`worker`、組み立て場所の `bootstrap.py`（下の表）。`.importlinter` で検査する。
- **D-07：Alembic**（async の env.py）。変更は「追加 → 移行 → 削除」を別のリビジョンに分け、`downgrade` も必ず書く。マイグレーションは所有者のロールで実行する。
- **D-08：factory_boy でテストデータ**を作り（オブジェクトを作るだけで、保存は UoW を通す）、**デモ用のシードは別に持つ**（`python -m thinkronos.cli seed`、`make seed`）。
- アプリは、テーブルの所有者ではない専用のロール **`thinkronos_app`** で接続する。ロールは**マイグレーションで作る**（存在しなければ作る。冪等）。
- Unit of Work が、トランザクションの最初に `set_config(..., is_local => true)` で `app.user_id` と `app.workspace_ids` を設定する。RLS のポリシーは `app_current_workspace_ids()` を通して読む。
- asyncpg、SQLAlchemy 2.1、pydantic-settings。

**層（実装規約 3.1）**

| 層 | import してよいもの | import してはいけないもの |
|---|---|---|
| domain | 標準ライブラリ、domain | フレームワーク、SDK、ほかのすべての層 |
| ports | domain | adapters、フレームワーク |
| application | domain、ports | adapters、api、worker、フレームワーク |
| adapters | ports、domain、外部のライブラリ | api、application、worker |
| api | application、自分のスキーマ | adapters（組み立て場所を除く） |
| worker | application | adapters（組み立て場所を除く） |
| bootstrap | すべて（環境変数を読み、ポートにアダプターを結び付ける役割だけ） | — |

- domain のエンティティは標準の `dataclasses`（frozen）で書く。Pydantic は api の入出力にだけ使う。
- api・worker は domain・ports を直接 import しないので、ユースケースの入力（コマンド）と出力（`WorkspaceView` など）は application の型にする。
- `thinkronos.cli`（手元で使うコマンド）は、bootstrap と application だけを使う。表に無いので `.importlinter` に契約を足した。
- `mcp/` は今は作らない（C-22）。

## 理由

- Python 3.13：Celery 5.7.0（2026-11-05）は CPython 3.10〜3.14 を正式にサポートし、strands-agents 1.65.0（2026-11-13）も 3.13 を分類子に載せている（[Celery 5.7 の What's new](https://docs.celeryq.dev/en/stable/history/whatsnew-5.7.html)、[strands-agents](https://pypi.org/project/strands-agents/)）。3.14 にする理由はまだ無い（3.14 の標準の `uuid.uuid7()` は、PostgreSQL 18 の `uuidv7()` で代わりになる）。
- ロールをマイグレーションで作る：会社の AWS（RDS／Aurora）には initdb のスクリプトが無く、ローカル・Testcontainers・CI・AWS を同じ手順にできる。
- 専用のロール：PostgreSQL の公式の説明では「スーパーユーザーと BYPASSRLS の属性を持つロールは、常に行のセキュリティを迂回する」「テーブルの所有者も通常は迂回する。`ALTER TABLE ... FORCE ROW LEVEL SECURITY` で対象にできる」（[Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)）。アプリのロールを所有者にしないこと、`FORCE` を付けることの両方で、RLS を確実に効かせる。
- `set_config` の `is_local = true` は「現在のトランザクションの間だけ」有効（[Configuration Settings Functions](https://www.postgresql.org/docs/current/functions-admin.html)）。接続をプールで使い回しても、次のトランザクションに文脈が漏れない。
- Alembic の async：公式の cookbook「Using Asyncio with Alembic」の形で、async のエンジンから `connection.run_sync` で通常のマイグレーションを実行する（[cookbook](https://alembic.sqlalchemy.org/en/latest/cookbook.html)）。cookbook は `async_engine_from_config` を使うが、接続先を環境変数から読むため `create_async_engine` にした。なお cookbook の該当の節は、ページの後半のため要約でしか確認できていない。
- factory_boy は SQLAlchemy の async のセッションを直接扱えない。保存を UoW に通すことで、テストでも RLS の文脈を必ず通る。
- SQLAlchemy 2.1 で、Alembic 1.20.1 との組み合わせに問題は出なかった（上げる・戻す・もう一度上げるの結合テストが通った）。2.0 系には下げていない。

確かめたこと（`backend/tests/integration/`、Testcontainers、`thinkronos/postgres:18`）：

| 確認 | 結果 |
|---|---|
| 所属するワークスペースの行だけが見える | 通過 |
| 別のワークスペースの行は見えない・更新されない・挿入できない（WITH CHECK） | 通過 |
| 文脈が未設定なら0行 | 通過 |
| トランザクションが終わると文脈が残らない | 通過（一度設定された名前は、未設定のとき空文字になる。ポリシーは空文字を「所属なし」として扱う） |
| アプリのロールは所有者でなく、superuser・BYPASSRLS・CREATEROLE を持たない。テーブルは ENABLE と FORCE | 通過 |
| マイグレーションの上げる・戻す・もう一度上げる。ロールが既にあっても通る | 通過 |

## 影響

- ワークスペースに属するテーブルは、必ず RLS（ENABLE と FORCE）、`app_current_workspace_ids()` のポリシー（USING と WITH CHECK）、アプリのロールへの GRANT を付ける。手順は `.claude/skills/create-migration/SKILL.md`。
- ロールのパスワードは環境変数 `APP_DB_PASSWORD` から渡す。マイグレーションのファイルにもログにも出さない（バインド変数で渡し、`DO` ブロックの中で読む。`alembic.ini` の SQLAlchemy のログは WARNING のまま）。オフライン（`--sql`）では 0001 を実行できない。
- ローカルの所有者（`POSTGRES_USER`）はスーパーユーザーなので RLS を迂回する。所有者で動作を確かめない。AWS ではマスターユーザーはスーパーユーザーではないが、所有者と同じく `FORCE` で RLS の対象になる。
- ロールはクラスタ全体のものなので、同じクラスタに複数のデータベースを作る場合はパスワードが共有される。
- `alembic.ini` は ASCII だけで書く。Alembic は OS の既定の文字コードで読む（Windows では cp932）。`.importlinter` も、Windows で実行するときは `PYTHONUTF8=1` が要る（CI は Linux なので不要）。
- Windows の Docker Desktop では、Testcontainers の Ryuk（後片付けのコンテナ）のポートの割り当てが間に合わず、結合テストが `Port mapping ... 8080 is not available` で失敗することがある。もう一度実行すると通る。CI（Linux）では未確認。
- 認証は別Issue。今は呼び出し側が `Actor(user_id, workspace_ids)` を組み立てて渡す。

## 参照

- Issue #13
- [0033](0033-postgresql-major-version.md)（`thinkronos/postgres:18`、`uuidv7()`）
- [0034](0034-ci.md)（uv、CI の backend ジョブ、`.importlinter`）
- [0005](0005-async-jobs.md)（ワーカーで async のユースケースを動かす方式）
