from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION
from artist_portrait_editor.models.timeline import TimelineSegment


class RevisionAppliedAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1)
    action_type: str = Field(min_length=1)
    status: str = Field(pattern=r"^(applied|preserved|manual_only|skipped|conflict)$")
    segment_id: str | None = None
    reason_code: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    baseline_timeline_start: float | None = Field(default=None, ge=0)
    baseline_timeline_end: float | None = Field(default=None, ge=0)
    revised_timeline_start: float | None = Field(default=None, ge=0)
    revised_timeline_end: float | None = Field(default=None, ge=0)
    duration_delta_seconds: float = 0.0
    evidence_refs: list[str] = Field(default_factory=list)


class RevisionSegmentChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_segment_id: str = Field(min_length=1)
    revised_segment_id: str | None = None
    status: str = Field(pattern=r"^(kept|trimmed|removed|moved|unchanged)$")
    action_ids: list[str] = Field(default_factory=list)
    baseline_timeline_start: float = Field(ge=0)
    baseline_timeline_end: float = Field(gt=0)
    revised_timeline_start: float | None = Field(default=None, ge=0)
    revised_timeline_end: float | None = Field(default=None, ge=0)
    duration_delta_seconds: float = 0.0
    detail: str = Field(min_length=1)


class DownstreamRevisionFreshness(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_ref: str
    present: bool
    status_if_candidate_promoted: str = Field(pattern=r"^(unchanged|stale|requires_rerun|missing)$")
    reason: str = Field(min_length=1)
    next_command: str | None = None


class RevisionApplication(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    revision_application_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    status: str = Field(pattern=r"^(ready|warning|blocked)$")
    revision_plan_id: str = Field(min_length=1)
    revision_plan_ref: str = Field(min_length=1)
    revision_plan_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    baseline_timeline_id: str = Field(min_length=1)
    baseline_timeline_ref: str = Field(min_length=1)
    baseline_timeline_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    selected_version_id: str = Field(min_length=1)
    selected_action_ids: list[str] = Field(default_factory=list)
    current_duration_seconds: float = Field(gt=0)
    revised_duration_seconds: float = Field(gt=0)
    duration_delta_seconds: float
    baseline_segment_count: int = Field(ge=0)
    revised_segment_count: int = Field(ge=0)
    applied_action_count: int = Field(ge=0)
    manual_action_count: int = Field(ge=0)
    skipped_action_count: int = Field(ge=0)
    conflict_count: int = Field(ge=0)
    revised_segments: list[TimelineSegment] = Field(min_length=1)
    segment_changes: list[RevisionSegmentChange] = Field(default_factory=list)
    action_results: list[RevisionAppliedAction] = Field(default_factory=list)
    downstream_freshness: list[DownstreamRevisionFreshness] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_command: str | None = None
    commands_executed: bool = False
    media_rendered: bool = False
    canonical_timeline_mutated: bool = False
    canonical_edit_points_moved: bool = False
    revised_candidate_edit_points_changed: bool = False
    automatic_music_selection: bool = False
    automatic_bgm_fit: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
    image_generation_or_editing_used: bool = False
