from __future__ import annotations

import hashlib
import json
from pathlib import Path

from artist_portrait_editor.constants import DATA_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.bgm import BgmAnalysisReport, BgmBeatGrid, BgmFitPlan
from artist_portrait_editor.models.acceptance import ProjectAcceptanceReport
from artist_portrait_editor.models.final_export import FinalExportManifest, FinalExportValidationReport
from artist_portrait_editor.models.preview import PreviewRenderManifest, PreviewValidationReport
from artist_portrait_editor.models.rhythm import (
    RhythmAgentCandidate,
    RhythmAuditDomain,
    RhythmIntent,
    RhythmIssue,
    RhythmMediaQcReport,
    RhythmPlan,
    RhythmProfileMetric,
    RhythmRepairAction,
    RhythmRepairPlan,
)
from artist_portrait_editor.models.timeline import TimelineDraft
from artist_portrait_editor.run_records import write_json


class RhythmError(ValueError):
    pass


DEFAULT_INTENT = RhythmIntent(
    intent_id="default_balanced_medium",
    mode="balanced",
    pacing="medium",
    text_density="low",
    transition_style="smooth",
    ending_style="fade_out",
    notes="default deterministic rhythm-planning intent",
)


def build_rhythm_plan(
    *,
    root: Path,
    project_id: str,
    intent_path: Path | None = None,
    agent_output_path: Path | None = None,
) -> tuple[Path, Path, Path, RhythmPlan]:
    timeline_path = root / "output" / "timeline_draft.json"
    if not timeline_path.exists():
        raise RhythmError("rhythm planning requires output/timeline_draft.json")
    timeline = TimelineDraft.model_validate_json(timeline_path.read_text(encoding="utf-8"))
    if timeline.project_id != project_id:
        raise RhythmError("timeline project_id mismatches project")
    timeline_fingerprint = _fingerprint(timeline_path)
    fit_path = root / WORKSPACE_DIR / DATA_DIR / "bgm_fit.json"
    analysis_path = root / WORKSPACE_DIR / DATA_DIR / "bgm_analysis.json"
    fit = (
        BgmFitPlan.model_validate_json(fit_path.read_text(encoding="utf-8"))
        if fit_path.exists()
        else None
    )
    analysis = (
        BgmAnalysisReport.model_validate_json(analysis_path.read_text(encoding="utf-8"))
        if analysis_path.exists()
        else None
    )
    intent = _read_intent(intent_path) if intent_path else DEFAULT_INTENT
    candidate = _read_candidate(agent_output_path) if agent_output_path else None
    domains = _build_domains(root, timeline, timeline_fingerprint, fit, analysis, intent, candidate)
    issues = [issue for domain in domains for issue in domain.issues]
    warnings = sum(issue.severity == "warning" for issue in issues)
    errors = sum(issue.severity == "error" for issue in issues)
    status = "blocked" if errors else "warning" if warnings else "passed"
    fit_fingerprint = _fingerprint(fit_path) if fit_path.exists() else None
    analysis_fingerprint = _fingerprint(analysis_path) if analysis_path.exists() else None
    key = f"{project_id}:{timeline.timeline_id}:{timeline_fingerprint}:{intent.intent_id}:{fit.fit_id if fit else 'none'}:{len(issues)}"
    plan = RhythmPlan(
        rhythm_plan_id="rhythm_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=project_id,
        timeline_id=timeline.timeline_id,
        timeline_fingerprint=timeline_fingerprint,
        bgm_fit_id=fit.fit_id if fit else None,
        bgm_fit_fingerprint=fit_fingerprint,
        bgm_analysis_fingerprint=analysis_fingerprint,
        intent=intent,
        timeline_profile=domains[0],
        bgm_profile=domains[1],
        compatibility_audit=domains[2],
        intent_audit=domains[3],
        cut_cue_audit=domains[4],
        transition_audit=domains[5],
        text_audit=domains[6],
        ducking_silence_audit=domains[7],
        ending_audit=domains[8],
        agent_candidate_audit=domains[9] if candidate else None,
        issue_count=len(issues),
        warning_count=warnings,
        error_count=errors,
        status=status,
    )
    json_path = root / WORKSPACE_DIR / DATA_DIR / "rhythm_plan.json"
    md_path = root / "output" / "rhythm_report.md"
    handoff_path = root / "output" / "rhythm_agent_handoff.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, plan.model_dump(mode="json"))
    md_path.write_text(render_rhythm_report(plan) + "\n", encoding="utf-8")
    write_json(handoff_path, _handoff_payload(plan))
    return json_path, md_path, handoff_path, plan


