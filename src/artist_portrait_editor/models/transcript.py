from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from artist_portrait_editor.constants import SCHEMA_VERSION
from artist_portrait_editor.models.source import EvidenceRef


class TranscriptTextType(str, Enum):
    interview = "interview"
    role_dialogue = "role_dialogue"
    lyrics = "lyrics"
    stage_dialogue = "stage_dialogue"
    voice_over = "voice_over"
    program_caption = "program_caption"
    fan_caption = "fan_caption"


class TranscriptRiskFlag(str, Enum):
    low_confidence = "low_confidence"
    empty_text = "empty_text"
    unclassified_text_type = "unclassified_text_type"


class WordTimestamp(BaseModel):
    model_config = ConfigDict(extra="forbid")

    word: str = Field(min_length=1)
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_boundary(self) -> "WordTimestamp":
        if self.end_seconds <= self.start_seconds:
            raise ValueError("end_seconds must be greater than start_seconds")
        return self


class TranscriptRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    transcript_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_location: str = Field(min_length=1)
    source_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    segment_index: int = Field(ge=0)
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    text: str
    language: str | None = None
    speaker: str | None = None
    text_type: TranscriptTextType | None = None
    word_timestamps: list[WordTimestamp] = Field(default_factory=list)
    method: str = Field(min_length=1)
    method_version: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    user_confirmed: bool = False
    risk_flags: list[TranscriptRiskFlag] = Field(default_factory=list)
    notes: str | None = None

    @model_validator(mode="after")
    def validate_boundary(self) -> "TranscriptRecord":
        if self.end_seconds <= self.start_seconds:
            raise ValueError("end_seconds must be greater than start_seconds")
        return self
