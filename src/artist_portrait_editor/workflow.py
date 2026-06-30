from __future__ import annotations

import hashlib
from pathlib import Path

from artist_portrait_editor.constants import DATA_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.acceptance import ProjectAcceptanceReport
from artist_portrait_editor.models.rhythm import RhythmRepairPlan
from artist_portrait_editor.models.state import ProjectState, StepStatus
from artist_portrait_editor.models.workflow import (
    WorkflowExecutionRecord,
    WorkflowExecutionReview,
    WorkflowExecutionStepReview,
    WorkflowPlan,
    WorkflowRepairAction,
    WorkflowRepairApprovalRecord,
    WorkflowRepairApprovalRequest,
    WorkflowRepairDryRun,
    WorkflowRepairDryRunStep,
    WorkflowRepairExecutionRecord,
    WorkflowRepairExecutionReview,
    WorkflowRepairExecutionActionReview,
    WorkflowRepairRefreshPlan,
    WorkflowRepairRefreshStep,
    WorkflowRepairPlan,
    WorkflowStep,
)
from artist_portrait_editor.run_records import write_json


WORKFLOW_TARGETS = {"core", "preview", "delivery"}


class WorkflowExecutionReviewError(RuntimeError):
    pass


def build_workflow_plan(
    *,
    root: Path,
    project_id: str,
    target: str,
    state: ProjectState | None,
) -> tuple[Path, Path, Path, WorkflowPlan]:
    if target not in WORKFLOW_TARGETS:
        raise ValueError(f"unsupported workflow target: {target}")
    acceptance = _read_optional(root / WORKSPACE_DIR / DATA_DIR / "acceptance_report.json", ProjectAcceptanceReport)
    rhythm_repair = _read_optional(root / WORKSPACE_DIR / DATA_DIR / "rhythm_repair_plan.json", RhythmRepairPlan)
    steps = _workflow_steps(root, target, state, acceptance, rhythm_repair)
    next_step = next((step for step in steps if step.status in {"next", "blocked"}), None)
    completed = sum(step.status == "done" for step in steps)
    blocked = sum(step.status == "blocked" for step in steps)
    remaining = sum(step.status in {"next", "pending", "blocked"} for step in steps)
    status = "ready" if remaining == 0 else "blocked" if blocked else "in_progress"
    key = f"{project_id}:{target}:{completed}:{remaining}:{blocked}:{next_step.command if next_step else 'none'}"
    plan = WorkflowPlan(
        workflow_plan_id="workflow_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=project_id,
        target=target,
        status=status,
        next_command=next_step.command if next_step else None,
        completed_step_count=completed,
        remaining_step_count=remaining,
        blocked_step_count=blocked,
        steps=steps,
    )
    json_path = root / WORKSPACE_DIR / DATA_DIR / "workflow_plan.json"
    md_path = root / "output" / "workflow_plan.md"
    handoff_path = root / "output" / "workflow_agent_handoff.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, plan.model_dump(mode="json"))
    md_path.write_text(render_workflow_plan(plan) + "\n", encoding="utf-8")
    write_json(handoff_path, _workflow_handoff(plan))
    return json_path, md_path, handoff_path, plan


def render_workflow_plan(plan: WorkflowPlan) -> str:
    lines = [
        "# Workflow Plan",
        "",
        "This plan orders explicit user-visible commands. It does not execute commands, render media, move edit points, select music, call models, or access the network.",
        "",
        f"- Target: `{plan.target}`",
        f"- Status: `{plan.status}`",
        f"- Next command: `{plan.next_command or 'none'}`",
        f"- Completed steps: `{plan.completed_step_count}`",
        f"- Remaining steps: `{plan.remaining_step_count}`",
        "",
    ]
    for step in plan.steps:
        lines.extend(
            [
                f"## `{step.step_id}`",
                "",
                f"- Phase: `{step.phase}`",
                f"- Status: `{step.status}`",
                f"- Source: `{step.source}`",
                f"- Command: `{step.command}`",
                f"- Rationale: {step.rationale}",
            ]
        )
        if step.expected_artifacts:
            lines.append(
                f"- Expected artifacts: {', '.join(f'`{ref}`' for ref in step.expected_artifacts)}"
            )
        lines.append("")
    return "\n".join(lines)


def import_workflow_execution_record(
    *,
    root: Path,
    project_id: str,
    target: str,
    candidate_path: Path,
    state: ProjectState | None,
) -> tuple[Path, Path, Path, WorkflowExecutionReview]:
    plan_path = root / WORKSPACE_DIR / DATA_DIR / "workflow_plan.json"
    if plan_path.exists():
        plan = WorkflowPlan.model_validate_json(plan_path.read_text(encoding="utf-8"))
    else:
        _, _, _, plan = build_workflow_plan(
            root=root,
            project_id=project_id,
            target=target,
            state=state,
        )
    if plan.project_id != project_id or plan.target != target:
        raise WorkflowExecutionReviewError("current workflow plan does not match project or target")
    if not candidate_path.exists():
        raise WorkflowExecutionReviewError(f"workflow execution record not found: {candidate_path}")

    data = candidate_path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    quarantine_path = root / WORKSPACE_DIR / DATA_DIR / "workflow_execution_record_quarantine.json"
    quarantine_path.parent.mkdir(parents=True, exist_ok=True)
    quarantine_path.write_bytes(data)
    record = WorkflowExecutionRecord.model_validate_json(data.decode("utf-8"))
    review = _review_execution_record(
        root=root,
        plan=plan,
        record=record,
        quarantine_ref=quarantine_path.relative_to(root).as_posix(),
        candidate_sha256=digest,
        candidate_bytes=len(data),
    )
    json_path = root / WORKSPACE_DIR / DATA_DIR / "workflow_execution_review.json"
    md_path = root / "output" / "workflow_execution_review.md"
    handoff_path = root / "output" / "workflow_execution_handoff.json"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, review.model_dump(mode="json"))
    md_path.write_text(render_workflow_execution_review(review) + "\n", encoding="utf-8")
    write_json(handoff_path, _workflow_execution_handoff(review))
    return json_path, md_path, handoff_path, review


