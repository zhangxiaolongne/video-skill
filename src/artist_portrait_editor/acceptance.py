from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel

from artist_portrait_editor.constants import DATA_DIR, WORKSPACE_DIR
from artist_portrait_editor.media.scanner import read_sources_jsonl
from artist_portrait_editor.models.acceptance import (
    AcceptanceIssue,
    AcceptanceStage,
    ProjectAcceptanceReport,
)
from artist_portrait_editor.models.analysis import AnalysisRecord
from artist_portrait_editor.models.bgm import BgmFitPlan
from artist_portrait_editor.models.bgm_recommendation import BgmRecommendationFitReview
from artist_portrait_editor.models.clip import ClipRecord
from artist_portrait_editor.models.cut_review import CutReviewReport
from artist_portrait_editor.models.final_export import FinalExportValidationReport
from artist_portrait_editor.models.preview import PreviewValidationReport
from artist_portrait_editor.models.proposal import ProposalSet
from artist_portrait_editor.models.proposal_validation import ProposalValidationReport
from artist_portrait_editor.models.rhythm import RhythmMediaQcReport, RhythmPlan
from artist_portrait_editor.models.sound import SoundDecision
from artist_portrait_editor.models.state import ProjectState, StepStatus
from artist_portrait_editor.models.timeline import TimelineDraft, TimelineValidationReport
from artist_portrait_editor.run_records import write_json


ACCEPTANCE_PROFILES = {"standard", "core", "preview", "delivery"}


def build_project_acceptance_report(
    *,
    root: Path,
    project_id: str,
    state: ProjectState | None,
    profile: str = "standard",
) -> tuple[Path, Path, ProjectAcceptanceReport]:
    if profile not in ACCEPTANCE_PROFILES:
        raise ValueError(f"unsupported acceptance profile: {profile}")
    stages = [
        _state_stage(state),
        _jsonl_stage(root, "source_scan", ".artist-portrait/data/sources.jsonl", None, True, True, "artist-portrait scan --project <project.yaml>"),
        _jsonl_stage(root, "segmentation", ".artist-portrait/data/clips.jsonl", ClipRecord, True, True, "artist-portrait segment --project <project.yaml>"),
        _jsonl_stage(root, "evidence_analysis", ".artist-portrait/data/analysis.jsonl", AnalysisRecord, True, True, "artist-portrait analyze --project <project.yaml>"),
        _proposal_stage(root, project_id),
        _timeline_stage(root, project_id),
        _sound_stage(root, project_id),
        _cut_review_stage(root, project_id),
        _bgm_stage(root, project_id),
        _rhythm_plan_stage(root, project_id),
        _preview_stage(root),
        _final_export_stage(root),
        _rhythm_media_qc_stage(root, project_id),
        _forbidden_capability_stage(root),
    ]
    errors = sum(1 for stage in stages for item in stage.issues if item.severity == "error")
    warnings = sum(1 for stage in stages for item in stage.issues if item.severity == "warning")
    failed = sum(stage.status == "failed" for stage in stages)
    warning_stages = sum(stage.status == "warning" for stage in stages)
    passed = sum(stage.status == "passed" for stage in stages)
    core_ready = not any(stage.required_for_core and stage.status == "failed" for stage in stages)
    preview_ready = _stage_status(stages, "preview") == "passed"
    final_ready = _stage_status(stages, "final_export") == "passed"
    required_stage_ids = _required_stage_ids(profile)
    required_stages = [stage for stage in stages if stage.stage_id in required_stage_ids]
    profile_blocked = any(_required_stage_blocks_profile(stage) for stage in required_stages)
    if profile == "standard":
        profile_passed = core_ready
        status = "failed" if failed and not core_ready else "warning" if warnings or failed else "passed"
    else:
        profile_passed = not profile_blocked
        status = "failed" if profile_blocked else "passed"
    score = round(passed / len(stages), 3) if stages else 0.0
    key = ":".join(
        [
            project_id,
            profile,
            str(passed),
            str(warning_stages),
            str(failed),
            str(errors),
            str(warnings),
        ]
    )
    report = ProjectAcceptanceReport(
        acceptance_id="accept_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=project_id,
        acceptance_profile=profile,
        status=status,
        profile_passed=profile_passed,
        required_stage_ids=required_stage_ids,
        core_ready=core_ready,
        preview_ready=preview_ready,
        final_export_ready=final_ready,
        acceptance_score=score,
        stage_count=len(stages),
        passed_stage_count=passed,
        warning_stage_count=warning_stages,
        failed_stage_count=failed,
        issue_count=errors + warnings,
        error_count=errors,
        warning_count=warnings,
        stages=stages,
    )
    json_path = root / WORKSPACE_DIR / DATA_DIR / "acceptance_report.json"
    md_path = root / "output" / "acceptance_report.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, report.model_dump(mode="json"))
    md_path.write_text(render_acceptance_report(report) + "\n", encoding="utf-8")
    return json_path, md_path, report


