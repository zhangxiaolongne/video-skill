from __future__ import annotations

import os
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path


class TranscriptionError(Exception):
    pass


@dataclass(frozen=True)
class TranscribedWord:
    word: str
    start_seconds: float
    end_seconds: float
    confidence: float | None = None


@dataclass(frozen=True)
class TranscribedSegment:
    start_seconds: float
    end_seconds: float
    text: str
    language: str | None = None
    confidence: float = 0.0
    words: list[TranscribedWord] = field(default_factory=list)


def faster_whisper_version() -> str:
    try:
        return metadata.version("faster-whisper")
    except metadata.PackageNotFoundError:
        return "unknown"


def transcribe_source_faster_whisper(path: Path) -> list[TranscribedSegment]:
    try:
        from faster_whisper import WhisperModel
    except Exception as exc:
        raise TranscriptionError("faster-whisper is not installed") from exc

    model_name = os.environ.get("ARTIST_PORTRAIT_WHISPER_MODEL", "base")
    try:
        model = WhisperModel(
            model_name,
            device="auto",
            compute_type="default",
            local_files_only=True,
        )
        raw_segments, info = model.transcribe(str(path), word_timestamps=True)
    except Exception as exc:
        raise TranscriptionError(
            "faster-whisper failed with local-only model loading; set "
            "ARTIST_PORTRAIT_WHISPER_MODEL to a local model path"
        ) from exc

    language = getattr(info, "language", None)
    segments: list[TranscribedSegment] = []
    for raw_segment in raw_segments:
        words: list[TranscribedWord] = []
        for raw_word in getattr(raw_segment, "words", None) or []:
            word = str(getattr(raw_word, "word", "")).strip()
            start = getattr(raw_word, "start", None)
            end = getattr(raw_word, "end", None)
            if not word or start is None or end is None or float(end) <= float(start):
                continue
            words.append(
                TranscribedWord(
                    word=word,
                    start_seconds=round(float(start), 3),
                    end_seconds=round(float(end), 3),
                    confidence=getattr(raw_word, "probability", None),
                )
            )

        start_seconds = round(float(raw_segment.start), 3)
        end_seconds = round(float(raw_segment.end), 3)
        text = str(raw_segment.text or "").strip()
        if end_seconds <= start_seconds:
            continue
        confidence = _segment_confidence(raw_segment)
        segments.append(
            TranscribedSegment(
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                text=text,
                language=language,
                confidence=confidence,
                words=words,
            )
        )
    return segments


def _segment_confidence(raw_segment: object) -> float:
    avg_logprob = getattr(raw_segment, "avg_logprob", None)
    if avg_logprob is None:
        return 0.5
    try:
        # Map a rough log probability range to the Pydantic confidence contract.
        return max(0.0, min(1.0, (float(avg_logprob) + 5.0) / 5.0))
    except (TypeError, ValueError):
        return 0.5
