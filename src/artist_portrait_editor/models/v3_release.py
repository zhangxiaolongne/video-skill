from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from artist_portrait_editor.constants import SCHEMA_VERSION


class V3ReleaseEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    ref: str = Field(min_length=1)
    fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    current: bool
    limitation: str


class V3ReleaseOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome_id: Literal[
        "workflow_chain",
        "real_media_binding",
        "multi_version_strategies",
        "human_revision_truth",
        "ab_review_truth",
        "publishability_truth",
        "nle_handoff_truth",
        "creative_memory_boundary",
        "audiovisual_coupling",
        "benchmark_package_boundary",
    ]
    status: Literal["passed", "warning", "failed"]
    summary: str = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)
    limitations: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class V3ReleaseAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    audit_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    release_version: str = Field(pattern=r"^0\.50\.0$")
    release_tag: str = "v0.50.0"
    status: Literal["release_ready_with_known_gaps", "blocked"]
    product_claim: Literal["mature_assistant_workflow"] = "mature_assistant_workflow"
    aesthetic_maturity: Literal["manual_refinement_still_required"] = (
        "manual_refinement_still_required"
    )
    outcome_count: int = Field(ge=10, le=10)
    passed_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    outcomes: list[V3ReleaseOutcome] = Field(min_length=10, max_length=10)
    evidence: list[V3ReleaseEvidence] = Field(min_length=10)
    known_gaps: list[str] = Field(min_length=1)
    release_statement: str = Field(min_length=1)
    mature_editor_claimed: bool = False
    human_playback_claimed: bool = False
    nle_roundtrip_claimed: bool = False
    selected_version_id: None = None
    canonical_timeline_mutated: bool = False
    media_rendered: bool = False
    memory_applied_to_edit: bool = False
    automatic_version_selection: bool = False
    automatic_music_selection: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False

    @model_validator(mode="after")
    def validate_outcomes(self) -> "V3ReleaseAudit":
        if self.outcome_count != len(self.outcomes):
            raise ValueError("outcome_count must match outcomes")
        if len({item.outcome_id for item in self.outcomes}) != 10:
            raise ValueError("V3 release requires ten distinct outcomes")
        counts = {
            "passed": sum(item.status == "passed" for item in self.outcomes),
            "warning": sum(item.status == "warning" for item in self.outcomes),
            "failed": sum(item.status == "failed" for item in self.outcomes),
        }
        if (self.passed_count, self.warning_count, self.failed_count) != (
            counts["passed"], counts["warning"], counts["failed"]
        ):
            raise ValueError("release outcome counts must match outcomes")
        if (self.status == "blocked") != bool(self.failed_count):
            raise ValueError("blocked status must match failed outcomes")
        return self
