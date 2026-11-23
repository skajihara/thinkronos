"""死活確認のユースケース。"""

from dataclasses import dataclass

from thinkronos.ports.health import DatabaseProbe


@dataclass(frozen=True, slots=True)
class HealthStatus:
    database: bool

    @property
    def ok(self) -> bool:
        return self.database


class CheckHealth:
    def __init__(self, database: DatabaseProbe) -> None:
        self._database = database

    async def __call__(self) -> HealthStatus:
        return HealthStatus(database=await self._database.ping())