def render_workflow_execution_review(review: WorkflowExecutionReview) -> str:
    lines = [
        "# Workflow Execution Review",
        "",
        "This review validates an explicit external execution record. It does not execute commands, render media, move edit points, select music, call models, or access the network.",
        "",
        f"- Target: `{review.target}`",
        f"- Status: `{review.status}`",
        f"- Workflow plan: `{review.workflow_plan_id}`",
        f"- Quarantine: `{review.quarantine_ref}`",
        f"- Candidate SHA-256: `{review.candidate_sha256}`",
        f"- Accepted steps: `{review.accepted_step_count}`",
        f"- Rejected steps: `{review.rejected_step_count}`",
        f"- Missing steps: `{review.missing_step_count}`",
        f"- Skipped steps: `{review.skipped_step_count}`",
        "",
    ]
    for step in review.step_reviews:
        lines.extend(
            [
                f"## `{step.step_id}`",
                "",
                f"- Review status: `{step.review_status}`",
                f"- Planned status: `{step.planned_status or 'none'}`",
                f"- Submitted status: `{step.submitted_status or 'none'}`",
                f"- Command matched: `{str(step.command_matched).lower()}`",
                f"- Detail: {step.detail}",
            ]
        )
        if step.evidence_refs:
            lines.append(f"- Evidence refs: {', '.join(f'`{ref}`' for ref in step.evidence_refs)}")
        if step.missing_refs:
            lines.append(f"- Missing refs: {', '.join(f'`{ref}`' for ref in step.missing_refs)}")
        lines.append("")
    return "\n".join(lines)


def build_workflow_repair_plan(
    *,
    root: Path,
    project_id: str,
    target: str,
    state: ProjectState | None,
) -> tuple[Path, Path, Path, WorkflowRepairPlan]:
    plan_path = root / WORKSPACE_DIR / DATA_DIR / "workflow_plan.json"
    review_path = root / WORKSPACE_DIR / DATA_DIR / "workflow_execution_review.json"
    if not review_path.exists():
        raise WorkflowExecutionReviewError("workflow execution review is required before workflow repair planning")
    if plan_path.exists():
        plan = WorkflowPlan.model_validate_json(plan_path.read_text(encoding="utf-8"))
    else:
        _, _, _, plan = build_workflow_plan(
            root=root,
            project_id=project_id,
            target=target,
            state=state,
        )
    review = WorkflowExecutionReview.model_validate_json(review_path.read_text(encoding="utf-8"))
    if plan.project_id != project_id or plan.target != target:
        raise WorkflowExecutionReviewError("current workflow plan does not match project or target")
    if review.project_id != project_id or review.target != target:
        raise WorkflowExecutionReviewError("current workflow execution review does not match project or target")
    if review.workflow_plan_id != plan.workflow_plan_id:
        raise WorkflowExecutionReviewError("workflow execution review does not bind to current workflow plan")
    repair_plan = _build_repair_plan_from_review(plan=plan, review=review)
    json_path = root / WORKSPACE_DIR / DATA_DIR / "workflow_repair_plan.json"
    md_path = root / "output" / "workflow_repair_plan.md"
    handoff_path = root / "output" / "workflow_repair_handoff.json"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, repair_plan.model_dump(mode="json"))
    md_path.write_text(render_workflow_repair_plan(repair_plan) + "\n", encoding="utf-8")
    write_json(handoff_path, _workflow_repair_handoff(repair_plan))
    return json_path, md_path, handoff_path, repair_plan


def render_workflow_repair_plan(plan: WorkflowRepairPlan) -> str:
    lines = [
        "# Workflow Repair Plan",
        "",
        "This plan converts workflow execution evidence gaps into explicit manual next commands. It does not execute commands, render media, move edit points, select music, call models, access the network, or promote acceptance success.",
        "",
        f"- Target: `{plan.target}`",
        f"- Status: `{plan.status}`",
        f"- Workflow plan: `{plan.workflow_plan_id}`",
        f"- Execution review: `{plan.workflow_execution_review_id}`",
        f"- Required actions: `{plan.required_action_count}`",
        f"- Optional actions: `{plan.optional_action_count}`",
        f"- First required command: `{plan.first_required_command or 'none'}`",
        "",
    ]
    for action in plan.actions:
        lines.extend(
            [
                f"## `{action.action_id}`",
                "",
                f"- Step: `{action.step_id}`",
                f"- Severity: `{action.severity}`",
                f"- Reason: `{action.reason}`",
                f"- Command: `{action.command}`",
                f"- Rationale: {action.rationale}",
            ]
        )
        if action.expected_artifacts:
            lines.append(
                f"- Expected artifacts: {', '.join(f'`{ref}`' for ref in action.expected_artifacts)}"
            )
        if action.evidence_to_resubmit:
            lines.append(
                f"- Evidence to resubmit: {', '.join(f'`{ref}`' for ref in action.evidence_to_resubmit)}"
            )
        lines.append("")
    return "\n".join(lines)


def build_workflow_repair_approval_request(
    *, root: Path, project_id: str, target: str
) -> tuple[Path, Path, Path, WorkflowRepairApprovalRequest]:
    plan = _load_workflow_repair_plan(root, project_id, target)
    required = [action.action_id for action in plan.actions if action.severity == "required"]
    optional = [action.action_id for action in plan.actions if action.severity == "optional"]
    key = f"{plan.workflow_repair_plan_id}:{len(required)}:{len(optional)}"
    request = WorkflowRepairApprovalRequest(
        approval_request_id="workflow_repair_approval_request_"
        + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=plan.project_id,
        workflow_repair_plan_id=plan.workflow_repair_plan_id,
        workflow_plan_id=plan.workflow_plan_id,
        workflow_execution_review_id=plan.workflow_execution_review_id,
        target=plan.target,
        required_action_ids=required,
        optional_action_ids=optional,
    )
    json_path = root / WORKSPACE_DIR / DATA_DIR / "workflow_repair_approval_request.json"
    md_path = root / "output" / "workflow_repair_approval_request.md"
    handoff_path = root / "output" / "workflow_repair_approval_handoff.json"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, request.model_dump(mode="json"))
    md_path.write_text(render_workflow_repair_approval_request(request) + "\n", encoding="utf-8")
    write_json(handoff_path, _workflow_repair_approval_handoff(request, plan))
    return json_path, md_path, handoff_path, request


def render_workflow_repair_approval_request(request: WorkflowRepairApprovalRequest) -> str:
    return "\n".join(
        [
            "# Workflow Repair Approval Request",
            "",
            "This request asks for explicit approval of manual workflow repair actions. It does not execute commands, render media, or promote acceptance success.",
            "",
            f"- Target: `{request.target}`",
            f"- Repair plan: `{request.workflow_repair_plan_id}`",
            f"- Required action ids: {', '.join(f'`{item}`' for item in request.required_action_ids) or '`none`'}",
            f"- Optional action ids: {', '.join(f'`{item}`' for item in request.optional_action_ids) or '`none`'}",
            f"- Approval required: `{str(request.approval_required).lower()}`",
        ]
    )


