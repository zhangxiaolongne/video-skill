from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION
from artist_portrait_editor.models.config import ContentPolicy, CreativeBrief
from artist_portrait_editor.models.source import EvidenceRef, MediaKind


class ProposalSourceContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    primary_location: str = Field(min_length=1)
    media_kind: MediaKind
    source_type: str
    rights_status: str
    duration_seconds: float = Field(gt=0)
    forbidden_by_user: bool
    risk_flags: list[str] = Field(default_factory=list)


class ProposalClipContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clip_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_location: str = Field(min_length=1)
    media_kind: MediaKind
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    duration_seconds: float = Field(gt=0)
    method: str = Field(min_length=1)
    risk_flags: list[str] = Field(default_factory=list)


class ProposalAnalysisContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    analysis_id: str = Field(min_length=1)
    clip_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    material_type: str
    original_audio_usability: str
    transcript_refs: list[str] = Field(default_factory=list)
    keyframe_refs: list[str] = Field(default_factory=list)
    pending_visual_fields: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    review_score: float = Field(ge=0)


class ProposalContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    context_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    material_map_ref: str = Field(min_length=1)
    material_map_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sources_ref: str = Field(min_length=1)
    clips_ref: str = Field(min_length=1)
    analysis_ref: str = Field(min_length=1)
    input_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    creative_brief: CreativeBrief
    content_policy: ContentPolicy
    proposal_ids_required: list[str] = Field(min_length=3, max_length=3)
    sources: list[ProposalSourceContext] = Field(default_factory=list)
    clips: list[ProposalClipContext] = Field(default_factory=list)
    analyses: list[ProposalAnalysisContext] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    bgm_requirements: list[str] = Field(default_factory=list)
    blocked_capabilities: list[str] = Field(default_factory=list)
