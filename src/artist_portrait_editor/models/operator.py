from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class OperatorArtifactStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(min_length=1)
    ref: str = Field(min_length=1)
    status: str = Field(pattern=r"^(present|missing|stale_or_unknown)$")
    bound_to_current_context: bool | None = None
    summary: str = Field(min_length=1)


class OperatorStage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage_id: str = Field(min_length=1)
    order: int = Field(ge=1)
    phase: str = Field(min_length=1)
    status: str = Field(pattern=r"^(done|current|pending|blocked|warning)$")
    command: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    blocking_refs: list[str] = Field(default_factory=list)
    source: str = Field(pattern=r"^(workflow|acceptance|rhythm|bgm|state|operator)$")


class OperatorBgmInputGuidance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: str = Field(
        pattern=r"^(direct_audio|video_audio_extract|source_embedded_audio|no_file_yet)$"
    )
    status: str = Field(pattern=r"^(available|missing|warning)$")
    guidance: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)


class OperatorRunbook(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    operator_runbook_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    target: str = Field(pattern=r"^(core|preview|delivery)$")
    status: str = Field(pattern=r"^(ready|in_progress|blocked|warning)$")
    workflow_plan_id: str | None = None
    acceptance_id: str | None = None
    rhythm_plan_id: str | None = None
    rhythm_qc_id: str | None = None
    edit_guidance_id: str | None = None
    bgm_rhythm_intelligence_id: str | None = None
    next_command: str | None = None
    stage_count: int = Field(ge=0)
    done_stage_count: int = Field(ge=0)
    pending_stage_count: int = Field(ge=0)
    blocked_stage_count: int = Field(ge=0)
    warning_stage_count: int = Field(ge=0)
    artifact_count: int = Field(ge=0)
    present_artifact_count: int = Field(ge=0)
    stages: list[OperatorStage] = Field(default_factory=list)
    artifact_map: list[OperatorArtifactStatus] = Field(default_factory=list)
    bgm_input_guidance: list[OperatorBgmInputGuidance] = Field(default_factory=list)
    manual_guidance_refs: list[str] = Field(default_factory=list)
    forbidden_capabilities: list[str] = Field(default_factory=list)
    commands_executed: bool = False
    media_rendered: bool = False
    timeline_mutated: bool = False
    edit_points_moved: bool = False
    automatic_music_selection: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