def import_workflow_repair_approval_record(
    *, root: Path, project_id: str, target: str, candidate_path: Path
) -> tuple[Path, Path, WorkflowRepairApprovalRecord]:
    plan = _load_workflow_repair_plan(root, project_id, target)
    if not candidate_path.exists():
        raise WorkflowExecutionReviewError(f"workflow repair approval record not found: {candidate_path}")
    data = candidate_path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    quarantine_path = root / WORKSPACE_DIR / DATA_DIR / "workflow_repair_approval_record_quarantine.json"
    quarantine_path.parent.mkdir(parents=True, exist_ok=True)
    quarantine_path.write_bytes(data)
    candidate = WorkflowRepairApprovalRecord.model_validate_json(data.decode("utf-8"))
    valid_action_ids = {action.action_id for action in plan.actions}
    invalid: list[str] = []
    if candidate.project_id != plan.project_id:
        invalid.append("project_id does not match workflow repair plan")
    if candidate.workflow_repair_plan_id != plan.workflow_repair_plan_id:
        invalid.append("workflow_repair_plan_id does not match current repair plan")
    if candidate.workflow_plan_id != plan.workflow_plan_id:
        invalid.append("workflow_plan_id does not match current repair plan")
    if candidate.workflow_execution_review_id != plan.workflow_execution_review_id:
        invalid.append("workflow_execution_review_id does not match current repair plan")
    if candidate.target != plan.target:
        invalid.append("target does not match current repair plan")
    unknown = sorted((set(candidate.approved_action_ids) | set(candidate.rejected_action_ids)) - valid_action_ids)
    if unknown:
        invalid.append("approval record references unknown action ids: " + ", ".join(unknown))
    if any(
        (
            candidate.commands_executed_by_cli,
            candidate.media_rendered_by_cli,
            candidate.acceptance_success_promoted_by_cli,
        )
    ):
        invalid.append("approval record claims forbidden CLI-side execution")
    record = candidate.model_copy(
        update={
            "status": "failed" if invalid else "passed",
            "invalid_reasons": invalid,
            "quarantine_ref": quarantine_path.relative_to(root).as_posix(),
            "candidate_sha256": digest,
            "candidate_bytes": len(data),
            "commands_executed_by_cli": False,
            "media_rendered_by_cli": False,
            "acceptance_success_promoted_by_cli": False,
        }
    )
    json_path = root / WORKSPACE_DIR / DATA_DIR / "workflow_repair_approval_record.json"
    md_path = root / "output" / "workflow_repair_approval_record.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, record.model_dump(mode="json"))
    md_path.write_text(render_workflow_repair_approval_record(record) + "\n", encoding="utf-8")
    return json_path, md_path, record


def render_workflow_repair_approval_record(record: WorkflowRepairApprovalRecord) -> str:
    lines = [
        "# Workflow Repair Approval Record",
        "",
        "This record validates explicit approval choices. It does not execute repair commands.",
        "",
        f"- Status: `{record.status}`",
        f"- Repair plan: `{record.workflow_repair_plan_id}`",
        f"- Approved action ids: {', '.join(f'`{item}`' for item in record.approved_action_ids) or '`none`'}",
        f"- Rejected action ids: {', '.join(f'`{item}`' for item in record.rejected_action_ids) or '`none`'}",
    ]
    if record.invalid_reasons:
        lines.append(f"- Invalid reasons: {'; '.join(record.invalid_reasons)}")
    return "\n".join(lines)


def build_workflow_repair_dry_run(
    *, root: Path, project_id: str, target: str
) -> tuple[Path, Path, Path, WorkflowRepairDryRun]:
    plan = _load_workflow_repair_plan(root, project_id, target)
    record_path = root / WORKSPACE_DIR / DATA_DIR / "workflow_repair_approval_record.json"
    if not record_path.exists():
        raise WorkflowExecutionReviewError("workflow repair approval record is required before dry-run")
    record = WorkflowRepairApprovalRecord.model_validate_json(record_path.read_text(encoding="utf-8"))
    if record.status != "passed":
        raise WorkflowExecutionReviewError("workflow repair approval record must pass before dry-run")
    approved = set(record.approved_action_ids)
    rejected = set(record.rejected_action_ids)
    steps: list[WorkflowRepairDryRunStep] = []
    for action in plan.actions:
        if action.action_id in approved:
            status = "approved"
            reason = "approved for manual execution"
        else:
            status = "rejected"
            reason = "not approved for manual execution"
            rejected.add(action.action_id)
        steps.append(
            WorkflowRepairDryRunStep(
                action_id=action.action_id,
                step_id=action.step_id,
                command=action.command,
                status=status,
                reason=reason,
                expected_artifacts=action.expected_artifacts,
            )
        )
    key = f"{plan.workflow_repair_plan_id}:{record.approval_record_id}:{len(approved)}:{len(rejected)}"
    dry_run = WorkflowRepairDryRun(
        dry_run_id="workflow_repair_dry_run_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=plan.project_id,
        workflow_repair_plan_id=plan.workflow_repair_plan_id,
        approval_record_id=record.approval_record_id,
        target=plan.target,
        approved_step_count=sum(step.status == "approved" for step in steps),
        rejected_step_count=sum(step.status == "rejected" for step in steps),
        steps=steps,
    )
    json_path = root / WORKSPACE_DIR / DATA_DIR / "workflow_repair_dry_run.json"
    md_path = root / "output" / "workflow_repair_dry_run.md"
    handoff_path = root / "output" / "workflow_repair_dry_run_handoff.json"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, dry_run.model_dump(mode="json"))
    md_path.write_text(render_workflow_repair_dry_run(dry_run) + "\n", encoding="utf-8")
    write_json(handoff_path, _workflow_repair_dry_run_handoff(dry_run))
    return json_path, md_path, handoff_path, dry_run


def render_workflow_repair_dry_run(dry_run: WorkflowRepairDryRun) -> str:
    lines = [
        "# Workflow Repair Dry Run",
        "",
        "This dry run enumerates approved manual commands. It does not execute commands.",
        "",
        f"- Approved steps: `{dry_run.approved_step_count}`",
        f"- Rejected steps: `{dry_run.rejected_step_count}`",
        "",
    ]
    for step in dry_run.steps:
        lines.extend([f"## `{step.action_id}`", "", f"- Status: `{step.status}`", f"- Command: `{step.command}`", ""])
    return "\n".join(lines)


