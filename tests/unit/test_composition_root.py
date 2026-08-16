from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any

import pytest

from yt_transcriber_bot.application.config import AppSettings
from yt_transcriber_bot.application.ports.gpu_detector import HardwareProfile
from yt_transcriber_bot.composition_root import _make_gpu_detector


def _settings(tmp_path: Any, **overrides: object) -> AppSettings:
    values: dict[str, object] = {
        "telegram_bot_token": "123:token",
        "telegram_allowed_user_id": 42,
        "hf_token": "hf_test",
        "base_dir": tmp_path / "data",
        "models_dir": tmp_path / "models",
        "db_path": tmp_path / "data" / "jobs.db",
        "summary_backend": "disabled",
    }
    values.update(overrides)
    return AppSettings(**values)


def _patch_heavy_ml(
    monkeypatch: pytest.MonkeyPatch,
    composition_root: Any,
) -> None:
    monkeypatch.setattr(composition_root, "_make_gpu_detector", lambda: object())
    monkeypatch.setattr(
        composition_root,
        "_make_transcription_engine",
        lambda: object(),
    )
    monkeypatch.setattr(
        composition_root,
        "_make_diarization_engine",
        lambda _hf_token: object(),
    )


def test_make_gpu_detector_falls_back_to_cpu_stub_when_torch_detector_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(
        sys.modules,
        "yt_transcriber_bot.infrastructure.gpu.torch_gpu_detector",
        None,
    )
    detector = _make_gpu_detector()
    profile = detector.detect()
    assert isinstance(profile, HardwareProfile)
    assert profile.has_cuda is False
    assert profile.cuda_compute_capability is None
    assert profile.vram_total_gb == 0.0
    assert profile.gpu_name == ""


