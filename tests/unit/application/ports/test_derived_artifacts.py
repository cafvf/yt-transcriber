from __future__ import annotations

import pytest

from yt_transcriber_bot.application.ports.derived_artifacts import DerivedArtifactAssociation
from yt_transcriber_bot.domain.entities.job import Job
from yt_transcriber_bot.domain.value_objects.artifact import ArtifactClass
from yt_transcriber_bot.domain.value_objects.video_id import VideoId


def test_derived_association_binds_job_and_canonical_reference() -> None:
    job = Job.new(VideoId("dQw4w9WgXcQ"), user_id=7)
    job.canonical_transcript_ref = "canonical"
    association = DerivedArtifactAssociation.from_job(job, ArtifactClass.DERIVED_EXPORT)
    assert association.job_id == job.job_id
    assert association.canonical_transcript_ref == "canonical"


def test_canonical_or_volatile_class_cannot_masquerade_as_derivative() -> None:
    with pytest.raises(ValueError, match="artifact class is not derived"):
        DerivedArtifactAssociation("job", "canonical", ArtifactClass.CANONICAL_MARKDOWN)
    with pytest.raises(ValueError, match="artifact class is not derived"):
        DerivedArtifactAssociation("job", "canonical", ArtifactClass.VOLATILE_SOURCE_MEDIA)
