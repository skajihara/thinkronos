"""CI の確認用（Issue #13）。application から adapters を import する違反。マージしない。"""

from thinkronos.adapters.db import engine  # noqa: F401
