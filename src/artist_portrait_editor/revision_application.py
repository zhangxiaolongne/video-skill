from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.revision import RevisionAction, RevisionPlan
from artist_portrait_editor.models.revision_application import (
    DownstreamRevisionFreshness,
    RevisionApplication,
    RevisionAppliedAction,
    RevisionSemanticOutcome,
    RevisionSegmentChange,
)
from artist_portrait_editor.models.state import ActiveMode, OverallStatus, StepLedgerEntry, StepStatus
from artist_portrait_editor.models.timeline import TimelineDraft, TimelineSegment
from artist_portrait_editor.run_records import environment_snapshot, new_run_id, utc_now, write_json
from artist_portrait_editor.workspace_errors import WorkspacePrerequisiteError
from artist_portrait_editor.workspace_state import (
    atomic_write_text,
    load_state,
    project_root,
    save_state,
    write_run_report,
)


class RevisionApplicationError(RuntimeError):
    pass


@dataclass
class _WorkingSegment:
    segment: TimelineSegment
    baseline_start: float
    baseline_end: float
    source_segment_id: str
    action_ids: list[str]
    status: str = "unchanged"
    detail: str = "Segment carried forward unchanged."


def build_revision_application_workspace(
    project_path: Path,
    *,
    version_id: str,
    action_ids: list[str] | None = None,
) -> tuple[Path, Path, RevisionApplication, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("apply-revision requires init to complete first")
    data_dir = root / WORKSPACE_DIR / DATA_DIR
    timeline_path = root / "output" / "timeline_draft.json"
    revision_plan_path = data_dir / "revision_plan.json"
    if state.steps.get("timeline", StepLedgerEntry()).status not in {
        StepStatus.completed,
        StepStatus.completed_with_warnings,
    }:
        raise WorkspacePrerequisiteError("apply-revision requires timeline to complete first")
    if not timeline_path.exists():
        raise WorkspacePrerequisiteError("apply-revision requires output/timeline_draft.json")
    if not revision_plan_path.exists():
        raise WorkspacePrerequisiteError("apply-revision requires revise to complete first")

    timeline = TimelineDraft.model_validate_json(timeline_path.read_text(encoding="utf-8"))
    plan = RevisionPlan.model_validate_json(revision_plan_path.read_text(encoding="utf-8"))
    application = build_revision_application(
        project_id=config.project.id,
        timeline=timeline,
        timeline_ref=timeline_path.relative_to(root).as_posix(),
        timeline_fingerprint=_fingerprint(timeline_path),
        revision_plan=plan,
        revision_plan_ref=revision_plan_path.relative_to(root).as_posix(),
        revision_plan_fingerprint=_fingerprint(revision_plan_path),
        selected_version_id=version_id,
        requested_action_ids=action_ids or [],
        root=root,
    )

    json_path = data_dir / "revision_application.json"
    md_path = root / "output" / "revision_application.md"
    atomic_write_text(
        json_path,
        json.dumps(application.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    atomic_write_text(md_path, render_revision_application(application))

    warnings = application.warnings
    run_id = new_run_id()
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    state.steps["revision_application"] = StepLedgerEntry(
        status=status,
        input_fingerprint=_fingerprint_many([timeline_path, revision_plan_path]),
        output_refs=[json_path.relative_to(root).as_posix(), md_path.relative_to(root).as_posix()],
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
            "command": "apply-revision",
            "project": str(project_path),
            "version_id": version_id,
            "action_ids": action_ids or [],
        },
    )
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "revision_application",
            "status": status.value,
            "output_refs": [json_path.relative_to(root).as_posix(), md_path.relative_to(root).as_posix()],
            "warnings": warnings,
            "commands_executed": False,
            "media_rendered": False,
            "canonical_timeline_mutated": False,
            "canonical_edit_points_moved": False,
            "automatic_music_selection": False,
            "model_call_performed": False,
            "network_performed": False,
        },
    )
    save_state(root, state)
    write_run_report(root / config.paths.output_dir, state, warnings)
    return json_path, md_path, application, warnings


