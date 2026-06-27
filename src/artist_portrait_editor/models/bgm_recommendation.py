from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from artist_portrait_editor.constants import SCHEMA_VERSION


class BgmRecommendationContextCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    music_candidate_id: str = Field(min_length=1)
    input_mode: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    duration: float = Field(gt=0)
    rights_status: str = Field(min_length=1)
    mixed_audio: bool
    user_intent: str = Field(min_length=1)
    integrated_loudness_lufs: float | None = None
    bpm: float | None = None
    beat_analysis_status: str = Field(min_length=1)
    analysis_summary: dict = Field(default_factory=dict)


class BgmRecommendationContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    context_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    timeline_id: str = Field(min_length=1)
    timeline_ref: str = Field(min_length=1)
    timeline_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    proposal_id: str = Field(min_length=1)
    target_duration: float = Field(gt=0)
    timeline_music_status: str = Field(min_length=1)
    proposal_sound_structure: list[str] = Field(default_factory=list)
    candidate_ledger_ref: str = ".artist-portrait/data/bgm_candidates.json"
    candidate_ledger_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    analysis_ref: str | None = None
    analysis_fingerprint: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    candidates: list[BgmRecommendationContextCandidate] = Field(default_factory=list)
    recommendation_policy: list[str] = Field(default_factory=list)


class BgmRecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    request_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    context_id: str = Field(min_length=1)
    required_root_model: str = "BgmRecommendationSet"
    allowed_methods: list[str] = Field(default_factory=lambda: ["host_agent", "codex", "chatgpt", "local_model", "third_party_tool"])
    instructions: list[str] = Field(default_factory=list)


class BgmRecommendationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendation_id: str = Field(min_length=1)
    music_candidate_id: str = Field(min_length=1)
    rank: int = Field(ge=1)
    fit_rationale: str = Field(min_length=1)
    timing_rationale: str = Field(min_length=1)
    risk_notes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class BgmRecommendationSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    recommendation_set_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    context_id: str = Field(min_length=1)
    method: str = Field(min_length=1)
    method_version: str = Field(min_length=1)
    recommendations: list[BgmRecommendationItem] = Field(min_length=1)
    selection_performed: bool = False
    automatic_selection_performed: bool = False
    network_performed: bool = False
    model_call_performed_by_cli: bool = False
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_ranks_and_candidates(self) -> "BgmRecommendationSet":
        ranks = [item.rank for item in self.recommendations]
        if len(ranks) != len(set(ranks)):
            raise ValueError("recommendation ranks must be unique")
        candidate_ids = [item.music_candidate_id for item in self.recommendations]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("music_candidate_id values must be unique")
        if self.selection_performed or self.automatic_selection_performed:
            raise ValueError("recommendation set must not perform candidate selection")
        if self.network_performed:
            raise ValueError("recommendation set must not report network access")
        if self.model_call_performed_by_cli:
            raise ValueError("CLI must not perform model calls")
        return self


class BgmRecommendationValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    severity: str = Field(pattern=r"^(error|warning)$")
    detail: str = Field(min_length=1)


class BgmRecommendationValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    recommendation_ref: str = Field(min_length=1)
    context_ref: str = Field(min_length=1)
    candidate_count: int = Field(ge=0)
    recommendation_count: int = Field(ge=0)
    issue_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    issues: list[BgmRecommendationValidationIssue] = Field(default_factory=list)
    valid: bool
