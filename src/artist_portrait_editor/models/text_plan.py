from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from artist_portrait_editor.constants import SCHEMA_VERSION


class TextPlanElement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    element_id: str
    element_type: Literal["title", "subtitle", "emphasis", "pause", "empty_space"]
    candidate_id: str | None = None
    source_id: str | None = None
    source_in: float | None = Field(default=None, ge=0)
    source_out: float | None = Field(default=None, gt=0)
    timeline_in: float = Field(ge=0)
    timeline_out: float = Field(gt=0)
    content: str | None = None
    evidence_status: Literal["available", "partial", "unavailable", "not_applicable"]
    evidence_refs: list[str] = Field(default_factory=list)
    character_count: int = Field(ge=0)
    characters_per_second: float | None = Field(default=None, ge=0)
    reading_risk: Literal["none", "low", "medium", "high", "unavailable"]
    safe_region: Literal["top", "center", "lower_third", "full_frame_reservation"]
    safe_region_status: Literal["reviewed_sample_only", "manual_review_required", "unavailable"]
    audio_pressure: Literal["low", "medium", "high", "unknown"]
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_timing_and_content(self) -> "TextPlanElement":
        if self.timeline_out <= self.timeline_in:
            raise ValueError("text element timeline_out must exceed timeline_in")
        if self.content is None and self.character_count != 0:
            raise ValueError("contentless text element must have zero characters")
        if self.content is not None and self.character_count != len(self.content):
            raise ValueError("character_count must equal content length")
        return self


class TextOptionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    option_id: Literal["short", "standard", "extended"]
    duration_seconds: float = Field(gt=0)
    elements: list[TextPlanElement] = Field(min_length=1)
    title_count: int = Field(ge=0)
    subtitle_count: int = Field(ge=0)
    unavailable_subtitle_slot_count: int = Field(ge=0)
    emphasis_count: int = Field(ge=0)
    pause_or_space_count: int = Field(ge=0)
    maximum_text_density_cps: float | None = Field(default=None, ge=0)
    status: Literal["ready", "degraded", "blocked"]
    warnings: list[str] = Field(default_factory=list)


class TextTimingPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    text_plan_id: str
    project_id: str
    structure_recommendation_id: str
    structure_ref: str
    structure_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evidence_map_id: str
    evidence_map_ref: str
    evidence_map_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    bgm_match_id: str
    bgm_match_ref: str
    bgm_match_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    edit_brief_id: str
    title_text: str
    options: list[TextOptionPlan] = Field(min_length=3, max_length=3)
    transcript_coverage_ratio: float = Field(ge=0, le=1)
    status: Literal["ready", "degraded", "blocked"]
    warnings: list[str] = Field(default_factory=list)
    invented_transcript: bool = False
    invented_lyrics: bool = False
    text_burned_into_media: bool = False
    timeline_mutated: bool = False
    media_rendered: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
