from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION
from artist_portrait_editor.models.source import EvidenceRef


class ProposalRequestStatus(str, Enum):
    blocked = "blocked"
    ready = "ready"


class ProposalRequestPacket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    request_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    status: ProposalRequestStatus
    proposal_context_ref: str = Field(min_length=1)
    text_model_gate_ref: str = Field(min_length=1)
    proposal_context_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    request_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    target_schema_ref: str = Field(min_length=1)
    target_schema_name: str = Field(min_length=1)
    required_proposal_ids: list[str] = Field(min_length=3, max_length=3)
    system_prompt: str = Field(min_length=1)
    developer_prompt: str = Field(min_length=1)
    user_prompt: str = Field(min_length=1)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    blocked_capabilities: list[str] = Field(default_factory=list)
    bgm_requirements: list[str] = Field(default_factory=list)
    validation_requirements: list[str] = Field(default_factory=list)
    refusal_requirements: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