def render_acceptance_report(report: ProjectAcceptanceReport) -> str:
    lines = [
        "# Project Acceptance Report",
        "",
        "This report audits existing artifacts. It does not execute repairs, render media, call models, or access the network.",
        "",
        f"- Status: `{report.status}`",
        f"- Acceptance profile: `{report.acceptance_profile}`",
        f"- Profile passed: `{str(report.profile_passed).lower()}`",
        f"- Required stages: {', '.join(f'`{stage_id}`' for stage_id in report.required_stage_ids)}",
        f"- Core ready: `{str(report.core_ready).lower()}`",
        f"- Preview ready: `{str(report.preview_ready).lower()}`",
        f"- Final export ready: `{str(report.final_export_ready).lower()}`",
        f"- Acceptance score: `{report.acceptance_score:.3f}`",
        f"- Issues: `{report.issue_count}`",
        "",
    ]
    for stage in report.stages:
        lines.extend([
            f"## `{stage.stage_id}`",
            "",
            f"- Status: `{stage.status}`",
            f"- Core required: `{str(stage.required_for_core).lower()}`",
            f"- Delivery required: `{str(stage.required_for_delivery).lower()}`",
            f"- Profile required: `{str(stage.stage_id in report.required_stage_ids).lower()}`",
        ])
        if stage.artifact_refs:
            lines.append(f"- Artifacts: {', '.join(f'`{ref}`' for ref in stage.artifact_refs)}")
        for issue in stage.issues:
            lines.append(f"- `{issue.code}` `{issue.severity}`: {issue.detail} Next: `{issue.next_action}`")
        lines.append("")
    return "\n".join(lines)


def _stage_status(stages: list[AcceptanceStage], stage_id: str) -> str:
    return next((stage.status for stage in stages if stage.stage_id == stage_id), "failed")


def _required_stage_ids(profile: str) -> list[str]:
    core = [
        "workspace_state",
        "source_scan",
        "segmentation",
        "evidence_analysis",
        "proposal",
        "timeline",
        "forbidden_capability_audit",
    ]
    if profile in {"standard", "core"}:
        return core
    if profile == "preview":
        return core + ["sound_decision", "rhythm_plan", "preview", "rhythm_media_qc", "cut_review"]
    if profile == "delivery":
        return core + ["sound_decision", "rhythm_plan", "preview", "final_export", "rhythm_media_qc", "cut_review"]
    raise ValueError(f"unsupported acceptance profile: {profile}")


def _state_stage(state: ProjectState | None) -> AcceptanceStage:
    if state is None:
        return _stage("workspace_state", "failed", True, True, [], [_issue("state_missing", "error", "workspace state is missing", "artist-portrait init --project <project.yaml>")])
    init_status = state.steps.get("init")
    if init_status is None or init_status.status not in {StepStatus.completed, StepStatus.completed_with_warnings}:
        return _stage("workspace_state", "failed", True, True, [".artist-portrait/state.json"], [_issue("init_not_completed", "error", "init has not completed", "artist-portrait init --project <project.yaml>")])
    return _stage("workspace_state", "passed", True, True, [".artist-portrait/state.json"], [], {"overall_status": state.overall_status.value})


def _jsonl_stage(root: Path, stage_id: str, ref: str, model: type[BaseModel] | None, core: bool, delivery: bool, next_action: str) -> AcceptanceStage:
    path = root / ref
    if not path.exists():
        return _stage(stage_id, "failed", core, delivery, [ref], [_issue(f"{stage_id}_missing", "error", f"{ref} is missing", next_action)])
    try:
        if model is None:
            count = len(read_sources_jsonl(path))
        else:
            count = _validate_jsonl(path, model)
    except Exception as exc:
        return _stage(stage_id, "failed", core, delivery, [ref], [_issue(f"{stage_id}_invalid", "error", f"{ref} is invalid: {exc}", next_action)])
    if count == 0:
        return _stage(stage_id, "failed", core, delivery, [ref], [_issue(f"{stage_id}_empty", "error", f"{ref} has no records", next_action)])
    return _stage(stage_id, "passed", core, delivery, [ref], [], {"record_count": count})