def import_workflow_repair_execution_record(
    *, root: Path, project_id: str, target: str, candidate_path: Path
) -> tuple[Path, Path, Path, WorkflowRepairExecutionReview]:
    dry_run_path = root / WORKSPACE_DIR / DATA_DIR / "workflow_repair_dry_run.json"
    if not dry_run_path.exists():
        raise WorkflowExecutionReviewError("workflow repair dry-run is required before execution review")
    dry_run = WorkflowRepairDryRun.model_validate_json(dry_run_path.read_text(encoding="utf-8"))
    if dry_run.project_id != project_id or dry_run.target != target:
        raise WorkflowExecutionReviewError("workflow repair dry-run does not match project or target")
    if not candidate_path.exists():
        raise WorkflowExecutionReviewError(f"workflow repair execution record not found: {candidate_path}")

    data = candidate_path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    quarantine_path = root / WORKSPACE_DIR / DATA_DIR / "workflow_repair_execution_record_quarantine.json"
    quarantine_path.parent.mkdir(parents=True, exist_ok=True)
    quarantine_path.write_bytes(data)
    record = WorkflowRepairExecutionRecord.model_validate_json(data.decode("utf-8"))
    review = _review_workflow_repair_execution_record(
        root=root,
        dry_run=dry_run,
        record=record,
        quarantine_ref=quarantine_path.relative_to(root).as_posix(),
        candidate_sha256=digest,
        candidate_bytes=len(data),
    )
    json_path = root / WORKSPACE_DIR / DATA_DIR / "workflow_repair_execution_review.json"
    md_path = root / "output" / "workflow_repair_execution_review.md"
    handoff_path = root / "output" / "workflow_repair_execution_handoff.json"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, review.model_dump(mode="json"))
    md_path.write_text(render_workflow_repair_execution_review(review) + "\n", encoding="utf-8")
    write_json(handoff_path, _workflow_repair_execution_handoff(review))
    return json_path, md_path, handoff_path, review


def render_workflow_repair_execution_review(review: WorkflowRepairExecutionReview) -> str:
    lines = [
        "# Workflow Repair Execution Review",
        "",
        "This review validates explicit external repair execution evidence. It does not execute commands, render media, move edit points, select music, call models, access the network, or promote acceptance success.",
        "",
        f"- Target: `{review.target}`",
        f"- Status: `{review.status}`",
        f"- Repair plan: `{review.workflow_repair_plan_id}`",
        f"- Approval record: `{review.approval_record_id}`",
        f"- Dry run: `{review.dry_run_id}`",
        f"- Quarantine: `{review.quarantine_ref}`",
        f"- Candidate SHA-256: `{review.candidate_sha256}`",
        f"- Accepted actions: `{review.accepted_action_count}`",
        f"- Rejected actions: `{review.rejected_action_count}`",
        f"- Missing actions: `{review.missing_action_count}`",
        f"- Skipped actions: `{review.skipped_action_count}`",
        "",
    ]
    for action in review.action_reviews:
        lines.extend(
            [
                f"## `{action.action_id}`",
                "",
                f"- Step: `{action.step_id}`",
                f"- Dry-run status: `{action.dry_run_status or 'none'}`",
                f"- Submitted status: `{action.submitted_status or 'none'}`",
                f"- Review status: `{action.review_status}`",
                f"- Command matched: `{str(action.command_matched).lower()}`",
                f"- Detail: {action.detail}",
            ]
        )
        if action.evidence_refs:
            lines.append(f"- Evidence refs: {', '.join(f'`{ref}`' for ref in action.evidence_refs)}")
        if action.missing_refs:
            lines.append(f"- Missing refs: {', '.join(f'`{ref}`' for ref in action.missing_refs)}")
        lines.append("")
    return "\n".join(lines)


def build_workflow_repair_refresh_plan(
    *, root: Path, project_id: str, target: str
) -> tuple[Path, Path, Path, WorkflowRepairRefreshPlan]:
    review_path = root / WORKSPACE_DIR / DATA_DIR / "workflow_repair_execution_review.json"
    if not review_path.exists():
        raise WorkflowExecutionReviewError("workflow repair execution review is required before refresh planning")
    review = WorkflowRepairExecutionReview.model_validate_json(review_path.read_text(encoding="utf-8"))
    if review.project_id != project_id or review.target != target:
        raise WorkflowExecutionReviewError("workflow repair execution review does not match project or target")
    steps: list[WorkflowRepairRefreshStep] = []
    for action in review.action_reviews:
        if action.review_status == "accepted":
            refresh_status = "ready_to_resubmit"
            rationale = "accepted repair evidence can be resubmitted in a workflow execution record"
        elif action.review_status == "rejected":
            refresh_status = "needs_repair"
            rationale = "repair evidence was rejected and needs another manual repair pass"
        elif action.review_status == "missing":
            refresh_status = "missing_evidence"
            rationale = "approved repair action is missing execution evidence"
        else:
            refresh_status = "skipped"
            rationale = "repair action was skipped and remains optional/manual"
        command = f"artist-portrait workflow --project <project.yaml> --target {target} --execution-record <workflow_execution_record.json>"
        steps.append(
            WorkflowRepairRefreshStep(
                action_id=action.action_id,
                step_id=action.step_id,
                refresh_status=refresh_status,
                command=command,
                evidence_refs=action.evidence_refs,
                missing_refs=action.missing_refs,
                rationale=f"{rationale}: {action.detail}",
            )
        )
    ready = sum(step.refresh_status == "ready_to_resubmit" for step in steps)
    blocked = sum(step.refresh_status in {"needs_repair", "missing_evidence"} for step in steps)
    status = "blocked" if blocked else "ready" if ready else "no_actions"
    next_command = next((step.command for step in steps if step.refresh_status == "ready_to_resubmit"), None)
    key = f"{review.workflow_repair_execution_review_id}:{ready}:{blocked}:{len(steps)}"
    plan = WorkflowRepairRefreshPlan(
        workflow_repair_refresh_plan_id="workflow_repair_refresh_"
        + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=review.project_id,
        workflow_repair_execution_review_id=review.workflow_repair_execution_review_id,
        workflow_repair_plan_id=review.workflow_repair_plan_id,
        target=review.target,
        status=status,
        ready_step_count=ready,
        blocked_step_count=blocked,
        next_command=next_command,
        steps=steps,
    )
    json_path = root / WORKSPACE_DIR / DATA_DIR / "workflow_repair_refresh_plan.json"
    md_path = root / "output" / "workflow_repair_refresh_plan.md"
    handoff_path = root / "output" / "workflow_repair_refresh_handoff.json"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, plan.model_dump(mode="json"))
    md_path.write_text(render_workflow_repair_refresh_plan(plan) + "\n", encoding="utf-8")
    write_json(handoff_path, _workflow_repair_refresh_handoff(plan))
    return json_path, md_path, handoff_path, plan


def render_workflow_repair_refresh_plan(plan: WorkflowRepairRefreshPlan) -> str:
    lines = [
        "# Workflow Repair Refresh Plan",
        "",
        "This plan packages reviewed repair evidence for the next explicit workflow execution record. It does not execute commands, mutate workflow plans, render media, or promote acceptance success.",
        "",
        f"- Target: `{plan.target}`",
        f"- Status: `{plan.status}`",
        f"- Repair execution review: `{plan.workflow_repair_execution_review_id}`",
        f"- Ready steps: `{plan.ready_step_count}`",
        f"- Blocked steps: `{plan.blocked_step_count}`",
        f"- Next command: `{plan.next_command or 'none'}`",
        "",
    ]
    for step in plan.steps:
        lines.extend(
            [
                f"## `{step.action_id}`",
                "",
                f"- Workflow step: `{step.step_id}`",
                f"- Refresh status: `{step.refresh_status}`",
                f"- Command: `{step.command}`",
                f"- Rationale: {step.rationale}",
            ]
        )
        if step.evidence_refs:
            lines.append(f"- Evidence refs: {', '.join(f'`{ref}`' for ref in step.evidence_refs)}")
        if step.missing_refs:
            lines.append(f"- Missing refs: {', '.join(f'`{ref}`' for ref in step.missing_refs)}")
        lines.append("")
    return "\n".join(lines)


