from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class FirstCutDomainReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: Literal[
        "opening", "middle_pacing", "emotion", "bgm_voice", "text",
        "ending", "transitions", "composition", "technical_delivery",
    ]
    status: Literal["usable", "review", "conflict", "unavailable"]
    severity: Literal["none", "low", "medium", "high", "critical"]
    diagnosis: str = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)
    required_change: str = Field(min_length=1)
    resolved_in_canonical_final: bool = False


class FirstCutSelfReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    review_id: str
    project_id: str
    final_ref: str
    final_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    final_validation_ref: str
    baseline_ref: str
    baseline_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    editorial_scores_ref: str
    editorial_scores_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    structure_ref: str
    structure_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    bgm_match_ref: str
    bgm_match_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    text_plan_ref: str
    text_plan_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    reframe_application_ref: str
    reframe_application_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    publishability: Literal["publishable", "conditional", "not_publishable"]
    maturity_score: float = Field(ge=0, le=1)
    technical_delivery_valid: bool
    second_cut_required: bool
    domains: list[FirstCutDomainReview] = Field(min_length=9, max_length=9)
    highest_priority_domain: str
    planned_but_unapplied: list[str] = Field(min_length=1)
    next_actions: list[str] = Field(min_length=1)
    warnings: list[str] = Field(default_factory=list)
    canonical_final_mutated: bool = False
    edits_applied: bool = False
    media_rendered: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
