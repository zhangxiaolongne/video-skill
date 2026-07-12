from __future__ import annotations

import hashlib
import json
from pathlib import Path

from artist_portrait_editor.constants import DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.bgm import (
    BgmAnalysisReport,
    BgmCandidateLedger,
    BgmFitPlan,
    BgmInputMode,
    BgmRhythmIntelligenceReport,
)
from artist_portrait_editor.models.edit_brief import EditBrief
from artist_portrait_editor.models.sound import (
    SoundDecision,
    SoundInputModeDecision,
    SoundMixPolicy,
)
from artist_portrait_editor.models.state import (
    ActiveMode,
    OverallStatus,
    StepLedgerEntry,
    StepStatus,
)
from artist_portrait_editor.models.timeline import TimelineDraft
from artist_portrait_editor.run_records import environment_snapshot, new_run_id, write_json, utc_now
from artist_portrait_editor.workspace_errors import WorkspacePrerequisiteError
from artist_portrait_editor.workspace_state import (
    atomic_write_text,
    load_state,
    project_root,
    save_state,
    write_run_report,
)
from artist_portrait_editor.config_loader import load_project_config


class SoundDecisionError(RuntimeError):
    pass


def build_sound_decision_workspace(project_path: Path) -> tuple[Path, Path, SoundDecision, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("sound requires init to complete first")
    data_dir = root / WORKSPACE_DIR / DATA_DIR
    timeline_path = root / "output" / "timeline_draft.json"
    edit_brief_path = data_dir / "edit_brief.json"
    if state.steps.get("timeline", StepLedgerEntry()).status not in {
        StepStatus.completed,
        StepStatus.completed_with_warnings,
    }:
        raise WorkspacePrerequisiteError("sound requires timeline to complete first")
    if not timeline_path.exists() or not edit_brief_path.exists():
        raise WorkspacePrerequisiteError("sound requires timeline and edit brief artifacts")

    timeline = TimelineDraft.model_validate_json(timeline_path.read_text(encoding="utf-8"))
    brief = EditBrief.model_validate_json(edit_brief_path.read_text(encoding="utf-8"))
    ledger_path = data_dir / "bgm_candidates.json"
    fit_path = data_dir / "bgm_fit.json"
    analysis_path = data_dir / "bgm_analysis.json"
    rhythm_path = data_dir / "bgm_rhythm_intelligence.json"
    ledger = _read_optional(ledger_path, BgmCandidateLedger)
    fit = _read_optional(fit_path, BgmFitPlan)
    analysis = _read_optional(analysis_path, BgmAnalysisReport)
    rhythm = _read_optional(rhythm_path, BgmRhythmIntelligenceReport)

    decision = build_sound_decision(
        project_id=config.project.id,
        allow_music=config.content_policy.allow_music,
        timeline=timeline,
        brief=brief,
        timeline_ref=timeline_path.relative_to(root).as_posix(),
        timeline_fingerprint=_fingerprint(timeline_path),
        edit_brief_ref=edit_brief_path.relative_to(root).as_posix(),
        edit_brief_fingerprint=_fingerprint(edit_brief_path),
        ledger=ledger,
        ledger_ref=ledger_path.relative_to(root).as_posix() if ledger_path.exists() else None,
        ledger_fingerprint=_fingerprint(ledger_path) if ledger_path.exists() else None,
        fit=fit,
        fit_ref=fit_path.relative_to(root).as_posix() if fit_path.exists() else None,
        fit_fingerprint=_fingerprint(fit_path) if fit_path.exists() else None,
        analysis=analysis,
        analysis_ref=analysis_path.relative_to(root).as_posix() if analysis_path.exists() else None,
        analysis_fingerprint=_fingerprint(analysis_path) if analysis_path.exists() else None,
        rhythm=rhythm,
        rhythm_ref=rhythm_path.relative_to(root).as_posix() if rhythm_path.exists() else None,
        rhythm_fingerprint=_fingerprint(rhythm_path) if rhythm_path.exists() else None,
    )

    json_path = data_dir / "sound_decision.json"
    md_path = root / "output" / "sound_decision.md"
    atomic_write_text(
        json_path,
        json.dumps(decision.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    atomic_write_text(md_path, render_sound_decision(decision))
    warnings = decision.warnings
    run_id = new_run_id()
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    state.steps["sound"] = StepLedgerEntry(
        status=status,
        input_fingerprint=_fingerprint_many(
            [timeline_path, edit_brief_path, ledger_path, fit_path, analysis_path, rhythm_path]
        ),
        output_refs=[
            json_path.relative_to(root).as_posix(),
            md_path.relative_to(root).as_posix(),
        ],
        last_run_id=run_id,
        warnings=warnings,
    )
    for dependent in ("rhythm", "rhythm_qc", "preview", "review_preview", "final_export", "review_final_export"):
        existing = state.steps.get(dependent)
        if existing and existing.status in {StepStatus.completed, StepStatus.completed_with_warnings}:
            state.steps[dependent] = StepLedgerEntry(
                status=StepStatus.invalidated,
                input_fingerprint=existing.input_fingerprint,
                output_refs=existing.output_refs,
                last_run_id=existing.last_run_id,
                warnings=[*existing.warnings, "sound decision changed"],
            )
    state.active_mode = ActiveMode.creative
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready

    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(runs_dir / "command.json", {"command": "sound", "project": str(project_path)})
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "sound",
            "status": status.value,
            "selected_strategy": decision.selected_strategy,
            "input_modes": [item.mode for item in decision.input_modes],
            "automatic_music_selection": False,
            "automatic_bgm_fit": False,
            "media_rendered": False,
            "network_performed": False,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text("sound decision completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(root / config.paths.output_dir, state, warnings)
    return json_path, md_path, decision, warnings


def build_sound_decision(
    *,
    project_id: str,
    allow_music: bool,
    timeline: TimelineDraft,
    brief: EditBrief,
    timeline_ref: str,
    timeline_fingerprint: str,
    edit_brief_ref: str,
    edit_brief_fingerprint: str,
    ledger: BgmCandidateLedger | None,
    ledger_ref: str | None,
    ledger_fingerprint: str | None,
    fit: BgmFitPlan | None,
    fit_ref: str | None,
    fit_fingerprint: str | None,
    analysis: BgmAnalysisReport | None,
    analysis_ref: str | None,
    analysis_fingerprint: str | None,
    rhythm: BgmRhythmIntelligenceReport | None,
    rhythm_ref: str | None,
    rhythm_fingerprint: str | None,
) -> SoundDecision:
    candidates = ledger.candidates if ledger else []
    direct = [item for item in candidates if item.input_mode == BgmInputMode.direct_audio]
    video_extracted = [item for item in candidates if item.input_mode == BgmInputMode.video_audio_extract]
    embedded = [item for item in candidates if item.input_mode == BgmInputMode.source_embedded_audio]
    mixed = [item for item in candidates if item.mixed_audio]
    source_audio_segments = [item for item in timeline.segments if item.media_role.value in {"audio", "both"}]
    warnings: list[str] = []
    if mixed:
        warnings.append("video-derived or source-embedded mixed audio must not be treated as clean BGM")
    if allow_music and not candidates:
        warnings.append("no BGM candidate has been imported yet")
    if fit is None and candidates and allow_music:
        warnings.append("BGM candidates exist but no explicit fit plan is current")
    if rhythm is None and candidates:
        warnings.append("BGM rhythm intelligence is missing; beat fallback remains conservative")

    selected_strategy = _selected_strategy(allow_music=allow_music, fit=fit, candidates=bool(candidates), source_audio_segments=bool(source_audio_segments))
    input_modes = [
        _original_audio_mode(source_audio_segments),
        _candidate_mode("direct_bgm", direct, "Use project-local uploaded audio only after explicit import and fit."),
        _candidate_mode(
            "video_extracted_mixed_audio",
            video_extracted,
            "Treat uploaded-video extracted audio as mixed audio; require human review or separation before using it as clean BGM.",
            mixed_audio=True,
        ),
        _candidate_mode(
            "source_embedded_audio",
            embedded,
            "Reuse embedded source audio only with source provenance and rights preserved; mixed tracks require review or separation.",
            mixed_audio=any(item.mixed_audio for item in embedded),
        ),
        SoundInputModeDecision(
            mode="silence",
            status="available",
            policy="Use intentional silence when music is disabled, no candidate exists, or ending needs breathing room.",
            next_actions=["Keep silence explicit in timeline/rhythm review instead of implying missing BGM."],
        ),
        SoundInputModeDecision(
            mode="no_file_yet",
            status="missing" if allow_music and not candidates else "disabled",
            policy="Planning state for projects where the user has not uploaded BGM yet.",
            next_actions=["Run `artist-portrait bgm import --project <project.yaml> --file <audio-or-video> --rights-status <status>` when music is desired."],
        ),
    ]
    if fit:
        for item in input_modes:
            if _fit_mode_name(fit) == item.mode:
                item.status = "selected"
                item.evidence_refs.append(fit_ref or ".artist-portrait/data/bgm_fit.json")

    beat_status = "available" if fit and fit.beat_evidence_status == "bound" else "unavailable" if allow_music else "not_applicable"
    policy = SoundMixPolicy(
        original_audio_policy=(
            "Retain original/source audio for speech or performance-led timeline segments; never replace it silently with BGM."
            if source_audio_segments
            else "No source-audio segment is currently retained; silence remains explicit when no BGM is fitted."
        ),
        bgm_policy=(
            "Use the current explicit BGM fit plan; do not auto-select or auto-fit music."
            if fit
            else "No BGM is fitted by this decision; import and explicitly fit a candidate if music is desired."
            if allow_music
            else "Music is disabled by content policy; use original audio or intentional silence."
        ),
        silence_policy="Silence is a valid intentional strategy for openings, pauses, endings, and no-file-yet states.",
        ducking_policy=(
            f"Apply explicit ducking from current fit at {fit.controls.ducking_gain_db:.2f} dB where original audio is retained."
            if fit and fit.controls.ducking_enabled
            else "Ducking is not applied unless an explicit fit plan enables it."
        ),
        fade_policy=(
            f"Use fitted BGM fades: in {fit.fade_in_seconds:.3f}s, out {fit.fade_out_seconds:.3f}s."
            if fit
            else "Default fade policy is planned only; no audio rendering or fitting is performed by sound decision."
        ),
        beat_fallback_policy=(
            "Validated beat evidence is available; rhythm planning may reference it without moving edit points."
            if beat_status == "available"
            else "Beat grid/BPM unavailable; keep cuts unchanged and use phrase/manual review instead of fabricated beat sync."
        ),
        fit_policy="Only explicit `bgm fit` or `bgm select` may create/refresh a fit plan; sound decision is advisory and non-mutating.",
    )
    next_actions = _next_actions(allow_music=allow_music, candidates=bool(candidates), fit=fit, analysis=analysis, rhythm=rhythm)
    decision_key = json.dumps(
        {
            "project_id": project_id,
            "timeline": timeline_fingerprint,
            "brief": edit_brief_fingerprint,
            "ledger": ledger_fingerprint,
            "fit": fit_fingerprint,
            "analysis": analysis_fingerprint,
            "rhythm": rhythm_fingerprint,
            "strategy": selected_strategy,
        },
        sort_keys=True,
    )
    return SoundDecision(
        sound_decision_id="sound_" + hashlib.sha256(decision_key.encode()).hexdigest()[:20],
        project_id=project_id,
        status="warning" if warnings else "ready",
        timeline_ref=timeline_ref,
        timeline_fingerprint=timeline_fingerprint,
        edit_brief_ref=edit_brief_ref,
        edit_brief_fingerprint=edit_brief_fingerprint,
        bgm_candidate_ledger_ref=ledger_ref,
        bgm_candidate_ledger_fingerprint=ledger_fingerprint,
        bgm_fit_ref=fit_ref,
        bgm_fit_fingerprint=fit_fingerprint,
        bgm_analysis_ref=analysis_ref,
        bgm_analysis_fingerprint=analysis_fingerprint,
        bgm_rhythm_ref=rhythm_ref,
        bgm_rhythm_fingerprint=rhythm_fingerprint,
        selected_strategy=selected_strategy,
        input_modes=input_modes,
        mix_policy=policy,
        source_audio_segment_count=len(source_audio_segments),
        bgm_candidate_count=len(candidates),
        direct_audio_candidate_count=len(direct),
        video_extracted_mixed_audio_candidate_count=len(video_extracted),
        source_embedded_audio_candidate_count=len(embedded),
        fitted_bgm_candidate_id=fit.music_candidate_id if fit else None,
        beat_status=beat_status,
        mixed_audio_warning_count=len(mixed),
        warnings=warnings,
        next_actions=next_actions,
    )


def render_sound_decision(decision: SoundDecision) -> str:
    lines = [
        "# Sound Decision",
        "",
        f"- Status: `{decision.status}`",
        f"- Strategy: `{decision.selected_strategy}`",
        f"- Timeline: `{decision.timeline_ref}`",
        f"- Edit brief: `{decision.edit_brief_ref}`",
        f"- BGM candidates: `{decision.bgm_candidate_count}`",
        f"- Fitted BGM: `{decision.fitted_bgm_candidate_id or 'none'}`",
        f"- Beat status: `{decision.beat_status}`",
        "",
        "## Input Modes",
        "",
    ]
    for mode in decision.input_modes:
        lines.append(f"- `{mode.mode}` `{mode.status}`: {mode.policy}")
        for risk in mode.risks:
            lines.append(f"  - Risk: {risk}")
    lines.extend(
        [
            "",
            "## Mix Policy",
            "",
            f"- Original audio: {decision.mix_policy.original_audio_policy}",
            f"- BGM: {decision.mix_policy.bgm_policy}",
            f"- Silence: {decision.mix_policy.silence_policy}",
            f"- Ducking: {decision.mix_policy.ducking_policy}",
            f"- Fades: {decision.mix_policy.fade_policy}",
            f"- Beat fallback: {decision.mix_policy.beat_fallback_policy}",
            f"- Fit policy: {decision.mix_policy.fit_policy}",
            "",
            "## Warnings",
            "",
        ]
    )
    lines.extend([f"- {item}" for item in decision.warnings] or ["- None"])
    lines.extend(["", "## Next Actions", ""])
    lines.extend([f"- {item}" for item in decision.next_actions] or ["- None"])
    return "\n".join(lines) + "\n"


def _candidate_mode(
    mode: str,
    candidates: list,
    policy: str,
    *,
    mixed_audio: bool = False,
) -> SoundInputModeDecision:
    refs = [candidate.music_candidate_id for candidate in candidates]
    risks = ["mixed extracted video audio may contain speech, effects, and environment"] if mixed_audio and candidates else []
    return SoundInputModeDecision(
        mode=mode,
        status="warning" if risks else "available" if candidates else "missing",
        policy=policy,
        evidence_refs=refs,
        risks=risks,
        next_actions=["Analyze and explicitly fit a candidate before rendering."] if candidates else [],
    )


def _original_audio_mode(source_audio_segments: list) -> SoundInputModeDecision:
    return SoundInputModeDecision(
        mode="original_audio",
        status="available" if source_audio_segments else "missing",
        policy="Preserve original speech/performance audio whenever the timeline segment carries audio or both media roles.",
        evidence_refs=[segment.segment_id for segment in source_audio_segments],
        next_actions=["Review ducking against retained source audio before preview/export."] if source_audio_segments else [],
    )


def _selected_strategy(*, allow_music: bool, fit: BgmFitPlan | None, candidates: bool, source_audio_segments: bool) -> str:
    if not allow_music:
        return "no_added_music" if source_audio_segments else "silence_fallback"
    if fit and source_audio_segments:
        return "original_audio_with_bgm"
    if fit:
        return "bgm_ready_for_mix"
    if candidates:
        return "needs_user_bgm_input"
    return "original_audio_only" if source_audio_segments else "needs_user_bgm_input"


def _fit_mode_name(fit: BgmFitPlan) -> str:
    # The fit plan does not persist the candidate input mode; evidence refs still bind the fit.
    return "direct_bgm"


def _next_actions(*, allow_music: bool, candidates: bool, fit: BgmFitPlan | None, analysis: BgmAnalysisReport | None, rhythm: BgmRhythmIntelligenceReport | None) -> list[str]:
    if not allow_music:
        return ["Proceed with original audio or intentional silence; do not import BGM unless policy changes."]
    actions: list[str] = []
    if not candidates:
        actions.append("Import direct audio, video audio extract, or source embedded audio before fitting BGM.")
    if candidates and analysis is None:
        actions.append("Run `artist-portrait bgm analyze --project <project.yaml>` before relying on technical BGM evidence.")
    if candidates and rhythm is None:
        actions.append("Run `artist-portrait bgm rhythm --project <project.yaml>` to document beat-unavailable fallback or beat evidence.")
    if candidates and fit is None:
        actions.append("Run explicit `artist-portrait bgm fit --project <project.yaml> --candidate <id>` only after choosing a candidate.")
    if fit:
        actions.append("Run rhythm planning and preview after reviewing the sound decision.")
    return actions


def _read_optional(path: Path, model):
    if not path.exists():
        return None
    return model.model_validate_json(path.read_text(encoding="utf-8"))


def _fingerprint(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _fingerprint_many(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        if path.exists():
            digest.update(path.as_posix().encode())
            digest.update(path.read_bytes())
    return "sha256:" + digest.hexdigest()
