"""Smoke tests for the fake/non-ML performance benchmark harness."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_fake_benchmark_script_writes_expected_sections(tmp_path: Path) -> None:
    output_path = tmp_path / "benchmark.json"
    script_path = Path("scripts/perf/benchmark_pipeline_fake.py")

    completed = subprocess.run(
        [sys.executable, str(script_path), "--output", str(output_path), "--iterations", "1"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["iterations"] == 1
    assert payload["benchmarks"]["pipeline_fake"]["timings_ms"]
    assert payload["benchmarks"]["markdown_render"]["timings_ms"]
    assert payload["benchmarks"]["subtitle_parse_dedupe"]["timings_ms"]
    assert payload["benchmarks"]["summary_chunk_prep"]["timings_ms"]
    assert payload["benchmarks"]["snapshot_history_titles"]["timings_ms"]
    assert payload["benchmarks"]["rename_workflow"]["timings_ms"]
