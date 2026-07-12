from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class PreviewRenderedSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    segment_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    timeline_start: float = Field(ge=0)
    timeline_end: float = Field(gt=0)
    source_in: float = Field(ge=0)
    source_out: float = Field(gt=0)
    media_role: str = Field(pattern=r"^(video|audio|both)$")
    video_rendered: bool
    original_audio_rendered: bool
    video_transition: str = Field(min_length=1)
    audio_transition: str = Field(min_length=1)
    video_transition_rendered: bool
    audio_transition_rendered: bool


class PreviewRenderManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    preview_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    timeline_id: str = Field(min_length=1)
    timeline_ref: str = Field(min_length=1)
    timeline_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    bgm_fit_ref: str | None = None
    bgm_fit_id: str | None = None
    bgm_fit_fingerprint: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    output_ref: str = Field(min_length=1)
    output_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    expected_duration: float = Field(gt=0)
    duration: float = Field(gt=0)
    duration_delta_seconds: float
    duration_tolerance_seconds: float = Field(ge=0)
    requested_width: int = Field(gt=0)
    requested_height: int = Field(gt=0)
    requested_aspect_ratio: str = Field(pattern=r"^[1-9][0-9]*:[1-9][0-9]*$")
    fit_mode: str = Field(pattern=r"^contain$")
    requested_fps: int = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fps: int = Field(gt=0)
    actual_frame_rate: float | None = Field(default=None, gt=0)
    video_codec: str = Field(min_length=1)
    video_present: bool
    audio_codec: str = Field(min_length=1)
    audio_present: bool
    audio_expected: bool
    render_profile: str = Field(pattern=r"^low_resolution_preview$")
    rendered_segments: list[PreviewRenderedSegment] = Field(min_length=1)
    original_audio_included: bool
    bgm_included: bool
    ducking_applied: bool
    final_export: bool = False
    network_performed: bool = False
    model_call_performed: bool = False
    warnings: list[str] = Field(default_factory=list)


class PreviewValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    severity: str = Field(pattern=r"^(error|warning)$")
    detail: str = Field(min_length=1)


class PreviewValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    preview_ref: str = Field(min_length=1)
    manifest_ref: str = Field(min_length=1)
    timeline_ref: str = Field(min_length=1)
    timeline_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    bgm_fit_ref: str | None = None
    bgm_fit_fingerprint: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    expected_duration: float = Field(gt=0)
    actual_duration: float = Field(ge=0)
    duration_delta_seconds: float
    duration_tolerance_seconds: float = Field(ge=0)
    requested_width: int = Field(gt=0)
    requested_height: int = Field(gt=0)
    requested_aspect_ratio: str = Field(pattern=r"^[1-9][0-9]*:[1-9][0-9]*$")
    requested_fps: int = Field(gt=0)
    actual_width: int | None = Field(default=None, gt=0)
    actual_height: int | None = Field(default=None, gt=0)
    actual_frame_rate: float | None = Field(default=None, gt=0)
    video_present: bool
    audio_present: bool
    audio_expected: bool
    quality_status: str = Field(pattern=r"^(passed|warning|failed)$")
    recovery_command: str = Field(min_length=1)
    issue_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    issues: list[PreviewValidationIssue] = Field(default_factory=list)
    valid: bool
