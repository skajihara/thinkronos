# 開発の規則

## ブランチ
| 名前 | 用途 |
|---|---|
| `main` | リリース済み。`release/*` と `hotfix/*` からのみ入れる（ADR 0013） |
| `develop` | 開発の統合先 |
| `feature/<Issue番号>-<英小文字とハイフン>` | 機能開発（例：`feature/8-repo-rules`） |
| `release/<版>` / `hotfix/<版>` | リリース準備／緊急修正（例：`release/1.0.0`） |
| `spike/<Issue番号>-…` | 試作。`develop` にはマージしない |

## コミットとPRタイトル
Conventional Commits：`type(scope): subject`。件名は日本語可。
- type：feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert
- scope は任意。使う場合は `api, web, worker, db, ai, infra, docs, spike, deps` のいずれか。

CIで PRタイトル（`pr-title`）、PR内の全コミット（`commitlint`）、ブランチ名（`branch-policy`）を検査する。

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
| `make setup` / `make lint` | git hooks を入れる／pre-commit を全ファイルに実行する |
| `make test` / `migrate` / `gen-types` | 未実装 |

ポートは `127.0.0.1` だけに公開する（Postgres 5432、Redis 6379、Ollama 11435、api 8000）。PC に Ollama を直接入れていても 11434 と被らない。