def build_revision_application(
    *,
    project_id: str,
    timeline: TimelineDraft,
    timeline_ref: str,
    timeline_fingerprint: str,
    revision_plan: RevisionPlan,
    revision_plan_ref: str,
    revision_plan_fingerprint: str,
    selected_version_id: str,
    requested_action_ids: list[str],
    root: Path,
) -> RevisionApplication:
    if timeline.project_id != project_id:
        raise RevisionApplicationError("timeline project_id mismatches project config")
    if revision_plan.project_id != project_id:
        raise RevisionApplicationError("revision plan project_id mismatches project config")
    if revision_plan.timeline_id != timeline.timeline_id:
        raise RevisionApplicationError("revision plan does not bind to the current timeline")
    if revision_plan.timeline_fingerprint != timeline_fingerprint:
        raise RevisionApplicationError("revision plan timeline fingerprint is stale")
    if selected_version_id == "current_version":
        raise RevisionApplicationError("apply-revision requires a non-current revision candidate")
    candidate = next(
        (item for item in revision_plan.version_candidates if item.version_id == selected_version_id),
        None,
    )
    if candidate is None:
        raise RevisionApplicationError(f"revision candidate not found: {selected_version_id}")
    candidate_action_ids = list(candidate.action_ids)
    selected_action_ids = requested_action_ids or candidate_action_ids
    unknown = sorted(set(selected_action_ids) - {action.action_id for action in revision_plan.actions})
    if unknown:
        raise RevisionApplicationError("unknown revision action ids: " + ", ".join(unknown))

    ordered = sorted(timeline.segments, key=lambda item: item.timeline_start)
    working = [
        _WorkingSegment(
            segment=segment,
            baseline_start=segment.timeline_start,
            baseline_end=segment.timeline_end,
            source_segment_id=segment.segment_id,
            action_ids=[],
        )
        for segment in ordered
    ]
    by_segment = {item.segment.segment_id: item for item in working}
    action_results: list[RevisionAppliedAction] = []
    warnings: list[str] = []
    protected_segments = {
        action.segment_id
        for action in revision_plan.actions
        if action.action_id in selected_action_ids and action.action_type == "keep" and action.segment_id
    }

    for action in revision_plan.actions:
        if action.action_id not in selected_action_ids:
            action_results.append(_action_result(action, "skipped", "not_selected", "Action was not selected for this application."))
            continue
        if action.action_type == "keep":
            result = _apply_keep(action, by_segment)
        elif action.action_type == "trim":
            result = _apply_trim(action, by_segment, protected_segments)
        elif action.action_type == "remove":
            result = _apply_remove(action, working, by_segment, protected_segments)
        elif action.action_type == "frontload_hook":
            result = _apply_frontload(action, working, by_segment)
        elif action.action_type == "strengthen_emotion":
            result = _apply_emotion_anchor(action, by_segment)
        else:
            result = _action_result(
                action,
                "manual_only",
                "unsupported_by_candidate_builder",
                f"{action.action_type} changes require editor or audio/text-specific tooling and were not applied to the revised timeline candidate.",
            )
        action_results.append(result)
    working = [item for item in working if item.status != "removed"]
    if not working:
        raise RevisionApplicationError("selected revision actions removed every segment")

    revised_segments = _retime_segments(working)
    segment_changes = _segment_changes(ordered, working)
    revised_duration = max(segment.timeline_end for segment in revised_segments)
    applied = sum(1 for item in action_results if item.status == "applied")
    manual = sum(1 for item in action_results if item.status == "manual_only")
    skipped = sum(1 for item in action_results if item.status == "skipped")
    conflicts = sum(1 for item in action_results if item.status == "conflict")
    if manual:
        warnings.append(f"{manual} selected revision actions remain manual-only")
    if conflicts:
        warnings.append(f"{conflicts} selected revision actions were blocked by conflicts")
    if not applied and selected_action_ids:
        warnings.append("no selected revision action changed the candidate timeline")

    downstream = _downstream_freshness(root)
    if any(item.present for item in downstream):
        warnings.append("existing preview/final/rhythm artifacts would be stale if this candidate is promoted")

    key = "|".join(
        [
            project_id,
            timeline.timeline_id,
            revision_plan.revision_plan_id,
            selected_version_id,
            ",".join(selected_action_ids),
            timeline_fingerprint,
            revision_plan_fingerprint,
        ]
    )
    semantic_outcomes = _semantic_outcomes(revision_plan, action_results)
    return RevisionApplication(
        revision_application_id="revision_application_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:20],
        project_id=project_id,
        status="blocked" if conflicts and not applied else "warning" if warnings else "ready",
        revision_plan_id=revision_plan.revision_plan_id,
        revision_plan_ref=revision_plan_ref,
        revision_plan_fingerprint=revision_plan_fingerprint,
        baseline_timeline_id=timeline.timeline_id,
        baseline_timeline_ref=timeline_ref,
        baseline_timeline_fingerprint=timeline_fingerprint,
        selected_version_id=selected_version_id,
        selected_action_ids=selected_action_ids,
        current_duration_seconds=timeline.actual_duration,
        revised_duration_seconds=revised_duration,
        duration_delta_seconds=revised_duration - timeline.actual_duration,
        baseline_segment_count=len(ordered),
        revised_segment_count=len(revised_segments),
        applied_action_count=applied,
        manual_action_count=manual,
        skipped_action_count=skipped,
        conflict_count=conflicts,
        revised_segments=revised_segments,
        segment_changes=segment_changes,
        action_results=action_results,
        semantic_outcomes=semantic_outcomes,
        downstream_freshness=downstream,
        warnings=warnings,
        next_command="artist-portrait preview --project <project.yaml>",
        revised_candidate_edit_points_changed=any(
            change.status in {"trimmed", "removed", "moved"} for change in segment_changes
        ),
    )


