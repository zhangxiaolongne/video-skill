from __future__ import annotations

from importlib.util import find_spec
from shutil import which

from artist_portrait_editor.models.state import Capabilities


def detect_capabilities() -> Capabilities:
    return Capabilities(
        ffmpeg=which("ffmpeg") is not None,
        ffprobe=which("ffprobe") is not None,
        pyscenedetect=which("scenedetect") is not None or find_spec("scenedetect") is not None,
        faster_whisper=find_spec("faster_whisper") is not None,
        opencv=find_spec("cv2") is not None,
        beat_librosa=find_spec("librosa") is not None,
        beat_aubio=find_spec("aubio") is not None,
        beat_essentia=find_spec("essentia") is not None,
        beat_madmom=find_spec("madmom") is not None,
        text_model=False,
        vision_model=False,
    )


def capability_warnings(capabilities: Capabilities) -> list[str]:
    warnings: list[str] = []
    if not capabilities.ffmpeg:
        warnings.append("ffmpeg not found; media commands will be blocked")
    if not capabilities.ffprobe:
        warnings.append("ffprobe not found; media commands will be blocked")
    return warnings
