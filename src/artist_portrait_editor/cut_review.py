from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.cut_review import (
    CutReviewIssue,
    CutReviewReport,
    SecondPassAction,
)
from artist_portrait_editor.models.final_export import FinalExportValidationReport
from artist_portrait_editor.models.preview import PreviewValidationReport
from artist_portrait_editor.models.rhythm import EditGuidanceReport, RhythmMediaQcReport, RhythmPlan
from artist_portrait_editor.models.sound import SoundDecision
from artist_portrait_editor.models.state import ActiveMode, OverallStatus, StepLedgerEntry, StepStatus
from artist_portrait_editor.models.timeline import TimelineDraft
from artist_portrait_editor.run_records import environment_snapshot, new_run_id, write_json, utc_now
from artist_portrait_editor.workspace_errors import WorkspacePrerequisiteError
from artist_portrait_editor.workspace_state import (
    atomic_write_text,
    load_state,
    project_root,
    save_state,
    write_run_report,
)


class CutReviewError(RuntimeError):
    pass


T = TypeVar("T", bound=BaseModel)


def build_cut_review_workspace(project_path: Path) -> tuple[Path, Path, CutReviewReport, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("cut-review requires init to complete first")
    data_dir = root / WORKSPACE_DIR / DATA_DIR
    timeline_path = root / "output" / "timeline_draft.json"
    sound_path = data_dir / "sound_decision.json"
    if state.steps.get("timeline", StepLedgerEntry()).status not in {
        StepStatus.completed,
        StepStatus.completed_with_warnings,
    }:
        raise WorkspacePrerequisiteError("cut-review requires timeline to complete first")
    if not timeline_path.exists():
        raise WorkspacePrerequisiteError("cut-review requires output/timeline_draft.json")
    if not sound_path.exists():
        raise WorkspacePrerequisiteError("cut-review requires sound decision to complete first")

    rhythm_path = data_dir / "rhythm_plan.json"
    rhythm_qc_path = data_dir / "rhythm_media_qc.json"
    preview_validation_path = data_dir / "preview_validation.json"
    final_validation_path = data_dir / "final_export_validation.json"
    guidance_path = data_dir / "edit_guidance.json"

    report = build_cut_review(
        project_id=config.project.id,
        timeline=TimelineDraft.model_validate_json(timeline_path.read_text(encoding="utf-8")),
        timeline_ref=timeline_path.relative_to(root).as_posix(),
        timeline_fingerprint=_fingerprint(timeline_path),
        sound=_read_optional(sound_path, SoundDecision),
        sound_fingerprint=_fingerprint(sound_path),
        rhythm=_read_optional(rhythm_path, RhythmPlan),
        rhythm_fingerprint=_fingerprint(rhythm_path) if rhythm_path.exists() else None,
        rhythm_qc=_read_optional(rhythm_qc_path, RhythmMediaQcReport),
        rhythm_qc_fingerprint=_fingerprint(rhythm_qc_path) if rhythm_qc_path.exists() else None,
        preview_validation=_read_optional(preview_validation_path, PreviewValidationReport),
        preview_validation_ref=preview_validation_path.relative_to(root).as_posix()
        if preview_validation_path.exists()
        else None,
        preview_validation_fingerprint=_fingerprint(preview_validation_path)
        if preview_validation_path.exists()
        else None,
        final_validation=_read_optional(final_validation_path, FinalExportValidationReport),
        final_validation_ref=final_validation_path.relative_to(root).as_posix()
        if final_validation_path.exists()
        else None,
        final_validation_fingerprint=_fingerprint(final_validation_path)
        if final_validation_path.exists()
        else None,
        guidance=_read_optional(guidance_path, EditGuidanceReport),
        guidance_fingerprint=_fingerprint(guidance_path) if guidance_path.exists() else None,
    )

    json_path = data_dir / "cut_review.json"
    md_path = root / "output" / "cut_review.md"
    atomic_write_text(
        json_path,
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    atomic_write_text(md_path, render_cut_review(report))

    warnings = report.warnings
    run_id = new_run_id()
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    state.steps["cut_review"] = StepLedgerEntry(
        status=status,
        input_fingerprint=_fingerprint_many(
            [
                timeline_path,
                sound_path,
                rhythm_path,
                rhythm_qc_path,
                preview_validation_path,
                final_validation_path,
                guidance_path,
            ]
        ),
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
    write_json(runs_dir / "command.json", {"command": "cut-review", "project": str(project_path)})
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "cut_review",
            "status": status.value,
            "output_refs": [json_path.relative_to(root).as_posix(), md_path.relative_to(root).as_posix()],
            "warnings": warnings,
        },
    )
    save_state(root, state)
    write_run_report(root / config.paths.output_dir, state, warnings)
    return json_path, md_path, report, warnings


def build_cut_review(
    *,
    project_id: str,
    timeline: TimelineDraft,
    timeline_ref: str,
    timeline_fingerprint: str,
    sound: SoundDecision | None,
    sound_fingerprint: str | None,
    rhythm: RhythmPlan | None,
    rhythm_fingerprint: str | None,
    rhythm_qc: RhythmMediaQcReport | None,
    rhythm_qc_fingerprint: str | None,
    preview_validation: PreviewValidationReport | None,
    preview_validation_ref: str | None,
    preview_validation_fingerprint: str | None,
    final_validation: FinalExportValidationReport | None,
    final_validation_ref: str | None,
    final_validation_fingerprint: str | None,
    guidance: EditGuidanceReport | None,
    guidance_fingerprint: str | None,
) -> CutReviewReport:
    if timeline.project_id != project_id:
        raise CutReviewError("timeline project_id mismatches project config")
    if sound and sound.project_id != project_id:
        raise CutReviewError("sound decision project_id mismatches project config")

    warnings: list[str] = []
    if preview_validation is None and final_validation is None:
        warnings.append("no preview or final export validation was available; cut review is timeline-only")
    if rhythm is None:
        warnings.append("rhythm plan is missing; rhythm review uses conservative fallback")
    if rhythm_qc is None:
        warnings.append("rhythm media QC is missing; rendered rhythm fit cannot be confirmed")

    issues: list[CutReviewIssue] = []
    actions: list[SecondPassAction] = []

    ordered = sorted(timeline.segments, key=lambda item: item.timeline_start)
    first = ordered[0]
    last = ordered[-1]
    opening_status = "strong"
    if first.structural_role.value != "hook" or (first.clip_overall_score is not None and first.clip_overall_score < 0.55):
        opening_status = "weak"
        _add_issue_action(
            issues,
            actions,
            domain="opening",
            severity="warning",
            start=first.timeline_start,
            end=first.timeline_end,
            diagnosis="Opening segment is not a strong hook by current structure/score evidence.",
            action_type="tighten_opening",
            recommendation="Review the first segment and replace, shorten, or front-load stronger hook material.",
            expected_effect="Faster first-impression and clearer viewer commitment.",
            evidence=[first.segment_id, timeline_ref],
        )

    long_segments = [item for item in ordered if item.timeline_end - item.timeline_start > 12.0]
    dead_space_status = "clear"
    if long_segments:
        dead_space_status = "review"
        for item in long_segments[:3]:
            _add_issue_action(
                issues,
                actions,
                domain="dead_space",
                severity="warning",
                start=item.timeline_start,
                end=item.timeline_end,
                diagnosis="Segment is long enough to require dead-space review.",
                action_type="trim_dead_space",
                recommendation="Review the segment for pause, repetition, or low-information tail and tighten if needed.",
                expected_effect="Higher information density without changing the whole timeline strategy.",
                evidence=[item.segment_id, timeline_ref],
            )

    ending_status = "strong"
    if last.structural_role.value != "payoff":
        ending_status = "weak"
        _add_issue_action(
            issues,
            actions,
            domain="ending",
            severity="warning",
            start=last.timeline_start,
            end=last.timeline_end,
            diagnosis="Ending segment is not marked as payoff.",
            action_type="strengthen_ending",
            recommendation="Review the final segment and move a payoff or clearer closing moment to the end.",
            expected_effect="More intentional final impression and less abrupt close.",
            evidence=[last.segment_id, timeline_ref],
        )

    rhythm_status = "aligned"
    if rhythm is None or rhythm.status != "passed" or (rhythm_qc and rhythm_qc.status != "passed"):
        rhythm_status = "review" if rhythm or rhythm_qc else "unknown"
        _add_issue_action(
            issues,
            actions,
            domain="rhythm",
            severity="warning",
            start=None,
            end=None,
            diagnosis="Rhythm plan or rendered rhythm QC is missing or warning.",
            action_type="adjust_transition",
            recommendation="Review transitions, pauses, and cut-to-cue moments before accepting the cut aesthetically.",
            expected_effect="Better pacing continuity between the timeline and actual rendered media.",
            evidence=[ref for ref in [".artist-portrait/data/rhythm_plan.json", ".artist-portrait/data/rhythm_media_qc.json"] if ref],
        )

    audio_status = "clean"
    if sound is None or sound.status in {"warning", "blocked"} or sound.mixed_audio_warning_count:
        audio_status = "conflict" if sound and sound.mixed_audio_warning_count else "review"
        _add_issue_action(
            issues,
            actions,
            domain="audio",
            severity="warning",
            start=None,
            end=None,
            diagnosis="Sound decision requires audio review before the cut can be treated as aesthetically final.",
            action_type="rebalance_audio",
            recommendation="Review original audio, BGM source mode, ducking, fades, and mixed-audio contamination risk.",
            expected_effect="Cleaner relationship between speech/source audio and BGM.",
            evidence=[".artist-portrait/data/sound_decision.json"],
        )

    media_status = _media_status(preview_validation, final_validation)
    if media_status != "passed":
        _add_issue_action(
            issues,
            actions,
            domain="media_qc",
            severity="warning",
            start=None,
            end=None,
            diagnosis="Preview or final export validation is missing or not fully passed.",
            action_type="rerender_preview" if preview_validation is None else "rerender_final",
            recommendation="Render or refresh preview/final media before treating second-pass review as complete.",
            expected_effect="Review evidence binds to current rendered media instead of a stale or missing output.",
            evidence=[
                ref
                for ref in [
                    preview_validation_ref or ".artist-portrait/data/preview_validation.json",
                    final_validation_ref or ".artist-portrait/data/final_export_validation.json",
                ]
            ],
        )

    status = "passed" if not issues else "warning"
    if preview_validation is None and final_validation is None:
        status = "warning"
    high_issues = sum(1 for issue in issues if issue.severity == "error")
    high_actions = sum(1 for action in actions if action.priority == "high")
    reviewed_media_scope = "final_export" if final_validation else "preview" if preview_validation else "timeline_only"
    assessment = (
        "Cut has no deterministic aesthetic warnings from current evidence."
        if not issues
        else "Cut needs a second-pass editorial review before it should be treated as mature."
    )
    key = ":".join(
        [
            project_id,
            timeline.timeline_id,
            timeline_fingerprint,
            sound_fingerprint or "no-sound",
            rhythm_fingerprint or "no-rhythm",
            preview_validation_fingerprint or "no-preview",
            final_validation_fingerprint or "no-final",
            str(len(issues)),
            str(len(actions)),
        ]
    )
    return CutReviewReport(
        cut_review_id="cut_review_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:20],
        project_id=project_id,
        timeline_id=timeline.timeline_id,
        timeline_ref=timeline_ref,
        timeline_fingerprint=timeline_fingerprint,
        sound_decision_id=sound.sound_decision_id if sound else None,
        sound_decision_fingerprint=sound_fingerprint,
        rhythm_plan_id=rhythm.rhythm_plan_id if rhythm else None,
        rhythm_plan_fingerprint=rhythm_fingerprint,
        rhythm_media_qc_id=rhythm_qc.rhythm_qc_id if rhythm_qc else None,
        rhythm_media_qc_fingerprint=rhythm_qc_fingerprint,
        preview_validation_ref=preview_validation_ref,
        preview_validation_fingerprint=preview_validation_fingerprint,
        final_export_validation_ref=final_validation_ref,
        final_export_validation_fingerprint=final_validation_fingerprint,
        edit_guidance_id=guidance.edit_guidance_id if guidance else None,
        edit_guidance_fingerprint=guidance_fingerprint,
        reviewed_media_scope=reviewed_media_scope,
        status=status,
        overall_assessment=assessment,
        opening_status=opening_status,
        dead_space_status=dead_space_status,
        ending_status=ending_status,
        rhythm_status=rhythm_status,
        audio_status=audio_status,
        issue_count=len(issues),
        high_priority_issue_count=high_issues,
        second_pass_action_count=len(actions),
        high_priority_action_count=high_actions,
        first_second_pass_action=actions[0].recommendation if actions else None,
        issues=issues,
        second_pass_actions=actions,
        warnings=warnings,
    )


def render_cut_review(report: CutReviewReport) -> str:
    lines = [
        "# Cut Review",
        "",
        "This deterministic review checks the current cut evidence and proposes a manual second pass. It does not render media, mutate timelines, move edit points, select music, call models, access the network, or use image generation.",
        "",
        f"- Status: `{report.status}`",
        f"- Media scope: `{report.reviewed_media_scope}`",
        f"- Overall assessment: {report.overall_assessment}",
        f"- Issues: `{report.issue_count}`",
        f"- Second-pass actions: `{report.second_pass_action_count}`",
        "",
        "## Domain Status",
        "",
        f"- Opening: `{report.opening_status}`",
        f"- Dead space: `{report.dead_space_status}`",
        f"- Ending: `{report.ending_status}`",
        f"- Rhythm: `{report.rhythm_status}`",
        f"- Audio: `{report.audio_status}`",
        "",
        "## Issues",
        "",
    ]
    if not report.issues:
        lines.append("- None")
    for issue in report.issues:
        where = _range_label(issue.timeline_start, issue.timeline_end)
        lines.append(f"- `{issue.domain}` `{issue.severity}` {where}: {issue.diagnosis}")
    lines.extend(["", "## Second-Pass Actions", ""])
    if not report.second_pass_actions:
        lines.append("- None")
    for action in report.second_pass_actions:
        where = _range_label(action.timeline_start, action.timeline_end)
        lines.append(f"- `{action.action_type}` `{action.priority}` {where}: {action.recommendation}")
        lines.append(f"  Rationale: {action.rationale}")
    if report.warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in report.warnings:
            lines.append(f"- {warning}")
    lines.append("")
    return "\n".join(lines)


def _add_issue_action(
    issues: list[CutReviewIssue],
    actions: list[SecondPassAction],
    *,
    domain: str,
    severity: str,
    start: float | None,
    end: float | None,
    diagnosis: str,
    action_type: str,
    recommendation: str,
    expected_effect: str,
    evidence: list[str],
) -> None:
    action_id = f"second_pass_{len(actions) + 1:02d}"
    issues.append(
        CutReviewIssue(
            issue_id=f"cut_issue_{len(issues) + 1:02d}",
            domain=domain,
            severity=severity,
            timeline_start=start,
            timeline_end=end,
            diagnosis=diagnosis,
            evidence_refs=evidence,
            second_pass_action_id=action_id,
        )
    )
    actions.append(
        SecondPassAction(
            action_id=action_id,
            order=len(actions) + 1,
            action_type=action_type,
            priority="high" if severity == "error" else "medium",
            timeline_start=start,
            timeline_end=end,
            recommendation=recommendation,
            rationale=diagnosis,
            expected_effect=expected_effect,
            evidence_refs=evidence,
            command_hint="artist-portrait timeline --project <project.yaml> --proposal <id>",
        )
    )


def _media_status(
    preview_validation: PreviewValidationReport | None,
    final_validation: FinalExportValidationReport | None,
) -> str:
    if final_validation is not None:
        return final_validation.quality_status
    if preview_validation is not None:
        return "passed" if preview_validation.valid else "warning"
    return "missing"


def _range_label(start: float | None, end: float | None) -> str:
    if start is None or end is None:
        return "`global`"
    return f"`{start:.2f}-{end:.2f}s`"


def _read_optional(path: Path, model: type[T]) -> T | None:
    if not path.exists():
        return None
    return model.model_validate_json(path.read_text(encoding="utf-8"))


def _fingerprint(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _fingerprint_many(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.as_posix().encode("utf-8"))
        if path.exists():
            digest.update(path.read_bytes())
        else:
            digest.update(b"<missing>")
    return "sha256:" + digest.hexdigest()