def build_rhythm_media_qc(
    *,
    root: Path,
    project_id: str,
) -> tuple[Path, Path, Path, RhythmMediaQcReport]:
    plan_path = root / WORKSPACE_DIR / DATA_DIR / "rhythm_plan.json"
    if not plan_path.exists():
        raise RhythmError("rhythm QC requires .artist-portrait/data/rhythm_plan.json")
    plan = RhythmPlan.model_validate_json(plan_path.read_text(encoding="utf-8"))
    if plan.project_id != project_id:
        raise RhythmError("rhythm plan project_id mismatches project")
    plan_fingerprint = _fingerprint(plan_path)
    timeline_path = root / "output" / "timeline_draft.json"
    fit_path = root / WORKSPACE_DIR / DATA_DIR / "bgm_fit.json"
    preview_manifest = _read_optional(root / WORKSPACE_DIR / DATA_DIR / "preview_manifest.json", PreviewRenderManifest)
    preview_validation = _read_optional(root / WORKSPACE_DIR / DATA_DIR / "preview_validation.json", PreviewValidationReport)
    final_manifest = _read_optional(root / WORKSPACE_DIR / DATA_DIR / "final_export_manifest.json", FinalExportManifest)
    final_validation = _read_optional(root / WORKSPACE_DIR / DATA_DIR / "final_export_validation.json", FinalExportValidationReport)
    domains = [
        _preview_binding_qc(plan, preview_manifest, preview_validation),
        _final_binding_qc(plan, final_manifest, final_validation),
        _timeline_freshness_qc(plan, timeline_path),
        _bgm_freshness_qc(plan, fit_path),
        _duration_qc("preview_duration_qc", "preview", plan, preview_manifest, preview_validation),
        _duration_qc("final_duration_qc", "final_export", plan, final_manifest, final_validation),
        _audio_expectation_qc(plan, preview_manifest, preview_validation, final_manifest, final_validation),
        _ducking_render_qc(plan, preview_manifest, final_manifest),
        _ending_render_qc(plan, preview_manifest, final_manifest),
    ]
    summary = _media_qc_summary(domains)
    all_domains = domains + [summary]
    issues = [issue for domain in all_domains for issue in domain.issues]
    warnings = sum(issue.severity == "warning" for issue in issues)
    errors = sum(issue.severity == "error" for issue in issues)
    status = "blocked" if errors else "warning" if warnings else "passed"
    key = f"{project_id}:{plan.rhythm_plan_id}:{plan_fingerprint}:{warnings}:{errors}"
    report = RhythmMediaQcReport(
        rhythm_qc_id="rhythm_qc_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=project_id,
        rhythm_plan_id=plan.rhythm_plan_id,
        rhythm_plan_fingerprint=plan_fingerprint,
        timeline_id=plan.timeline_id,
        preview_binding=domains[0],
        final_export_binding=domains[1],
        timeline_freshness=domains[2],
        bgm_freshness=domains[3],
        preview_duration_qc=domains[4],
        final_duration_qc=domains[5],
        audio_expectation_qc=domains[6],
        ducking_render_qc=domains[7],
        ending_render_qc=domains[8],
        media_qc_summary=summary,
        issue_count=len(issues),
        warning_count=warnings,
        error_count=errors,
        status=status,
    )
    json_path = root / WORKSPACE_DIR / DATA_DIR / "rhythm_media_qc.json"
    md_path = root / "output" / "rhythm_media_qc.md"
    handoff_path = root / "output" / "rhythm_media_qc_handoff.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, report.model_dump(mode="json"))
    md_path.write_text(render_rhythm_media_qc(report) + "\n", encoding="utf-8")
    write_json(handoff_path, _media_qc_handoff_payload(report))
    return json_path, md_path, handoff_path, report


def build_rhythm_repair_plan(
    *,
    root: Path,
    project_id: str,
    acceptance_profile: str = "delivery",
) -> tuple[Path, Path, Path, RhythmRepairPlan]:
    if acceptance_profile not in {"standard", "core", "preview", "delivery"}:
        raise RhythmError(f"unsupported acceptance profile: {acceptance_profile}")
    plan_path = root / WORKSPACE_DIR / DATA_DIR / "rhythm_plan.json"
    qc_path = root / WORKSPACE_DIR / DATA_DIR / "rhythm_media_qc.json"
    acceptance_path = root / WORKSPACE_DIR / DATA_DIR / "acceptance_report.json"
    rhythm_plan = _read_optional(plan_path, RhythmPlan)
    rhythm_qc = _read_optional(qc_path, RhythmMediaQcReport)
    acceptance = _read_optional(acceptance_path, ProjectAcceptanceReport)
    if rhythm_plan and rhythm_plan.project_id != project_id:
        raise RhythmError("rhythm plan project_id mismatches project")
    if rhythm_qc and rhythm_qc.project_id != project_id:
        raise RhythmError("rhythm media QC project_id mismatches project")
    if acceptance and acceptance.project_id != project_id:
        raise RhythmError("acceptance report project_id mismatches project")
    actions = _rhythm_repair_actions(
        root,
        acceptance_profile,
        rhythm_plan,
        rhythm_qc,
        acceptance,
    )
    required = [action for action in actions if action.severity == "required"]
    key = (
        f"{project_id}:{acceptance_profile}:"
        f"{rhythm_plan.rhythm_plan_id if rhythm_plan else 'no-plan'}:"
        f"{rhythm_qc.rhythm_qc_id if rhythm_qc else 'no-qc'}:"
        f"{','.join(action.action_id for action in actions)}"
    )
    status = "blocked" if required else "warning" if actions else "passed"
    repair = RhythmRepairPlan(
        rhythm_repair_plan_id="rhythm_repair_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=project_id,
        acceptance_profile=acceptance_profile,
        rhythm_plan_id=rhythm_plan.rhythm_plan_id if rhythm_plan else None,
        rhythm_qc_id=rhythm_qc.rhythm_qc_id if rhythm_qc else None,
        acceptance_id=acceptance.acceptance_id if acceptance else None,
        action_count=len(actions),
        required_action_count=len(required),
        optional_action_count=len(actions) - len(required),
        first_required_command=required[0].command if required else None,
        status=status,
        actions=actions,
    )
    json_path = root / WORKSPACE_DIR / DATA_DIR / "rhythm_repair_plan.json"
    md_path = root / "output" / "rhythm_repair_plan.md"
    handoff_path = root / "output" / "rhythm_repair_handoff.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, repair.model_dump(mode="json"))
    md_path.write_text(render_rhythm_repair_plan(repair) + "\n", encoding="utf-8")
    write_json(handoff_path, _repair_handoff_payload(repair))
    return json_path, md_path, handoff_path, repair


def render_rhythm_report(plan: RhythmPlan) -> str:
    lines = [
        "# Rhythm Planning Report",
        "",
        "This report audits edit rhythm and BGM fit evidence. It does not move edit points, select music, render media, call models, or access the network.",
        "",
        f"- Status: `{plan.status}`",
        f"- Intent: `{plan.intent.mode}` / `{plan.intent.pacing}`",
        f"- Issues: `{plan.issue_count}`",
        f"- Warnings: `{plan.warning_count}`",
        f"- Errors: `{plan.error_count}`",
        "",
    ]
    domains = [
        plan.timeline_profile,
        plan.bgm_profile,
        plan.compatibility_audit,
        plan.intent_audit,
        plan.cut_cue_audit,
        plan.transition_audit,
        plan.text_audit,
        plan.ducking_silence_audit,
        plan.ending_audit,
    ]
    if plan.agent_candidate_audit:
        domains.append(plan.agent_candidate_audit)
    for domain in domains:
        lines.extend([f"## `{domain.domain_id}`", "", f"- Status: `{domain.status}`", f"- Summary: {domain.summary}"])
        for metric in domain.metrics:
            lines.append(f"- `{metric.metric_id}` `{metric.status}`: {metric.label} = `{metric.value}`. {metric.detail}")
        for issue in domain.issues:
            lines.append(f"- `{issue.severity}` `{issue.issue_id}`: {issue.detail} Next: `{issue.next_action}`")
        lines.append("")
    return "\n".join(lines)


