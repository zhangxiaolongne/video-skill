from __future__ import annotations

import hashlib
import json
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path
from shutil import copy2, which

from pydantic import ValidationError

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import CACHE_DIR, DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.media.scanner import hash_file
from artist_portrait_editor.models.final_export import FinalExportManifest, FinalExportValidationReport
from artist_portrait_editor.models.composition import CompositionReview
from artist_portrait_editor.models.state import ActiveMode, OverallStatus, StepLedgerEntry, StepStatus
from artist_portrait_editor.run_records import environment_snapshot, new_run_id, utc_now, write_json
from artist_portrait_editor.workspace_state import (
    atomic_write_text,
    fingerprint_inputs,
    load_state,
    project_root,
    save_state,
    write_run_report,
)


class CompositionEvidenceError(RuntimeError):
    pass


MAX_COMPOSITION_CANDIDATE_BYTES = 1024 * 1024


@dataclass(frozen=True)
class QuarantinedCompositionCandidate:
    ref: str
    sha256: str
    raw_bytes: bytes


def build_composition_evidence(
    project_path: Path,
    *,
    sample_count: int = 9,
) -> tuple[Path, Path, dict, list[str]]:
    if sample_count not in {4, 6, 9}:
        raise CompositionEvidenceError("composition --samples must be 4, 6, or 9")
    if which("ffmpeg") is None:
        raise CompositionEvidenceError("composition evidence requires ffmpeg")
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise CompositionEvidenceError("composition evidence requires init first")
    data_dir = root / WORKSPACE_DIR / DATA_DIR
    manifest_path = data_dir / "final_export_manifest.json"
    validation_path = data_dir / "final_export_validation.json"
    if not manifest_path.exists() or not validation_path.exists():
        raise CompositionEvidenceError("composition evidence requires a current final export")
    manifest = FinalExportManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    validation = FinalExportValidationReport.model_validate_json(validation_path.read_text(encoding="utf-8"))
    if not validation.valid:
        raise CompositionEvidenceError("composition evidence requires valid final-export media QC")
    media_path = root / manifest.output_ref
    if not media_path.exists() or hash_file(media_path) != manifest.output_content_hash:
        raise CompositionEvidenceError("composition evidence final export is missing or stale")

    evidence_id = "composition_" + hashlib.sha256(
        f"{manifest.output_content_hash}:{sample_count}".encode()
    ).hexdigest()[:20]
    cache_dir = root / WORKSPACE_DIR / CACHE_DIR / "composition" / evidence_id
    cache_dir.mkdir(parents=True, exist_ok=True)
    samples: list[dict] = []
    for index in range(sample_count):
        timestamp = round((index + 0.5) * manifest.duration / sample_count, 3)
        frame_path = cache_dir / f"frame_{index + 1:02d}.jpg"
        _ffmpeg([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", f"{timestamp:.3f}", "-i", str(media_path), "-frames:v", "1",
            "-q:v", "2", str(frame_path),
        ], frame_path)
        samples.append({
            "sample_id": f"sample_{index + 1:02d}",
            "timestamp_seconds": timestamp,
            "frame_ref": frame_path.relative_to(root).as_posix(),
            "content_hash": hash_file(frame_path),
        })

    columns = 3 if sample_count in {6, 9} else 2
    rows = math.ceil(sample_count / columns)
    contact_sheet = root / "output" / "composition_contact_sheet.jpg"
    interval = manifest.duration / sample_count
    _ffmpeg([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(media_path),
        "-vf", (
            f"fps=1/{interval:.6f},scale=360:-2,"
            f"tile={columns}x{rows}:nb_frames={sample_count}"
        ),
        "-frames:v", "1", "-q:v", "2", str(contact_sheet),
    ], contact_sheet)

    handoff = {
        "handoff_version": "1.0",
        "mode": "codex_chatgpt_host_agent_composition_review",
        "composition_evidence_id": evidence_id,
        "project_id": config.project.id,
        "timeline_id": manifest.timeline_id,
        "timeline_ref": manifest.timeline_ref,
        "timeline_fingerprint": manifest.timeline_fingerprint,
        "final_export_ref": manifest.output_ref,
        "final_export_hash": manifest.output_content_hash,
        "canvas": {
            "width": manifest.width,
            "height": manifest.height,
            "aspect_ratio": manifest.requested_profile.aspect_ratio,
            "fit_mode": manifest.requested_profile.fit_mode,
        },
        "duration_seconds": manifest.duration,
        "sample_count": sample_count,
        "samples": samples,
        "contact_sheet_ref": contact_sheet.relative_to(root).as_posix(),
        "contact_sheet_hash": hash_file(contact_sheet),
        "review_dimensions": [
            "performer_prominence",
            "persistent_branding_or_title_intrusion",
            "dead_space",
            "crop_safety",
            "protected_regions",
            "frame_usability",
        ],
        "instructions": {
            "reviewer": "active Codex/ChatGPT host Agent or explicit human reviewer",
            "truth_boundary": "Review only the supplied frames. Do not infer unseen visual content.",
            "candidate_boundary": "Any crop/reframe is a proposal until explicitly selected and rendered.",
            "next_stage": "V201-04 supervised safe-reframe candidate import",
        },
        "composition_review_json_schema": CompositionReview.model_json_schema(),
        "commands_executed": True,
        "media_rendered": False,
        "source_frames_extracted": True,
        "model_call_performed_by_cli": False,
        "network_performed": False,
        "image_generation_or_editing_used": False,
    }
    handoff_path = root / "output" / "composition_review_handoff.json"
    atomic_write_text(
        handoff_path,
        json.dumps(handoff, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )

    run_id = new_run_id()
    refs = [contact_sheet.relative_to(root).as_posix(), handoff_path.relative_to(root).as_posix()]
    state.steps["composition"] = StepLedgerEntry(
        status=StepStatus.completed,
        input_fingerprint=fingerprint_inputs([
            ("final_export_manifest", manifest_path),
            ("final_export_validation", validation_path),
            ("final_export", media_path),
        ]),
        output_refs=refs,
        last_run_id=run_id,
    )
    state.active_mode = ActiveMode.creative
    state.overall_status = OverallStatus.ready
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(runs_dir / "command.json", {"command": "composition", "project": str(project_path), "samples": sample_count})
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(runs_dir / "step_result.json", {"step": "composition", "status": "completed", "output_refs": refs})
    save_state(root, state)
    write_run_report(root / config.paths.output_dir, state, [])
    return contact_sheet, handoff_path, handoff, []


def import_composition_review(
    project_path: Path,
    *,
    candidate_path: Path,
) -> tuple[Path, Path, CompositionReview, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise CompositionEvidenceError("composition review import requires init first")
    handoff_path = root / "output" / "composition_review_handoff.json"
    if not handoff_path.exists():
        raise CompositionEvidenceError("composition review import requires composition evidence first")
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    _validate_handoff_files(root, handoff)
    candidate = _quarantine_candidate(root, candidate_path)
    try:
        review = CompositionReview.model_validate_json(candidate.raw_bytes)
    except ValidationError as exc:
        raise CompositionEvidenceError(f"composition review candidate is invalid: {exc}") from exc
    _validate_review_binding(review, handoff)

    data_dir = root / WORKSPACE_DIR / DATA_DIR
    canonical_path = data_dir / "composition_review.json"
    report_path = root / "output" / "composition_review.md"
    atomic_write_text(
        canonical_path,
        json.dumps(review.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    atomic_write_text(report_path, render_composition_review(review))

    warnings = list(review.warnings)
    if review.aesthetic_status != "usable":
        warnings.append(f"composition aesthetic status is {review.aesthetic_status}")
    warnings = list(dict.fromkeys(warnings))
    run_id = new_run_id()
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    refs = [
        candidate.ref,
        canonical_path.relative_to(root).as_posix(),
        report_path.relative_to(root).as_posix(),
    ]
    state.steps["composition_review"] = StepLedgerEntry(
        status=status,
        input_fingerprint=fingerprint_inputs([
            ("composition_handoff", handoff_path),
            ("candidate_quarantine", root / candidate.ref),
        ]),
        output_refs=refs,
        last_run_id=run_id,
        warnings=warnings,
    )
    state.active_mode = ActiveMode.creative
    state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        runs_dir / "command.json",
        {"command": "composition", "project": str(project_path), "agent_output": str(candidate_path)},
    )
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "composition_review",
            "status": status.value,
            "candidate_sha256": candidate.sha256,
            "output_refs": refs,
            "crop_applied": False,
            "media_rendered": False,
            "model_call_performed_by_cli": False,
            "network_performed": False,
        },
    )
    save_state(root, state)
    write_run_report(root / config.paths.output_dir, state, warnings)
    return canonical_path, report_path, review, warnings


def render_reframe_candidate_preview(
    project_path: Path,
    *,
    candidate_id: str,
) -> tuple[Path, dict]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise CompositionEvidenceError("reframe preview requires init first")
    review_path = root / WORKSPACE_DIR / DATA_DIR / "composition_review.json"
    handoff_path = root / "output" / "composition_review_handoff.json"
    if not review_path.exists() or not handoff_path.exists():
        raise CompositionEvidenceError("reframe preview requires an imported composition review")
    review = CompositionReview.model_validate_json(review_path.read_text(encoding="utf-8"))
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    _validate_handoff_files(root, handoff)
    _validate_review_binding(review, handoff)
    candidate = next(
        (item for item in review.reframe_candidates if item.candidate_id == candidate_id),
        None,
    )
    if candidate is None:
        raise CompositionEvidenceError(f"unknown reframe candidate: {candidate_id}")
    if candidate.status == "rejected":
        raise CompositionEvidenceError("rejected reframe candidate cannot render a review preview")

    sample_by_id = {item["sample_id"]: item for item in handoff["samples"]}
    preview_dir = (
        root
        / WORKSPACE_DIR
        / CACHE_DIR
        / "composition"
        / handoff["composition_evidence_id"]
        / candidate.candidate_id
    )
    preview_dir.mkdir(parents=True, exist_ok=True)
    box = candidate.crop_box
    preview_frames: list[Path] = []
    for index, sample_id in enumerate(candidate.applicable_sample_ids, start=1):
        source = root / sample_by_id[sample_id]["frame_ref"]
        output = preview_dir / f"preview_{index:02d}_{sample_id}.jpg"
        _ffmpeg([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(source),
            "-vf", f"crop={box.width}:{box.height}:{box.x}:{box.y},scale=360:640",
            "-frames:v", "1", "-q:v", "2", str(output),
        ], output)
        preview_frames.append(output)

    columns = min(3, len(preview_frames))
    output_path = root / "output" / f"{candidate.candidate_id}_contact_sheet.jpg"
    if len(preview_frames) == 1:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        copy2(preview_frames[0], output_path)
    else:
        _render_preview_sheet(preview_frames, output_path, columns)

    result = {
        "candidate_id": candidate.candidate_id,
        "candidate_status": candidate.status,
        "composition_evidence_id": review.composition_evidence_id,
        "review_id": review.review_id,
        "crop_box": box.model_dump(mode="json"),
        "target_aspect_ratio": candidate.target_aspect_ratio,
        "sample_ids": candidate.applicable_sample_ids,
        "preview_ref": output_path.relative_to(root).as_posix(),
        "preview_hash": hash_file(output_path),
        "candidate_preview_rendered": True,
        "crop_applied_to_final": False,
        "timeline_mutated": False,
        "final_media_rendered": False,
        "model_call_performed_by_cli": False,
        "network_performed": False,
    }
    run_id = new_run_id()
    state.steps["composition_preview"] = StepLedgerEntry(
        status=StepStatus.completed,
        input_fingerprint=fingerprint_inputs([
            ("composition_review", review_path),
            ("composition_handoff", handoff_path),
        ]),
        output_refs=[output_path.relative_to(root).as_posix()],
        last_run_id=run_id,
    )
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        runs_dir / "command.json",
        {"command": "composition", "project": str(project_path), "preview_candidate": candidate_id},
    )
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(runs_dir / "step_result.json", {"step": "composition_preview", **result})
    save_state(root, state)
    write_run_report(root / config.paths.output_dir, state, [])
    return output_path, result


