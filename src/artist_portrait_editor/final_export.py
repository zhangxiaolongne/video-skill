from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from shutil import which

from artist_portrait_editor.media.probe import probe_media
from artist_portrait_editor.media.rendering import (
    MediaRenderError,
    atomic_json,
    canvas_from_short_edge,
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
from artist_portrait_editor.models.final_export import (
    FinalExportManifest,
    FinalExportProfile,
    FinalExportValidationIssue,
    FinalExportValidationReport,
)
from artist_portrait_editor.models.preview import PreviewRenderedSegment


class FinalExportError(ValueError):
    pass


@dataclass(frozen=True)
class _ExportProfileTemplate:
    short_edge: int
    fps: int
    video_crf: int
    audio_bitrate: str
    intent: str


EXPORT_PROFILES = {
    "review_720p": _ExportProfileTemplate(720, 24, 23, "160k", "local review-quality final export candidate"),
    "delivery_1080p": _ExportProfileTemplate(1080, 30, 20, "192k", "local high-quality delivery export candidate"),
}


def render_final_export(
    *,
    root: Path,
    project_id: str,
    profile_name: str = "review_720p",
    aspect_ratio: str = "16:9",
) -> tuple[Path, Path, Path, FinalExportManifest, FinalExportValidationReport]:
    template = EXPORT_PROFILES.get(profile_name)
    if template is None:
        raise FinalExportError("export --profile must be review_720p or delivery_1080p")
    try:
        canvas = canvas_from_short_edge(short_edge=template.short_edge, aspect_ratio=aspect_ratio, fps=template.fps)
    except MediaRenderError as exc:
        raise FinalExportError(str(exc)) from exc
    profile = FinalExportProfile(
        name=profile_name,
        width=canvas.width,
        height=canvas.height,
        aspect_ratio=canvas.aspect_ratio,
        fit_mode=canvas.fit_mode,
        fps=template.fps,
        video_crf=template.video_crf,
        audio_bitrate=template.audio_bitrate,
        intent=template.intent,
    )
    if which("ffmpeg") is None or which("ffprobe") is None:
        raise FinalExportError("export requires ffmpeg and ffprobe")
    timeline_path = root / "output" / "timeline_draft.json"
    if not timeline_path.exists():
        raise FinalExportError("export requires output/timeline_draft.json")
    try:
        timeline = read_timeline(timeline_path)
    except MediaRenderError as exc:
        raise FinalExportError(str(exc)) from exc
    if timeline.project_id != project_id:
        raise FinalExportError("timeline project_id mismatch")

    sources = {
        item.source_id: item
        for item in read_sources_jsonl(root / ".artist-portrait" / "data" / "sources.jsonl")
    }
    cache_dir = root / ".artist-portrait" / "cache" / "final_export" / timeline.timeline_id
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
            raise FinalExportError(f"timeline references unknown source: {segment.source_id}")
        source_path = (root / source.primary_location).resolve()
        try:
            source_path.relative_to(root.resolve())
        except ValueError as exc:
            raise FinalExportError("export source path escapes project root") from exc
        if not source_path.exists():
            raise FinalExportError(f"export source file missing: {source.primary_location}")
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
                    preset="medium",
                    crf=profile.video_crf,
                    timeout=300,
                )
            except MediaRenderError as exc:
                raise FinalExportError(str(exc)) from exc
        else:
            try:
                video_transition_rendered, video_transition_warning = render_black_video(
                    output_path=video_path,
                    duration=duration,
                    canvas=canvas,
                    video_transition=segment.video_transition.value,
                    preset="medium",
                    crf=profile.video_crf,
                    timeout=300,
                )
            except MediaRenderError as exc:
                raise FinalExportError(str(exc)) from exc
            warnings.append(f"{segment.segment_id}: audio-only segment rendered with black video")
        if original_audio:
            try:
                audio_transition_rendered, audio_transition_warning = render_audio_segment(
                    source_path=source_path,
                    output_path=audio_path,
                    source_in=segment.source_in,
                    duration=duration,
                    audio_transition=segment.audio_transition.value,
                    timeout=300,
                )
            except MediaRenderError as exc:
                raise FinalExportError(str(exc)) from exc
            original_audio_included = True
        else:
            try:
                render_silence(output_path=audio_path, duration=duration, timeout=300)
            except MediaRenderError as exc:
                raise FinalExportError(str(exc)) from exc
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
        concat_files(video_segments, video_track, media_type="video", timeout=300)
        concat_files(audio_segments, original_audio_track, media_type="audio", timeout=300)
    except MediaRenderError as exc:
        raise FinalExportError(str(exc)) from exc

    bgm_fit_path = root / ".artist-portrait" / "data" / "bgm_fit.json"
    bgm_fit: BgmFitPlan | None = None
    bgm_fit_fingerprint: str | None = None
    bgm_track: Path | None = None
    if bgm_fit_path.exists():
        bgm_fit = BgmFitPlan.model_validate_json(bgm_fit_path.read_text(encoding="utf-8"))
        bgm_fit_fingerprint = fingerprint_file(bgm_fit_path)
        bgm_track = cache_dir / "bgm_track.wav"
        try:
            render_bgm_track(
                root=root,
                project_id=project_id,
                plan=bgm_fit,
                output_path=bgm_track,
                timeout=300,
            )
        except MediaRenderError as exc:
            raise FinalExportError(str(exc)) from exc
    else:
        warnings.append("no current BGM fit plan; export uses original audio or silence only")

    mixed_audio = cache_dir / "mixed_audio.wav"
    if bgm_track is not None and bgm_fit is not None:
        mix_audio(
            original_audio=original_audio_track,
            bgm_audio=bgm_track,
            output_path=mixed_audio,
            ducking_intervals=[(item.start, item.end, item.gain_db) for item in bgm_fit.ducking_intervals],
            timeout=300,
        )
    else:
        mixed_audio = original_audio_track

    export_id = _export_id(
        timeline.timeline_id,
        fingerprint_file(timeline_path),
        bgm_fit_fingerprint,
        profile.name,
    )
    output_path = output_dir / "final_export.mp4"
    try:
        mux_tracks(video_track=video_track, audio_track=mixed_audio, output_path=output_path, audio_bitrate=profile.audio_bitrate, timeout=300)
    except MediaRenderError as exc:
        raise FinalExportError(str(exc)) from exc
    output_hash = hash_file(output_path)
    _, media_probe = probe_media(output_path)
    expected_duration = round(timeline.actual_duration, 3)
    actual_duration = round(media_probe.duration, 3)
    duration_delta = round(actual_duration - expected_duration, 3)
    manifest_path = root / ".artist-portrait" / "data" / "final_export_manifest.json"
    validation_path = root / ".artist-portrait" / "data" / "final_export_validation.json"
    manifest = FinalExportManifest(
        export_id=export_id,
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
        duration_tolerance_seconds=0.35,
        requested_profile=profile,
        width=media_probe.width or profile.width,
        height=media_probe.height or profile.height,
        actual_frame_rate=round(media_probe.frame_rate, 3) if media_probe.frame_rate else None,
        video_codec=media_probe.video_codec or "unknown",
        video_present=media_probe.video_codec is not None,
        audio_codec=media_probe.audio_codec or "unknown",
        audio_present=media_probe.audio_present,
        audio_expected=True,
        render_profile=profile.name,
        rendered_segments=rendered_segments,
        original_audio_included=original_audio_included,
        bgm_included=bgm_fit is not None,
        ducking_applied=bool(bgm_fit.ducking_intervals) if bgm_fit is not None else False,
        warnings=sorted(set(warnings)),
    )
    atomic_json(manifest_path, manifest.model_dump(mode="json"))
    validation = validate_final_export(root=root, manifest=manifest)
    atomic_json(validation_path, validation.model_dump(mode="json"))
    return output_path, manifest_path, validation_path, manifest, validation


