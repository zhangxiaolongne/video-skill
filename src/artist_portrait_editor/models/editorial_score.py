from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class EditorialDimension(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    evidence_status: Literal["available", "partial", "unavailable"]
    rationale: list[str] = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)


class EditorialCandidateScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1)
    unit_id: str = Field(min_length=1)
    clip_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    hook: EditorialDimension
    emotion: EditorialDimension
    information_density: EditorialDimension
    visual_usability: EditorialDimension
    audio_usability: EditorialDimension
    rhythm: EditorialDimension
    ending_resonance: EditorialDimension
    risk_penalty: EditorialDimension
    highlight_score: float = Field(ge=0, le=1)
    hook_score: float = Field(ge=0, le=1)
    ending_score: float = Field(ge=0, le=1)
    ranking_confidence: float = Field(ge=0, le=1)
    highlight_rank: int = Field(ge=1)
    hook_rank: int = Field(ge=1)
    ending_rank: int = Field(ge=1)
    user_goal_ref: str = Field(min_length=1)
    unknowns: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class EditorialScoreSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    score_set_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    evidence_map_id: str = Field(min_length=1)
    evidence_map_ref: str = Field(min_length=1)
    evidence_map_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    candidate_count: int = Field(ge=1)
    status: Literal["ready", "degraded", "blocked"]
    candidates: list[EditorialCandidateScore] = Field(min_length=1)
    top_highlight_ids: list[str] = Field(min_length=1)
    top_hook_ids: list[str] = Field(min_length=1)
    top_ending_ids: list[str] = Field(min_length=1)
    warnings: list[str] = Field(default_factory=list)
    first_clip_position_bonus: bool = False
    last_clip_position_bonus: bool = False
    loudness_treated_as_emotion: bool = False
    missing_evidence_treated_as_zero_quality: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
    media_rendered: bool = False
    timeline_mutated: bool = False
