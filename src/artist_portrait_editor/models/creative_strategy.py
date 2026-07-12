from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from artist_portrait_editor.constants import SCHEMA_VERSION


StrategyId = Literal["emotional_arc", "high_energy", "narrative_clarity", "portrait_highlight"]


class StrategyRange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    source_id: str
    source_in: float = Field(ge=0)
    source_out: float = Field(gt=0)
    planned_duration: float = Field(gt=0)
    role: Literal["hook", "build", "payoff"]
    strategy_score: float = Field(ge=0, le=1)
    evidence_confidence: float = Field(ge=0, le=1)
    selection_reason: str = Field(min_length=1)
    semantic_status: Literal["available", "partial", "unavailable"]


class CreativeStrategy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy_id: StrategyId
    title: str
    creative_intent: str
    target_duration_seconds: float = Field(gt=0)
    planned_duration_seconds: float = Field(gt=0)
    ranges: list[StrategyRange] = Field(min_length=1)
    ordering_logic: str
    retained_qualities: list[str] = Field(min_length=1)
    sacrifices: list[str] = Field(min_length=1)
    source_audio_policy: str
    bgm_policy: str
    text_density_policy: Literal["minimal", "restrained", "moderate"]
    transition_policy: str
    composition_policy: str
    acceptance_checks: list[str] = Field(min_length=5)
    strategy_confidence: float = Field(ge=0, le=1)
    status: Literal["ready", "degraded", "blocked"]
    warnings: list[str] = Field(default_factory=list)


class CreativeStrategyPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    package_id: str
    project_id: str
    target_duration_seconds: float = Field(gt=0)
    editorial_scores_ref: str
    editorial_scores_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    structure_ref: str
    structure_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    bgm_match_ref: str
    bgm_match_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    text_plan_ref: str
    text_plan_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    first_cut_review_ref: str
    first_cut_review_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    second_cut_ref: str
    second_cut_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    strategies: list[CreativeStrategy] = Field(min_length=4, max_length=4)
    materially_distinct: bool
    distinct_range_signatures: int = Field(ge=1, le=4)
    transcript_coverage_ratio: float = Field(ge=0, le=1)
    status: Literal["ready", "degraded", "blocked"]
    selected_strategy_id: StrategyId | None = None
    timeline_mutated: bool = False
    media_rendered: bool = False
    automatic_bgm_selection: bool = False
    invented_semantics: bool = False
    model_call_performed_by_cli: bool = False
    network_performed_by_cli: bool = False
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_four_distinct_strategies(self) -> "CreativeStrategyPackage":
        ids = {item.strategy_id for item in self.strategies}
        expected = {"emotional_arc", "high_energy", "narrative_clarity", "portrait_highlight"}
        if ids != expected:
            raise ValueError("exactly four canonical creative strategies are required")
        if self.materially_distinct and self.distinct_range_signatures != 4:
            raise ValueError("materially distinct package requires four range signatures")
        return self
