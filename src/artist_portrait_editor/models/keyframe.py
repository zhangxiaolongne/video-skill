from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION
from artist_portrait_editor.models.source import EvidenceRef


class KeyframeRiskFlag(str, Enum):
    cache_missing = "cache_missing"


class KeyframeRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    keyframe_id: str = Field(min_length=1)
    clip_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_location: str = Field(min_length=1)
    source_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    clip_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    frame_index: int = Field(ge=0)
    timestamp_seconds: float = Field(ge=0)
    image_path: str = Field(min_length=1)
    method: str = Field(min_length=1)
    method_version: str = Field(min_length=1)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    risk_flags: list[KeyframeRiskFlag] = Field(default_factory=list)
    notes: str | None = None
