"""Speech scan that returns timed words for lyric alignment.

The speech model is loaded once per process. The first scan downloads it.
ponytail: voice-activity filtering is off because onnxruntime has no Intel
macOS wheel. Turn vad_filter on when that wheel exists.
"""

from __future__ import annotations

import logging
from pathlib import Path
from threading import Lock
from typing import Any

from app.align import TimedWord

logger = logging.getLogger(__name__)

_lock = Lock()
_models: dict[str, Any] = {}


class ScanUnavailable(Exception):
    """The scan could not produce timed words."""


def transcribe_words(path: Path, language: str, model_name: str) -> list[TimedWord]:
    with _lock:
        model = _model(model_name)
        code = language.strip() or None
        try:
            segments, _info = model.transcribe(
                str(path),
                language=code,
                word_timestamps=True,
                vad_filter=False,
                beam_size=1,
            )
            words: list[TimedWord] = []
            for segment in segments:
                for word in segment.words or []:
                    text = (word.word or "").strip()
                    probability = float(getattr(word, "probability", 1.0))
                    start = float(word.start)
                    end = float(word.end)
                    if text and probability >= 0.2 and end >= start:
                        words.append(TimedWord(text, start, end))
        except ScanUnavailable:
            raise
        except Exception as exc:
            logger.exception("lyric scan failed")
            raise ScanUnavailable("The scan could not read this song.") from exc
    if not words:
        raise ScanUnavailable("The scan did not hear any words in this song.")
    return words


def _model(model_name: str) -> Any:
    cached = _models.get(model_name)
    if cached is not None:
        return cached
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise ScanUnavailable("The timing scan is not installed. From the backend directory, run uv sync.") from exc
    cached = WhisperModel(model_name, device="cpu", compute_type="int8")
    _models[model_name] = cached
    return cached
