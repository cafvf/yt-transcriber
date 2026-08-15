"""Taxonomia explícita de evidência, derivados e dados voláteis."""

from __future__ import annotations

from enum import StrEnum


class ArtifactClass(StrEnum):
    CANONICAL_STRUCTURED_TRANSCRIPT = "canonical_structured_transcript"
    CANONICAL_MARKDOWN = "canonical_markdown"
    DERIVED_SUMMARY = "derived_summary"
    DERIVED_EXPORT = "derived_export"
    DERIVED_SEARCH_INDEX = "derived_search_index"
    DERIVED_VIDEO = "derived_video"
    VOLATILE_SOURCE_MEDIA = "volatile_source_media"
    VOLATILE_CONVERTED_AUDIO = "volatile_converted_audio"
    OPERATIONAL_LOG = "operational_log"
    RECONSTRUCTIBLE_CACHE = "reconstructible_cache"

    @property
    def is_canonical(self) -> bool:
        return self in {
            self.CANONICAL_STRUCTURED_TRANSCRIPT,
            self.CANONICAL_MARKDOWN,
        }

    @property
    def is_volatile(self) -> bool:
        return self in {
            self.VOLATILE_SOURCE_MEDIA,
            self.VOLATILE_CONVERTED_AUDIO,
            self.OPERATIONAL_LOG,
            self.RECONSTRUCTIBLE_CACHE,
        }
