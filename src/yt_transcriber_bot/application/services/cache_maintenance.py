from yt_transcriber_bot.application.ports.cache import CacheCleanupResult, ReconstructibleCache


class CacheMaintenanceService:
    def __init__(self, cache: ReconstructibleCache) -> None:
        self._cache = cache

    def clear(self) -> CacheCleanupResult:
        return self._cache.clear()