def _render_preview_sheet(preview_frames: list[Path], output_path: Path, columns: int) -> None:
    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for path in preview_frames:
        command.extend(["-i", str(path)])
    filters = [f"[{index}:v]scale=360:640[s{index}]" for index in range(len(preview_frames))]
    layout = "|".join(
        f"{(index % columns) * 360}_{(index // columns) * 640}"
        for index in range(len(preview_frames))
    )
    inputs = "".join(f"[s{index}]" for index in range(len(preview_frames)))
    filters.append(
        f"{inputs}xstack=inputs={len(preview_frames)}:layout={layout}:fill=black[out]"
    )
    command.extend([
        "-filter_complex", ";".join(filters), "-map", "[out]", "-frames:v", "1",
        "-q:v", "2", str(output_path),
    ])
    _ffmpeg(command, output_path)


def render_composition_review(review: CompositionReview) -> str:
    lines = [
        "# Composition Review",
        "",
        f"- Aesthetic status: `{review.aesthetic_status}`",
        f"- Evidence: `{review.composition_evidence_id}`",
        f"- Final export: `{review.final_export_ref}`",
        f"- Reviewed frames: `{len(review.frame_reviews)}`",
        f"- Reframe candidates: `{len(review.reframe_candidates)}`",
        f"- Recommended candidate: `{review.recommended_candidate_id or 'none'}`",
        "- Crop applied: `false`",
        "- Media rendered: `false`",
        "",
        "## Frame Review",
        "",
    ]
    for item in review.frame_reviews:
        lines.append(
            f"- `{item.sample_id}` `{item.timestamp_seconds:.3f}s`: "
            f"usability `{item.usability}`, prominence `{item.performer_prominence:.2f}`, "
            f"branding `{item.branding_intrusion:.2f}`, dead space `{item.dead_space:.2f}`, "
            f"crop `{item.crop_safety}`. {' '.join(item.observations)}"
        )
    lines.extend(["", "## Reframe Candidates", ""])
    for item in review.reframe_candidates:
        box = item.crop_box
        lines.append(
            f"- `{item.candidate_id}` `{item.status}`: crop "
            f"`{box.x},{box.y},{box.width},{box.height}` -> `{item.target_aspect_ratio}`; "
            f"samples {', '.join(item.applicable_sample_ids)}. {' '.join(item.benefits)}"
        )
        if item.risks:
            lines.append(f"  Risks: {' '.join(item.risks)}")
        if item.reject_reason:
            lines.append(f"  Rejected: {item.reject_reason}")
    lines.extend(["", "## Conclusions", ""])
    lines.extend(f"- {item}" for item in review.conclusions)
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {item}" for item in review.warnings] or ["- None"])
    return "\n".join(lines) + "\n"