def render_revision_application(application: RevisionApplication) -> str:
    lines = [
        "# Revision Application",
        "",
        f"- Status: `{application.status}`",
        f"- Selected version: `{application.selected_version_id}`",
        f"- Revision plan: `{application.revision_plan_ref}`",
        f"- Baseline timeline: `{application.baseline_timeline_ref}`",
        f"- Current duration: `{application.current_duration_seconds:.2f}s`",
        f"- Revised candidate duration: `{application.revised_duration_seconds:.2f}s`",
        f"- Duration delta: `{application.duration_delta_seconds:.2f}s`",
        f"- Applied actions: `{application.applied_action_count}`",
        f"- Manual-only actions: `{application.manual_action_count}`",
        f"- Conflicts: `{application.conflict_count}`",
        "",
        "## Action Results",
        "",
    ]
    for result in application.action_results:
        lines.extend(
            [
                f"### {result.action_id}",
                "",
                f"- Type: `{result.action_type}`",
                f"- Status: `{result.status}`",
                f"- Segment: `{result.segment_id or 'none'}`",
                f"- Reason: `{result.reason_code}`",
                f"- Detail: {result.detail}",
                f"- Duration delta: `{result.duration_delta_seconds:.2f}s`",
                "",
            ]
        )
    lines.extend(["## Segment Changes", ""])
    for change in application.segment_changes:
        lines.extend(
            [
                f"- `{change.source_segment_id}` -> `{change.status}`; delta `{change.duration_delta_seconds:.2f}s`; {change.detail}",
            ]
        )
    lines.extend(["", "## Semantic Outcomes", ""])
    for outcome in application.semantic_outcomes:
        lines.append(
            f"- `{outcome.clause_id}` {outcome.domain}/{outcome.operation}: `{outcome.status}`; actions `{', '.join(outcome.action_ids) or 'none'}`"
        )
    lines.extend(["", "## Downstream Freshness", ""])
    for item in application.downstream_freshness:
        lines.extend(
            [
                f"- `{item.artifact_ref}`: `{item.status_if_candidate_promoted}`; {item.reason}",
            ]
        )
    if application.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in application.warnings)
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- Media rendered: `false`",
            "- Canonical timeline mutated: `false`",
            "- Canonical edit points moved: `false`",
            "- Automatic music selection: `false`",
            "- Automatic BGM fit: `false`",
            "- Model call by CLI: `false`",
            "- Network access: `false`",
            "- Image generation/editing: `false`",
            "",
        ]
    )
    return "\n".join(lines)


