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
