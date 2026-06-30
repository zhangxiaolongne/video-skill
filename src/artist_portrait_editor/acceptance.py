from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel

from artist_portrait_editor.constants import DATA_DIR, WORKSPACE_DIR
from artist_portrait_editor.media.scanner import read_sources_jsonl
from artist_portrait_editor.models.acceptance import (
    AcceptanceIssue,
    AcceptanceRepairApprovalAction,
    AcceptanceRepairApprovalRecord,
    AcceptanceRepairApprovalRequest,
    AcceptanceRepairExecutionBundle,
    AcceptanceRepairExecutionBundleCommand,
    AcceptanceRepairExecutionDryRun,
    AcceptanceRepairExecutionEvidenceAction,
    AcceptanceRepairExecutionRecord,
    AcceptanceRepairExecutionStep,
    AcceptanceRepairAction,
    AcceptanceRepairPlan,
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
from artist_portrait_editor.models.rhythm import RhythmMediaQcReport, RhythmPlan
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
    profile_blocked = any(stage.status != "passed" for stage in required_stages)
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


def build_acceptance_repair_plan(
    *,
    root: Path,
    report: ProjectAcceptanceReport,
) -> tuple[Path, Path, AcceptanceRepairPlan]:
    plan = create_acceptance_repair_plan(report)
    json_path = root / WORKSPACE_DIR / DATA_DIR / "acceptance_repair_plan.json"
    md_path = root / "output" / "acceptance_repair_plan.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, plan.model_dump(mode="json"))
    md_path.write_text(render_acceptance_repair_plan(plan) + "\n", encoding="utf-8")
    return json_path, md_path, plan


def build_acceptance_repair_approval_request(
    *,
    root: Path,
    plan: AcceptanceRepairPlan,
) -> tuple[Path, Path, AcceptanceRepairApprovalRequest]:
    request = create_acceptance_repair_approval_request(plan)
    json_path = root / WORKSPACE_DIR / DATA_DIR / "acceptance_repair_approval_request.json"
    md_path = root / "output" / "acceptance_repair_approval_request.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, request.model_dump(mode="json"))
    md_path.write_text(render_acceptance_repair_approval_request(request) + "\n", encoding="utf-8")
    return json_path, md_path, request


def import_acceptance_repair_approval_record(
    *,
    root: Path,
    plan: AcceptanceRepairPlan,
    candidate_path: Path,
) -> tuple[Path, Path, AcceptanceRepairApprovalRecord]:
    candidate = AcceptanceRepairApprovalRecord.model_validate_json(
        candidate_path.read_text(encoding="utf-8")
    )
    record = validate_acceptance_repair_approval_record(candidate, plan)
    json_path = root / WORKSPACE_DIR / DATA_DIR / "acceptance_repair_approval_record.json"
    md_path = root / "output" / "acceptance_repair_approval_record.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, record.model_dump(mode="json"))
    md_path.write_text(render_acceptance_repair_approval_record(record) + "\n", encoding="utf-8")
    return json_path, md_path, record


def build_acceptance_repair_execution_dry_run(
    *,
    root: Path,
    plan: AcceptanceRepairPlan,
    approval_record: AcceptanceRepairApprovalRecord,
) -> tuple[Path, Path, AcceptanceRepairExecutionDryRun]:
    dry_run = create_acceptance_repair_execution_dry_run(plan, approval_record)
    json_path = root / WORKSPACE_DIR / DATA_DIR / "acceptance_repair_execution_dry_run.json"
    md_path = root / "output" / "acceptance_repair_execution_dry_run.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, dry_run.model_dump(mode="json"))
    md_path.write_text(render_acceptance_repair_execution_dry_run(dry_run) + "\n", encoding="utf-8")
    return json_path, md_path, dry_run


def build_acceptance_repair_execution_bundle(
    *,
    root: Path,
    plan: AcceptanceRepairPlan,
    dry_run: AcceptanceRepairExecutionDryRun,
) -> tuple[Path, Path, AcceptanceRepairExecutionBundle]:
    bundle = create_acceptance_repair_execution_bundle(plan, dry_run)
    json_path = root / WORKSPACE_DIR / DATA_DIR / "acceptance_repair_execution_bundle.json"
    md_path = root / "output" / "acceptance_repair_execution_bundle.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, bundle.model_dump(mode="json"))
    md_path.write_text(render_acceptance_repair_execution_bundle(bundle) + "\n", encoding="utf-8")
    return json_path, md_path, bundle


def import_acceptance_repair_execution_record(
    *,
    root: Path,
    dry_run: AcceptanceRepairExecutionDryRun,
    candidate_path: Path,
) -> tuple[Path, Path, AcceptanceRepairExecutionRecord]:
    candidate = AcceptanceRepairExecutionRecord.model_validate_json(
        candidate_path.read_text(encoding="utf-8")
    )
    record = validate_acceptance_repair_execution_record(candidate, dry_run)
    json_path = root / WORKSPACE_DIR / DATA_DIR / "acceptance_repair_execution_record.json"
    md_path = root / "output" / "acceptance_repair_execution_record.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, record.model_dump(mode="json"))
    md_path.write_text(render_acceptance_repair_execution_record(record) + "\n", encoding="utf-8")
    return json_path, md_path, record


def create_acceptance_repair_execution_dry_run(
    plan: AcceptanceRepairPlan,
    approval_record: AcceptanceRepairApprovalRecord,
) -> AcceptanceRepairExecutionDryRun:
    issues: list[str] = []
    if approval_record.project_id != plan.project_id:
        issues.append("project_id_mismatch")
    if approval_record.repair_plan_id != plan.repair_plan_id:
        issues.append("repair_plan_id_mismatch")
    if approval_record.acceptance_profile != plan.acceptance_profile:
        issues.append("acceptance_profile_mismatch")
    if not approval_record.valid:
        issues.extend(f"approval_record_invalid:{issue}" for issue in approval_record.issues)
    plan_actions = {action.action_id: action for action in plan.actions}
    steps: list[AcceptanceRepairExecutionStep] = []
    for action in approval_record.actions:
        if action.action_id not in plan_actions:
            issues.append(f"unknown_action:{action.action_id}")
            continue
        if action.decision == "pending":
            issues.append(f"pending_decision:{action.action_id}")
            continue
        plan_action = plan_actions[action.action_id]
        steps.append(
            AcceptanceRepairExecutionStep(
                step_id=f"dry_step_{len(steps) + 1:03d}_{action.action_id}",
                order=len(steps) + 1,
                action_id=action.action_id,
                command=plan_action.command,
                required_for_profile=plan_action.required_for_profile,
                approval_decision=action.decision,
                blocked_reason="dry_run_only_no_commands_executed"
                if action.decision == "approved"
                else "action_rejected",
            )
        )
    approved = sum(step.approval_decision == "approved" for step in steps)
    rejected = sum(step.approval_decision == "rejected" for step in steps)
    key = f"{plan.project_id}:{plan.repair_plan_id}:{approval_record.approval_record_id}:{approved}:{rejected}:{len(issues)}"
    return AcceptanceRepairExecutionDryRun(
        dry_run_id="dry_run_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=plan.project_id,
        repair_plan_id=plan.repair_plan_id,
        approval_record_id=approval_record.approval_record_id,
        acceptance_profile=plan.acceptance_profile,
        approval_record_valid=approval_record.valid and not issues,
        approved_step_count=approved,
        rejected_step_count=rejected,
        blocked=True,
        issues=issues,
        steps=steps,
    )


def create_acceptance_repair_execution_bundle(
    plan: AcceptanceRepairPlan,
    dry_run: AcceptanceRepairExecutionDryRun,
) -> AcceptanceRepairExecutionBundle:
    issues: list[str] = []
    if dry_run.project_id != plan.project_id:
        issues.append("project_id_mismatch")
    if dry_run.repair_plan_id != plan.repair_plan_id:
        issues.append("repair_plan_id_mismatch")
    if dry_run.acceptance_profile != plan.acceptance_profile:
        issues.append("acceptance_profile_mismatch")
    if not dry_run.approval_record_valid:
        issues.append("dry_run_approval_record_invalid")
    if dry_run.commands_executed:
        issues.append("dry_run_claims_commands_executed")
    if dry_run.automatic_repair_performed:
        issues.append("dry_run_claims_automatic_repair")
    action_artifacts = {action.action_id: action.expected_artifacts for action in plan.actions}
    commands: list[AcceptanceRepairExecutionBundleCommand] = []
    for step in dry_run.steps:
        if step.approval_decision != "approved":
            continue
        commands.append(
            AcceptanceRepairExecutionBundleCommand(
                command_id=f"manual_cmd_{len(commands) + 1:03d}_{step.action_id}",
                order=len(commands) + 1,
                step_id=step.step_id,
                action_id=step.action_id,
                command=step.command,
                required_for_profile=step.required_for_profile,
                expected_artifacts=action_artifacts.get(step.action_id, []),
            )
        )
    if not commands:
        issues.append("no_approved_commands")
    key = f"{dry_run.project_id}:{dry_run.repair_plan_id}:{dry_run.approval_record_id}:{dry_run.dry_run_id}:{len(commands)}:{len(issues)}"
    return AcceptanceRepairExecutionBundle(
        execution_bundle_id="execution_bundle_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=dry_run.project_id,
        repair_plan_id=dry_run.repair_plan_id,
        approval_record_id=dry_run.approval_record_id,
        dry_run_id=dry_run.dry_run_id,
        acceptance_profile=dry_run.acceptance_profile,
        dry_run_valid=dry_run.approval_record_valid and not issues,
        command_count=len(commands),
        blocked=bool(issues),
        issues=issues,
        commands=commands,
    )


def validate_acceptance_repair_execution_record(
    candidate: AcceptanceRepairExecutionRecord,
    dry_run: AcceptanceRepairExecutionDryRun,
) -> AcceptanceRepairExecutionRecord:
    issues: list[str] = []
    if candidate.project_id != dry_run.project_id:
        issues.append("project_id_mismatch")
    if candidate.repair_plan_id != dry_run.repair_plan_id:
        issues.append("repair_plan_id_mismatch")
    if candidate.approval_record_id != dry_run.approval_record_id:
        issues.append("approval_record_id_mismatch")
    if candidate.dry_run_id != dry_run.dry_run_id:
        issues.append("dry_run_id_mismatch")
    if candidate.acceptance_profile != dry_run.acceptance_profile:
        issues.append("acceptance_profile_mismatch")
    if candidate.commands_executed_by_cli:
        issues.append("candidate_claims_cli_executed_commands")
    if candidate.automatic_repair_performed:
        issues.append("candidate_claims_automatic_repair")
    steps_by_id = {step.step_id: step for step in dry_run.steps}
    approved_steps = {step.step_id for step in dry_run.steps if step.approval_decision == "approved"}
    seen_steps: set[str] = set()
    completed: list[str] = []
    failed: list[str] = []
    skipped: list[str] = []
    actions: list[AcceptanceRepairExecutionEvidenceAction] = []
    for item in candidate.actions:
        if item.step_id in seen_steps:
            issues.append(f"duplicate_step:{item.step_id}")
        seen_steps.add(item.step_id)
        step = steps_by_id.get(item.step_id)
        if step is None:
            issues.append(f"unknown_step:{item.step_id}")
            action_id = item.action_id
            command = item.command
        else:
            action_id = step.action_id
            command = step.command
            if item.action_id != step.action_id:
                issues.append(f"action_id_mismatch:{item.step_id}")
            if item.command != step.command:
                issues.append(f"command_mismatch:{item.step_id}")
            if step.approval_decision != "approved" and item.status == "succeeded":
                issues.append(f"rejected_step_marked_succeeded:{item.step_id}")
        if item.status == "succeeded":
            completed.append(action_id)
            if item.exit_code not in (0, None):
                issues.append(f"succeeded_step_nonzero_exit:{item.step_id}")
        elif item.status == "failed":
            failed.append(action_id)
            if item.exit_code == 0:
                issues.append(f"failed_step_zero_exit:{item.step_id}")
        else:
            skipped.append(action_id)
        actions.append(
            AcceptanceRepairExecutionEvidenceAction(
                action_id=action_id,
                step_id=item.step_id,
                command=command,
                status=item.status,
                exit_code=item.exit_code,
                artifact_refs=item.artifact_refs,
                notes=item.notes,
            )
        )
    missing_approved = sorted(approved_steps - seen_steps)
    issues.extend(f"missing_approved_step:{step_id}" for step_id in missing_approved)
    key = f"{candidate.project_id}:{candidate.repair_plan_id}:{candidate.dry_run_id}:{','.join(sorted(completed))}:{','.join(sorted(failed))}:{','.join(sorted(skipped))}:{len(issues)}"
    return AcceptanceRepairExecutionRecord(
        execution_record_id="execution_record_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=candidate.project_id,
        repair_plan_id=candidate.repair_plan_id,
        approval_record_id=candidate.approval_record_id,
        dry_run_id=candidate.dry_run_id,
        execution_bundle_id=candidate.execution_bundle_id,
        acceptance_profile=candidate.acceptance_profile,
        valid=not issues,
        completed_action_ids=completed,
        failed_action_ids=failed,
        skipped_action_ids=skipped,
        issue_count=len(issues),
        issues=issues,
        actions=actions,
    )


def create_acceptance_repair_approval_request(plan: AcceptanceRepairPlan) -> AcceptanceRepairApprovalRequest:
    key = f"{plan.project_id}:{plan.repair_plan_id}:request"
    return AcceptanceRepairApprovalRequest(
        approval_request_id="approval_request_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=plan.project_id,
        repair_plan_id=plan.repair_plan_id,
        acceptance_profile=plan.acceptance_profile,
        required_action_count=plan.required_action_count,
        optional_action_count=plan.optional_action_count,
        actions=[
            AcceptanceRepairApprovalAction(
                action_id=action.action_id,
                command=action.command,
                required_for_profile=action.required_for_profile,
                decision="pending",
            )
            for action in plan.actions
        ],
    )


def validate_acceptance_repair_approval_record(
    candidate: AcceptanceRepairApprovalRecord,
    plan: AcceptanceRepairPlan,
) -> AcceptanceRepairApprovalRecord:
    issues: list[str] = []
    plan_actions = {action.action_id: action for action in plan.actions}
    if candidate.project_id != plan.project_id:
        issues.append("project_id_mismatch")
    if candidate.repair_plan_id != plan.repair_plan_id:
        issues.append("repair_plan_id_mismatch")
    if candidate.acceptance_profile != plan.acceptance_profile:
        issues.append("acceptance_profile_mismatch")
    seen: set[str] = set()
    approved: list[str] = []
    rejected: list[str] = []
    actions: list[AcceptanceRepairApprovalAction] = []
    for item in candidate.actions:
        if item.action_id in seen:
            issues.append(f"duplicate_action:{item.action_id}")
        seen.add(item.action_id)
        plan_action = plan_actions.get(item.action_id)
        if plan_action is None:
            issues.append(f"unknown_action:{item.action_id}")
            required = item.required_for_profile
            command = item.command
        else:
            required = plan_action.required_for_profile
            command = plan_action.command
            if item.command != plan_action.command:
                issues.append(f"command_mismatch:{item.action_id}")
        if item.decision == "approved":
            approved.append(item.action_id)
        elif item.decision == "rejected":
            rejected.append(item.action_id)
        else:
            issues.append(f"pending_decision:{item.action_id}")
        actions.append(
            AcceptanceRepairApprovalAction(
                action_id=item.action_id,
                command=command,
                required_for_profile=required,
                decision=item.decision,
                rationale=item.rationale,
            )
        )
    missing_required = [
        action_id
        for action_id, action in plan_actions.items()
        if action.required_for_profile and action_id not in seen
    ]
    issues.extend(f"missing_required_action:{action_id}" for action_id in missing_required)
    key = f"{candidate.project_id}:{candidate.repair_plan_id}:{','.join(sorted(approved))}:{','.join(sorted(rejected))}:{len(issues)}"
    return AcceptanceRepairApprovalRecord(
        approval_record_id="approval_record_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=candidate.project_id,
        repair_plan_id=candidate.repair_plan_id,
        acceptance_profile=candidate.acceptance_profile,
        valid=not issues,
        approved_action_ids=approved,
        rejected_action_ids=rejected,
        issue_count=len(issues),
        issues=issues,
        actions=actions,
    )


def create_acceptance_repair_plan(report: ProjectAcceptanceReport) -> AcceptanceRepairPlan:
    actions: list[AcceptanceRepairAction] = []
    required_ids = set(report.required_stage_ids)
    stages = sorted(
        report.stages,
        key=lambda stage: (
            0 if stage.stage_id in required_ids else 1,
            report.required_stage_ids.index(stage.stage_id)
            if stage.stage_id in required_ids
            else len(report.required_stage_ids),
            stage.stage_id,
        ),
    )
    for stage in stages:
        if stage.status == "passed":
            continue
        stage_required = stage.stage_id in required_ids
        for issue in stage.issues:
            action_id = f"repair_{len(actions) + 1:03d}_{stage.stage_id}_{issue.code}"
            actions.append(
                AcceptanceRepairAction(
                    action_id=action_id,
                    order=len(actions) + 1,
                    stage_id=stage.stage_id,
                    issue_code=issue.code,
                    severity=issue.severity,
                    required_for_profile=stage_required,
                    command=issue.next_action,
                    reason=issue.detail,
                    expected_artifacts=stage.artifact_refs,
                )
            )
    required_actions = [action for action in actions if action.required_for_profile]
    key = ":".join(
        [
            report.project_id,
            report.acceptance_id,
            report.acceptance_profile,
            str(len(actions)),
            "|".join(action.action_id for action in actions),
        ]
    )
    return AcceptanceRepairPlan(
        repair_plan_id="repair_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=report.project_id,
        acceptance_id=report.acceptance_id,
        acceptance_profile=report.acceptance_profile,
        acceptance_status=report.status,
        profile_passed=report.profile_passed,
        action_count=len(actions),
        required_action_count=len(required_actions),
        optional_action_count=len(actions) - len(required_actions),
        blocked_stage_ids=sorted({action.stage_id for action in required_actions}),
        first_required_command=required_actions[0].command if required_actions else None,
        actions=actions,
    )


def render_acceptance_report(report: ProjectAcceptanceReport) -> str:
    lines = [
        "# Project Acceptance Report",
        "",
        "This report audits existing project artifacts. It does not generate proposals, select music, render media, call models, or access the network.",
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
        if stage.issues:
            lines.append("")
            for item in stage.issues:
                lines.append(f"- `{item.code}` `{item.severity}`: {item.detail} Next: `{item.next_action}`")
        lines.append("")
    return "\n".join(lines)


def render_acceptance_repair_plan(plan: AcceptanceRepairPlan) -> str:
    lines = [
        "# Acceptance Repair Plan",
        "",
        "This plan is deterministic guidance only. It does not execute commands, generate proposals, select music, render media, call models, or access the network.",
        "",
        f"- Acceptance profile: `{plan.acceptance_profile}`",
        f"- Acceptance status: `{plan.acceptance_status}`",
        f"- Profile passed: `{str(plan.profile_passed).lower()}`",
        f"- Required actions: `{plan.required_action_count}`",
        f"- Optional actions: `{plan.optional_action_count}`",
        f"- First required command: `{plan.first_required_command or 'none'}`",
        "",
    ]
    if not plan.actions:
        lines.append("No repair actions are required for the current acceptance report.")
        return "\n".join(lines)
    for action in plan.actions:
        lines.extend(
            [
                f"## `{action.action_id}`",
                "",
                f"- Stage: `{action.stage_id}`",
                f"- Issue: `{action.issue_code}` `{action.severity}`",
                f"- Required for profile: `{str(action.required_for_profile).lower()}`",
                f"- Command: `{action.command}`",
                f"- Reason: {action.reason}",
            ]
        )
        if action.expected_artifacts:
            lines.append(
                f"- Expected artifacts: {', '.join(f'`{ref}`' for ref in action.expected_artifacts)}"
            )
        lines.append("")
    return "\n".join(lines)


def render_acceptance_repair_approval_request(request: AcceptanceRepairApprovalRequest) -> str:
    lines = [
        "# Acceptance Repair Approval Request",
        "",
        "This request records repair actions that need explicit user approval. It does not execute commands or mutate project artifacts.",
        "",
        f"- Acceptance profile: `{request.acceptance_profile}`",
        f"- Required actions: `{request.required_action_count}`",
        f"- Optional actions: `{request.optional_action_count}`",
        "",
    ]
    for action in request.actions:
        lines.extend([
            f"## `{action.action_id}`",
            "",
            f"- Required for profile: `{str(action.required_for_profile).lower()}`",
            f"- Decision: `{action.decision}`",
            f"- Command: `{action.command}`",
            "",
        ])
    return "\n".join(lines)


def render_acceptance_repair_approval_record(record: AcceptanceRepairApprovalRecord) -> str:
    lines = [
        "# Acceptance Repair Approval Record",
        "",
        "This record validates explicit user approval decisions. It does not execute commands or mutate project artifacts.",
        "",
        f"- Valid: `{str(record.valid).lower()}`",
        f"- Approved actions: `{len(record.approved_action_ids)}`",
        f"- Rejected actions: `{len(record.rejected_action_ids)}`",
        f"- Issues: `{record.issue_count}`",
        "",
    ]
    for issue in record.issues:
        lines.append(f"- `{issue}`")
    if record.issues:
        lines.append("")
    for action in record.actions:
        lines.extend([
            f"## `{action.action_id}`",
            "",
            f"- Decision: `{action.decision}`",
            f"- Required for profile: `{str(action.required_for_profile).lower()}`",
            f"- Command: `{action.command}`",
            "",
        ])
    return "\n".join(lines)


def render_acceptance_repair_execution_dry_run(dry_run: AcceptanceRepairExecutionDryRun) -> str:
    lines = [
        "# Acceptance Repair Execution Dry Run",
        "",
        "This dry run enumerates approved repair commands without executing them.",
        "",
        f"- Acceptance profile: `{dry_run.acceptance_profile}`",
        f"- Approval record valid: `{str(dry_run.approval_record_valid).lower()}`",
        f"- Approved steps: `{dry_run.approved_step_count}`",
        f"- Rejected steps: `{dry_run.rejected_step_count}`",
        f"- Commands executed: `{str(dry_run.commands_executed).lower()}`",
        f"- Automatic repair performed: `{str(dry_run.automatic_repair_performed).lower()}`",
        "",
    ]
    for issue in dry_run.issues:
        lines.append(f"- `{issue}`")
    if dry_run.issues:
        lines.append("")
    for step in dry_run.steps:
        lines.extend([
            f"## `{step.step_id}`",
            "",
            f"- Action: `{step.action_id}`",
            f"- Decision: `{step.approval_decision}`",
            f"- Would execute: `{str(step.would_execute).lower()}`",
            f"- Command: `{step.command}`",
            f"- Blocked reason: `{step.blocked_reason or 'none'}`",
            "",
        ])
    return "\n".join(lines)


def render_acceptance_repair_execution_bundle(bundle: AcceptanceRepairExecutionBundle) -> str:
    lines = [
        "# Acceptance Repair Execution Bundle",
        "",
        "This bundle is a manual handoff. The CLI did not execute commands, run repairs, render media, call models, or access the network.",
        "",
        f"- Acceptance profile: `{bundle.acceptance_profile}`",
        f"- Dry run valid: `{str(bundle.dry_run_valid).lower()}`",
        f"- Blocked: `{str(bundle.blocked).lower()}`",
        f"- Commands: `{bundle.command_count}`",
        f"- Commands executed by CLI: `{str(bundle.commands_executed_by_cli).lower()}`",
        f"- Automatic repair performed: `{str(bundle.automatic_repair_performed).lower()}`",
        "",
    ]
    for issue in bundle.issues:
        lines.append(f"- `{issue}`")
    if bundle.issues:
        lines.append("")
    for command in bundle.commands:
        lines.extend([
            f"## `{command.command_id}`",
            "",
            f"- Step: `{command.step_id}`",
            f"- Action: `{command.action_id}`",
            f"- Required for profile: `{str(command.required_for_profile).lower()}`",
            f"- Manual execution required: `{str(command.manual_execution_required).lower()}`",
            f"- Executable by CLI: `{str(command.executable_by_cli).lower()}`",
            f"- Command: `{command.command}`",
        ])
        if command.expected_artifacts:
            lines.append(
                f"- Expected artifacts: {', '.join(f'`{ref}`' for ref in command.expected_artifacts)}"
            )
        lines.append("")
    return "\n".join(lines)


def render_acceptance_repair_execution_record(record: AcceptanceRepairExecutionRecord) -> str:
    lines = [
        "# Acceptance Repair Execution Record",
        "",
        "This record validates explicit external execution evidence. It does not mark acceptance passed, execute commands, render media, call models, or access the network.",
        "",
        f"- Valid: `{str(record.valid).lower()}`",
        f"- Completed actions: `{len(record.completed_action_ids)}`",
        f"- Failed actions: `{len(record.failed_action_ids)}`",
        f"- Skipped actions: `{len(record.skipped_action_ids)}`",
        f"- Issues: `{record.issue_count}`",
        f"- Commands executed by CLI: `{str(record.commands_executed_by_cli).lower()}`",
        f"- Automatic repair performed: `{str(record.automatic_repair_performed).lower()}`",
        "",
    ]
    for issue in record.issues:
        lines.append(f"- `{issue}`")
    if record.issues:
        lines.append("")
    for action in record.actions:
        lines.extend([
            f"## `{action.step_id}`",
            "",
            f"- Action: `{action.action_id}`",
            f"- Status: `{action.status}`",
            f"- Exit code: `{action.exit_code if action.exit_code is not None else 'unknown'}`",
            f"- Command: `{action.command}`",
        ])
        if action.artifact_refs:
            lines.append(
                f"- Artifact refs: {', '.join(f'`{ref}`' for ref in action.artifact_refs)}"
            )
        if action.notes:
            lines.append(f"- Notes: {action.notes}")
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
        return core + ["rhythm_plan", "preview", "rhythm_media_qc"]
    if profile == "delivery":
        return core + ["rhythm_plan", "preview", "final_export", "rhythm_media_qc"]
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
    if plan and plan.status == "warning":
        issues.append(_issue("rhythm_plan_warning", "warning", "rhythm plan has warnings", "inspect output/rhythm_report.md"))
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
