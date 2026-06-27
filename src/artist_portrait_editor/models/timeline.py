from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from artist_portrait_editor.constants import SCHEMA_VERSION
from artist_portrait_editor.models.proposal import ProposalId
from artist_portrait_editor.models.source import EvidenceRef


class MediaRole(str, Enum):
    video = "video"
    audio = "audio"
    both = "both"


class VideoTransition(str, Enum):
    none = "none"
    hard_cut = "hard_cut"
    crossfade = "crossfade"
    fade_in = "fade_in"
    fade_out = "fade_out"
    match_cut = "match_cut"


class AudioTransition(str, Enum):
    none = "none"
    cut = "cut"
    crossfade = "crossfade"
    fade_in = "fade_in"
    fade_out = "fade_out"
    j_cut = "j_cut"
    l_cut = "l_cut"


class MusicSlotStatus(str, Enum):
    unresolved = "unresolved"
    disabled_by_policy = "disabled_by_policy"
    fitted = "fitted"


class TimelineSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    segment_id: str = Field(min_length=1)
    timeline_start: float = Field(ge=0)
    timeline_end: float = Field(gt=0)
    clip_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_in: float = Field(ge=0)
    source_out: float = Field(gt=0)
    track_id: str = Field(min_length=1)
    media_role: MediaRole
    video_transition: VideoTransition
    audio_transition: AudioTransition
    reason: str = Field(min_length=1)
    evidence: list[EvidenceRef] = Field(min_length=1)
    creative_intent: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_ranges(self) -> "TimelineSegment":
        if self.timeline_end <= self.timeline_start:
            raise ValueError("timeline_end must be greater than timeline_start")
        if self.source_out <= self.source_in:
            raise ValueError("source_out must be greater than source_in")
        timeline_duration = self.timeline_end - self.timeline_start
        source_duration = self.source_out - self.source_in
        if abs(timeline_duration - source_duration) > 0.001:
            raise ValueError("timeline and source durations must match")
        return self


class TimelineMusicPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: MusicSlotStatus
    input_mode: str = Field(pattern=r"^(none_yet|disabled_by_policy|direct_audio|video_audio_extract|source_embedded_audio)$")
    candidate_id: str | None = None
    proposal_sound_structure: list[str] = Field(default_factory=list)
    future_input_modes: list[str] = Field(min_length=5)
    selection_performed: bool = False
    beat_analysis_performed: bool = False
    fitting_performed: bool = False
    fit_ref: str | None = None


class TimelineDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    timeline_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    proposal_set_id: str = Field(min_length=1)
    proposal_id: ProposalId
    proposal_map_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    input_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    target_duration: float = Field(gt=0)
    actual_duration: float = Field(gt=0)
    segments: list[TimelineSegment] = Field(min_length=1)
    music_plan: TimelineMusicPlan
    evidence: list[EvidenceRef] = Field(min_length=1)
    risks: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_timeline(self) -> "TimelineDraft":
        ordered = sorted(
            self.segments,
            key=lambda item: (item.track_id, item.timeline_start, item.segment_id),
        )
        by_track: dict[str, list[TimelineSegment]] = {}
        for segment in ordered:
            by_track.setdefault(segment.track_id, []).append(segment)
        for segments in by_track.values():
            for previous, current in zip(segments, segments[1:]):
                if current.timeline_start < previous.timeline_end - 0.001:
                    raise ValueError("segments must not overlap on the same track")
        maximum_end = max(segment.timeline_end for segment in self.segments)
        if abs(maximum_end - self.actual_duration) > 0.001:
            raise ValueError("actual_duration must equal the maximum segment end")
        if self.actual_duration > self.target_duration + 0.001:
            raise ValueError("actual_duration must not exceed target_duration")
        return self


class TimelineValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    severity: str = Field(pattern=r"^(error|warning)$")
    detail: str = Field(min_length=1)
    segment_id: str | None = None


class TimelineValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    timeline_ref: str = Field(min_length=1)
    input_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    proposal_id: ProposalId
    segment_count: int = Field(ge=0)
    actual_duration: float = Field(ge=0)
    issues: list[TimelineValidationIssue] = Field(default_factory=list)
    issue_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    valid: bool