def render_rhythm_repair_plan(plan: RhythmRepairPlan) -> str:
    lines = [
        "# Rhythm Repair Plan",
        "",
        "This plan lists explicit manual next commands for rhythm and media alignment. It does not execute commands, render media, move edit points, select music, fit music, call models, or access the network.",
        "",
        f"- Status: `{plan.status}`",
        f"- Acceptance profile: `{plan.acceptance_profile}`",
        f"- Required actions: `{plan.required_action_count}`",
        f"- Optional actions: `{plan.optional_action_count}`",
        f"- First required command: `{plan.first_required_command or 'none'}`",
        "",
    ]
    if not plan.actions:
        lines.append("No rhythm repair actions are required by the current evidence.")
        return "\n".join(lines)
    for action in plan.actions:
        lines.extend(
            [
                f"## `{action.action_id}`",
                "",
                f"- Category: `{action.category}`",
                f"- Severity: `{action.severity}`",
                f"- Reason: `{action.reason_code}`",
                f"- Command: `{action.command}`",
                f"- Rationale: {action.rationale}",
            ]
        )
        if action.expected_artifacts:
            lines.append(
                f"- Expected artifacts: {', '.join(f'`{ref}`' for ref in action.expected_artifacts)}"
            )
        lines.append("")
    return "\n".join(lines)


def render_rhythm_media_qc(report: RhythmMediaQcReport) -> str:
    lines = [
        "# Rhythm Media QC Report",
        "",
        "This report checks rhythm-planning evidence against existing preview/final artifacts. It does not render media, move edit points, select music, call models, or access the network.",
        "",
        f"- Status: `{report.status}`",
        f"- Issues: `{report.issue_count}`",
        f"- Warnings: `{report.warning_count}`",
        f"- Errors: `{report.error_count}`",
        "",
    ]
    for domain in [
        report.preview_binding,
        report.final_export_binding,
        report.timeline_freshness,
        report.bgm_freshness,
        report.preview_duration_qc,
        report.final_duration_qc,
        report.audio_expectation_qc,
        report.ducking_render_qc,
        report.ending_render_qc,
        report.media_qc_summary,
    ]:
        lines.extend([f"## `{domain.domain_id}`", "", f"- Status: `{domain.status}`", f"- Summary: {domain.summary}"])
        for metric in domain.metrics:
            lines.append(f"- `{metric.metric_id}` `{metric.status}`: {metric.label} = `{metric.value}`. {metric.detail}")
        for issue in domain.issues:
            lines.append(f"- `{issue.severity}` `{issue.issue_id}`: {issue.detail} Next: `{issue.next_action}`")
        lines.append("")
    return "\n".join(lines)


def _build_domains(
    root: Path,
    timeline: TimelineDraft,
    timeline_fingerprint: str,
    fit: BgmFitPlan | None,
    analysis: BgmAnalysisReport | None,
    intent: RhythmIntent,
    candidate: RhythmAgentCandidate | None,
) -> list[RhythmAuditDomain]:
    timeline_profile = _timeline_profile(timeline)
    bgm_profile = _bgm_profile(fit, analysis)
    compatibility = _compatibility_audit(timeline, fit, analysis)
    intent_audit = _intent_audit(intent, timeline)
    cut_cue = _cut_cue_audit(root, timeline, fit)
    transition = _transition_audit(timeline, intent)
    text = _text_audit(root, intent)
    ducking_silence = _ducking_silence_audit(fit, analysis)
    ending = _ending_audit(timeline, fit, analysis, intent)
    agent = _agent_candidate_audit(candidate, timeline, timeline_fingerprint) if candidate else _domain(
        "agent_candidate",
        "unavailable",
        "No external rhythm candidate was imported.",
        [],
        [],
    )
    return [
        timeline_profile,
        bgm_profile,
        compatibility,
        intent_audit,
        cut_cue,
        transition,
        text,
        ducking_silence,
        ending,
        agent,
    ]


def _timeline_profile(timeline: TimelineDraft) -> RhythmAuditDomain:
    durations = [item.timeline_end - item.timeline_start for item in timeline.segments]
    avg = round(sum(durations) / len(durations), 3)
    cuts_per_minute = round((max(len(timeline.segments) - 1, 0) / timeline.actual_duration) * 60, 3)
    transitions = sum(item.video_transition.value != "none" for item in timeline.segments)
    status = "warning" if cuts_per_minute > 45 else "passed"
    issues = []
    if cuts_per_minute > 45:
        issues.append(_issue("timeline_cut_density_high", "timeline", "warning", "Timeline cut density is high.", "Review pacing before requesting music-first rhythm."))
    return _domain(
        "timeline_profile",
        status,
        "Timeline pacing profile was derived from canonical segments.",
        [
            _metric("segment_count", "Segment count", len(timeline.segments), "available", "Canonical timeline segments counted."),
            _metric("average_segment_seconds", "Average segment duration", avg, "available", "Mean timeline segment length."),
            _metric("cuts_per_minute", "Cuts per minute", cuts_per_minute, "available", "Cut density derived from timeline duration."),
            _metric("video_transition_count", "Video transition count", transitions, "available", "Non-none video transitions counted."),
        ],
        issues,
    )


