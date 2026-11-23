# AGENTS.md

AIツール（Claude Code、Kiro など）が共通で読む規約。短く保つ。詳細は各文書を参照し、ここに複製しない。

## プロジェクト
Thinkronos：マインドマップをAIがカレンダーの時間ブロックに落とすアプリ。文書とコミットは日本語で書く。

## ディレクトリ
| 場所 | 内容 |
|---|---|
| `docs/` | 設計・運用の文書。`docs/adr/`（設計判断）、`docs/observability.md` |
| `docs/conventions/` | 実装規約（別Issueで追加予定。入ったらここを正とする） |
| `backend/` | API・ワーカー（Python 3.13、uv）。層は ADR 0035 と `.importlinter` |
| `docker/`、`compose*.yaml` | ローカル環境（Postgres、Redis、Ollama、監視） |
| `spike/` | 試作。`develop` にはマージしない |
| `.github/` | CI、Issue・PRのテンプレート |

## 共通コマンド
`make help` で一覧を表示する。主なもの：`make setup`（git hooks）、`make up` / `make up-cpu` / `make down`、`make lint`、`make test`、`make migrate`、`make gen-openapi`。`make gen-types` は未実装。
Windows（PowerShell）から実行できる。詳細は `CONTRIBUTING.md`。

## ブランチ・コミット・PR
`CONTRIBUTING.md` に従う（Conventional Commits、`feature/<Issue番号>-…`、CIの検査）。
`main` と `develop` は直接変更しない。必ずブランチを切ってPRを通す。

## 文書の場所
- 要件・要件ID：`docs/` を参照する（コードやコミットでは要件IDで指す）
- 設計判断：`docs/adr/`（書き方は `docs/adr/README.md`）
- ツールごとの使い方の記録：`docs/tool-notes.md`

## UIの表現の原則（B-11）
補足のラベルや説明文を足す前に、配置・グループ化・階層・余白・強調で表せないかを必ず検討する。文字で補うのは、それでも伝わらないときだけにする。
