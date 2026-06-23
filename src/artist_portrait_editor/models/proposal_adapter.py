from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class ProposalAdapterCheckStatus(str, Enum):
    blocked = "blocked"
    ready_for_future_adapter = "ready_for_future_adapter"


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
