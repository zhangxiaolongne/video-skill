from __future__ import annotations

import json
import subprocess
from pathlib import Path

from artist_portrait_editor.models.source import MediaKind, MediaProbe


class ProbeError(Exception):
    pass


def parse_frame_rate(value: str | None) -> float | None:
    if not value or value == "0/0":
        return None
    if "/" in value:
        numerator, denominator = value.split("/", 1)
        try:
            denominator_float = float(denominator)
            if denominator_float == 0:
                return None
            return float(numerator) / denominator_float
        except ValueError:
            return None
    try:
        return float(value)
    except ValueError:
        return None


def probe_media(path: Path) -> tuple[MediaKind, MediaProbe]:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        message = completed.stderr.strip() or "ffprobe failed"
        raise ProbeError(message)
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ProbeError("ffprobe returned invalid JSON") from exc
    return media_probe_from_ffprobe(payload)


def media_probe_from_ffprobe(payload: dict) -> tuple[MediaKind, MediaProbe]:
    streams = payload.get("streams") or []
    format_info = payload.get("format") or {}
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    if video_stream is None and audio_stream is None:
        raise ProbeError("no audio or video streams found")
    duration = (
        (video_stream or {}).get("duration")
        or (audio_stream or {}).get("duration")
        or format_info.get("duration")
    )
    try:
        duration_float = float(duration)
    except (TypeError, ValueError) as exc:
        raise ProbeError("media duration is missing or invalid") from exc
    if duration_float <= 0:
        raise ProbeError("media duration must be positive")

    if video_stream is not None:
        return (
            MediaKind.video,
            MediaProbe(
                duration=duration_float,
                width=video_stream.get("width"),
                height=video_stream.get("height"),
                frame_rate=parse_frame_rate(video_stream.get("avg_frame_rate")),
                video_codec=video_stream.get("codec_name"),
                audio_present=audio_stream is not None,
                audio_codec=(audio_stream or {}).get("codec_name"),
            ),
        )
    return (
        MediaKind.audio,
        MediaProbe(
            duration=duration_float,
            width=None,
            height=None,
            frame_rate=None,
            video_codec=None,
            audio_present=True,
            audio_codec=audio_stream.get("codec_name"),
        ),
    )