def review_final_export(root: Path) -> FinalExportValidationReport:
    manifest_path = root / ".artist-portrait" / "data" / "final_export_manifest.json"
    if not manifest_path.exists():
        return _validation(
            export_ref="output/final_export.mp4",
            manifest_ref=manifest_path.relative_to(root).as_posix(),
            timeline_ref="output/timeline_draft.json",
            timeline_fingerprint="sha256:" + "0" * 64,
            issues=[_issue("final_export_manifest_missing", "error", "final export manifest is missing")],
        )
    try:
        manifest = FinalExportManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return _validation(
            export_ref="output/final_export.mp4",
            manifest_ref=manifest_path.relative_to(root).as_posix(),
            timeline_ref="output/timeline_draft.json",
            timeline_fingerprint="sha256:" + "0" * 64,
            issues=[_issue("final_export_manifest_invalid", "error", f"invalid final export manifest: {exc}")],
        )
    return validate_final_export(root=root, manifest=manifest)


def final_export_manifest_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        manifest = FinalExportManifest.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": f"invalid FinalExportManifest JSON: {exc}",
        }
    return {
        "exists": True,
        "valid": True,
        "export_id": manifest.export_id,
        "timeline_id": manifest.timeline_id,
        "output_ref": manifest.output_ref,
        "profile": manifest.render_profile,
        "duration": manifest.duration,
        "duration_delta_seconds": manifest.duration_delta_seconds,
        "width": manifest.width,
        "height": manifest.height,
        "bgm_included": manifest.bgm_included,
        "ducking_applied": manifest.ducking_applied,
        "audio_present": manifest.audio_present,
        "video_present": manifest.video_present,
    }


