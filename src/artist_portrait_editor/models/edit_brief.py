from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class EditBriefEvidenceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_count: int = Field(ge=0)
    video_source_count: int = Field(ge=0)
    audio_source_count: int = Field(ge=0)
    total_video_duration_seconds: float = Field(ge=0)
    total_audio_duration_seconds: float = Field(ge=0)
    clip_count: int = Field(ge=0)
    video_clip_count: int = Field(ge=0)
    analysis_record_count: int = Field(ge=0)
    transcript_backed_analysis_count: int = Field(ge=0)
    keyframe_backed_analysis_count: int = Field(ge=0)
    stage_or_music_source_count: int = Field(ge=0)
    content_density: str = Field(pattern=r"^(unknown|low|medium|high)$")
    evidence_level: str = Field(pattern=r"^(sources_only|clips_available|analysis_available)$")


class DurationOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    option_id: str = Field(pattern=r"^(short_cut|standard_cut|extended_cut|user_specified)$")
    label: str = Field(min_length=1)
    duration_seconds: float = Field(gt=0)
    duration_ratio_to_video: float = Field(ge=0)
    primary_platform_fit: list[str] = Field(default_factory=list)
    editorial_purpose: str = Field(min_length=1)
    rationale: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class EditBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    edit_brief_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    artist_name: str = Field(min_length=1)
    status: str = Field(pattern=r"^(ready|warning|blocked)$")
    target_platform: str = Field(min_length=1)
    aspect_ratio: str = Field(min_length=1)
    theme: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    tone: list[str] = Field(default_factory=list)
    duration_source: str = Field(pattern=r"^(user_specified|system_recommended)$")
    requested_duration_seconds: float | None = Field(default=None, gt=0)
    selected_option_id: str = Field(min_length=1)
    selected_duration_seconds: float = Field(gt=0)
    duration_options: list[DurationOption] = Field(min_length=1)
    evidence_summary: EditBriefEvidenceSummary
    source_ledger_ref: str = Field(min_length=1)
    source_ledger_fingerprint: str = Field(min_length=1)
    clip_ledger_ref: str | None = None
    clip_ledger_fingerprint: str | None = None
    analysis_ledger_ref: str | None = None
    analysis_ledger_fingerprint: str | None = None
    edit_intent: list[str] = Field(default_factory=list)
    selection_strategy: list[str] = Field(default_factory=list)
    pacing_strategy: list[str] = Field(default_factory=list)
    sound_strategy: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)
    forbidden_capability_flags: dict[str, bool] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    commands_executed: bool = False
    media_rendered: bool = False
    timeline_mutated: bool = False
    edit_points_moved: bool = False
    automatic_music_selection: bool = False
    automatic_bgm_fit: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
    image_generation_or_editing_used: bool = False
