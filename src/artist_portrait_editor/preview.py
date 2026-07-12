from __future__ import annotations

import hashlib
from pathlib import Path
from shutil import which

from artist_portrait_editor.media.probe import probe_media
from artist_portrait_editor.media.rendering import (
    MediaRenderError,
    atomic_json,
    canvas_from_width,
    concat_files,
    fingerprint_file,
    mix_audio,
    mux_tracks,
    read_timeline,
    render_audio_segment,
    render_bgm_track,
    render_black_video,
    render_silence,
    render_video_segment,
)
from artist_portrait_editor.media.scanner import hash_file, read_sources_jsonl
from artist_portrait_editor.models.bgm import BgmFitPlan
from artist_portrait_editor.models.preview import (
    PreviewRenderedSegment,
    PreviewRenderManifest,
    PreviewValidationIssue,
    PreviewValidationReport,
)


class PreviewError(ValueError):
    pass


def validate_preview_controls(*, width: int, fps: int) -> None:
    if width < 160 or width > 1280:
        raise PreviewError("preview --width must be between 160 and 1280")
    if width % 2:
        raise PreviewError("preview --width must be an even number")
    if fps < 6 or fps > 30:
        raise PreviewError("preview --fps must be between 6 and 30")


def render_preview(
    *,
    root: Path,
    project_id: str,
    width: int = 480,
    fps: int = 12,
    aspect_ratio: str = "16:9",
) -> tuple[Path, Path, Path, PreviewRenderManifest, PreviewValidationReport]:
    validate_preview_controls(width=width, fps=fps)
    if which("ffmpeg") is None or which("ffprobe") is None:
        raise PreviewError("preview requires ffmpeg and ffprobe")
    timeline_path = root / "output" / "timeline_draft.json"
    if not timeline_path.exists():
        raise PreviewError("preview requires output/timeline_draft.json")
    try:
        timeline = read_timeline(timeline_path)
        canvas = canvas_from_width(width=width, aspect_ratio=aspect_ratio, fps=fps)
    except MediaRenderError as exc:
        raise PreviewError(str(exc)) from exc
    if timeline.project_id != project_id:
        raise PreviewError("timeline project_id mismatch")
    sources = {item.source_id: item for item in read_sources_jsonl(root / ".artist-portrait" / "data" / "sources.jsonl")}
    cache_dir = root / ".artist-portrait" / "cache" / "preview" / timeline.timeline_id
    cache_dir.mkdir(parents=True, exist_ok=True)
    output_dir = root / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    video_segments: list[Path] = []
    audio_segments: list[Path] = []
    rendered_segments: list[PreviewRenderedSegment] = []
    warnings: list[str] = []
    original_audio_included = False
    for index, segment in enumerate(timeline.segments, start=1):
        source = sources.get(segment.source_id)
        if source is None:
            raise PreviewError(f"timeline references unknown source: {segment.source_id}")
        source_path = (root / source.primary_location).resolve()
        try:
            source_path.relative_to(root.resolve())
        except ValueError as exc:
            raise PreviewError("preview source path escapes project root") from exc
        if not source_path.exists():
            raise PreviewError(f"preview source file missing: {source.primary_location}")
        duration = segment.timeline_end - segment.timeline_start
        video_path = cache_dir / f"{index:03d}_{segment.segment_id}_video.mp4"
        audio_path = cache_dir / f"{index:03d}_{segment.segment_id}_audio.wav"
        video_rendered = segment.media_role.value in {"video", "both"}
        original_audio = segment.media_role.value in {"audio", "both"} and source.media_probe.audio_present
        if video_rendered:
            try:
                video_transition_rendered, video_transition_warning = render_video_segment(
                source_path=source_path,
                output_path=video_path,
                source_in=segment.source_in,
                duration=duration,
                canvas=canvas,
                video_transition=segment.video_transition.value,
                preset="veryfast",
                crf=30,
                timeout=180,
                )
            except MediaRenderError as exc:
                raise PreviewError(str(exc)) from exc
        else:
            try:
                video_transition_rendered, video_transition_warning = render_black_video(
                output_path=video_path,
                duration=duration,
                canvas=canvas,
                video_transition=segment.video_transition.value,
                preset="veryfast",
                crf=30,
                timeout=180,
                )
            except MediaRenderError as exc:
                raise PreviewError(str(exc)) from exc
            warnings.append(f"{segment.segment_id}: audio-only segment rendered with black video")
        if original_audio:
            try:
                audio_transition_rendered, audio_transition_warning = render_audio_segment(
                source_path=source_path,
                output_path=audio_path,
                source_in=segment.source_in,
                duration=duration,
                audio_transition=segment.audio_transition.value,
                )
            except MediaRenderError as exc:
                raise PreviewError(str(exc)) from exc
            original_audio_included = True
        else:
            try:
                render_silence(output_path=audio_path, duration=duration)
            except MediaRenderError as exc:
                raise PreviewError(str(exc)) from exc
            audio_transition_rendered = segment.audio_transition.value in {"none", "cut"}
            audio_transition_warning = None
            if segment.media_role.value in {"audio", "both"}:
                warnings.append(f"{segment.segment_id}: source has no retained audio stream")
        if video_transition_warning:
            warnings.append(f"{segment.segment_id}: {video_transition_warning}")
        if audio_transition_warning:
            warnings.append(f"{segment.segment_id}: {audio_transition_warning}")
        video_segments.append(video_path)
        audio_segments.append(audio_path)
        rendered_segments.append(
            PreviewRenderedSegment(
                segment_id=segment.segment_id,
                source_id=segment.source_id,
                source_ref=source.primary_location,
                timeline_start=segment.timeline_start,
                timeline_end=segment.timeline_end,
                source_in=segment.source_in,
                source_out=segment.source_out,
                media_role=segment.media_role.value,
                video_rendered=video_rendered,
                original_audio_rendered=original_audio,
                video_transition=segment.video_transition.value,
                audio_transition=segment.audio_transition.value,
                video_transition_rendered=video_transition_rendered,
                audio_transition_rendered=audio_transition_rendered,
            )
        )

    video_track = cache_dir / "video_track.mp4"
    original_audio_track = cache_dir / "original_audio.wav"
    try:
        concat_files(video_segments, video_track, media_type="video")
        concat_files(audio_segments, original_audio_track, media_type="audio")
    except MediaRenderError as exc:
        raise PreviewError(str(exc)) from exc

    bgm_fit_path = root / ".artist-portrait" / "data" / "bgm_fit.json"
    bgm_fit: BgmFitPlan | None = None
    bgm_fit_fingerprint: str | None = None
    bgm_track: Path | None = None
    if bgm_fit_path.exists():
        bgm_fit = BgmFitPlan.model_validate_json(bgm_fit_path.read_text(encoding="utf-8"))
        bgm_fit_fingerprint = fingerprint_file(bgm_fit_path)
        bgm_track = cache_dir / "bgm_track.wav"
        try:
            render_bgm_track(root=root, project_id=project_id, plan=bgm_fit, output_path=bgm_track)
        except MediaRenderError as exc:
            raise PreviewError(str(exc)) from exc
    else:
        warnings.append("no current BGM fit plan; preview uses original audio or silence only")

    mixed_audio = cache_dir / "mixed_audio.wav"
    if bgm_track is not None and bgm_fit is not None:
        mix_audio(
            original_audio=original_audio_track,
            bgm_audio=bgm_track,
            output_path=mixed_audio,
            ducking_intervals=[(item.start, item.end, item.gain_db) for item in bgm_fit.ducking_intervals],
        )
    else:
        mixed_audio = original_audio_track

    preview_id = _preview_id(timeline.timeline_id, fingerprint_file(timeline_path), bgm_fit_fingerprint)
    output_path = output_dir / "preview_lowres.mp4"
    try:
        mux_tracks(video_track=video_track, audio_track=mixed_audio, output_path=output_path, audio_bitrate="96k", timeout=180)
    except MediaRenderError as exc:
        raise PreviewError(str(exc)) from exc
    output_hash = hash_file(output_path)
    _, media_probe = probe_media(output_path)
    expected_duration = round(timeline.actual_duration, 3)
    actual_duration = round(media_probe.duration, 3)
    duration_delta = round(actual_duration - expected_duration, 3)
    audio_expected = True
    manifest_path = root / ".artist-portrait" / "data" / "preview_manifest.json"
    validation_path = root / ".artist-portrait" / "data" / "preview_validation.json"
    manifest = PreviewRenderManifest(
        preview_id=preview_id,
        project_id=project_id,
        timeline_id=timeline.timeline_id,
        timeline_ref=timeline_path.relative_to(root).as_posix(),
        timeline_fingerprint=fingerprint_file(timeline_path),
        bgm_fit_ref=bgm_fit_path.relative_to(root).as_posix() if bgm_fit is not None else None,
        bgm_fit_id=bgm_fit.fit_id if bgm_fit is not None else None,
        bgm_fit_fingerprint=bgm_fit_fingerprint,
        output_ref=output_path.relative_to(root).as_posix(),
        output_content_hash=output_hash,
        expected_duration=expected_duration,
        duration=actual_duration,
        duration_delta_seconds=duration_delta,
        duration_tolerance_seconds=0.25,
        requested_width=width,
        requested_height=canvas.height,
        requested_aspect_ratio=canvas.aspect_ratio,
        fit_mode=canvas.fit_mode,
        requested_fps=fps,
        width=media_probe.width or canvas.width,
        height=media_probe.height or canvas.height,
        fps=fps,
        actual_frame_rate=round(media_probe.frame_rate, 3) if media_probe.frame_rate else None,
        video_codec=media_probe.video_codec or "unknown",
        video_present=media_probe.video_codec is not None,
        audio_codec=media_probe.audio_codec or "unknown",
        audio_present=media_probe.audio_present,
        audio_expected=audio_expected,
        render_profile="low_resolution_preview",
        rendered_segments=rendered_segments,
        original_audio_included=original_audio_included,
        bgm_included=bgm_fit is not None,
        ducking_applied=bool(bgm_fit.ducking_intervals) if bgm_fit is not None else False,
        warnings=sorted(set(warnings)),
    )
    atomic_json(manifest_path, manifest.model_dump(mode="json"))
    validation = validate_preview(root=root, manifest=manifest)
    atomic_json(validation_path, validation.model_dump(mode="json"))
    return output_path, manifest_path, validation_path, manifest, validation


