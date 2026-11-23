"""API の入出力のスキーマ（Pydantic は api の入出力にだけ使う）。"""

from typing import Literal

from pydantic import BaseModel

from thinkronos.application.health import HealthStatus


class HealthResponse(BaseModel):
    status: Literal["ok", "unavailable"]
    database: Literal["ok", "unreachable"]

    @classmethod
    def of(cls, result: HealthStatus) -> "HealthResponse":
        return cls(
            status="ok" if result.ok else "unavailable",
            database="ok" if result.database else "unreachable",
        )
