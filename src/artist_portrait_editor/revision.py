from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.cut_review import CutReviewReport
from artist_portrait_editor.models.final_export import FinalExportValidationReport
from artist_portrait_editor.models.preview import PreviewValidationReport
from artist_portrait_editor.models.revision import (
    RevisionAction,
    RevisionComparison,
    RevisionIntent,
    RevisionPlan,
    RevisionSemanticClause,
    RevisionSemanticConflict,
    RevisionVersionCandidate,
)
from artist_portrait_editor.models.rhythm import RhythmPlan
from artist_portrait_editor.models.sound import SoundDecision
from artist_portrait_editor.models.state import ActiveMode, OverallStatus, StepLedgerEntry, StepStatus
from artist_portrait_editor.models.timeline import TimelineDraft, TimelineSegment
from artist_portrait_editor.run_records import environment_snapshot, new_run_id, write_json, utc_now
from artist_portrait_editor.workspace_errors import WorkspacePrerequisiteError
from artist_portrait_editor.workspace_state import (
    atomic_write_text,
    load_state,
    project_root,
    save_state,
    write_run_report,
)


class RevisionPlanError(RuntimeError):
    pass


T = TypeVar("T", bound=BaseModel)


def build_revision_plan_workspace(
    project_path: Path,
    *,
    request_text: str,
    request_type: str | None,
    target_duration_seconds: float | None,
    keep_segment_ids: list[str],
    remove_segment_ids: list[str],
) -> tuple[Path, Path, RevisionPlan, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("revise requires init to complete first")
    data_dir = root / WORKSPACE_DIR / DATA_DIR
    timeline_path = root / "output" / "timeline_draft.json"
    cut_review_path = data_dir / "cut_review.json"
    if state.steps.get("timeline", StepLedgerEntry()).status not in {
        StepStatus.completed,
        StepStatus.completed_with_warnings,
    }:
        raise WorkspacePrerequisiteError("revise requires timeline to complete first")
    if not timeline_path.exists():
        raise WorkspacePrerequisiteError("revise requires output/timeline_draft.json")
    if not cut_review_path.exists():
        raise WorkspacePrerequisiteError("revise requires cut-review to complete first")

    sound_path = data_dir / "sound_decision.json"
    rhythm_path = data_dir / "rhythm_plan.json"
    preview_validation_path = data_dir / "preview_validation.json"
    final_validation_path = data_dir / "final_export_validation.json"

    plan = build_revision_plan(
        project_id=config.project.id,
        request_text=request_text,
        request_type=request_type,
        target_duration_seconds=target_duration_seconds,
        keep_segment_ids=keep_segment_ids,
        remove_segment_ids=remove_segment_ids,
        timeline=TimelineDraft.model_validate_json(timeline_path.read_text(encoding="utf-8")),
        timeline_ref=timeline_path.relative_to(root).as_posix(),
        timeline_fingerprint=_fingerprint(timeline_path),
        cut_review=CutReviewReport.model_validate_json(cut_review_path.read_text(encoding="utf-8")),
        cut_review_ref=cut_review_path.relative_to(root).as_posix(),
        cut_review_fingerprint=_fingerprint(cut_review_path),
        sound=_read_optional(sound_path, SoundDecision),
        sound_fingerprint=_fingerprint(sound_path) if sound_path.exists() else None,
        rhythm=_read_optional(rhythm_path, RhythmPlan),
        rhythm_fingerprint=_fingerprint(rhythm_path) if rhythm_path.exists() else None,
        preview_validation_ref=preview_validation_path.relative_to(root).as_posix()
        if preview_validation_path.exists()
        else None,
        preview_validation_fingerprint=_fingerprint(preview_validation_path)
        if preview_validation_path.exists()
        else None,
        final_validation_ref=final_validation_path.relative_to(root).as_posix()
        if final_validation_path.exists()
        else None,
        final_validation_fingerprint=_fingerprint(final_validation_path)
        if final_validation_path.exists()
        else None,
    )

    json_path = data_dir / "revision_plan.json"
    md_path = root / "output" / "revision_plan.md"
    atomic_write_text(
        json_path,
        json.dumps(plan.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    atomic_write_text(md_path, render_revision_plan(plan))

    warnings = plan.warnings
    run_id = new_run_id()
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    state.steps["revision"] = StepLedgerEntry(
        status=status,
        input_fingerprint=_fingerprint_many(
            [timeline_path, cut_review_path, sound_path, rhythm_path, preview_validation_path, final_validation_path]
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
    write_json(
        runs_dir / "command.json",
        {
            "command": "revise",
            "project": str(project_path),
            "intent": request_text,
            "request_type": request_type,
        },
    )
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "revision",
            "status": status.value,
            "output_refs": [json_path.relative_to(root).as_posix(), md_path.relative_to(root).as_posix()],
            "warnings": warnings,
        },
    )
    save_state(root, state)
    write_run_report(root / config.paths.output_dir, state, warnings)
    return json_path, md_path, plan, warnings


def build_revision_plan(
    *,
    project_id: str,
    request_text: str,
    request_type: str | None,
    target_duration_seconds: float | None,
    keep_segment_ids: list[str],
    remove_segment_ids: list[str],
    timeline: TimelineDraft,
    timeline_ref: str,
    timeline_fingerprint: str,
    cut_review: CutReviewReport,
    cut_review_ref: str,
    cut_review_fingerprint: str,
    sound: SoundDecision | None,
    sound_fingerprint: str | None,
    rhythm: RhythmPlan | None,
    rhythm_fingerprint: str | None,
    preview_validation_ref: str | None,
    preview_validation_fingerprint: str | None,
    final_validation_ref: str | None,
    final_validation_fingerprint: str | None,
) -> RevisionPlan:
    if timeline.project_id != project_id:
        raise RevisionPlanError("timeline project_id mismatches project config")
    if cut_review.project_id != project_id:
        raise RevisionPlanError("cut review project_id mismatches project config")
    if cut_review.timeline_id != timeline.timeline_id:
        raise RevisionPlanError("cut review does not bind to the current timeline")
    if sound and sound.project_id != project_id:
        raise RevisionPlanError("sound decision project_id mismatches project config")

    ordered = sorted(timeline.segments, key=lambda item: item.timeline_start)
    classified, reasons = _classify_request(request_text, request_type)
    semantic_clauses = _parse_revision_semantics(request_text, classified, request_type is not None)
    semantic_conflicts = _find_semantic_conflicts(semantic_clauses)
    intent = RevisionIntent(
        intent_id=_id("intent", request_text, classified, ",".join(keep_segment_ids), ",".join(remove_segment_ids)),
        request_text=request_text,
        request_type=classified,
        target_duration_seconds=target_duration_seconds,
        keep_segment_ids=keep_segment_ids,
        remove_segment_ids=remove_segment_ids,
        classification_reasons=reasons,
    )
    warnings: list[str] = []
    if preview_validation_ref is None and final_validation_ref is None:
        warnings.append("revision comparison has no rendered media validation; version comparison is plan-only")
    if not keep_segment_ids and classified == "keep_segment":
        warnings.append("keep_segment request has no explicit --keep-segment ids; planner falls back to manual review")
    if not remove_segment_ids and classified == "remove_segment":
        warnings.append("remove_segment request has no explicit --remove-segment ids; planner falls back to manual review")
    if sound is None and classified == "reduce_bgm":
        warnings.append("reduce_bgm request has no sound decision evidence; action remains manual")

    actions = _build_actions(
        intent=intent,
        timeline=timeline,
        ordered=ordered,
        cut_review=cut_review,
        timeline_ref=timeline_ref,
        cut_review_ref=cut_review_ref,
    )
    _append_semantic_actions(actions, semantic_clauses, ordered, timeline_ref, cut_review_ref)
    candidates = _build_candidates(intent, timeline, actions)
    comparison = RevisionComparison(
        baseline_version_id="current_version",
        recommended_version_id="revision_candidate_1",
        summary=_comparison_summary(intent.request_type),
        improvement_axes=_improvement_axes(intent.request_type),
        risk_axes=_risk_axes(intent.request_type),
    )
    status = "warning" if warnings else "ready"
    key = "|".join(
        [
            project_id,
            timeline.timeline_id,
            cut_review.cut_review_id,
            intent.intent_id,
            timeline_fingerprint,
            cut_review_fingerprint,
        ]
    )
    return RevisionPlan(
        revision_plan_id="revision_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:20],
        project_id=project_id,
        status=status,
        timeline_id=timeline.timeline_id,
        timeline_ref=timeline_ref,
        timeline_fingerprint=timeline_fingerprint,
        cut_review_id=cut_review.cut_review_id,
        cut_review_ref=cut_review_ref,
        cut_review_fingerprint=cut_review_fingerprint,
        sound_decision_id=sound.sound_decision_id if sound else None,
        sound_decision_fingerprint=sound_fingerprint,
        rhythm_plan_id=rhythm.rhythm_plan_id if rhythm else None,
        rhythm_plan_fingerprint=rhythm_fingerprint,
        preview_validation_ref=preview_validation_ref,
        preview_validation_fingerprint=preview_validation_fingerprint,
        final_export_validation_ref=final_validation_ref,
        final_export_validation_fingerprint=final_validation_fingerprint,
        intent=intent,
        semantic_clauses=semantic_clauses,
        semantic_conflicts=semantic_conflicts,
        covered_domains=sorted({clause.domain for clause in semantic_clauses}),
        current_duration_seconds=timeline.actual_duration,
        target_duration_seconds=target_duration_seconds,
        action_count=len(actions),
        candidate_count=len(candidates),
        first_action_id=actions[0].action_id if actions else None,
        recommended_version_id="revision_candidate_1",
        actions=actions,
        version_candidates=candidates,
        comparison=comparison,
        warnings=warnings,
    )


def render_revision_plan(plan: RevisionPlan) -> str:
    lines = [
        "# Revision Plan",
        "",
        f"- Status: `{plan.status}`",
        f"- Request type: `{plan.intent.request_type}`",
        f"- User note: {plan.intent.request_text}",
        f"- Timeline: `{plan.timeline_ref}`",
        f"- Cut review: `{plan.cut_review_ref}`",
        f"- Current duration: `{plan.current_duration_seconds:.2f}s`",
        f"- Recommended version: `{plan.recommended_version_id}`",
        "",
        "## Version Comparison",
        "",
        f"{plan.comparison.summary}",
        "",
    ]
    lines.extend(["## Interpreted Revision Semantics", ""])
    for clause in plan.semantic_clauses:
        lines.extend(
            [
                f"### {clause.priority}. {clause.domain} / {clause.operation}",
                "",
                f"- Scope: `{clause.scope}`",
                f"- Intensity: `{clause.intensity}`",
                f"- Confidence: `{clause.confidence:.2f}`",
                f"- Coupled domains: `{', '.join(clause.coupled_domains) or 'none'}`",
                f"- Application status: `{clause.application_status}`",
                "- Acceptance observations:",
                *[f"  - {item}" for item in clause.acceptance_observations],
                "",
            ]
        )
    if plan.semantic_conflicts:
        lines.extend(["## Semantic Conflicts", ""])
        for conflict in plan.semantic_conflicts:
            lines.append(f"- `{conflict.status}`: {conflict.description} Resolution: {conflict.resolution}")
        lines.append("")
    for candidate in plan.version_candidates:
        lines.extend(
            [
                f"### {candidate.label}",
                "",
                f"- Version ID: `{candidate.version_id}`",
                f"- Estimated duration: `{candidate.estimated_duration_seconds:.2f}s`",
                f"- Duration delta: `{candidate.duration_delta_seconds:.2f}s`",
                f"- Risk: `{candidate.risk_level}`",
                f"- Satisfies intent: `{candidate.satisfies_intent}`",
                f"- Edits applied: `{candidate.edits_applied}`",
                f"- Strategy: {candidate.strategy}",
                "",
            ]
        )
        if candidate.expected_improvements:
            lines.append("Improvements:")
            lines.extend(f"- {item}" for item in candidate.expected_improvements)
            lines.append("")
        if candidate.tradeoffs:
            lines.append("Tradeoffs:")
            lines.extend(f"- {item}" for item in candidate.tradeoffs)
            lines.append("")
    lines.extend(["## Manual Revision Actions", ""])
    for action in plan.actions:
        lines.extend(
            [
                f"### {action.order}. {action.action_type}",
                "",
                f"- Action ID: `{action.action_id}`",
                f"- Segment: `{action.segment_id or 'manual'}`",
                f"- Recommendation: {action.recommendation}",
                f"- Rationale: {action.rationale}",
                f"- Expected effect: {action.expected_effect}",
                f"- Affected domains: `{', '.join(action.affected_domains) or 'unspecified'}`",
                f"- Application status: `{action.application_status}`",
                f"- Edits applied: `{action.edits_applied}`",
                "",
            ]
        )
    if plan.warnings:
        lines.extend(["## Warnings", ""])
        lines.extend(f"- {warning}" for warning in plan.warnings)
        lines.append("")
    lines.extend(
        [
            "## Guardrails",
            "",
            "- Media rendered: `false`",
            "- Canonical timeline mutated: `false`",
            "- Edit points moved automatically: `false`",
            "- Automatic music selection: `false`",
            "- Model call by CLI: `false`",
            "- Network access: `false`",
            "",
        ]
    )
    return "\n".join(lines)


def _build_actions(
    *,
    intent: RevisionIntent,
    timeline: TimelineDraft,
    ordered: list[TimelineSegment],
    cut_review: CutReviewReport,
    timeline_ref: str,
    cut_review_ref: str,
) -> list[RevisionAction]:
    actions: list[RevisionAction] = []
    if intent.request_type == "shorter":
        for segment in _longest_segments(ordered, limit=2):
            _append_action(
                actions,
                "trim",
                segment,
                "Trim the segment by reviewing low-information lead-in or tail.",
                "The user asked for a shorter version.",
                "Shorter runtime with limited structural disruption.",
                [segment.segment_id, timeline_ref],
            )
    elif intent.request_type == "longer":
        _append_action(
            actions,
            "extend",
            ordered[-1],
            "Review dropped/context material and extend the build or payoff if evidence supports it.",
            "The user asked for a longer version.",
            "More context without replacing the current structure.",
            [ordered[-1].segment_id, timeline_ref],
        )
    elif intent.request_type == "stronger_hook":
        _append_action(
            actions,
            "frontload_hook",
            ordered[0],
            "Replace or tighten the opening with the highest-impact hook candidate.",
            "The user asked for a stronger opening.",
            "Faster first-impression and clearer emotional premise.",
            [ordered[0].segment_id, timeline_ref, cut_review_ref],
        )
    elif intent.request_type == "more_emotional":
        target = max(ordered, key=lambda item: item.clip_overall_score or 0.0)
        _append_action(
            actions,
            "strengthen_emotion",
            target,
            "Preserve the strongest-scored moment and give it more breathing room in the revised version.",
            "The user asked for a more emotional version.",
            "Clearer emotional center with less mechanical pacing.",
            [target.segment_id, timeline_ref],
        )
    elif intent.request_type == "change_ending":
        _append_action(
            actions,
            "replace_ending",
            ordered[-1],
            "Review payoff alternatives and replace or tighten the final segment.",
            "The user asked to change the ending.",
            "More deliberate closing impression.",
            [ordered[-1].segment_id, timeline_ref, cut_review_ref],
        )
    elif intent.request_type == "reduce_subtitles":
        _append_action(
            actions,
            "reduce_subtitles",
            None,
            "Mark subtitle density for manual reduction in the revised version.",
            "The user asked for fewer subtitles.",
            "Cleaner visual field and less text fatigue.",
            [timeline_ref],
        )
    elif intent.request_type == "reduce_bgm":
        _append_action(
            actions,
            "rebalance_bgm",
            None,
            "Lower BGM prominence or preserve more original audio in the revised version.",
            "The user asked for less BGM.",
            "More natural source-audio emphasis.",
            [timeline_ref],
        )
    for segment_id in intent.keep_segment_ids:
        segment = _find_segment(ordered, segment_id)
        _append_action(
            actions,
            "keep",
            segment,
            "Preserve this segment in all revised versions.",
            "The user explicitly marked the segment to keep.",
            "User constraint remains visible in version comparison.",
            [ref for ref in [segment_id, timeline_ref] if ref],
        )
    for segment_id in intent.remove_segment_ids:
        segment = _find_segment(ordered, segment_id)
        _append_action(
            actions,
            "remove",
            segment,
            "Remove or replace this segment in the revised version.",
            "The user explicitly marked the segment to remove.",
            "User constraint remains visible in version comparison.",
            [ref for ref in [segment_id, timeline_ref] if ref],
        )
    for second_pass in cut_review.second_pass_actions[:2]:
        _append_action(
            actions,
            "manual_review",
            None,
            second_pass.recommendation,
            "Carried forward from the latest cut review.",
            second_pass.expected_effect,
            [cut_review_ref, second_pass.action_id],
            required=False,
        )
    if not actions:
        _append_action(
            actions,
            "manual_review",
            None,
            "Review the current cut against the user note and choose a manual revision direction.",
            "The request is custom and cannot be reduced to a deterministic edit operation.",
            "Keeps the revision loop explicit without fabricating applied edits.",
            [timeline_ref, cut_review_ref],
        )
    return actions


def _build_candidates(
    intent: RevisionIntent,
    timeline: TimelineDraft,
    actions: list[RevisionAction],
) -> list[RevisionVersionCandidate]:
    current_duration = timeline.actual_duration
    revised_duration = _estimate_duration(intent, current_duration, timeline.target_duration)
    return [
        RevisionVersionCandidate(
            version_id="current_version",
            label="Current version",
            strategy="Keep the current canonical timeline unchanged.",
            estimated_duration_seconds=current_duration,
            duration_delta_seconds=0.0,
            expected_improvements=["No additional editing risk."],
            tradeoffs=["Does not answer the new user revision note."],
            risk_level="low",
            satisfies_intent=False,
            current_version=True,
        ),
        RevisionVersionCandidate(
            version_id="revision_candidate_1",
            label="Revision candidate 1",
            strategy=_candidate_strategy(intent.request_type),
            estimated_duration_seconds=revised_duration,
            duration_delta_seconds=revised_duration - current_duration,
            action_ids=[action.action_id for action in actions if action.required_for_intent],
            expected_improvements=_improvement_axes(intent.request_type),
            tradeoffs=_risk_axes(intent.request_type),
            risk_level="medium" if actions else "high",
            satisfies_intent=True,
        ),
    ]


def _classify_request(request_text: str, request_type: str | None) -> tuple[str, list[str]]:
    if request_type:
        return request_type, [f"explicit request type: {request_type}"]
    lowered = request_text.lower()
    checks = [
        ("shorter", ("shorter", "short", "trim", "短", "缩短")),
        ("longer", ("longer", "extend", "more context", "长", "更完整")),
        ("stronger_hook", ("hook", "opening", "开头", "开场", "冲击")),
        ("more_emotional", ("emotional", "emotion", "moving", "情绪", "感动")),
        ("keep_segment", ("keep", "preserve", "保留")),
        ("remove_segment", ("remove", "delete", "drop", "删除", "去掉")),
        ("change_ending", ("ending", "end", "结尾", "收尾")),
        ("reduce_subtitles", ("subtitle", "caption", "字幕")),
        ("reduce_bgm", ("bgm", "music", "音乐", "配乐")),
    ]
    for value, tokens in checks:
        if any(token in lowered for token in tokens):
            return value, [f"matched keyword for {value}"]
    return "custom", ["no deterministic keyword match; classified as custom"]


_SEMANTIC_RULES = (
    ("duration", "shorten", ("shorter", "trim", "缩短", "短一点"), "whole_cut", ("structure", "rhythm"), "Playback duration is lower without removing protected material."),
    ("duration", "lengthen", ("longer", "extend", "长一点", "更完整"), "whole_cut", ("structure", "rhythm"), "Playback adds useful context without obvious dead space."),
    ("structure", "strengthen_hook", ("stronger hook", "hook", "开头更强", "开场", "抓人"), "opening", ("rhythm", "source_audio", "text"), "The first meaningful beat arrives earlier and states the premise more clearly."),
    ("rhythm", "accelerate", ("faster", "快点", "快一点", "节奏快", "更紧凑"), "whole_cut", ("duration", "text", "transition", "bgm"), "Dead time decreases while dialogue, performance, and emotional buildup remain intelligible."),
    ("rhythm", "slow_or_breathe", ("slower", "慢一点", "留白", "呼吸感"), "whole_cut", ("emotion", "source_audio", "bgm"), "Key moments gain breathing room without turning into accidental dead space."),
    ("emotion", "strengthen", ("more emotional", "emotion", "更有情绪", "感动", "情绪更强"), "whole_cut", ("rhythm", "bgm", "source_audio", "ending"), "The emotional turn is clearer in playback and remains supported by real evidence."),
    ("style", "refine_premium", ("高级", "premium", "更克制", "质感"), "whole_cut", ("rhythm", "text", "transition", "composition", "bgm"), "Playback shows fewer decorative interventions, cleaner hierarchy, and deliberate restraint."),
    ("text", "reduce_density", ("少点字", "少一点字", "减少字幕", "字幕少", "less text", "fewer subtitles"), "whole_cut", ("rhythm", "composition", "source_audio"), "Text occupancy and simultaneous reading pressure decrease without losing required meaning."),
    ("source_audio", "protect_voice", ("别压人声", "不要压人声", "人声清楚", "voice clearer", "protect voice"), "whole_cut", ("bgm", "text", "rhythm"), "Dialogue remains intelligible at every BGM overlap and ducking is audible but not pumping."),
    ("bgm", "reduce_prominence", ("reduce bgm", "less music", "音乐小", "配乐小", "bgm小"), "whole_cut", ("source_audio", "rhythm", "emotion"), "BGM supports rather than masks voice, ambience, or intended silence."),
    ("ending", "strengthen", ("结尾更有力量", "ending stronger", "stronger ending", "收尾更强", "结尾"), "ending", ("emotion", "rhythm", "bgm", "text"), "The final image/sound decision resolves or deliberately suspends the chosen arc."),
    ("transition", "restrain", ("少点转场", "转场克制", "fewer transitions"), "whole_cut", ("rhythm", "style", "composition"), "Transitions stop drawing attention away from the subject and remain motivated."),
)


def _parse_revision_semantics(request_text: str, primary: str, explicit: bool) -> list[RevisionSemanticClause]:
    lowered = request_text.lower()
    clauses: list[RevisionSemanticClause] = []
    for domain, operation, tokens, scope, coupled, observation in _SEMANTIC_RULES:
        matched = [token for token in tokens if token in lowered]
        if not matched:
            continue
        intensity = "strong" if any(token in lowered for token in ("极度", "非常", "更强", "stronger")) else "moderate"
        clauses.append(
            RevisionSemanticClause(
                clause_id=f"semantic_{len(clauses) + 1:03d}",
                domain=domain,
                operation=operation,
                intensity=intensity,
                scope=scope,
                priority=len(clauses) + 1,
                matched_text=matched,
                evidence_requirements=["current timeline binding", "latest cut-review evidence", "playback comparison before promotion"],
                coupled_domains=list(coupled),
                acceptance_observations=[observation],
                confidence=1.0 if explicit else 0.85,
            )
        )
    if not clauses:
        clauses.append(
            RevisionSemanticClause(
                clause_id="semantic_001", domain="custom", operation=primary,
                intensity="unspecified", scope="whole_cut", priority=1,
                matched_text=[request_text],
                evidence_requirements=["host or user interpretation", "playback comparison before promotion"],
                acceptance_observations=["The user confirms that the revised playback answers the original note."],
                confidence=0.25,
            )
        )
    return clauses


def _find_semantic_conflicts(clauses: list[RevisionSemanticClause]) -> list[RevisionSemanticConflict]:
    conflicts: list[RevisionSemanticConflict] = []
    by_operation = {item.operation: item for item in clauses}
    for left, right, description in (
        ("shorten", "lengthen", "The request asks for both a shorter and a longer cut."),
        ("accelerate", "slow_or_breathe", "The request asks for both faster pacing and more breathing room."),
    ):
        if left in by_operation and right in by_operation:
            conflicts.append(
                RevisionSemanticConflict(
                    conflict_id=f"semantic_conflict_{len(conflicts) + 1:03d}",
                    clause_ids=[by_operation[left].clause_id, by_operation[right].clause_id],
                    description=description,
                    resolution="Scope the opposing requests to different sections or ask the user to prioritize one.",
                    status="warning",
                )
            )
    return conflicts


def _append_semantic_actions(
    actions: list[RevisionAction], clauses: list[RevisionSemanticClause], ordered: list[TimelineSegment],
    timeline_ref: str, cut_review_ref: str,
) -> None:
    existing = {action.action_type for action in actions}
    mapping = {
        "accelerate": ("accelerate_pacing", ordered[0], "Tighten pauses and low-value edges section by section; do not speed through intelligible speech."),
        "refine_premium": ("refine_style", None, "Reduce decorative text/transitions and review spacing, composition, sound restraint, and shot holds together."),
        "reduce_density": ("reduce_subtitles", None, "Remove redundant on-screen text and preserve only evidence-backed, necessary reading beats."),
        "protect_voice": ("protect_voice", None, "Audit every voice/music overlap and define local ducking or source-audio priority before rendering."),
        "reduce_prominence": ("rebalance_bgm", None, "Lower BGM prominence while preserving phrase continuity and intended emotional support."),
        "strengthen_hook": ("frontload_hook", ordered[0], "Tighten or replace the opening using current hook evidence without inventing a premise."),
        "strengthen": ("strengthen_emotion", max(ordered, key=lambda item: item.clip_overall_score or 0.0), "Build more space and audiovisual support around the strongest evidenced emotional candidate."),
        "restrain": ("adjust_transition", None, "Replace unmotivated transitions with direct cuts, holds, or evidenced continuity."),
    }
    for clause in clauses:
        if clause.domain == "ending" and clause.operation == "strengthen":
            spec = ("replace_ending", ordered[-1], "Strengthen the final image/sound relation and verify the chosen emotional arc in playback.")
        else:
            spec = mapping.get(clause.operation)
        if not spec or spec[0] in existing:
            continue
        action_type, segment, recommendation = spec
        _append_action(
            actions, action_type, segment, recommendation,
            f"Interpreted from semantic clause {clause.clause_id}: {clause.domain}/{clause.operation}.",
            clause.acceptance_observations[0], [timeline_ref, cut_review_ref, clause.clause_id],
            affected_domains=[clause.domain, *clause.coupled_domains],
            acceptance=clause.acceptance_observations,
        )
        existing.add(action_type)


def _estimate_duration(intent: RevisionIntent, current: float, target: float) -> float:
    if intent.target_duration_seconds:
        return intent.target_duration_seconds
    if intent.request_type == "shorter":
        return max(0.5, current * 0.85)
    if intent.request_type == "longer":
        return max(current, min(target, current * 1.12))
    return current


def _candidate_strategy(request_type: str) -> str:
    mapping = {
        "shorter": "Create a tighter cut by trimming low-density segment edges.",
        "longer": "Create a fuller cut by extending context or payoff material.",
        "stronger_hook": "Create a stronger first beat by front-loading hook material.",
        "more_emotional": "Create a more emotional cut by preserving the strongest moment and slowing around it.",
        "keep_segment": "Create a constrained cut that preserves user-selected segments.",
        "remove_segment": "Create a constrained cut that removes or replaces user-selected segments.",
        "change_ending": "Create a revised ending with a clearer payoff.",
        "reduce_subtitles": "Create a cleaner text-light version.",
        "reduce_bgm": "Create a source-audio-forward version with lower BGM prominence.",
        "custom": "Create a manual revision candidate from the user note.",
    }
    return mapping[request_type]


def _comparison_summary(request_type: str) -> str:
    return (
        f"The current version remains the baseline; revision_candidate_1 is the "
        f"manual plan most directly aligned with `{request_type}`."
    )


def _improvement_axes(request_type: str) -> list[str]:
    mapping = {
        "shorter": ["runtime efficiency", "higher information density"],
        "longer": ["more context", "slower development"],
        "stronger_hook": ["stronger opening", "clearer first impression"],
        "more_emotional": ["stronger emotional focus", "more breathing room"],
        "keep_segment": ["explicit user preservation constraint"],
        "remove_segment": ["explicit user removal constraint"],
        "change_ending": ["stronger closing impression"],
        "reduce_subtitles": ["less visual text clutter"],
        "reduce_bgm": ["more source-audio clarity"],
        "custom": ["manual creative alignment"],
    }
    return mapping[request_type]


def _risk_axes(request_type: str) -> list[str]:
    mapping = {
        "shorter": ["may lose context or emotional buildup"],
        "longer": ["may weaken pacing"],
        "stronger_hook": ["may over-frontload the story"],
        "more_emotional": ["may reduce pace or informational density"],
        "keep_segment": ["may constrain rhythm or duration"],
        "remove_segment": ["may damage continuity if replacement material is weak"],
        "change_ending": ["may require new payoff material"],
        "reduce_subtitles": ["may reduce clarity for silent viewing"],
        "reduce_bgm": ["may reduce energy if source audio is weak"],
        "custom": ["requires manual interpretation"],
    }
    return mapping[request_type]


def _append_action(
    actions: list[RevisionAction],
    action_type: str,
    segment: TimelineSegment | None,
    recommendation: str,
    rationale: str,
    expected_effect: str,
    evidence: list[str],
    *,
    required: bool = True,
    affected_domains: list[str] | None = None,
    acceptance: list[str] | None = None,
) -> None:
    order = len(actions) + 1
    actions.append(
        RevisionAction(
            action_id=f"revision_action_{order:03d}",
            order=order,
            action_type=action_type,
            segment_id=segment.segment_id if segment else None,
            timeline_start=segment.timeline_start if segment else None,
            timeline_end=segment.timeline_end if segment else None,
            recommendation=recommendation,
            rationale=rationale,
            expected_effect=expected_effect,
            affected_domains=affected_domains or [],
            acceptance_observations=acceptance or [expected_effect],
            evidence_refs=evidence,
            required_for_intent=required,
        )
    )


def _longest_segments(segments: list[TimelineSegment], *, limit: int) -> list[TimelineSegment]:
    return sorted(
        segments,
        key=lambda item: item.timeline_end - item.timeline_start,
        reverse=True,
    )[:limit]


def _find_segment(segments: list[TimelineSegment], segment_id: str) -> TimelineSegment | None:
    return next((segment for segment in segments if segment.segment_id == segment_id), None)


def _id(prefix: str, *parts: str) -> str:
    return prefix + "_" + hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:20]


def _read_optional(path: Path, model: type[T]) -> T | None:
    if not path.exists():
        return None
    return model.model_validate_json(path.read_text(encoding="utf-8"))


def _fingerprint(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _fingerprint_many(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        if path.exists():
            digest.update(path.as_posix().encode("utf-8"))
            digest.update(path.read_bytes())
    return "sha256:" + digest.hexdigest()
