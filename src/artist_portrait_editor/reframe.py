from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from pydantic import ValidationError

from artist_portrait_editor.composition import CompositionEvidenceError
from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import CACHE_DIR, DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.media.probe import probe_media
from artist_portrait_editor.media.rendering import (
    RenderCanvas,
    concat_files,
    fingerprint_file,
    mux_tracks,
    render_audio_segment,
    render_video_segment,
)
from artist_portrait_editor.media.scanner import hash_file
from artist_portrait_editor.models.composition import CompositionReview, PixelCropBox
from artist_portrait_editor.models.final_export import FinalExportManifest, FinalExportValidationReport
from artist_portrait_editor.models.reframe import (
    AppliedSegmentReframe,
    CropChangeAudit,
    ReframeApplication,
    ReframeSelection,
)
from artist_portrait_editor.models.state import ActiveMode, OverallStatus, StepLedgerEntry, StepStatus
from artist_portrait_editor.models.timeline import TimelineDraft
from artist_portrait_editor.run_records import environment_snapshot, new_run_id, utc_now, write_json
from artist_portrait_editor.workspace_state import atomic_write_text, fingerprint_inputs, load_state, project_root, save_state, write_run_report


class ReframeError(RuntimeError):
    pass


MAX_SELECTION_BYTES = 1024 * 1024


