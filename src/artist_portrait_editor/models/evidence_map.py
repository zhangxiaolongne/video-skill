from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class EvidenceChannel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["available", "partial", "unavailable", "not_applicable"]
    confidence: float = Field(ge=0, le=1)
    refs: list[str] = Field(default_factory=list)
    facts: dict[str, object] = Field(default_factory=dict)
    missing_reason: str | None = None
    limitations: list[str] = Field(default_factory=list)


class EvidenceMapUnit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    clip_id: str = Field(min_length=1)
    clip_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    scene_method: str = Field(min_length=1)
    scene_confidence: float = Field(ge=0, le=1)
    transcript: EvidenceChannel
    vision: EvidenceChannel
    audio: EvidenceChannel
    user_goal: EvidenceChannel
    semantic_unknowns: list[str] = Field(default_factory=list)
    conflict_risks: list[str] = Field(default_factory=list)
    downstream_usable_features: list[str] = Field(default_factory=list)
    degradation_reasons: list[str] = Field(default_factory=list)


class EvidenceMap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    evidence_map_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    input_fingerprints: dict[str, str]
    unit_count: int = Field(ge=1)
    transcript_coverage_ratio: float = Field(ge=0, le=1)
    keyframe_coverage_ratio: float = Field(ge=0, le=1)
    audio_feature_coverage_ratio: float = Field(ge=0, le=1)
    scene_detection_ratio: float = Field(ge=0, le=1)
    overall_status: Literal["ready", "degraded", "blocked"]
    units: list[EvidenceMapUnit] = Field(min_length=1)
    global_unknowns: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
    paid_api_used: bool = False
    fabricated_semantics: bool = False
