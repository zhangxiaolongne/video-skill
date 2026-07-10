from __future__ import annotations

import subprocess
from pathlib import Path
from shutil import which


class KeyframeExtractionError(Exception):
    pass


def ffmpeg_version() -> str:
    binary = which("ffmpeg")
    if binary is None:
        return "unknown"
    try:
        result = subprocess.run(
            [binary, "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return "unknown"
    first_line = result.stdout.splitlines()[0] if result.stdout else ""
    return first_line or "unknown"


def extract_keyframe_image(
    *,
    source_path: Path,
    output_path: Path,
    timestamp_seconds: float,
) -> None:
    binary = which("ffmpeg")
    if binary is None:
        raise KeyframeExtractionError("ffmpeg is not available")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            binary,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{timestamp_seconds:.3f}",
            "-i",
            str(source_path),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise KeyframeExtractionError(detail or "ffmpeg keyframe extraction failed")
    if not output_path.exists():
        raise KeyframeExtractionError("ffmpeg did not write keyframe output")