def _workflow_steps(
    root: Path,
    target: str,
    state: ProjectState | None,
    acceptance: ProjectAcceptanceReport | None,
    rhythm_repair: RhythmRepairPlan | None,
) -> list[WorkflowStep]:
    base = [
        ("init", "foundation", "artist-portrait init --project <project.yaml>", [".artist-portrait/state.json"], "Initialize the project workspace."),
        ("scan", "media", "artist-portrait scan --project <project.yaml>", [".artist-portrait/data/sources.jsonl", "output/scan_report.md"], "Scan source media into the canonical source ledger."),
        ("segment", "media", "artist-portrait segment --project <project.yaml>", [".artist-portrait/data/clips.jsonl", "output/clip_report.md"], "Create deterministic clip records from sources."),
        ("analyze", "evidence", "artist-portrait analyze --project <project.yaml>", [".artist-portrait/data/analysis.jsonl", "output/analysis_report.md"], "Create evidence-only analysis records."),
        ("map", "evidence", "artist-portrait map --project <project.yaml>", ["output/material_map.md"], "Create the analysis-led material map."),
        ("propose", "creative", "artist-portrait propose --project <project.yaml>", ["output/proposal_agent_handoff.json"], "Prepare the host-Agent proposal handoff."),
        ("proposal_import", "creative", "artist-portrait propose --project <project.yaml> --agent-output <candidate.json>", [".artist-portrait/data/proposals.json", ".artist-portrait/data/proposal_validation.json"], "Import and validate an explicit host-Agent proposal candidate."),
        ("timeline", "timeline", "artist-portrait timeline --project <project.yaml> --proposal <id>", ["output/timeline_draft.json"], "Generate a canonical timeline after explicit proposal selection."),
    ]
    if target in {"preview", "delivery"}:
        base.extend(
            [
                ("bgm_import_or_fit", "sound", "artist-portrait bgm import --project <project.yaml> --file <audio-or-video> --rights-status <status>", [".artist-portrait/data/bgm_candidates.json"], "Import or select BGM evidence when music is part of the edit."),
                ("bgm_fit", "sound", "artist-portrait bgm fit --project <project.yaml> --candidate <id>", [".artist-portrait/data/bgm_fit.json"], "Fit the explicit BGM candidate to the timeline when needed."),
                ("rhythm", "rhythm", "artist-portrait rhythm --project <project.yaml>", [".artist-portrait/data/rhythm_plan.json", "output/rhythm_report.md"], "Plan BGM/edit rhythm before preview review."),
                ("preview", "media", "artist-portrait preview --project <project.yaml>", [".artist-portrait/data/preview_validation.json", "output/preview_lowres.mp4"], "Render and validate low-resolution preview media."),
                ("rhythm_qc_preview", "rhythm", "artist-portrait rhythm --project <project.yaml> --qc", [".artist-portrait/data/rhythm_media_qc.json", "output/rhythm_media_qc.md"], "Check preview media against rhythm evidence."),
                ("acceptance_preview", "acceptance", "artist-portrait acceptance --project <project.yaml> --profile preview", [".artist-portrait/data/acceptance_report.json", "output/acceptance_report.md"], "Evaluate preview readiness."),
            ]
        )
    if target == "delivery":
        base.extend(
            [
                ("final_export", "delivery", "artist-portrait export --project <project.yaml> --profile review_720p", [".artist-portrait/data/final_export_validation.json", "output/final_export.mp4"], "Render and validate delivery-review export."),
                ("rhythm_qc_delivery", "rhythm", "artist-portrait rhythm --project <project.yaml> --qc", [".artist-portrait/data/rhythm_media_qc.json", "output/rhythm_media_qc.md"], "Refresh rhythm QC against final export."),
                ("acceptance_delivery", "acceptance", "artist-portrait acceptance --project <project.yaml> --profile delivery", [".artist-portrait/data/acceptance_report.json", "output/acceptance_report.md"], "Evaluate delivery readiness."),
            ]
        )
    steps: list[WorkflowStep] = []
    first_open_seen = False
    for index, (step_id, phase, command, artifacts, rationale) in enumerate(base, start=1):
        done = _step_done(root, state, step_id, artifacts)
        status = "done" if done else "next" if not first_open_seen else "pending"
        if not done:
            first_open_seen = True
        steps.append(
            WorkflowStep(
                step_id=step_id,
                order=index,
                phase=phase,
                status=status,
                command=command,
                rationale=rationale,
                expected_artifacts=artifacts,
                source="workflow",
            )
        )
    if acceptance and acceptance.status == "failed":
        for stage in acceptance.stages:
            if stage.stage_id in set(acceptance.required_stage_ids) and stage.status != "passed":
                for issue in stage.issues:
                    steps.append(
                        WorkflowStep(
                            step_id=f"acceptance_{stage.stage_id}_{len(steps) + 1}",
                            order=len(steps) + 1,
                            phase="acceptance",
                            status="blocked",
                            command=issue.next_action,
                            rationale=issue.detail,
                            expected_artifacts=stage.artifact_refs,
                            source="acceptance",
                        )
                    )
    if rhythm_repair:
        for action in rhythm_repair.actions:
            steps.append(
                WorkflowStep(
                    step_id=f"rhythm_repair_{action.action_id}",
                    order=len(steps) + 1,
                    phase="rhythm",
                    status="blocked" if action.severity == "required" else "optional",
                    command=action.command,
                    rationale=action.rationale,
                    expected_artifacts=action.expected_artifacts,
                    source="rhythm_repair",
                )
            )
    return steps