def _bgm_profile(fit: BgmFitPlan | None, analysis: BgmAnalysisReport | None) -> RhythmAuditDomain:
    if fit is None:
        return _domain("bgm_profile", "unavailable", "No current BGM fit plan is available.", [], [_issue("bgm_fit_missing", "bgm", "warning", "Rhythm planning has no fitted BGM.", "Run explicit BGM import/fit or keep no-music planning.")])
    candidate = next((item for item in (analysis.candidates if analysis else []) if item.music_candidate_id == fit.music_candidate_id), None)
    metrics = [
        _metric("fit_mode", "Fit mode", fit.fit_mode, "available", "Current BGM fit mode."),
        _metric("ducking_intervals", "Ducking interval count", len(fit.ducking_intervals), "available", "Ducking intervals from current fit plan."),
        _metric("beat_alignment_status", "Beat alignment status", fit.beat_alignment_status, "available", "Beat alignment state from current fit plan."),
    ]
    if candidate:
        metrics.extend([
            _metric("quiet_head_seconds", "Quiet head seconds", candidate.quiet_head_seconds, "available", "Technical BGM analysis quiet head."),
            _metric("quiet_tail_seconds", "Quiet tail seconds", candidate.quiet_tail_seconds, "available", "Technical BGM analysis quiet tail."),
            _metric("high_energy_start", "High energy start", candidate.high_energy_start, "available" if candidate.high_energy_start is not None else "unavailable", "High-energy range from local analysis."),
        ])
    issues = []
    if fit.beat_alignment_status == "unavailable" and fit.controls.beat_alignment_requested:
        issues.append(_issue("beat_alignment_unavailable", "bgm", "warning", "Beat alignment was requested but no validated beat grid is available.", "Keep edit points unchanged or install a validated local beat engine."))
    return _domain("bgm_profile", "warning" if issues else "passed", "BGM rhythm profile was derived from current fit and analysis evidence.", metrics, issues)


def _compatibility_audit(timeline: TimelineDraft, fit: BgmFitPlan | None, analysis: BgmAnalysisReport | None) -> RhythmAuditDomain:
    issues = []
    if fit is None:
        issues.append(_issue("compatibility_no_bgm", "compatibility", "warning", "No fitted BGM exists for compatibility scoring.", "Run explicit BGM fit or keep no-music rhythm planning."))
    elif abs(fit.target_duration - timeline.actual_duration) > 0.25:
        issues.append(_issue("duration_mismatch", "compatibility", "error", "BGM fit duration and timeline duration diverge.", "Rebuild BGM fit from the current timeline."))
    score = 1.0 - min(len(issues) * 0.25, 1.0)
    return _domain("compatibility_audit", "blocked" if any(i.severity == "error" for i in issues) else "warning" if issues else "passed", "Timeline and BGM compatibility was checked without changing either artifact.", [_metric("compatibility_score", "Compatibility score", round(score, 3), "available", "Deterministic readiness score from blocking issues.")], issues)


def _intent_audit(intent: RhythmIntent, timeline: TimelineDraft) -> RhythmAuditDomain:
    cuts_per_minute = (max(len(timeline.segments) - 1, 0) / timeline.actual_duration) * 60
    issues = []
    if intent.pacing == "calm" and cuts_per_minute > 30:
        issues.append(_issue("calm_intent_fast_cutting", "intent", "warning", "Calm intent conflicts with fast timeline cutting.", "Review segment selection before changing edit timing."))
    if intent.mode == "speech_first" and intent.text_density == "high":
        issues.append(_issue("speech_first_high_text_density", "intent", "warning", "Speech-first mode with high text density may overload viewer attention.", "Review text/subtitle strategy."))
    return _domain("intent_audit", "warning" if issues else "passed", "Explicit rhythm intent was checked against timeline evidence.", [_metric("intent_mode", "Intent mode", intent.mode, "available", "User-provided or default rhythm intent."), _metric("intent_pacing", "Intent pacing", intent.pacing, "available", "User-provided or default pacing intent.")], issues)


def _cut_cue_audit(root: Path, timeline: TimelineDraft, fit: BgmFitPlan | None) -> RhythmAuditDomain:
    if fit is None or not fit.beat_grid_ref:
        return _domain("cut_cue_audit", "unavailable", "Cut/cue alignment requires a validated beat grid; none is available.", [_metric("edit_points_moved", "Edit points moved", False, "available", "Rhythm planning never moves edit points.")], [])
    grid = BgmBeatGrid.model_validate_json((root / fit.beat_grid_ref).read_text(encoding="utf-8"))
    beat_times = [beat.time for beat in grid.beat_times]
    distances = []
    for segment in timeline.segments[1:]:
        distances.append(min((abs(segment.timeline_start - beat) for beat in beat_times), default=999.0))
    avg_distance = round(sum(distances) / len(distances), 3) if distances else 0.0
    issues = []
    if avg_distance > 0.2:
        issues.append(_issue("cuts_far_from_beats", "cut_cue", "warning", "Average cut distance from beat grid is high.", "Consider manual edit review; do not auto-move edit points."))
    return _domain("cut_cue_audit", "warning" if issues else "passed", "Cut/cue proximity was measured against validated beat evidence.", [_metric("average_cut_to_beat_seconds", "Average cut-to-beat distance", avg_distance, "available", "Nearest beat distance for each non-first segment start."), _metric("edit_points_moved", "Edit points moved", False, "available", "Rhythm planning never moves edit points.")], issues)


def _transition_audit(timeline: TimelineDraft, intent: RhythmIntent) -> RhythmAuditDomain:
    non_none = [item for item in timeline.segments if item.video_transition.value != "none"]
    issues = []
    if intent.transition_style == "minimal" and len(non_none) > 2:
        issues.append(_issue("minimal_transition_conflict", "transition", "warning", "Minimal transition intent conflicts with multiple video transitions.", "Review transition strategy manually."))
    if intent.transition_style == "energetic" and not non_none:
        issues.append(_issue("energetic_transition_absent", "transition", "warning", "Energetic transition intent has no explicit transition evidence.", "Review transition placement manually."))
    return _domain("transition_audit", "warning" if issues else "passed", "Transition rhythm was checked against explicit timeline transitions.", [_metric("non_none_transition_count", "Non-none transition count", len(non_none), "available", "Video transitions counted from timeline.")], issues)


