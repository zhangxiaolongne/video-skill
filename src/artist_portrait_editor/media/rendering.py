from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from artist_portrait_editor.bgm import load_ledger
from artist_portrait_editor.models.bgm import BgmFitPlan
from artist_portrait_editor.models.timeline import TimelineDraft
from artist_portrait_editor.models.composition import PixelCropBox


class MediaRenderError(ValueError):
    pass


@dataclass(frozen=True)
class RenderCanvas:
    width: int
    height: int
    fps: int
    aspect_ratio: str
    fit_mode: str = "contain"


def canvas_from_width(*, width: int, aspect_ratio: str, fps: int) -> RenderCanvas:
    ratio_width, ratio_height = parse_aspect_ratio(aspect_ratio)
    height = _even(round(width * ratio_height / ratio_width))
    return RenderCanvas(width, height, fps, aspect_ratio)


def canvas_from_short_edge(*, short_edge: int, aspect_ratio: str, fps: int) -> RenderCanvas:
    ratio_width, ratio_height = parse_aspect_ratio(aspect_ratio)
    if ratio_width >= ratio_height:
        width = _even(round(short_edge * ratio_width / ratio_height))
        height = short_edge
    else:
        width = short_edge
        height = _even(round(short_edge * ratio_height / ratio_width))
    return RenderCanvas(width, height, fps, aspect_ratio)


def parse_aspect_ratio(value: str) -> tuple[int, int]:
    try:
        width_text, height_text = value.split(":", maxsplit=1)
        width, height = int(width_text), int(height_text)
    except (AttributeError, TypeError, ValueError) as exc:
        raise MediaRenderError(f"invalid aspect ratio: {value!r}") from exc
    if width <= 0 or height <= 0:
        raise MediaRenderError(f"invalid aspect ratio: {value!r}")
    return width, height


def render_video_segment(
    *,
    source_path: Path,
    output_path: Path,
    source_in: float,
    duration: float,
    canvas: RenderCanvas,
    video_transition: str,
    preset: str,
    crf: int,
    timeout: int,
    crop_box: PixelCropBox | None = None,
) -> tuple[bool, str | None]:
    filters = []
    if crop_box is not None:
        filters.append(f"crop={crop_box.width}:{crop_box.height}:{crop_box.x}:{crop_box.y}")
    filters.extend([
        (
            f"scale={canvas.width}:{canvas.height}:force_original_aspect_ratio=decrease,"
            f"pad={canvas.width}:{canvas.height}:(ow-iw)/2:(oh-ih)/2:color=black,"
            "setsar=1"
        ),
        f"fps={canvas.fps}",
        "format=yuv420p",
    ])
    rendered, warning = _video_transition_filters(filters, video_transition, duration)
    run_ffmpeg(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", f"{source_in:.3f}", "-t", f"{duration:.3f}", "-i", str(source_path),
            "-an", "-vf", ",".join(filters), "-c:v", "libx264", "-preset", preset,
            "-crf", str(crf), str(output_path),
        ],
        output_path,
        timeout=timeout,
    )
    return rendered, warning


def render_black_video(
    *,
    output_path: Path,
    duration: float,
    canvas: RenderCanvas,
    video_transition: str,
    preset: str,
    crf: int,
    timeout: int,
) -> tuple[bool, str | None]:
    filters = ["format=yuv420p"]
    rendered, warning = _video_transition_filters(filters, video_transition, duration)
    run_ffmpeg(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
            "-i", f"color=c=black:s={canvas.width}x{canvas.height}:d={duration:.3f}:r={canvas.fps}",
            "-an", "-vf", ",".join(filters), "-c:v", "libx264", "-preset", preset,
            "-crf", str(crf), str(output_path),
        ],
        output_path,
        timeout=timeout,
    )
    return rendered, warning


def render_audio_segment(
    *,
    source_path: Path,
    output_path: Path,
    source_in: float,
    duration: float,
    audio_transition: str = "none",
    timeout: int = 180,
) -> tuple[bool, str | None]:
    filters: list[str] = []
    rendered, warning = _audio_transition_filters(filters, audio_transition, duration)
    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{source_in:.3f}",
        "-t", f"{duration:.3f}", "-i", str(source_path), "-vn",
    ]
    if filters:
        command.extend(["-af", ",".join(filters)])
    command.extend(["-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", str(output_path)])
    run_ffmpeg(command, output_path, timeout=timeout)
    return rendered, warning


def render_silence(*, output_path: Path, duration: float, timeout: int = 180) -> None:
    run_ffmpeg(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
            "-i", "anullsrc=channel_layout=stereo:sample_rate=48000", "-t", f"{duration:.3f}",
            "-c:a", "pcm_s16le", str(output_path),
        ],
        output_path,
        timeout=timeout,
    )


