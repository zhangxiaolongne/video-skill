from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class RevisionPromotionSegmentBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_segment_id: str = Field(min_length=1)
    promoted_segment_id: str = Field(min_length=1)
    status: str = Field(pattern=r"^(kept|trimmed|removed|moved|unchanged)$")
    baseline_timeline_start: float = Field(ge=0)
    baseline_timeline_end: float = Field(gt=0)
    promoted_timeline_start: float | None = Field(default=None, ge=0)
    promoted_timeline_end: float | None = Field(default=None, ge=0)
    duration_delta_seconds: float = 0.0
    action_ids: list[str] = Field(default_factory=list)


class RevisionPromotionInvalidation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: str = Field(min_length=1)
    previous_status: str = Field(min_length=1)
    output_refs: list[str] = Field(default_factory=list)
    reason: str = Field(min_length=1)


class RevisionPromotion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    revision_promotion_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    status: str = Field(pattern=r"^(promoted|warning|blocked)$")
    revision_application_id: str = Field(min_length=1)
    revision_application_ref: str = Field(min_length=1)
    revision_application_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    selected_version_id: str = Field(min_length=1)
    baseline_timeline_id: str = Field(min_length=1)
    baseline_timeline_ref: str = Field(min_length=1)
    baseline_timeline_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    promoted_timeline_id: str = Field(min_length=1)
    promoted_timeline_ref: str = Field(min_length=1)
    promoted_timeline_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    current_duration_seconds: float = Field(gt=0)
    promoted_duration_seconds: float = Field(gt=0)
    duration_delta_seconds: float
    baseline_segment_count: int = Field(ge=0)
    promoted_segment_count: int = Field(ge=0)
    changed_segment_count: int = Field(ge=0)
    segment_bindings: list[RevisionPromotionSegmentBinding] = Field(default_factory=list)
    invalidated_steps: list[RevisionPromotionInvalidation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_commands: list[str] = Field(default_factory=list)
    commands_executed: bool = False
    media_rendered: bool = False
    canonical_timeline_mutated: bool = True
    canonical_edit_points_moved: bool = False
    automatic_music_selection: bool = False
    automatic_bgm_fit: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
    image_generation_or_editing_used: bool = False