def _text_audit(root: Path, intent: RhythmIntent) -> RhythmAuditDomain:
    transcript_path = root / WORKSPACE_DIR / DATA_DIR / "transcripts.jsonl"
    transcript_exists = transcript_path.exists()
    line_count = 0
    if transcript_exists:
        line_count = len([line for line in transcript_path.read_text(encoding="utf-8").splitlines() if line.strip()])
    issues = []
    if intent.text_density in {"medium", "high"} and not transcript_exists:
        issues.append(_issue("text_intent_without_transcripts", "text", "warning", "Text-density intent has no transcript ledger evidence.", "Run transcription or keep text rhythm planning conservative."))
    return _domain("text_audit", "warning" if issues else "passed", "Text/subtitle rhythm readiness was checked from transcript evidence.", [_metric("transcript_ledger_present", "Transcript ledger present", transcript_exists, "available", "Transcript ledger existence."), _metric("transcript_record_count", "Transcript record count", line_count, "available" if transcript_exists else "unavailable", "Transcript records available for text rhythm planning.")], issues)


def _ducking_silence_audit(fit: BgmFitPlan | None, analysis: BgmAnalysisReport | None) -> RhythmAuditDomain:
    issues = []
    metrics = []
    if fit is None:
        issues.append(_issue("ducking_no_fit", "ducking_silence", "warning", "No BGM fit exists for ducking/silence audit.", "Run explicit BGM fit if music is intended."))
    else:
        metrics.append(_metric("ducking_enabled", "Ducking enabled", fit.controls.ducking_enabled, "available", "Explicit BGM fit control."))
        metrics.append(_metric("ducking_gain_db", "Ducking gain dB", fit.controls.ducking_gain_db, "available", "Explicit BGM fit control."))
        if fit.controls.ducking_enabled and not fit.ducking_intervals:
            issues.append(_issue("ducking_enabled_without_intervals", "ducking_silence", "warning", "Ducking is enabled but no intervals are present.", "Review retained original audio and speech-first mix needs."))
    return _domain("ducking_silence_audit", "warning" if issues else "passed", "Speech/music ducking and silence readiness were checked without rendering audio.", metrics, issues)


def _ending_audit(timeline: TimelineDraft, fit: BgmFitPlan | None, analysis: BgmAnalysisReport | None, intent: RhythmIntent) -> RhythmAuditDomain:
    last = max(timeline.segments, key=lambda item: item.timeline_end)
    last_duration = round(last.timeline_end - last.timeline_start, 3)
    issues = []
    if intent.ending_style == "fade_out" and fit and fit.fade_out_seconds <= 0:
        issues.append(_issue("fade_out_intent_without_fade", "ending", "warning", "Fade-out ending intent has no BGM fade-out seconds.", "Set explicit BGM fade-out controls if desired."))
    if last_duration < 0.5:
        issues.append(_issue("short_final_segment", "ending", "warning", "Final timeline segment is very short.", "Review ending hold manually."))
    return _domain("ending_audit", "warning" if issues else "passed", "Ending/outro rhythm was checked from final segment and BGM controls.", [_metric("final_segment_seconds", "Final segment seconds", last_duration, "available", "Duration of the last timeline segment."), _metric("ending_style", "Ending style", intent.ending_style, "available", "User-provided or default ending intent.")], issues)


def _agent_candidate_audit(candidate: RhythmAgentCandidate, timeline: TimelineDraft, timeline_fingerprint: str) -> RhythmAuditDomain:
    issues = []
    if candidate.project_id != timeline.project_id:
        issues.append(_issue("candidate_project_mismatch", "agent_candidate", "error", "Candidate project_id mismatches timeline.", "Regenerate rhythm candidate for the current project."))
    if candidate.timeline_id != timeline.timeline_id:
        issues.append(_issue("candidate_timeline_mismatch", "agent_candidate", "error", "Candidate timeline_id mismatches current timeline.", "Regenerate rhythm candidate for the current timeline."))
    if candidate.edit_points_moved:
        issues.append(_issue("candidate_moves_edit_points", "agent_candidate", "error", "Candidate claims edit points were moved.", "Reject candidate; V0-031 cannot move edit points."))
    if candidate.music_selected:
        issues.append(_issue("candidate_selects_music", "agent_candidate", "error", "Candidate claims music was selected.", "Reject candidate; V0-031 cannot select music."))
    if candidate.media_rendered:
        issues.append(_issue("candidate_renders_media", "agent_candidate", "error", "Candidate claims media was rendered.", "Reject candidate; V0-031 cannot render media."))
    if candidate.model_call_performed_by_cli or candidate.network_performed:
        issues.append(_issue("candidate_forbidden_cli_capability", "agent_candidate", "error", "Candidate claims CLI model/network execution.", "Reject candidate."))
    return _domain("agent_candidate_audit", "blocked" if issues else "passed", "External rhythm candidate was validated without promotion to timeline changes.", [_metric("recommendation_count", "Recommendation count", len(candidate.recommendations), "available", "Host-Agent/local-model recommendations carried as review text only.")], issues)


def _preview_binding_qc(plan: RhythmPlan, manifest: PreviewRenderManifest | None, validation: PreviewValidationReport | None) -> RhythmAuditDomain:
    issues = []
    if manifest is None or validation is None:
        issues.append(_issue("preview_artifacts_missing", "compatibility", "warning", "Preview manifest or validation is missing.", "Run preview and review preview before rhythm media QC."))
        return _domain("preview_binding", "warning", "Preview artifacts are not fully available for rhythm QC.", [], issues)
    if manifest.timeline_id != plan.timeline_id:
        issues.append(_issue("preview_timeline_mismatch", "compatibility", "error", "Preview timeline_id mismatches rhythm plan.", "Rebuild preview from the current timeline."))
    if validation.timeline_fingerprint != plan.timeline_fingerprint:
        issues.append(_issue("preview_timeline_fingerprint_stale", "compatibility", "error", "Preview validation timeline fingerprint is stale for rhythm plan.", "Rebuild preview from the current rhythm timeline."))
    return _domain("preview_binding", "blocked" if any(i.severity == "error" for i in issues) else "passed", "Preview artifacts were bound to the rhythm plan.", [_metric("preview_present", "Preview artifacts present", True, "available", "Preview manifest and validation exist."), _metric("preview_quality_status", "Preview quality status", validation.quality_status, "available", "Preview validation quality status.")], issues)


