from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION
from artist_portrait_editor.models.preview import PreviewRenderedSegment


class FinalExportProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(pattern=r"^(review_720p|delivery_1080p)$")
    width: int = Field(gt=0)
    fps: int = Field(gt=0)
    video_crf: int = Field(ge=0, le=51)
    audio_bitrate: str = Field(pattern=r"^[0-9]+k$")
    intent: str = Field(min_length=1)


class FinalExportManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    export_id: str = Field(min_length=1)
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
    requested_profile: FinalExportProfile
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    actual_frame_rate: float | None = Field(default=None, gt=0)
    video_codec: str = Field(min_length=1)
    video_present: bool
    audio_codec: str = Field(min_length=1)
    audio_present: bool
    audio_expected: bool
    render_profile: str = Field(pattern=r"^(review_720p|delivery_1080p)$")
    rendered_segments: list[PreviewRenderedSegment] = Field(min_length=1)
    original_audio_included: bool
    bgm_included: bool
    ducking_applied: bool
    final_export: bool = True
    network_performed: bool = False
    model_call_performed: bool = False
    automatic_music_selection: bool = False
    warnings: list[str] = Field(default_factory=list)


class FinalExportValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    severity: str = Field(pattern=r"^(error|warning)$")
    detail: str = Field(min_length=1)


class FinalExportValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    export_ref: str = Field(min_length=1)
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
    requested_profile: str = Field(pattern=r"^(review_720p|delivery_1080p)$")
    requested_width: int = Field(gt=0)
    requested_fps: int = Field(gt=0)
    actual_width: int | None = Field(default=None, gt=0)
    actual_height: int | None = Field(default=None, gt=0)
    actual_frame_rate: float | None = Field(default=None, gt=0)
    video_codec: str | None = None
    audio_codec: str | None = None
    video_present: bool
    audio_present: bool
    audio_expected: bool
    quality_status: str = Field(pattern=r"^(passed|warning|failed)$")
    recovery_command: str = Field(min_length=1)
    issue_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    issues: list[FinalExportValidationIssue] = Field(default_factory=list)
    valid: bool
