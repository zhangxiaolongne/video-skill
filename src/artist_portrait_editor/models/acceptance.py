from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class AcceptanceIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    severity: str = Field(pattern=r"^(error|warning)$")
    detail: str = Field(min_length=1)
    next_action: str = Field(min_length=1)


class AcceptanceStage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage_id: str = Field(min_length=1)
    status: str = Field(pattern=r"^(passed|warning|failed|not_applicable)$")
    required_for_core: bool
    required_for_delivery: bool
    artifact_refs: list[str] = Field(default_factory=list)
    evidence_summary: dict = Field(default_factory=dict)
    issues: list[AcceptanceIssue] = Field(default_factory=list)


class ProjectAcceptanceReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    acceptance_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    acceptance_profile: str = Field(pattern=r"^(standard|core|preview|delivery)$")
    status: str = Field(pattern=r"^(passed|warning|failed)$")
    profile_passed: bool
    required_stage_ids: list[str] = Field(default_factory=list)
    core_ready: bool
    preview_ready: bool
    final_export_ready: bool
    acceptance_score: float = Field(ge=0, le=1)
    stage_count: int = Field(ge=0)
    passed_stage_count: int = Field(ge=0)
    warning_stage_count: int = Field(ge=0)
    failed_stage_count: int = Field(ge=0)
    issue_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    stages: list[AcceptanceStage] = Field(default_factory=list)
    network_performed: bool = False
    model_call_performed_by_cli: bool = False
    media_rendered: bool = False
    automatic_music_selection: bool = False
