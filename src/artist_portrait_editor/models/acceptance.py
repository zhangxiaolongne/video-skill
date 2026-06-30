from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class AcceptanceIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    severity: str = Field(pattern=r"^(error|warning)$")
    detail: str = Field(min_length=1)
    next_action: str = Field(min_length=1)


class AcceptanceStage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage_id: str = Field(min_length=1)
    status: str = Field(pattern=r"^(passed|warning|failed|not_applicable)$")
    required_for_core: bool
    required_for_delivery: bool
    artifact_refs: list[str] = Field(default_factory=list)
    evidence_summary: dict = Field(default_factory=dict)
    issues: list[AcceptanceIssue] = Field(default_factory=list)


class ProjectAcceptanceReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    acceptance_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    acceptance_profile: str = Field(pattern=r"^(standard|core|preview|delivery)$")
    status: str = Field(pattern=r"^(passed|warning|failed)$")
    profile_passed: bool
    required_stage_ids: list[str] = Field(default_factory=list)
    core_ready: bool
    preview_ready: bool
    final_export_ready: bool
    acceptance_score: float = Field(ge=0, le=1)
    stage_count: int = Field(ge=0)
    passed_stage_count: int = Field(ge=0)
    warning_stage_count: int = Field(ge=0)
    failed_stage_count: int = Field(ge=0)
    issue_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    stages: list[AcceptanceStage] = Field(default_factory=list)
    network_performed: bool = False
    model_call_performed_by_cli: bool = False
    media_rendered: bool = False
    automatic_music_selection: bool = False


class AcceptanceRepairAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1)
    order: int = Field(ge=1)
    stage_id: str = Field(min_length=1)
    issue_code: str = Field(min_length=1)
    severity: str = Field(pattern=r"^(error|warning)$")
    required_for_profile: bool
    command: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    expected_artifacts: list[str] = Field(default_factory=list)
    executes_automatically: bool = False


class AcceptanceRepairPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    repair_plan_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    acceptance_id: str = Field(min_length=1)
    acceptance_profile: str = Field(pattern=r"^(standard|core|preview|delivery)$")
    acceptance_status: str = Field(pattern=r"^(passed|warning|failed)$")
    profile_passed: bool
    action_count: int = Field(ge=0)
    required_action_count: int = Field(ge=0)
    optional_action_count: int = Field(ge=0)
    blocked_stage_ids: list[str] = Field(default_factory=list)
    first_required_command: str | None = None
    actions: list[AcceptanceRepairAction] = Field(default_factory=list)
    network_performed: bool = False
    model_call_performed_by_cli: bool = False
    media_rendered: bool = False
    automatic_repair_performed: bool = False
    automatic_music_selection: bool = False


class AcceptanceRepairApprovalAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1)
    command: str = Field(min_length=1)
    required_for_profile: bool
    decision: str = Field(pattern=r"^(pending|approved|rejected)$")
    rationale: str | None = None


class AcceptanceRepairApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    approval_request_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    repair_plan_id: str = Field(min_length=1)
    acceptance_profile: str = Field(pattern=r"^(standard|core|preview|delivery)$")
    required_action_count: int = Field(ge=0)
    optional_action_count: int = Field(ge=0)
    actions: list[AcceptanceRepairApprovalAction] = Field(default_factory=list)
    network_performed: bool = False
    model_call_performed_by_cli: bool = False
    media_rendered: bool = False
    automatic_repair_performed: bool = False


class AcceptanceRepairApprovalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    approval_record_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    repair_plan_id: str = Field(min_length=1)
    acceptance_profile: str = Field(pattern=r"^(standard|core|preview|delivery)$")
    valid: bool
    approved_action_ids: list[str] = Field(default_factory=list)
    rejected_action_ids: list[str] = Field(default_factory=list)
    issue_count: int = Field(ge=0)
    issues: list[str] = Field(default_factory=list)
    actions: list[AcceptanceRepairApprovalAction] = Field(default_factory=list)
    network_performed: bool = False
    model_call_performed_by_cli: bool = False
    media_rendered: bool = False
    automatic_repair_performed: bool = False


class AcceptanceRepairExecutionStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(min_length=1)
    order: int = Field(ge=1)
    action_id: str = Field(min_length=1)
    command: str = Field(min_length=1)
    required_for_profile: bool
    approval_decision: str = Field(pattern=r"^(approved|rejected)$")
    would_execute: bool = False
    blocked_reason: str | None = None


class AcceptanceRepairExecutionDryRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    dry_run_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    repair_plan_id: str = Field(min_length=1)
    approval_record_id: str = Field(min_length=1)
    acceptance_profile: str = Field(pattern=r"^(standard|core|preview|delivery)$")
    approval_record_valid: bool
    approved_step_count: int = Field(ge=0)
    rejected_step_count: int = Field(ge=0)
    blocked: bool
    issues: list[str] = Field(default_factory=list)
    steps: list[AcceptanceRepairExecutionStep] = Field(default_factory=list)
    network_performed: bool = False
    model_call_performed_by_cli: bool = False
    media_rendered: bool = False
    automatic_repair_performed: bool = False
    commands_executed: bool = False


class AcceptanceRepairExecutionBundleCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command_id: str = Field(min_length=1)
    order: int = Field(ge=1)
    step_id: str = Field(min_length=1)
    action_id: str = Field(min_length=1)
    command: str = Field(min_length=1)
    required_for_profile: bool
    expected_artifacts: list[str] = Field(default_factory=list)
    manual_execution_required: bool = True
    executable_by_cli: bool = False


class AcceptanceRepairExecutionBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    execution_bundle_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    repair_plan_id: str = Field(min_length=1)
    approval_record_id: str = Field(min_length=1)
    dry_run_id: str = Field(min_length=1)
    acceptance_profile: str = Field(pattern=r"^(standard|core|preview|delivery)$")
    dry_run_valid: bool
    command_count: int = Field(ge=0)
    blocked: bool
    issues: list[str] = Field(default_factory=list)
    commands: list[AcceptanceRepairExecutionBundleCommand] = Field(default_factory=list)
    network_performed: bool = False
    model_call_performed_by_cli: bool = False
    media_rendered: bool = False
    automatic_repair_performed: bool = False
    commands_executed_by_cli: bool = False


class AcceptanceRepairExecutionEvidenceAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1)
    step_id: str = Field(min_length=1)
    command: str = Field(min_length=1)
    status: str = Field(pattern=r"^(succeeded|failed|skipped)$")
    exit_code: int | None = Field(default=None, ge=0)
    artifact_refs: list[str] = Field(default_factory=list)
    notes: str | None = None


class AcceptanceRepairExecutionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    execution_record_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    repair_plan_id: str = Field(min_length=1)
    approval_record_id: str = Field(min_length=1)
    dry_run_id: str = Field(min_length=1)
    execution_bundle_id: str | None = None
    acceptance_profile: str = Field(pattern=r"^(standard|core|preview|delivery)$")
    valid: bool
    completed_action_ids: list[str] = Field(default_factory=list)
    failed_action_ids: list[str] = Field(default_factory=list)
    skipped_action_ids: list[str] = Field(default_factory=list)
    issue_count: int = Field(ge=0)
    issues: list[str] = Field(default_factory=list)
    actions: list[AcceptanceRepairExecutionEvidenceAction] = Field(default_factory=list)
    network_performed: bool = False
    model_call_performed_by_cli: bool = False
    media_rendered: bool = False
    automatic_repair_performed: bool = False
    commands_executed_by_cli: bool = False