def _quarantine_candidate(root: Path, candidate_path: Path) -> QuarantinedCompositionCandidate:
    if candidate_path.is_symlink() or not candidate_path.is_file():
        raise CompositionEvidenceError("composition review candidate must be a regular non-symlink file")
    if candidate_path.stat().st_size > MAX_COMPOSITION_CANDIDATE_BYTES:
        raise CompositionEvidenceError("composition review candidate exceeds 1 MiB")
    raw_bytes = candidate_path.read_bytes()
    digest = hashlib.sha256(raw_bytes).hexdigest()
    path = root / WORKSPACE_DIR / "quarantine" / "composition" / f"host_agent_{digest}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        tmp = path.with_suffix(".json.tmp")
        tmp.write_bytes(raw_bytes)
        tmp.replace(path)
    return QuarantinedCompositionCandidate(
        ref=path.relative_to(root).as_posix(),
        sha256=digest,
        raw_bytes=raw_bytes,
    )


def _validate_handoff_files(root: Path, handoff: dict) -> None:
    contact_sheet = root / handoff["contact_sheet_ref"]
    if not contact_sheet.exists() or hash_file(contact_sheet) != handoff["contact_sheet_hash"]:
        raise CompositionEvidenceError("composition contact sheet is missing or stale")
    for item in handoff["samples"]:
        path = root / item["frame_ref"]
        if not path.exists() or hash_file(path) != item["content_hash"]:
            raise CompositionEvidenceError(f"composition sample is missing or stale: {item['sample_id']}")


