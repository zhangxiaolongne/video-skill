from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class RevisionIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_id: str = Field(min_length=1)
    request_text: str = Field(min_length=1)
    request_type: str = Field(
        pattern=(
            r"^(shorter|longer|stronger_hook|more_emotional|keep_segment|"
            r"remove_segment|change_ending|reduce_subtitles|reduce_bgm|custom)$"
        )
    )
    target_duration_seconds: float | None = Field(default=None, gt=0)
    keep_segment_ids: list[str] = Field(default_factory=list)
    remove_segment_ids: list[str] = Field(default_factory=list)
    source: str = Field(default="cli", pattern=r"^(cli|host_agent|imported)$")
    classification_reasons: list[str] = Field(default_factory=list)


class RevisionSemanticClause(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clause_id: str = Field(min_length=1)
    domain: str = Field(
        pattern=r"^(duration|structure|rhythm|emotion|style|text|source_audio|bgm|transition|ending|constraint|custom)$"
    )
    operation: str = Field(min_length=1)
    intensity: str = Field(pattern=r"^(subtle|moderate|strong|unspecified)$")
    scope: str = Field(pattern=r"^(opening|middle|ending|segment|whole_cut)$")
    priority: int = Field(ge=1)
    matched_text: list[str] = Field(default_factory=list)
    evidence_requirements: list[str] = Field(default_factory=list)
    coupled_domains: list[str] = Field(default_factory=list)
    acceptance_observations: list[str] = Field(default_factory=list)
    application_status: str = Field(default="planned", pattern=r"^(planned|applied|manual_only|blocked|unavailable)$")
    confidence: float = Field(ge=0, le=1)


class RevisionSemanticConflict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conflict_id: str = Field(min_length=1)
    clause_ids: list[str] = Field(min_length=2)
    description: str = Field(min_length=1)
    resolution: str = Field(min_length=1)
    status: str = Field(pattern=r"^(warning|blocked)$")


class RevisionAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1)
    order: int = Field(ge=1)
    action_type: str = Field(
        pattern=(
            r"^(trim|extend|keep|remove|frontload_hook|strengthen_emotion|"
            r"replace_ending|reduce_subtitles|rebalance_bgm|refine_style|"
            r"accelerate_pacing|protect_voice|adjust_transition|manual_review)$"
        )
    )
    segment_id: str | None = None
    timeline_start: float | None = Field(default=None, ge=0)
    timeline_end: float | None = Field(default=None, ge=0)
    recommendation: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    expected_effect: str = Field(min_length=1)
    affected_domains: list[str] = Field(default_factory=list)
    acceptance_observations: list[str] = Field(default_factory=list)
    application_status: str = Field(default="planned", pattern=r"^(planned|applied|manual_only|blocked|skipped)$")
    evidence_refs: list[str] = Field(default_factory=list)
    required_for_intent: bool = True
    manual_only: bool = True
    edits_applied: bool = False


class RevisionVersionCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    strategy: str = Field(min_length=1)
    estimated_duration_seconds: float = Field(gt=0)
    duration_delta_seconds: float
    action_ids: list[str] = Field(default_factory=list)
    expected_improvements: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    risk_level: str = Field(pattern=r"^(low|medium|high)$")
    satisfies_intent: bool
    current_version: bool = False
    edits_applied: bool = False


class RevisionComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_version_id: str = Field(min_length=1)
    recommended_version_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    improvement_axes: list[str] = Field(default_factory=list)
    risk_axes: list[str] = Field(default_factory=list)


class RevisionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    revision_plan_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    status: str = Field(pattern=r"^(ready|warning|blocked)$")
    timeline_id: str = Field(min_length=1)
    timeline_ref: str = Field(min_length=1)
    timeline_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    cut_review_id: str = Field(min_length=1)
    cut_review_ref: str = Field(min_length=1)
    cut_review_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sound_decision_id: str | None = None
    sound_decision_fingerprint: str | None = Field(
        default=None, pattern=r"^sha256:[0-9a-f]{64}$"
    )
    rhythm_plan_id: str | None = None
    rhythm_plan_fingerprint: str | None = Field(
        default=None, pattern=r"^sha256:[0-9a-f]{64}$"
    )
    preview_validation_ref: str | None = None
    preview_validation_fingerprint: str | None = Field(
        default=None, pattern=r"^sha256:[0-9a-f]{64}$"
    )
    final_export_validation_ref: str | None = None
    final_export_validation_fingerprint: str | None = Field(
        default=None, pattern=r"^sha256:[0-9a-f]{64}$"
    )
    intent: RevisionIntent
    semantic_clauses: list[RevisionSemanticClause] = Field(default_factory=list)
    semantic_conflicts: list[RevisionSemanticConflict] = Field(default_factory=list)
    covered_domains: list[str] = Field(default_factory=list)
    current_duration_seconds: float = Field(gt=0)
    target_duration_seconds: float | None = Field(default=None, gt=0)
    action_count: int = Field(ge=0)
    candidate_count: int = Field(ge=0)
    first_action_id: str | None = None
    recommended_version_id: str = Field(min_length=1)
    actions: list[RevisionAction] = Field(default_factory=list)
    version_candidates: list[RevisionVersionCandidate] = Field(min_length=1)
    comparison: RevisionComparison
    warnings: list[str] = Field(default_factory=list)
    commands_executed: bool = False
    media_rendered: bool = False
    timeline_mutated: bool = False
    edit_points_moved: bool = False
    automatic_music_selection: bool = False
    automatic_bgm_fit: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
    image_generation_or_editing_used: bool = False
