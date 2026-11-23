"""workspaces テーブルと RLS（D-19、I-01）

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-23

ワークスペースに属するテーブルは、必ず次の3つを付ける（.claude/skills/create-migration/SKILL.md）。
1. ENABLE と FORCE ROW LEVEL SECURITY（FORCE で所有者にも効かせる）
2. app_current_workspace_ids() で絞るポリシー（USING と WITH CHECK の両方）
3. アプリのロールへの必要な権限だけの GRANT
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "thinkronos_app"


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("uuidv7()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_workspaces_name_not_blank"),
    )
    op.execute("ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE workspaces FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY workspaces_isolation ON workspaces
          USING (id = ANY (app_current_workspace_ids()))
          WITH CHECK (id = ANY (app_current_workspace_ids()))
        """
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON workspaces TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON workspaces FROM {APP_ROLE}")
    op.execute("DROP POLICY IF EXISTS workspaces_isolation ON workspaces")
    op.drop_table("workspaces")