def _validate_review_binding(review: CompositionReview, handoff: dict) -> None:
    expected = {
        "project_id": handoff["project_id"],
        "composition_evidence_id": handoff["composition_evidence_id"],
        "timeline_id": handoff["timeline_id"],
        "timeline_fingerprint": handoff["timeline_fingerprint"],
        "final_export_ref": handoff["final_export_ref"],
        "final_export_hash": handoff["final_export_hash"],
        "contact_sheet_ref": handoff["contact_sheet_ref"],
        "contact_sheet_hash": handoff["contact_sheet_hash"],
    }
    for field, value in expected.items():
        if getattr(review, field) != value:
            raise CompositionEvidenceError(f"composition review {field} binding mismatch")
    normalized_method = review.method.lower().replace("-", "_").replace(" ", "_")
    if not any(token in normalized_method for token in ("host_agent", "codex", "chatgpt", "human")):
        raise CompositionEvidenceError("composition review method must identify the host Agent or human reviewer")
    sample_by_id = {item["sample_id"]: item for item in handoff["samples"]}
    if {item.sample_id for item in review.frame_reviews} != set(sample_by_id):
        raise CompositionEvidenceError("composition review must cover every supplied sample exactly once")
    for item in review.frame_reviews:
        if abs(item.timestamp_seconds - sample_by_id[item.sample_id]["timestamp_seconds"]) > 0.001:
            raise CompositionEvidenceError(f"composition review timestamp mismatch: {item.sample_id}")
    canvas = handoff["canvas"]
    for candidate in review.reframe_candidates:
        if candidate.source_width != canvas["width"] or candidate.source_height != canvas["height"]:
            raise CompositionEvidenceError("reframe candidate source canvas binding mismatch")
    forbidden = (
        review.crop_applied,
        review.timeline_mutated,
        review.media_rendered,
        review.model_call_performed_by_cli,
        review.network_performed,
        review.image_generation_or_editing_used,
    )
    if any(forbidden) or not review.reviewed_only_supplied_frames:
        raise CompositionEvidenceError("composition review violates V2-01 truth boundaries")


def _ffmpeg(command: list[str], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(command, capture_output=True, text=True, timeout=180)
    if result.returncode != 0 or not output_path.exists():
        raise CompositionEvidenceError((result.stderr or "composition frame extraction failed").strip())
