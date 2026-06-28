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
from artist_portrait_editor.models.final_export import FinalExportValidationReport
from artist_portrait_editor.models.preview import PreviewValidationReport
from artist_portrait_editor.models.proposal import ProposalSet
from artist_portrait_editor.models.proposal_validation import ProposalValidationReport
from artist_portrait_editor.models.state import ProjectState, StepStatus
from artist_portrait_editor.models.timeline import TimelineDraft, TimelineValidationReport
from artist_portrait_editor.run_records import write_json


def build_project_acceptance_report(*, root: Path, project_id: str, state: ProjectState | None) -> tuple[Path, Path, ProjectAcceptanceReport]:
    stages = [
        _state_stage(state),
        _jsonl_stage(root, "source_scan", ".artist-portrait/data/sources.jsonl", None, True, True, "artist-portrait scan --project <project.yaml>"),
        _jsonl_stage(root, "segmentation", ".artist-portrait/data/clips.jsonl", ClipRecord, True, True, "artist-portrait segment --project <project.yaml>"),
        _jsonl_stage(root, "evidence_analysis", ".artist-portrait/data/analysis.jsonl", AnalysisRecord, True, True, "artist-portrait analyze --project <project.yaml>"),
        _proposal_stage(root, project_id),
        _timeline_stage(root, project_id),
        _bgm_stage(root, project_id),
        _preview_stage(root),
        _final_export_stage(root),
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
    status = "failed" if failed and not core_ready else "warning" if warnings or failed else "passed"
    score = round(passed / len(stages), 3) if stages else 0.0
    key = ":".join(
        [
            project_id,
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
        status=status,
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
        "This report audits existing project artifacts. It does not generate proposals, select music, render media, call models, or access the network.",
        "",
        f"- Status: `{report.status}`",
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
        ])
        if stage.artifact_refs:
            lines.append(f"- Artifacts: {', '.join(f'`{ref}`' for ref in stage.artifact_refs)}")
        if stage.issues:
            lines.append("")
            for item in stage.issues:
                lines.append(f"- `{item.code}` `{item.severity}`: {item.detail} Next: `{item.next_action}`")
        lines.append("")
    return "\n".join(lines)


def _stage_status(stages: list[AcceptanceStage], stage_id: str) -> str:
    return next((stage.status for stage in stages if stage.stage_id == stage_id), "failed")


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


def _forbidden_capability_stage(root: Path) -> AcceptanceStage:
    issues = []
    for ref, model in (
        (".artist-portrait/data/preview_manifest.json", None),
        (".artist-portrait/data/final_export_manifest.json", None),
        (".artist-portrait/data/bgm_fit_review.json", BgmRecommendationFitReview),
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


def _issue(code: str, severity: str, detail: str, next_action: str) -> AcceptanceIssue:
    return AcceptanceIssue(code=code, severity=severity, detail=detail, next_action=next_action)


def _status_from_issues(issues: list[AcceptanceIssue]) -> str:
    if any(item.severity == "error" for item in issues):
        return "failed"
    if issues:
        return "warning"
    return "passed"
