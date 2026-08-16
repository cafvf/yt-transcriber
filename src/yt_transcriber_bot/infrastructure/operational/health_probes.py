from __future__ import annotations

import importlib.util
import json
import shutil
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def probe_openai_compatible_models(
    url: str,
    headers: Mapping[str, str],
    timeout_s: float,
) -> Mapping[str, Any]:
    request = urllib.request.Request(
        url,
        headers=dict(headers),
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        raw = response.read().decode("utf-8")
    parsed = json.loads(raw)
    if not isinstance(parsed, Mapping):
        raise ValueError("resposta não é um objeto JSON")
    return parsed


def find_executable(name: str) -> str | None:
    return shutil.which(name)


def module_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


@dataclass(slots=True)
class _LocalDiskUsageResult:
    free: int


def local_disk_usage(path: Path) -> _LocalDiskUsageResult:
    usage = shutil.disk_usage(path)
    return _LocalDiskUsageResult(free=usage.free)