def _final_binding_qc(plan: RhythmPlan, manifest: FinalExportManifest | None, validation: FinalExportValidationReport | None) -> RhythmAuditDomain:
    issues = []
    if manifest is None or validation is None:
        issues.append(_issue("final_export_artifacts_missing", "compatibility", "warning", "Final export manifest or validation is missing.", "Run export and review final_export before delivery rhythm QC."))
        return _domain("final_export_binding", "warning", "Final export artifacts are not fully available for rhythm QC.", [], issues)
    if manifest.timeline_id != plan.timeline_id:
        issues.append(_issue("final_timeline_mismatch", "compatibility", "error", "Final export timeline_id mismatches rhythm plan.", "Rebuild final export from the current timeline."))
    if validation.timeline_fingerprint != plan.timeline_fingerprint:
        issues.append(_issue("final_timeline_fingerprint_stale", "compatibility", "error", "Final export validation timeline fingerprint is stale for rhythm plan.", "Rebuild final export from the current rhythm timeline."))
    return _domain("final_export_binding", "blocked" if any(i.severity == "error" for i in issues) else "passed", "Final export artifacts were bound to the rhythm plan.", [_metric("final_export_present", "Final export artifacts present", True, "available", "Final export manifest and validation exist."), _metric("final_quality_status", "Final quality status", validation.quality_status, "available", "Final export validation quality status.")], issues)


def _timeline_freshness_qc(plan: RhythmPlan, timeline_path: Path) -> RhythmAuditDomain:
    issues = []
    current = _fingerprint(timeline_path) if timeline_path.exists() else None
    if current is None:
        issues.append(_issue("timeline_missing", "timeline", "error", "Canonical timeline is missing.", "Regenerate timeline before rhythm media QC."))
    elif current != plan.timeline_fingerprint:
        issues.append(_issue("rhythm_plan_timeline_stale", "timeline", "error", "Rhythm plan is stale against current timeline.", "Regenerate rhythm plan."))
    return _domain("timeline_freshness", "blocked" if issues else "passed", "Rhythm plan timeline freshness was checked.", [_metric("timeline_fingerprint_matches", "Timeline fingerprint matches", not issues, "available", "Current timeline hash compared with rhythm plan.")], issues)


def _bgm_freshness_qc(plan: RhythmPlan, fit_path: Path) -> RhythmAuditDomain:
    issues = []
    if plan.bgm_fit_fingerprint and not fit_path.exists():
        issues.append(_issue("bgm_fit_missing", "bgm", "error", "Rhythm plan references a BGM fit but current fit is missing.", "Regenerate BGM fit or rhythm plan."))
    elif plan.bgm_fit_fingerprint and _fingerprint(fit_path) != plan.bgm_fit_fingerprint:
        issues.append(_issue("rhythm_plan_bgm_fit_stale", "bgm", "error", "Rhythm plan is stale against current BGM fit.", "Regenerate rhythm plan."))
    return _domain("bgm_freshness", "blocked" if issues else "passed", "Rhythm plan BGM freshness was checked.", [_metric("bgm_fit_fingerprint_matches", "BGM fit fingerprint matches", not issues, "available", "Current BGM fit hash compared with rhythm plan when applicable.")], issues)


def _duration_qc(domain_id: str, label: str, plan: RhythmPlan, manifest, validation) -> RhythmAuditDomain:
    issues = []
    if manifest is None or validation is None:
        issues.append(_issue(f"{label}_duration_unavailable", "compatibility", "warning", f"{label} duration evidence is unavailable.", f"Generate {label} media before duration rhythm QC."))
        return _domain(domain_id, "warning", f"{label} duration QC is unavailable.", [], issues)
    delta = abs(validation.duration_delta_seconds)
    if delta > validation.duration_tolerance_seconds:
        issues.append(_issue(f"{label}_duration_drift", "compatibility", "error", f"{label} duration exceeds tolerance.", f"Rebuild {label} media from the current timeline."))
    return _domain(domain_id, "blocked" if issues else "passed", f"{label} duration was checked against rhythm/timeline duration.", [_metric("duration_delta_seconds", "Duration delta seconds", validation.duration_delta_seconds, "available", f"{label} validation duration delta."), _metric("duration_tolerance_seconds", "Duration tolerance seconds", validation.duration_tolerance_seconds, "available", f"{label} validation duration tolerance.")], issues)


def _audio_expectation_qc(plan: RhythmPlan, preview_manifest, preview_validation, final_manifest, final_validation) -> RhythmAuditDomain:
    issues = []
    metrics = []
    for name, validation in (("preview", preview_validation), ("final_export", final_validation)):
        if validation is None:
            issues.append(_issue(f"{name}_audio_unavailable", "ducking_silence", "warning", f"{name} audio validation is unavailable.", f"Generate/review {name} before audio rhythm QC."))
            continue
        metrics.append(_metric(f"{name}_audio_present", f"{name} audio present", validation.audio_present, "available", f"{name} audio stream state."))
        if validation.audio_expected and not validation.audio_present:
            issues.append(_issue(f"{name}_audio_missing", "ducking_silence", "error", f"{name} expected audio but none is present.", f"Rebuild {name} audio."))
    return _domain("audio_expectation_qc", "blocked" if any(i.severity == "error" for i in issues) else "warning" if issues else "passed", "Audio presence was checked against rendered media expectations.", metrics, issues)


def _ducking_render_qc(plan: RhythmPlan, preview_manifest, final_manifest) -> RhythmAuditDomain:
    issues = []
    metrics = []
    requested = plan.ducking_silence_audit.status != "unavailable"
    for name, manifest in (("preview", preview_manifest), ("final_export", final_manifest)):
        if manifest is None:
            issues.append(_issue(f"{name}_ducking_unavailable", "ducking_silence", "warning", f"{name} manifest is unavailable for ducking QC.", f"Generate {name} before ducking QC."))
            continue
        metrics.append(_metric(f"{name}_ducking_applied", f"{name} ducking applied", manifest.ducking_applied, "available", f"{name} manifest ducking flag."))
    return _domain("ducking_render_qc", "warning" if issues else "passed", "Ducking render state was checked from existing manifests.", metrics + [_metric("ducking_planned", "Ducking planned/audited", requested, "available", "Rhythm plan contains ducking/silence audit.")], issues)