def _semantic_outcomes(
    plan: RevisionPlan, results: list[RevisionAppliedAction]
) -> list[RevisionSemanticOutcome]:
    result_by_id = {item.action_id: item for item in results}
    outcomes: list[RevisionSemanticOutcome] = []
    for clause in plan.semantic_clauses:
        actions = [
            action for action in plan.actions
            if clause.clause_id in action.evidence_refs
        ]
        statuses = [result_by_id[action.action_id].status for action in actions if action.action_id in result_by_id]
        if not actions or not statuses:
            status = "manual_only"
        elif all(item in {"applied", "preserved"} for item in statuses):
            status = "applied"
        elif any(item == "conflict" for item in statuses):
            status = "blocked"
        elif any(item in {"applied", "preserved"} for item in statuses):
            status = "partially_applied"
        elif all(item == "skipped" for item in statuses):
            status = "not_selected"
        else:
            status = "manual_only"
        outcomes.append(
            RevisionSemanticOutcome(
                clause_id=clause.clause_id,
                domain=clause.domain,
                operation=clause.operation,
                action_ids=[item.action_id for item in actions],
                status=status,
                evidence=[item.reason_code for item in (result_by_id[a.action_id] for a in actions if a.action_id in result_by_id)],
                acceptance_observations=clause.acceptance_observations,
            )
        )
    return outcomes


def _apply_keep(action: RevisionAction, by_segment: dict[str, _WorkingSegment]) -> RevisionAppliedAction:
    item = by_segment.get(action.segment_id or "")
    if item is None:
        return _action_result(action, "conflict", "segment_not_found", "Segment requested for keep was not found.")
    item.action_ids.append(action.action_id)
    item.status = "kept" if item.status == "unchanged" else item.status
    item.detail = "User-selected keep constraint preserved."
    return _action_result(action, "preserved", "keep_constraint_preserved", "Segment is preserved in the revised candidate.")


def _apply_trim(
    action: RevisionAction,
    by_segment: dict[str, _WorkingSegment],
    protected_segments: set[str],
) -> RevisionAppliedAction:
    item = by_segment.get(action.segment_id or "")
    if item is None:
        return _action_result(action, "conflict", "segment_not_found", "Segment requested for trim was not found.")
    if item.segment.segment_id in protected_segments:
        return _action_result(action, "conflict", "keep_constraint_conflict", "Trim conflicts with an explicit keep constraint.")
    duration = item.segment.timeline_end - item.segment.timeline_start
    trim_amount = min(max(duration * 0.15, 0.25), max(duration - 0.5, 0.0))
    if trim_amount <= 0:
        return _action_result(action, "conflict", "segment_too_short", "Segment is too short to trim safely.")
    new_source_out = item.segment.source_out - trim_amount
    item.segment = item.segment.model_copy(
        update={
            "source_out": new_source_out,
            "timeline_end": item.segment.timeline_start + (new_source_out - item.segment.source_in),
            "reason": item.segment.reason + " Revised candidate trims low-density edge.",
            "keep_reason": item.segment.keep_reason or "Retained after controlled trim.",
        }
    )
    item.action_ids.append(action.action_id)
    item.status = "trimmed"
    item.detail = f"Trimmed {trim_amount:.2f}s from the segment tail."
    return _action_result(
        action,
        "applied",
        "tail_trim_applied",
        item.detail,
        duration_delta=-trim_amount,
    )


