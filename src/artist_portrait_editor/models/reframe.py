from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from artist_portrait_editor.constants import SCHEMA_VERSION
from artist_portrait_editor.models.composition import PixelCropBox


class SegmentReframeChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    segment_id: str = Field(min_length=1)
    mode: Literal["candidate", "preserve"]
    candidate_id: str | None = Field(default=None, pattern=r"^reframe_[a-z0-9_]+$")
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_mode(self) -> "SegmentReframeChoice":
        if self.mode == "candidate" and not self.candidate_id:
            raise ValueError("candidate mode requires candidate_id")
        if self.mode == "preserve" and self.candidate_id is not None:
            raise ValueError("preserve mode must not set candidate_id")
        return self


class ReframeSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    selection_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    timeline_id: str = Field(min_length=1)
    timeline_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    final_export_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    composition_review_id: str = Field(min_length=1)
    composition_review_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    choices: list[SegmentReframeChoice] = Field(min_length=1)
    approved_by: str = Field(pattern=r"^(user|host_agent|human_editor)$")
    approval_note: str = Field(min_length=1)

    @model_validator(mode="after")
    def unique_segments(self) -> "ReframeSelection":
        ids = [item.segment_id for item in self.choices]
        if len(ids) != len(set(ids)):
            raise ValueError("reframe choices must have unique segment_id values")
        return self


class AppliedSegmentReframe(BaseModel):
    model_config = ConfigDict(extra="forbid")

    segment_id: str
    timeline_start: float = Field(ge=0)
    timeline_end: float = Field(gt=0)
    mode: Literal["candidate", "preserve"]
    candidate_id: str | None = None
    crop_box: PixelCropBox
    applicable_sample_ids: list[str] = Field(default_factory=list)
    protected_regions_preserved: bool
    performer_regions_preserved: bool
    visible_crop_applied: bool
    warnings: list[str] = Field(default_factory=list)


class CropChangeAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_segment_id: str
    to_segment_id: str
    candidate_changed: bool
    normalized_center_jump: float = Field(ge=0)
    risk: Literal["low", "medium", "high"]


class ReframeApplication(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    application_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    selection_id: str = Field(min_length=1)
    selection_ref: str = Field(min_length=1)
    selection_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    timeline_id: str = Field(min_length=1)
    timeline_ref: str = Field(min_length=1)
    timeline_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    final_export_ref: str = Field(min_length=1)
    final_export_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    composition_review_id: str = Field(min_length=1)
    composition_review_ref: str = Field(min_length=1)
    composition_review_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    contact_sheet_ref: str = Field(min_length=1)
    contact_sheet_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    output_ref: str = Field(min_length=1)
    output_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    duration: float = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    frame_rate: float | None = Field(default=None, gt=0)
    video_present: bool
    audio_present: bool
    audio_preserved_from_final: bool
    quality_status: Literal["passed", "warning", "failed"]
    segments: list[AppliedSegmentReframe] = Field(min_length=1)
    crop_changes: list[CropChangeAudit] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    explicit_selection_used: bool = True
    canonical_timeline_mutated: bool = False
    canonical_final_overwritten: bool = False
    media_rendered: bool = True
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
    automatic_candidate_selection: bool = False
