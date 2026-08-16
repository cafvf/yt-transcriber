"""Trusted configuration policy for outbound text-generation endpoints."""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class TextGenerationEndpointPolicy:
    base_url: str
    model: str
    explicitly_configured: bool

    def __post_init__(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("SUMMARY_BASE_URL must be an absolute http(s) endpoint")
        if not self.model.strip():
            raise ValueError("SUMMARY_MODEL cannot be empty")

    @property
    def is_local(self) -> bool:
        host = (urlparse(self.base_url).hostname or "").lower()
        if host == "localhost":
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    def require_transcript_disclosure_allowed(self) -> None:
        if not self.is_local and not self.explicitly_configured:
            raise ValueError(
                "Non-local text-generation endpoint requires an explicit "
                "SUMMARY_BASE_URL operator configuration"
            )
