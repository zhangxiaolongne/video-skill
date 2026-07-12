from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from artist_portrait_editor.constants import SCHEMA_VERSION


class NormalizedBox(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def stays_in_frame(self) -> "NormalizedBox":
        if self.x + self.width > 1.000001 or self.y + self.height > 1.000001:
            raise ValueError("normalized box must stay inside the frame")
        return self


class CompositionFrameReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sample_id: str = Field(pattern=r"^sample_[0-9]{2}$")
    timestamp_seconds: float = Field(ge=0)
    performer_prominence: float = Field(ge=0, le=1)
    branding_intrusion: float = Field(ge=0, le=1)
    dead_space: float = Field(ge=0, le=1)
    crop_safety: str = Field(pattern=r"^(safe|conditional|unsafe)$")
    usability: str = Field(pattern=r"^(usable|reframe_required|reject)$")
    performer_box: NormalizedBox | None = None
    protected_boxes: list[NormalizedBox] = Field(default_factory=list)
    observations: list[str] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class PixelCropBox(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=1)
    height: int = Field(gt=1)


class ReframeCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(pattern=r"^reframe_[a-z0-9_]+$")
    name: str = Field(min_length=1)
    status: str = Field(pattern=r"^(candidate|conditional|rejected)$")
    source_width: int = Field(gt=0)
    source_height: int = Field(gt=0)
    crop_box: PixelCropBox
    target_aspect_ratio: str = Field(pattern=r"^[1-9][0-9]*:[1-9][0-9]*$")
    applicable_sample_ids: list[str] = Field(min_length=1)
    protected_region_policy: str = Field(min_length=1)
    benefits: list[str] = Field(min_length=1)
    risks: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    reject_reason: str | None = None
    applied: bool = False
    media_rendered: bool = False

    @model_validator(mode="after")
    def validate_geometry_and_status(self) -> "ReframeCandidate":
        box = self.crop_box
        if box.x + box.width > self.source_width or box.y + box.height > self.source_height:
            raise ValueError("crop box must stay inside the source canvas")
        ratio_width, ratio_height = (int(item) for item in self.target_aspect_ratio.split(":"))
        target = ratio_width / ratio_height
        actual = box.width / box.height
        if abs(actual - target) / target > 0.01:
            raise ValueError("crop box must match target aspect ratio within 1 percent")
        if self.status == "rejected" and not self.reject_reason:
            raise ValueError("rejected crop candidate requires reject_reason")
        if self.status != "rejected" and self.reject_reason:
            raise ValueError("non-rejected crop candidate must not set reject_reason")
        return self


class CompositionReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    review_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    composition_evidence_id: str = Field(min_length=1)
    timeline_id: str = Field(min_length=1)
    timeline_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    final_export_ref: str = Field(min_length=1)
    final_export_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    contact_sheet_ref: str = Field(min_length=1)
    contact_sheet_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    method: str = Field(min_length=1)
    method_version: str = Field(min_length=1)
    aesthetic_status: str = Field(pattern=r"^(usable|needs_reframe|unpublishable)$")
    frame_reviews: list[CompositionFrameReview] = Field(min_length=1)
    reframe_candidates: list[ReframeCandidate] = Field(min_length=1)
    recommended_candidate_id: str | None = None
    conclusions: list[str] = Field(min_length=1)
    warnings: list[str] = Field(default_factory=list)
    reviewed_only_supplied_frames: bool = True
    crop_applied: bool = False
    timeline_mutated: bool = False
    media_rendered: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
    image_generation_or_editing_used: bool = False

    @model_validator(mode="after")
    def validate_unique_ids_and_recommendation(self) -> "CompositionReview":
        sample_ids = [item.sample_id for item in self.frame_reviews]
        if len(sample_ids) != len(set(sample_ids)):
            raise ValueError("frame review sample_ids must be unique")
        candidate_ids = [item.candidate_id for item in self.reframe_candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("reframe candidate ids must be unique")
        known_samples = set(sample_ids)
        for candidate in self.reframe_candidates:
            if not set(candidate.applicable_sample_ids).issubset(known_samples):
                raise ValueError("reframe candidate references an unknown sample_id")
        if self.recommended_candidate_id:
            candidate = next(
                (item for item in self.reframe_candidates if item.candidate_id == self.recommended_candidate_id),
                None,
            )
            if candidate is None or candidate.status == "rejected":
                raise ValueError("recommended candidate must exist and not be rejected")
        return self
