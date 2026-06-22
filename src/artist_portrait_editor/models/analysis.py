from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION
from artist_portrait_editor.models.source import Assertion, EvidenceRef, MediaKind


class AnalysisRiskFlag(str, Enum):
    inherited_source_risk = "inherited_source_risk"
    keyframe_missing = "keyframe_missing"
    transcript_missing = "transcript_missing"
    audio_missing = "audio_missing"
    audio_only_clip = "audio_only_clip"
    visual_analysis_not_run = "visual_analysis_not_run"
    short_clip = "short_clip"


class AnalysisRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    analysis_id: str = Field(min_length=1)
    clip_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_location: str = Field(min_length=1)
    source_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    clip_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    analysis_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    media_kind: MediaKind
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    duration_seconds: float = Field(gt=0)
    material_type: Assertion
    shot_size: Assertion
    camera_motion: Assertion
    emotion_candidates: Assertion
    action_candidates: Assertion
    visual_quality: Assertion
    original_audio_usability: Assertion
    transcript_refs: list[str] = Field(default_factory=list)
    keyframe_refs: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    risk_flags: list[AnalysisRiskFlag] = Field(default_factory=list)
    notes: str | None = None
