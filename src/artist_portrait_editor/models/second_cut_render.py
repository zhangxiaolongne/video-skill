from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class SecondCutSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    segment_id: str
    candidate_id: str
    role: Literal["hook", "build", "payoff"]
    source_id: str
    source_ref: str
    source_in: float = Field(ge=0)
    source_out: float = Field(gt=0)
    timeline_start: float = Field(ge=0)
    timeline_end: float = Field(gt=0)
    ranking_score: float = Field(ge=0, le=1)
    ranking_confidence: float = Field(ge=0, le=1)
    original_audio_rendered: bool
    reframe_applied: bool = False
    text_applied: bool = False


class SecondCutComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: Literal[
        "duration_structure", "opening", "middle_pacing", "ending",
        "source_audio_bgm", "text", "composition", "semantic_continuity",
        "technical_delivery",
    ]
    status: Literal["improved", "preserved", "unresolved", "regressed"]
    finding: str = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)
    next_action: str = Field(min_length=1)


class SecondCutRender(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    render_id: str
    project_id: str
    selected_option_id: Literal["short", "standard", "extended"]
    selection_explicit: bool = True
    structure_ref: str
    structure_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    first_cut_review_ref: str
    first_cut_review_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    editorial_scores_ref: str
    editorial_scores_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    bgm_match_ref: str
    bgm_match_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    text_plan_ref: str
    text_plan_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sources_ref: str
    sources_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    first_cut_ref: str
    first_cut_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    output_ref: str
    output_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    target_duration_seconds: float = Field(gt=0)
    actual_duration_seconds: float = Field(gt=0)
    duration_delta_seconds: float
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    frame_rate: float = Field(gt=0)
    video_present: bool
    audio_present: bool
    media_valid: bool
    candidate_timeline: list[SecondCutSegment] = Field(min_length=1)
    source_audio_retained: bool
    added_bgm_applied: bool = False
    text_applied: bool = False
    reframes_applied: bool = False
    canonical_timeline_mutated: bool = False
    canonical_final_overwritten: bool = False
    comparisons: list[SecondCutComparison] = Field(min_length=9, max_length=9)
    publishability: Literal["not_publishable", "conditional", "publishable"]
    warnings: list[str] = Field(default_factory=list)
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
    automatic_music_selection: bool = False
