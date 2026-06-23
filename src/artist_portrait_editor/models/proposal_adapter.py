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