def _step_done(root: Path, state: ProjectState | None, step_id: str, artifacts: list[str]) -> bool:
    if step_id == "init":
        return state is not None
    if step_id == "proposal_import":
        return all((root / ref).exists() for ref in artifacts)
    if step_id == "bgm_import_or_fit":
        return (root / WORKSPACE_DIR / DATA_DIR / "bgm_candidates.json").exists() or (
            root / WORKSPACE_DIR / DATA_DIR / "bgm_fit.json"
        ).exists()
    if step_id == "rhythm_qc_preview":
        return (root / WORKSPACE_DIR / DATA_DIR / "rhythm_media_qc.json").exists()
    if step_id == "rhythm_qc_delivery":
        return (root / WORKSPACE_DIR / DATA_DIR / "rhythm_media_qc.json").exists() and (
            root / WORKSPACE_DIR / DATA_DIR / "final_export_validation.json"
        ).exists()
    if step_id.startswith("acceptance_"):
        report_path = root / WORKSPACE_DIR / DATA_DIR / "acceptance_report.json"
        if not report_path.exists():
            return False
        report = ProjectAcceptanceReport.model_validate_json(report_path.read_text(encoding="utf-8"))
        expected = step_id.removeprefix("acceptance_")
        if report.acceptance_profile == expected and report.profile_passed:
            return True
        if expected == "preview" and report.acceptance_profile == "delivery" and report.profile_passed:
            return True
        return False
    if all((root / ref).exists() for ref in artifacts):
        return True
    if state and step_id in state.steps:
        return state.steps[step_id].status in {StepStatus.completed, StepStatus.completed_with_warnings}
    return False


def _review_execution_record(
    *,
    root: Path,
    plan: WorkflowPlan,
    record: WorkflowExecutionRecord,
    quarantine_ref: str,
    candidate_sha256: str,
    candidate_bytes: int,
) -> WorkflowExecutionReview:
    planned = {step.step_id: step for step in plan.steps}
    submitted = {step.step_id: step for step in record.steps}
    reviews: list[WorkflowExecutionStepReview] = []

    binding_errors: list[str] = []
    if record.project_id != plan.project_id:
        binding_errors.append("project_id does not match current workflow plan")
    if record.workflow_plan_id != plan.workflow_plan_id:
        binding_errors.append("workflow_plan_id does not match current workflow plan")
    if record.target != plan.target:
        binding_errors.append("target does not match current workflow plan")
    if any(
        (
            record.commands_executed_by_cli,
            record.media_rendered_by_cli,
            record.edit_points_moved_by_cli,
            record.automatic_music_selection_by_cli,
            record.model_call_performed_by_cli,
            record.network_performed_by_cli,
        )
    ):
        binding_errors.append("record claims a forbidden CLI-side execution capability")

    for submitted_step in record.steps:
        plan_step = planned.get(submitted_step.step_id)
        refs = submitted_step.output_refs + submitted_step.evidence_refs
        missing_refs = [ref for ref in refs if not (root / ref).exists()]
        if plan_step is None:
            reviews.append(
                WorkflowExecutionStepReview(
                    step_id=submitted_step.step_id,
                    submitted_status=submitted_step.status,
                    review_status="rejected",
                    evidence_refs=refs,
                    missing_refs=missing_refs,
                    detail="submitted step is not present in the current workflow plan",
                )
            )
            continue
        command_matched = submitted_step.command == plan_step.command
        if binding_errors:
            review_status = "rejected"
            detail = "; ".join(binding_errors)
        elif submitted_step.status == "skipped":
            review_status = "skipped"
            detail = "external record explicitly skipped this step"
        elif submitted_step.status == "failed":
            review_status = "rejected"
            detail = "external record reports this step failed"
        elif not command_matched:
            review_status = "rejected"
            detail = "submitted command does not match workflow plan command"
        elif not refs:
            review_status = "rejected"
            detail = "succeeded step did not provide output_refs or evidence_refs"
        elif missing_refs:
            review_status = "rejected"
            detail = "one or more submitted evidence refs are missing"
        else:
            review_status = "accepted"
            detail = "submitted success is bound to matching command and existing evidence refs"
        reviews.append(
            WorkflowExecutionStepReview(
                step_id=submitted_step.step_id,
                planned_status=plan_step.status,
                submitted_status=submitted_step.status,
                review_status=review_status,
                command_matched=command_matched,
                evidence_refs=refs,
                missing_refs=missing_refs,
                detail=detail,
            )
        )

    for step_id, plan_step in planned.items():
        if step_id not in submitted:
            review_status = "skipped" if plan_step.status == "optional" else "missing"
            detail = (
                "no external execution evidence was submitted for this optional workflow step"
                if plan_step.status == "optional"
                else "no external execution evidence was submitted for this workflow step"
            )
            reviews.append(
                WorkflowExecutionStepReview(
                    step_id=step_id,
                    planned_status=plan_step.status,
                    review_status=review_status,
                    command_matched=False,
                    detail=detail,
                )
            )

    accepted = sum(step.review_status == "accepted" for step in reviews)
    rejected = sum(step.review_status == "rejected" for step in reviews)
    missing = sum(step.review_status == "missing" for step in reviews)
    skipped = sum(step.review_status == "skipped" for step in reviews)
    required_skipped = any(
        step.review_status == "skipped" and step.planned_status != "optional"
        for step in reviews
    )
    status = "failed" if rejected else "warning" if missing or required_skipped else "passed"
    key = f"{plan.workflow_plan_id}:{candidate_sha256}:{accepted}:{rejected}:{missing}:{skipped}"
    return WorkflowExecutionReview(
        workflow_execution_review_id="workflow_execution_review_"
        + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=plan.project_id,
        workflow_plan_id=plan.workflow_plan_id,
        target=plan.target,
        status=status,
        quarantine_ref=quarantine_ref,
        candidate_sha256=candidate_sha256,
        candidate_bytes=candidate_bytes,
        accepted_step_count=accepted,
        rejected_step_count=rejected,
        missing_step_count=missing,
        skipped_step_count=skipped,
        step_reviews=reviews,
    )


def _build_repair_plan_from_review(
    *, plan: WorkflowPlan, review: WorkflowExecutionReview
) -> WorkflowRepairPlan:
    planned = {step.step_id: step for step in plan.steps}
    order = {step.step_id: step.order for step in plan.steps}
    actions: list[WorkflowRepairAction] = []
    for step_review in sorted(review.step_reviews, key=lambda item: order.get(item.step_id, 9999)):
        if step_review.review_status == "accepted":
            continue
        plan_step = planned.get(step_review.step_id)
        if plan_step is None:
            continue
        if step_review.review_status == "skipped" and plan_step.status == "optional":
            severity = "optional"
        else:
            severity = "required"
        if step_review.review_status not in {"rejected", "missing", "skipped"}:
            continue
        reason = step_review.review_status
        command = plan_step.command
        evidence = plan_step.expected_artifacts
        if step_review.missing_refs:
            evidence = step_review.missing_refs
        action = WorkflowRepairAction(
            action_id=f"workflow_repair_{len(actions) + 1:03d}_{step_review.step_id}",
            step_id=step_review.step_id,
            order=len(actions) + 1,
            severity=severity,
            reason=reason,
            command=command,
            expected_artifacts=plan_step.expected_artifacts,
            evidence_to_resubmit=evidence,
            rationale=_repair_rationale(step_review, plan_step),
        )
        actions.append(action)
    required = [action for action in actions if action.severity == "required"]
    optional = [action for action in actions if action.severity == "optional"]
    status = "blocked" if required else "ready" if optional else "no_actions"
    key = f"{review.workflow_execution_review_id}:{len(required)}:{len(optional)}:{required[0].command if required else 'none'}"
    return WorkflowRepairPlan(
        workflow_repair_plan_id="workflow_repair_"
        + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=plan.project_id,
        workflow_plan_id=plan.workflow_plan_id,
        workflow_execution_review_id=review.workflow_execution_review_id,
        target=plan.target,
        status=status,
        required_action_count=len(required),
        optional_action_count=len(optional),
        first_required_command=required[0].command if required else None,
        actions=actions,
    )