def _ending_render_qc(plan: RhythmPlan, preview_manifest, final_manifest) -> RhythmAuditDomain:
    issues = []
    metrics = []
    for name, manifest in (("preview", preview_manifest), ("final_export", final_manifest)):
        if manifest is None:
            issues.append(_issue(f"{name}_ending_unavailable", "ending", "warning", f"{name} manifest is unavailable for ending QC.", f"Generate {name} before ending QC."))
            continue
        metrics.append(_metric(f"{name}_duration", f"{name} rendered duration", manifest.duration, "available", f"{name} rendered duration for ending review."))
        if manifest.duration < 0.5:
            issues.append(_issue(f"{name}_too_short_for_ending", "ending", "error", f"{name} media is too short for ending rhythm review.", f"Rebuild {name} from a valid timeline."))
    return _domain("ending_render_qc", "blocked" if any(i.severity == "error" for i in issues) else "warning" if issues else "passed", "Rendered ending duration evidence was checked.", metrics, issues)


def _media_qc_summary(domains: list[RhythmAuditDomain]) -> RhythmAuditDomain:
    errors = sum(1 for domain in domains for issue in domain.issues if issue.severity == "error")
    warnings = sum(1 for domain in domains for issue in domain.issues if issue.severity == "warning")
    status = "blocked" if errors else "warning" if warnings else "passed"
    return _domain(
        "media_qc_summary",
        status,
        "Rhythm media QC summarized existing preview/final evidence without rendering.",
        [
            _metric("domain_count", "Domain count", len(domains), "available", "QC domains evaluated."),
            _metric("error_count", "Error count", errors, "available", "Blocking rhythm media QC issues."),
            _metric("warning_count", "Warning count", warnings, "available", "Non-blocking rhythm media QC issues."),
            _metric("media_rendered_by_qc", "Media rendered by QC", False, "available", "QC never renders media."),
        ],
        [],
    )


def _media_qc_handoff_payload(report: RhythmMediaQcReport) -> dict:
    return {
        "schema_version": report.schema_version,
        "handoff_id": f"rhythm_media_qc_handoff_{report.rhythm_qc_id}",
        "project_id": report.project_id,
        "rhythm_qc_id": report.rhythm_qc_id,
        "rhythm_plan_id": report.rhythm_plan_id,
        "task": "Review rhythm media QC and propose textual fixes only.",
        "forbidden": [
            "do not render media",
            "do not move edit points",
            "do not select music",
            "do not call models from the CLI",
            "do not access the network",
        ],
    }