def final_export_validation_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        report = FinalExportValidationReport.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": f"invalid FinalExportValidationReport JSON: {exc}",
        }
    return {
        "exists": True,
        "valid": True,
        "export_valid": report.valid,
        "quality_status": report.quality_status,
        "duration_delta_seconds": report.duration_delta_seconds,
        "issue_count": report.issue_count,
        "error_count": report.error_count,
        "warning_count": report.warning_count,
    }


def final_export_status_lines(summaries: dict) -> list[str]:
    final_export = summaries.get("final_export") or {}
    if final_export.get("exists") and final_export.get("valid", True):
        lines = [
            (
                f"final_export: {final_export.get('output_ref')} "
                f"({final_export.get('profile')}, "
                f"{final_export.get('width')}x{final_export.get('height')}, "
                f"bgm={str(final_export.get('bgm_included')).lower()})"
            )
        ]
        validation = summaries.get("final_export_validation") or {}
        if validation.get("exists") and validation.get("valid", True):
            lines.append(
                "final_export_qc: "
                f"{validation.get('quality_status')} "
                f"(delta={validation.get('duration_delta_seconds')}s)"
            )
        return lines
    if final_export.get("exists"):
        return ["final_export: invalid"]
    return ["final_export: missing"]


def final_export_doctor_issues(root: Path, project_path: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    manifest = final_export_manifest_summary(
        root / ".artist-portrait" / "data" / "final_export_manifest.json"
    )
    if manifest.get("valid") is False:
        issues.append(
            {
                "code": "final_export_manifest_invalid",
                "severity": "error",
                "detail": str(manifest.get("error")),
                "next_action": (
                    f"rerun artist-portrait export --project {project_path} "
                    "--profile review_720p"
                ),
            }
        )
    validation = final_export_validation_summary(
        root / ".artist-portrait" / "data" / "final_export_validation.json"
    )
    if validation.get("valid") is False:
        issues.append(
            {
                "code": "final_export_validation_invalid",
                "severity": "error",
                "detail": str(validation.get("error")),
                "next_action": (
                    f"rerun artist-portrait export --project {project_path} "
                    "--profile review_720p"
                ),
            }
        )
    if manifest.get("valid") is True:
        report = review_final_export(root)
        for issue in report.issues:
            issues.append(
                {
                    "code": issue.code,
                    "severity": issue.severity,
                    "detail": issue.detail,
                    "next_action": (
                        f"artist-portrait export --project {project_path} "
                        f"--profile {report.requested_profile}"
                    ),
                }
            )
    return issues


def validate_final_export(*, root: Path, manifest: FinalExportManifest) -> FinalExportValidationReport:
    issues: list[FinalExportValidationIssue] = []
    actual_duration = manifest.duration
    actual_width = manifest.width
    actual_height = manifest.height
    actual_frame_rate = manifest.actual_frame_rate
    video_codec: str | None = manifest.video_codec
    audio_codec: str | None = manifest.audio_codec
    video_present = manifest.video_present
    audio_present = manifest.audio_present
    output_path = root / manifest.output_ref
    timeline_path = root / manifest.timeline_ref
    if not output_path.exists():
        issues.append(_issue("final_export_output_missing", "error", "final export output is missing"))
    elif hash_file(output_path) != manifest.output_content_hash:
        issues.append(_issue("final_export_output_hash_stale", "error", "final export output hash changed"))
    else:
        try:
            _, media_probe = probe_media(output_path)
            actual_duration = round(media_probe.duration, 3)
            actual_width = media_probe.width or manifest.width
            actual_height = media_probe.height or manifest.height
            actual_frame_rate = round(media_probe.frame_rate, 3) if media_probe.frame_rate else None
            video_codec = media_probe.video_codec
            audio_codec = media_probe.audio_codec
            video_present = media_probe.video_codec is not None
            audio_present = media_probe.audio_present
        except Exception as exc:
            issues.append(_issue("final_export_probe_failed", "error", f"ffprobe failed for final export: {exc}"))
    if not timeline_path.exists():
        issues.append(_issue("final_export_timeline_missing", "error", "timeline is missing"))
    else:
        timeline_hash = fingerprint_file(timeline_path)
        if timeline_hash != manifest.timeline_fingerprint:
            issues.append(_issue("final_export_timeline_stale", "error", "timeline fingerprint changed"))
    if manifest.bgm_fit_ref:
        bgm_fit_path = root / manifest.bgm_fit_ref
        if not bgm_fit_path.exists():
            issues.append(_issue("final_export_bgm_fit_missing", "error", "BGM fit plan is missing"))
        else:
            fit_hash = fingerprint_file(bgm_fit_path)
            if fit_hash != manifest.bgm_fit_fingerprint:
                issues.append(_issue("final_export_bgm_fit_stale", "error", "BGM fit fingerprint changed"))
    duration_delta = round(actual_duration - manifest.expected_duration, 3)
    if abs(duration_delta) > manifest.duration_tolerance_seconds:
        issues.append(
            _issue(
                "final_export_duration_mismatch",
                "error",
                (
                    f"final export duration differs from timeline by {duration_delta:.3f}s "
                    f"(tolerance {manifest.duration_tolerance_seconds:.3f}s)"
                ),
            )
        )
    if not video_present:
        issues.append(_issue("final_export_video_missing", "error", "final export has no video stream"))
    if actual_width != manifest.requested_profile.width:
        issues.append(_issue("final_export_width_mismatch", "error", "final export width differs from requested profile"))
    if actual_height != manifest.requested_profile.height:
        issues.append(_issue("final_export_height_mismatch", "error", "final export height differs from requested profile"))
    if actual_frame_rate is not None and abs(actual_frame_rate - manifest.requested_profile.fps) > 0.25:
        issues.append(_issue("final_export_fps_mismatch", "warning", "final export frame rate differs from profile"))
    if manifest.audio_expected and not audio_present:
        issues.append(_issue("final_export_audio_missing", "error", "final export expected audio but has no audio stream"))
    if manifest.render_profile != manifest.requested_profile.name:
        issues.append(_issue("final_export_profile_drift", "error", "manifest render profile differs from requested profile"))
    errors = sum(item.severity == "error" for item in issues)
    warnings = sum(item.severity == "warning" for item in issues)
    quality_status = "failed" if errors else "warning" if warnings else "passed"
    return FinalExportValidationReport(
        export_ref=manifest.output_ref,
        manifest_ref=".artist-portrait/data/final_export_manifest.json",
        timeline_ref=manifest.timeline_ref,
        timeline_fingerprint=manifest.timeline_fingerprint,
        bgm_fit_ref=manifest.bgm_fit_ref,
        bgm_fit_fingerprint=manifest.bgm_fit_fingerprint,
        expected_duration=manifest.expected_duration,
        actual_duration=actual_duration,
        duration_delta_seconds=duration_delta,
        duration_tolerance_seconds=manifest.duration_tolerance_seconds,
        requested_profile=manifest.requested_profile.name,
        requested_width=manifest.requested_profile.width,
        requested_height=manifest.requested_profile.height,
        requested_aspect_ratio=manifest.requested_profile.aspect_ratio,
        requested_fps=manifest.requested_profile.fps,
        actual_width=actual_width,
        actual_height=actual_height,
        actual_frame_rate=actual_frame_rate,
        video_codec=video_codec,
        audio_codec=audio_codec,
        video_present=video_present,
        audio_present=audio_present,
        audio_expected=manifest.audio_expected,
        quality_status=quality_status,
        recovery_command="artist-portrait export --project <project.yaml> --profile "
        + manifest.requested_profile.name,
        issue_count=len(issues),
        error_count=errors,
        warning_count=warnings,
        issues=issues,
        valid=errors == 0,
    )


def render_final_export_review(report: FinalExportValidationReport) -> str:
    lines = [
        "# Final Export Review",
        "",
        "This deterministic review validates an existing local final export.",
        "It does not choose music, call models, use image generation/editing, or access the network.",
        "",
        "## Summary",
        "",
        f"- Export: `{report.export_ref}`",
        f"- Manifest: `{report.manifest_ref}`",
        f"- Timeline: `{report.timeline_ref}`",
        f"- Valid: `{str(report.valid).lower()}`",
        f"- Quality status: `{report.quality_status}`",
        f"- Profile: `{report.requested_profile}`",
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
        lines.append("No final export issues were found.")
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


def _export_id(
    timeline_id: str,
    timeline_fingerprint: str,
    bgm_fit_fingerprint: str | None,
    profile: str,
) -> str:
    payload = f"{timeline_id}:{timeline_fingerprint}:{bgm_fit_fingerprint or 'no-bgm'}:{profile}"
    return "export_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def _issue(code: str, severity: str, detail: str) -> FinalExportValidationIssue:
    return FinalExportValidationIssue(code=code, severity=severity, detail=detail)


def _validation(
    *,
    export_ref: str,
    manifest_ref: str,
    timeline_ref: str,
    timeline_fingerprint: str,
    issues: list[FinalExportValidationIssue],
) -> FinalExportValidationReport:
    errors = sum(item.severity == "error" for item in issues)
    warnings = sum(item.severity == "warning" for item in issues)
    return FinalExportValidationReport(
        export_ref=export_ref,
        manifest_ref=manifest_ref,
        timeline_ref=timeline_ref,
        timeline_fingerprint=timeline_fingerprint,
        expected_duration=0.001,
        actual_duration=0,
        duration_delta_seconds=0,
        duration_tolerance_seconds=0.35,
        requested_profile="review_720p",
        requested_width=1280,
        requested_height=720,
        requested_aspect_ratio="16:9",
        requested_fps=24,
        actual_width=None,
        actual_height=None,
        actual_frame_rate=None,
        video_present=False,
        audio_present=False,
        audio_expected=False,
        quality_status="failed" if errors else "warning" if warnings else "passed",
        recovery_command="artist-portrait export --project <project.yaml> --profile review_720p",
        issue_count=len(issues),
        error_count=errors,
        warning_count=warnings,
        issues=issues,
        valid=errors == 0,
    )