def review_preview(root: Path) -> PreviewValidationReport:
    manifest_path = root / ".artist-portrait" / "data" / "preview_manifest.json"
    if not manifest_path.exists():
        return _validation(
            preview_ref="output/preview_lowres.mp4",
            manifest_ref=manifest_path.relative_to(root).as_posix(),
            timeline_ref="output/timeline_draft.json",
            timeline_fingerprint="sha256:" + "0" * 64,
            issues=[
                _issue("preview_manifest_missing", "error", "preview manifest is missing")
            ],
        )
    try:
        manifest = PreviewRenderManifest.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
    except ValueError as exc:
        return _validation(
            preview_ref="output/preview_lowres.mp4",
            manifest_ref=manifest_path.relative_to(root).as_posix(),
            timeline_ref="output/timeline_draft.json",
            timeline_fingerprint="sha256:" + "0" * 64,
            issues=[
                _issue("preview_manifest_invalid", "error", f"invalid preview manifest: {exc}")
            ],
        )
    return validate_preview(root=root, manifest=manifest)


def preview_manifest_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        manifest = PreviewRenderManifest.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": f"invalid PreviewRenderManifest JSON: {exc}",
        }
    return {
        "exists": True,
        "valid": True,
        "preview_id": manifest.preview_id,
        "timeline_id": manifest.timeline_id,
        "output_ref": manifest.output_ref,
        "duration": manifest.duration,
        "duration_delta_seconds": manifest.duration_delta_seconds,
        "width": manifest.width,
        "height": manifest.height,
        "requested_width": manifest.requested_width,
        "requested_fps": manifest.requested_fps,
        "bgm_included": manifest.bgm_included,
        "ducking_applied": manifest.ducking_applied,
        "audio_present": manifest.audio_present,
        "video_present": manifest.video_present,
    }


