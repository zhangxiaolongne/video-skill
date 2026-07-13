from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class VersionDomainAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: str = Field(pattern=r"^(hook|emotional_arc|information_density|bgm_conflict|text_burden|ending_strength|platform_fit)$")
    status: str = Field(pattern=r"^(known|partial|unavailable)$")
    score: float | None = Field(default=None, ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    finding: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ReviewedVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_id: str = Field(min_length=1)
    version_kind: str = Field(pattern=r"^(canonical_timeline|rendered_second_cut|revision_candidate)$")
    artifact_ref: str = Field(min_length=1)
    artifact_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evidence_level: str = Field(pattern=r"^(rendered_media|timeline_candidate|plan_only)$")
    duration_seconds: float = Field(gt=0)
    segment_count: int = Field(ge=1)
    media_valid: bool | None = None
    current: bool
    assessments: list[VersionDomainAssessment] = Field(min_length=7, max_length=7)
    unresolved_domains: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class VersionPairComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    left_version_id: str
    right_version_id: str
    comparable_domains: list[str] = Field(default_factory=list)
    left_advantages: list[str] = Field(default_factory=list)
    right_advantages: list[str] = Field(default_factory=list)
    unresolved_domains: list[str] = Field(default_factory=list)
    tradeoff_summary: str = Field(min_length=1)


class GoalAdvantage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str = Field(pattern=r"^(fast_hook|emotional_depth|information_clarity|voice_first|text_light|strong_ending|platform_delivery)$")
    leading_version_ids: list[str] = Field(default_factory=list)
    status: str = Field(pattern=r"^(supported|tie|unavailable)$")
    rationale: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class VersionReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    review_id: str
    project_id: str
    status: str = Field(pattern=r"^(ready|warning|blocked)$")
    version_count: int = Field(ge=2)
    versions: list[ReviewedVersion] = Field(min_length=2)
    pairwise_comparisons: list[VersionPairComparison] = Field(min_length=1)
    goal_advantages: list[GoalAdvantage] = Field(min_length=7, max_length=7)
    overall_winner_id: None = None
    selection_required: bool = True
    comparison_is_aesthetic_acceptance: bool = False
    warnings: list[str] = Field(default_factory=list)
    canonical_timeline_mutated: bool = False
    media_rendered: bool = False
    automatic_version_selection: bool = False
    automatic_music_selection: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
