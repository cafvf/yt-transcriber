"""Repeatable fake/non-ML benchmark harness for Phase 5 hotspots."""

from __future__ import annotations

import argparse
import json
import statistics
import tempfile
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from yt_transcriber_bot.application.services.rename_speakers import RenameSpeakersService
from yt_transcriber_bot.application.services.transcript_summary import (
    _chunk_text,
    _snapshot_to_text,
)
from yt_transcriber_bot.domain.entities.job import Job, JobStatus
from yt_transcriber_bot.domain.entities.media_metadata import MediaMetadata
from yt_transcriber_bot.domain.entities.transcript import (
    SpeakerTurn,
    Transcript,
    TranscriptSegment,
)
from yt_transcriber_bot.domain.value_objects.duration import Duration
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.persistence.filesystem.canonical_markdown_writer import (
    FilesystemCanonicalMarkdownWriter,
)
from yt_transcriber_bot.infrastructure.persistence.filesystem.transcript_snapshot import (
    TranscriptSnapshot,
    TranscriptSnapshotRepository,
)
from yt_transcriber_bot.infrastructure.rendering.markdown_renderer import (
    MarkdownTranscriptRenderer,
    RenderContext,
)
from yt_transcriber_bot.infrastructure.youtube.yt_dlp_downloader import _parse_subtitle


@dataclass(frozen=True)
class BenchmarkSummary:
    timings_ms: list[float]
    median_ms: float
    min_ms: float
    max_ms: float


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=3)
    return parser.parse_args()


def _main() -> None:
    args = _args()
    payload = run_benchmarks(iterations=max(1, args.iterations))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_benchmarks(*, iterations: int) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="yt-transcriber-perf-") as tmpdir:
        base_dir = Path(tmpdir)
        snapshots = TranscriptSnapshotRepository(base_dir / "segments")
        renderer = MarkdownTranscriptRenderer()
        legacy_renderer = _LegacyMarkdownTranscriptRenderer()
        rename_service = RenameSpeakersService(
            snapshots, renderer, FilesystemCanonicalMarkdownWriter()
        )
        transcript = _build_transcript(segment_count=160)
        metadata = _build_metadata("benchmark-video")
        context = _build_context()
        snapshot = TranscriptSnapshot(metadata=metadata, transcript=transcript, context=context)
        snapshots.save("benchmark-video", snapshot)
        for index in range(10):
            slug = f"history-{index:02d}"
            snapshots.save(slug, TranscriptSnapshot(_build_metadata(slug), transcript, context))

        subtitle_fixture = _build_vtt_fixture()

        jobs = [
            _make_completed_job(
                video_id=f"vid{index:02d}".ljust(11, "x"),
                slug=f"history-{index:02d}",
                requested_at=datetime(2026, 5, 1, 12, index, tzinfo=UTC),
            )
            for index in range(10)
        ][::-1]

        benchmarks = {
            "pipeline_fake": _measure(
                iterations,
                lambda: _pipeline_fake(renderer, transcript, metadata, context),
            ),
            "markdown_render": _measure(
                iterations,
                lambda: renderer.render(metadata, transcript, context),
            ),
            "markdown_render_legacy_reference": _measure(
                iterations,
                lambda: legacy_renderer.render(metadata, transcript, context),
            ),
            "subtitle_parse_dedupe": _measure(
                iterations,
                lambda: _parse_subtitle(subtitle_fixture, "vtt"),
            ),
            "summary_chunk_prep": _measure(
                iterations,
                lambda: _chunk_text(
                    _snapshot_to_text(snapshot, {}, deduplicate=True),
                    max_chars_per_chunk=4_000,
                    max_input_tokens=8_000,
                    chars_per_token=4.0,
                    tokenizer=None,
                ),
            ),
            "snapshot_history_titles": _measure(
                iterations,
                lambda: _history_title_listing(rename_service, jobs),
            ),
            "snapshot_history_titles_legacy_reference": _measure(
                iterations,
                lambda: _history_title_listing_legacy(snapshots, jobs),
            ),
            "rename_workflow": _measure(
                iterations,
                lambda: rename_service.rename(
                    "benchmark-video",
                    {"SPEAKER_00": "Ana", "SPEAKER_01": "Bruno"},
                    base_dir / "transcripts" / "benchmark-video.md",
                ),
            ),
        }

    return {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "iterations": iterations,
        "benchmarks": {name: asdict(summary) for name, summary in benchmarks.items()},
    }


def _measure(iterations: int, fn: Callable[[], object]) -> BenchmarkSummary:
    timings_ms: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        fn()
        timings_ms.append(round((time.perf_counter() - started) * 1000, 3))
    return BenchmarkSummary(
        timings_ms=timings_ms,
        median_ms=round(statistics.median(timings_ms), 3),
        min_ms=min(timings_ms),
        max_ms=max(timings_ms),
    )


def _pipeline_fake(
    renderer: MarkdownTranscriptRenderer,
    transcript: Transcript,
    metadata: MediaMetadata,
    context: RenderContext,
) -> str:
    rendered = renderer.render(metadata, transcript, context)
    parsed = _parse_subtitle(_build_vtt_fixture(), "vtt")
    return f"{len(rendered)}:{len(parsed)}"


def _history_title_listing(rename_service: RenameSpeakersService, jobs: list[Job]) -> list[str]:
    slugs = tuple(
        reference
        for reference in (job.canonical_transcript_ref for job in jobs)
        if reference is not None
    )
    titles = rename_service.metadata_for_many(slugs)
    return [titles[slug].title for slug in slugs if slug in titles]