def _rhythm_repair_actions(
    root: Path,
    acceptance_profile: str,
    rhythm_plan: RhythmPlan | None,
    rhythm_qc: RhythmMediaQcReport | None,
    acceptance: ProjectAcceptanceReport | None,
) -> list[RhythmRepairAction]:
    required_profiles = {"preview", "delivery"}
    delivery_profile = acceptance_profile == "delivery"
    profile_requires_rhythm = acceptance_profile in required_profiles
    actions: list[RhythmRepairAction] = []
    seen: set[tuple[str, str]] = set()

    def add(
        category: str,
        reason_code: str,
        command: str,
        rationale: str,
        expected_artifacts: list[str],
        *,
        required: bool,
    ) -> None:
        key = (category, reason_code)
        if key in seen:
            return
        seen.add(key)
        actions.append(
            RhythmRepairAction(
                action_id=f"rhythm_repair_{len(actions) + 1:03d}_{category}_{reason_code}",
                order=len(actions) + 1,
                category=category,
                reason_code=reason_code,
                severity="required" if required else "optional",
                command=command,
                rationale=rationale,
                expected_artifacts=expected_artifacts,
            )
        )

    if rhythm_plan is None:
        add(
            "rhythm_plan",
            "missing",
            "artist-portrait rhythm --project <project.yaml>",
            "Generate the canonical rhythm plan before rhythm-aware preview or delivery acceptance.",
            [".artist-portrait/data/rhythm_plan.json", "output/rhythm_report.md"],
            required=profile_requires_rhythm,
        )
    elif rhythm_plan.status == "blocked":
        add(
            "rhythm_plan",
            "blocked",
            "artist-portrait rhythm --project <project.yaml>",
            "Rebuild or inspect the blocked rhythm plan before media QC.",
            [".artist-portrait/data/rhythm_plan.json", "output/rhythm_report.md"],
            required=profile_requires_rhythm,
        )

    if acceptance_profile in {"preview", "delivery"} and not (root / WORKSPACE_DIR / DATA_DIR / "preview_validation.json").exists():
        add(
            "preview",
            "missing",
            "artist-portrait preview --project <project.yaml>",
            "Render and validate preview media before preview-scoped rhythm QC can pass.",
            [".artist-portrait/data/preview_validation.json", "output/preview_lowres.mp4"],
            required=True,
        )
    if delivery_profile and not (root / WORKSPACE_DIR / DATA_DIR / "final_export_validation.json").exists():
        add(
            "final_export",
            "missing",
            "artist-portrait export --project <project.yaml> --profile review_720p",
            "Render and validate final export media before delivery-scoped rhythm QC can pass.",
            [".artist-portrait/data/final_export_validation.json", "output/final_export.mp4"],
            required=True,
        )

    if rhythm_qc is None:
        add(
            "rhythm_qc",
            "missing",
            "artist-portrait rhythm --project <project.yaml> --qc",
            "Generate rhythm media QC after the required preview/final artifacts exist.",
            [".artist-portrait/data/rhythm_media_qc.json", "output/rhythm_media_qc.md"],
            required=profile_requires_rhythm,
        )
    else:
        domain_actions = [
            (rhythm_qc.timeline_freshness, "rhythm_plan", "timeline_stale", "artist-portrait rhythm --project <project.yaml>", "Refresh the rhythm plan against the current timeline.", [".artist-portrait/data/rhythm_plan.json"]),
            (rhythm_qc.bgm_freshness, "bgm", "bgm_stale", "artist-portrait bgm fit --project <project.yaml> --candidate <id>", "Refresh the BGM fit before rebuilding rhythm QC.", [".artist-portrait/data/bgm_fit.json"]),
            (rhythm_qc.preview_binding, "preview", "preview_binding", "artist-portrait preview --project <project.yaml>", "Rebuild preview so it binds to the current rhythm timeline.", [".artist-portrait/data/preview_validation.json", "output/preview_lowres.mp4"]),
            (rhythm_qc.preview_duration_qc, "preview", "preview_duration", "artist-portrait preview --project <project.yaml>", "Rebuild preview to resolve duration drift.", [".artist-portrait/data/preview_validation.json", "output/preview_lowres.mp4"]),
            (rhythm_qc.final_export_binding, "final_export", "final_binding", "artist-portrait export --project <project.yaml> --profile review_720p", "Rebuild final export so it binds to the current rhythm timeline.", [".artist-portrait/data/final_export_validation.json", "output/final_export.mp4"]),
            (rhythm_qc.final_duration_qc, "final_export", "final_duration", "artist-portrait export --project <project.yaml> --profile review_720p", "Rebuild final export to resolve duration drift.", [".artist-portrait/data/final_export_validation.json", "output/final_export.mp4"]),
            (rhythm_qc.audio_expectation_qc, "review", "audio_expectation", "artist-portrait rhythm --project <project.yaml> --qc", "Inspect audio expectations and rerun rhythm QC after upstream media repairs.", [".artist-portrait/data/rhythm_media_qc.json"]),
            (rhythm_qc.ducking_render_qc, "review", "ducking_render", "artist-portrait rhythm --project <project.yaml> --qc", "Inspect ducking render evidence and rerun rhythm QC after upstream media repairs.", [".artist-portrait/data/rhythm_media_qc.json"]),
            (rhythm_qc.ending_render_qc, "review", "ending_render", "artist-portrait rhythm --project <project.yaml> --qc", "Inspect ending render evidence and rerun rhythm QC after upstream media repairs.", [".artist-portrait/data/rhythm_media_qc.json"]),
        ]
        for domain, category, reason, command, rationale, artifacts in domain_actions:
            if domain.status in {"blocked", "warning", "unavailable"}:
                add(category, reason, command, rationale, artifacts, required=profile_requires_rhythm)
        if rhythm_qc.status != "passed":
            add(
                "rhythm_qc",
                "refresh",
                "artist-portrait rhythm --project <project.yaml> --qc",
                "Refresh rhythm media QC after completing upstream rhythm/media actions.",
                [".artist-portrait/data/rhythm_media_qc.json", "output/rhythm_media_qc.md"],
                required=profile_requires_rhythm,
            )

    if acceptance is not None:
        for stage in acceptance.stages:
            if stage.stage_id not in {"rhythm_plan", "rhythm_media_qc", "preview", "final_export"}:
                continue
            stage_required = stage.stage_id in set(acceptance.required_stage_ids)
            for issue in stage.issues:
                category = "rhythm_qc" if stage.stage_id == "rhythm_media_qc" else stage.stage_id
                add(
                    category,
                    f"acceptance_{issue.code}",
                    issue.next_action,
                    issue.detail,
                    stage.artifact_refs,
                    required=stage_required,
                )

    return actions


def _repair_handoff_payload(plan: RhythmRepairPlan) -> dict:
    return {
        "schema_version": plan.schema_version,
        "handoff_id": f"rhythm_repair_handoff_{plan.rhythm_repair_plan_id}",
        "project_id": plan.project_id,
        "rhythm_repair_plan_id": plan.rhythm_repair_plan_id,
        "acceptance_profile": plan.acceptance_profile,
        "task": "Review rhythm repair commands and propose manual execution guidance only.",
        "required_action_count": plan.required_action_count,
        "actions": [action.model_dump(mode="json") for action in plan.actions],
        "forbidden": [
            "do not execute commands",
            "do not render media",
            "do not move edit points",
            "do not select music",
            "do not fit music automatically",
            "do not call models from the CLI",
            "do not access the network",
        ],
    }


def _read_optional(path: Path, model):
    if not path.exists():
        return None
    return model.model_validate_json(path.read_text(encoding="utf-8"))


def _read_intent(path: Path) -> RhythmIntent:
    return RhythmIntent.model_validate_json(path.read_text(encoding="utf-8"))


def _read_candidate(path: Path) -> RhythmAgentCandidate:
    return RhythmAgentCandidate.model_validate_json(path.read_text(encoding="utf-8"))


def _handoff_payload(plan: RhythmPlan) -> dict:
    return {
        "schema_version": plan.schema_version,
        "handoff_id": f"rhythm_handoff_{plan.rhythm_plan_id}",
        "project_id": plan.project_id,
        "timeline_id": plan.timeline_id,
        "rhythm_plan_id": plan.rhythm_plan_id,
        "task": "Review rhythm report and propose textual rhythm recommendations only.",
        "forbidden": [
            "do not move edit points",
            "do not select music",
            "do not render media",
            "do not fabricate BPM or beat grids",
            "do not claim CLI model or network execution",
        ],
        "expected_candidate_schema": "RhythmAgentCandidate",
    }


def _fingerprint(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _metric(metric_id: str, label: str, value: float | str | bool | None, status: str, detail: str) -> RhythmProfileMetric:
    return RhythmProfileMetric(metric_id=metric_id, label=label, value=value, status=status, detail=detail)


def _issue(issue_id: str, domain: str, severity: str, detail: str, next_action: str) -> RhythmIssue:
    return RhythmIssue(issue_id=issue_id, domain=domain, severity=severity, detail=detail, next_action=next_action)


def _domain(domain_id: str, status: str, summary: str, metrics: list[RhythmProfileMetric], issues: list[RhythmIssue]) -> RhythmAuditDomain:
    return RhythmAuditDomain(domain_id=domain_id, status=status, summary=summary, metrics=metrics, issues=issues)
