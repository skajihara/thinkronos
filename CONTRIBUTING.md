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

## 初回セットアップ（Windows）
1. GNU Make：`winget install ezwinports.make`（Git Bash から実行する）
2. pre-commit：`uv tool install pre-commit`
3. Node.js（commitlint用）を入れ、リポジトリ直下で `make setup`

## 共通コマンド
`make help` で一覧を表示する（up, down, test, lint, migrate, gen-types, setup）。
