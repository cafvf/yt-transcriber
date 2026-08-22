"""Gate A: prove canonical Job state across legacy SQL columns."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from yt_transcriber_bot.domain.entities.job import Job
from yt_transcriber_bot.domain.value_objects.language import Language
from yt_transcriber_bot.domain.value_objects.video_id import VideoId
from yt_transcriber_bot.infrastructure.persistence.sqlalchemy.job_repository import (
    SqlAlchemyJobRepository,
)

pytestmark = pytest.mark.integration


def test_processing_fingerprint_and_language_round_trip_through_legacy_sql() -> None:
    repo = SqlAlchemyJobRepository.from_url("sqlite:///:memory:")
    job = Job.new(
        VideoId("dQw4w9WgXcQ"),
        user_id=42,
        processing_fingerprint="fp-canonical",
        requested_language=Language("pt"),
    )

    repo.save(job)
    loaded = repo.get_by_id(job.job_id)

    assert loaded is not None
    assert loaded.processing_fingerprint == "fp-canonical"
    assert loaded.requested_language == Language("pt")

    with repo._engine.connect() as connection:
        row = connection.execute(
            text("SELECT config_signature, artifact_policy FROM jobs WHERE job_id = :job_id"),
            {"job_id": job.job_id},
        ).one()

    assert row.config_signature == "fp-canonical"
    assert row.artifact_policy == "audio+markdown"


def test_legacy_config_signature_value_loads_as_processing_fingerprint() -> None:
    repo = SqlAlchemyJobRepository.from_url("sqlite:///:memory:")
    job = Job.new(VideoId("dQw4w9WgXcQ"), user_id=42)
    repo.save(job)

    with repo._engine.begin() as connection:
        connection.execute(
            text("UPDATE jobs SET config_signature = :fingerprint WHERE job_id = :job_id"),
            {
                "fingerprint": "legacy-physical-value",
                "job_id": job.job_id,
            },
        )

    loaded = repo.get_by_id(job.job_id)

    assert loaded is not None
    assert loaded.processing_fingerprint == "legacy-physical-value"
