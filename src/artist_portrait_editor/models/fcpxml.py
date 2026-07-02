from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class FcpxmlDraftClip(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clip_id: str = Field(min_length=1)
    mapping_id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    offset_seconds: float = Field(ge=0)
    duration_seconds: float = Field(gt=0)
    source_start_seconds: float = Field(ge=0)
    source_duration_seconds: float = Field(gt=0)
    source_id: str = Field(min_length=1)
    relink_required: bool = True
    warning_count: int = Field(ge=0)
    evidence_refs: list[str] = Field(default_factory=list)


class FcpxmlDraftMarker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    marker_id: str = Field(min_length=1)
    mapping_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    note: str = Field(min_length=1)
    offset_seconds: float = Field(ge=0)
    duration_seconds: float = Field(ge=0)
    priority: str = Field(min_length=1)
    category: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)


class FcpxmlValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    validation_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    fcpxml_draft_id: str = Field(min_length=1)
    status: str = Field(pattern=r"^(passed|warning|failed)$")
    xml_parse_passed: bool
    project_binding_passed: bool
    plan_binding_passed: bool
    timeline_mapping_coverage_passed: bool
    relink_required: bool
    import_verified: bool = False
    commands_executed: bool = False
    media_rendered: bool = False
    timeline_mutated: bool = False
    edit_points_moved: bool = False
    nle_import_performed: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class FcpxmlDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    fcpxml_draft_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    nle_plan_id: str = Field(min_length=1)
    editor_package_id: str = Field(min_length=1)
    status: str = Field(pattern=r"^(ready|warning|blocked)$")
    frame_rate: float = Field(gt=0)
    fcpxml_version: str = Field(min_length=1)
    draft_ref: str = Field(min_length=1)
    validation_ref: str = Field(min_length=1)
    clip_count: int = Field(ge=0)
    marker_count: int = Field(ge=0)
    audio_note_count: int = Field(ge=0)
    relink_required: bool = True
    import_verified: bool = False
    clips: list[FcpxmlDraftClip] = Field(default_factory=list)
    markers: list[FcpxmlDraftMarker] = Field(default_factory=list)
    audio_notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    forbidden_capabilities: list[str] = Field(default_factory=list)
    commands_executed: bool = False
    media_rendered: bool = False
    timeline_mutated: bool = False
    edit_points_moved: bool = False
    nle_import_performed: bool = False
    automatic_music_selection: bool = False
    automatic_bgm_fit: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
    image_generation_or_editing_used: bool = False


class FcpxmlImportReviewIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_id: str = Field(min_length=1)
    severity: str = Field(pattern=r"^(info|warning|error)$")
    category: str = Field(min_length=1)
    detail: str = Field(min_length=1)


class FcpxmlImportReviewCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    import_review_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    fcpxml_draft_id: str = Field(min_length=1)
    nle_plan_id: str = Field(min_length=1)
    reviewed_by: str = Field(min_length=1)
    application_name: str = Field(min_length=1)
    application_version: str | None = None
    import_attempted: bool
    import_succeeded: bool
    relink_attempted: bool = False
    relink_succeeded: bool = False
    relink_missing_count: int = Field(default=0, ge=0)
    timeline_opened: bool = False
    playback_checked: bool = False
    issue_count: int = Field(ge=0)
    issues: list[FcpxmlImportReviewIssue] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    media_rendered: bool = False
    timeline_mutated: bool = False
    edit_points_moved: bool = False
    automatic_music_selection: bool = False
    automatic_bgm_fit: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
    image_generation_or_editing_used: bool = False


class FcpxmlImportReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    review_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    fcpxml_draft_id: str = Field(min_length=1)
    nle_plan_id: str = Field(min_length=1)
    candidate_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    quarantine_ref: str = Field(min_length=1)
    status: str = Field(pattern=r"^(accepted|warning|rejected)$")
    binding_status: str = Field(pattern=r"^(matched|mismatch)$")
    import_attempted: bool
    import_success_claimed: bool
    relink_success_claimed: bool
    timeline_opened: bool
    playback_checked: bool
    issue_count: int = Field(ge=0)
    accepted_issue_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    import_success_accepted_as_project_success: bool = False
    findings: list[FcpxmlImportReviewIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    rejected_reasons: list[str] = Field(default_factory=list)
    forbidden_capabilities: list[str] = Field(default_factory=list)
    commands_executed: bool = False
    media_rendered: bool = False
    timeline_mutated: bool = False
    edit_points_moved: bool = False
    automatic_music_selection: bool = False
    automatic_bgm_fit: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
    image_generation_or_editing_used: bool = False


class FcpxmlRepairAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1)
    order: int = Field(ge=1)
    source: str = Field(pattern=r"^(draft|validation|import_review|finding|playback)$")
    category: str = Field(
        pattern=r"^(asset_relink|import_blocker|mapping_review|playback_review|operator_review)$"
    )
    severity: str = Field(pattern=r"^(required|optional)$")
    command: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    expected_artifacts: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    executes_automatically: bool = False


class FcpxmlRepairPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    repair_plan_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    fcpxml_draft_id: str = Field(min_length=1)
    fcpxml_validation_id: str = Field(min_length=1)
    fcpxml_import_review_id: str = Field(min_length=1)
    nle_plan_id: str = Field(min_length=1)
    status: str = Field(pattern=r"^(ready|warning|blocked)$")
    action_count: int = Field(ge=0)
    required_action_count: int = Field(ge=0)
    optional_action_count: int = Field(ge=0)
    first_required_command: str | None = None
    relink_action_count: int = Field(ge=0)
    import_blocker_count: int = Field(ge=0)
    playback_review_required: bool
    actions: list[FcpxmlRepairAction] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    forbidden_capabilities: list[str] = Field(default_factory=list)
    commands_executed: bool = False
    media_rendered: bool = False
    timeline_mutated: bool = False
    edit_points_moved: bool = False
    nle_import_performed: bool = False
    source_relink_performed: bool = False
    automatic_music_selection: bool = False
    automatic_bgm_fit: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
    image_generation_or_editing_used: bool = False
    repair_success_claimed: bool = False


class FcpxmlRepairApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    approval_request_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    fcpxml_repair_plan_id: str = Field(min_length=1)
    fcpxml_draft_id: str = Field(min_length=1)
    fcpxml_import_review_id: str = Field(min_length=1)
    required_action_ids: list[str] = Field(default_factory=list)
    optional_action_ids: list[str] = Field(default_factory=list)
    approval_required: bool = True
    commands_executed: bool = False
    media_rendered: bool = False
    timeline_mutated: bool = False
    edit_points_moved: bool = False
    nle_import_performed: bool = False
    source_relink_performed: bool = False
    repair_success_claimed: bool = False


class FcpxmlRepairApprovalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    approval_record_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    fcpxml_repair_plan_id: str = Field(min_length=1)
    fcpxml_draft_id: str = Field(min_length=1)
    fcpxml_import_review_id: str = Field(min_length=1)
    approved_by: str = Field(min_length=1)
    approved_action_ids: list[str] = Field(default_factory=list)
    rejected_action_ids: list[str] = Field(default_factory=list)
    status: str = Field(pattern=r"^(passed|failed)$")
    invalid_reasons: list[str] = Field(default_factory=list)
    quarantine_ref: str | None = None
    candidate_sha256: str | None = None
    candidate_bytes: int = Field(default=0, ge=0)
    commands_executed_by_cli: bool = False
    media_rendered_by_cli: bool = False
    timeline_mutated_by_cli: bool = False
    edit_points_moved_by_cli: bool = False
    nle_import_performed_by_cli: bool = False
    source_relink_performed_by_cli: bool = False
    automatic_music_selection_by_cli: bool = False
    automatic_bgm_fit_by_cli: bool = False
    model_call_performed_by_cli: bool = False
    network_performed_by_cli: bool = False
    image_generation_or_editing_used_by_cli: bool = False
    repair_success_claimed_by_cli: bool = False


class FcpxmlRepairDryRunStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1)
    command: str = Field(min_length=1)
    status: str = Field(pattern=r"^(approved|rejected)$")
    reason: str = Field(min_length=1)
    expected_artifacts: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class FcpxmlRepairDryRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    dry_run_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    fcpxml_repair_plan_id: str = Field(min_length=1)
    approval_record_id: str = Field(min_length=1)
    fcpxml_draft_id: str = Field(min_length=1)
    fcpxml_import_review_id: str = Field(min_length=1)
    approved_action_count: int = Field(ge=0)
    rejected_action_count: int = Field(ge=0)
    steps: list[FcpxmlRepairDryRunStep] = Field(default_factory=list)
    commands_executed: bool = False
    media_rendered: bool = False
    timeline_mutated: bool = False
    edit_points_moved: bool = False
    nle_import_performed: bool = False
    source_relink_performed: bool = False
    automatic_music_selection: bool = False
    automatic_bgm_fit: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
    image_generation_or_editing_used: bool = False
    repair_success_claimed: bool = False


class FcpxmlRepairExecutionActionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1)
    command: str = Field(min_length=1)
    status: str = Field(pattern=r"^(succeeded|failed|skipped)$")
    exit_code: int | None = Field(default=None, ge=0)
    output_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    notes: str | None = None


class FcpxmlRepairExecutionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    execution_record_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    fcpxml_repair_plan_id: str = Field(min_length=1)
    approval_record_id: str = Field(min_length=1)
    dry_run_id: str = Field(min_length=1)
    fcpxml_draft_id: str = Field(min_length=1)
    fcpxml_import_review_id: str = Field(min_length=1)
    executed_by: str = Field(min_length=1)
    actions: list[FcpxmlRepairExecutionActionRecord] = Field(default_factory=list)
    commands_executed_by_cli: bool = False
    media_rendered_by_cli: bool = False
    timeline_mutated_by_cli: bool = False
    edit_points_moved_by_cli: bool = False
    nle_import_performed_by_cli: bool = False
    source_relink_performed_by_cli: bool = False
    automatic_music_selection_by_cli: bool = False
    automatic_bgm_fit_by_cli: bool = False
    model_call_performed_by_cli: bool = False
    network_performed_by_cli: bool = False
    image_generation_or_editing_used_by_cli: bool = False
    repair_success_promoted_by_cli: bool = False
    acceptance_success_promoted_by_cli: bool = False


class FcpxmlRepairExecutionActionReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1)
    dry_run_status: str | None = None
    submitted_status: str | None = None
    review_status: str = Field(pattern=r"^(accepted|rejected|missing|skipped)$")
    command_matched: bool = False
    evidence_refs: list[str] = Field(default_factory=list)
    output_refs: list[str] = Field(default_factory=list)
    missing_refs: list[str] = Field(default_factory=list)
    detail: str = Field(min_length=1)


class FcpxmlRepairExecutionReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    execution_review_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    fcpxml_repair_plan_id: str = Field(min_length=1)
    approval_record_id: str = Field(min_length=1)
    dry_run_id: str = Field(min_length=1)
    fcpxml_draft_id: str = Field(min_length=1)
    fcpxml_import_review_id: str = Field(min_length=1)
    status: str = Field(pattern=r"^(passed|warning|failed)$")
    quarantine_ref: str = Field(min_length=1)
    candidate_sha256: str = Field(min_length=64, max_length=64)
    candidate_bytes: int = Field(ge=0)
    accepted_action_count: int = Field(ge=0)
    rejected_action_count: int = Field(ge=0)
    missing_action_count: int = Field(ge=0)
    skipped_action_count: int = Field(ge=0)
    action_reviews: list[FcpxmlRepairExecutionActionReview] = Field(default_factory=list)
    commands_executed_by_cli: bool = False
    media_rendered_by_cli: bool = False
    timeline_mutated_by_cli: bool = False
    edit_points_moved_by_cli: bool = False
    nle_import_performed_by_cli: bool = False
    source_relink_performed_by_cli: bool = False
    automatic_music_selection_by_cli: bool = False
    automatic_bgm_fit_by_cli: bool = False
    model_call_performed_by_cli: bool = False
    network_performed_by_cli: bool = False
    image_generation_or_editing_used_by_cli: bool = False
    repair_success_promoted_by_cli: bool = False
    acceptance_success_promoted_by_cli: bool = False
