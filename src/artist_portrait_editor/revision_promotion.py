from __future__ import annotations

import hashlib
import json
from pathlib import Path

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.revision_application import RevisionApplication
from artist_portrait_editor.models.revision_promotion import (
    RevisionPromotion,
    RevisionPromotionInvalidation,
    RevisionPromotionSegmentBinding,
)
from artist_portrait_editor.models.source import EvidenceRef
from artist_portrait_editor.models.state import ActiveMode, OverallStatus, StepLedgerEntry, StepStatus
from artist_portrait_editor.models.timeline import TimelineContinuityCheck, TimelineDraft, TimelineSegment
from artist_portrait_editor.run_records import environment_snapshot, new_run_id, utc_now, write_json
from artist_portrait_editor.workspace_errors import WorkspacePrerequisiteError
from artist_portrait_editor.workspace_state import (
    atomic_write_text,
    fingerprint_file,
    fingerprint_inputs,
    load_state,
    project_root,
    save_state,
    write_run_report,
)


class RevisionPromotionError(RuntimeError):
    pass


DOWNSTREAM_STEPS = (
    "sound",
    "bgm_analyze",
    "bgm_recommend",
    "review_bgm_recommendation",
    "bgm_fit",
    "preview",
    "review_preview",
    "final_export",
    "review_final_export",
    "review_bgm",
    "rhythm",
    "rhythm_qc_preview",
    "rhythm_qc_delivery",
    "cut_review",
    "revision",
    "acceptance",
    "review_project",
    "operator",
    "editor_package",
    "nle_plan",
    "fcpxml_draft",
    "fcpxml_import_review",
    "fcpxml_repair_plan",
)