def _review_workflow_repair_execution_record(
    *,
    root: Path,
    dry_run: WorkflowRepairDryRun,
    record: WorkflowRepairExecutionRecord,
    quarantine_ref: str,
    candidate_sha256: str,
    candidate_bytes: int,
) -> WorkflowRepairExecutionReview:
    planned = {step.action_id: step for step in dry_run.steps}
    submitted = {action.action_id: action for action in record.actions}
    reviews: list[WorkflowRepairExecutionActionReview] = []

    binding_errors: list[str] = []
    if record.project_id != dry_run.project_id:
        binding_errors.append("project_id does not match workflow repair dry-run")
    if record.workflow_repair_plan_id != dry_run.workflow_repair_plan_id:
        binding_errors.append("workflow_repair_plan_id does not match workflow repair dry-run")
    if record.approval_record_id != dry_run.approval_record_id:
        binding_errors.append("approval_record_id does not match workflow repair dry-run")
    if record.dry_run_id != dry_run.dry_run_id:
        binding_errors.append("dry_run_id does not match workflow repair dry-run")
    if record.target != dry_run.target:
        binding_errors.append("target does not match workflow repair dry-run")
    if any(
        (
            record.commands_executed_by_cli,
            record.media_rendered_by_cli,
            record.edit_points_moved_by_cli,
            record.automatic_music_selection_by_cli,
            record.model_call_performed_by_cli,
            record.network_performed_by_cli,
            record.acceptance_success_promoted_by_cli,
        )
    ):
        binding_errors.append("record claims a forbidden CLI-side execution capability")

    for submitted_action in record.actions:
        dry_step = planned.get(submitted_action.action_id)
        refs = submitted_action.output_refs + submitted_action.evidence_refs
        existing_missing = [ref for ref in refs if not (root / ref).exists()]
        if dry_step is None:
            reviews.append(
                WorkflowRepairExecutionActionReview(
                    action_id=submitted_action.action_id,
                    step_id=submitted_action.step_id,
                    submitted_status=submitted_action.status,
                    review_status="rejected",
                    evidence_refs=refs,
                    missing_refs=existing_missing,
                    detail="submitted action is not present in the current workflow repair dry-run",
                )
            )
            continue

        expected_refs = dry_step.expected_artifacts
        expected_missing = [ref for ref in expected_refs if ref not in refs]
        missing_refs = existing_missing + [ref for ref in expected_missing if ref not in existing_missing]
        command_matched = submitted_action.command == dry_step.command
        if binding_errors:
            review_status = "rejected"
            detail = "; ".join(binding_errors)
        elif dry_step.status != "approved":
            review_status = "rejected"
            detail = "submitted action was not approved in the workflow repair dry-run"
        elif submitted_action.step_id != dry_step.step_id:
            review_status = "rejected"
            detail = "submitted step_id does not match workflow repair dry-run"
        elif submitted_action.status == "skipped":
            review_status = "skipped"
            detail = "external repair execution record explicitly skipped this action"
        elif submitted_action.status == "failed":
            review_status = "rejected"
            detail = "external repair execution record reports this action failed"
        elif not command_matched:
            review_status = "rejected"
            detail = "submitted command does not match workflow repair dry-run command"
        elif not refs:
            review_status = "rejected"
            detail = "succeeded action did not provide output_refs or evidence_refs"
        elif missing_refs:
            review_status = "rejected"
            detail = "submitted evidence does not cover existing expected artifacts"
        else:
            review_status = "accepted"
            detail = "submitted repair success is bound to approved action, matching command, and existing evidence refs"
        reviews.append(
            WorkflowRepairExecutionActionReview(
                action_id=submitted_action.action_id,
                step_id=dry_step.step_id,
                dry_run_status=dry_step.status,
                submitted_status=submitted_action.status,
                review_status=review_status,
                command_matched=command_matched,
                evidence_refs=refs,
                missing_refs=missing_refs,
                detail=detail,
            )
        )

    for action_id, dry_step in planned.items():
        if dry_step.status != "approved" or action_id in submitted:
            continue
        reviews.append(
            WorkflowRepairExecutionActionReview(
                action_id=action_id,
                step_id=dry_step.step_id,
                dry_run_status=dry_step.status,
                review_status="missing",
                command_matched=False,
                missing_refs=dry_step.expected_artifacts,
                detail="no external repair execution evidence was submitted for this approved action",
            )
        )

    accepted = sum(action.review_status == "accepted" for action in reviews)
    rejected = sum(action.review_status == "rejected" for action in reviews)
    missing = sum(action.review_status == "missing" for action in reviews)
    skipped = sum(action.review_status == "skipped" for action in reviews)
    status = "failed" if rejected else "warning" if missing or skipped else "passed"
    key = f"{dry_run.dry_run_id}:{candidate_sha256}:{accepted}:{rejected}:{missing}:{skipped}"
    return WorkflowRepairExecutionReview(
        workflow_repair_execution_review_id="workflow_repair_execution_review_"
        + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=dry_run.project_id,
        workflow_repair_plan_id=dry_run.workflow_repair_plan_id,
        approval_record_id=dry_run.approval_record_id,
        dry_run_id=dry_run.dry_run_id,
        target=dry_run.target,
        status=status,
        quarantine_ref=quarantine_ref,
        candidate_sha256=candidate_sha256,
        candidate_bytes=candidate_bytes,
        accepted_action_count=accepted,
        rejected_action_count=rejected,
        missing_action_count=missing,
        skipped_action_count=skipped,
        action_reviews=reviews,
    )


def _repair_rationale(step_review: WorkflowExecutionStepReview, plan_step: WorkflowStep) -> str:
    if step_review.review_status == "rejected":
        return f"Repair rejected evidence for `{step_review.step_id}`: {step_review.detail}"
    if step_review.review_status == "missing":
        return f"Run or resubmit evidence for required workflow step `{step_review.step_id}`."
    if step_review.review_status == "skipped" and plan_step.status == "optional":
        return f"Optional workflow step `{step_review.step_id}` was skipped; run only if this optional guidance is still desired."
    return f"Repair workflow step `{step_review.step_id}` evidence."


