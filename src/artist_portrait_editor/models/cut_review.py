from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class CutReviewIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_id: str = Field(min_length=1)
    domain: str = Field(
        pattern=r"^(opening|dead_space|ending|rhythm|audio|structure|media_qc|delivery)$"
    )
    severity: str = Field(pattern=r"^(info|warning|error)$")
    timeline_start: float | None = Field(default=None, ge=0)
    timeline_end: float | None = Field(default=None, ge=0)
    diagnosis: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    second_pass_action_id: str | None = None


class SecondPassAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1)
    order: int = Field(ge=1)
    action_type: str = Field(
        pattern=(
            r"^(tighten_opening|trim_dead_space|strengthen_ending|"
            r"adjust_transition|rebalance_audio|rerender_preview|rerender_final|"
            r"manual_review)$"
        )
    )
    priority: str = Field(pattern=r"^(low|medium|high)$")
    timeline_start: float | None = Field(default=None, ge=0)
    timeline_end: float | None = Field(default=None, ge=0)
    recommendation: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    expected_effect: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    command_hint: str | None = None
    manual_only: bool = True
    edits_applied: bool = False


class CutReviewReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    cut_review_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    timeline_id: str = Field(min_length=1)
    timeline_ref: str = Field(min_length=1)
    timeline_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    sound_decision_id: str | None = None
    sound_decision_fingerprint: str | None = Field(
        default=None, pattern=r"^sha256:[0-9a-f]{64}$"
    )
    rhythm_plan_id: str | None = None
    rhythm_plan_fingerprint: str | None = Field(
        default=None, pattern=r"^sha256:[0-9a-f]{64}$"
    )
    rhythm_media_qc_id: str | None = None
    rhythm_media_qc_fingerprint: str | None = Field(
        default=None, pattern=r"^sha256:[0-9a-f]{64}$"
    )
    preview_validation_ref: str | None = None
    preview_validation_fingerprint: str | None = Field(
        default=None, pattern=r"^sha256:[0-9a-f]{64}$"
    )
    final_export_validation_ref: str | None = None
    final_export_validation_fingerprint: str | None = Field(
        default=None, pattern=r"^sha256:[0-9a-f]{64}$"
    )
    edit_guidance_id: str | None = None
    edit_guidance_fingerprint: str | None = Field(
        default=None, pattern=r"^sha256:[0-9a-f]{64}$"
    )
    reviewed_media_scope: str = Field(pattern=r"^(timeline_only|preview|final_export)$")
    status: str = Field(pattern=r"^(passed|warning|blocked)$")
    overall_assessment: str = Field(min_length=1)
    opening_status: str = Field(pattern=r"^(strong|review|weak|unknown)$")
    dead_space_status: str = Field(pattern=r"^(clear|review|crowded|unknown)$")
    ending_status: str = Field(pattern=r"^(strong|review|weak|unknown)$")
    rhythm_status: str = Field(pattern=r"^(aligned|review|conflict|unknown)$")
    audio_status: str = Field(pattern=r"^(clean|review|conflict|unknown)$")
    issue_count: int = Field(ge=0)
    high_priority_issue_count: int = Field(ge=0)
    second_pass_action_count: int = Field(ge=0)
    high_priority_action_count: int = Field(ge=0)
    first_second_pass_action: str | None = None
    issues: list[CutReviewIssue] = Field(default_factory=list)
    second_pass_actions: list[SecondPassAction] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    commands_executed: bool = False
    media_rendered: bool = False
    timeline_mutated: bool = False
    edit_points_moved: bool = False
    automatic_music_selection: bool = False
    automatic_bgm_fit: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
    image_generation_or_editing_used: bool = False
