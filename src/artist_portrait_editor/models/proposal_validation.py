from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class ProposalValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    severity: str = Field(pattern=r"^(info|warning|error)$")
    detail: str = Field(min_length=1)
    proposal_id: str | None = None
    ref: str | None = None


class ProposalValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    report_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    proposal_set_id: str = Field(min_length=1)
    proposal_context_ref: str = Field(min_length=1)
    proposals_ref: str = Field(min_length=1)
    input_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    proposal_count: int = Field(ge=0)
    issue_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    issues: list[ProposalValidationIssue] = Field(default_factory=list)
