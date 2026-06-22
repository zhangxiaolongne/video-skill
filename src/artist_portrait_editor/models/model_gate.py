from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class TextModelGateStatus(str, Enum):
    blocked = "blocked"
    ready = "ready"


class TextModelGate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    gate_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    proposal_context_ref: str = Field(min_length=1)
    proposal_context_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    status: TextModelGateStatus
    remote_text_model_allowed: bool
    text_model_capability: bool
    include_absolute_paths_in_remote_requests: bool
    reasons: list[str] = Field(default_factory=list)
    required_next_steps: list[str] = Field(default_factory=list)