def preview_validation_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        report = PreviewValidationReport.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": f"invalid PreviewValidationReport JSON: {exc}",
        }
    return {
        "exists": True,
        "valid": True,
        "preview_valid": report.valid,
        "quality_status": report.quality_status,
        "duration_delta_seconds": report.duration_delta_seconds,
        "issue_count": report.issue_count,
        "error_count": report.error_count,
        "warning_count": report.warning_count,
    }


def validate_preview(*, root: Path, manifest: PreviewRenderManifest) -> PreviewValidationReport:
    issues: list[PreviewValidationIssue] = []
    actual_duration = manifest.duration
    actual_width = manifest.width
    actual_height = manifest.height
    actual_frame_rate = manifest.actual_frame_rate
    video_present = manifest.video_present
    audio_present = manifest.audio_present
    output_path = root / manifest.output_ref
    timeline_path = root / manifest.timeline_ref
    if not output_path.exists():
        issues.append(_issue("preview_output_missing", "error", "preview output is missing"))
    elif hash_file(output_path) != manifest.output_content_hash:
        issues.append(_issue("preview_output_hash_stale", "error", "preview output hash changed"))
    else:
        try:
            _, media_probe = probe_media(output_path)
            actual_duration = round(media_probe.duration, 3)
            actual_width = media_probe.width or manifest.width
            actual_height = media_probe.height or manifest.height
            actual_frame_rate = round(media_probe.frame_rate, 3) if media_probe.frame_rate else None
            video_present = media_probe.video_codec is not None
            audio_present = media_probe.audio_present
        except Exception as exc:
            issues.append(_issue("preview_probe_failed", "error", f"ffprobe failed for preview output: {exc}"))
    if not timeline_path.exists():
        issues.append(_issue("preview_timeline_missing", "error", "timeline is missing"))
    else:
        timeline_hash = fingerprint_file(timeline_path)
        if timeline_hash != manifest.timeline_fingerprint:
            issues.append(_issue("preview_timeline_stale", "error", "timeline fingerprint changed"))
    if manifest.bgm_fit_ref:
        bgm_fit_path = root / manifest.bgm_fit_ref
        if not bgm_fit_path.exists():
            issues.append(_issue("preview_bgm_fit_missing", "error", "BGM fit plan is missing"))
        else:
            fit_hash = fingerprint_file(bgm_fit_path)
            if fit_hash != manifest.bgm_fit_fingerprint:
                issues.append(_issue("preview_bgm_fit_stale", "error", "BGM fit fingerprint changed"))
    duration_delta = round(actual_duration - manifest.expected_duration, 3)
    if abs(duration_delta) > manifest.duration_tolerance_seconds:
        issues.append(
            _issue(
                "preview_duration_mismatch",
                "error",
                (
                    f"preview duration differs from timeline by {duration_delta:.3f}s "
                    f"(tolerance {manifest.duration_tolerance_seconds:.3f}s)"
                ),
            )
        )
    if not video_present:
        issues.append(_issue("preview_video_missing", "error", "preview has no video stream"))
    if actual_width != manifest.width or actual_height != manifest.height:
        issues.append(_issue("preview_dimension_drift", "error", "preview dimensions differ from manifest"))
    if manifest.width != manifest.requested_width:
        issues.append(_issue("preview_width_mismatch", "error", "rendered width differs from requested width"))
    if manifest.height != manifest.requested_height:
        issues.append(_issue("preview_height_mismatch", "error", "rendered height differs from requested height"))
    if actual_frame_rate is not None and abs(actual_frame_rate - manifest.requested_fps) > 0.25:
        issues.append(_issue("preview_fps_mismatch", "warning", "preview frame rate differs from requested fps"))
    if manifest.audio_expected and not audio_present:
        issues.append(_issue("preview_audio_missing", "error", "preview expected audio but has no audio stream"))
    if not manifest.audio_expected and audio_present:
        issues.append(_issue("preview_unexpected_audio", "warning", "preview has audio although no audio was expected"))
    errors = sum(item.severity == "error" for item in issues)
    warnings = sum(item.severity == "warning" for item in issues)
    quality_status = "failed" if errors else "warning" if warnings else "passed"
    return PreviewValidationReport(
        preview_ref=manifest.output_ref,
        manifest_ref=".artist-portrait/data/preview_manifest.json",
        timeline_ref=manifest.timeline_ref,
        timeline_fingerprint=manifest.timeline_fingerprint,
        bgm_fit_ref=manifest.bgm_fit_ref,
        bgm_fit_fingerprint=manifest.bgm_fit_fingerprint,
        expected_duration=manifest.expected_duration,
        actual_duration=actual_duration,
        duration_delta_seconds=duration_delta,
        duration_tolerance_seconds=manifest.duration_tolerance_seconds,
        requested_width=manifest.requested_width,
        requested_height=manifest.requested_height,
        requested_aspect_ratio=manifest.requested_aspect_ratio,
        requested_fps=manifest.requested_fps,
        actual_width=actual_width,
        actual_height=actual_height,
        actual_frame_rate=actual_frame_rate,
        video_present=video_present,
        audio_present=audio_present,
        audio_expected=manifest.audio_expected,
        quality_status=quality_status,
        recovery_command="artist-portrait preview --project <project.yaml>",
        issue_count=len(issues),
        error_count=errors,
        warning_count=warnings,
        issues=issues,
        valid=errors == 0,
    )


