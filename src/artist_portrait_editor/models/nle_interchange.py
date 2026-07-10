from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class NleInterchangeTimelineMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mapping_id: str = Field(min_length=1)
    source_item_id: str = Field(min_length=1)
    target: str = Field(pattern=r"^(fcpxml|edl|resolve_csv)$")
    order: int = Field(ge=1)
    timeline_start: float = Field(ge=0)
    timeline_end: float = Field(gt=0)
    record_in: str = Field(min_length=1)
    record_out: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    clip_id: str = Field(min_length=1)
    source_in: float = Field(ge=0)
    source_out: float = Field(gt=0)
    track_id: str = Field(min_length=1)
    media_role: str = Field(min_length=1)
    transition_support: str = Field(pattern=r"^(native|note_only|unsupported)$")
    compatibility: str = Field(pattern=r"^(export_candidate|warning|blocked)$")
    instruction: str = Field(min_length=1)
    warnings: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class NleInterchangeAudioMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mapping_id: str = Field(min_length=1)
    source_item_id: str = Field(min_length=1)
    target: str = Field(pattern=r"^(fcpxml|edl|resolve_csv)$")
    order: int = Field(ge=1)
    category: str = Field(min_length=1)
    timeline_start: float | None = Field(default=None, ge=0)
    timeline_end: float | None = Field(default=None, gt=0)
    compatibility: str = Field(pattern=r"^(export_candidate|warning|blocked)$")
    instruction: str = Field(min_length=1)
    warnings: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class NleInterchangeMarkerMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mapping_id: str = Field(min_length=1)
    source_action_id: str = Field(min_length=1)
    target: str = Field(pattern=r"^(fcpxml|edl|resolve_csv)$")
    order: int = Field(ge=1)
    category: str = Field(min_length=1)
    priority: str = Field(min_length=1)
    timeline_start: float | None = Field(default=None, ge=0)
    timeline_end: float | None = Field(default=None, ge=0)
    compatibility: str = Field(pattern=r"^(export_candidate|warning|blocked)$")
    marker_name: str = Field(min_length=1)
    note: str = Field(min_length=1)
    warnings: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class NleInterchangeTargetSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: str = Field(pattern=r"^(fcpxml|edl|resolve_csv)$")
    status: str = Field(pattern=r"^(ready|warning|blocked)$")
    timeline_mapping_count: int = Field(ge=0)
    audio_mapping_count: int = Field(ge=0)
    marker_mapping_count: int = Field(ge=0)
    export_candidate_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    blocked_count: int = Field(ge=0)
    format_limitations: list[str] = Field(default_factory=list)


class NleInterchangePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    nle_plan_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    editor_package_id: str = Field(min_length=1)
    target: str = Field(pattern=r"^(fcpxml|edl|resolve_csv|all)$")
    status: str = Field(pattern=r"^(ready|warning|blocked)$")
    frame_rate: float = Field(gt=0)
    timeline_mapping_count: int = Field(ge=0)
    audio_mapping_count: int = Field(ge=0)
    marker_mapping_count: int = Field(ge=0)
    target_summaries: list[NleInterchangeTargetSummary] = Field(default_factory=list)
    timeline_mappings: list[NleInterchangeTimelineMapping] = Field(default_factory=list)
    audio_mappings: list[NleInterchangeAudioMapping] = Field(default_factory=list)
    marker_mappings: list[NleInterchangeMarkerMapping] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    forbidden_capabilities: list[str] = Field(default_factory=list)
    commands_executed: bool = False
    media_rendered: bool = False
    timeline_mutated: bool = False
    edit_points_moved: bool = False
    nle_project_written: bool = False
    automatic_music_selection: bool = False
    automatic_bgm_fit: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
    image_generation_or_editing_used: bool = False
