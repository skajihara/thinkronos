"""ワークスペース。データを分ける単位で、RLS の境界になる（D-19、I-01）。"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from uuid import UUID

NAME_MAX_LENGTH = 100


class InvalidWorkspaceName(ValueError):
    """ワークスペースの名前が規則に合わない。"""


def _validate_name(name: str) -> str:
    stripped = name.strip()
    if not stripped:
        raise InvalidWorkspaceName("名前が空です")
    if len(stripped) > NAME_MAX_LENGTH:
        raise InvalidWorkspaceName(f"名前は{NAME_MAX_LENGTH}文字以内にします")
    return stripped


@dataclass(frozen=True, slots=True)
class Workspace:
    id: UUID
    name: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _validate_name(self.name))

    def renamed(self, name: str) -> Workspace:
        return dataclasses.replace(self, name=name)
