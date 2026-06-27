from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class ProposalAdapterCheckStatus(str, Enum):
    blocked = "blocked"
    ready_for_future_adapter = "ready_for_future_adapter"


class ProposalMockAdapterHandshakeStatus(str, Enum):
    blocked = "blocked"
    ready_for_future_execution = "ready_for_future_execution"


class ProposalProviderResultStatus(str, Enum):
    blocked = "blocked"
    ready_for_future_result_validation = "ready_for_future_result_validation"


class ProposalProviderOutputQuarantineStatus(str, Enum):
    blocked = "blocked"
    ready_for_future_ingest = "ready_for_future_ingest"


class ProposalExecutionAuthorizationStatus(str, Enum):
    blocked = "blocked"
    ready_for_future_execution = "ready_for_future_execution"


class ProposalExecutionApprovalRequestStatus(str, Enum):
    blocked = "blocked"
    ready_for_future_authorization = "ready_for_future_authorization"


class ProposalExecutionApprovalRecordStatus(str, Enum):
    blocked = "blocked"
    ready_for_future_execution_authorization = (
        "ready_for_future_execution_authorization"
    )


class ProposalExecutionReadinessPlanStatus(str, Enum):
    blocked = "blocked"
    ready_for_future_execution = "ready_for_future_execution"


class ProposalExecutionInputBundleStatus(str, Enum):
    blocked = "blocked"
    ready_for_future_execution_input = "ready_for_future_execution_input"


class ProposalProviderCallDryRunStatus(str, Enum):
    blocked = "blocked"
    ready_for_future_provider_call = "ready_for_future_provider_call"


class ProposalProviderResponseIntakeStatus(str, Enum):
    blocked = "blocked"
    ready_for_future_response_intake = "ready_for_future_response_intake"


class ProposalProviderResponseValidationStatus(str, Enum):
    blocked = "blocked"
    ready_for_future_response_validation = "ready_for_future_response_validation"


class ProposalPromotionAuthorizationStatus(str, Enum):
    blocked = "blocked"
    ready_for_future_promotion = "ready_for_future_promotion"


class ProposalPromotionValidationReportStatus(str, Enum):
    blocked = "blocked"
    ready_for_future_promotion_decision = "ready_for_future_promotion_decision"


class ProposalCanonicalWriteTransactionStatus(str, Enum):
    blocked = "blocked"
    ready_for_future_transaction = "ready_for_future_transaction"


class ProposalAdapterCheckIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    severity: str = Field(pattern=r"^(info|warning|error)$")
    detail: str = Field(min_length=1)
    ref: str | None = None


class ProposalAdapterCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    check_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    status: ProposalAdapterCheckStatus
    provider: str = Field(min_length=1)
    provider_mode: str = Field(min_length=1)
    request_ref: str = Field(min_length=1)
    request_status: str = Field(min_length=1)
    request_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    target_schema_ref: str = Field(min_length=1)
    secret_policy: str = Field(min_length=1)
    allowed_secret_sources: list[str] = Field(default_factory=list)
    checked_refs: list[str] = Field(default_factory=list)
    model_call_performed: bool = False
    network_performed: bool = False
    issues: list[ProposalAdapterCheckIssue] = Field(default_factory=list)


class ProposalProviderRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: str = Field(min_length=1)
    provider_type: str = Field(min_length=1)
    enabled: bool
    execution_mode: str = Field(min_length=1)
    secret_source: str = Field(min_length=1)
    requires_network: bool
    supports_structured_output: bool
    target_schema_ref: str = Field(min_length=1)
    notes: list[str] = Field(default_factory=list)


class ProposalProviderRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    registry_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    request_ref: str = Field(min_length=1)
    adapter_check_ref: str = Field(min_length=1)
    registry_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    selected_provider_id: str = Field(min_length=1)
    providers: list[ProposalProviderRecord] = Field(min_length=1)
    generation_open: bool = False
    model_call_performed: bool = False
    network_performed: bool = False


