# 開発の規則

## ブランチ
| 名前 | 用途 |
|---|---|
| `main` | リリース済み。`release/*` と `hotfix/*` からのみ入れる（ADR 0013） |
| `develop` | 開発の統合先 |
| `feature/<Issue番号>-<英小文字とハイフン>` | 機能開発（例：`feature/8-repo-rules`） |
| `release/<版>` / `hotfix/<版>` | リリース準備／緊急修正（例：`release/1.0.0`） |
| `spike/<Issue番号>-…` | 試作。`develop` にはマージしない |
| `dependabot/…` | Dependabot が作る依存の更新。`develop` へマージできる |

## コミットとPRタイトル
Conventional Commits：`type(scope): subject`。件名は英語の命令形で、小文字で始め、末尾にピリオドを付けない（例：`feat(api): add map listing endpoint`）。PR本文は日本語で書く。
- type：feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert
- scope は任意。使う場合は `api, web, worker, db, ai, infra, docs, spike, deps, deps-dev` のいずれか（`deps-dev` は Dependabot が開発用の依存に付ける）。

CIで PRタイトル（`pr-title`）、PR内の全コミット（`commitlint`）、ブランチ名（`branch-policy`）を検査する。

## CI（ADR 0034）
`develop` へのマージに必須のチェックは次の5つ。

| チェック | 内容 |
|---|---|
| `ci-gate` | `ci.yml` の全ジョブの結果（lint、型、テスト、変更行カバレッジ80%、層の依存、openapi.json の差分、ビルド）。スキップは通し、失敗・取り消しは落とす |
| `security-scan` | 依存ライブラリの脆弱性（HIGH以上で失敗）。週1回も実行 |
| `pr-title` / `branch-policy` / `commitlint` | 上のとおり |

- `backend/`・`frontend/` が無いうちは、該当ジョブはスキップされる。
- ジョブを足すときは `ci-gate` の `needs` に加える（ルールセットは変えない）。
- Dependabot は週1回、`chore(deps): ...` のPRを作る。

## 初回セットアップ（Windows、PowerShell）
1. GNU Make：`winget install ezwinports.make`（入れたら PowerShell を開き直す）
2. pre-commit：`uv tool install pre-commit`
3. Node.js（commitlint用）と Docker Desktop を入れる
4. リポジトリ直下で `Copy-Item .env.example .env`（中のパスワードを変える）、`make setup`

Makefile は bash に依存しない書き方にしてあるので、PowerShell から `make` を実行できる。

## 共通コマンド
`make help` で一覧を表示する。
| コマンド | 内容 |
|---|---|
| `make up` | 全サービスを起動する（Ollama は GPU を使う。Docker Desktop を先に起動しておく） |
| `make up-cpu` | GPU が無い環境で起動する |
| `make down` | 止める（データは残る。消すときは `docker compose down -v`） |
| `make pull-models` | Ollama のモデル（qwen3:8b、bge-m3）を取得する。初回だけ、約6 GB |
| `make grafana` | Grafana のURLを表示する（ログ・メトリクス・トレース） |
| `make setup` / `make lint` | git hooks を入れる／pre-commit を全ファイルに実行する |
| `make test` | バックエンドのテスト（ユニットと結合。結合は Testcontainers で `thinkronos/postgres:18` を使うので、Docker を起動し、先に `make up` か `docker build -t thinkronos/postgres:18 docker/postgres` でイメージを作っておく） |
| `make migrate` | DBマイグレーション（所有者のロールで実行。`make up` でも自動で実行される） |
| `make seed` | デモ用のシードを入れる（何度実行してもよい） |
| `make gen-openapi` | `openapi.json`（リポジトリ直下）を作り直す。APIを変えたらコミットする（CI が差分を見る） |
| `make agent-smoke` | エージェント（Ollama、qwen3:8b）に子ノードを提案させる。`make pull-models` の後 |
| `make gen-types` | `openapi.json` からフロントのAPI型（`frontend/src/shared/api/schema.d.ts`）を作り直す。`make gen-openapi` の後に実行し、両方をコミットする |
| `make web` | 画面の開発サーバーを起動する（初回は `npm --prefix frontend ci`）。`http://localhost:5173` を開く。API は `make up` で起動しておく |

## バックエンド（`backend/`、ADR 0035）
- 層の構成と依存の向きは ADR 0035 と `.importlinter`。組み立ては `thinkronos/bootstrap.py` だけで行う。
- 手元での検査は `backend/` で `uv run ruff check .`、`uv run mypy .`、`uv run lint-imports ../.importlinter`。Windows では `lint-imports` の前に `$env:PYTHONUTF8 = "1"` を設定する（設定ファイルを cp932 で読もうとして失敗するため）。
- `.env` に `APP_DB_PASSWORD`（アプリのロールのパスワード、英数字）が要る。`.env.example` を参照。
- 結合テストが `Port mapping ... 8080 is not available` で失敗したときは、もう一度実行する（Testcontainers の後片付けのコンテナの起動待ちが Docker Desktop で間に合わないことがある）。

ポートは `127.0.0.1` だけに公開する（Postgres 5432、Redis 6379、Ollama 11435、api 8000、Grafana 3000、OTLP 4317/4318）。PC に Ollama を直接入れていても 11434 と被らない。

## 監視（Grafana）
`make up` の後、`make grafana` で表示される `http://127.0.0.1:3000` を開く（ログイン不要。匿名で Admin になるので、外部には公開しない）。左メニューの **Explore** で、上部のデータソースを切り替えて見る。
| 見たいもの | データソース | 例 |
|---|---|---|
| トレース | Tempo | Search で Service Name に `api` を選ぶ |
| ログ | Loki | `{service_name="api"} \| request_id="…"` |
| メトリクス | Prometheus | `http_server_requests_total` |

- ログの `trace_id` から、対応するトレースへ移れる。
- ログとメトリクスは `lgtmdata` ボリュームに残る（トレースは再起動で消えることがある）。消すときは `docker compose down -v`。
- 設計は `docs/observability.md`。
