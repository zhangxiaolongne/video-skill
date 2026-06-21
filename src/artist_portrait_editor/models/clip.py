from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from artist_portrait_editor.constants import SCHEMA_VERSION
from artist_portrait_editor.models.source import EvidenceRef, MediaKind, SourceRiskFlag


class ClipMethod(str, Enum):
    fixed_window = "fixed_window"


class ClipRiskFlag(str, Enum):
    short_tail = "short_tail"
    inherited_source_risk = "inherited_source_risk"


class ClipBoundary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    duration_seconds: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_boundary(self) -> "ClipBoundary":
        if self.end_seconds <= self.start_seconds:
            raise ValueError("end_seconds must be greater than start_seconds")
        expected_duration = self.end_seconds - self.start_seconds
        if abs(expected_duration - self.duration_seconds) > 0.001:
            raise ValueError("duration_seconds must equal end_seconds - start_seconds")
        return self


class ClipRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    clip_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_location: str = Field(min_length=1)
    source_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    clip_index: int = Field(ge=0)
    media_kind: MediaKind
    boundary: ClipBoundary
    method: ClipMethod
    method_version: str = Field(min_length=1)
    boundary_confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    inherited_source_risk_flags: list[SourceRiskFlag] = Field(default_factory=list)
    risk_flags: list[ClipRiskFlag] = Field(default_factory=list)
    notes: str | None = None
