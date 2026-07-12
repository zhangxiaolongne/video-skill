from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from artist_portrait_editor.constants import SCHEMA_VERSION


TemplateId = Literal[
    "stage_portrait", "interview_portrait", "event_montage",
    "short_talking_head", "promotional_film", "documentary_portrait",
]


class TemplateStructureBeat(BaseModel):
    model_config = ConfigDict(extra="forbid")

    beat: Literal["hook", "context", "build", "payoff", "outro"]
    minimum_ratio: float = Field(ge=0, le=1)
    maximum_ratio: float = Field(ge=0, le=1)
    purpose: str


class StyleTemplate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: TemplateId
    name: str
    intended_source_types: list[str] = Field(min_length=1)
    intended_platforms: list[str] = Field(min_length=1)
    intended_aspects: list[str] = Field(min_length=1)
    structure: list[TemplateStructureBeat] = Field(min_length=3)
    shot_duration_range_seconds: tuple[float, float]
    rhythm_policy: str
    source_audio_policy: str
    bgm_policy: str
    subtitle_density: Literal["none", "minimal", "restrained", "moderate", "dense"]
    maximum_characters_per_second: float | None = Field(default=None, gt=0)
    transition_restraint: Literal["strict", "restrained", "moderate"]
    transition_policy: str
    composition_policy: str
    required_evidence: list[str] = Field(min_length=1)
    acceptance_checks: list[str] = Field(min_length=6)
    hard_incompatibilities: list[str] = Field(min_length=1)


class TemplateCompatibility(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_id: TemplateId
    compatibility_score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    status: Literal["compatible", "conditional", "incompatible"]
    matched_signals: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    application_constraints: list[str] = Field(min_length=1)


class StyleTemplatePackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    package_id: str
    project_id: str
    project_ref: str
    project_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sources_ref: str
    sources_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    creative_strategy_ref: str | None = None
    creative_strategy_fingerprint: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    templates: list[StyleTemplate] = Field(min_length=6, max_length=6)
    compatibility: list[TemplateCompatibility] = Field(min_length=6, max_length=6)
    best_match_template_ids: list[TemplateId] = Field(min_length=1)
    selected_template_id: TemplateId | None = None
    source_type_evidence_status: Literal["confirmed", "partial", "unavailable"]
    status: Literal["ready", "degraded", "blocked"]
    template_applied: bool = False
    timeline_mutated: bool = False
    media_rendered: bool = False
    automatic_bgm_selection: bool = False
    invented_source_classification: bool = False
    model_call_performed_by_cli: bool = False
    network_performed_by_cli: bool = False
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_complete_library(self) -> "StyleTemplatePackage":
        expected = {"stage_portrait", "interview_portrait", "event_montage", "short_talking_head", "promotional_film", "documentary_portrait"}
        if {item.template_id for item in self.templates} != expected:
            raise ValueError("style package requires all six canonical templates")
        if {item.template_id for item in self.compatibility} != expected:
            raise ValueError("compatibility must cover all six canonical templates")
        return self
