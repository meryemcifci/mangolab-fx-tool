#Aynı döviz kuru için upstream API'ye tekrar tekrar istek atmayı önlemek.
from datetime import datetime, timedelta
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: int = 300):#cache'e koyduğumuz veri 5 dakika geçerli olacak(300/60).
        self.ttl = timedelta(seconds=ttl_seconds)
        self._cache: dict[str, tuple[Any, datetime]] = {}

    def get(self, key: str) -> Any | None:
        item = self._cache.get(key)

        if item is None:
            return None

        value, expires_at = item

        if datetime.now() >= expires_at:
            del self._cache[key]
            return None

        return value

    def set(self, key: str, value: Any) -> None:
        expires_at = datetime.now() + self.ttl
        self._cache[key] = (value, expires_at)

    def clear(self) -> None:
        self._cache.clear()
        