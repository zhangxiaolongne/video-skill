from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION
from artist_portrait_editor.models.source import RightsStatus


class BgmInputMode(str, Enum):
    direct_audio = "direct_audio"
    video_audio_extract = "video_audio_extract"
    source_embedded_audio = "source_embedded_audio"


class ContentPresence(str, Enum):
    unknown = "unknown"
    present = "present"
    absent = "absent"


class BgmCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    music_candidate_id: str = Field(min_length=1)
    input_mode: BgmInputMode
    source_ref: str = Field(min_length=1)
    source_media_kind: str = Field(pattern=r"^(audio|video)$")
    extract_in: float = Field(ge=0)
    extract_out: float = Field(gt=0)
    audio_stream_index: int = Field(ge=0)
    content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    cache_ref: str = Field(min_length=1)
    duration: float = Field(gt=0)
    rights_status: RightsStatus
    contains_speech: ContentPresence = ContentPresence.unknown
    contains_vocals: ContentPresence = ContentPresence.unknown
    contains_environment: ContentPresence = ContentPresence.unknown
    contains_sound_effects: ContentPresence = ContentPresence.unknown
    user_intent: str = Field(min_length=1)
    analysis_status: str = Field(pattern=r"^(technical_only|failed)$")
    integrated_loudness_lufs: float | None = None
    bpm: float | None = None
    beat_analysis_status: str = Field(pattern=r"^(unavailable|completed)$")
    beat_analysis_reason: str | None = None
    beat_grid_ref: str | None = None
    beat_grid_fingerprint: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    analysis_ref: str | None = None
    analysis_fingerprint: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    mixed_audio: bool


class BgmCandidateLedger(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    project_id: str = Field(min_length=1)
    candidates: list[BgmCandidate] = Field(default_factory=list)


class BgmEnergyWindow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: float = Field(ge=0)
    end: float = Field(gt=0)
    rms_dbfs: float
    peak_dbfs: float
    energy_label: str = Field(pattern=r"^(quiet|low|medium|high)$")


class BgmBeatEngineCapability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    engine: str = Field(min_length=1)
    package_available: bool
    execution_supported: bool
    status: str = Field(pattern=r"^(available|unavailable|unsupported)$")
    reason: str | None = None


class BgmBeatEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=0)
    time: float = Field(ge=0)
    confidence: float = Field(ge=0, le=1)


class BgmBeatGrid(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    project_id: str = Field(min_length=1)
    music_candidate_id: str = Field(min_length=1)
    cache_ref: str = Field(min_length=1)
    cache_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    beat_engine: str = Field(min_length=1)
    bpm: float = Field(gt=0)
    tempo_confidence: float = Field(ge=0, le=1)
    beat_count: int = Field(ge=0)
    beat_times: list[BgmBeatEvent] = Field(default_factory=list)
    model_call_performed: bool = False
    network_performed: bool = False
    fabricated: bool = False


class BgmCandidateAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    music_candidate_id: str = Field(min_length=1)
    cache_ref: str = Field(min_length=1)
    cache_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    duration: float = Field(gt=0)
    analysis_engine: str = Field(min_length=1)
    beat_engine: str = Field(min_length=1)
    beat_analysis_status: str = Field(pattern=r"^(unavailable|completed)$")
    beat_analysis_reason: str | None = None
    bpm: float | None = Field(default=None, gt=0)
    beat_grid_ref: str | None = None
    beat_grid_fingerprint: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    tempo_confidence: float | None = Field(default=None, ge=0, le=1)
    beat_count: int = Field(default=0, ge=0)
    window_seconds: float = Field(gt=0)
    window_count: int = Field(ge=0)
    average_rms_dbfs: float
    max_peak_dbfs: float
    quiet_head_seconds: float = Field(ge=0)
    quiet_tail_seconds: float = Field(ge=0)
    high_energy_start: float | None = Field(default=None, ge=0)
    high_energy_end: float | None = Field(default=None, gt=0)
    recommended_loop_safe: bool
    warnings: list[str] = Field(default_factory=list)
    windows: list[BgmEnergyWindow] = Field(default_factory=list)


class BgmAnalysisReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    project_id: str = Field(min_length=1)
    source_ledger_ref: str = ".artist-portrait/data/bgm_candidates.json"
    source_ledger_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    analysis_engine: str = Field(min_length=1)
    beat_engine_capabilities: list[BgmBeatEngineCapability] = Field(default_factory=list)
    network_performed: bool = False
    model_call_performed: bool = False
    automatic_music_selection: bool = False
    candidates: list[BgmCandidateAnalysis] = Field(default_factory=list)


class BgmFitSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timeline_start: float = Field(ge=0)
    timeline_end: float = Field(gt=0)
    source_in: float = Field(ge=0)
    source_out: float = Field(gt=0)
    loop_index: int = Field(ge=0)


class BgmDuckingInterval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: float = Field(ge=0)
    end: float = Field(gt=0)
    gain_db: float = Field(le=0)
    reason: str = Field(min_length=1)


class BgmFitControls(BaseModel):
    model_config = ConfigDict(extra="forbid")

    control_policy: str = Field(pattern=r"^(default_v1|explicit_cli_v1)$")
    requested_fit_mode: str = Field(pattern=r"^(auto|single_pass|trim|loop)$")
    fade_in_seconds: float = Field(ge=0)
    fade_out_seconds: float = Field(ge=0)
    target_gain_db: float
    ducking_enabled: bool
    ducking_gain_db: float = Field(le=0)
    beat_alignment_requested: bool
    edit_points_moved: bool = False
    automatic_music_selection: bool = False


class BgmFitPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    fit_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    timeline_id: str = Field(min_length=1)
    timeline_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    music_candidate_id: str = Field(min_length=1)
    candidate_content_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    target_duration: float = Field(gt=0)
    fit_mode: str = Field(pattern=r"^(single_pass|trim|loop)$")
    segments: list[BgmFitSegment] = Field(min_length=1)
    fade_in_seconds: float = Field(ge=0)
    fade_out_seconds: float = Field(ge=0)
    ducking_intervals: list[BgmDuckingInterval] = Field(default_factory=list)
    target_gain_db: float
    controls: BgmFitControls
    beat_alignment_status: str = Field(pattern=r"^(unavailable|not_requested|completed)$")
    beat_grid_ref: str | None = None
    beat_grid_fingerprint: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    beat_evidence_status: str = Field(
        default="unavailable",
        pattern=r"^(unavailable|bound)$",
    )
    analysis_ref: str | None = None
    analysis_fingerprint: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    energy_alignment_status: str = Field(
        default="unavailable",
        pattern=r"^(unavailable|analysis_used)$",
    )
    warnings: list[str] = Field(default_factory=list)
