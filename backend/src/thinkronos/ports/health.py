"""死活確認のポート。"""

from typing import Protocol


class DatabaseProbe(Protocol):
    async def ping(self) -> bool:
        """DB に問い合わせて応答があれば True。例外は投げない。"""
        ...
