from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from artist_portrait_editor.constants import SCHEMA_VERSION


class MediaKind(str, Enum):
    video = "video"
    audio = "audio"


class SourceType(str, Enum):
    interview = "interview"
    stage_performance = "stage_performance"
    live_performance = "live_performance"
    music_video = "music_video"
    film_scene = "film_scene"
    tv_scene = "tv_scene"
    theatre_scene = "theatre_scene"
    musical_scene = "musical_scene"
    variety_show = "variety_show"
    rehearsal = "rehearsal"
    behind_the_scenes = "behind_the_scenes"
    public_event = "public_event"
    fan_edit = "fan_edit"
    other = "other"


class RightsStatus(str, Enum):
    owned = "owned"
    licensed = "licensed"
    publicly_available = "publicly_available"
    permission_unknown = "permission_unknown"
    restricted = "restricted"


class SourceRiskFlag(str, Enum):
    unknown_provenance = "unknown_provenance"
    low_provenance_confidence = "low_provenance_confidence"
    rights_unknown = "rights_unknown"
    rights_restricted = "rights_restricted"
    decode_failed = "decode_failed"
    conflicting_metadata = "conflicting_metadata"
    forbidden_by_user = "forbidden_by_user"


class EvidenceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(min_length=1)
    ref: str = Field(min_length=1)


class Assertion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Any | None = None
    method: str = Field(min_length=1)
    level: int = Field(ge=0, le=4)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    user_confirmed: bool = False


class MediaProbe(BaseModel):
    model_config = ConfigDict(extra="forbid")

    duration: float = Field(gt=0)
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    frame_rate: float | None = Field(default=None, gt=0)
    video_codec: str | None = None
    audio_present: bool
    audio_codec: str | None = None


class SourceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    source_id: str = Field(min_length=1)
    locations: list[str] = Field(min_length=1)
    primary_location: str = Field(min_length=1)
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    supersedes_source_id: str | None = None
    media_kind: MediaKind
    media_probe: MediaProbe
    source_type: Assertion
    work: Assertion | None = None
    role: Assertion | None = None
    recorded_date: Assertion | None = None
    published_date: Assertion | None = None
    rights_status: Assertion
    provenance_confidence: float = Field(ge=0.0, le=1.0)
    provenance_method: str = Field(min_length=1)
    provenance_evidence: list[EvidenceRef] = Field(default_factory=list)
    candidate_values: list[dict[str, Any]] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    user_confirmed: bool = False
    confirmation_history: list[dict[str, Any]] = Field(default_factory=list)
    forbidden_by_user: bool = False
    risk_flags: list[SourceRiskFlag] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("primary_location")
    @classmethod
    def primary_location_must_be_in_locations(cls, value: str, info) -> str:
        locations = info.data.get("locations") or []
        if locations and value not in locations:
            raise ValueError("primary_location must be present in locations")
        return value
