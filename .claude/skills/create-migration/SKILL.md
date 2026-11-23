---
name: create-migration
description: データベースのマイグレーション（Alembic）を作成する。テーブルの追加・変更、RLS のポリシー、アプリのロールへの権限を扱う。
disable-model-invocation: true
---

# マイグレーションの作成（D-07、ADR 0035）

## 前提
- ツールは Alembic（async の `env.py`）。置き場所は `backend/migrations/versions/`、ファイル名は `<番号>_<題>.py`（番号は4桁の連番。`revision` も同じ番号にする）。
- 実行：`make migrate`（compose の `migrate` サービス。所有者のロールで実行する）。手元で直接なら `backend/` で `uv run alembic upgrade head`（環境変数 `MIGRATION_DATABASE_URL` と `APP_DB_PASSWORD` が要る）。
- アプリは所有者ではないロール `thinkronos_app` で接続する。マイグレーションはアプリのロールで実行しない。
- `alembic.ini` は ASCII だけで書く（Windows では cp932 で読まれる）。

## 手順
1. 変更を「追加 → 移行 → 削除」に分け、それぞれ別のリビジョンにする（列の改名なら：新しい列を足す → データを写す・アプリを切り替える → 古い列を消す）。1つのリビジョンで壊れる変更（列の削除・型の変更）をしない。
2. ワークスペースに属する新しいテーブルには、必ず次の3つを付ける（例：`0002_workspaces.py`）。
   - `ALTER TABLE … ENABLE ROW LEVEL SECURITY` と `ALTER TABLE … FORCE ROW LEVEL SECURITY`
   - `CREATE POLICY … USING (workspace_id = ANY (app_current_workspace_ids())) WITH CHECK (同じ)`
   - `GRANT SELECT, INSERT, UPDATE, DELETE ON … TO thinkronos_app`（必要なものだけ）
3. `downgrade` を必ず書く。`upgrade` と逆の順で戻す（ポリシー・権限 → テーブル）。
4. パスワードなどの秘密は、ファイルにもログにも出さない。SQL の文字列に埋め込まず、環境変数から読んでバインド変数で渡す（`0001_app_role.py` の形）。
5. SQLAlchemy のモデル（`thinkronos/adapters/db/models.py`）を合わせる。スキーマの正はマイグレーション。

## 確認
- 結合テスト（`backend/tests/integration/`）に、新しいテーブルの RLS のテストを足す：所属するワークスペースの行だけ見える、別のワークスペースの行は見えない・更新されない・挿入できない。
- `test_migrations.py` の「上げる → 戻す → もう一度上げる」が通る。
- `make test` が通る。