def _history_title_listing_legacy(
    snapshots: TranscriptSnapshotRepository, jobs: list[Job]
) -> list[str]:
    titles: list[str] = []
    for job in jobs:
        if job.md_path is None:
            continue
        slug = Path(job.md_path).stem
        snapshot = snapshots.load(slug)
        if snapshot is not None:
            titles.append(snapshot.metadata.title)
    return titles


def _make_completed_job(*, video_id: str, slug: str, requested_at: datetime) -> Job:
    job = Job.new(VideoId(video_id), 42)
    object.__setattr__(job, "requested_at", requested_at)
    for status in (
        JobStatus.ACQUIRING,
        JobStatus.CONVERTING,
        JobStatus.TRANSCRIBING,
        JobStatus.DIARIZING,
        JobStatus.RENDERING,
        JobStatus.DELIVERING,
        JobStatus.COMPLETED,
    ):
        job.transition_to(status)
    object.__setattr__(job, "updated_at", requested_at)
    job.md_path = f"/tmp/{slug}.md"
    job.canonical_transcript_ref = slug
    return job


def _build_transcript(*, segment_count: int) -> Transcript:
    segments = tuple(
        TranscriptSegment(
            start_seconds=float(index * 4),
            end_seconds=float(index * 4 + 3),
            text=(
                "Este é um trecho de benchmark com texto suficiente para normalização, "
                "paragrafação e deduplicação leve."
            ),
            speaker_label=f"SPEAKER_{index % 2:02d}",
        )
        for index in range(segment_count)
    )
    return Transcript(
        segments=segments,
        language=Language("pt"),
        language_confidence=0.99,
        source="whisperx",
    )


def _build_metadata(slug: str) -> MediaMetadata:
    return MediaMetadata(
        video_id=VideoId(slug[:11].ljust(11, "x")),
        title=f"Título {slug}",
        channel="Canal Benchmark",
        duration=Duration.from_seconds(640),
        upload_date=date(2024, 1, 1),
        original_language=Language("pt"),
    )


def _build_context() -> RenderContext:
    return RenderContext(
        rendered_at=datetime(2026, 5, 1, tzinfo=UTC),
        whisper_model="small",
        diarization_model="pyannote/speaker-diarization-3.1",
        transcription_source="whisperx",
    )


def _build_vtt_fixture() -> str:
    return "\n".join(
        [
            "WEBVTT",
            "",
            *[
                (
                    f"00:00:{index:02d}.000 --> 00:00:{index + 1:02d}.000\n"
                    f"Olá mundo trecho {index} Olá mundo trecho {index}"
                )
                for index in range(20)
            ],
        ]
    )


class _LegacyMarkdownTranscriptRenderer(MarkdownTranscriptRenderer):
    def _render_turns(self, transcript: Transcript, aliases: dict[str, str]) -> list[str]:
        turns = self._readable_turns(transcript)
        if not turns:
            return ["*Nenhum turno de fala disponível.*"]
        out: list[str] = []
        i = 0
        while i < len(turns):
            run_start = turns[i]
            run_display = self._display_speaker(run_start.speaker_label, aliases)
            run_end = run_start
            j = i + 1
            while j < len(turns):
                current_display = self._display_speaker(turns[j].speaker_label, aliases)
                if current_display != run_display:
                    break
                run_end = turns[j]
                j += 1

            start = Duration.from_seconds(run_start.start_seconds).to_hms()
            end = Duration.from_seconds(run_end.end_seconds).to_hms()
            out.append(f"### [{start} — {end}] {run_display}")
            out.append("")
            for turn in turns[i:j]:
                out.extend(self._paragraphize(turn.text))
                out.append("")
            i = j
        return out

    def _readable_turns(self, transcript: Transcript) -> tuple[SpeakerTurn, ...]:
        valid_segments = tuple(
            seg
            for seg in transcript.segments
            if seg.text.strip() and seg.end_seconds > seg.start_seconds
        )
        if not valid_segments:
            return ()

        turns: list[SpeakerTurn] = []
        current_label = valid_segments[0].speaker_label
        current_start = valid_segments[0].start_seconds
        current_end = valid_segments[0].end_seconds
        current_parts: list[str] = [valid_segments[0].text]

        def flush() -> None:
            nonlocal current_start, current_end, current_label, current_parts
            text = self._normalize_text(" ".join(current_parts))
            if text:
                turns.append(
                    SpeakerTurn(
                        start_seconds=current_start,
                        end_seconds=current_end,
                        speaker_label=current_label,
                        text=text,
                    )
                )

        for seg in valid_segments[1:]:
            current_text = self._normalize_text(" ".join(current_parts))
            would_exceed_duration = (seg.end_seconds - current_start) > self.max_block_duration_s
            would_exceed_chars = (len(current_text) + 1 + len(seg.text)) > self.max_block_chars
            speaker_changed = seg.speaker_label != current_label

            if speaker_changed or would_exceed_duration or would_exceed_chars:
                flush()
                current_label = seg.speaker_label
                current_start = seg.start_seconds
                current_end = seg.end_seconds
                current_parts = [seg.text]
            else:
                current_end = seg.end_seconds
                current_parts.append(seg.text)

        flush()
        return tuple(turns)


if __name__ == "__main__":
    _main()
