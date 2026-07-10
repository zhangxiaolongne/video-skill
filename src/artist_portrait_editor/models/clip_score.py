from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION
from artist_portrait_editor.models.source import EvidenceRef, MediaKind


class ClipScoreComponent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(pattern=r"^(available|missing|not_applicable|failed)$")
    score: float = Field(ge=0.0, le=1.0)
    detail: str = Field(min_length=1)


class ClipAudioEnergy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(pattern=r"^(available|missing|not_applicable|failed)$")
    rms: float | None = Field(default=None, ge=0.0)
    dbfs: float | None = None
    score: float = Field(ge=0.0, le=1.0)
    method: str = Field(min_length=1)
    detail: str = Field(min_length=1)


class ClipScoreRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    clip_score_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    clip_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_location: str = Field(min_length=1)
    source_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    clip_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    scoring_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    media_kind: MediaKind
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    duration_seconds: float = Field(gt=0)
    evidence_level: str = Field(
        pattern=r"^(clips_only|analysis_available|transcript_available|keyframe_available|multi_modal)$"
    )
    speech_score: ClipScoreComponent
    transcript_density_score: ClipScoreComponent
    audio_energy: ClipAudioEnergy
    visual_change_score: ClipScoreComponent
    keyframe_coverage_score: ClipScoreComponent
    analysis_confidence_score: ClipScoreComponent
    duration_fit_score: ClipScoreComponent
    source_risk_penalty: float = Field(ge=0.0, le=1.0)
    overall_score: float = Field(ge=0.0, le=1.0)
    selection_tier: str = Field(pattern=r"^(hero|support|context|review|drop)$")
    keep_recommendation: str = Field(pattern=r"^(keep|consider|review|drop)$")
    keyframe_cluster_id: str | None = None
    transcript_refs: list[str] = Field(default_factory=list)
    keyframe_refs: list[str] = Field(default_factory=list)
    analysis_refs: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    commands_executed: bool = False
    media_rendered: bool = False
    timeline_mutated: bool = False
    edit_points_moved: bool = False
    automatic_music_selection: bool = False
    automatic_bgm_fit: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
    image_generation_or_editing_used: bool = False
