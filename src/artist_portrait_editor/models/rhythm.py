from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class RhythmIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_id: str = Field(min_length=1)
    mode: str = Field(pattern=r"^(speech_first|music_first|balanced)$")
    pacing: str = Field(pattern=r"^(calm|medium|fast)$")
    text_density: str = Field(pattern=r"^(none|low|medium|high)$")
    transition_style: str = Field(pattern=r"^(minimal|smooth|energetic)$")
    ending_style: str = Field(pattern=r"^(clean_stop|fade_out|open_loop)$")
    notes: str | None = None
    model_call_performed_by_cli: bool = False
    network_performed: bool = False


class RhythmProfileMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    value: float | str | bool | None = None
    status: str = Field(pattern=r"^(available|unavailable|warning)$")
    detail: str = Field(min_length=1)


class RhythmIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_id: str = Field(min_length=1)
    domain: str = Field(
        pattern=(
            r"^(timeline|bgm|compatibility|intent|cut_cue|transition|text|"
            r"ducking_silence|ending|agent_candidate)$"
        )
    )
    severity: str = Field(pattern=r"^(info|warning|error)$")
    detail: str = Field(min_length=1)
    next_action: str = Field(min_length=1)


class RhythmAuditDomain(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain_id: str = Field(min_length=1)
    status: str = Field(pattern=r"^(passed|warning|blocked|unavailable)$")
    summary: str = Field(min_length=1)
    metrics: list[RhythmProfileMetric] = Field(default_factory=list)
    issues: list[RhythmIssue] = Field(default_factory=list)


class RhythmAgentCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    timeline_id: str = Field(min_length=1)
    rhythm_plan_id: str = Field(min_length=1)
    recommendations: list[str] = Field(min_length=1)
    rejected_automatic_actions: list[str] = Field(default_factory=list)
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
    edit_points_moved: bool = False
    music_selected: bool = False
    media_rendered: bool = False


class RhythmPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    rhythm_plan_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    timeline_id: str = Field(min_length=1)
    timeline_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    bgm_fit_id: str | None = None
    bgm_fit_fingerprint: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    bgm_analysis_fingerprint: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    bgm_rhythm_intelligence_fingerprint: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    intent: RhythmIntent
    timeline_profile: RhythmAuditDomain
    bgm_profile: RhythmAuditDomain
    compatibility_audit: RhythmAuditDomain
    intent_audit: RhythmAuditDomain
    cut_cue_audit: RhythmAuditDomain
    transition_audit: RhythmAuditDomain
    text_audit: RhythmAuditDomain
    ducking_silence_audit: RhythmAuditDomain
    ending_audit: RhythmAuditDomain
    agent_candidate_audit: RhythmAuditDomain | None = None
    issue_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    status: str = Field(pattern=r"^(passed|warning|blocked)$")
    automatic_music_selection: bool = False
    edit_points_moved: bool = False
    media_rendered: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False


class RhythmMediaQcReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    rhythm_qc_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    rhythm_plan_id: str = Field(min_length=1)
    rhythm_plan_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    timeline_id: str = Field(min_length=1)
    preview_binding: RhythmAuditDomain
    final_export_binding: RhythmAuditDomain
    timeline_freshness: RhythmAuditDomain
    bgm_freshness: RhythmAuditDomain
    preview_duration_qc: RhythmAuditDomain
    final_duration_qc: RhythmAuditDomain
    audio_expectation_qc: RhythmAuditDomain
    ducking_render_qc: RhythmAuditDomain
    ending_render_qc: RhythmAuditDomain
    media_qc_summary: RhythmAuditDomain
    issue_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    status: str = Field(pattern=r"^(passed|warning|blocked)$")
    preview_rendered_by_qc: bool = False
    final_export_rendered_by_qc: bool = False
    edit_points_moved: bool = False
    automatic_music_selection: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False


class RhythmRepairAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1)
    order: int = Field(ge=1)
    category: str = Field(
        pattern=r"^(rhythm_plan|preview|final_export|bgm|rhythm_qc|review)$"
    )
    reason_code: str = Field(min_length=1)
    severity: str = Field(pattern=r"^(required|optional)$")
    command: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    expected_artifacts: list[str] = Field(default_factory=list)
    executes_automatically: bool = False


class RhythmRepairPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    rhythm_repair_plan_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    acceptance_profile: str = Field(pattern=r"^(standard|core|preview|delivery)$")
    rhythm_plan_id: str | None = None
    rhythm_qc_id: str | None = None
    acceptance_id: str | None = None
    action_count: int = Field(ge=0)
    required_action_count: int = Field(ge=0)
    optional_action_count: int = Field(ge=0)
    first_required_command: str | None = None
    status: str = Field(pattern=r"^(passed|warning|blocked)$")
    actions: list[RhythmRepairAction] = Field(default_factory=list)
    commands_executed: bool = False
    media_rendered: bool = False
    edit_points_moved: bool = False
    automatic_music_selection: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
