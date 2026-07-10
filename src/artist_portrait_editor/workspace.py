from __future__ import annotations

import hashlib
import json
from pathlib import Path
from artist_portrait_editor.capabilities import capability_warnings, detect_capabilities
from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import CACHE_DIR, DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.cleanup import project_storage_summary
from artist_portrait_editor.diagnostics import (
    artifact_issue,
    rebuild_command_for_step,
    render_risk_report,
    risk_issue,
    workspace_issue,
)
from artist_portrait_editor.bgm import bgm_analysis_summary
from artist_portrait_editor.bgm_recommendation import bgm_recommendation_doctor_issues, bgm_recommendation_selection_summary, bgm_recommendation_summary
from artist_portrait_editor.media.keyframes import (
    KeyframeExtractionError,
    extract_keyframe_image,
    ffmpeg_version,
)
from artist_portrait_editor.media.scene_detection import (
    SceneDetectionError,
    detect_scenes_pyscenedetect,
    pyscenedetect_version,
)
from artist_portrait_editor.media.transcription import (
    TranscribedSegment,
    TranscriptionError,
    faster_whisper_version,
    transcribe_source_faster_whisper,
)
from artist_portrait_editor.media.scanner import (
    ScanResult,
    read_sources_jsonl,
    scan_project_sources,
    write_sources_jsonl,
)
from artist_portrait_editor.models.config import FeatureSwitch
from artist_portrait_editor.models.analysis import AnalysisRecord, AnalysisRiskFlag
from artist_portrait_editor.models.bgm import BgmCandidateLedger, BgmFitPlan
from artist_portrait_editor.models.clip import (
    ClipBoundary,
    ClipMethod,
    ClipRecord,
    ClipRiskFlag,
)
from artist_portrait_editor.models.clip_score import ClipScoreRecord
from artist_portrait_editor.models.edit_brief import EditBrief
from artist_portrait_editor.models.keyframe import KeyframeRecord, KeyframeRiskFlag
from artist_portrait_editor.models.proposal import ProposalId, ProposalSet
from artist_portrait_editor.models.timeline import TimelineDraft, TimelineValidationReport
from artist_portrait_editor.models.proposal_context import (
    ProposalAnalysisContext,
    ProposalClipScoreContext,
    ProposalClipContext,
    ProposalContext,
    ProposalSourceContext,
)
from artist_portrait_editor.models.proposal_validation import (
    ProposalValidationIssue,
    ProposalValidationReport,
)
from artist_portrait_editor.models.state import (
    ActiveMode,
    Capabilities,
    OverallStatus,
    ProjectState,
    StepLedgerEntry,
    StepStatus,
    initial_steps,
)
from artist_portrait_editor.models.source import (
    Assertion,
    MediaKind,
    RightsStatus,
    SourceRecord,
)
from artist_portrait_editor.models.transcript import (
    TranscriptRecord,
    TranscriptRiskFlag,
    WordTimestamp,
)
from artist_portrait_editor.run_records import (
    environment_snapshot,
    new_run_id,
    utc_now,
    write_json,
)
from artist_portrait_editor.workspace_state import (
    atomic_write_text,
    fingerprint_file,
    fingerprint_inputs,
    init_workspace,
    invalidate_downstream_steps_for_sources,
    load_state,
    project_root,
    render_run_report,
    save_state,
    stable_analysis_id,
    stable_clip_id,
    stable_keyframe_id,
    stable_transcript_id,
    state_as_dict,
    state_path,
    write_run_report,
)
from artist_portrait_editor.workspace_diagnostics import (
    doctor_project_payload,
    invalidated_step_issues,
    ledger_output_ref_issues,
    project_status_payload,
    render_doctor_panel,
    render_status_panel,
)
from artist_portrait_editor.workspace_errors import (
    WorkspaceDependencyError,
    WorkspacePreviewError,
    WorkspacePrerequisiteError,
    WorkspaceProposalCandidateError,
    WorkspaceTimelineError,
)
from artist_portrait_editor.workspace_records import (
    read_analysis_jsonl,
    read_clips_jsonl,
    read_keyframes_jsonl,
    read_transcripts_jsonl,
    write_analysis_jsonl,
    write_clips_jsonl,
    write_keyframes_jsonl,
    write_transcripts_jsonl,
)
from artist_portrait_editor.workspace_proposal_io import (
    read_proposal_context_json,
    read_proposals_json,
)
from artist_portrait_editor.workspace_summaries import (
    analysis_summary,
    count_by_value,
    bgm_candidates_summary,
    bgm_fit_summary,
    keyframe_summary,
    proposal_status_summaries,
    timeline_summary,
    timeline_validation_summary,
    transcript_summary,
)
from artist_portrait_editor.proposal_artifacts import (
    proposal_artifact_paths,
    proposal_chain_issues,
    proposal_invalid_artifacts,
)
from artist_portrait_editor.proposal_review import (
    proposal_validation_issue,
    validate_proposal_set_against_context,
)
from artist_portrait_editor.proposal_handoff import (
    AgentProposalCandidateError,
    parse_quarantined_proposal_set,
    quarantine_agent_candidate,
    require_host_agent_method,
    write_agent_handoff_bundle,
)
from artist_portrait_editor.timeline import (
    TimelineBuildError,
    build_timeline_draft,
    render_timeline_review,
    validate_timeline_draft,
)
from artist_portrait_editor.preview import (
    preview_manifest_summary,
    preview_validation_summary,
    review_preview,
)
from artist_portrait_editor.final_export import (
    final_export_doctor_issues,
    final_export_manifest_summary,
    final_export_status_lines,
    final_export_validation_summary,
)


PROPOSAL_INVALID_ARTIFACTS = proposal_invalid_artifacts()


def stable_context_id(project_id: str, input_fingerprint: str) -> str:
    payload = f"{project_id}:{input_fingerprint}"
    return "ctx_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def stable_proposal_validation_report_id(
    project_id: str,
    input_fingerprint: str,
) -> str:
    payload = f"{project_id}:{input_fingerprint}"
    return "pvr_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def pending_visual_fields(analysis: AnalysisRecord) -> list[str]:
    pending = []
    if analysis.shot_size.value is None:
        pending.append("shot_size")
    if analysis.camera_motion.value is None:
        pending.append("camera_motion")
    if analysis.visual_quality.value is None:
        pending.append("visual_quality")
    if not analysis.emotion_candidates.value:
        pending.append("emotion_candidates")
    if not analysis.action_candidates.value:
        pending.append("action_candidates")
    return pending


def build_proposal_context(
    *,
    config,
    sources: list[SourceRecord],
    clips: list[ClipRecord],
    analyses: list[AnalysisRecord],
    clip_scores: list[ClipScoreRecord],
    sources_ref: str,
    clips_ref: str,
    analysis_ref: str,
    clip_scores_ref: str,
    clip_scores_fingerprint: str,
    material_map_ref: str,
    material_map_fingerprint: str,
    input_fingerprint: str,
) -> ProposalContext:
    sorted_sources = sorted(sources, key=lambda item: item.primary_location)
    sorted_clips = sorted(clips, key=lambda item: (item.source_location, item.clip_index))
    sorted_analyses = sorted(
        analyses,
        key=lambda item: (item.source_location, item.start_seconds, item.clip_id),
    )
    sorted_scores = sorted(
        clip_scores,
        key=lambda item: (-item.overall_score, item.source_location, item.start_seconds, item.clip_id),
    )
    return ProposalContext(
        context_id=stable_context_id(config.project.id, input_fingerprint),
        project_id=config.project.id,
        material_map_ref=material_map_ref,
        material_map_fingerprint=material_map_fingerprint,
        sources_ref=sources_ref,
        clips_ref=clips_ref,
        analysis_ref=analysis_ref,
        clip_scores_ref=clip_scores_ref,
        clip_scores_fingerprint=clip_scores_fingerprint,
        input_fingerprint=input_fingerprint,
        creative_brief=config.creative_brief,
        content_policy=config.content_policy,
        proposal_ids_required=[
            "proposal_safe",
            "proposal_advanced",
            "proposal_risky",
        ],
        sources=[
            ProposalSourceContext(
                source_id=source.source_id,
                primary_location=source.primary_location,
                media_kind=source.media_kind,
                source_type=str(source.source_type.value),
                rights_status=str(source.rights_status.value),
                duration_seconds=source.media_probe.duration,
                forbidden_by_user=source.forbidden_by_user,
                risk_flags=[flag.value for flag in source.risk_flags],
            )
            for source in sorted_sources
        ],
        clips=[
            ProposalClipContext(
                clip_id=clip.clip_id,
                source_id=clip.source_id,
                source_location=clip.source_location,
                media_kind=clip.media_kind,
                start_seconds=clip.boundary.start_seconds,
                end_seconds=clip.boundary.end_seconds,
                duration_seconds=clip.boundary.duration_seconds,
                method=clip.method.value,
                risk_flags=[flag.value for flag in clip.risk_flags],
            )
            for clip in sorted_clips
        ],
        analyses=[
            ProposalAnalysisContext(
                analysis_id=analysis.analysis_id,
                clip_id=analysis.clip_id,
                source_id=analysis.source_id,
                material_type=str(analysis.material_type.value),
                original_audio_usability=str(analysis.original_audio_usability.value),
                transcript_refs=analysis.transcript_refs,
                keyframe_refs=analysis.keyframe_refs,
                pending_visual_fields=pending_visual_fields(analysis),
                risk_flags=[flag.value for flag in analysis.risk_flags],
                review_score=analysis_review_score(analysis),
            )
            for analysis in sorted_analyses
        ],
        clip_scores=[
            ProposalClipScoreContext(
                clip_id=score.clip_id,
                overall_score=score.overall_score,
                selection_tier=score.selection_tier,
                keep_recommendation=score.keep_recommendation,
                evidence_level=score.evidence_level,
                reasons=score.reasons,
            )
            for score in sorted_scores
        ],
        evidence=[
            {"type": "source_ledger", "ref": sources_ref},
            {"type": "clip_ledger", "ref": clips_ref},
            {"type": "analysis_ledger", "ref": analysis_ref},
            {"type": "clip_score_ledger", "ref": clip_scores_ref},
            {"type": "material_map", "ref": material_map_ref},
        ],
        constraints=[
            "Generate exactly proposal_safe, proposal_advanced, and proposal_risky.",
            "Every factual claim must cite source, clip, analysis, or material_map evidence.",
            "Use clip_scores to prefer higher-value clips and explain any use of low-score clips.",
            "Do not use forbidden_by_user sources.",
            "Do not infer visual semantics from keyframes in the current gate.",
            "Do not fabricate missing material, identity, dates, rights, dialogue, or timecodes.",
        ],
        bgm_requirements=[
            "Proposals must describe BGM strategy without selecting or downloading tracks.",
            "BGM strategy must account for mood, BPM, section structure, pacing, transitions, original audio, speech ducking, and rights status.",
        ],
        blocked_capabilities=[
            "timeline_generation",
            "bgm_selection",
            "beat_analysis",
            "preview_rendering",
            "vision_analysis",
            "network_search",
            "image_generation_or_editing",
        ],
    )