def _apply_remove(
    action: RevisionAction,
    working: list[_WorkingSegment],
    by_segment: dict[str, _WorkingSegment],
    protected_segments: set[str],
) -> RevisionAppliedAction:
    item = by_segment.get(action.segment_id or "")
    if item is None:
        return _action_result(action, "conflict", "segment_not_found", "Segment requested for removal was not found.")
    if item.segment.segment_id in protected_segments:
        return _action_result(action, "conflict", "keep_constraint_conflict", "Remove conflicts with an explicit keep constraint.")
    if len([candidate for candidate in working if candidate.status != "removed"]) <= 1:
        return _action_result(action, "conflict", "last_segment_guard", "Removal would leave the revised candidate empty.")
    duration = item.segment.timeline_end - item.segment.timeline_start
    item.status = "removed"
    item.action_ids.append(action.action_id)
    item.detail = "Segment removed from the revised candidate."
    return _action_result(
        action,
        "applied",
        "segment_removed",
        item.detail,
        duration_delta=-duration,
    )


def _apply_frontload(
    action: RevisionAction,
    working: list[_WorkingSegment],
    by_segment: dict[str, _WorkingSegment],
) -> RevisionAppliedAction:
    item = by_segment.get(action.segment_id or "")
    if item is None:
        return _action_result(action, "conflict", "segment_not_found", "Segment requested for frontload was not found.")
    active = [candidate for candidate in working if candidate.status != "removed"]
    if active and active[0].segment.segment_id == item.segment.segment_id:
        item.action_ids.append(action.action_id)
        item.status = "kept" if item.status == "unchanged" else item.status
        return _action_result(action, "preserved", "already_opening", "Selected segment is already the opening segment.")
    working.remove(item)
    insert_at = next((index for index, candidate in enumerate(working) if candidate.status != "removed"), 0)
    working.insert(insert_at, item)
    item.action_ids.append(action.action_id)
    item.status = "moved"
    item.detail = "Segment moved to the first active position in the revised candidate."
    return _action_result(action, "applied", "frontloaded", item.detail)


def _apply_emotion_anchor(
    action: RevisionAction,
    by_segment: dict[str, _WorkingSegment],
) -> RevisionAppliedAction:
    item = by_segment.get(action.segment_id or "")
    if item is None:
        return _action_result(action, "conflict", "segment_not_found", "Segment requested for emotional anchor was not found.")
    item.action_ids.append(action.action_id)
    item.status = "kept" if item.status == "unchanged" else item.status
    item.detail = "Emotional anchor preserved; timing expansion remains manual without source-bound evidence."
    return _action_result(
        action,
        "preserved",
        "anchor_preserved",
        item.detail,
    )


def _retime_segments(working: list[_WorkingSegment]) -> list[TimelineSegment]:
    cursor = 0.0
    revised: list[TimelineSegment] = []
    for index, item in enumerate(working, start=1):
        duration = item.segment.source_out - item.segment.source_in
        segment = item.segment.model_copy(
            update={
                "segment_id": f"revision_{index:03d}_{item.source_segment_id}",
                "timeline_start": round(cursor, 6),
                "timeline_end": round(cursor + duration, 6),
                "continuity_note": _continuity_note(item),
            }
        )
        revised.append(segment)
        item.segment = segment
        cursor += duration
    return revised


