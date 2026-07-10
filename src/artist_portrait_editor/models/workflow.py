from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class WorkflowStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(min_length=1)
    order: int = Field(ge=1)
    phase: str = Field(min_length=1)
    status: str = Field(pattern=r"^(done|next|pending|blocked|optional)$")
    command: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    expected_artifacts: list[str] = Field(default_factory=list)
    source: str = Field(pattern=r"^(workflow|acceptance|rhythm_repair|state)$")
    executes_automatically: bool = False


class CreatorWorkflowStage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage_id: str = Field(min_length=1)
    order: int = Field(ge=1)
    title: str = Field(min_length=1)
    status: str = Field(pattern=r"^(done|current|pending|blocked)$")
    next_command: str | None = None
    summary: str = Field(min_length=1)
    step_ids: list[str] = Field(default_factory=list)
    deliverable_refs: list[str] = Field(default_factory=list)
    blocking_step_ids: list[str] = Field(default_factory=list)


class CreatorWorkflowDeliverable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deliverable_id: str = Field(min_length=1)
    stage_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    status: str = Field(pattern=r"^(present|missing|blocked)$")
    refs: list[str] = Field(default_factory=list)
    summary: str = Field(min_length=1)


class WorkflowPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    workflow_plan_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    target: str = Field(pattern=r"^(core|preview|delivery)$")
    status: str = Field(pattern=r"^(ready|in_progress|blocked)$")
    next_command: str | None = None
    completed_step_count: int = Field(ge=0)
    remaining_step_count: int = Field(ge=0)
    blocked_step_count: int = Field(ge=0)
    steps: list[WorkflowStep] = Field(default_factory=list)
    creator_stage_count: int = Field(ge=0)
    current_stage_id: str | None = None
    current_stage_title: str | None = None
    creator_stages: list[CreatorWorkflowStage] = Field(default_factory=list)
    deliverables: list[CreatorWorkflowDeliverable] = Field(default_factory=list)
    bgm_input_guidance: list[str] = Field(default_factory=list)
    commands_executed: bool = False
    media_rendered: bool = False
    edit_points_moved: bool = False
    automatic_music_selection: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False


class WorkflowExecutionStepRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(min_length=1)
    command: str = Field(min_length=1)
    status: str = Field(pattern=r"^(succeeded|failed|skipped)$")
    exit_code: int | None = None
    output_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    notes: str | None = None


class WorkflowExecutionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    execution_record_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    workflow_plan_id: str = Field(min_length=1)
    target: str = Field(pattern=r"^(core|preview|delivery)$")
    executed_by: str = Field(min_length=1)
    steps: list[WorkflowExecutionStepRecord] = Field(default_factory=list)
    commands_executed_by_cli: bool = False
    media_rendered_by_cli: bool = False
    edit_points_moved_by_cli: bool = False
    automatic_music_selection_by_cli: bool = False
    model_call_performed_by_cli: bool = False
    network_performed_by_cli: bool = False


class WorkflowExecutionStepReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(min_length=1)
    planned_status: str | None = None
    submitted_status: str | None = None
    review_status: str = Field(pattern=r"^(accepted|rejected|missing|skipped)$")
    command_matched: bool = False
    evidence_refs: list[str] = Field(default_factory=list)
    missing_refs: list[str] = Field(default_factory=list)
    detail: str = Field(min_length=1)


class WorkflowExecutionReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    workflow_execution_review_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    workflow_plan_id: str = Field(min_length=1)
    target: str = Field(pattern=r"^(core|preview|delivery)$")
    status: str = Field(pattern=r"^(passed|warning|failed)$")
    quarantine_ref: str = Field(min_length=1)
    candidate_sha256: str = Field(min_length=64, max_length=64)
    candidate_bytes: int = Field(ge=0)
    accepted_step_count: int = Field(ge=0)
    rejected_step_count: int = Field(ge=0)
    missing_step_count: int = Field(ge=0)
    skipped_step_count: int = Field(ge=0)
    step_reviews: list[WorkflowExecutionStepReview] = Field(default_factory=list)
    commands_executed_by_cli: bool = False
    media_rendered_by_cli: bool = False
    edit_points_moved_by_cli: bool = False
    automatic_music_selection_by_cli: bool = False
    model_call_performed_by_cli: bool = False
    network_performed_by_cli: bool = False