def write_proposal_context_json(root: Path, context: ProposalContext) -> Path:
    output = root / WORKSPACE_DIR / DATA_DIR / "proposal_context.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(context.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def write_proposal_validation_json(root: Path, report: ProposalValidationReport) -> Path:
    output = root / WORKSPACE_DIR / DATA_DIR / "proposal_validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def build_proposal_validation_report(
    *,
    proposal_set: ProposalSet,
    context: ProposalContext,
    proposal_context_ref: str,
    proposals_ref: str,
    input_fingerprint: str,
) -> ProposalValidationReport:
    issues = validate_proposal_set_against_context(
        proposal_set=proposal_set,
        context=context,
    )
    error_count = sum(1 for issue in issues if issue.severity == "error")
    warning_count = sum(1 for issue in issues if issue.severity == "warning")
    return ProposalValidationReport(
        report_id=stable_proposal_validation_report_id(
            context.project_id,
            input_fingerprint,
        ),
        project_id=context.project_id,
        proposal_set_id=proposal_set.proposal_set_id,
        proposal_context_ref=proposal_context_ref,
        proposals_ref=proposals_ref,
        input_fingerprint=input_fingerprint,
        proposal_count=len(proposal_set.proposals),
        issue_count=len(issues),
        error_count=error_count,
        warning_count=warning_count,
        issues=issues,
    )


def build_transcript_records_for_source(
    *,
    record: SourceRecord,
    source_fingerprint: str,
    segments: list[TranscribedSegment],
    method_version: str,
) -> list[TranscriptRecord]:
    transcripts: list[TranscriptRecord] = []
    for segment_index, segment in enumerate(segments):
        risk_flags: list[TranscriptRiskFlag] = []
        text = segment.text.strip()
        if not text:
            risk_flags.append(TranscriptRiskFlag.empty_text)
        if segment.confidence < 0.5:
            risk_flags.append(TranscriptRiskFlag.low_confidence)
        risk_flags.append(TranscriptRiskFlag.unclassified_text_type)
        transcripts.append(
            TranscriptRecord(
                transcript_id=stable_transcript_id(
                    record.source_id,
                    segment_index,
                    segment.start_seconds,
                    segment.end_seconds,
                ),
                source_id=record.source_id,
                source_location=record.primary_location,
                source_content_hash=record.content_hash,
                source_fingerprint=source_fingerprint,
                segment_index=segment_index,
                start_seconds=segment.start_seconds,
                end_seconds=segment.end_seconds,
                text=text,
                language=segment.language,
                speaker=None,
                text_type=None,
                word_timestamps=[
                    WordTimestamp(
                        word=word.word,
                        start_seconds=word.start_seconds,
                        end_seconds=word.end_seconds,
                        confidence=word.confidence,
                    )
                    for word in segment.words
                ],
                method="faster_whisper",
                method_version=method_version,
                confidence=segment.confidence,
                evidence=[
                    {"type": "source", "ref": record.source_id},
                    {"type": "tool", "ref": method_version},
                ],
                user_confirmed=False,
                risk_flags=risk_flags,
                notes=(
                    "ASR text is an audible-content candidate only; it does not "
                    "classify interview, lyrics, role dialogue, or captions"
                ),
            )
        )
    return transcripts


def build_transcripts(
    *,
    root: Path,
    records: list[SourceRecord],
    source_fingerprint: str,
) -> list[TranscriptRecord]:
    transcripts: list[TranscriptRecord] = []
    method_version = f"faster-whisper-{faster_whisper_version()}"
    for record in sorted(records, key=lambda item: item.primary_location):
        segments = transcribe_source_faster_whisper(root / record.primary_location)
        transcripts.extend(
            build_transcript_records_for_source(
                record=record,
                source_fingerprint=source_fingerprint,
                segments=segments,
                method_version=method_version,
            )
        )
    return transcripts


def build_keyframes(
    *,
    root: Path,
    clips: list[ClipRecord],
    clips_fingerprint: str,
) -> tuple[list[KeyframeRecord], list[str]]:
    keyframes: list[KeyframeRecord] = []
    warnings: list[str] = []
    video_clips = [clip for clip in clips if clip.media_kind == MediaKind.video]
    if not video_clips:
        return [], ["no video clips available for keyframe extraction"]

    method_version = ffmpeg_version()
    cache_dir = root / WORKSPACE_DIR / CACHE_DIR / "keyframes"
    for frame_index, clip in enumerate(
        sorted(video_clips, key=lambda item: (item.source_location, item.clip_index))
    ):
        timestamp = round(
            clip.boundary.start_seconds + (clip.boundary.duration_seconds / 2.0),
            3,
        )
        keyframe_id = stable_keyframe_id(clip.clip_id, frame_index, timestamp)
        output_path = cache_dir / f"{keyframe_id}.jpg"
        extract_keyframe_image(
            source_path=root / clip.source_location,
            output_path=output_path,
            timestamp_seconds=timestamp,
        )
        keyframes.append(
            KeyframeRecord(
                keyframe_id=keyframe_id,
                clip_id=clip.clip_id,
                source_id=clip.source_id,
                source_location=clip.source_location,
                source_content_hash=clip.source_content_hash,
                clip_fingerprint=clips_fingerprint,
                frame_index=frame_index,
                timestamp_seconds=timestamp,
                image_path=output_path.relative_to(root).as_posix(),
                method="ffmpeg",
                method_version=method_version,
                evidence=[
                    {"type": "clip", "ref": clip.clip_id},
                    {"type": "tool", "ref": method_version},
                ],
                risk_flags=[],
                notes=(
                    "deterministic midpoint frame extraction; this is visual "
                    "sampling only, not visual analysis"
                ),
            )
        )
    return keyframes, warnings


def not_run_assertion(*, evidence: list[dict[str, str]]) -> Assertion:
    return Assertion(
        value=None,
        method="not_run_current_gate",
        level=0,
        confidence=0.0,
        evidence=evidence,
        user_confirmed=False,
    )


def copied_assertion(assertion: Assertion, *, fallback_evidence: list[dict[str, str]]) -> Assertion:
    return Assertion(
        value=assertion.value,
        method=assertion.method,
        level=assertion.level,
        confidence=assertion.confidence,
        evidence=assertion.evidence or fallback_evidence,
        user_confirmed=assertion.user_confirmed,
    )


def original_audio_assertion(
    *,
    source: SourceRecord,
    transcript_refs: list[str],
) -> Assertion:
    evidence = [{"type": "source", "ref": source.source_id}]
    evidence.extend({"type": "transcript", "ref": ref} for ref in transcript_refs)
    if not source.media_probe.audio_present:
        value = "not_present"
        confidence = 1.0
    elif transcript_refs:
        value = "present_transcript_available"
        confidence = 0.9
    else:
        value = "present_untranscribed"
        confidence = 0.75
    return Assertion(
        value=value,
        method="ffprobe_transcript_presence",
        level=0,
        confidence=confidence,
        evidence=evidence,
        user_confirmed=False,
    )


def transcript_refs_for_clip(
    clip: ClipRecord,
    transcripts: list[TranscriptRecord],
) -> list[str]:
    refs: list[str] = []
    for transcript in transcripts:
        if transcript.source_id != clip.source_id:
            continue
        if transcript.end_seconds <= clip.boundary.start_seconds:
            continue
        if transcript.start_seconds >= clip.boundary.end_seconds:
            continue
        refs.append(transcript.transcript_id)
    return sorted(refs)


def build_analysis(
    *,
    clips: list[ClipRecord],
    sources: list[SourceRecord],
    transcripts: list[TranscriptRecord],
    keyframes: list[KeyframeRecord],
    clip_fingerprint: str,
    analysis_fingerprint: str,
) -> tuple[list[AnalysisRecord], list[str]]:
    source_by_id = {source.source_id: source for source in sources}
    keyframes_by_clip: dict[str, list[str]] = {}
    for keyframe in keyframes:
        keyframes_by_clip.setdefault(keyframe.clip_id, []).append(keyframe.keyframe_id)

    analyses: list[AnalysisRecord] = []
    warnings: list[str] = []
    for clip in sorted(clips, key=lambda item: (item.source_location, item.clip_index)):
        source = source_by_id.get(clip.source_id)
        if source is None:
            warnings.append(f"missing source for clip {clip.clip_id}; skipped analysis")
            continue

        transcript_refs = transcript_refs_for_clip(clip, transcripts)
        keyframe_refs = sorted(keyframes_by_clip.get(clip.clip_id, []))
        evidence = [
            {"type": "source", "ref": source.source_id},
            {"type": "clip", "ref": clip.clip_id},
        ]
        evidence.extend({"type": "transcript", "ref": ref} for ref in transcript_refs)
        evidence.extend({"type": "keyframe", "ref": ref} for ref in keyframe_refs)

        risk_flags: list[AnalysisRiskFlag] = [AnalysisRiskFlag.visual_analysis_not_run]
        if source.risk_flags:
            risk_flags.append(AnalysisRiskFlag.inherited_source_risk)
        if clip.media_kind == MediaKind.video and not keyframe_refs:
            risk_flags.append(AnalysisRiskFlag.keyframe_missing)
        if source.media_probe.audio_present and not transcript_refs:
            risk_flags.append(AnalysisRiskFlag.transcript_missing)
        if not source.media_probe.audio_present:
            risk_flags.append(AnalysisRiskFlag.audio_missing)
        if clip.media_kind == MediaKind.audio:
            risk_flags.append(AnalysisRiskFlag.audio_only_clip)
        if clip.boundary.duration_seconds < 3:
            risk_flags.append(AnalysisRiskFlag.short_clip)

        analyses.append(
            AnalysisRecord(
                analysis_id=stable_analysis_id(clip.clip_id, analysis_fingerprint),
                clip_id=clip.clip_id,
                source_id=clip.source_id,
                source_location=clip.source_location,
                source_content_hash=clip.source_content_hash,
                clip_fingerprint=clip_fingerprint,
                analysis_fingerprint=analysis_fingerprint,
                media_kind=clip.media_kind,
                start_seconds=clip.boundary.start_seconds,
                end_seconds=clip.boundary.end_seconds,
                duration_seconds=clip.boundary.duration_seconds,
                material_type=copied_assertion(
                    source.source_type,
                    fallback_evidence=[{"type": "source", "ref": source.source_id}],
                ),
                shot_size=not_run_assertion(evidence=evidence),
                camera_motion=not_run_assertion(evidence=evidence),
                emotion_candidates=Assertion(
                    value=[],
                    method="not_run_current_gate",
                    level=0,
                    confidence=0.0,
                    evidence=evidence,
                    user_confirmed=False,
                ),
                action_candidates=Assertion(
                    value=[],
                    method="not_run_current_gate",
                    level=0,
                    confidence=0.0,
                    evidence=evidence,
                    user_confirmed=False,
                ),
                visual_quality=not_run_assertion(evidence=evidence),
                original_audio_usability=original_audio_assertion(
                    source=source,
                    transcript_refs=transcript_refs,
                ),
                transcript_refs=transcript_refs,
                keyframe_refs=keyframe_refs,
                evidence=evidence,
                risk_flags=sorted(set(risk_flags), key=lambda flag: flag.value),
                notes=(
                    "V0-008 records deterministic and context-derived analysis only; "
                    "shot size, motion, emotion, action, and visual quality remain "
                    "unclassified until a later visual-analysis gate opens"
                ),
            )
        )
    if not analyses:
        warnings.append("no analysis records generated")
    return analyses, warnings


def build_fixed_window_clips(
    *,
    records: list[SourceRecord],
    sources_fingerprint: str,
    window_seconds: float = 10.0,
    fallback: bool = False,
) -> list[ClipRecord]:
    clips: list[ClipRecord] = []
    for record in sorted(records, key=lambda item: item.primary_location):
        clips.extend(
            build_fixed_window_clips_for_record(
                record=record,
                sources_fingerprint=sources_fingerprint,
                window_seconds=window_seconds,
                fallback=fallback,
            )
        )
    return clips