def apply_reframe_selection(
    project_path: Path,
    *,
    selection_path: Path,
) -> tuple[Path, Path, ReframeApplication, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise ReframeError("reframe requires init first")
    data = root / WORKSPACE_DIR / DATA_DIR
    timeline_path = root / "output" / "timeline_draft.json"
    manifest_path = data / "final_export_manifest.json"
    validation_path = data / "final_export_validation.json"
    review_path = data / "composition_review.json"
    handoff_path = root / "output" / "composition_review_handoff.json"
    required = [timeline_path, manifest_path, validation_path, review_path, handoff_path]
    missing = [path.relative_to(root).as_posix() for path in required if not path.exists()]
    if missing:
        raise ReframeError("reframe missing current evidence: " + ", ".join(missing))

    timeline = TimelineDraft.model_validate_json(timeline_path.read_text(encoding="utf-8"))
    manifest = FinalExportManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    validation = FinalExportValidationReport.model_validate_json(validation_path.read_text(encoding="utf-8"))
    review = CompositionReview.model_validate_json(review_path.read_text(encoding="utf-8"))
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    final_path = root / manifest.output_ref
    contact_sheet = root / handoff["contact_sheet_ref"]
    if not validation.valid or validation.timeline_fingerprint != fingerprint_file(timeline_path):
        raise ReframeError("reframe requires a current valid final export")
    if not final_path.exists() or hash_file(final_path) != manifest.output_content_hash:
        raise ReframeError("final export media is missing or stale")
    if not contact_sheet.exists() or hash_file(contact_sheet) != handoff["contact_sheet_hash"]:
        raise ReframeError("composition contact sheet is missing or stale")
    if review.timeline_fingerprint != fingerprint_file(timeline_path) or review.final_export_hash != manifest.output_content_hash:
        raise ReframeError("composition review is stale against timeline or final export")

    if not selection_path.is_file():
        raise ReframeError(f"reframe selection does not exist: {selection_path}")
    raw = selection_path.read_bytes()
    if not raw or len(raw) > MAX_SELECTION_BYTES:
        raise ReframeError("reframe selection must be non-empty and at most 1 MiB")
    quarantine = data / "reframe_selection_quarantine.json"
    quarantine.parent.mkdir(parents=True, exist_ok=True)
    quarantine.write_bytes(raw)
    try:
        selection = ReframeSelection.model_validate_json(raw)
    except ValidationError as exc:
        raise ReframeError(f"invalid reframe selection: {exc}") from exc

    timeline_fp = fingerprint_file(timeline_path)
    review_fp = fingerprint_file(review_path)
    expected = (
        config.project.id,
        timeline.timeline_id,
        timeline_fp,
        manifest.output_content_hash,
        review.review_id,
        review_fp,
    )
    actual = (
        selection.project_id,
        selection.timeline_id,
        selection.timeline_fingerprint,
        selection.final_export_hash,
        selection.composition_review_id,
        selection.composition_review_fingerprint,
    )
    if actual != expected:
        raise ReframeError("reframe selection does not bind current project evidence")
    timeline_segments = sorted(timeline.segments, key=lambda item: (item.timeline_start, item.segment_id))
    choices = {item.segment_id: item for item in selection.choices}
    expected_ids = {item.segment_id for item in timeline_segments}
    if set(choices) != expected_ids:
        raise ReframeError("reframe selection must explicitly cover every timeline segment")

    candidates = {item.candidate_id: item for item in review.reframe_candidates}
    samples = {item["sample_id"]: item for item in handoff["samples"]}
    canvas_box = PixelCropBox(x=0, y=0, width=manifest.width, height=manifest.height)
    applied: list[AppliedSegmentReframe] = []
    warnings: list[str] = []
    for segment in timeline_segments:
        choice = choices[segment.segment_id]
        candidate = candidates.get(choice.candidate_id) if choice.candidate_id else None
        if choice.mode == "candidate":
            if candidate is None:
                raise ReframeError(f"unknown candidate for {segment.segment_id}: {choice.candidate_id}")
            if candidate.status == "rejected":
                raise ReframeError(f"rejected candidate cannot be applied: {candidate.candidate_id}")
            segment_samples = [
                sample_id
                for sample_id, sample in samples.items()
                if segment.timeline_start
                <= float(sample["timestamp_seconds"])
                < segment.timeline_end
            ]
            applicable = sorted(set(segment_samples) & set(candidate.applicable_sample_ids))
            if not applicable:
                raise ReframeError(f"candidate {candidate.candidate_id} has no sampled evidence inside {segment.segment_id}")
            protected_ok, performer_ok = _safety(
                review, candidate.crop_box, applicable,
                candidate.source_width, candidate.source_height,
            )
            if not protected_ok:
                raise ReframeError(f"candidate {candidate.candidate_id} crops a protected region in {segment.segment_id}")
            segment_warnings: list[str] = []
            if not performer_ok:
                segment_warnings.append("sampled performer box is not fully contained; full-motion review required")
            if candidate.status == "conditional":
                segment_warnings.append("conditional crop requires playback review")
            if len(segment_samples) > len(applicable):
                segment_warnings.append("candidate does not cover every sampled frame in this segment")
            crop = candidate.crop_box
        else:
            applicable = []
            protected_ok = performer_ok = True
            segment_warnings = []
            crop = canvas_box
        warnings.extend(f"{segment.segment_id}: {item}" for item in segment_warnings)
        applied.append(AppliedSegmentReframe(
            segment_id=segment.segment_id, timeline_start=segment.timeline_start,
            timeline_end=segment.timeline_end, mode=choice.mode, candidate_id=choice.candidate_id,
            crop_box=crop, applicable_sample_ids=applicable,
            protected_regions_preserved=protected_ok, performer_regions_preserved=performer_ok,
            visible_crop_applied=(crop != canvas_box), warnings=segment_warnings,
        ))

    cache = root / WORKSPACE_DIR / CACHE_DIR / "reframe" / selection.selection_id
    cache.mkdir(parents=True, exist_ok=True)
    canvas = RenderCanvas(manifest.width, manifest.height, manifest.requested_profile.fps, manifest.requested_profile.aspect_ratio)
    segment_paths: list[Path] = []
    for index, item in enumerate(applied, start=1):
        output = cache / f"video_{index:03d}.mp4"
        render_video_segment(
            source_path=final_path, output_path=output, source_in=item.timeline_start,
            duration=item.timeline_end - item.timeline_start, canvas=canvas,
            video_transition="none", preset="medium", crf=manifest.requested_profile.video_crf,
            timeout=300, crop_box=item.crop_box,
        )
        segment_paths.append(output)
    video_track = cache / "video_concat.mp4"
    concat_files(segment_paths, video_track, media_type="video", timeout=300)
    output_path = root / "output" / "reframe_playback.mp4"
    if manifest.audio_present:
        audio_track = cache / "audio.wav"
        render_audio_segment(source_path=final_path, output_path=audio_track, source_in=0, duration=timeline.actual_duration, timeout=300)
        mux_tracks(video_track=video_track, audio_track=audio_track, output_path=output_path, audio_bitrate=manifest.requested_profile.audio_bitrate, timeout=300)
    else:
        output_path.write_bytes(video_track.read_bytes())

    _, probe = probe_media(output_path)
    duration_delta = abs(probe.duration - timeline.actual_duration)
    if duration_delta > max(0.25, 2 / manifest.requested_profile.fps):
        raise ReframeError(f"reframe playback duration drift is {duration_delta:.3f}s")
    if probe.width != manifest.width or probe.height != manifest.height:
        raise ReframeError("reframe playback canvas does not match final export")
    if bool(probe.audio_present) != bool(manifest.audio_present):
        raise ReframeError("reframe playback audio stream does not match final export")

    crop_changes = _crop_changes(applied, manifest.width, manifest.height)
    application_id = "reframe_" + hashlib.sha256((fingerprint_file(quarantine) + hash_file(output_path)).encode()).hexdigest()[:20]
    status = "warning" if warnings else "passed"
    application = ReframeApplication(
        application_id=application_id, project_id=config.project.id,
        selection_id=selection.selection_id, selection_ref=quarantine.relative_to(root).as_posix(),
        selection_fingerprint=fingerprint_file(quarantine), timeline_id=timeline.timeline_id,
        timeline_ref=timeline_path.relative_to(root).as_posix(), timeline_fingerprint=timeline_fp,
        final_export_ref=manifest.output_ref, final_export_hash=manifest.output_content_hash,
        composition_review_id=review.review_id, composition_review_ref=review_path.relative_to(root).as_posix(),
        composition_review_fingerprint=review_fp, contact_sheet_ref=handoff["contact_sheet_ref"],
        contact_sheet_hash=handoff["contact_sheet_hash"], output_ref=output_path.relative_to(root).as_posix(),
        output_hash=hash_file(output_path), duration=probe.duration, width=probe.width or 0,
        height=probe.height or 0, frame_rate=probe.frame_rate, video_present=True,
        audio_present=probe.audio_present, audio_preserved_from_final=manifest.audio_present,
        quality_status=status, segments=applied, crop_changes=crop_changes, warnings=warnings,
    )
    canonical = data / "reframe_application.json"
    report = root / "output" / "reframe_application.md"
    atomic_write_text(canonical, application.model_dump_json(indent=2) + "\n")
    atomic_write_text(report, _report(application))
    run_id = new_run_id()
    refs = [quarantine.relative_to(root).as_posix(), canonical.relative_to(root).as_posix(), report.relative_to(root).as_posix(), output_path.relative_to(root).as_posix()]
    state.steps["reframe"] = StepLedgerEntry(status=StepStatus.completed_with_warnings if warnings else StepStatus.completed, input_fingerprint=fingerprint_inputs([("selection", quarantine), ("timeline", timeline_path), ("final", final_path), ("review", review_path)]), output_refs=refs, last_run_id=run_id, warnings=warnings)
    state.active_mode = ActiveMode.creative
    state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    runs = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs.mkdir(parents=True, exist_ok=True)
    write_json(runs / "command.json", {"command": "reframe", "project": str(project_path), "selection": str(selection_path)})
    write_json(runs / "environment.json", environment_snapshot())
    write_json(runs / "step_result.json", {"step": "reframe", "status": status, "output_refs": refs, "media_rendered": True, "canonical_timeline_mutated": False, "canonical_final_overwritten": False})
    save_state(root, state)
    write_run_report(root / config.paths.output_dir, state, warnings)
    return canonical, report, application, warnings


def _contains(crop: PixelCropBox, box, width: int, height: int) -> bool:
    left, top = box.x * width, box.y * height
    right, bottom = (box.x + box.width) * width, (box.y + box.height) * height
    return left >= crop.x - 1 and top >= crop.y - 1 and right <= crop.x + crop.width + 1 and bottom <= crop.y + crop.height + 1


def _safety(
    review: CompositionReview,
    crop: PixelCropBox,
    sample_ids: list[str],
    source_width: int,
    source_height: int,
) -> tuple[bool, bool]:
    frames = {item.sample_id: item for item in review.frame_reviews}
    protected = performer = True
    for sample_id in sample_ids:
        frame = frames[sample_id]
        protected = protected and all(
            _contains(crop, box, source_width, source_height)
            for box in frame.protected_boxes
        )
        performer = performer and (
            frame.performer_box is None
            or _contains(crop, frame.performer_box, source_width, source_height)
        )
    return protected, performer


def _crop_changes(items: list[AppliedSegmentReframe], width: int, height: int) -> list[CropChangeAudit]:
    audits = []
    for previous, current in zip(items, items[1:]):
        p, c = previous.crop_box, current.crop_box
        jump = math.hypot(((p.x + p.width / 2) - (c.x + c.width / 2)) / width, ((p.y + p.height / 2) - (c.y + c.height / 2)) / height)
        risk = "high" if jump > 0.3 else "medium" if jump > 0.15 else "low"
        audits.append(CropChangeAudit(from_segment_id=previous.segment_id, to_segment_id=current.segment_id, candidate_changed=(previous.candidate_id != current.candidate_id or previous.mode != current.mode), normalized_center_jump=round(jump, 4), risk=risk))
    return audits


def _report(application: ReframeApplication) -> str:
    lines = ["# Reframe Application", "", f"- Application: `{application.application_id}`", f"- Selection: `{application.selection_id}`", f"- Quality: `{application.quality_status}`", f"- Playback: `{application.output_ref}`", f"- Duration: `{application.duration:.3f}s`", f"- Canvas: `{application.width}x{application.height}`", f"- Audio preserved: `{str(application.audio_preserved_from_final).lower()}`", f"- Canonical timeline mutated: `false`", f"- Canonical final overwritten: `false`", "", "## Segment Decisions", ""]
    for item in application.segments:
        lines.append(f"- `{item.segment_id}`: `{item.mode}` / `{item.candidate_id or 'full_frame'}` / crop `{item.crop_box.x},{item.crop_box.y},{item.crop_box.width},{item.crop_box.height}` / visible `{str(item.visible_crop_applied).lower()}`")
    lines.extend(["", "## Crop Change Audit", ""])
    for item in application.crop_changes:
        lines.append(f"- `{item.from_segment_id}` -> `{item.to_segment_id}`: jump `{item.normalized_center_jump:.4f}`, risk `{item.risk}`")
    if application.warnings:
        lines.extend(["", "## Warnings", ""] + [f"- {item}" for item in application.warnings])
    return "\n".join(lines) + "\n"
