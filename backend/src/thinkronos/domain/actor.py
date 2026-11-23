"""操作する人と、その人が所属するワークスペースの一覧（D-19）。

認証は別Issue。今は呼び出し側（API・ワーカー）が組み立てて渡す。
"""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Actor:
    user_id: UUID
    workspace_ids: frozenset[UUID]
