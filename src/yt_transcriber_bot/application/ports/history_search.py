# Compatibility query contract; indexing is separate after P04-006.
from yt_transcriber_bot.application.ports.text_search import HistorySearchHit, TextSearchQuery


class HistorySearchRepository(TextSearchQuery):
    pass


__all__ = ["HistorySearchHit", "HistorySearchRepository"]
