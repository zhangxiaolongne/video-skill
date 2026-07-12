from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from artist_portrait_editor.constants import SCHEMA_VERSION


class TemplateStructureBeat(BaseModel):
    model_config = ConfigDict(extra="forbid")
    beat: str = Field(min_length=1)
    minimum_ratio: float = Field(ge=0, le=1)
    maximum_ratio: float = Field(ge=0, le=1)
    purpose: str = Field(min_length=1)


class ContentFormTemplate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    template_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    form_family: Literal["performance", "spoken", "fiction", "process", "event", "promotional", "documentary", "cross_media", "fan_creation"]
    intended_source_types: list[str] = Field(min_length=1)
    brief_keywords: list[str] = Field(min_length=1)
    intended_platforms: list[str] = Field(min_length=1)
    intended_aspects: list[str] = Field(min_length=1)
    structure: list[TemplateStructureBeat] = Field(min_length=3)
    shot_duration_range_seconds: tuple[float, float]
    rhythm_policy: str
    source_audio_policy: str
    bgm_policy: str
    subtitle_density: Literal["none", "minimal", "restrained", "moderate", "dense"]
    maximum_characters_per_second: float | None = Field(default=None, gt=0)
    transition_policy: str
    composition_policy: str
    required_evidence: list[str] = Field(min_length=1)
    acceptance_checks: list[str] = Field(min_length=6)
    hard_incompatibilities: list[str] = Field(min_length=1)


class AestheticStyle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    style_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    emotional_palette: list[str] = Field(min_length=1)
    pacing_character: str
    image_character: str
    color_direction: str
    bgm_character: str
    text_character: str
    transition_character: str
    suitable_intents: list[str] = Field(min_length=1)
    failure_risks: list[str] = Field(min_length=1)
    evidence_requirements: list[str] = Field(min_length=1)


class CreativeTechnique(BaseModel):
    model_config = ConfigDict(extra="forbid")
    technique_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    default_rule_mode: Literal["follow", "bend", "break"]
    form: str
    expected_feeling: str
    meaning_requirement: str
    principal_risk: str
    playback_verification: str
    fallback: str


class EmotionalArc(BaseModel):
    model_config = ConfigDict(extra="forbid")
    arc_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    phases: list[str] = Field(min_length=2)
    reversal_strength: Literal["none", "subtle", "strong", "extreme"]
    evidence_requirement: str
    failure_mode: str


class TemplateCompatibility(BaseModel):
    model_config = ConfigDict(extra="forbid")
    template_id: str
    compatibility_score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    status: Literal["compatible", "conditional", "incompatible"]
    matched_signals: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    application_constraints: list[str] = Field(min_length=1)


class CreativeCombinationExample(BaseModel):
    model_config = ConfigDict(extra="forbid")
    combination_id: str
    content_template_id: str
    aesthetic_style_id: str
    creative_strategy_id: str
    technique_ids: list[str] = Field(min_length=1)
    emotional_arc_id: str
    rule_modes: dict[str, Literal["follow", "bend", "break"]]
    concept: str
    intended_effect: str
    meaning: str
    risks: list[str] = Field(min_length=1)
    illustrative_only: bool = True


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
    content_templates: list[ContentFormTemplate] = Field(min_length=12)
    aesthetic_styles: list[AestheticStyle] = Field(min_length=12)
    creative_techniques: list[CreativeTechnique] = Field(min_length=8)
    emotional_arcs: list[EmotionalArc] = Field(min_length=8)
    content_compatibility: list[TemplateCompatibility] = Field(min_length=12)
    best_match_content_template_ids: list[str] = Field(min_length=1)
    combination_examples: list[CreativeCombinationExample] = Field(min_length=6)
    selected_content_template_id: str | None = None
    selected_aesthetic_style_id: str | None = None
    selected_combination_id: str | None = None
    source_type_evidence_status: Literal["confirmed", "partial", "unavailable"]
    custom_content_templates_supported: bool = True
    custom_aesthetic_styles_supported: bool = True
    mixed_content_forms_supported: bool = True
    mixed_aesthetic_styles_supported: bool = True
    rule_modes_supported: list[Literal["follow", "bend", "break"]] = Field(default_factory=lambda: ["follow", "bend", "break"])
    extreme_reversal_supported: bool = True
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
    def require_open_composable_space(self) -> "StyleTemplatePackage":
        collections = [
            (self.content_templates, "template_id"), (self.aesthetic_styles, "style_id"),
            (self.creative_techniques, "technique_id"), (self.emotional_arcs, "arc_id"),
        ]
        for items, key in collections:
            values = [getattr(item, key) for item in items]
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {key} values are not allowed")
        template_ids = {item.template_id for item in self.content_templates}
        if {item.template_id for item in self.content_compatibility} != template_ids:
            raise ValueError("compatibility must cover every content template")
        if not {"follow", "bend", "break"}.issubset(self.rule_modes_supported):
            raise ValueError("follow, bend, and break rule modes are required")
        return self