def render_preview_review(report: PreviewValidationReport) -> str:
    lines = [
        "# Preview Review",
        "",
        "This deterministic review validates an existing low-resolution local preview.",
        "It does not render final export media, choose music, call models, or access the network.",
        "",
        "## Summary",
        "",
        f"- Preview: `{report.preview_ref}`",
        f"- Manifest: `{report.manifest_ref}`",
        f"- Timeline: `{report.timeline_ref}`",
        f"- Valid: `{str(report.valid).lower()}`",
        f"- Quality status: `{report.quality_status}`",
        f"- Expected duration: `{report.expected_duration:.3f}s`",
        f"- Actual duration: `{report.actual_duration:.3f}s`",
        f"- Duration delta: `{report.duration_delta_seconds:.3f}s`",
        f"- Requested profile: `{report.requested_width}x{report.requested_height}` (`{report.requested_aspect_ratio}`) @ {report.requested_fps}fps",
        f"- Actual size: `{report.actual_width}x{report.actual_height}`",
        f"- Actual frame rate: `{report.actual_frame_rate}`",
        f"- Video present: `{str(report.video_present).lower()}`",
        f"- Audio expected: `{str(report.audio_expected).lower()}`",
        f"- Audio present: `{str(report.audio_present).lower()}`",
        f"- Recovery command: `{report.recovery_command}`",
        f"- Issues: `{report.issue_count}`",
        "",
        "## Issues",
        "",
    ]
    if not report.issues:
        lines.append("No preview issues were found.")
    for issue in report.issues:
        lines.extend(
            [
                f"### `{issue.code}`",
                "",
                f"- Severity: `{issue.severity}`",
                f"- Detail: {issue.detail}",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def _preview_id(timeline_id: str, timeline_fingerprint: str, bgm_fit_fingerprint: str | None) -> str:
    payload = f"{timeline_id}:{timeline_fingerprint}:{bgm_fit_fingerprint or 'no-bgm'}"
    return "preview_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def _issue(code: str, severity: str, detail: str) -> PreviewValidationIssue:
    return PreviewValidationIssue(code=code, severity=severity, detail=detail)


def _validation(
    *,
    preview_ref: str,
    manifest_ref: str,
    timeline_ref: str,
    timeline_fingerprint: str,
    issues: list[PreviewValidationIssue],
) -> PreviewValidationReport:
    errors = sum(item.severity == "error" for item in issues)
    warnings = sum(item.severity == "warning" for item in issues)
    return PreviewValidationReport(
        preview_ref=preview_ref,
        manifest_ref=manifest_ref,
        timeline_ref=timeline_ref,
        timeline_fingerprint=timeline_fingerprint,
        expected_duration=0.001,
        actual_duration=0,
        duration_delta_seconds=0,
        duration_tolerance_seconds=0.25,
        requested_width=480,
        requested_height=270,
        requested_aspect_ratio="16:9",
        requested_fps=12,
        actual_width=None,
        actual_height=None,
        actual_frame_rate=None,
        video_present=False,
        audio_present=False,
        audio_expected=False,
        quality_status="failed" if errors else "warning" if warnings else "passed",
        recovery_command="artist-portrait preview --project <project.yaml>",
        issue_count=len(issues),
        error_count=errors,
        warning_count=warnings,
        issues=issues,
        valid=errors == 0,
    )
