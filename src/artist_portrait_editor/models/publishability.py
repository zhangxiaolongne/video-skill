from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class PublishabilityIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_id: str
    domain: Literal[
        "media", "technical", "hook", "emotion", "information", "bgm_voice",
        "text", "ending", "transitions", "composition", "platform", "nle",
        "evidence",
    ]
    severity: Literal["info", "low", "medium", "high", "critical"]
    disposition: Literal[
        "blocks_use", "blocks_publish", "requires_refinement", "evidence_gap",
    ]
    detail: str
    evidence_refs: list[str] = Field(default_factory=list)
    next_action: str


class VersionPublishability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_id: str
    version_kind: str
    evidence_level: str
    tier: Literal[
        "previewable", "publishable", "manual_refinement_required", "unusable",
    ]
    media_present: bool
    technical_valid: bool | None = None
    aesthetic_review_present: bool
    ready_for_preview: bool
    ready_for_publish: bool
    issue_count: int = Field(ge=0)
    blocking_issue_count: int = Field(ge=0)
    refinement_issue_count: int = Field(ge=0)
    evidence_gap_count: int = Field(ge=0)
    issues: list[PublishabilityIssue] = Field(default_factory=list)
    satisfied_requirements: list[str] = Field(default_factory=list)
    next_commands: list[str] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class PublishabilityReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    report_id: str
    project_id: str
    status: Literal["ready", "warning", "blocked"]
    version_review_id: str
    version_review_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    version_count: int = Field(ge=2)
    tier_counts: dict[str, int]
    highest_available_tier: Literal[
        "previewable", "publishable", "manual_refinement_required", "unusable",
    ]
    highest_tier_version_ids: list[str] = Field(min_length=1)
    selected_version_id: None = None
    explicit_selection_required: bool = True
    versions: list[VersionPublishability] = Field(min_length=2)
    warnings: list[str] = Field(default_factory=list)
    canonical_timeline_mutated: bool = False
    media_rendered: bool = False
    automatic_version_selection: bool = False
    automatic_music_selection: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