def _proposal_stage(root: Path, project_id: str) -> AcceptanceStage:
    refs = [".artist-portrait/data/proposals.json", ".artist-portrait/data/proposal_validation.json", "output/proposal_review.md"]
    issues = []
    proposals = _load_json_model(root / refs[0], ProposalSet, refs[0], issues, "artist-portrait propose --project <project.yaml> --agent-output <candidate.json>")
    validation = _load_json_model(root / refs[1], ProposalValidationReport, refs[1], issues, "artist-portrait review --project <project.yaml> --scope proposal")
    if proposals and proposals.project_id != project_id:
        issues.append(_issue("proposal_project_mismatch", "error", "proposal project_id mismatches project", "rerun proposal import"))
    if validation and validation.error_count:
        issues.append(_issue("proposal_validation_failed", "error", "proposal validation has errors", "artist-portrait review --project <project.yaml> --scope proposal"))
    return _stage("proposal", _status_from_issues(issues), True, True, refs, issues, {"proposal_count": len(proposals.proposals) if proposals else 0})


def _timeline_stage(root: Path, project_id: str) -> AcceptanceStage:
    refs = ["output/timeline_draft.json", ".artist-portrait/data/timeline_validation.json", "output/timeline_review.md"]
    issues = []
    timeline = _load_json_model(root / refs[0], TimelineDraft, refs[0], issues, "artist-portrait timeline --project <project.yaml> --proposal <id>")
    validation = _load_json_model(root / refs[1], TimelineValidationReport, refs[1], issues, "artist-portrait review --project <project.yaml> --scope timeline")
    if timeline and timeline.project_id != project_id:
        issues.append(_issue("timeline_project_mismatch", "error", "timeline project_id mismatches project", "rerun timeline"))
    if validation and not validation.valid:
        issues.append(_issue("timeline_validation_failed", "error", "timeline validation has errors", "artist-portrait review --project <project.yaml> --scope timeline"))
    return _stage("timeline", _status_from_issues(issues), True, True, refs, issues, {"segment_count": len(timeline.segments) if timeline else 0})


def _bgm_stage(root: Path, project_id: str) -> AcceptanceStage:
    refs = [".artist-portrait/data/bgm_fit.json", ".artist-portrait/data/bgm_fit_review.json", "output/bgm_fit_review.md"]
    issues = []
    fit = _load_json_model(root / refs[0], BgmFitPlan, refs[0], issues, "artist-portrait bgm fit --project <project.yaml> --candidate <id>")
    review = _load_json_model(root / refs[1], BgmRecommendationFitReview, refs[1], issues, "artist-portrait bgm review --project <project.yaml>")
    if fit and fit.project_id != project_id:
        issues.append(_issue("bgm_fit_project_mismatch", "error", "BGM fit project_id mismatches project", "rerun BGM fit"))
    if review and review.status == "failed":
        issues.append(_issue("bgm_fit_review_failed", "error", "BGM fit review failed", "artist-portrait bgm review --project <project.yaml>"))
    if review and review.status == "warning":
        issues.append(_issue("bgm_fit_review_warning", "warning", "BGM fit review has warnings", "inspect output/bgm_fit_review.md"))
    return _stage("bgm", _status_from_issues(issues), False, True, refs, issues, {"candidate_id": fit.music_candidate_id if fit else None})


def _sound_stage(root: Path, project_id: str) -> AcceptanceStage:
    refs = [".artist-portrait/data/sound_decision.json", "output/sound_decision.md"]
    issues = []
    decision = _load_json_model(
        root / refs[0],
        SoundDecision,
        refs[0],
        issues,
        "artist-portrait sound --project <project.yaml>",
    )
    if decision and decision.project_id != project_id:
        issues.append(_issue("sound_decision_project_mismatch", "error", "sound decision project_id mismatches project", "artist-portrait sound --project <project.yaml>"))
    if decision and decision.status == "blocked":
        issues.append(_issue("sound_decision_blocked", "error", "sound decision is blocked", "inspect output/sound_decision.md and rerun sound"))
    if issues and all(item.code.endswith("_missing") for item in issues):
        issues = [_issue("sound_decision_missing", "warning", "sound decision has not been generated", "artist-portrait sound --project <project.yaml>")]
    return _stage(
        "sound_decision",
        _status_from_issues(issues),
        False,
        True,
        refs,
        issues,
        {
            "status": decision.status if decision else "missing",
            "strategy": decision.selected_strategy if decision else None,
            "bgm_candidate_count": decision.bgm_candidate_count if decision else 0,
        },
    )