def build_fixed_window_clips_for_record(
    *,
    record: SourceRecord,
    sources_fingerprint: str,
    window_seconds: float = 10.0,
    fallback: bool = False,
) -> list[ClipRecord]:
    clips: list[ClipRecord] = []
    duration = record.media_probe.duration
    start = 0.0
    clip_index = 0
    while start < duration:
        end = min(start + window_seconds, duration)
        clip_duration = end - start
        risk_flags: list[ClipRiskFlag] = []
        if record.risk_flags:
            risk_flags.append(ClipRiskFlag.inherited_source_risk)
        if fallback:
            risk_flags.append(ClipRiskFlag.scene_detection_fallback)
        if clip_duration < min(window_seconds, duration):
            risk_flags.append(ClipRiskFlag.short_tail)
        clips.append(
            ClipRecord(
                clip_id=stable_clip_id(record.source_id, clip_index, start, end),
                source_id=record.source_id,
                source_location=record.primary_location,
                source_content_hash=record.content_hash,
                source_fingerprint=sources_fingerprint,
                clip_index=clip_index,
                media_kind=record.media_kind,
                boundary=ClipBoundary(
                    start_seconds=round(start, 3),
                    end_seconds=round(end, 3),
                    duration_seconds=round(clip_duration, 3),
                ),
                method=ClipMethod.fixed_window,
                method_version="fixed-window-v1",
                boundary_confidence=0.5,
                evidence=[{"type": "source", "ref": record.source_id}],
                inherited_source_risk_flags=record.risk_flags,
                risk_flags=risk_flags,
                notes=(
                    "deterministic fixed-window segmentation after scene detection fallback"
                    if fallback
                    else "deterministic fixed-window segmentation"
                ),
            )
        )
        clip_index += 1
        start = end
    return clips


def build_pyscenedetect_clips_for_record(
    *,
    record: SourceRecord,
    sources_fingerprint: str,
    boundaries: list[tuple[float, float]],
    method_version: str,
) -> list[ClipRecord]:
    clips: list[ClipRecord] = []
    duration = record.media_probe.duration
    for clip_index, (raw_start, raw_end) in enumerate(boundaries):
        start = max(0.0, round(raw_start, 3))
        end = min(duration, round(raw_end, 3))
        if end <= start:
            continue
        clip_duration = round(end - start, 3)
        risk_flags: list[ClipRiskFlag] = []
        if record.risk_flags:
            risk_flags.append(ClipRiskFlag.inherited_source_risk)
        clips.append(
            ClipRecord(
                clip_id=stable_clip_id(record.source_id, clip_index, start, end),
                source_id=record.source_id,
                source_location=record.primary_location,
                source_content_hash=record.content_hash,
                source_fingerprint=sources_fingerprint,
                clip_index=clip_index,
                media_kind=record.media_kind,
                boundary=ClipBoundary(
                    start_seconds=start,
                    end_seconds=end,
                    duration_seconds=clip_duration,
                ),
                method=ClipMethod.pyscenedetect,
                method_version=method_version,
                boundary_confidence=0.75,
                evidence=[
                    {"type": "source", "ref": record.source_id},
                    {"type": "tool", "ref": method_version},
                ],
                inherited_source_risk_flags=record.risk_flags,
                risk_flags=risk_flags,
                notes="PySceneDetect content-detector scene segmentation",
            )
        )
    if not clips:
        raise SceneDetectionError(
            f"PySceneDetect produced no in-range scenes for {record.primary_location}"
        )
    return clips


def build_segment_clips(
    *,
    root: Path,
    capabilities: Capabilities,
    scene_detection: FeatureSwitch,
    records: list[SourceRecord],
    sources_fingerprint: str,
) -> tuple[list[ClipRecord], list[str]]:
    clips: list[ClipRecord] = []
    warnings: list[str] = []
    method_version = f"pyscenedetect-{pyscenedetect_version()}"

    for record in sorted(records, key=lambda item: item.primary_location):
        if record.media_kind != MediaKind.video or scene_detection == FeatureSwitch.off:
            clips.extend(
                build_fixed_window_clips_for_record(
                    record=record,
                    sources_fingerprint=sources_fingerprint,
                )
            )
            continue

        if not capabilities.pyscenedetect:
            if scene_detection == FeatureSwitch.required:
                raise WorkspaceDependencyError(
                    "scene_detection is required but PySceneDetect is not available"
                )
            warnings.append(
                "pyscenedetect_missing: using fixed_window for "
                f"{record.primary_location}"
            )
            clips.extend(
                build_fixed_window_clips_for_record(
                    record=record,
                    sources_fingerprint=sources_fingerprint,
                    fallback=True,
                )
            )
            continue

        try:
            boundaries = detect_scenes_pyscenedetect(root / record.primary_location)
            clips.extend(
                build_pyscenedetect_clips_for_record(
                    record=record,
                    sources_fingerprint=sources_fingerprint,
                    boundaries=boundaries,
                    method_version=method_version,
                )
            )
        except SceneDetectionError as exc:
            if scene_detection == FeatureSwitch.required:
                raise WorkspaceDependencyError(
                    f"scene_detection is required but PySceneDetect failed: {exc}"
                ) from exc
            warnings.append(
                "pyscenedetect_failed_fallback: using fixed_window for "
                f"{record.primary_location}: {exc}"
            )
            clips.extend(
                build_fixed_window_clips_for_record(
                    record=record,
                    sources_fingerprint=sources_fingerprint,
                    fallback=True,
                )
            )
    return clips, warnings