def _segment_changes(
    baseline: list[TimelineSegment],
    working: list[_WorkingSegment],
) -> list[RevisionSegmentChange]:
    by_source = {item.source_segment_id: item for item in working}
    changes: list[RevisionSegmentChange] = []
    for segment in baseline:
        item = by_source.get(segment.segment_id)
        if item is None:
            status = "removed"
            revised_id = None
            revised_start = None
            revised_end = None
            delta = -(segment.timeline_end - segment.timeline_start)
            detail = "Segment removed from revised candidate."
            action_ids: list[str] = []
        else:
            revised_id = item.segment.segment_id
            revised_start = item.segment.timeline_start
            revised_end = item.segment.timeline_end
            delta = (item.segment.timeline_end - item.segment.timeline_start) - (
                segment.timeline_end - segment.timeline_start
            )
            status = item.status
            if status == "kept":
                status = "kept"
            elif status not in {"trimmed", "moved"}:
                status = "unchanged"
            detail = item.detail
            action_ids = item.action_ids
        changes.append(
            RevisionSegmentChange(
                source_segment_id=segment.segment_id,
                revised_segment_id=revised_id,
                status=status,
                action_ids=action_ids,
                baseline_timeline_start=segment.timeline_start,
                baseline_timeline_end=segment.timeline_end,
                revised_timeline_start=revised_start,
                revised_timeline_end=revised_end,
                duration_delta_seconds=delta,
                detail=detail,
            )
        )
    return changes


def _continuity_note(item: _WorkingSegment) -> str:
    suffix = {
        "trimmed": "controlled trim candidate",
        "moved": "frontloaded candidate",
        "kept": "explicitly preserved candidate",
    }.get(item.status, "revision candidate")
    base = item.segment.continuity_note or ""
    return f"{base} {suffix}".strip()


def _action_result(
    action: RevisionAction,
    status: str,
    reason_code: str,
    detail: str,
    *,
    duration_delta: float = 0.0,
) -> RevisionAppliedAction:
    return RevisionAppliedAction(
        action_id=action.action_id,
        action_type=action.action_type,
        status=status,
        segment_id=action.segment_id,
        reason_code=reason_code,
        detail=detail,
        baseline_timeline_start=action.timeline_start,
        baseline_timeline_end=action.timeline_end,
        duration_delta_seconds=duration_delta,
        evidence_refs=action.evidence_refs,
    )


def _downstream_freshness(root: Path) -> list[DownstreamRevisionFreshness]:
    checks = [
        (
            root / "output" / "preview_lowres.mp4",
            "output/preview_lowres.mp4",
            "artist-portrait preview --project <project.yaml>",
        ),
        (
            root / WORKSPACE_DIR / DATA_DIR / "preview_validation.json",
            ".artist-portrait/data/preview_validation.json",
            "artist-portrait preview --project <project.yaml>",
        ),
        (
            root / "output" / "final_export.mp4",
            "output/final_export.mp4",
            "artist-portrait export --project <project.yaml> --profile review_720p",
        ),
        (
            root / WORKSPACE_DIR / DATA_DIR / "final_export_validation.json",
            ".artist-portrait/data/final_export_validation.json",
            "artist-portrait export --project <project.yaml> --profile review_720p",
        ),
        (
            root / WORKSPACE_DIR / DATA_DIR / "rhythm_media_qc.json",
            ".artist-portrait/data/rhythm_media_qc.json",
            "artist-portrait rhythm --project <project.yaml> --qc",
        ),
    ]
    result = []
    for path, ref, command in checks:
        present = path.exists()
        result.append(
            DownstreamRevisionFreshness(
                artifact_ref=ref,
                present=present,
                status_if_candidate_promoted="stale" if present else "missing",
                reason=(
                    "Artifact was generated from the baseline canonical timeline and must be regenerated after candidate promotion."
                    if present
                    else "Artifact is not present yet for this project."
                ),
                next_command=command,
            )
        )
    return result


def _fingerprint(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _fingerprint_many(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        if path.exists():
            digest.update(path.as_posix().encode("utf-8"))
            digest.update(path.read_bytes())
    return "sha256:" + digest.hexdigest()