def test_build_wires_credentials_and_runtime_tokenizer_at_composition(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    import yt_transcriber_bot.composition_root as composition_root

    diarization: dict[str, str] = {}
    youtube: dict[str, object] = {}
    video_export: dict[str, object] = {}
    summary_client: dict[str, object] = {}
    summary_service: dict[str, object] = {}
    tokenizer_args: dict[str, object] = {}
    healthcheck: dict[str, object] = {}
    health_environment: dict[str, object] = {}
    tokenizer = object()

    monkeypatch.setattr(composition_root, "_make_gpu_detector", lambda: object())
    monkeypatch.setattr(composition_root, "_make_transcription_engine", lambda: object())

    def fake_diarization(hf_token: str) -> object:
        diarization["hf_token"] = hf_token
        return object()

    monkeypatch.setattr(composition_root, "_make_diarization_engine", fake_diarization)

    class FakeYtDlpDownloader:
        def __init__(self, **kwargs: object) -> None:
            youtube.update(kwargs)

    class FakeVideoSubtitleService:
        def __init__(self, **kwargs: object) -> None:
            video_export.update(kwargs)

    class FakeSummaryClient:
        def __init__(self, **kwargs: object) -> None:
            summary_client.update(kwargs)

    class FakeSummaryService:
        def __init__(self, **kwargs: object) -> None:
            summary_service.update(kwargs)

    class FakeHealthCheckService:
        def __init__(self, **kwargs: object) -> None:
            healthcheck.update(kwargs)

    class FakeHealthEnvironmentProbe:
        def __init__(self, **kwargs: object) -> None:
            health_environment.update(kwargs)

    def fake_tokenizer(**kwargs: object) -> object:
        tokenizer_args.update(kwargs)
        return tokenizer

    monkeypatch.setattr(composition_root, "YtDlpDownloader", FakeYtDlpDownloader)
    monkeypatch.setattr(
        composition_root,
        "VideoSoftSubtitleExportService",
        FakeVideoSubtitleService,
    )
    monkeypatch.setattr(composition_root, "OpenAICompatibleChatClient", FakeSummaryClient)
    monkeypatch.setattr(composition_root, "TranscriptSummaryService", FakeSummaryService)
    monkeypatch.setattr(composition_root, "HealthCheckService", FakeHealthCheckService)
    monkeypatch.setattr(composition_root, "LocalHealthEnvironmentProbe", FakeHealthEnvironmentProbe)
    monkeypatch.setattr(composition_root, "make_text_tokenizer", fake_tokenizer)

    settings = _settings(
        tmp_path,
        summary_backend="openai_compatible",
        summary_api_key="summary-placeholder",
        youtube_cookies_file="/tmp/cookies.txt",
        youtube_cookies_browser="firefox",
        summary_tokenizer_backend="hf",
        summary_tokenizer_model="local/tokenizer",
        summary_tokenizer_trust_remote_code=True,
    )
    composition = composition_root.build(
        settings,
        credentials=settings.credentials,
    )

    assert composition.summary_service is not None
    assert diarization["hf_token"] == "hf_test"
    assert youtube["cookies_file"] == "/tmp/cookies.txt"
    assert youtube["cookies_browser"] == "firefox"
    assert video_export["cookies_file"] == "/tmp/cookies.txt"
    assert video_export["cookies_browser"] == "firefox"
    assert summary_client["api_key"] == "summary-placeholder"
    assert summary_client["base_url"] == settings.summary_base_url
    assert tokenizer_args == {
        "backend": "hf",
        "model": "local/tokenizer",
        "chars_per_token": settings.summary_chars_per_token,
        "trust_remote_code": True,
    }
    assert summary_service["tokenizer"] is tokenizer
    assert summary_service["tokenizer_trust_remote_code"] is True
    assert health_environment["models_probe"] is composition_root.probe_openai_compatible_models
    assert health_environment["executable_finder"] is composition_root.find_executable
    assert health_environment["module_checker"] is composition_root.module_available
    assert health_environment["disk_usage"] is composition_root.local_disk_usage
    assert health_environment["sqlite_probe"] is not None
    assert isinstance(healthcheck["environment_probe"], FakeHealthEnvironmentProbe)


def test_disabled_summary_skips_optional_provider_construction_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    import yt_transcriber_bot.composition_root as composition_root

    _patch_heavy_ml(monkeypatch, composition_root)

    def must_not_run(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("disabled summary must not construct optional providers")

    monkeypatch.setattr(composition_root, "OpenAICompatibleChatClient", must_not_run)
    monkeypatch.setattr(composition_root, "TranscriptSummaryService", must_not_run)
    monkeypatch.setattr(composition_root, "make_text_tokenizer", must_not_run)

    settings = _settings(
        tmp_path,
        summary_backend="disabled",
        summary_api_key="",
    )
    composition = composition_root.build(
        settings,
        credentials=settings.credentials,
    )

    assert settings.credentials.summary_api_key == ""
    assert composition.summary_service is None


def test_build_smoke_constructs_core_graph_without_external_network(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    import yt_transcriber_bot.composition_root as composition_root

    _patch_heavy_ml(monkeypatch, composition_root)
    settings = _settings(tmp_path, summary_backend="disabled")
    composition = composition_root.build(
        settings,
        credentials=settings.credentials,
    )

    assert composition.settings is settings
    assert composition.repository is not None
    assert composition.snapshots is not None
    assert composition.use_case is not None
    assert composition.summary_service is None
    assert composition.healthcheck_service is not None
    assert composition.retention_policy is not None


def test_build_runtime_owns_telegram_provider_graph(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    import yt_transcriber_bot.composition_root as composition_root
    from yt_transcriber_bot.infrastructure.telegram.audience import DeniedAudienceFilter
    from yt_transcriber_bot.infrastructure.telegram.bot_adapter import TelegramBotAdapter

    settings = _settings(tmp_path)
    core = SimpleNamespace(
        use_case=object(),
        repository=object(),
        rename_service=object(),
        export_service=object(),
        plain_text_export_service=object(),
        summary_service=None,
        video_subtitle_export_service=object(),
        healthcheck_service=object(),
        history_search_service=object(),
        lasterror_service=object(),
        retention_policy=object(),
        audit_logger=object(),
        search_indexing_service=SimpleNamespace(refresh=lambda _job: None),
        text_search_workflow=object(),
        derivative_workflow=object(),
        summary_workflow=None,
        operational_workflow=object(),
    )
    application = SimpleNamespace(bot=object())
    captured: dict[str, object] = {}

    def fake_build(actual_settings: AppSettings, *, credentials: object) -> Any:
        captured["core_settings"] = actual_settings
        captured["core_credentials"] = credentials
        return core

    def fake_application(bot_token: str) -> object:
        captured["telegram_token"] = bot_token
        return application

    monkeypatch.setattr(composition_root, "build", fake_build)
    monkeypatch.setattr(composition_root, "_make_telegram_application", fake_application)

    runtime = composition_root.build_runtime(
        settings,
        credentials=settings.credentials,
    )

    assert captured["core_settings"] is settings
    assert captured["core_credentials"] is settings.credentials
    assert captured["telegram_token"] == "123:token"
    assert runtime.core is core
    assert runtime.application is application
    assert isinstance(runtime.adapter, TelegramBotAdapter)
    assert runtime.adapter._text_search_workflow is core.text_search_workflow
    assert runtime.adapter._derivative_workflow is core.derivative_workflow
    assert runtime.adapter._summary_workflow is core.summary_workflow
    assert runtime.adapter._operational_workflow is core.operational_workflow
    assert runtime.adapter._search_indexing_service is core.search_indexing_service
    assert runtime.adapter._rename_service is None
    assert runtime.adapter._export_service is None
    assert runtime.adapter._plain_text_export_service is None
    assert runtime.adapter._summary_service is None
    assert runtime.adapter._video_subtitle_export_service is None
    assert runtime.adapter._history_search_service is None
    assert runtime.adapter._healthcheck_service is None
    assert runtime.adapter._lasterror_service is None
    assert runtime.adapter._retention_policy is None
    assert runtime.audience.allowed_user_id == 42
    assert isinstance(runtime.denied_audience_filter, DeniedAudienceFilter)