def invalidate_downstream_steps_for_clips(
    state: ProjectState,
    *,
    clips_fingerprint: str,
) -> list[str]:
    invalidated: list[str] = []
    for step_name in (
        "keyframes",
        "analyze",
        "map",
        "brief",
        "score",
        "propose",
        "timeline",
        "review_timeline",
        "preview",
        "review_preview",
        "final_export",
        "review_final_export",
        "review_project",
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
        if entry.input_fingerprint == clips_fingerprint:
            continue
        state.steps[step_name] = StepLedgerEntry(
            status=StepStatus.invalidated,
            input_fingerprint=entry.input_fingerprint,
            output_refs=entry.output_refs,
            last_run_id=entry.last_run_id,
            warnings=[
                *entry.warnings,
                "clips ledger changed; rerun this step before trusting its output",
            ],
        )
        invalidated.append(step_name)
    return invalidated


def invalidate_downstream_steps_for_analysis_input(
    state: ProjectState,
    *,
    input_fingerprint: str,
    reason: str,
) -> list[str]:
    invalidated: list[str] = []
    for step_name in (
        "analyze",
        "map",
        "brief",
        "score",
        "propose",
        "timeline",
        "review_timeline",
        "preview",
        "review_preview",
        "final_export",
        "review_final_export",
        "review_project",
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
        if entry.input_fingerprint == input_fingerprint:
            continue
        state.steps[step_name] = StepLedgerEntry(
            status=StepStatus.invalidated,
            input_fingerprint=entry.input_fingerprint,
            output_refs=entry.output_refs,
            last_run_id=entry.last_run_id,
            warnings=[
                *entry.warnings,
                f"{reason}; rerun this step before trusting its output",
            ],
        )
        invalidated.append(step_name)
    return invalidated


def invalidate_downstream_steps_for_analysis(
    state: ProjectState,
    *,
    analysis_fingerprint: str,
) -> list[str]:
    invalidated: list[str] = []
    for step_name in (
        "map",
        "brief",
        "propose",
        "timeline",
        "review_timeline",
        "preview",
        "review_preview",
        "final_export",
        "review_final_export",
        "review_project",
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
        if entry.input_fingerprint == analysis_fingerprint:
            continue
        state.steps[step_name] = StepLedgerEntry(
            status=StepStatus.invalidated,
            input_fingerprint=entry.input_fingerprint,
            output_refs=entry.output_refs,
            last_run_id=entry.last_run_id,
            warnings=[
                *entry.warnings,
                "analysis ledger changed; rerun this step before trusting its output",
            ],
        )
        invalidated.append(step_name)
    return invalidated


def invalidate_downstream_steps_for_map(
    state: ProjectState,
    *,
    map_fingerprint: str,
) -> list[str]:
    invalidated: list[str] = []
    for step_name in (
        "brief",
        "propose",
        "timeline",
        "review_timeline",
        "preview",
        "review_preview",
        "final_export",
        "review_final_export",
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
        if entry.input_fingerprint == map_fingerprint:
            continue
        state.steps[step_name] = StepLedgerEntry(
            status=StepStatus.invalidated,
            input_fingerprint=entry.input_fingerprint,
            output_refs=entry.output_refs,
            last_run_id=entry.last_run_id,
            warnings=[
                *entry.warnings,
                "material map changed; rerun this step before trusting its output",
            ],
        )
        invalidated.append(step_name)
    return invalidated


def scan_workspace(project_path: Path) -> tuple[ScanResult, ProjectState]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise RuntimeError("scan requires initialized state")

    run_id = new_run_id()
    previous_sources_path = root / WORKSPACE_DIR / DATA_DIR / "sources.jsonl"
    previous_records = (
        read_sources_jsonl(previous_sources_path)
        if previous_sources_path.exists()
        else []
    )
    result = scan_project_sources(root=root, config=config, previous_records=previous_records)
    output_refs: list[str] = []
    output_dir = root / config.paths.output_dir
    invalidated_steps: list[str] = []
    if result.records or not result.errors:
        output_path = write_sources_jsonl(root, result.records)
        output_refs.append(output_path.relative_to(root).as_posix())
        sources_fingerprint = fingerprint_file(output_path)
        invalidated_steps = invalidate_downstream_steps_for_sources(
            state,
            sources_fingerprint=sources_fingerprint,
        )
        scan_report_path = output_dir / "scan_report.md"
        atomic_write_text(
            scan_report_path,
            render_scan_report(
                records=result.records,
                warnings=result.warnings,
                errors=result.errors,
                sources_ref=output_path.relative_to(root).as_posix(),
                invalidated_steps=invalidated_steps,
            ),
        )
        output_refs.append(scan_report_path.relative_to(root).as_posix())

    input_fingerprint = fingerprint_file(project_path)
    if result.errors:
        status = StepStatus.failed
    elif result.warnings:
        status = StepStatus.completed_with_warnings
    else:
        status = StepStatus.completed
    state.steps["scan"] = StepLedgerEntry(
        status=status,
        input_fingerprint=input_fingerprint,
        output_refs=output_refs,
        last_run_id=run_id,
        warnings=result.warnings + result.errors,
    )
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    if result.errors:
        state.overall_status = OverallStatus.blocked
    elif result.warnings:
        state.overall_status = OverallStatus.degraded
    else:
        state.overall_status = OverallStatus.ready

    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(runs_dir / "command.json", {"command": "scan", "project": str(project_path)})
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "scan",
            "status": status.value,
            "sources": len(result.records),
            "output_refs": output_refs,
            "invalidated_steps": invalidated_steps,
        },
    )
    write_json(runs_dir / "warnings.json", result.warnings)
    write_json(runs_dir / "errors.json", result.errors)
    (runs_dir / "log.txt").write_text("scan completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(output_dir, state, result.warnings + result.errors)
    return result, state


def render_scan_report(
    *,
    records: list[SourceRecord],
    warnings: list[str],
    errors: list[str],
    sources_ref: str,
    invalidated_steps: list[str],
) -> str:
    sorted_records = sorted(records, key=lambda record: record.primary_location)
    media_counts = count_by_value(record.media_kind.value for record in sorted_records)
    rights_counts = count_by_value(str(record.rights_status.value) for record in sorted_records)
    total_duration = sum(record.media_probe.duration for record in sorted_records)
    warning_lines = "\n".join(f"- {warning}" for warning in warnings) or "- None"
    error_lines = "\n".join(f"- {error}" for error in errors) or "- None"
    invalidated_lines = "\n".join(f"- `{step}`" for step in invalidated_steps) or "- None"
    return (
        "# Scan Report\n\n"
        "This deterministic scan report is rendered from local filesystem, content "
        "hashes, sources.csv metadata, and ffprobe-derived media facts only. No "
        "transcription, visual analysis, embeddings, creative proposals, timeline "
        "generation, preview rendering, network calls, image generation/editing, or "
        "model calls were performed.\n\n"
        "## Summary\n\n"
        f"- Source ledger: `{sources_ref}`\n"
        f"- Source count: `{len(sorted_records)}`\n"
        f"- Total duration seconds: `{total_duration:.3f}`\n\n"
        "## Distribution\n\n"
        "### Media Kind\n\n"
        f"{render_count_lines(media_counts)}"
        "### Rights Status\n\n"
        f"{render_count_lines(rights_counts)}"
        "## Invalidated Downstream Steps\n\n"
        f"{invalidated_lines}\n\n"
        "## Warnings\n\n"
        f"{warning_lines}\n\n"
        "## Errors\n\n"
        f"{error_lines}\n\n"
        "## Sources\n\n"
        f"{render_scan_source_sections(sorted_records)}"
    )


def render_scan_source_sections(records: list[SourceRecord]) -> str:
    if not records:
        return "No sources were found in the current scan ledger.\n"
    sections = []
    for index, record in enumerate(records, start=1):
        probe = record.media_probe
        frame_rate = f"{probe.frame_rate:.3f}" if probe.frame_rate else "n/a"
        locations = ", ".join(f"`{location}`" for location in record.locations)
        sections.append(
            f"### {index}. `{record.primary_location}`\n\n"
            f"- Source ID: `{record.source_id}`\n"
            f"- Content hash: `{record.content_hash}`\n"
            f"- Media kind: `{record.media_kind.value}`\n"
            f"- Duration seconds: `{probe.duration:.3f}`\n"
            f"- Width: `{probe.width or 'n/a'}`\n"
            f"- Height: `{probe.height or 'n/a'}`\n"
            f"- Frame rate: `{frame_rate}`\n"
            f"- Video codec: `{probe.video_codec or 'n/a'}`\n"
            f"- Audio present: `{str(probe.audio_present).lower()}`\n"
            f"- Audio codec: `{probe.audio_codec or 'n/a'}`\n"
            f"- Rights status: `{record.rights_status.value}`\n"
            f"- Supersedes source ID: `{record.supersedes_source_id or 'none'}`\n"
            f"- Locations: {locations}\n"
        )
    return "\n".join(sections)


def segment_workspace(project_path: Path) -> tuple[Path, ProjectState, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("segment requires init to complete first")

    sources_path = root / WORKSPACE_DIR / DATA_DIR / "sources.jsonl"
    if not sources_path.exists():
        raise WorkspacePrerequisiteError("segment requires scan to complete first")

    records = read_sources_jsonl(sources_path)
    sources_fingerprint = fingerprint_file(sources_path)
    capabilities = detect_capabilities()
    state.capabilities = capabilities
    clips, segmentation_warnings = build_segment_clips(
        root=root,
        capabilities=capabilities,
        scene_detection=config.features.scene_detection,
        records=records,
        sources_fingerprint=sources_fingerprint,
    )
    warnings = segmentation_warnings
    if not records:
        warnings.append("no sources available for segmentation")
    run_id = new_run_id()
    output_dir = root / config.paths.output_dir
    clips_path = write_clips_jsonl(root, clips)
    clips_fingerprint = fingerprint_file(clips_path)
    invalidated_steps = invalidate_downstream_steps_for_clips(
        state,
        clips_fingerprint=clips_fingerprint,
    )
    clip_report_path = output_dir / "clip_report.md"
    atomic_write_text(
        clip_report_path,
        render_clip_report(
            clips=clips,
            warnings=warnings,
            clips_ref=clips_path.relative_to(root).as_posix(),
            sources_ref=sources_path.relative_to(root).as_posix(),
            invalidated_steps=invalidated_steps,
        ),
    )

    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    state.steps["segment"] = StepLedgerEntry(
        status=status,
        input_fingerprint=sources_fingerprint,
        output_refs=[
            clips_path.relative_to(root).as_posix(),
            clip_report_path.relative_to(root).as_posix(),
        ],
        last_run_id=run_id,
        warnings=warnings,
    )
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready

    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(runs_dir / "command.json", {"command": "segment", "project": str(project_path)})
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "segment",
            "status": status.value,
            "sources": len(records),
            "clips": len(clips),
            "scene_detection": config.features.scene_detection.value,
            "method_counts": count_by_value(clip.method.value for clip in clips),
            "output_refs": state.steps["segment"].output_refs,
            "invalidated_steps": invalidated_steps,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text("segment completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(output_dir, state, warnings)
    return clip_report_path, state, warnings


def render_clip_report(
    *,
    clips: list[ClipRecord],
    warnings: list[str],
    clips_ref: str,
    sources_ref: str,
    invalidated_steps: list[str],
) -> str:
    sorted_clips = sorted(clips, key=lambda clip: (clip.source_location, clip.clip_index))
    method_counts = count_by_value(clip.method.value for clip in sorted_clips)
    media_counts = count_by_value(clip.media_kind.value for clip in sorted_clips)
    source_counts = count_by_value(clip.source_location for clip in sorted_clips)
    total_duration = sum(clip.boundary.duration_seconds for clip in sorted_clips)
    warning_lines = "\n".join(f"- {warning}" for warning in warnings) or "- None"
    invalidated_lines = "\n".join(f"- `{step}`" for step in invalidated_steps) or "- None"
    return (
        "# Clip Report\n\n"
        "This deterministic clip report is rendered from local source ledger data "
        "and the configured local segmentation method. It may use PySceneDetect "
        "only when `features.scene_detection` allows it and the dependency is "
        "available; otherwise it uses fixed-window segmentation. No transcription, "
        "visual analysis, embeddings, creative proposals, timeline generation, "
        "preview rendering, network calls, BGM selection, image generation/editing, "
        "or model calls were performed.\n\n"
        "## Summary\n\n"
        f"- Source ledger: `{sources_ref}`\n"
        f"- Clip ledger: `{clips_ref}`\n"
        f"- Clip count: `{len(sorted_clips)}`\n"
        f"- Source count: `{len(source_counts)}`\n"
        f"- Total clip duration seconds: `{total_duration:.3f}`\n\n"
        "## Distribution\n\n"
        "### Method\n\n"
        f"{render_count_lines(method_counts)}"
        "### Media Kind\n\n"
        f"{render_count_lines(media_counts)}"
        "## Invalidated Downstream Steps\n\n"
        f"{invalidated_lines}\n\n"
        "## Warnings\n\n"
        f"{warning_lines}\n\n"
        "## Clips\n\n"
        f"{render_clip_sections(sorted_clips)}"
    )


def render_clip_sections(clips: list[ClipRecord]) -> str:
    if not clips:
        return "No clips were generated from the current source ledger.\n"
    sections = []
    for index, clip in enumerate(clips, start=1):
        sections.append(
            f"### {index}. `{clip.clip_id}`\n\n"
            f"- Source ID: `{clip.source_id}`\n"
            f"- Source location: `{clip.source_location}`\n"
            f"- Clip index: `{clip.clip_index}`\n"
            f"- Start seconds: `{clip.boundary.start_seconds:.3f}`\n"
            f"- End seconds: `{clip.boundary.end_seconds:.3f}`\n"
            f"- Duration seconds: `{clip.boundary.duration_seconds:.3f}`\n"
            f"- Method: `{clip.method.value}`\n"
            f"- Boundary confidence: `{clip.boundary_confidence:.3f}`\n"
        )
    return "\n".join(sections)


def transcribe_workspace(project_path: Path) -> tuple[Path | None, ProjectState, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("transcribe requires init to complete first")

    sources_path = root / WORKSPACE_DIR / DATA_DIR / "sources.jsonl"
    if not sources_path.exists():
        raise WorkspacePrerequisiteError("transcribe requires scan to complete first")

    records = read_sources_jsonl(sources_path)
    source_fingerprint = fingerprint_file(sources_path)
    capabilities = detect_capabilities()
    state.capabilities = capabilities
    run_id = new_run_id()
    output_dir = root / config.paths.output_dir
    warnings: list[str] = []
    output_path: Path | None = None
    output_refs: list[str] = []

    if config.features.transcription == FeatureSwitch.off:
        status = StepStatus.skipped
        warnings = []
    elif not capabilities.faster_whisper:
        if config.features.transcription == FeatureSwitch.required:
            raise WorkspaceDependencyError(
                "transcription is required but faster-whisper is not available"
            )
        status = StepStatus.skipped
        warnings = ["faster_whisper_missing: transcription skipped"]
    else:
        try:
            transcripts = build_transcripts(
                root=root,
                records=records,
                source_fingerprint=source_fingerprint,
            )
        except TranscriptionError as exc:
            if config.features.transcription == FeatureSwitch.required:
                raise WorkspaceDependencyError(
                    f"transcription is required but faster-whisper failed: {exc}"
                ) from exc
            status = StepStatus.skipped
            warnings = [f"faster_whisper_failed: transcription skipped: {exc}"]
        else:
            output_path = write_transcripts_jsonl(root, transcripts)
            output_refs = [output_path.relative_to(root).as_posix()]
            warnings = ["no transcript segments generated"] if not transcripts else []
            status = StepStatus.completed_with_warnings if warnings else StepStatus.completed

    analysis_invalidated_steps: list[str] = []
    clips_path = root / WORKSPACE_DIR / DATA_DIR / "clips.jsonl"
    if output_path and clips_path.exists():
        analysis_input_fingerprint = fingerprint_inputs(
            [
                ("clips", clips_path),
                ("transcripts", output_path),
                ("keyframes", root / WORKSPACE_DIR / DATA_DIR / "keyframes.jsonl"),
            ]
        )
        analysis_invalidated_steps = invalidate_downstream_steps_for_analysis_input(
            state,
            input_fingerprint=analysis_input_fingerprint,
            reason="transcript ledger changed",
        )

    state.steps["transcribe"] = StepLedgerEntry(
        status=status,
        input_fingerprint=source_fingerprint,
        output_refs=output_refs,
        last_run_id=run_id,
        warnings=warnings,
    )
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    state.overall_status = (
        OverallStatus.degraded
        if warnings
        else OverallStatus.ready
    )

    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(runs_dir / "command.json", {"command": "transcribe", "project": str(project_path)})
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "transcribe",
            "status": status.value,
            "sources": len(records),
            "transcripts": transcript_summary(output_path).get("count", 0)
            if output_path
            else 0,
            "transcription": config.features.transcription.value,
            "output_refs": output_refs,
            "invalidated_steps": analysis_invalidated_steps,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text("transcribe completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(output_dir, state, warnings)
    return output_path, state, warnings


def keyframes_workspace(project_path: Path) -> tuple[Path, ProjectState, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("keyframes requires init to complete first")

    clips_path = root / WORKSPACE_DIR / DATA_DIR / "clips.jsonl"
    if not clips_path.exists():
        raise WorkspacePrerequisiteError("keyframes requires segment to complete first")

    clips = read_clips_jsonl(clips_path)
    clips_fingerprint = fingerprint_file(clips_path)
    capabilities = detect_capabilities()
    state.capabilities = capabilities
    if any(clip.media_kind == MediaKind.video for clip in clips) and not capabilities.ffmpeg:
        raise WorkspaceDependencyError("keyframes requires ffmpeg for video clips")

    try:
        keyframes, warnings = build_keyframes(
            root=root,
            clips=clips,
            clips_fingerprint=clips_fingerprint,
        )
    except KeyframeExtractionError as exc:
        raise WorkspaceDependencyError(f"keyframe extraction failed: {exc}") from exc

    run_id = new_run_id()
    output_dir = root / config.paths.output_dir
    output_path = write_keyframes_jsonl(root, keyframes)
    analysis_input_fingerprint = fingerprint_inputs(
        [
            ("clips", clips_path),
            ("transcripts", root / WORKSPACE_DIR / DATA_DIR / "transcripts.jsonl"),
            ("keyframes", output_path),
        ]
    )
    invalidated_steps = invalidate_downstream_steps_for_analysis_input(
        state,
        input_fingerprint=analysis_input_fingerprint,
        reason="keyframe ledger changed",
    )
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    state.steps["keyframes"] = StepLedgerEntry(
        status=status,
        input_fingerprint=clips_fingerprint,
        output_refs=[output_path.relative_to(root).as_posix()],
        last_run_id=run_id,
        warnings=warnings,
    )
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready

    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(runs_dir / "command.json", {"command": "keyframes", "project": str(project_path)})
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "keyframes",
            "status": status.value,
            "clips": len(clips),
            "keyframes": len(keyframes),
            "output_refs": state.steps["keyframes"].output_refs,
            "invalidated_steps": invalidated_steps,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text("keyframes completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(output_dir, state, warnings)
    return output_path, state, warnings


def analyze_workspace(project_path: Path) -> tuple[Path, Path, ProjectState, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("analyze requires init to complete first")

    sources_path = root / WORKSPACE_DIR / DATA_DIR / "sources.jsonl"
    clips_path = root / WORKSPACE_DIR / DATA_DIR / "clips.jsonl"
    if not sources_path.exists():
        raise WorkspacePrerequisiteError("analyze requires scan to complete first")
    if not clips_path.exists():
        raise WorkspacePrerequisiteError("analyze requires segment to complete first")

    sources = read_sources_jsonl(sources_path)
    clips = read_clips_jsonl(clips_path)
    transcripts_path = root / WORKSPACE_DIR / DATA_DIR / "transcripts.jsonl"
    keyframes_path = root / WORKSPACE_DIR / DATA_DIR / "keyframes.jsonl"
    transcripts = read_transcripts_jsonl(transcripts_path) if transcripts_path.exists() else []
    keyframes = read_keyframes_jsonl(keyframes_path) if keyframes_path.exists() else []
    clip_fingerprint = fingerprint_file(clips_path)
    analysis_fingerprint = fingerprint_inputs(
        [
            ("clips", clips_path),
            ("transcripts", transcripts_path),
            ("keyframes", keyframes_path),
        ]
    )
    analyses, warnings = build_analysis(
        clips=clips,
        sources=sources,
        transcripts=transcripts,
        keyframes=keyframes,
        clip_fingerprint=clip_fingerprint,
        analysis_fingerprint=analysis_fingerprint,
    )
    run_id = new_run_id()
    output_dir = root / config.paths.output_dir
    output_path = write_analysis_jsonl(root, analyses)
    report_path = output_dir / "analysis_report.md"
    atomic_write_text(
        report_path,
        render_analysis_report(
            analyses=analyses,
            analysis_ref=output_path.relative_to(root).as_posix(),
            clips_ref=clips_path.relative_to(root).as_posix(),
            transcripts_ref=transcripts_path.relative_to(root).as_posix()
            if transcripts_path.exists()
            else None,
            keyframes_ref=keyframes_path.relative_to(root).as_posix()
            if keyframes_path.exists()
            else None,
            warnings=warnings,
        ),
    )
    invalidated_steps = invalidate_downstream_steps_for_analysis(
        state,
        analysis_fingerprint=fingerprint_file(output_path),
    )

    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    state.steps["analyze"] = StepLedgerEntry(
        status=status,
        input_fingerprint=analysis_fingerprint,
        output_refs=[
            output_path.relative_to(root).as_posix(),
            report_path.relative_to(root).as_posix(),
        ],
        last_run_id=run_id,
        warnings=warnings,
    )
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready

    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(runs_dir / "command.json", {"command": "analyze", "project": str(project_path)})
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "analyze",
            "status": status.value,
            "clips": len(clips),
            "analysis_records": len(analyses),
            "transcripts": len(transcripts),
            "keyframes": len(keyframes),
            "output_refs": state.steps["analyze"].output_refs,
            "invalidated_steps": invalidated_steps,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text("analyze completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(output_dir, state, warnings)
    return output_path, report_path, state, warnings


def render_analysis_report(
    *,
    analyses: list[AnalysisRecord],
    analysis_ref: str,
    clips_ref: str,
    transcripts_ref: str | None,
    keyframes_ref: str | None,
    warnings: list[str],
) -> str:
    media_counts = count_by_value(analysis.media_kind.value for analysis in analyses)
    risk_counts = count_by_value(
        flag.value
        for analysis in analyses
        for flag in analysis.risk_flags
    )
    audio_counts = count_by_value(
        str(analysis.original_audio_usability.value) for analysis in analyses
    )
    warning_lines = "\n".join(f"- {warning}" for warning in warnings) or "- None"
    return (
        "# Analysis Report\n\n"
        "This V0-008 report is rendered from local source, clip, transcript, and "
        "keyframe ledgers. It records deterministic and context-derived evidence "
        "only. Shot size, camera motion, emotion, action, and visual quality remain "
        "`null` or empty candidates until a later visual-analysis gate opens. No "
        "OpenCV analysis, embeddings, creative proposals, timeline generation, "
        "preview rendering, network calls, BGM selection, image generation/editing, "
        "or model calls were performed.\n\n"
        "## Inputs\n\n"
        f"- Analysis ledger: `{analysis_ref}`\n"
        f"- Clip ledger: `{clips_ref}`\n"
        f"- Transcript ledger: `{transcripts_ref or 'missing'}`\n"
        f"- Keyframe ledger: `{keyframes_ref or 'missing'}`\n\n"
        "## Summary\n\n"
        f"- Analysis record count: `{len(analyses)}`\n\n"
        "### Media Kind\n\n"
        f"{render_count_lines(media_counts)}"
        "### Original Audio Usability\n\n"
        f"{render_count_lines(audio_counts)}"
        "### Risk Flags\n\n"
        f"{render_count_lines(risk_counts)}"
        "## Warnings\n\n"
        f"{warning_lines}\n\n"
        "## Records\n\n"
        f"{render_analysis_sections(analyses)}"
    )


def render_analysis_sections(analyses: list[AnalysisRecord]) -> str:
    if not analyses:
        return "No analysis records were generated.\n"
    sections = []
    for index, analysis in enumerate(
        sorted(analyses, key=lambda item: (item.source_location, item.start_seconds)),
        start=1,
    ):
        risks = ", ".join(f"`{flag.value}`" for flag in analysis.risk_flags) or "None"
        transcript_refs = ", ".join(f"`{ref}`" for ref in analysis.transcript_refs) or "None"
        keyframe_refs = ", ".join(f"`{ref}`" for ref in analysis.keyframe_refs) or "None"
        sections.append(
            f"### {index}. `{analysis.analysis_id}`\n\n"
            f"- Clip ID: `{analysis.clip_id}`\n"
            f"- Source location: `{analysis.source_location}`\n"
            f"- Start seconds: `{analysis.start_seconds:.3f}`\n"
            f"- End seconds: `{analysis.end_seconds:.3f}`\n"
            f"- Media kind: `{analysis.media_kind.value}`\n"
            f"- Material type: `{analysis.material_type.value}` "
            f"(method `{analysis.material_type.method}`, "
            f"confidence `{analysis.material_type.confidence:.3f}`)\n"
            f"- Original audio usability: `{analysis.original_audio_usability.value}` "
            f"(confidence `{analysis.original_audio_usability.confidence:.3f}`)\n"
            f"- Transcript refs: {transcript_refs}\n"
            f"- Keyframe refs: {keyframe_refs}\n"
            f"- Risk flags: {risks}\n"
        )
    return "\n".join(sections)


def map_workspace(project_path: Path) -> tuple[Path, ProjectState, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("map requires init to complete first")

    sources_path = root / WORKSPACE_DIR / DATA_DIR / "sources.jsonl"
    if not sources_path.exists():
        raise WorkspacePrerequisiteError("map requires scan to complete first")
    records = read_sources_jsonl(sources_path)
    analysis_path = root / WORKSPACE_DIR / DATA_DIR / "analysis.jsonl"
    if not analysis_path.exists():
        raise WorkspacePrerequisiteError("map requires analyze to complete first")
    analyze_step = state.steps.get("analyze", StepLedgerEntry())
    if analyze_step.status in {StepStatus.pending, StepStatus.invalidated}:
        raise WorkspacePrerequisiteError("map requires analyze to be current first")

    analyses = read_analysis_jsonl(analysis_path)
    warnings = ["no analysis records available for material map"] if not analyses else []
    run_id = new_run_id()
    output_dir = root / config.paths.output_dir
    output_path = output_dir / "material_map.md"
    atomic_write_text(
        output_path,
        render_material_map(
            records=records,
            analyses=analyses,
            sources_ref=sources_path.relative_to(root).as_posix(),
            analysis_ref=analysis_path.relative_to(root).as_posix(),
        ),
    )

    input_fingerprint = fingerprint_inputs(
        [
            ("sources", sources_path),
            ("analysis", analysis_path),
        ]
    )
    invalidated_steps = invalidate_downstream_steps_for_map(
        state,
        map_fingerprint=fingerprint_file(output_path),
    )
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    state.steps["map"] = StepLedgerEntry(
        status=status,
        input_fingerprint=input_fingerprint,
        output_refs=[output_path.relative_to(root).as_posix()],
        last_run_id=run_id,
        warnings=warnings,
    )
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready

    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(runs_dir / "command.json", {"command": "map", "project": str(project_path)})
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "map",
            "status": status.value,
            "sources": len(records),
            "analysis_records": len(analyses),
            "output": output_path.relative_to(root).as_posix(),
            "invalidated_steps": invalidated_steps,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text("map completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(output_dir, state, warnings)
    return output_path, state, warnings


def propose_workspace(project_path: Path) -> ProjectState:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("propose requires init to complete first")

    material_map_path = root / config.paths.output_dir / "material_map.md"
    sources_path = root / WORKSPACE_DIR / DATA_DIR / "sources.jsonl"
    clips_path = root / WORKSPACE_DIR / DATA_DIR / "clips.jsonl"
    analysis_path = root / WORKSPACE_DIR / DATA_DIR / "analysis.jsonl"
    clip_scores_path = root / WORKSPACE_DIR / DATA_DIR / "clip_scores.jsonl"
    prerequisites = {
        "map": material_map_path,
        "scan": sources_path,
        "segment": clips_path,
        "analyze": analysis_path,
        "score": clip_scores_path,
    }
    for stage, artifact in prerequisites.items():
        if not artifact.exists():
            raise WorkspacePrerequisiteError(f"propose requires {stage} to complete first")
    for stage in ("map", "score"):
        if state.steps.get(stage, StepLedgerEntry()).status in {
            StepStatus.pending,
            StepStatus.invalidated,
        }:
            raise WorkspacePrerequisiteError(f"propose requires {stage} to be current first")

    sources = read_sources_jsonl(sources_path)
    clips = read_clips_jsonl(clips_path)
    analyses = read_analysis_jsonl(analysis_path)
    from artist_portrait_editor.clip_scoring import read_clip_scores_jsonl

    clip_scores = read_clip_scores_jsonl(clip_scores_path)
    input_fingerprint = fingerprint_inputs(
        [
            ("sources", sources_path),
            ("clips", clips_path),
            ("analysis", analysis_path),
            ("clip_scores", clip_scores_path),
            ("material_map", material_map_path),
        ]
    )
    proposal_context = build_proposal_context(
        config=config,
        sources=sources,
        clips=clips,
        analyses=analyses,
        clip_scores=clip_scores,
        sources_ref=sources_path.relative_to(root).as_posix(),
        clips_ref=clips_path.relative_to(root).as_posix(),
        analysis_ref=analysis_path.relative_to(root).as_posix(),
        clip_scores_ref=clip_scores_path.relative_to(root).as_posix(),
        clip_scores_fingerprint=fingerprint_file(clip_scores_path),
        material_map_ref=material_map_path.relative_to(root).as_posix(),
        material_map_fingerprint=fingerprint_file(material_map_path),
        input_fingerprint=input_fingerprint,
    )
    context_path = write_proposal_context_json(root, proposal_context)
    handoff_path = write_agent_handoff_bundle(
        root=root,
        output_dir=config.paths.output_dir,
        context=proposal_context,
    )
    output_refs = [
        context_path.relative_to(root).as_posix(),
        handoff_path.relative_to(root).as_posix(),
    ]
    warnings = [
        "host_agent_candidate_required: proposal handoff is ready; generate a "
        "ProposalSet with the active Codex/ChatGPT Agent and import it with "
        "--agent-output"
    ]
    run_id = new_run_id()
    state.steps["propose"] = StepLedgerEntry(
        status=StepStatus.blocked,
        input_fingerprint=input_fingerprint,
        output_refs=output_refs,
        last_run_id=run_id,
        warnings=warnings,
    )
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    state.overall_status = OverallStatus.blocked
    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(runs_dir / "command.json", {"command": "propose", "project": str(project_path)})
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "propose",
            "status": StepStatus.blocked.value,
            "proposal_context": output_refs[0],
            "proposal_agent_handoff": output_refs[1],
            "reason": "host_agent_candidate_required",
            "model_call_performed": False,
            "network_performed": False,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text("host Agent proposal handoff prepared\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(root / config.paths.output_dir, state, warnings)
    return state


def import_agent_proposal_workspace(
    project_path: Path,
    candidate_path: Path,
) -> dict[str, object]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError(
            "agent proposal import requires init to complete first"
        )

    context_path = root / WORKSPACE_DIR / DATA_DIR / "proposal_context.json"
    handoff_path = root / config.paths.output_dir / "proposal_agent_handoff.json"
    if not context_path.exists() or not handoff_path.exists():
        raise WorkspacePrerequisiteError(
            "agent proposal import requires propose to prepare the Agent handoff first"
        )

    context = read_proposal_context_json(context_path)

    try:
        quarantined = quarantine_agent_candidate(
            root=root,
            candidate_path=candidate_path,
        )
        proposal_set = parse_quarantined_proposal_set(quarantined)
        require_host_agent_method(
            proposal_set=proposal_set,
            candidate=quarantined,
        )
    except AgentProposalCandidateError as exc:
        raise WorkspaceProposalCandidateError(
            str(exc),
            code=exc.code,
            quarantine_ref=exc.quarantine_ref,
        ) from exc

    quarantine_validation = build_proposal_validation_report(
        proposal_set=proposal_set,
        context=context,
        proposal_context_ref=context_path.relative_to(root).as_posix(),
        proposals_ref=quarantined.ref,
        input_fingerprint=fingerprint_inputs(
            [
                ("proposal_context", context_path),
                ("agent_candidate", quarantined.path),
            ]
        ),
    )
    if quarantine_validation.error_count:
        validation_path = quarantined.path.with_suffix(".validation.json")
        validation_path.write_text(
            json.dumps(
                quarantine_validation.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        codes = sorted(
            {
                issue.code
                for issue in quarantine_validation.issues
                if issue.severity == "error"
            }
        )
        raise WorkspaceProposalCandidateError(
            "agent proposal candidate failed semantic validation: "
            + ", ".join(codes),
            code="agent_candidate_semantic_invalid",
            quarantine_ref=quarantined.ref,
        )

    proposals_path = root / WORKSPACE_DIR / DATA_DIR / "proposals.json"
    atomic_write_text(
        proposals_path,
        json.dumps(
            proposal_set.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    validation = build_proposal_validation_report(
        proposal_set=proposal_set,
        context=context,
        proposal_context_ref=context_path.relative_to(root).as_posix(),
        proposals_ref=proposals_path.relative_to(root).as_posix(),
        input_fingerprint=fingerprint_inputs(
            [
                ("proposal_context", context_path),
                ("proposals", proposals_path),
            ]
        ),
    )
    validation_path = write_proposal_validation_json(root, validation)
    review_path = root / config.paths.output_dir / "proposal_review.md"
    atomic_write_text(review_path, render_proposal_review_report(validation))

    warnings = (
        [f"{validation.warning_count} proposal validation warning(s) found"]
        if validation.warning_count
        else []
    )
    run_id = new_run_id()
    output_refs = [
        handoff_path.relative_to(root).as_posix(),
        quarantined.ref,
        proposals_path.relative_to(root).as_posix(),
        validation_path.relative_to(root).as_posix(),
        review_path.relative_to(root).as_posix(),
    ]
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    state.steps["propose"] = StepLedgerEntry(
        status=status,
        input_fingerprint="sha256:" + quarantined.sha256,
        output_refs=output_refs,
        last_run_id=run_id,
        warnings=warnings,
    )
    state.steps["review_proposal"] = StepLedgerEntry(
        status=status,
        input_fingerprint=validation.input_fingerprint,
        output_refs=[
            validation_path.relative_to(root).as_posix(),
            review_path.relative_to(root).as_posix(),
        ],
        last_run_id=run_id,
        warnings=warnings,
    )
    for step_name in (
        "timeline",
        "review_timeline",
        "bgm_fit",
        "preview",
        "review_preview",
        "final_export",
        "review_final_export",
    ):
        existing = state.steps.get(step_name)
        if existing and existing.status in {
            StepStatus.completed,
            StepStatus.completed_with_warnings,
        }:
            state.steps[step_name] = StepLedgerEntry(
                status=StepStatus.invalidated,
                input_fingerprint=existing.input_fingerprint,
                output_refs=existing.output_refs,
                last_run_id=existing.last_run_id,
                warnings=[
                    *existing.warnings,
                    "canonical proposals changed; regenerate the selected-proposal timeline",
                ],
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
            "command": "propose",
            "mode": "host_agent_import",
            "project": str(project_path),
            "candidate": str(candidate_path),
        },
    )
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "propose",
            "status": status.value,
            "host_agent": True,
            "paid_api_call_performed": False,
            "network_performed": False,
            "candidate_sha256": quarantined.sha256,
            "candidate_bytes": quarantined.byte_count,
            "output_refs": output_refs,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text(
        "host Agent proposal imported, validated, and promoted\n",
        encoding="utf-8",
    )
    save_state(root, state)
    write_run_report(root / config.paths.output_dir, state, warnings)
    return {
        "status": status.value,
        "handoff_ref": handoff_path.relative_to(root).as_posix(),
        "quarantine_ref": quarantined.ref,
        "proposals_ref": proposals_path.relative_to(root).as_posix(),
        "validation_ref": validation_path.relative_to(root).as_posix(),
        "review_ref": review_path.relative_to(root).as_posix(),
        "warnings": warnings,
    }


def render_material_map(
    *,
    records: list[SourceRecord],
    analyses: list[AnalysisRecord],
    sources_ref: str,
    analysis_ref: str,
) -> str:
    sorted_records = sorted(records, key=lambda record: record.primary_location)
    sorted_analyses = sorted(analyses, key=lambda item: (item.source_location, item.start_seconds))
    total_duration = sum(record.media_probe.duration for record in sorted_records)
    media_counts = count_by_value(record.media_kind.value for record in sorted_records)
    source_type_counts = count_by_value(
        str(record.source_type.value) for record in sorted_records
    )
    rights_counts = count_by_value(str(record.rights_status.value) for record in sorted_records)
    analysis_material_counts = count_by_value(
        str(analysis.material_type.value) for analysis in sorted_analyses
    )
    audio_counts = count_by_value(
        str(analysis.original_audio_usability.value) for analysis in sorted_analyses
    )
    risk_counts = count_by_value(
        flag.value
        for analysis in sorted_analyses
        for flag in analysis.risk_flags
    )

    return (
        "# Material Map\n\n"
        "This deterministic material map is rendered from local source and analysis "
        "ledgers. It ranks clips for human review using evidence coverage and risk "
        "signals only. It does not perform OpenCV/vision-model visual classification, "
        "embeddings, creative proposals, timeline generation, preview rendering, "
        "network calls, BGM selection, image generation/editing, or model calls.\n\n"
        "## Summary\n\n"
        f"- Source ledger: `{sources_ref}`\n"
        f"- Analysis ledger: `{analysis_ref}`\n"
        f"- Source count: `{len(sorted_records)}`\n"
        f"- Analysis record count: `{len(sorted_analyses)}`\n"
        f"- Total duration seconds: `{total_duration:.3f}`\n\n"
        "## Distribution\n\n"
        "### Media Kind\n\n"
        f"{render_count_lines(media_counts)}\n"
        "### Source Type\n\n"
        f"{render_count_lines(source_type_counts)}\n"
        "### Analysis Material Type\n\n"
        f"{render_count_lines(analysis_material_counts)}\n"
        "### Original Audio Usability\n\n"
        f"{render_count_lines(audio_counts)}\n"
        "### Rights Status\n\n"
        f"{render_count_lines(rights_counts)}\n"
        "### Risk Flags\n\n"
        f"{render_count_lines(risk_counts)}\n"
        "## Priority Review Queue\n\n"
        f"{render_priority_review_queue(sorted_analyses)}"
        "## Pending Confirmation\n\n"
        f"{render_pending_confirmation(sorted_analyses)}"
        "## Risk Items\n\n"
        f"{render_material_map_risks(sorted_analyses)}"
        "## Sources\n\n"
        f"{render_source_sections(sorted_records)}"
    )


def analysis_review_score(analysis: AnalysisRecord) -> float:
    score = analysis.duration_seconds
    if analysis.keyframe_refs:
        score += 2.0
    if analysis.transcript_refs:
        score += 2.0
    score -= len(analysis.risk_flags) * 0.5
    return round(max(score, 0.0), 3)


def render_priority_review_queue(analyses: list[AnalysisRecord]) -> str:
    if not analyses:
        return "No analysis records are available for review prioritization.\n\n"
    ranked = sorted(
        analyses,
        key=lambda analysis: (
            -analysis_review_score(analysis),
            analysis.source_location,
            analysis.start_seconds,
        ),
    )
    lines = []
    for index, analysis in enumerate(ranked, start=1):
        reasons = []
        if analysis.keyframe_refs:
            reasons.append("has keyframe evidence")
        if analysis.transcript_refs:
            reasons.append("has transcript evidence")
        if not reasons:
            reasons.append("needs manual evidence review")
        risk_count = len(analysis.risk_flags)
        lines.append(
            f"{index}. `{analysis.clip_id}` score `{analysis_review_score(analysis):.3f}` - "
            f"{analysis.source_location} "
            f"{analysis.start_seconds:.3f}-{analysis.end_seconds:.3f}s; "
            f"{', '.join(reasons)}; risks `{risk_count}`"
        )
    return "\n".join(lines) + "\n\n"


def render_pending_confirmation(analyses: list[AnalysisRecord]) -> str:
    if not analyses:
        return "- None\n\n"
    lines = []
    for analysis in analyses:
        pending = []
        if analysis.shot_size.value is None:
            pending.append("shot_size")
        if analysis.camera_motion.value is None:
            pending.append("camera_motion")
        if analysis.visual_quality.value is None:
            pending.append("visual_quality")
        if not analysis.emotion_candidates.value:
            pending.append("emotion_candidates")
        if not analysis.action_candidates.value:
            pending.append("action_candidates")
        if pending:
            lines.append(
                f"- `{analysis.clip_id}` requires confirmation for "
                f"{', '.join(pending)}"
            )
    return ("\n".join(lines) if lines else "- None") + "\n\n"


def render_material_map_risks(analyses: list[AnalysisRecord]) -> str:
    rows = []
    for analysis in analyses:
        if not analysis.risk_flags:
            continue
        risks = ", ".join(f"`{flag.value}`" for flag in analysis.risk_flags)
        rows.append(f"- `{analysis.clip_id}`: {risks}")
    return ("\n".join(rows) if rows else "- None") + "\n\n"


def render_count_lines(counts: dict[str, int]) -> str:
    if not counts:
        return "- None\n\n"
    return "".join(f"- `{key}`: {value}\n" for key, value in counts.items()) + "\n"


def render_source_sections(records: list[SourceRecord]) -> str:
    if not records:
        return "No sources were found in the current scan ledger.\n"
    sections = []
    for index, record in enumerate(records, start=1):
        sections.append(render_source_section(index, record))
    return "\n".join(sections)


def render_source_section(index: int, record: SourceRecord) -> str:
    probe = record.media_probe
    dimensions = f"{probe.width}x{probe.height}" if probe.width and probe.height else "n/a"
    frame_rate = f"{probe.frame_rate:.3f}" if probe.frame_rate else "n/a"
    supersedes = f"`{record.supersedes_source_id}`" if record.supersedes_source_id else "None"
    risk_flags = ", ".join(f"`{flag.value}`" for flag in record.risk_flags) or "None"
    locations = "".join(f"  - `{location}`\n" for location in record.locations)
    notes = record.notes or "None"
    return (
        f"### {index}. `{record.primary_location}`\n\n"
        f"- Source ID: `{record.source_id}`\n"
        f"- Media kind: `{record.media_kind.value}`\n"
        f"- Duration seconds: `{probe.duration:.3f}`\n"
        f"- Dimensions: `{dimensions}`\n"
        f"- Frame rate: `{frame_rate}`\n"
        f"- Video codec: `{probe.video_codec or 'n/a'}`\n"
        f"- Audio present: `{str(probe.audio_present).lower()}`\n"
        f"- Audio codec: `{probe.audio_codec or 'n/a'}`\n"
        f"- Source type: `{record.source_type.value}` "
        f"(method `{record.source_type.method}`, confidence `{record.source_type.confidence:.3f}`)\n"
        f"- Rights status: `{record.rights_status.value}` "
        f"(method `{record.rights_status.method}`, confidence `{record.rights_status.confidence:.3f}`)\n"
        f"- Provenance confidence: `{record.provenance_confidence:.3f}`\n"
        f"- Forbidden by user: `{str(record.forbidden_by_user).lower()}`\n"
        f"- Supersedes source ID: {supersedes}\n"
        f"- Risk flags: {risk_flags}\n"
        f"- Notes: {notes}\n"
        "- Locations:\n"
        f"{locations}"
    )


def read_timeline_draft(path: Path) -> TimelineDraft:
    try:
        return TimelineDraft.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise WorkspaceTimelineError(f"invalid TimelineDraft JSON: {exc}") from exc


def read_edit_brief_json(path: Path) -> EditBrief:
    try:
        return EditBrief.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise WorkspaceTimelineError(f"invalid EditBrief JSON: {exc}") from exc


def timeline_workspace(
    project_path: Path,
    *,
    proposal_id: str,
) -> tuple[Path, Path, Path, ProjectState, list[str], list[dict]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("timeline requires init to complete first")
    if state.steps.get("propose", StepLedgerEntry()).status not in {
        StepStatus.completed,
        StepStatus.completed_with_warnings,
    }:
        raise WorkspacePrerequisiteError(
            "timeline requires a validated canonical proposal import first"
        )
    for prerequisite in ("brief", "score"):
        if state.steps.get(prerequisite, StepLedgerEntry()).status not in {
            StepStatus.completed,
            StepStatus.completed_with_warnings,
        }:
            raise WorkspacePrerequisiteError(
                f"timeline requires {prerequisite} to complete first"
            )
    proposals_path = root / WORKSPACE_DIR / DATA_DIR / "proposals.json"
    clips_path = root / WORKSPACE_DIR / DATA_DIR / "clips.jsonl"
    sources_path = root / WORKSPACE_DIR / DATA_DIR / "sources.jsonl"
    edit_brief_path = root / WORKSPACE_DIR / DATA_DIR / "edit_brief.json"
    clip_scores_path = root / WORKSPACE_DIR / DATA_DIR / "clip_scores.jsonl"
    if not proposals_path.exists():
        raise WorkspacePrerequisiteError("timeline requires canonical proposals.json first")
    if not clips_path.exists() or not sources_path.exists():
        raise WorkspacePrerequisiteError("timeline requires current sources and clips first")
    if not edit_brief_path.exists() or not clip_scores_path.exists():
        raise WorkspacePrerequisiteError(
            "timeline requires current edit_brief.json and clip_scores.jsonl first"
        )
    try:
        selected_id = ProposalId(proposal_id)
    except ValueError as exc:
        raise WorkspaceTimelineError(
            "timeline proposal must be proposal_safe, proposal_advanced, or proposal_risky"
        ) from exc

    proposal_set = read_proposals_json(proposals_path)
    clips = read_clips_jsonl(clips_path)
    sources = read_sources_jsonl(sources_path)
    edit_brief = read_edit_brief_json(edit_brief_path)
    from artist_portrait_editor.clip_scoring import read_clip_scores_jsonl

    clip_scores = read_clip_scores_jsonl(clip_scores_path)
    edit_brief_ref = edit_brief_path.relative_to(root).as_posix()
    clip_scores_ref = clip_scores_path.relative_to(root).as_posix()
    edit_brief_fingerprint = fingerprint_file(edit_brief_path)
    clip_scores_fingerprint = fingerprint_file(clip_scores_path)
    input_fingerprint = fingerprint_inputs(
        [
            ("project", project_path),
            ("proposals", proposals_path),
            ("clips", clips_path),
            ("sources", sources_path),
            ("edit_brief", edit_brief_path),
            ("clip_scores", clip_scores_path),
        ]
    )
    try:
        timeline = build_timeline_draft(
            config=config,
            proposal_set=proposal_set,
            clips=clips,
            sources=sources,
            edit_brief=edit_brief,
            edit_brief_ref=edit_brief_ref,
            edit_brief_fingerprint=edit_brief_fingerprint,
            clip_scores=clip_scores,
            clip_scores_ref=clip_scores_ref,
            clip_scores_fingerprint=clip_scores_fingerprint,
            proposal_id=selected_id,
            input_fingerprint=input_fingerprint,
        )
    except TimelineBuildError as exc:
        raise WorkspaceTimelineError(str(exc)) from exc

    output_dir = root / config.paths.output_dir
    timeline_path = output_dir / "timeline_draft.json"
    timeline_ref = timeline_path.relative_to(root).as_posix()
    validation = validate_timeline_draft(
        timeline=timeline,
        proposal_set=proposal_set,
        clips=clips,
        sources=sources,
        edit_brief=edit_brief,
        clip_scores=clip_scores,
        timeline_ref=timeline_ref,
        input_fingerprint=input_fingerprint,
    )
    if validation.error_count:
        raise WorkspaceTimelineError(
            "generated timeline failed validation: "
            + ", ".join(
                sorted(
                    {
                        issue.code
                        for issue in validation.issues
                        if issue.severity == "error"
                    }
                )
            )
        )

    atomic_write_text(
        timeline_path,
        json.dumps(
            timeline.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    validation_path = root / WORKSPACE_DIR / DATA_DIR / "timeline_validation.json"
    atomic_write_text(
        validation_path,
        json.dumps(
            validation.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    review_path = output_dir / "timeline_review.md"
    atomic_write_text(review_path, render_timeline_review(validation))

    warnings = list(timeline.warnings)
    warnings.extend(
        issue.detail for issue in validation.issues if issue.severity == "warning"
    )
    warnings = list(dict.fromkeys(warnings))
    run_id = new_run_id()
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    output_refs = [
        timeline_ref,
        validation_path.relative_to(root).as_posix(),
        review_path.relative_to(root).as_posix(),
    ]
    state.steps["timeline"] = StepLedgerEntry(
        status=status,
        input_fingerprint=input_fingerprint,
        output_refs=output_refs,
        last_run_id=run_id,
        warnings=warnings,
    )
    state.steps["review_timeline"] = StepLedgerEntry(
        status=status,
        input_fingerprint=input_fingerprint,
        output_refs=[
            validation_path.relative_to(root).as_posix(),
            review_path.relative_to(root).as_posix(),
        ],
        last_run_id=run_id,
        warnings=warnings,
    )
    timeline_dependents = {
        "bgm_fit": "canonical timeline changed; rerun BGM fitting",
        "preview": "canonical timeline changed; rerun preview",
        "review_preview": "canonical timeline changed; rerun preview review",
        "final_export": "canonical timeline changed; rerun final export",
        "review_final_export": "canonical timeline changed; rerun final export review",
    }
    for step_name, reason in timeline_dependents.items():
        existing = state.steps.get(step_name)
        if existing and existing.status in {
            StepStatus.completed,
            StepStatus.completed_with_warnings,
        }:
            state.steps[step_name] = StepLedgerEntry(
                status=StepStatus.invalidated,
                input_fingerprint=existing.input_fingerprint,
                output_refs=existing.output_refs,
                last_run_id=existing.last_run_id,
                warnings=[*existing.warnings, reason],
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
            "command": "timeline",
            "project": str(project_path),
            "proposal": selected_id.value,
        },
    )
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "timeline",
            "status": status.value,
            "proposal_id": selected_id.value,
            "segments": len(timeline.segments),
            "actual_duration": timeline.actual_duration,
            "edit_brief_ref": edit_brief_ref,
            "clip_scores_ref": clip_scores_ref,
            "structural_roles": sorted({segment.structural_role.value for segment in timeline.segments}),
            "dropped_clips": len(timeline.dropped_clips),
            "continuity_checks": len(timeline.continuity_checks),
            "music_status": timeline.music_plan.status.value,
            "bgm_selection_performed": False,
            "beat_analysis_performed": False,
            "render_performed": False,
            "network_performed": False,
            "output_refs": output_refs,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text("timeline completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(output_dir, state, warnings)
    return (
        timeline_path,
        validation_path,
        review_path,
        state,
        warnings,
        [issue.model_dump(mode="json") for issue in validation.issues],
    )


def review_timeline_workspace(
    project_path: Path,
) -> tuple[Path, Path, ProjectState, list[str], list[dict]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError(
            "review --scope timeline requires init to complete first"
        )
    timeline_path = root / config.paths.output_dir / "timeline_draft.json"
    proposals_path = root / WORKSPACE_DIR / DATA_DIR / "proposals.json"
    clips_path = root / WORKSPACE_DIR / DATA_DIR / "clips.jsonl"
    sources_path = root / WORKSPACE_DIR / DATA_DIR / "sources.jsonl"
    edit_brief_path = root / WORKSPACE_DIR / DATA_DIR / "edit_brief.json"
    clip_scores_path = root / WORKSPACE_DIR / DATA_DIR / "clip_scores.jsonl"
    if not timeline_path.exists():
        raise WorkspacePrerequisiteError(
            "review --scope timeline requires timeline generation first"
        )
    if (
        not proposals_path.exists()
        or not clips_path.exists()
        or not sources_path.exists()
        or not edit_brief_path.exists()
        or not clip_scores_path.exists()
    ):
        raise WorkspacePrerequisiteError(
            "review --scope timeline requires proposals, clips, sources, edit brief, and clip scores"
        )
    timeline = read_timeline_draft(timeline_path)
    proposal_set = read_proposals_json(proposals_path)
    clips = read_clips_jsonl(clips_path)
    sources = read_sources_jsonl(sources_path)
    edit_brief = read_edit_brief_json(edit_brief_path)
    from artist_portrait_editor.clip_scoring import read_clip_scores_jsonl

    clip_scores = read_clip_scores_jsonl(clip_scores_path)
    input_fingerprint = fingerprint_inputs(
        [
            ("project", project_path),
            ("proposals", proposals_path),
            ("clips", clips_path),
            ("sources", sources_path),
            ("edit_brief", edit_brief_path),
            ("clip_scores", clip_scores_path),
        ]
    )
    validation = validate_timeline_draft(
        timeline=timeline,
        proposal_set=proposal_set,
        clips=clips,
        sources=sources,
        edit_brief=edit_brief,
        clip_scores=clip_scores,
        timeline_ref=timeline_path.relative_to(root).as_posix(),
        input_fingerprint=input_fingerprint,
    )
    validation_path = root / WORKSPACE_DIR / DATA_DIR / "timeline_validation.json"
    atomic_write_text(
        validation_path,
        json.dumps(
            validation.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    report_path = root / config.paths.output_dir / "timeline_review.md"
    atomic_write_text(report_path, render_timeline_review(validation))
    warnings = [f"{validation.issue_count} timeline issue(s) found"] if validation.issue_count else []
    run_id = new_run_id()
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    state.steps["review_timeline"] = StepLedgerEntry(
        status=status,
        input_fingerprint=input_fingerprint,
        output_refs=[
            validation_path.relative_to(root).as_posix(),
            report_path.relative_to(root).as_posix(),
        ],
        last_run_id=run_id,
        warnings=warnings,
    )
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready
    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        runs_dir / "command.json",
        {"command": "review", "scope": "timeline", "project": str(project_path)},
    )
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "review_timeline",
            "status": status.value,
            "issues": validation.issue_count,
            "errors": validation.error_count,
            "warnings": validation.warning_count,
            "output_refs": state.steps["review_timeline"].output_refs,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(
        runs_dir / "errors.json",
        [issue.code for issue in validation.issues if issue.severity == "error"],
    )
    (runs_dir / "log.txt").write_text("review timeline completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(root / config.paths.output_dir, state, warnings)
    return (
        validation_path,
        report_path,
        state,
        warnings,
        [issue.model_dump(mode="json") for issue in validation.issues],
    )


def review_project_workspace(
    project_path: Path,
    *,
    scope: str = "project",
) -> tuple[Path, ProjectState, list[str], list[dict[str, str]]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("review requires init to complete first")

    sources_path = root / WORKSPACE_DIR / DATA_DIR / "sources.jsonl"
    if not sources_path.exists():
        raise WorkspacePrerequisiteError(
            "review --scope project requires scan to complete first"
        )

    records = read_sources_jsonl(sources_path)
    issues = review_source_risks(
        records,
        allow_restricted_rights=config.content_policy.allow_restricted_rights,
    )
    issues.extend(ledger_output_ref_issues(root, state))
    issues.extend(
        issue
        for issue in invalidated_step_issues(project_path, state)
        if issue.get("code") != "review_project_invalidated"
    )
    if scope == "all":
        issues.extend(review_all_scope_issues())
    warnings = [f"{len(issues)} project review issue(s) found"] if issues else []
    run_id = new_run_id()
    output_dir = root / config.paths.output_dir
    output_path = output_dir / "risk_report.md"
    atomic_write_text(
        output_path,
        render_risk_report(
            records=records,
            issues=issues,
            sources_ref=sources_path.relative_to(root).as_posix(),
        ),
    )

    input_fingerprint = fingerprint_file(sources_path)
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    state.steps["review_project"] = StepLedgerEntry(
        status=status,
        input_fingerprint=input_fingerprint,
        output_refs=[output_path.relative_to(root).as_posix()],
        last_run_id=run_id,
        warnings=warnings,
    )
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready

    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        runs_dir / "command.json",
        {"command": "review", "scope": scope, "project": str(project_path)},
    )
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "review_project",
            "status": status.value,
            "sources": len(records),
            "issues": len(issues),
            "output": output_path.relative_to(root).as_posix(),
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text("review project completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(output_dir, state, warnings)
    return output_path, state, warnings, issues


def review_proposal_workspace(
    project_path: Path,
) -> tuple[Path, Path, ProjectState, list[str], list[dict[str, str]]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("review --scope proposal requires init to complete first")

    context_path = root / WORKSPACE_DIR / DATA_DIR / "proposal_context.json"
    proposals_path = root / WORKSPACE_DIR / DATA_DIR / "proposals.json"
    if not context_path.exists():
        raise WorkspacePrerequisiteError(
            "review --scope proposal requires propose to prepare proposal context first"
        )
    if not proposals_path.exists():
        raise WorkspacePrerequisiteError(
            "review --scope proposal requires proposals.json to exist first"
        )

    context = read_proposal_context_json(context_path)
    proposal_set = read_proposals_json(proposals_path)
    input_fingerprint = fingerprint_inputs(
        [
            ("proposal_context", context_path),
            ("proposals", proposals_path),
        ]
    )
    validation = build_proposal_validation_report(
        proposal_set=proposal_set,
        context=context,
        proposal_context_ref=context_path.relative_to(root).as_posix(),
        proposals_ref=proposals_path.relative_to(root).as_posix(),
        input_fingerprint=input_fingerprint,
    )
    validation_path = write_proposal_validation_json(root, validation)
    output_dir = root / config.paths.output_dir
    report_path = output_dir / "proposal_review.md"
    atomic_write_text(report_path, render_proposal_review_report(validation))

    warnings = (
        [f"{validation.issue_count} proposal validation issue(s) found"]
        if validation.issue_count
        else []
    )
    run_id = new_run_id()
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    state.steps["review_proposal"] = StepLedgerEntry(
        status=status,
        input_fingerprint=input_fingerprint,
        output_refs=[
            validation_path.relative_to(root).as_posix(),
            report_path.relative_to(root).as_posix(),
        ],
        last_run_id=run_id,
        warnings=warnings,
    )
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready

    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        runs_dir / "command.json",
        {"command": "review", "scope": "proposal", "project": str(project_path)},
    )
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "review_proposal",
            "status": status.value,
            "proposal_count": validation.proposal_count,
            "issues": validation.issue_count,
            "errors": validation.error_count,
            "warnings": validation.warning_count,
            "output_refs": state.steps["review_proposal"].output_refs,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(
        runs_dir / "errors.json",
        [issue.code for issue in validation.issues if issue.severity == "error"],
    )
    (runs_dir / "log.txt").write_text("review proposal completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(output_dir, state, warnings)
    return (
        validation_path,
        report_path,
        state,
        warnings,
        [issue.model_dump(mode="json") for issue in validation.issues],
    )


def review_all_scope_issues() -> list[dict[str, str]]:
    return []


def review_source_risks(
    records: list[SourceRecord],
    *,
    allow_restricted_rights: bool,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for record in sorted(records, key=lambda item: item.primary_location):
        if record.provenance_confidence < 0.7:
            issues.append(
                risk_issue(
                    source=record,
                    code="low_provenance_confidence",
                    severity="warning",
                    detail=(
                        "provenance_confidence is below 0.7; do not use this source "
                        "as a confirmed factual basis without user confirmation"
                    ),
                )
            )
        if record.rights_status.value == RightsStatus.permission_unknown:
            issues.append(
                risk_issue(
                    source=record,
                    code="rights_unknown",
                    severity="warning",
                    detail="rights_status is permission_unknown",
                )
            )
        if record.rights_status.value == RightsStatus.restricted and not allow_restricted_rights:
            issues.append(
                risk_issue(
                    source=record,
                    code="rights_restricted",
                    severity="error",
                    detail="rights_status is restricted and project policy does not allow restricted rights",
                )
            )
        if record.forbidden_by_user:
            issues.append(
                risk_issue(
                    source=record,
                    code="forbidden_by_user",
                    severity="error",
                    detail="source is marked forbidden_by_user and must not enter proposals, timelines, or previews",
                )
            )
    return issues


def render_proposal_review_report(report: ProposalValidationReport) -> str:
    severity_counts = count_by_value(issue.severity for issue in report.issues)
    code_counts = count_by_value(issue.code for issue in report.issues)
    return (
        "# Proposal Review\n\n"
        "This deterministic proposal review validates an existing proposals.json "
        "against the local proposal context. It does not generate proposals, call "
        "models, choose BGM, create timelines, or render previews.\n\n"
        "## Summary\n\n"
        f"- Proposal context: `{report.proposal_context_ref}`\n"
        f"- Proposals: `{report.proposals_ref}`\n"
        f"- Proposal count: `{report.proposal_count}`\n"
        f"- Issue count: `{report.issue_count}`\n"
        f"- Error count: `{report.error_count}`\n"
        f"- Warning count: `{report.warning_count}`\n\n"
        "## Severity Counts\n\n"
        f"{render_count_lines(severity_counts)}"
        "## Issue Counts\n\n"
        f"{render_count_lines(code_counts)}"
        "## Issues\n\n"
        f"{render_proposal_validation_issue_sections(report.issues)}"
    )


def render_proposal_validation_issue_sections(
    issues: list[ProposalValidationIssue],
) -> str:
    if not issues:
        return "No proposal validation issues were found.\n"
    sections = []
    for index, issue in enumerate(issues, start=1):
        optional_lines = ""
        if issue.proposal_id:
            optional_lines += f"- Proposal ID: `{issue.proposal_id}`\n"
        if issue.ref:
            optional_lines += f"- Ref: `{issue.ref}`\n"
        sections.append(
            f"### {index}. `{issue.code}`\n\n"
            f"- Severity: `{issue.severity}`\n"
            f"{optional_lines}"
            f"- Detail: {issue.detail}\n"
        )
    return "\n".join(sections)
