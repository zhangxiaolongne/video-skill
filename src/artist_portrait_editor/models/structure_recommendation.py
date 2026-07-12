from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from artist_portrait_editor.constants import SCHEMA_VERSION


class RecommendedRange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: str
    role: Literal["hook", "build", "payoff"]
    source_id: str
    source_in: float = Field(ge=0)
    source_out: float = Field(gt=0)
    planned_duration: float = Field(gt=0)
    score: float = Field(ge=0, le=1)
    ranking_confidence: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1)


class StructureOption(BaseModel):
    model_config = ConfigDict(extra="forbid")
    option_id: Literal["short", "standard", "extended"]
    target_duration_seconds: float = Field(gt=0)
    estimated_duration_seconds: float = Field(gt=0)
    duration_source: Literal["derived", "user_or_config_target"]
    ranges: list[RecommendedRange] = Field(min_length=1)
    role_allocation_seconds: dict[str, float]
    retained_qualities: list[str] = Field(min_length=1)
    sacrifices: list[str] = Field(min_length=1)
    coupled_risks: list[str] = Field(min_length=1)
    recommendation_confidence: float = Field(ge=0, le=1)


class StructureRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = SCHEMA_VERSION
    recommendation_id: str
    project_id: str
    score_set_id: str
    score_set_ref: str
    score_set_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    edit_brief_id: str
    edit_brief_ref: str
    edit_brief_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    target_platform: str
    explicit_standard_duration_seconds: float = Field(gt=0)
    options: list[StructureOption] = Field(min_length=3, max_length=3)
    recommended_option_id: Literal["short", "standard", "extended"]
    status: Literal["ready", "degraded"]
    warnings: list[str] = Field(default_factory=list)
    timeline_mutated: bool = False
    edit_points_applied: bool = False
    media_rendered: bool = False
    automatic_music_selection: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False

    @model_validator(mode="after")
    def distinct_options(self) -> "StructureRecommendation":
        ids = [item.option_id for item in self.options]
        if set(ids) != {"short", "standard", "extended"}:
            raise ValueError("exactly short, standard, and extended options are required")
        durations = {item.option_id: item.target_duration_seconds for item in self.options}
        if not durations["short"] < durations["standard"] < durations["extended"]:
            raise ValueError("duration options must be strictly increasing")
        return self