def build_revision_promotion_workspace(
    project_path: Path,
    *,
    revision_application_id: str,
) -> tuple[Path, Path, Path, RevisionPromotion, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("promote-revision requires init to complete first")
    if state.steps.get("timeline", StepLedgerEntry()).status not in {
        StepStatus.completed,
        StepStatus.completed_with_warnings,
    }:
        raise WorkspacePrerequisiteError("promote-revision requires a current timeline first")
    if state.steps.get("revision_application", StepLedgerEntry()).status not in {
        StepStatus.completed,
        StepStatus.completed_with_warnings,
    }:
        raise WorkspacePrerequisiteError("promote-revision requires apply-revision to complete first")

    output_dir = root / config.paths.output_dir
    data_dir = root / WORKSPACE_DIR / DATA_DIR
    timeline_path = output_dir / "timeline_draft.json"
    application_path = data_dir / "revision_application.json"
    if not timeline_path.exists():
        raise WorkspacePrerequisiteError("promote-revision requires output/timeline_draft.json")
    if not application_path.exists():
        raise WorkspacePrerequisiteError("promote-revision requires revision_application.json")

    baseline_timeline = TimelineDraft.model_validate_json(timeline_path.read_text(encoding="utf-8"))
    application = RevisionApplication.model_validate_json(application_path.read_text(encoding="utf-8"))
    promoted_timeline = build_promoted_timeline(
        current_timeline=baseline_timeline,
        current_timeline_fingerprint=fingerprint_file(timeline_path),
        application=application,
        requested_revision_application_id=revision_application_id,
        application_fingerprint=fingerprint_file(application_path),
    )

    atomic_write_text(
        timeline_path,
        json.dumps(
            promoted_timeline.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    promoted_fingerprint = fingerprint_file(timeline_path)
    invalidated = _invalidate_downstream_steps(state)
    warnings = list(application.warnings)
    if invalidated:
        warnings.append(
            "downstream artifacts were invalidated because the canonical timeline changed"
        )
    warnings = list(dict.fromkeys(warnings))
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    promotion = build_revision_promotion(
        project_id=config.project.id,
        application=application,
        application_ref=application_path.relative_to(root).as_posix(),
        application_fingerprint=fingerprint_file(application_path),
        baseline_timeline=baseline_timeline,
        promoted_timeline=promoted_timeline,
        promoted_timeline_ref=timeline_path.relative_to(root).as_posix(),
        promoted_timeline_fingerprint=promoted_fingerprint,
        invalidated_steps=invalidated,
        warnings=warnings,
    )

    json_path = data_dir / "revision_promotion.json"
    md_path = output_dir / "revision_promotion.md"
    atomic_write_text(
        json_path,
        json.dumps(promotion.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    atomic_write_text(md_path, render_revision_promotion(promotion))

    run_id = new_run_id()
    timeline_input_fingerprint = fingerprint_inputs(
        [
            ("baseline_timeline", timeline_path),
            ("revision_application", application_path),
        ]
    )
    state.steps["timeline"] = StepLedgerEntry(
        status=status,
        input_fingerprint=timeline_input_fingerprint,
        output_refs=[
            timeline_path.relative_to(root).as_posix(),
            json_path.relative_to(root).as_posix(),
            md_path.relative_to(root).as_posix(),
        ],
        last_run_id=run_id,
        warnings=warnings,
    )
    state.steps["revision_promotion"] = StepLedgerEntry(
        status=status,
        input_fingerprint=timeline_input_fingerprint,
        output_refs=[
            json_path.relative_to(root).as_posix(),
            md_path.relative_to(root).as_posix(),
            timeline_path.relative_to(root).as_posix(),
        ],
        last_run_id=run_id,
        warnings=warnings,
    )
    state.active_mode = ActiveMode.creative
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready

    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        runs_dir / "command.json",
        {
            "command": "promote-revision",
            "project": str(project_path),
            "revision_application_id": revision_application_id,
        },
    )
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "revision_promotion",
            "status": status.value,
            "output_refs": state.steps["revision_promotion"].output_refs,
            "warnings": warnings,
            "invalidated_steps": [item.step for item in invalidated],
            "commands_executed": False,
            "media_rendered": False,
            "canonical_timeline_mutated": True,
            "canonical_edit_points_moved": promotion.canonical_edit_points_moved,
            "automatic_music_selection": False,
            "automatic_bgm_fit": False,
            "model_call_performed_by_cli": False,
            "network_performed": False,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text("revision promotion completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(output_dir, state, warnings)
    return timeline_path, json_path, md_path, promotion, warnings


def build_promoted_timeline(
    *,
    current_timeline: TimelineDraft,
    current_timeline_fingerprint: str,
    application: RevisionApplication,
    requested_revision_application_id: str,
    application_fingerprint: str,
) -> TimelineDraft:
    if application.revision_application_id != requested_revision_application_id:
        raise RevisionPromotionError("revision_application_id does not match current revision_application.json")
    if application.project_id != current_timeline.project_id:
        raise RevisionPromotionError("revision application project_id mismatches current timeline")
    if application.status == "blocked":
        raise RevisionPromotionError("blocked revision application cannot be promoted")
    if application.baseline_timeline_id != current_timeline.timeline_id:
        raise RevisionPromotionError("revision application does not bind to the current timeline")
    if application.baseline_timeline_fingerprint != current_timeline_fingerprint:
        raise RevisionPromotionError("revision application baseline timeline fingerprint is stale")
    if not application.revised_segments:
        raise RevisionPromotionError("revision application has no revised segments to promote")

    promoted_segments = [
        segment.model_copy(
            update={
                "reason": segment.reason + " Promoted from revision application.",
                "evidence": [
                    *segment.evidence,
                    EvidenceRef(type="revision_application", ref=application.revision_application_id),
                ],
            }
        )
        for segment in application.revised_segments
    ]
    promoted_duration = round(max(segment.timeline_end for segment in promoted_segments), 6)
    key = "|".join(
        [
            current_timeline.project_id,
            current_timeline.timeline_id,
            application.revision_application_id,
            application.selected_version_id,
            current_timeline_fingerprint,
            application_fingerprint,
        ]
    )
    promoted_id = "timeline_revision_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    input_fingerprint = "sha256:" + hashlib.sha256(key.encode("utf-8")).hexdigest()
    target_duration = max(current_timeline.target_duration, promoted_duration)
    strategy = list(dict.fromkeys([
        *current_timeline.structure_strategy,
        "promoted controlled revision candidate",
    ]))
    warnings = list(dict.fromkeys([
        *current_timeline.warnings,
        f"promoted from revision application {application.revision_application_id}",
    ]))
    return current_timeline.model_copy(
        update={
            "timeline_id": promoted_id,
            "input_fingerprint": input_fingerprint,
            "target_duration": target_duration,
            "actual_duration": promoted_duration,
            "segments": promoted_segments,
            "continuity_checks": _continuity_checks(promoted_segments),
            "structure_strategy": strategy,
            "warnings": warnings,
            "evidence": [
                *current_timeline.evidence,
                EvidenceRef(type="revision_application", ref=application.revision_application_id),
            ],
            "timeline_mutated": False,
            "edit_points_moved": False,
            "commands_executed": False,
            "media_rendered": False,
            "automatic_music_selection": False,
            "automatic_bgm_fit": False,
            "model_call_performed_by_cli": False,
            "network_performed": False,
            "image_generation_or_editing_used": False,
        }
    )


def build_revision_promotion(
    *,
    project_id: str,
    application: RevisionApplication,
    application_ref: str,
    application_fingerprint: str,
    baseline_timeline: TimelineDraft,
    promoted_timeline: TimelineDraft,
    promoted_timeline_ref: str,
    promoted_timeline_fingerprint: str,
    invalidated_steps: list[RevisionPromotionInvalidation],
    warnings: list[str],
) -> RevisionPromotion:
    changed_count = sum(
        1 for item in application.segment_changes if item.status in {"trimmed", "removed", "moved"}
    )
    key = "|".join(
        [
            project_id,
            application.revision_application_id,
            baseline_timeline.timeline_id,
            promoted_timeline.timeline_id,
            promoted_timeline_fingerprint,
        ]
    )
    bindings = [
        RevisionPromotionSegmentBinding(
            source_segment_id=item.source_segment_id,
            promoted_segment_id=item.revised_segment_id or "removed",
            status=item.status,
            action_ids=item.action_ids,
            baseline_timeline_start=item.baseline_timeline_start,
            baseline_timeline_end=item.baseline_timeline_end,
            promoted_timeline_start=item.revised_timeline_start,
            promoted_timeline_end=item.revised_timeline_end,
            duration_delta_seconds=item.duration_delta_seconds,
        )
        for item in application.segment_changes
    ]
    return RevisionPromotion(
        revision_promotion_id="revision_promotion_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:20],
        project_id=project_id,
        status="warning" if warnings else "promoted",
        revision_application_id=application.revision_application_id,
        revision_application_ref=application_ref,
        revision_application_fingerprint=application_fingerprint,
        selected_version_id=application.selected_version_id,
        baseline_timeline_id=baseline_timeline.timeline_id,
        baseline_timeline_ref=application.baseline_timeline_ref,
        baseline_timeline_fingerprint=application.baseline_timeline_fingerprint,
        promoted_timeline_id=promoted_timeline.timeline_id,
        promoted_timeline_ref=promoted_timeline_ref,
        promoted_timeline_fingerprint=promoted_timeline_fingerprint,
        current_duration_seconds=application.current_duration_seconds,
        promoted_duration_seconds=promoted_timeline.actual_duration,
        duration_delta_seconds=promoted_timeline.actual_duration - application.current_duration_seconds,
        baseline_segment_count=application.baseline_segment_count,
        promoted_segment_count=len(promoted_timeline.segments),
        changed_segment_count=changed_count,
        segment_bindings=bindings,
        invalidated_steps=invalidated_steps,
        warnings=warnings,
        next_commands=[
            "artist-portrait sound --project <project.yaml>",
            "artist-portrait preview --project <project.yaml>",
            "artist-portrait export --project <project.yaml> --profile review_720p",
        ],
        canonical_edit_points_moved=application.revised_candidate_edit_points_changed,
    )


def render_revision_promotion(promotion: RevisionPromotion) -> str:
    lines = [
        "# Revision Promotion",
        "",
        f"- Status: `{promotion.status}`",
        f"- Revision application: `{promotion.revision_application_id}`",
        f"- Selected version: `{promotion.selected_version_id}`",
        f"- Baseline timeline: `{promotion.baseline_timeline_id}`",
        f"- Promoted timeline: `{promotion.promoted_timeline_id}`",
        f"- Baseline fingerprint: `{promotion.baseline_timeline_fingerprint}`",
        f"- Promoted fingerprint: `{promotion.promoted_timeline_fingerprint}`",
        f"- Current duration: `{promotion.current_duration_seconds:.2f}s`",
        f"- Promoted duration: `{promotion.promoted_duration_seconds:.2f}s`",
        f"- Duration delta: `{promotion.duration_delta_seconds:.2f}s`",
        f"- Changed segments: `{promotion.changed_segment_count}`",
        "",
        "## Segment Bindings",
        "",
    ]
    for item in promotion.segment_bindings:
        lines.append(
            f"- `{item.source_segment_id}` -> `{item.promoted_segment_id}`; `{item.status}`; delta `{item.duration_delta_seconds:.2f}s`"
        )
    lines.extend(["", "## Invalidated Steps", ""])
    if promotion.invalidated_steps:
        for item in promotion.invalidated_steps:
            lines.append(f"- `{item.step}` from `{item.previous_status}`: {item.reason}")
    else:
        lines.append("- none")
    if promotion.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in promotion.warnings)
    lines.extend(["", "## Next Commands", ""])
    lines.extend(f"- `{command}`" for command in promotion.next_commands)
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- Media rendered: `false`",
            "- Canonical timeline mutated: `true`",
            f"- Canonical edit points moved: `{str(promotion.canonical_edit_points_moved).lower()}`",
            "- Automatic music selection: `false`",
            "- Automatic BGM fit: `false`",
            "- Model call by CLI: `false`",
            "- Network access: `false`",
            "- Image generation/editing: `false`",
            "",
        ]
    )
    return "\n".join(lines)


def _invalidate_downstream_steps(state) -> list[RevisionPromotionInvalidation]:
    invalidated: list[RevisionPromotionInvalidation] = []
    for step in DOWNSTREAM_STEPS:
        entry = state.steps.get(step)
        if entry is None or entry.status not in {
            StepStatus.completed,
            StepStatus.completed_with_warnings,
            StepStatus.blocked,
        }:
            continue
        state.steps[step] = StepLedgerEntry(
            status=StepStatus.invalidated,
            input_fingerprint=entry.input_fingerprint,
            output_refs=entry.output_refs,
            last_run_id=entry.last_run_id,
            warnings=[
                *entry.warnings,
                "canonical timeline changed by revision promotion; rerun before trusting this output",
            ],
        )
        invalidated.append(
            RevisionPromotionInvalidation(
                step=step,
                previous_status=entry.status.value,
                output_refs=entry.output_refs,
                reason="canonical timeline changed by revision promotion",
            )
        )
    return invalidated


def _continuity_checks(segments: list[TimelineSegment]) -> list[TimelineContinuityCheck]:
    checks: list[TimelineContinuityCheck] = []
    ordered = sorted(segments, key=lambda item: item.timeline_start)
    for previous, current in zip(ordered, ordered[1:]):
        if previous.source_id == current.source_id:
            if abs(previous.source_out - current.source_in) <= 0.001:
                status = "same_source_continuous"
                risk = "low"
                detail = "same source with continuous source timing"
            else:
                status = "same_source_jump"
                risk = "medium"
                detail = "same source with a source-time jump after revision promotion"
        elif previous.track_id == "A1" or current.track_id == "A1":
            status = "audio_only_transition"
            risk = "medium"
            detail = "audio-only transition after revision promotion"
        else:
            status = "cross_source_cut"
            risk = "medium"
            detail = "cross-source cut after revision promotion"
        checks.append(
            TimelineContinuityCheck(
                from_segment_id=previous.segment_id,
                to_segment_id=current.segment_id,
                status=status,
                detail=detail,
                risk_level=risk,
            )
        )
    return checks
