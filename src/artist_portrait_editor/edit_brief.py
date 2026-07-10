from __future__ import annotations

import hashlib
from pathlib import Path

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.media.scanner import read_sources_jsonl
from artist_portrait_editor.models.analysis import AnalysisRecord
from artist_portrait_editor.models.clip import ClipRecord
from artist_portrait_editor.models.edit_brief import (
    DurationOption,
    EditBrief,
    EditBriefEvidenceSummary,
)
from artist_portrait_editor.models.source import MediaKind, SourceRecord, SourceType
from artist_portrait_editor.models.state import ActiveMode, OverallStatus, StepLedgerEntry, StepStatus
from artist_portrait_editor.run_records import environment_snapshot, new_run_id, write_json, utc_now
from artist_portrait_editor.workspace_errors import WorkspacePrerequisiteError
from artist_portrait_editor.workspace_records import read_analysis_jsonl, read_clips_jsonl
from artist_portrait_editor.workspace_state import (
    atomic_write_text,
    fingerprint_file,
    fingerprint_inputs,
    load_state,
    project_root,
    save_state,
    write_run_report,
)


class EditBriefError(RuntimeError):
    pass


def build_edit_brief_workspace(
    project_path: Path,
    *,
    target_duration_seconds: float | None = None,
    platform: str | None = None,
) -> tuple[Path, Path, EditBrief]:
    if target_duration_seconds is not None and target_duration_seconds <= 0:
        raise EditBriefError("target duration must be greater than zero seconds")

    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("brief requires init to complete first")

    data_dir = root / WORKSPACE_DIR / DATA_DIR
    json_path = data_dir / "edit_brief.json"
    md_path = root / "output" / "edit_brief.md"
    sources_path = data_dir / "sources.jsonl"
    if not sources_path.exists():
        raise WorkspacePrerequisiteError("brief requires scan to complete first")

    sources = read_sources_jsonl(sources_path)
    clips_path = data_dir / "clips.jsonl"
    analysis_path = data_dir / "analysis.jsonl"
    clips = read_clips_jsonl(clips_path) if clips_path.exists() else []
    analyses = read_analysis_jsonl(analysis_path) if analysis_path.exists() else []
    evidence = _evidence_summary(sources, clips, analyses)
    target_platform = (platform or config.creative_brief.platform).strip()
    warnings = _brief_warnings(evidence, target_duration_seconds)
    options = _duration_options(
        sources=sources,
        evidence=evidence,
        platform=target_platform,
        config_duration=float(config.creative_brief.target_duration_seconds),
    )
    selected_option = _select_duration_option(
        options=options,
        requested_seconds=target_duration_seconds,
        total_video_duration=evidence.total_video_duration_seconds,
        platform=target_platform,
    )
    duration_source = "user_specified" if target_duration_seconds is not None else "system_recommended"
    if target_duration_seconds is not None:
        options = [
            *options,
            DurationOption(
                option_id="user_specified",
                label="User specified cut",
                duration_seconds=round(float(target_duration_seconds), 3),
                duration_ratio_to_video=_ratio(
                    float(target_duration_seconds),
                    evidence.total_video_duration_seconds,
                ),
                primary_platform_fit=[target_platform],
                editorial_purpose="Obey the explicit target duration before automatic recommendation.",
                rationale=[
                    "The user supplied a target duration, so the deterministic recommender does not override it.",
                ],
                risks=_requested_duration_risks(
                    float(target_duration_seconds),
                    evidence.total_video_duration_seconds,
                ),
            ),
        ]

    source_ref = sources_path.relative_to(root).as_posix()
    source_fp = fingerprint_file(sources_path)
    clip_ref = clips_path.relative_to(root).as_posix() if clips_path.exists() else None
    analysis_ref = analysis_path.relative_to(root).as_posix() if analysis_path.exists() else None
    clip_fp = fingerprint_file(clips_path) if clips_path.exists() else None
    analysis_fp = fingerprint_file(analysis_path) if analysis_path.exists() else None
    input_fingerprint = fingerprint_inputs(
        [
            ("project", project_path),
            ("sources", sources_path),
            ("clips", clips_path),
            ("analysis", analysis_path),
        ]
    )
    key = (
        f"{config.project.id}:{selected_option.option_id}:{selected_option.duration_seconds:.3f}:"
        f"{duration_source}:{source_fp}:{clip_fp}:{analysis_fp}:{target_platform}"
    )
    brief = EditBrief(
        edit_brief_id="edit_brief_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:20],
        project_id=config.project.id,
        title=config.project.title,
        artist_name=config.project.artist_name,
        status="warning" if warnings else "ready",
        target_platform=target_platform,
        aspect_ratio=config.creative_brief.aspect_ratio,
        theme=config.creative_brief.theme,
        audience=config.creative_brief.audience,
        tone=config.creative_brief.tone,
        duration_source=duration_source,
        requested_duration_seconds=round(float(target_duration_seconds), 3)
        if target_duration_seconds is not None
        else None,
        selected_option_id=selected_option.option_id,
        selected_duration_seconds=selected_option.duration_seconds,
        duration_options=options,
        evidence_summary=evidence,
        source_ledger_ref=source_ref,
        source_ledger_fingerprint=source_fp,
        clip_ledger_ref=clip_ref,
        clip_ledger_fingerprint=clip_fp,
        analysis_ledger_ref=analysis_ref,
        analysis_ledger_fingerprint=analysis_fp,
        edit_intent=_edit_intent(config.creative_brief.theme, target_platform, selected_option),
        selection_strategy=_selection_strategy(evidence),
        pacing_strategy=_pacing_strategy(evidence, selected_option),
        sound_strategy=_sound_strategy(sources),
        next_actions=[
            "Review output/edit_brief.md and decide whether to accept the selected duration.",
            "Run `artist-portrait propose --project <project.yaml>` after the brief is accepted.",
            "When BGM is needed, import explicit local audio or extract a selected stream/range from project-local video; never treat mixed video audio as clean BGM.",
        ],
        artifact_refs=[
            json_path.relative_to(root).as_posix(),
            md_path.relative_to(root).as_posix(),
        ],
        forbidden_capability_flags={
            "commands_executed": False,
            "media_rendered": False,
            "timeline_mutated": False,
            "edit_points_moved": False,
            "automatic_music_selection": False,
            "automatic_bgm_fit": False,
            "model_call_performed_by_cli": False,
            "network_performed": False,
            "image_generation_or_editing_used": False,
        },
        warnings=warnings,
        risk_notes=_risk_notes(evidence, sources, selected_option),
    )

    data_dir.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, brief.model_dump(mode="json"))
    atomic_write_text(md_path, render_edit_brief(brief) + "\n")

    run_id = new_run_id()
    invalidated = invalidate_downstream_steps_for_brief(
        state,
        brief_fingerprint=fingerprint_file(json_path),
    )
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    state.steps["brief"] = StepLedgerEntry(
        status=status,
        input_fingerprint=input_fingerprint,
        output_refs=[
            json_path.relative_to(root).as_posix(),
            md_path.relative_to(root).as_posix(),
        ],
        last_run_id=run_id,
        warnings=warnings,
    )
    state.active_mode = ActiveMode.creative
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready
    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        runs_dir / "command.json",
        {
            "command": "brief",
            "project": str(project_path),
            "target_duration_seconds": target_duration_seconds,
            "platform": platform,
        },
    )
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "brief",
            "status": status.value,
            "selected_duration_seconds": brief.selected_duration_seconds,
            "duration_source": brief.duration_source,
            "output_refs": state.steps["brief"].output_refs,
            "invalidated_steps": invalidated,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text("brief completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(root / config.paths.output_dir, state, warnings)
    return json_path, md_path, brief


def render_edit_brief(brief: EditBrief) -> str:
    warning_lines = "\n".join(f"- {item}" for item in brief.warnings) or "- None"
    risk_lines = "\n".join(f"- {item}" for item in brief.risk_notes) or "- None"
    options = []
    for option in brief.duration_options:
        options.extend(
            [
                f"### `{option.option_id}` {option.label}",
                "",
                f"- Duration: `{option.duration_seconds:.3f}` seconds",
                f"- Ratio to video evidence: `{option.duration_ratio_to_video:.3f}`",
                f"- Platform fit: {', '.join(f'`{item}`' for item in option.primary_platform_fit) or '`none`'}",
                f"- Purpose: {option.editorial_purpose}",
            ]
        )
        if option.rationale:
            options.append("- Rationale:")
            options.extend(f"  - {item}" for item in option.rationale)
        if option.risks:
            options.append("- Risks:")
            options.extend(f"  - {item}" for item in option.risks)
        options.append("")
    return "\n".join(
        [
            "# Edit Brief",
            "",
            "This V1-01 brief makes a deterministic duration decision from local evidence. It does not render media, mutate timelines, move edit points, select music, call models, use image generation, or access the network.",
            "",
            "## Decision",
            "",
            f"- Status: `{brief.status}`",
            f"- Duration source: `{brief.duration_source}`",
            f"- Selected option: `{brief.selected_option_id}`",
            f"- Selected duration: `{brief.selected_duration_seconds:.3f}` seconds",
            f"- Platform: `{brief.target_platform}`",
            f"- Aspect ratio: `{brief.aspect_ratio}`",
            f"- Theme: {brief.theme}",
            "",
            "## Evidence",
            "",
            f"- Sources: `{brief.evidence_summary.source_count}`",
            f"- Video sources: `{brief.evidence_summary.video_source_count}`",
            f"- Audio sources: `{brief.evidence_summary.audio_source_count}`",
            f"- Total video duration: `{brief.evidence_summary.total_video_duration_seconds:.3f}` seconds",
            f"- Clips: `{brief.evidence_summary.clip_count}`",
            f"- Analysis records: `{brief.evidence_summary.analysis_record_count}`",
            f"- Evidence level: `{brief.evidence_summary.evidence_level}`",
            f"- Content density: `{brief.evidence_summary.content_density}`",
            f"- Source ledger: `{brief.source_ledger_ref}`",
            f"- Clip ledger: `{brief.clip_ledger_ref or 'missing'}`",
            f"- Analysis ledger: `{brief.analysis_ledger_ref or 'missing'}`",
            "",
            "## Duration Options",
            "",
            *options,
            "## Edit Intent",
            "",
            *[f"- {item}" for item in brief.edit_intent],
            "",
            "## Selection Strategy",
            "",
            *[f"- {item}" for item in brief.selection_strategy],
            "",
            "## Pacing Strategy",
            "",
            *[f"- {item}" for item in brief.pacing_strategy],
            "",
            "## Sound Strategy",
            "",
            *[f"- {item}" for item in brief.sound_strategy],
            "",
            "## Warnings",
            "",
            warning_lines,
            "",
            "## Risk Notes",
            "",
            risk_lines,
            "",
            "## Next Actions",
            "",
            *[f"- {item}" for item in brief.next_actions],
        ]
    )


def invalidate_downstream_steps_for_brief(
    state,
    *,
    brief_fingerprint: str,
) -> list[str]:
    invalidated: list[str] = []
    for step_name in (
        "score",
        "propose",
        "timeline",
        "review_timeline",
        "bgm_recommend",
        "review_bgm_recommendation",
        "bgm_fit",
        "rhythm",
        "preview",
        "review_preview",
        "final_export",
        "review_final_export",
        "acceptance",
        "operator",
        "editor_package",
        "nle_plan",
        "fcpxml_draft",
    ):
        entry = state.steps.get(step_name)
        if entry is None:
            continue
        if entry.status not in {
            StepStatus.completed,
            StepStatus.completed_with_warnings,
            StepStatus.blocked,
        }:
            continue
        if entry.input_fingerprint == brief_fingerprint:
            continue
        state.steps[step_name] = StepLedgerEntry(
            status=StepStatus.invalidated,
            input_fingerprint=entry.input_fingerprint,
            output_refs=entry.output_refs,
            last_run_id=entry.last_run_id,
            warnings=[
                *entry.warnings,
                "edit brief changed; rerun this step before trusting its output",
            ],
        )
        invalidated.append(step_name)
    return invalidated


def _evidence_summary(
    sources: list[SourceRecord],
    clips: list[ClipRecord],
    analyses: list[AnalysisRecord],
) -> EditBriefEvidenceSummary:
    video_sources = [item for item in sources if item.media_kind == MediaKind.video]
    audio_sources = [item for item in sources if item.media_kind == MediaKind.audio]
    total_video = sum(item.media_probe.duration for item in video_sources)
    total_audio = sum(item.media_probe.duration for item in audio_sources)
    video_clips = [item for item in clips if item.media_kind == MediaKind.video]
    stage_sources = [
        item
        for item in sources
        if item.source_type.value
        in {
            SourceType.stage_performance.value,
            SourceType.live_performance.value,
            SourceType.music_video.value,
            SourceType.musical_scene.value,
        }
    ]
    if analyses:
        evidence_level = "analysis_available"
    elif clips:
        evidence_level = "clips_available"
    else:
        evidence_level = "sources_only"
    if not total_video:
        density = "unknown"
    elif len(video_clips) / max(total_video / 60.0, 1.0) >= 10:
        density = "high"
    elif len(video_clips) / max(total_video / 60.0, 1.0) >= 4:
        density = "medium"
    else:
        density = "low"
    return EditBriefEvidenceSummary(
        source_count=len(sources),
        video_source_count=len(video_sources),
        audio_source_count=len(audio_sources),
        total_video_duration_seconds=round(total_video, 3),
        total_audio_duration_seconds=round(total_audio, 3),
        clip_count=len(clips),
        video_clip_count=len(video_clips),
        analysis_record_count=len(analyses),
        transcript_backed_analysis_count=sum(1 for item in analyses if item.transcript_refs),
        keyframe_backed_analysis_count=sum(1 for item in analyses if item.keyframe_refs),
        stage_or_music_source_count=len(stage_sources),
        content_density=density,
        evidence_level=evidence_level,
    )


def _duration_options(
    *,
    sources: list[SourceRecord],
    evidence: EditBriefEvidenceSummary,
    platform: str,
    config_duration: float,
) -> list[DurationOption]:
    total = evidence.total_video_duration_seconds or config_duration
    stage_or_music = evidence.stage_or_music_source_count > 0
    platform_norm = platform.lower()
    if total <= 45:
        short = max(8.0, min(total, round(total * 0.55, 3)))
        standard = max(short, min(total, round(total * 0.8, 3)))
        extended = max(standard, total)
    elif total <= 180:
        short = min(45.0, max(20.0, round(total * 0.28, 3)))
        standard = min(75.0, max(35.0, round(total * 0.42, 3)))
        extended = min(total, max(60.0, round(total * 0.65, 3)))
    else:
        short = min(60.0, max(30.0, round(total * 0.18, 3)))
        standard = min(95.0, max(45.0, round(total * 0.30, 3)))
        extended = min(180.0, max(90.0, round(total * 0.48, 3)))
    if stage_or_music:
        short = max(short, 30.0)
        standard = max(standard, 55.0)
    if "bilibili" in platform_norm or "youtube" in platform_norm:
        standard = max(standard, min(total, 75.0))
        extended = max(extended, min(total, 120.0))
    if "tiktok" in platform_norm or "douyin" in platform_norm or "reels" in platform_norm:
        short = min(short, 45.0)
        standard = min(standard, 75.0)
    if evidence.total_video_duration_seconds > 0:
        short = min(short, evidence.total_video_duration_seconds)
        standard = min(max(standard, short), evidence.total_video_duration_seconds)
        extended = min(max(extended, standard), evidence.total_video_duration_seconds)

    source_risks = _source_risk_summary(sources)
    return [
        DurationOption(
            option_id="short_cut",
            label="Short cut",
            duration_seconds=round(short, 3),
            duration_ratio_to_video=_ratio(short, evidence.total_video_duration_seconds),
            primary_platform_fit=["douyin", "tiktok", "reels", "shorts"],
            editorial_purpose="Fast hook, strongest moments only, minimal context.",
            rationale=[
                "Use when distribution rewards completion rate over narrative depth.",
                f"Computed from {evidence.total_video_duration_seconds:.3f}s video evidence and `{evidence.content_density}` density.",
            ],
            risks=[
                "May flatten performance build-up or emotional transition.",
                *source_risks,
            ],
        ),
        DurationOption(
            option_id="standard_cut",
            label="Standard cut",
            duration_seconds=round(standard, 3),
            duration_ratio_to_video=_ratio(standard, evidence.total_video_duration_seconds),
            primary_platform_fit=["douyin", "reels", "shorts", "bilibili", "youtube"],
            editorial_purpose="Balanced portrait cut with enough setup, peak, and landing.",
            rationale=[
                "Default choice when the user has not supplied a target duration.",
                "Preserves room for one visible setup, one or more highlight blocks, and a deliberate ending.",
            ],
            risks=source_risks,
        ),
        DurationOption(
            option_id="extended_cut",
            label="Extended cut",
            duration_seconds=round(extended, 3),
            duration_ratio_to_video=_ratio(extended, evidence.total_video_duration_seconds),
            primary_platform_fit=["bilibili", "youtube", "internal_review"],
            editorial_purpose="Context-rich review cut with more source continuity.",
            rationale=[
                "Use when source performance or interview continuity matters more than short-form completion.",
                "Keeps more breathing room for rhythm, transitions, and text beats.",
            ],
            risks=[
                "Requires stronger pacing review; weak sections become more visible.",
                *source_risks,
            ],
        ),
    ]


def _select_duration_option(
    *,
    options: list[DurationOption],
    requested_seconds: float | None,
    total_video_duration: float,
    platform: str,
) -> DurationOption:
    if requested_seconds is not None:
        return DurationOption(
            option_id="user_specified",
            label="User specified cut",
            duration_seconds=round(float(requested_seconds), 3),
            duration_ratio_to_video=_ratio(float(requested_seconds), total_video_duration),
            primary_platform_fit=[platform],
            editorial_purpose="Explicit user target duration.",
            rationale=["User-specified duration overrides deterministic recommendation."],
            risks=_requested_duration_risks(float(requested_seconds), total_video_duration),
        )
    platform_norm = platform.lower()
    if "bilibili" in platform_norm or "youtube" in platform_norm:
        return next(option for option in options if option.option_id == "standard_cut")
    if "douyin" in platform_norm or "tiktok" in platform_norm or "reels" in platform_norm:
        return next(option for option in options if option.option_id == "standard_cut")
    return next(option for option in options if option.option_id == "standard_cut")


def _brief_warnings(
    evidence: EditBriefEvidenceSummary,
    requested_seconds: float | None,
) -> list[str]:
    warnings: list[str] = []
    if evidence.video_source_count == 0:
        warnings.append("no video source evidence is available; duration recommendation is configuration-led")
    if evidence.evidence_level == "sources_only":
        warnings.append("clip and analysis ledgers are missing; brief cannot reason about shot density")
    elif evidence.evidence_level == "clips_available":
        warnings.append("analysis ledger is missing; brief uses clip density without material analysis")
    if requested_seconds and evidence.total_video_duration_seconds and requested_seconds > evidence.total_video_duration_seconds:
        warnings.append("requested duration exceeds total scanned video duration")
    return warnings


def _risk_notes(
    evidence: EditBriefEvidenceSummary,
    sources: list[SourceRecord],
    selected: DurationOption,
) -> list[str]:
    notes = list(selected.risks)
    if evidence.transcript_backed_analysis_count == 0:
        notes.append("No transcript-backed analysis is available; text rhythm and quote selection remain manual.")
    if evidence.keyframe_backed_analysis_count == 0:
        notes.append("No keyframe-backed analysis is available; visual highlight judgment remains weak.")
    for item in _source_risk_summary(sources):
        if item not in notes:
            notes.append(item)
    return notes


def _edit_intent(theme: str, platform: str, selected: DurationOption) -> list[str]:
    return [
        f"Build a {selected.duration_seconds:.3f}s artist portrait around `{theme}`.",
        f"Fit the cut for `{platform}` without changing source evidence or selecting music automatically.",
        "Prioritize recognisable performance/personality beats over exhaustive chronology.",
    ]


def _selection_strategy(evidence: EditBriefEvidenceSummary) -> list[str]:
    strategy = [
        "Select clips that can carry the opening hook, identity signal, emotional peak, and final landing.",
        "Avoid using every available source merely because it exists.",
    ]
    if evidence.evidence_level != "analysis_available":
        strategy.append("Because material analysis is incomplete, require human or host-Agent review before final timeline selection.")
    return strategy


def _pacing_strategy(evidence: EditBriefEvidenceSummary, selected: DurationOption) -> list[str]:
    return [
        f"Treat {selected.duration_seconds:.3f}s as the pacing budget before proposal generation.",
        "Reserve ending time for a clean visual/audio landing instead of cutting abruptly at the last beat.",
        f"Use `{evidence.content_density}` density as a weak local signal, not a substitute for aesthetic review.",
    ]


def _sound_strategy(sources: list[SourceRecord]) -> list[str]:
    has_audio = any(item.media_probe.audio_present for item in sources)
    strategy = [
        "Keep BGM as an explicit later selection; this brief does not choose or fit music.",
        "Support direct audio uploads, video-audio extraction, embedded source audio, multiple candidates, and no-file-yet planning.",
        "Never treat extracted mixed video audio as clean BGM without explicit separation or analysis evidence.",
    ]
    if has_audio:
        strategy.append("Original source audio exists and should be reviewed separately from any selected BGM.")
    else:
        strategy.append("No source audio stream was detected in scanned media.")
    return strategy


def _source_risk_summary(sources: list[SourceRecord]) -> list[str]:
    risky = sorted(
        {
            flag.value
            for source in sources
            for flag in source.risk_flags
        }
    )
    if not risky:
        return []
    return ["Source risk flags are present: " + ", ".join(risky)]


def _requested_duration_risks(requested: float, total: float) -> list[str]:
    risks: list[str] = []
    if total and requested > total:
        risks.append("Requested duration is longer than available video evidence.")
    if total and requested / total < 0.12:
        risks.append("Requested duration is extremely compressed relative to source duration.")
    if requested < 8:
        risks.append("Requested duration is too short for a mature artist portrait unless it is only a teaser.")
    return risks


def _ratio(duration: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return round(duration / total, 6)
