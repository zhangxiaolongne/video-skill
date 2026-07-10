from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class EditorPackageTimelineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1)
    order: int = Field(ge=1)
    track_id: str = Field(min_length=1)
    timeline_start: float = Field(ge=0)
    timeline_end: float = Field(gt=0)
    source_id: str = Field(min_length=1)
    clip_id: str = Field(min_length=1)
    source_in: float = Field(ge=0)
    source_out: float = Field(gt=0)
    media_role: str = Field(pattern=r"^(video|audio|both)$")
    video_transition: str = Field(min_length=1)
    audio_transition: str = Field(min_length=1)
    creative_intent: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)


class EditorPackageAudioItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1)
    order: int = Field(ge=1)
    category: str = Field(pattern=r"^(bgm_segment|ducking|fade|gain|beat_alignment)$")
    timeline_start: float | None = Field(default=None, ge=0)
    timeline_end: float | None = Field(default=None, gt=0)
    instruction: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)


class EditorPackageManualAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1)
    order: int = Field(ge=1)
    category: str = Field(min_length=1)
    priority: str = Field(pattern=r"^(low|medium|high)$")
    timeline_start: float | None = Field(default=None, ge=0)
    timeline_end: float | None = Field(default=None, ge=0)
    instruction: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    manual_only: bool = True
    edits_applied: bool = False


class EditorPackageArtifactBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(min_length=1)
    ref: str = Field(min_length=1)
    status: str = Field(pattern=r"^(present|missing|optional_missing)$")
    summary: str = Field(min_length=1)


class EditorPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    editor_package_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    timeline_id: str = Field(min_length=1)
    timeline_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    status: str = Field(pattern=r"^(ready|warning|blocked)$")
    target_duration: float = Field(gt=0)
    actual_duration: float = Field(gt=0)
    timeline_item_count: int = Field(ge=0)
    audio_item_count: int = Field(ge=0)
    manual_action_count: int = Field(ge=0)
    cue_sheet_row_count: int = Field(ge=0)
    timeline_items: list[EditorPackageTimelineItem] = Field(default_factory=list)
    audio_items: list[EditorPackageAudioItem] = Field(default_factory=list)
    manual_actions: list[EditorPackageManualAction] = Field(default_factory=list)
    artifact_bindings: list[EditorPackageArtifactBinding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    forbidden_capabilities: list[str] = Field(default_factory=list)
    commands_executed: bool = False
    media_rendered: bool = False
    timeline_mutated: bool = False
    edit_points_moved: bool = False
    automatic_music_selection: bool = False
    automatic_bgm_fit: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
    image_generation_or_editing_used: bool = False
