"""アプリが接続する専用のロールと、RLS の文脈を読む関数（D-14、D-19）

Revision ID: 0001
Revises:
Create Date: 2026-11-23

- ロール thinkronos_app は、存在しなければ作る（冪等）。あればパスワードと属性を合わせる。
  会社のAWS（RDS／Aurora）には initdb が無いので、ロールもマイグレーションで作る。
- パスワードは環境変数 APP_DB_PASSWORD から読み、バインド変数で渡す。
  このファイルにもログにも出さない（SQL の文字列にパスワードを埋め込まない）。
- テーブルの所有者ではないので、RLS が効く。NOBYPASSRLS を明示する。
"""

import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "thinkronos_app"


def upgrade() -> None:
    if context.is_offline_mode():
        raise RuntimeError("このリビジョンはパスワードを扱うため、オフライン（--sql）では実行しない")
    password = os.environ.get("APP_DB_PASSWORD")
    if not password:
        raise RuntimeError("APP_DB_PASSWORD を設定する（アプリのロールのパスワード）")

    # パスワードはトランザクション内だけの設定値に入れ、DO ブロックの中で読む
    op.get_bind().execute(
        sa.text("SELECT set_config('thinkronos.app_db_password', :password, true)"),
        {"password": password},
    )
    op.execute(
        f"""
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
            EXECUTE format('CREATE ROLE {APP_ROLE} LOGIN PASSWORD %L',
                           current_setting('thinkronos.app_db_password'));
          ELSE
            EXECUTE format('ALTER ROLE {APP_ROLE} LOGIN PASSWORD %L',
                           current_setting('thinkronos.app_db_password'));
          END IF;
        END
        $$;
        """
    )
    op.execute("SELECT set_config('thinkronos.app_db_password', '', true)")
    op.execute(f"ALTER ROLE {APP_ROLE} NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOINHERIT")
    op.execute(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}")

    # RLS のポリシーから使う。未設定・空文字のときは空の配列（どの行も見えない）
    op.execute(
        """
        CREATE FUNCTION app_current_workspace_ids() RETURNS uuid[]
        LANGUAGE sql STABLE PARALLEL SAFE AS $$
          SELECT coalesce(
            string_to_array(nullif(current_setting('app.workspace_ids', true), ''), ',')::uuid[],
            '{}'::uuid[])
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION app_current_user_id() RETURNS uuid
        LANGUAGE sql STABLE PARALLEL SAFE AS $$
          SELECT nullif(current_setting('app.user_id', true), '')::uuid
        $$
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS app_current_user_id()")
    op.execute("DROP FUNCTION IF EXISTS app_current_workspace_ids()")
    op.execute(
        f"""
        DO $$
        BEGIN
          IF EXISTS (SELECT FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
            REVOKE USAGE ON SCHEMA public FROM {APP_ROLE};
            DROP ROLE {APP_ROLE};
          END IF;
        END
        $$;
        """
    )