def _cut_review_stage(root: Path, project_id: str) -> AcceptanceStage:
    refs = [".artist-portrait/data/cut_review.json", "output/cut_review.md"]
    issues = []
    review = _load_json_model(
        root / refs[0],
        CutReviewReport,
        refs[0],
        issues,
        "artist-portrait cut-review --project <project.yaml>",
    )
    if review and review.project_id != project_id:
        issues.append(_issue("cut_review_project_mismatch", "error", "cut review project_id mismatches project", "artist-portrait cut-review --project <project.yaml>"))
    if review and review.status == "blocked":
        issues.append(_issue("cut_review_blocked", "error", "cut review is blocked", "inspect output/cut_review.md and rerun cut-review"))
    if issues and all(item.code.endswith("_missing") for item in issues):
        issues = [_issue("cut_review_missing", "warning", "cut review has not been generated", "artist-portrait cut-review --project <project.yaml>")]
    return _stage(
        "cut_review",
        _status_from_issues(issues),
        False,
        True,
        refs,
        issues,
        {
            "status": review.status if review else "missing",
            "media_scope": review.reviewed_media_scope if review else None,
            "second_pass_action_count": review.second_pass_action_count if review else 0,
        },
    )


def _rhythm_plan_stage(root: Path, project_id: str) -> AcceptanceStage:
    refs = [
        ".artist-portrait/data/rhythm_plan.json",
        "output/rhythm_report.md",
        "output/rhythm_agent_handoff.json",
    ]
    issues = []
    plan = _load_json_model(
        root / refs[0],
        RhythmPlan,
        refs[0],
        issues,
        "artist-portrait rhythm --project <project.yaml>",
    )
    timeline_path = root / "output" / "timeline_draft.json"
    timeline = (
        TimelineDraft.model_validate_json(timeline_path.read_text(encoding="utf-8"))
        if timeline_path.exists()
        else None
    )
    if plan and plan.project_id != project_id:
        issues.append(_issue("rhythm_plan_project_mismatch", "error", "rhythm plan project_id mismatches project", "artist-portrait rhythm --project <project.yaml>"))
    if plan and plan.status == "blocked":
        issues.append(_issue("rhythm_plan_blocked", "error", "rhythm plan is blocked", "inspect output/rhythm_report.md and rerun rhythm"))
    if plan and timeline:
        current_fingerprint = _fingerprint(timeline_path)
        if plan.timeline_id != timeline.timeline_id:
            issues.append(_issue("rhythm_plan_timeline_mismatch", "error", "rhythm plan timeline_id mismatches current timeline", "artist-portrait rhythm --project <project.yaml>"))
        if plan.timeline_fingerprint != current_fingerprint:
            issues.append(_issue("rhythm_plan_timeline_stale", "error", "rhythm plan timeline fingerprint is stale", "artist-portrait rhythm --project <project.yaml>"))
    if issues and all(item.code.endswith("_missing") for item in issues):
        issues = [_issue("rhythm_plan_missing", "warning", "rhythm plan has not been generated", "artist-portrait rhythm --project <project.yaml>")]
    return _stage(
        "rhythm_plan",
        _status_from_issues(issues),
        False,
        True,
        refs,
        issues,
        {
            "rhythm_plan_id": plan.rhythm_plan_id if plan else None,
            "status": plan.status if plan else "missing",
            "timeline_id": plan.timeline_id if plan else None,
        },
    )