def concat_files(paths: list[Path], output_path: Path, *, media_type: str, timeout: int = 180) -> None:
    if not paths:
        raise MediaRenderError(f"cannot concatenate empty {media_type} segment list")
    list_path = output_path.with_suffix(".concat.txt")
    list_path.write_text("".join(f"file '{path.as_posix()}'\n" for path in paths), encoding="utf-8")
    codec = ["-c", "copy"] if media_type == "video" else ["-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le"]
    run_ffmpeg(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(list_path), *codec, str(output_path)],
        output_path,
        timeout=timeout,
    )


def render_bgm_track(*, root: Path, project_id: str, plan: BgmFitPlan, output_path: Path, timeout: int = 180) -> None:
    ledger = load_ledger(root / ".artist-portrait" / "data" / "bgm_candidates.json", project_id)
    candidate = next((item for item in ledger.candidates if item.music_candidate_id == plan.music_candidate_id), None)
    if candidate is None:
        raise MediaRenderError("BGM fit references unknown candidate")
    source = root / candidate.cache_ref
    if not source.exists():
        raise MediaRenderError("BGM candidate cache audio is missing")
    segment_paths: list[Path] = []
    for index, segment in enumerate(plan.segments, start=1):
        segment_path = output_path.with_name(f"bgm_{index:03d}.wav")
        render_audio_segment(source_path=source, output_path=segment_path, source_in=segment.source_in, duration=segment.source_out - segment.source_in, timeout=timeout)
        segment_paths.append(segment_path)
    concatenated = output_path.with_name("bgm_concat.wav")
    concat_files(segment_paths, concatenated, media_type="audio", timeout=timeout)
    filters = [f"volume={plan.target_gain_db}dB"]
    if plan.fade_in_seconds > 0:
        filters.append(f"afade=t=in:st=0:d={plan.fade_in_seconds:.3f}")
    if plan.fade_out_seconds > 0:
        filters.append(f"afade=t=out:st={max(0.0, plan.target_duration - plan.fade_out_seconds):.3f}:d={plan.fade_out_seconds:.3f}")
    run_ffmpeg(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(concatenated), "-af", ",".join(filters), "-t", f"{plan.target_duration:.3f}", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", str(output_path)],
        output_path,
        timeout=timeout,
    )


def mix_audio(*, original_audio: Path, bgm_audio: Path, output_path: Path, ducking_intervals: list[tuple[float, float, float]], timeout: int = 180) -> None:
    duck_filters = [f"volume=enable='between(t,{start:.3f},{end:.3f})':volume={10 ** (gain / 20):.6f}" for start, end, gain in ducking_intervals]
    bgm_chain = ",".join(duck_filters) if duck_filters else "anull"
    run_ffmpeg(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(original_audio), "-i", str(bgm_audio), "-filter_complex", f"[1:a]{bgm_chain}[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=0[a]", "-map", "[a]", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", str(output_path)],
        output_path,
        timeout=timeout,
    )


def mux_tracks(*, video_track: Path, audio_track: Path, output_path: Path, audio_bitrate: str, timeout: int) -> None:
    run_ffmpeg(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(video_track), "-i", str(audio_track), "-shortest", "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", audio_bitrate, "-movflags", "+faststart", str(output_path)],
        output_path,
        timeout=timeout,
    )


def run_ffmpeg(command: list[str], output_path: Path, *, timeout: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0 or not output_path.exists():
        raise MediaRenderError((result.stderr or "ffmpeg media render failed").strip())


def read_timeline(path: Path) -> TimelineDraft:
    try:
        return TimelineDraft.model_validate_json(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise MediaRenderError(f"invalid TimelineDraft JSON: {exc}") from exc


def fingerprint_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _video_transition_filters(filters: list[str], transition: str, duration: float) -> tuple[bool, str | None]:
    fade_duration = min(0.5, max(0.0, duration / 3))
    if transition == "fade_in":
        filters.append(f"fade=t=in:st=0:d={fade_duration:.3f}")
        return True, None
    if transition == "fade_out":
        filters.append(f"fade=t=out:st={max(0.0, duration - fade_duration):.3f}:d={fade_duration:.3f}")
        return True, None
    if transition == "crossfade":
        return False, "crossfade requires overlapping timeline segments; rendered as a hard cut"
    return True, None


def _audio_transition_filters(filters: list[str], transition: str, duration: float) -> tuple[bool, str | None]:
    fade_duration = min(0.5, max(0.0, duration / 3))
    if transition == "fade_in":
        filters.append(f"afade=t=in:st=0:d={fade_duration:.3f}")
        return True, None
    if transition == "fade_out":
        filters.append(f"afade=t=out:st={max(0.0, duration - fade_duration):.3f}:d={fade_duration:.3f}")
        return True, None
    if transition == "crossfade":
        return False, "audio crossfade requires overlapping timeline segments; rendered as a cut"
    return True, None


def _even(value: int) -> int:
    return max(2, value if value % 2 == 0 else value + 1)
