"""Compatibilidade entre versoes de WhisperX/pyannote para diarizacao."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, TypeVar

T = TypeVar("T")


def call_with_hf_token(factory: Any, /, *args: Any, hf_token: str, **kwargs: Any) -> Any:
    """Chama factories Hugging Face tentando ``token`` e ``use_auth_token``.

    Versoes recentes de ``pyannote.audio``/``whisperx`` usam ``token``. Versoes
    antigas usavam ``use_auth_token``. O fallback abaixo evita acoplamento
    fragil a uma versao especifica da API.
    """

    try:
        return factory(*args, token=hf_token, **kwargs)
    except TypeError as exc:
        if "token" not in str(exc):
            raise
        return factory(*args, use_auth_token=hf_token, **kwargs)


def iter_speaker_turns(annotation: Any) -> Iterable[tuple[float, float, str]]:
    """Extrai ``(start, end, speaker)`` de saidas pyannote/WhisperX.

    Formatos suportados:
    - pyannote antigo: ``Annotation.itertracks(yield_label=True)``;
    - pyannote.audio 4.x: objeto com ``speaker_diarization`` ou
      ``exclusive_speaker_diarization``;
    - pandas DataFrame: colunas ``start``, ``end`` e ``speaker``;
    - iteraveis de dicts ou objetos simples com atributos homonimos.
    """

    # pyannote.audio 4.x retorna um objeto de saida com estes atributos.
    diar = getattr(annotation, "exclusive_speaker_diarization", None)
    if diar is None:
        diar = getattr(annotation, "speaker_diarization", None)
    if diar is not None:
        yield from iter_speaker_turns(diar)
        return

    # pyannote Annotation classica.
    itertracks = getattr(annotation, "itertracks", None)
    if callable(itertracks):
        for segment, _, label in itertracks(yield_label=True):
            start = _as_float(getattr(segment, "start", None))
            end = _as_float(getattr(segment, "end", None))
            speaker = str(label)
            if _valid_turn(start, end, speaker):
                yield start, end, speaker
        return

    # pandas.DataFrame ou objetos com iterrows.
    iterrows = getattr(annotation, "iterrows", None)
    if callable(iterrows):
        for _, row in iterrows():
            parsed = _parse_row(row)
            if parsed is not None:
                yield parsed
        return

    # pyannote.audio 4.x: for turn, speaker in output.speaker_diarization.
    try:
        iterator = iter(annotation)
    except TypeError:
        return

    for item in iterator:
        parsed = _parse_iter_item(item)
        if parsed is not None:
            yield parsed


def _parse_iter_item(item: Any) -> tuple[float, float, str] | None:
    if isinstance(item, tuple):
        if len(item) == 2:
            turn, speaker = item
            start = _as_float(getattr(turn, "start", None))
            end = _as_float(getattr(turn, "end", None))
            label = str(speaker)
            if _valid_turn(start, end, label):
                return start, end, label
        if len(item) >= 3:
            turn, _, speaker = item[:3]
            start = _as_float(getattr(turn, "start", None))
            end = _as_float(getattr(turn, "end", None))
            label = str(speaker)
            if _valid_turn(start, end, label):
                return start, end, label
    return _parse_row(item)


def _parse_row(row: Any) -> tuple[float, float, str] | None:
    if isinstance(row, dict):
        start = _as_float(row.get("start"))
        end = _as_float(row.get("end"))
        speaker = str(row.get("speaker", "SPEAKER_00"))
    else:
        getter = getattr(row, "get", None)
        if callable(getter):
            start = _as_float(getter("start", None))
            end = _as_float(getter("end", None))
            speaker = str(getter("speaker", "SPEAKER_00"))
        else:
            start = _as_float(getattr(row, "start", None))
            end = _as_float(getattr(row, "end", None))
            speaker = str(getattr(row, "speaker", "SPEAKER_00"))
    if _valid_turn(start, end, speaker):
        return start, end, speaker
    return None


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _valid_turn(start: float, end: float, speaker: str) -> bool:
    return start == start and end == end and end > start and bool(speaker)