def _preview_stage(root: Path) -> AcceptanceStage:
    refs = [".artist-portrait/data/preview_manifest.json", ".artist-portrait/data/preview_validation.json", "output/preview_lowres.mp4", "output/preview_review.md"]
    issues = []
    validation = _load_json_model(root / refs[1], PreviewValidationReport, refs[1], issues, "artist-portrait preview --project <project.yaml>")
    if validation and not validation.valid:
        issues.append(_issue("preview_validation_failed", "error", "preview validation failed", "artist-portrait review --project <project.yaml> --scope preview"))
    if issues and all(item.code.endswith("_missing") for item in issues):
        issues = [_issue("preview_missing", "warning", "preview has not been rendered", "artist-portrait preview --project <project.yaml>")]
    return _stage("preview", _status_from_issues(issues), False, True, refs, issues, {"valid": validation.valid if validation else False})


def _final_export_stage(root: Path) -> AcceptanceStage:
    refs = [".artist-portrait/data/final_export_manifest.json", ".artist-portrait/data/final_export_validation.json", "output/final_export.mp4", "output/final_export_review.md"]
    issues = []
    validation = _load_json_model(root / refs[1], FinalExportValidationReport, refs[1], issues, "artist-portrait export --project <project.yaml> --profile review_720p")
    if validation and not validation.valid:
        issues.append(_issue("final_export_validation_failed", "error", "final export validation failed", "artist-portrait review --project <project.yaml> --scope final_export"))
    if issues and all(item.code.endswith("_missing") for item in issues):
        issues = [_issue("final_export_missing", "warning", "final export has not been rendered", "artist-portrait export --project <project.yaml> --profile review_720p")]
    return _stage("final_export", _status_from_issues(issues), False, True, refs, issues, {"valid": validation.valid if validation else False})


def _rhythm_media_qc_stage(root: Path, project_id: str) -> AcceptanceStage:
    refs = [
        ".artist-portrait/data/rhythm_media_qc.json",
        "output/rhythm_media_qc.md",
        "output/rhythm_media_qc_handoff.json",
    ]
    issues = []
    report = _load_json_model(
        root / refs[0],
        RhythmMediaQcReport,
        refs[0],
        issues,
        "artist-portrait rhythm --project <project.yaml> --qc",
    )
    plan_path = root / WORKSPACE_DIR / DATA_DIR / "rhythm_plan.json"
    plan = (
        RhythmPlan.model_validate_json(plan_path.read_text(encoding="utf-8"))
        if plan_path.exists()
        else None
    )
    if report and report.project_id != project_id:
        issues.append(_issue("rhythm_media_qc_project_mismatch", "error", "rhythm media QC project_id mismatches project", "artist-portrait rhythm --project <project.yaml> --qc"))
    if report and plan:
        if report.rhythm_plan_id != plan.rhythm_plan_id:
            issues.append(_issue("rhythm_media_qc_plan_mismatch", "error", "rhythm media QC is bound to a different rhythm plan", "artist-portrait rhythm --project <project.yaml> --qc"))
        if report.rhythm_plan_fingerprint != _fingerprint(plan_path):
            issues.append(_issue("rhythm_media_qc_plan_stale", "error", "rhythm media QC rhythm-plan fingerprint is stale", "artist-portrait rhythm --project <project.yaml> --qc"))
    if report:
        preview_validation_path = root / WORKSPACE_DIR / DATA_DIR / "preview_validation.json"
        final_validation_path = root / WORKSPACE_DIR / DATA_DIR / "final_export_validation.json"
        preview_exists = preview_validation_path.exists()
        final_exists = final_validation_path.exists()
        if report.timeline_freshness.status != "passed":
            issues.append(_issue("rhythm_media_qc_timeline_not_current", "error", "rhythm media QC reports stale or missing timeline evidence", "artist-portrait rhythm --project <project.yaml> --qc"))
        if report.bgm_freshness.status != "passed":
            issues.append(_issue("rhythm_media_qc_bgm_not_current", "error", "rhythm media QC reports stale BGM fit evidence", "artist-portrait rhythm --project <project.yaml> --qc"))
        if preview_exists:
            for domain in (report.preview_binding, report.preview_duration_qc):
                if domain.status != "passed":
                    issues.append(_issue(f"rhythm_media_qc_{domain.domain_id}", "error", f"rhythm media QC {domain.domain_id} is {domain.status}", "artist-portrait rhythm --project <project.yaml> --qc"))
        if final_exists:
            for domain in (report.final_export_binding, report.final_duration_qc):
                if domain.status != "passed":
                    issues.append(_issue(f"rhythm_media_qc_{domain.domain_id}", "error", f"rhythm media QC {domain.domain_id} is {domain.status}", "artist-portrait rhythm --project <project.yaml> --qc"))
        if preview_exists or final_exists:
            for domain in (report.audio_expectation_qc, report.ducking_render_qc, report.ending_render_qc):
                if domain.status == "blocked":
                    issues.append(_issue(f"rhythm_media_qc_{domain.domain_id}", "error", f"rhythm media QC {domain.domain_id} is blocked", "artist-portrait rhythm --project <project.yaml> --qc"))
    if report:
        forbidden = {
            "preview_rendered_by_qc": report.preview_rendered_by_qc,
            "final_export_rendered_by_qc": report.final_export_rendered_by_qc,
            "edit_points_moved": report.edit_points_moved,
            "automatic_music_selection": report.automatic_music_selection,
            "model_call_performed_by_cli": report.model_call_performed_by_cli,
            "network_performed": report.network_performed,
        }
        for key, value in forbidden.items():
            if value:
                issues.append(_issue(f"rhythm_media_qc_forbidden_{key}", "error", f"rhythm media QC reports forbidden {key}=true", "remove forbidden artifact and rerun rhythm --qc"))
    if issues and all(item.code.endswith("_missing") for item in issues):
        issues = [_issue("rhythm_media_qc_missing", "warning", "rhythm media QC has not been generated", "artist-portrait rhythm --project <project.yaml> --qc")]
    return _stage(
        "rhythm_media_qc",
        _status_from_issues(issues),
        False,
        True,
        refs,
        issues,
        {
            "rhythm_qc_id": report.rhythm_qc_id if report else None,
            "status": report.status if report else "missing",
            "rhythm_plan_id": report.rhythm_plan_id if report else None,
            "error_count": report.error_count if report else None,
            "warning_count": report.warning_count if report else None,
        },
    )