class ProposalMockAdapterHandshake(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    handshake_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    status: ProposalMockAdapterHandshakeStatus
    provider_id: str = Field(min_length=1)
    request_ref: str = Field(min_length=1)
    registry_ref: str = Field(min_length=1)
    adapter_check_ref: str = Field(min_length=1)
    handshake_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    response_contract_ref: str = Field(min_length=1)
    model_call_performed: bool = False
    network_performed: bool = False
    proposal_content_generated: bool = False
    issues: list[ProposalAdapterCheckIssue] = Field(default_factory=list)


class ProposalProviderResultEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    result_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    status: ProposalProviderResultStatus
    provider_id: str = Field(min_length=1)
    request_ref: str = Field(min_length=1)
    registry_ref: str = Field(min_length=1)
    handshake_ref: str = Field(min_length=1)
    execution_authorization_ref: str = Field(min_length=1)
    output_quarantine_ref: str = Field(min_length=1)
    response_validation_ref: str = Field(min_length=1)
    promotion_authorization_ref: str = Field(min_length=1)
    promotion_validation_report_ref: str = Field(min_length=1)
    canonical_write_transaction_ref: str = Field(min_length=1)
    adapter_check_ref: str = Field(min_length=1)
    result_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    expected_output_kind: str = Field(min_length=1)
    target_schema_ref: str = Field(min_length=1)
    payload_generated: bool = False
    payload_json_ref: str | None = None
    validation_performed: bool = False
    model_call_performed: bool = False
    network_performed: bool = False
    proposal_content_generated: bool = False
    issues: list[ProposalAdapterCheckIssue] = Field(default_factory=list)


class ProposalProviderOutputQuarantine(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    quarantine_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    status: ProposalProviderOutputQuarantineStatus
    provider_id: str = Field(min_length=1)
    request_ref: str = Field(min_length=1)
    registry_ref: str = Field(min_length=1)
    handshake_ref: str = Field(min_length=1)
    execution_authorization_ref: str = Field(min_length=1)
    response_intake_ref: str = Field(min_length=1)
    adapter_check_ref: str = Field(min_length=1)
    quarantine_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    raw_output_captured: bool = False
    raw_output_ref: str | None = None
    raw_output_sha256: str | None = None
    raw_output_bytes: int = Field(default=0, ge=0)
    parsed_payload_generated: bool = False
    parsed_payload_ref: str | None = None
    promoted_to_proposals: bool = False
    validation_performed: bool = False
    model_call_performed: bool = False
    network_performed: bool = False
    proposal_content_generated: bool = False
    quarantine_required: bool = True
    issues: list[ProposalAdapterCheckIssue] = Field(default_factory=list)


class ProposalExecutionAuthorization(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    authorization_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    status: ProposalExecutionAuthorizationStatus
    provider_id: str = Field(min_length=1)
    request_ref: str = Field(min_length=1)
    registry_ref: str = Field(min_length=1)
    handshake_ref: str = Field(min_length=1)
    approval_request_ref: str = Field(min_length=1)
    approval_record_ref: str = Field(min_length=1)
    execution_readiness_ref: str = Field(min_length=1)
    execution_input_bundle_ref: str = Field(min_length=1)
    provider_call_dry_run_ref: str = Field(min_length=1)
    adapter_check_ref: str = Field(min_length=1)
    authorization_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approved_execution_gate: bool = False
    user_approval_required: bool = True
    user_approval_present: bool = False
    credential_policy: str = Field(min_length=1)
    allowed_secret_sources: list[str] = Field(default_factory=list)
    selected_secret_source: str | None = None
    network_required: bool = False
    network_allowed: bool = False
    model_call_allowed: bool = False
    execution_performed: bool = False
    model_call_performed: bool = False
    network_performed: bool = False
    proposal_content_generated: bool = False
    quarantine_required: bool = True
    issues: list[ProposalAdapterCheckIssue] = Field(default_factory=list)


class ProposalExecutionReadinessStage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage_id: str = Field(min_length=1)
    status: ProposalExecutionReadinessPlanStatus
    allowed: bool = False
    performed: bool = False
    ref: str | None = None
    issues: list[ProposalAdapterCheckIssue] = Field(default_factory=list)


class ProposalExecutionReadinessPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    readiness_plan_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    status: ProposalExecutionReadinessPlanStatus
    provider_id: str = Field(min_length=1)
    approval_record_ref: str = Field(min_length=1)
    approval_request_ref: str = Field(min_length=1)
    request_ref: str = Field(min_length=1)
    registry_ref: str = Field(min_length=1)
    handshake_ref: str = Field(min_length=1)
    adapter_check_ref: str = Field(min_length=1)
    readiness_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    secret_source_selection: ProposalExecutionReadinessStage
    credential_access: ProposalExecutionReadinessStage
    execution_plan: ProposalExecutionReadinessStage
    provider_call_preflight: ProposalExecutionReadinessStage
    output_capture_plan: ProposalExecutionReadinessStage
    selected_secret_source: str | None = None
    credential_value_read: bool = False
    network_allowed: bool = False
    model_call_allowed: bool = False
    execution_allowed: bool = False
    execution_performed: bool = False
    model_call_performed: bool = False
    network_performed: bool = False
    raw_output_capture_allowed: bool = False
    raw_output_captured: bool = False
    proposal_content_generated: bool = False
    quarantine_required: bool = True
    issues: list[ProposalAdapterCheckIssue] = Field(default_factory=list)


class ProposalExecutionInputBundleItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1)
    status: ProposalExecutionInputBundleStatus
    allowed: bool = False
    materialized: bool = False
    ref: str | None = None
    issues: list[ProposalAdapterCheckIssue] = Field(default_factory=list)


class ProposalExecutionInputBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    bundle_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    status: ProposalExecutionInputBundleStatus
    provider_id: str = Field(min_length=1)
    request_ref: str = Field(min_length=1)
    registry_ref: str = Field(min_length=1)
    handshake_ref: str = Field(min_length=1)
    adapter_check_ref: str = Field(min_length=1)
    approval_request_ref: str = Field(min_length=1)
    approval_record_ref: str = Field(min_length=1)
    readiness_plan_ref: str = Field(min_length=1)
    input_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    provider_identity: ProposalExecutionInputBundleItem
    request_packet: ProposalExecutionInputBundleItem
    prompt_contract: ProposalExecutionInputBundleItem
    schema_contract: ProposalExecutionInputBundleItem
    approval_chain: ProposalExecutionInputBundleItem
    secret_reference: ProposalExecutionInputBundleItem
    credential_access_policy: ProposalExecutionInputBundleItem
    network_policy: ProposalExecutionInputBundleItem
    quarantine_target: ProposalExecutionInputBundleItem
    output_routing: ProposalExecutionInputBundleItem
    selected_secret_source: str | None = None
    credential_value_read: bool = False
    network_allowed: bool = False
    model_call_allowed: bool = False
    execution_allowed: bool = False
    execution_performed: bool = False
    model_call_performed: bool = False
    network_performed: bool = False
    raw_output_capture_allowed: bool = False
    raw_output_captured: bool = False
    proposal_content_generated: bool = False
    prompt_embedded: bool = False
    quarantine_required: bool = True
    issues: list[ProposalAdapterCheckIssue] = Field(default_factory=list)


class ProposalProviderCallDryRunItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1)
    status: ProposalProviderCallDryRunStatus
    allowed: bool = False
    materialized: bool = False
    ref: str | None = None
    issues: list[ProposalAdapterCheckIssue] = Field(default_factory=list)


class ProposalProviderCallDryRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    dry_run_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    status: ProposalProviderCallDryRunStatus
    provider_id: str = Field(min_length=1)
    request_ref: str = Field(min_length=1)
    registry_ref: str = Field(min_length=1)
    handshake_ref: str = Field(min_length=1)
    adapter_check_ref: str = Field(min_length=1)
    approval_request_ref: str = Field(min_length=1)
    approval_record_ref: str = Field(min_length=1)
    readiness_plan_ref: str = Field(min_length=1)
    input_bundle_ref: str = Field(min_length=1)
    dry_run_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    endpoint_reference: ProposalProviderCallDryRunItem
    auth_header_policy: ProposalProviderCallDryRunItem
    request_body_reference: ProposalProviderCallDryRunItem
    timeout_policy: ProposalProviderCallDryRunItem
    retry_policy: ProposalProviderCallDryRunItem
    rate_limit_policy: ProposalProviderCallDryRunItem
    idempotency_policy: ProposalProviderCallDryRunItem
    network_egress_policy: ProposalProviderCallDryRunItem
    response_capture_policy: ProposalProviderCallDryRunItem
    failure_handling_policy: ProposalProviderCallDryRunItem
    endpoint_resolved: bool = False
    auth_header_materialized: bool = False
    request_body_materialized: bool = False
    timeout_seconds: int | None = None
    retry_count: int = Field(default=0, ge=0)
    idempotency_key_materialized: bool = False
    selected_secret_source: str | None = None
    credential_value_read: bool = False
    network_allowed: bool = False
    model_call_allowed: bool = False
    execution_allowed: bool = False
    execution_performed: bool = False
    model_call_performed: bool = False
    network_performed: bool = False
    raw_output_capture_allowed: bool = False
    raw_output_captured: bool = False
    request_payload_sent: bool = False
    proposal_content_generated: bool = False
    quarantine_required: bool = True
    issues: list[ProposalAdapterCheckIssue] = Field(default_factory=list)


class ProposalProviderResponseIntakeItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1)
    status: ProposalProviderResponseIntakeStatus
    allowed: bool = False
    materialized: bool = False
    ref: str | None = None
    issues: list[ProposalAdapterCheckIssue] = Field(default_factory=list)


class ProposalProviderResponseIntakePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    intake_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    status: ProposalProviderResponseIntakeStatus
    provider_id: str = Field(min_length=1)
    request_ref: str = Field(min_length=1)
    registry_ref: str = Field(min_length=1)
    handshake_ref: str = Field(min_length=1)
    adapter_check_ref: str = Field(min_length=1)
    execution_authorization_ref: str = Field(min_length=1)
    provider_call_dry_run_ref: str = Field(min_length=1)
    intake_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    response_channel: ProposalProviderResponseIntakeItem
    raw_output_location: ProposalProviderResponseIntakeItem
    content_type_policy: ProposalProviderResponseIntakeItem
    size_limit_policy: ProposalProviderResponseIntakeItem
    checksum_policy: ProposalProviderResponseIntakeItem
    redaction_policy: ProposalProviderResponseIntakeItem
    parser_selection: ProposalProviderResponseIntakeItem
    validation_queue: ProposalProviderResponseIntakeItem
    promotion_gate: ProposalProviderResponseIntakeItem
    audit_trail: ProposalProviderResponseIntakeItem
    response_channel_open: bool = False
    raw_output_location_materialized: bool = False
    content_type_validated: bool = False
    size_limit_bytes: int = Field(default=0, ge=0)
    checksum_computed: bool = False
    redaction_performed: bool = False
    parser_selected: bool = False
    validation_enqueued: bool = False
    promotion_allowed: bool = False
    audit_event_written: bool = False
    raw_output_captured: bool = False
    parsed_payload_generated: bool = False
    validation_performed: bool = False
    promoted_to_proposals: bool = False
    model_call_performed: bool = False
    network_performed: bool = False
    proposal_content_generated: bool = False
    quarantine_required: bool = True
    issues: list[ProposalAdapterCheckIssue] = Field(default_factory=list)


class ProposalProviderResponseValidationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1)
    status: ProposalProviderResponseValidationStatus
    allowed: bool = False
    materialized: bool = False
    ref: str | None = None
    issues: list[ProposalAdapterCheckIssue] = Field(default_factory=list)


class ProposalProviderResponseValidationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    validation_plan_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    status: ProposalProviderResponseValidationStatus
    provider_id: str = Field(min_length=1)
    request_ref: str = Field(min_length=1)
    registry_ref: str = Field(min_length=1)
    handshake_ref: str = Field(min_length=1)
    adapter_check_ref: str = Field(min_length=1)
    response_intake_ref: str = Field(min_length=1)
    output_quarantine_ref: str = Field(min_length=1)
    target_schema_ref: str = Field(min_length=1)
    validation_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    quarantine_input_binding: ProposalProviderResponseValidationItem
    content_type_check: ProposalProviderResponseValidationItem
    size_limit_check: ProposalProviderResponseValidationItem
    checksum_verification: ProposalProviderResponseValidationItem
    redaction_verification: ProposalProviderResponseValidationItem
    parser_contract: ProposalProviderResponseValidationItem
    json_syntax_validation: ProposalProviderResponseValidationItem
    schema_validation: ProposalProviderResponseValidationItem
    semantic_validation: ProposalProviderResponseValidationItem
    promotion_decision: ProposalProviderResponseValidationItem
    quarantine_input_bound: bool = False
    content_type_checked: bool = False
    size_limit_checked: bool = False
    checksum_verified: bool = False
    redaction_verified: bool = False
    parser_contract_selected: bool = False
    json_syntax_validated: bool = False
    schema_validated: bool = False
    semantic_validation_performed: bool = False
    promotion_decided: bool = False
    raw_output_read: bool = False
    parsed_payload_generated: bool = False
    validation_performed: bool = False
    promoted_to_proposals: bool = False
    audit_event_written: bool = False
    model_call_performed: bool = False
    network_performed: bool = False
    proposal_content_generated: bool = False
    quarantine_required: bool = True
    issues: list[ProposalAdapterCheckIssue] = Field(default_factory=list)


class ProposalPromotionAuthorizationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1)
    status: ProposalPromotionAuthorizationStatus
    allowed: bool = False
    materialized: bool = False
    ref: str | None = None
    issues: list[ProposalAdapterCheckIssue] = Field(default_factory=list)


class ProposalPromotionAuthorizationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    promotion_plan_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    status: ProposalPromotionAuthorizationStatus
    provider_id: str = Field(min_length=1)
    request_ref: str = Field(min_length=1)
    registry_ref: str = Field(min_length=1)
    adapter_check_ref: str = Field(min_length=1)
    response_validation_ref: str = Field(min_length=1)
    output_quarantine_ref: str = Field(min_length=1)
    target_schema_ref: str = Field(min_length=1)
    promotion_target_ref: str = Field(min_length=1)
    promotion_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    validation_report_binding: ProposalPromotionAuthorizationItem
    schema_validation_requirement: ProposalPromotionAuthorizationItem
    semantic_validation_requirement: ProposalPromotionAuthorizationItem
    evidence_validation_requirement: ProposalPromotionAuthorizationItem
    risk_acceptance_requirement: ProposalPromotionAuthorizationItem
    proposal_identity_requirement: ProposalPromotionAuthorizationItem
    overwrite_policy: ProposalPromotionAuthorizationItem
    atomic_write_policy: ProposalPromotionAuthorizationItem
    provenance_binding: ProposalPromotionAuthorizationItem
    final_promotion_authorization: ProposalPromotionAuthorizationItem
    validation_report_bound: bool = False
    schema_validation_passed: bool = False
    semantic_validation_passed: bool = False
    evidence_validation_passed: bool = False
    risk_acceptance_recorded: bool = False
    proposal_ids_unique: bool = False
    overwrite_allowed: bool = False
    atomic_write_ready: bool = False
    provenance_bound: bool = False
    promotion_authorized: bool = False
    promotion_performed: bool = False
    proposals_file_written: bool = False
    audit_event_written: bool = False
    model_call_performed: bool = False
    network_performed: bool = False
    proposal_content_generated: bool = False
    quarantine_required: bool = True
    issues: list[ProposalAdapterCheckIssue] = Field(default_factory=list)


class ProposalPromotionValidationCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_id: str = Field(min_length=1)
    status: ProposalPromotionValidationReportStatus
    performed: bool = False
    passed: bool = False
    issue_count: int = Field(default=0, ge=0)
    ref: str | None = None
    issues: list[ProposalAdapterCheckIssue] = Field(default_factory=list)


class ProposalPromotionValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    report_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    status: ProposalPromotionValidationReportStatus
    provider_id: str = Field(min_length=1)
    request_ref: str = Field(min_length=1)
    response_validation_ref: str = Field(min_length=1)
    promotion_authorization_ref: str = Field(min_length=1)
    output_quarantine_ref: str = Field(min_length=1)
    target_schema_ref: str = Field(min_length=1)
    promotion_target_ref: str = Field(min_length=1)
    report_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    input_binding_check: ProposalPromotionValidationCheck
    schema_result_check: ProposalPromotionValidationCheck
    semantic_result_check: ProposalPromotionValidationCheck
    evidence_traceability_check: ProposalPromotionValidationCheck
    risk_result_check: ProposalPromotionValidationCheck
    proposal_identity_check: ProposalPromotionValidationCheck
    overwrite_conflict_check: ProposalPromotionValidationCheck
    atomic_write_readiness_check: ProposalPromotionValidationCheck
    provenance_integrity_check: ProposalPromotionValidationCheck
    final_authorization_check: ProposalPromotionValidationCheck
    checks_performed: int = Field(default=0, ge=0)
    checks_passed: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    warning_count: int = Field(default=0, ge=0)
    overall_passed: bool = False
    promotion_recommended: bool = False
    promotion_authorized: bool = False
    promotion_performed: bool = False
    proposals_file_written: bool = False
    model_call_performed: bool = False
    network_performed: bool = False
    proposal_content_generated: bool = False
    quarantine_required: bool = True
    issues: list[ProposalAdapterCheckIssue] = Field(default_factory=list)


class ProposalCanonicalWriteTransactionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1)
    status: ProposalCanonicalWriteTransactionStatus
    allowed: bool = False
    materialized: bool = False
    ref: str | None = None
    issues: list[ProposalAdapterCheckIssue] = Field(default_factory=list)


class ProposalCanonicalWriteTransactionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    transaction_plan_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    status: ProposalCanonicalWriteTransactionStatus
    request_ref: str = Field(min_length=1)
    promotion_authorization_ref: str = Field(min_length=1)
    promotion_validation_report_ref: str = Field(min_length=1)
    canonical_target_ref: str = Field(min_length=1)
    transaction_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    target_lock: ProposalCanonicalWriteTransactionItem
    prewrite_snapshot: ProposalCanonicalWriteTransactionItem
    temporary_file: ProposalCanonicalWriteTransactionItem
    schema_prewrite_check: ProposalCanonicalWriteTransactionItem
    durability_policy: ProposalCanonicalWriteTransactionItem
    atomic_replace: ProposalCanonicalWriteTransactionItem
    conflict_detection: ProposalCanonicalWriteTransactionItem
    rollback_plan: ProposalCanonicalWriteTransactionItem
    audit_commit: ProposalCanonicalWriteTransactionItem
    postcommit_verification: ProposalCanonicalWriteTransactionItem
    lock_acquired: bool = False
    snapshot_created: bool = False
    temporary_file_created: bool = False
    schema_prewrite_passed: bool = False
    fsync_performed: bool = False
    atomic_replace_performed: bool = False
    conflict_check_performed: bool = False
    rollback_prepared: bool = False
    rollback_performed: bool = False
    audit_commit_written: bool = False
    postcommit_verified: bool = False
    transaction_started: bool = False
    transaction_committed: bool = False
    proposals_file_written: bool = False
    model_call_performed: bool = False
    network_performed: bool = False
    proposal_content_generated: bool = False
    issues: list[ProposalAdapterCheckIssue] = Field(default_factory=list)


class ProposalExecutionApprovalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    approval_record_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    status: ProposalExecutionApprovalRecordStatus
    provider_id: str = Field(min_length=1)
    approval_request_ref: str = Field(min_length=1)
    request_ref: str = Field(min_length=1)
    registry_ref: str = Field(min_length=1)
    handshake_ref: str = Field(min_length=1)
    adapter_check_ref: str = Field(min_length=1)
    approval_record_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approval_granted: bool = False
    approval_actor: str | None = None
    approval_recorded_at: str | None = None
    approval_scope: str = Field(min_length=1)
    allowed_secret_sources: list[str] = Field(default_factory=list)
    selected_secret_source: str | None = None
    credential_value_read: bool = False
    credential_value_ref: str | None = None
    network_allowed: bool = False
    model_call_allowed: bool = False
    execution_allowed: bool = False
    execution_performed: bool = False
    model_call_performed: bool = False
    network_performed: bool = False
    proposal_content_generated: bool = False
    quarantine_required: bool = True
    issues: list[ProposalAdapterCheckIssue] = Field(default_factory=list)


class ProposalExecutionApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    approval_request_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    status: ProposalExecutionApprovalRequestStatus
    provider_id: str = Field(min_length=1)
    request_ref: str = Field(min_length=1)
    registry_ref: str = Field(min_length=1)
    handshake_ref: str = Field(min_length=1)
    adapter_check_ref: str = Field(min_length=1)
    approval_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approval_required: bool = True
    approval_recorded: bool = False
    approval_record_ref: str | None = None
    secret_source_selection_required: bool = True
    allowed_secret_sources: list[str] = Field(default_factory=list)
    selected_secret_source: str | None = None
    credential_value_read: bool = False
    credential_value_ref: str | None = None
    network_allowed: bool = False
    model_call_allowed: bool = False
    execution_performed: bool = False
    model_call_performed: bool = False
    network_performed: bool = False
    proposal_content_generated: bool = False
    quarantine_required: bool = True
    issues: list[ProposalAdapterCheckIssue] = Field(default_factory=list)
