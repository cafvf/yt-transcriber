"""Testes do ProgressReporter — edição de uma única mensagem."""

from __future__ import annotations

import pytest

from yt_transcriber_bot.infrastructure.telegram.progress_reporter import (
    TRANSCRIPTION_MILESTONES,
    ProgressReporter,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeEditor:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.raise_on_next: BaseException | None = None

    async def __call__(self, text: str) -> None:
        if self.raise_on_next is not None:
            exc, self.raise_on_next = self.raise_on_next, None
            raise exc
        self.calls.append(text)


@pytest.mark.asyncio
async def test_set_title_emits_immediately() -> None:
    editor = FakeEditor()
    clock = FakeClock()
    rep = ProgressReporter(editor, clock=clock, min_interval_s=2.0)
    await rep.set_title("Vídeo X")
    assert len(editor.calls) == 1
    assert "Vídeo X" in editor.calls[0]


@pytest.mark.asyncio
async def test_transcription_milestones_emit_at_each_threshold() -> None:
    editor = FakeEditor()
    clock = FakeClock()
    rep = ProgressReporter(editor, clock=clock, min_interval_s=0.0)
    await rep.set_title("Y")
    await rep.stage("Transcrevendo")
    editor.calls.clear()

    # Frações sub-marco não emitem novas mensagens
    await rep.transcription_progress(0.05)
    await rep.transcription_progress(0.09)
    assert editor.calls == []

    # 0.10 cruza o primeiro marco
    await rep.transcription_progress(0.10)
    assert any("10%" in c for c in editor.calls)

    # 0.30 cruza só o marco 0.25 (sem pular para 0.50)
    await rep.transcription_progress(0.30)
    last = editor.calls[-1]
    assert "25%" in last
    assert "50%" not in last

    # Cruza todos os marcos restantes
    await rep.transcription_progress(0.95)
    assert any("50%" in c for c in editor.calls)
    assert any("75%" in c for c in editor.calls)
    assert any("90%" in c for c in editor.calls)


@pytest.mark.asyncio
async def test_progress_jumps_emit_all_crossed_milestones() -> None:
    # Regressão G5.1: chamada única que cruza vários marcos deve emitir todos.
    editor = FakeEditor()
    clock = FakeClock()
    rep = ProgressReporter(editor, clock=clock, min_interval_s=0.0)
    await rep.set_title("R")
    await rep.stage("Transcrevendo")
    editor.calls.clear()
    await rep.transcription_progress(0.95)
    # Deve ter emitido para 10/25/50/75/90.
    percentuais_emitidos = [
        p for p in ("10%", "25%", "50%", "75%", "90%") if any(p in c for c in editor.calls)
    ]
    assert percentuais_emitidos == ["10%", "25%", "50%", "75%", "90%"]


@pytest.mark.asyncio
async def test_milestones_are_exactly_five() -> None:
    assert TRANSCRIPTION_MILESTONES == (0.10, 0.25, 0.50, 0.75, 0.90)


@pytest.mark.asyncio
async def test_does_not_emit_duplicate_text() -> None:
    editor = FakeEditor()
    clock = FakeClock()
    rep = ProgressReporter(editor, clock=clock, min_interval_s=0.0)
    await rep.set_title("Z")
    await rep.set_title("Z")  # mesmo título
    assert len(editor.calls) == 1


@pytest.mark.asyncio
async def test_debounce_blocks_non_forced_updates() -> None:
    editor = FakeEditor()
    clock = FakeClock()
    rep = ProgressReporter(editor, clock=clock, min_interval_s=2.0)
    await rep.set_title("A")
    # Diagnóstico (não-forçado) não deve emitir antes de 2s
    await rep.diagnostic("info1")
    assert len(editor.calls) == 1  # apenas o título
    clock.advance(2.5)
    await rep.diagnostic("info2")
    assert len(editor.calls) == 2  # diagnóstico após debounce


@pytest.mark.asyncio
async def test_forced_updates_bypass_debounce() -> None:
    editor = FakeEditor()
    clock = FakeClock()
    rep = ProgressReporter(editor, clock=clock, min_interval_s=10.0)
    await rep.set_title("A")
    await rep.stage("Estágio X")  # forçado
    assert len(editor.calls) == 2


@pytest.mark.asyncio
async def test_editor_failure_is_swallowed() -> None:
    editor = FakeEditor()
    editor.raise_on_next = RuntimeError("rate limit")
    clock = FakeClock()
    rep = ProgressReporter(editor, clock=clock, min_interval_s=0.0)
    # Não deve levantar
    await rep.set_title("A")
    # Próxima chamada já não falha
    await rep.set_title("B")
    assert any("B" in c for c in editor.calls)


@pytest.mark.asyncio
async def test_finish_marks_100_percent() -> None:
    editor = FakeEditor()
    clock = FakeClock()
    rep = ProgressReporter(editor, clock=clock, min_interval_s=0.0)
    await rep.set_title("Z")
    await rep.finish("✅ Pronto")
    assert any("Pronto" in c for c in editor.calls)
    assert any("100%" in c for c in editor.calls)


@pytest.mark.asyncio
async def test_stage_transition_does_not_reset_visible_percent() -> None:
    editor = FakeEditor()
    clock = FakeClock()
    rep = ProgressReporter(editor, clock=clock, min_interval_s=0.0)
    await rep.set_title("Z")
    await rep.stage("🎙️ Transcrevendo")
    await rep.transcription_progress(0.90)
    await rep.stage("👥 Identificando falantes")

    last = editor.calls[-1]
    assert "Identificando falantes" in last
    assert "90%" in last
    assert " 0%" not in last


@pytest.mark.asyncio
async def test_updates_after_finish_are_ignored() -> None:
    editor = FakeEditor()
    clock = FakeClock()
    rep = ProgressReporter(editor, clock=clock, min_interval_s=0.0)
    await rep.set_title("Z")
    await rep.finish("✅ Pronto")
    finished_text = editor.calls[-1]

    await rep.stage("📥 Atualização atrasada")
    await rep.transcription_progress(0.10)
    await rep.diagnostic("diagnóstico atrasado")

    assert editor.calls[-1] == finished_text
    assert all("Atualização atrasada" not in call for call in editor.calls)
    assert all("diagnóstico atrasado" not in call for call in editor.calls)


@pytest.mark.asyncio
async def test_diagnostics_are_capped() -> None:
    editor = FakeEditor()
    clock = FakeClock()
    rep = ProgressReporter(editor, clock=clock, min_interval_s=0.0)
    await rep.set_title("Z")
    await rep.diagnostic("d1")
    await rep.diagnostic("d2")
    await rep.diagnostic("d3")
    await rep.diagnostic("d4")
    last = editor.calls[-1]
    assert "d2" in last
    assert "d3" in last
    assert "d4" in last
    assert "d1" not in last  # truncado para 3
