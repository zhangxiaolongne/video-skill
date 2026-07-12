from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from artist_portrait_editor.constants import SCHEMA_VERSION


class AestheticRangeAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    segment_id: str = Field(min_length=1)
    structural_role: str = Field(pattern=r"^(hook|build|payoff|bridge|context)$")
    timeline_start: float = Field(ge=0)
    timeline_end: float = Field(gt=0)
    source_id: str = Field(min_length=1)
    clip_id: str = Field(min_length=1)
    source_in: float = Field(ge=0)
    source_out: float = Field(gt=0)
    sample_ids: list[str] = Field(default_factory=list)
    category: str = Field(pattern=r"^(highlight|supporting|weak|reject)$")
    clip_overall_score: float | None = Field(default=None, ge=0, le=1)
    visual_evidence: list[str] = Field(min_length=1)
    audio_evidence: list[str] = Field(min_length=1)
    keep_or_drop: str = Field(pattern=r"^(keep|trim|replace|drop|review)$")
    rationale: list[str] = Field(min_length=1)
    uncertainty: list[str] = Field(default_factory=list)
    reframe_candidate_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_ranges(self) -> "AestheticRangeAssessment":
        if self.timeline_end <= self.timeline_start or self.source_out <= self.source_in:
            raise ValueError("aesthetic range end must be greater than start")
        return self


class AestheticEditConcept(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept_id: str = Field(pattern=r"^concept_[a-z0-9_]+$")
    name: str = Field(min_length=1)
    duration_option_id: str = Field(
        pattern=r"^(short_cut|standard_cut|extended_cut|user_specified)$"
    )
    target_duration_seconds: float = Field(gt=0)
    selected_segment_ids: list[str] = Field(min_length=1)
    requires_source_expansion: bool = False
    hook_strategy: list[str] = Field(min_length=1)
    build_strategy: list[str] = Field(min_length=1)
    payoff_strategy: list[str] = Field(min_length=1)
    composition_strategy: list[str] = Field(min_length=1)
    sound_bgm_strategy: list[str] = Field(min_length=1)
    text_strategy: list[str] = Field(min_length=1)
    rhythm_transition_strategy: list[str] = Field(min_length=1)
    materially_distinct_from: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(min_length=1)
    risks: list[str] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class AudiovisualDomainDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: str = Field(
        pattern=r"^(source_audio|bgm|speech_vocal|text|cuts|transitions|pauses|composition|ending)$"
    )
    status: str = Field(pattern=r"^(usable|review|conflict|unavailable)$")
    evidence: list[str] = Field(min_length=1)
    decision: list[str] = Field(min_length=1)
    dependencies: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class AudiovisualRhythmDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(min_length=1)
    overall_status: str = Field(pattern=r"^(usable|review|blocked)$")
    domains: list[AudiovisualDomainDecision] = Field(min_length=9, max_length=9)
    priority_sequence: list[str] = Field(min_length=1)
    concept_impacts: dict[str, list[str]] = Field(min_length=3)
    beat_sync_available: bool = False
    transcript_timing_available: bool = False
    clean_bgm_available: bool = False
    edits_applied: bool = False

    @model_validator(mode="after")
    def validate_domains(self) -> "AudiovisualRhythmDecision":
        expected = {
            "source_audio", "bgm", "speech_vocal", "text", "cuts",
            "transitions", "pauses", "composition", "ending",
        }
        domains = [item.domain for item in self.domains]
        if len(domains) != len(set(domains)) or set(domains) != expected:
            raise ValueError("audiovisual decision must cover all nine domains exactly once")
        return self


class FirstCutAestheticIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_id: str = Field(min_length=1)
    priority: int = Field(ge=1)
    severity: str = Field(pattern=r"^(critical|high|medium|low)$")
    domain: str = Field(
        pattern=r"^(opening|selection|composition|pacing|audio|text|transition|ending|publishability)$"
    )
    timeline_start: float | None = Field(default=None, ge=0)
    timeline_end: float | None = Field(default=None, ge=0)
    diagnosis: str = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)
    audience_impact: str = Field(min_length=1)
    required_change: str = Field(min_length=1)


class FirstCutAestheticReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_id: str = Field(min_length=1)
    technical_delivery_status: str = Field(pattern=r"^(valid|invalid|unknown)$")
    publishability: str = Field(pattern=r"^(publishable|conditional|not_publishable)$")
    maturity_score: float = Field(ge=0, le=1)
    strongest_elements: list[str] = Field(min_length=1)
    issues: list[FirstCutAestheticIssue] = Field(min_length=1)
    highest_impact_issue_id: str = Field(min_length=1)
    superseded_legacy_claims: list[str] = Field(default_factory=list)
    second_cut_required: bool = True
    edits_applied: bool = False

    @model_validator(mode="after")
    def validate_issue_order(self) -> "FirstCutAestheticReview":
        ids = [item.issue_id for item in self.issues]
        priorities = [item.priority for item in self.issues]
        if len(ids) != len(set(ids)) or priorities != list(range(1, len(priorities) + 1)):
            raise ValueError("first-cut issues must have unique ids and contiguous priority order")
        if self.highest_impact_issue_id != self.issues[0].issue_id:
            raise ValueError("highest impact issue must be priority one")
        return self


class AestheticBaseline(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    baseline_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    timeline_id: str = Field(min_length=1)
    timeline_ref: str = Field(min_length=1)
    timeline_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    edit_brief_ref: str = Field(min_length=1)
    edit_brief_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    clip_scores_ref: str = Field(min_length=1)
    clip_scores_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    composition_review_ref: str = Field(min_length=1)
    composition_review_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    composition_review_id: str = Field(min_length=1)
    sound_decision_ref: str = Field(min_length=1)
    sound_decision_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sound_decision_id: str = Field(min_length=1)
    rhythm_plan_ref: str = Field(min_length=1)
    rhythm_plan_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    rhythm_plan_id: str = Field(min_length=1)
    cut_review_ref: str = Field(min_length=1)
    cut_review_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    cut_review_id: str = Field(min_length=1)
    final_validation_ref: str = Field(min_length=1)
    final_validation_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    method: str = Field(min_length=1)
    method_version: str = Field(min_length=1)
    range_assessments: list[AestheticRangeAssessment] = Field(min_length=1)
    edit_concepts: list[AestheticEditConcept] = Field(min_length=3, max_length=3)
    audiovisual_rhythm_decision: AudiovisualRhythmDecision
    first_cut_review: FirstCutAestheticReview
    selected_concept_id: str | None = None
    conclusions: list[str] = Field(min_length=1)
    warnings: list[str] = Field(default_factory=list)
    reviewed_only_supplied_evidence: bool = True
    timeline_mutated: bool = False
    edit_points_moved: bool = False
    media_rendered: bool = False
    automatic_concept_selection: bool = False
    automatic_music_selection: bool = False
    automatic_bgm_fit: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
    image_generation_or_editing_used: bool = False

    @model_validator(mode="after")
    def validate_ids_and_selection(self) -> "AestheticBaseline":
        range_ids = [item.segment_id for item in self.range_assessments]
        if len(range_ids) != len(set(range_ids)):
            raise ValueError("range assessments must cover unique segment ids")
        concept_ids = [item.concept_id for item in self.edit_concepts]
        if len(concept_ids) != len(set(concept_ids)):
            raise ValueError("edit concept ids must be unique")
        known = set(range_ids)
        for concept in self.edit_concepts:
            if not set(concept.selected_segment_ids).issubset(known):
                raise ValueError("edit concept references an unknown segment id")
        if self.selected_concept_id is not None or self.automatic_concept_selection:
            raise ValueError("V2-01 baseline must not select an edit concept")
        concept_ids_set = set(concept_ids)
        if set(self.audiovisual_rhythm_decision.concept_impacts) != concept_ids_set:
            raise ValueError("audiovisual concept impacts must cover every edit concept")
        if self.audiovisual_rhythm_decision.edits_applied or self.first_cut_review.edits_applied:
            raise ValueError("baseline decisions and reviews must not claim applied edits")
        return self