def _workflow_handoff(plan: WorkflowPlan) -> dict:
    return {
        "schema_version": plan.schema_version,
        "handoff_id": f"workflow_handoff_{plan.workflow_plan_id}",
        "project_id": plan.project_id,
        "workflow_plan_id": plan.workflow_plan_id,
        "target": plan.target,
        "task": "Review the workflow plan and guide the user through explicit commands only.",
        "next_command": plan.next_command,
        "steps": [step.model_dump(mode="json") for step in plan.steps],
        "forbidden": [
            "do not execute commands without explicit user action",
            "do not render media from the workflow command",
            "do not move edit points",
            "do not select music",
            "do not call models from the CLI",
            "do not access the network",
        ],
    }


def _workflow_execution_handoff(review: WorkflowExecutionReview) -> dict:
    return {
        "schema_version": review.schema_version,
        "handoff_id": f"workflow_execution_handoff_{review.workflow_execution_review_id}",
        "project_id": review.project_id,
        "workflow_plan_id": review.workflow_plan_id,
        "workflow_execution_review_id": review.workflow_execution_review_id,
        "target": review.target,
        "task": "Review external workflow execution evidence without treating it as automatic acceptance success.",
        "status": review.status,
        "quarantine_ref": review.quarantine_ref,
        "step_reviews": [step.model_dump(mode="json") for step in review.step_reviews],
        "forbidden": [
            "do not execute commands from this review",
            "do not render media from this review",
            "do not move edit points",
            "do not select music",
            "do not call models from the CLI",
            "do not access the network",
            "do not treat execution evidence as acceptance success",
        ],
    }


def _workflow_repair_handoff(plan: WorkflowRepairPlan) -> dict:
    return {
        "schema_version": plan.schema_version,
        "handoff_id": f"workflow_repair_handoff_{plan.workflow_repair_plan_id}",
        "project_id": plan.project_id,
        "workflow_plan_id": plan.workflow_plan_id,
        "workflow_execution_review_id": plan.workflow_execution_review_id,
        "workflow_repair_plan_id": plan.workflow_repair_plan_id,
        "target": plan.target,
        "task": "Guide the user through manual workflow evidence repair commands only.",
        "status": plan.status,
        "first_required_command": plan.first_required_command,
        "actions": [action.model_dump(mode="json") for action in plan.actions],
        "forbidden": [
            "do not execute repair commands",
            "do not render media from this repair plan",
            "do not move edit points",
            "do not select music",
            "do not call models from the CLI",
            "do not access the network",
            "do not treat repaired evidence as acceptance success",
        ],
    }


def _workflow_repair_approval_handoff(
    request: WorkflowRepairApprovalRequest, plan: WorkflowRepairPlan
) -> dict:
    return {
        "schema_version": request.schema_version,
        "handoff_id": f"workflow_repair_approval_handoff_{request.approval_request_id}",
        "project_id": request.project_id,
        "workflow_repair_plan_id": request.workflow_repair_plan_id,
        "target": request.target,
        "task": "Collect explicit approval for manual workflow repair actions only.",
        "required_action_ids": request.required_action_ids,
        "optional_action_ids": request.optional_action_ids,
        "actions": [action.model_dump(mode="json") for action in plan.actions],
        "forbidden": [
            "do not execute repair commands",
            "do not render media from this approval request",
            "do not treat approval as acceptance success",
        ],
    }


def _workflow_repair_dry_run_handoff(dry_run: WorkflowRepairDryRun) -> dict:
    return {
        "schema_version": dry_run.schema_version,
        "handoff_id": f"workflow_repair_dry_run_handoff_{dry_run.dry_run_id}",
        "project_id": dry_run.project_id,
        "workflow_repair_plan_id": dry_run.workflow_repair_plan_id,
        "approval_record_id": dry_run.approval_record_id,
        "target": dry_run.target,
        "task": "Review approved manual workflow repair commands without executing them.",
        "steps": [step.model_dump(mode="json") for step in dry_run.steps],
        "forbidden": [
            "do not execute dry-run commands",
            "do not render media from this dry run",
            "do not treat dry-run approval as acceptance success",
        ],
    }


def _workflow_repair_execution_handoff(review: WorkflowRepairExecutionReview) -> dict:
    return {
        "schema_version": review.schema_version,
        "handoff_id": f"workflow_repair_execution_handoff_{review.workflow_repair_execution_review_id}",
        "project_id": review.project_id,
        "workflow_repair_plan_id": review.workflow_repair_plan_id,
        "approval_record_id": review.approval_record_id,
        "dry_run_id": review.dry_run_id,
        "workflow_repair_execution_review_id": review.workflow_repair_execution_review_id,
        "target": review.target,
        "task": "Review external manual workflow repair execution evidence without treating it as acceptance success.",
        "status": review.status,
        "quarantine_ref": review.quarantine_ref,
        "action_reviews": [action.model_dump(mode="json") for action in review.action_reviews],
        "forbidden": [
            "do not execute repair commands from this review",
            "do not render media from this review",
            "do not move edit points",
            "do not select music",
            "do not call models from the CLI",
            "do not access the network",
            "do not treat repair execution evidence as acceptance success",
        ],
    }


def _workflow_repair_refresh_handoff(plan: WorkflowRepairRefreshPlan) -> dict:
    return {
        "schema_version": plan.schema_version,
        "handoff_id": f"workflow_repair_refresh_handoff_{plan.workflow_repair_refresh_plan_id}",
        "project_id": plan.project_id,
        "workflow_repair_refresh_plan_id": plan.workflow_repair_refresh_plan_id,
        "workflow_repair_execution_review_id": plan.workflow_repair_execution_review_id,
        "workflow_repair_plan_id": plan.workflow_repair_plan_id,
        "target": plan.target,
        "task": "Prepare the next explicit workflow execution record from reviewed repair evidence without running commands.",
        "status": plan.status,
        "next_command": plan.next_command,
        "steps": [step.model_dump(mode="json") for step in plan.steps],
        "forbidden": [
            "do not execute workflow commands from this refresh plan",
            "do not mutate workflow plans from this refresh plan",
            "do not render media from this refresh plan",
            "do not move edit points",
            "do not select music",
            "do not call models from the CLI",
            "do not access the network",
            "do not treat refreshed evidence as acceptance success",
        ],
    }


def _load_workflow_repair_plan(root: Path, project_id: str, target: str) -> WorkflowRepairPlan:
    path = root / WORKSPACE_DIR / DATA_DIR / "workflow_repair_plan.json"
    if not path.exists():
        raise WorkflowExecutionReviewError("workflow repair plan is required")
    plan = WorkflowRepairPlan.model_validate_json(path.read_text(encoding="utf-8"))
    if plan.project_id != project_id or plan.target != target:
        raise WorkflowExecutionReviewError("workflow repair plan does not match project or target")
    return plan


def _read_optional(path: Path, model):
    if not path.exists():
        return None
    return model.model_validate_json(path.read_text(encoding="utf-8"))
