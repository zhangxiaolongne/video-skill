from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class SoundInputModeDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: str = Field(
        pattern=(
            r"^(original_audio|direct_bgm|video_extracted_mixed_audio|"
            r"source_embedded_audio|silence|no_file_yet)$"
        )
    )
    status: str = Field(pattern=r"^(selected|available|warning|missing|disabled)$")
    policy: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class SoundMixPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    original_audio_policy: str = Field(min_length=1)
    bgm_policy: str = Field(min_length=1)
    silence_policy: str = Field(min_length=1)
    ducking_policy: str = Field(min_length=1)
    fade_policy: str = Field(min_length=1)
    beat_fallback_policy: str = Field(min_length=1)
    fit_policy: str = Field(min_length=1)


class SoundDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    sound_decision_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    status: str = Field(pattern=r"^(ready|warning|blocked)$")
    timeline_ref: str = "output/timeline_draft.json"
    timeline_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    edit_brief_ref: str = ".artist-portrait/data/edit_brief.json"
    edit_brief_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    bgm_candidate_ledger_ref: str | None = None
    bgm_candidate_ledger_fingerprint: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    bgm_fit_ref: str | None = None
    bgm_fit_fingerprint: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    bgm_analysis_ref: str | None = None
    bgm_analysis_fingerprint: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    bgm_rhythm_ref: str | None = None
    bgm_rhythm_fingerprint: str | None = Field(
        default=None,
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    selected_strategy: str = Field(
        pattern=(
            r"^(original_audio_only|original_audio_with_bgm|bgm_ready_for_mix|"
            r"no_added_music|silence_fallback|needs_user_bgm_input)$"
        )
    )
    input_modes: list[SoundInputModeDecision] = Field(min_length=1)
    mix_policy: SoundMixPolicy
    source_audio_segment_count: int = Field(ge=0)
    bgm_candidate_count: int = Field(ge=0)
    direct_audio_candidate_count: int = Field(ge=0)
    video_extracted_mixed_audio_candidate_count: int = Field(ge=0)
    source_embedded_audio_candidate_count: int = Field(ge=0)
    fitted_bgm_candidate_id: str | None = None
    beat_status: str = Field(pattern=r"^(available|unavailable|not_applicable)$")
    mixed_audio_warning_count: int = Field(ge=0)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    commands_executed: bool = False
    media_rendered: bool = False
    timeline_mutated: bool = False
    edit_points_moved: bool = False
    automatic_music_selection: bool = False
    automatic_bgm_fit: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
    image_generation_or_editing_used: bool = False