def _forbidden_capability_stage(root: Path) -> AcceptanceStage:
    issues = []
    for ref, model in (
        (".artist-portrait/data/preview_manifest.json", None),
        (".artist-portrait/data/final_export_manifest.json", None),
        (".artist-portrait/data/bgm_fit_review.json", BgmRecommendationFitReview),
        (".artist-portrait/data/rhythm_plan.json", RhythmPlan),
        (".artist-portrait/data/rhythm_media_qc.json", RhythmMediaQcReport),
    ):
        path = root / ref
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for key in ("network_performed", "model_call_performed", "model_call_performed_by_cli", "automatic_music_selection"):
            if payload.get(key) is True:
                issues.append(_issue(f"forbidden_{key}", "error", f"{ref} reports {key}=true", "remove forbidden capability artifact and rerun the allowed command"))
        if model is not None:
            model.model_validate(payload)
    return _stage("forbidden_capability_audit", _status_from_issues(issues), True, True, [], issues)


def _validate_jsonl(path: Path, model: type[BaseModel]) -> int:
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            model.model_validate(json.loads(line))
            count += 1
    return count


def _load_json_model(path: Path, model: type[BaseModel], ref: str, issues: list[AcceptanceIssue], next_action: str):
    if not path.exists():
        issues.append(_issue(f"{Path(ref).stem}_missing", "error", f"{ref} is missing", next_action))
        return None
    try:
        return model.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as exc:
        issues.append(_issue(f"{Path(ref).stem}_invalid", "error", f"{ref} is invalid: {exc}", next_action))
        return None


def _stage(stage_id: str, status: str, core: bool, delivery: bool, refs: list[str], issues: list[AcceptanceIssue], summary: dict | None = None) -> AcceptanceStage:
    return AcceptanceStage(stage_id=stage_id, status=status, required_for_core=core, required_for_delivery=delivery, artifact_refs=refs, evidence_summary=summary or {}, issues=issues)


def _required_stage_blocks_profile(stage: AcceptanceStage) -> bool:
    if stage.status == "failed":
        return True
    return any(item.code.endswith("_missing") for item in stage.issues)


def _issue(code: str, severity: str, detail: str, next_action: str) -> AcceptanceIssue:
    return AcceptanceIssue(code=code, severity=severity, detail=detail, next_action=next_action)


def _status_from_issues(issues: list[AcceptanceIssue]) -> str:
    if any(item.severity == "error" for item in issues):
        return "failed"
    if issues:
        return "warning"
    return "passed"


def _fingerprint(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
