from __future__ import annotations

import hashlib
import importlib
import json
import math
import re
import subprocess
import wave
from importlib.util import find_spec
from pathlib import Path
from shutil import which

from artist_portrait_editor.media.probe import ProbeError, probe_media
from artist_portrait_editor.media.scanner import hash_file, read_sources_jsonl
from artist_portrait_editor.models.bgm import (
    BgmAnalysisReport,
    BgmBeatEngineCapability,
    BgmBeatEvent,
    BgmBeatGrid,
    BgmCandidate,
    BgmCandidateAnalysis,
    BgmCandidateLedger,
    BgmDuckingInterval,
    BgmEnergyWindow,
    BgmFitControls,
    BgmFitPlan,
    BgmFitSegment,
    BgmInputMode,
    BgmRhythmCandidateInsight,
    BgmRhythmIntelligenceReport,
)
from artist_portrait_editor.models.source import MediaKind, RightsStatus
from artist_portrait_editor.models.timeline import MusicSlotStatus, TimelineDraft


class BgmError(ValueError):
    pass


BEAT_ENGINE_PACKAGES = ("librosa", "aubio", "essentia", "madmom")
EXECUTABLE_BEAT_ENGINES = ("librosa",)


def load_ledger(path: Path, project_id: str) -> BgmCandidateLedger:
    if not path.exists():
        return BgmCandidateLedger(project_id=project_id)
    try:
        ledger = BgmCandidateLedger.model_validate_json(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise BgmError(f"invalid BgmCandidateLedger JSON: {exc}") from exc
    if ledger.project_id != project_id:
        raise BgmError("BGM candidate ledger project_id mismatch")
    return ledger


def import_candidate(
    *,
    root: Path,
    project_id: str,
    file_ref: str | None,
    source_id: str | None,
    extract_in: float,
    extract_out: float | None,
    stream_index: int,
    rights_status: RightsStatus,
    user_intent: str,
) -> tuple[BgmCandidateLedger, BgmCandidate]:
    if which("ffmpeg") is None or which("ffprobe") is None:
        raise BgmError("BGM import requires ffmpeg and ffprobe")
    if bool(file_ref) == bool(source_id):
        raise BgmError("provide exactly one of --file or --source-id")
    input_mode: BgmInputMode
    source_ref: str
    if source_id:
        sources_path = root / ".artist-portrait" / "data" / "sources.jsonl"
        if not sources_path.exists():
            raise BgmError("--source-id requires canonical sources.jsonl")
        source = next(
            (item for item in read_sources_jsonl(sources_path) if item.source_id == source_id),
            None,
        )
        if source is None:
            raise BgmError(f"unknown source_id: {source_id}")
        if source.forbidden_by_user:
            raise BgmError(f"source is forbidden by user: {source_id}")
        source_ref = source.primary_location
        input_path = (root / source_ref).resolve()
        input_mode = BgmInputMode.source_embedded_audio
        rights_status = RightsStatus(source.rights_status.value)
    else:
        source_ref = str(file_ref).replace("\\", "/")
        input_path = (root / source_ref).resolve()
        try:
            input_path.relative_to(root.resolve())
        except ValueError as exc:
            raise BgmError("BGM input must be inside the project") from exc
    if not input_path.is_file():
        raise BgmError(f"BGM input file does not exist: {source_ref}")
    try:
        media_kind, media_probe = probe_media(input_path)
    except ProbeError as exc:
        raise BgmError(str(exc)) from exc
    if not media_probe.audio_present:
        raise BgmError("BGM input has no audio stream")
    if not source_id:
        input_mode = (
            BgmInputMode.direct_audio
            if media_kind == MediaKind.audio
            else BgmInputMode.video_audio_extract
        )
    end = media_probe.duration if extract_out is None else extract_out
    if extract_in < 0 or end <= extract_in or end > media_probe.duration + 0.001:
        raise BgmError("invalid BGM extraction range")
    source_hash = hash_file(input_path)
    identity = (
        f"{source_hash}:{input_mode.value}:{extract_in:.3f}:{end:.3f}:{stream_index}"
    )
    candidate_id = "bgm_" + hashlib.sha256(identity.encode()).hexdigest()[:20]
    cache_ref = f".artist-portrait/cache/bgm/{candidate_id}.wav"
    cache_path = root / cache_ref
    extract_audio(
        input_path=input_path,
        output_path=cache_path,
        extract_in=extract_in,
        extract_out=end,
        stream_index=stream_index,
    )
    _, cache_probe = probe_media(cache_path)
    loudness = integrated_loudness(cache_path)
    candidate = BgmCandidate(
        music_candidate_id=candidate_id,
        input_mode=input_mode,
        source_ref=source_ref if not source_id else f"source_id:{source_id}",
        source_media_kind=media_kind.value,
        extract_in=round(extract_in, 3),
        extract_out=round(end, 3),
        audio_stream_index=stream_index,
        content_hash=source_hash,
        cache_ref=cache_ref,
        duration=round(cache_probe.duration, 3),
        rights_status=rights_status,
        user_intent=user_intent,
        analysis_status="technical_only",
        integrated_loudness_lufs=loudness,
        bpm=None,
        beat_analysis_status="unavailable",
        beat_analysis_reason="no mature local beat-analysis engine is installed",
        beat_grid_ref=None,
        beat_grid_fingerprint=None,
        mixed_audio=media_kind == MediaKind.video,
    )
    ledger_path = root / ".artist-portrait" / "data" / "bgm_candidates.json"
    ledger = load_ledger(ledger_path, project_id)
    by_id = {item.music_candidate_id: item for item in ledger.candidates}
    by_id[candidate_id] = candidate
    ledger = BgmCandidateLedger(
        project_id=project_id,
        candidates=[by_id[key] for key in sorted(by_id)],
    )
    atomic_json(ledger_path, ledger.model_dump(mode="json"))
    return ledger, candidate


def build_fit_plan(
    *,
    root: Path,
    project_id: str,
    candidate_id: str,
    requested_fit_mode: str = "auto",
    fade_in_seconds: float | None = None,
    fade_out_seconds: float | None = None,
    target_gain_db: float | None = None,
    ducking_gain_db: float = -9.0,
    ducking_enabled: bool = True,
    beat_alignment_requested: bool = False,
) -> tuple[BgmFitPlan, TimelineDraft]:
    if requested_fit_mode not in {"auto", "single_pass", "trim", "loop"}:
        raise BgmError("BGM fit mode must be auto, single_pass, trim, or loop")
    if ducking_gain_db > 0:
        raise BgmError("BGM ducking gain must be 0 dB or lower")
    ledger = load_ledger(
        root / ".artist-portrait" / "data" / "bgm_candidates.json",
        project_id,
    )
    candidate = next(
        (item for item in ledger.candidates if item.music_candidate_id == candidate_id),
        None,
    )
    if candidate is None:
        raise BgmError(f"unknown BGM candidate: {candidate_id}")
    timeline_path = root / "output" / "timeline_draft.json"
    if not timeline_path.exists():
        raise BgmError("BGM fitting requires output/timeline_draft.json")
    timeline = TimelineDraft.model_validate_json(timeline_path.read_text(encoding="utf-8"))
    target = timeline.actual_duration
    duration = candidate.duration
    default_fit_mode = "single_pass" if abs(duration - target) <= 0.001 else "trim" if duration > target else "loop"
    fit_mode = default_fit_mode if requested_fit_mode == "auto" else requested_fit_mode
    if fit_mode in {"single_pass", "trim"} and duration < target - 0.001:
        raise BgmError(f"BGM fit mode {fit_mode} requires candidate duration to cover the timeline")
    segments: list[BgmFitSegment] = []
    cursor = 0.0
    loop_index = 0
    while cursor < target - 0.001:
        length = min(duration, target - cursor)
        segments.append(
            BgmFitSegment(
                timeline_start=round(cursor, 3),
                timeline_end=round(cursor + length, 3),
                source_in=0.0,
                source_out=round(length, 3),
                loop_index=loop_index,
            )
        )
        cursor += length
        loop_index += 1
        if fit_mode in {"single_pass", "trim"}:
            break
    ducking = [
        BgmDuckingInterval(
            start=segment.timeline_start,
            end=segment.timeline_end,
            gain_db=ducking_gain_db,
            reason="preserve original audio, dialogue, or performance sound",
        )
        for segment in timeline.segments
        if ducking_enabled and segment.media_role.value in {"audio", "both"}
    ]
    analysis_report = load_analysis_report(
        root / ".artist-portrait" / "data" / "bgm_analysis.json",
        project_id,
    )
    candidate_analysis = None
    analysis_fingerprint = None
    analysis_ref = None
    beat_grid_ref = None
    beat_grid_fingerprint = None
    beat_alignment_status = "unavailable"
    beat_evidence_status = "unavailable"
    if analysis_report is not None:
        candidate_analysis = next(
            (
                item
                for item in analysis_report.candidates
                if item.music_candidate_id == candidate_id
            ),
            None,
        )
        if candidate_analysis is not None:
            analysis_ref = ".artist-portrait/data/bgm_analysis.json"
            analysis_fingerprint = "sha256:" + hashlib.sha256(
                (root / analysis_ref).read_bytes()
            ).hexdigest()
            if (
                candidate_analysis.beat_analysis_status == "completed"
                and candidate_analysis.beat_grid_ref
                and candidate_analysis.beat_grid_fingerprint
            ):
                beat_grid_ref = candidate_analysis.beat_grid_ref
                beat_grid_fingerprint = candidate_analysis.beat_grid_fingerprint
                beat_alignment_status = "completed"
                beat_evidence_status = "bound"
    timeline_fingerprint = "sha256:" + hashlib.sha256(timeline_path.read_bytes()).hexdigest()
    default_gain = -3.0 if candidate.integrated_loudness_lufs is None else round(
        min(0.0, -16.0 - candidate.integrated_loudness_lufs), 2
    )
    actual_fade_in = min(0.5, target / 4) if fade_in_seconds is None else fade_in_seconds
    actual_fade_out = min(1.0, target / 4) if fade_out_seconds is None else fade_out_seconds
    actual_target_gain = default_gain if target_gain_db is None else target_gain_db
    if actual_fade_in + actual_fade_out > target:
        raise BgmError("BGM fade-in plus fade-out must not exceed timeline duration")
    control_policy = "default_v1" if (
        requested_fit_mode == "auto"
        and fade_in_seconds is None
        and fade_out_seconds is None
        and target_gain_db is None
        and ducking_gain_db == -9.0
        and ducking_enabled is True
        and beat_alignment_requested is False
    ) else "explicit_cli_v1"
    controls = BgmFitControls(
        control_policy=control_policy,
        requested_fit_mode=requested_fit_mode,
        fade_in_seconds=round(actual_fade_in, 3),
        fade_out_seconds=round(actual_fade_out, 3),
        target_gain_db=round(actual_target_gain, 2),
        ducking_enabled=ducking_enabled,
        ducking_gain_db=round(ducking_gain_db, 2),
        beat_alignment_requested=beat_alignment_requested,
    )
    fit_key = (
        f"{timeline.timeline_id}:{candidate_id}:{timeline_fingerprint}:"
        f"{controls.model_dump_json()}"
    )
    warnings = [candidate.beat_analysis_reason] if candidate.beat_analysis_reason else []
    if candidate_analysis is None:
        warnings.append("BGM analysis report is missing or does not include this candidate")
    if beat_alignment_requested and beat_grid_ref is None:
        warnings.append("Beat alignment was requested but no validated beat grid is available")
    plan = BgmFitPlan(
        fit_id="bgmfit_" + hashlib.sha256(fit_key.encode()).hexdigest()[:20],
        project_id=project_id,
        timeline_id=timeline.timeline_id,
        timeline_fingerprint=timeline_fingerprint,
        music_candidate_id=candidate_id,
        candidate_content_hash=candidate.content_hash,
        target_duration=target,
        fit_mode=fit_mode,
        segments=segments,
        fade_in_seconds=controls.fade_in_seconds,
        fade_out_seconds=controls.fade_out_seconds,
        ducking_intervals=ducking,
        target_gain_db=controls.target_gain_db,
        controls=controls,
        beat_alignment_status=beat_alignment_status,
        beat_grid_ref=beat_grid_ref,
        beat_grid_fingerprint=beat_grid_fingerprint,
        beat_evidence_status=beat_evidence_status,
        analysis_ref=analysis_ref,
        analysis_fingerprint=analysis_fingerprint,
        energy_alignment_status="analysis_used" if candidate_analysis is not None else "unavailable",
        warnings=warnings,
    )
    fit_path = root / ".artist-portrait" / "data" / "bgm_fit.json"
    atomic_json(fit_path, plan.model_dump(mode="json"))
    timeline.music_plan.status = MusicSlotStatus.fitted
    timeline.music_plan.input_mode = candidate.input_mode.value
    timeline.music_plan.candidate_id = candidate_id
    timeline.music_plan.selection_performed = True
    timeline.music_plan.beat_analysis_performed = False
    timeline.music_plan.fitting_performed = True
    timeline.music_plan.fit_ref = fit_path.relative_to(root).as_posix()
    atomic_json(timeline_path, timeline.model_dump(mode="json"))
    plan.timeline_fingerprint = "sha256:" + hashlib.sha256(
        timeline_path.read_bytes()
    ).hexdigest()
    atomic_json(fit_path, plan.model_dump(mode="json"))
    return plan, timeline


def analyze_candidates(
    *,
    root: Path,
    project_id: str,
    window_seconds: float = 0.5,
) -> BgmAnalysisReport:
    if window_seconds <= 0 or window_seconds > 10:
        raise BgmError("BGM analysis window_seconds must be between 0 and 10")
    ledger_path = root / ".artist-portrait" / "data" / "bgm_candidates.json"
    ledger = load_ledger(ledger_path, project_id)
    if not ledger.candidates:
        raise BgmError("BGM analysis requires at least one candidate")
    beat_capabilities = detect_beat_engine_capabilities()
    beat_engine, beat_reason = selected_beat_engine(beat_capabilities)
    analyses = [
        analyze_candidate_audio(
            root=root,
            project_id=project_id,
            candidate=candidate,
            window_seconds=window_seconds,
            beat_engine=beat_engine,
            beat_reason=beat_reason,
            beat_capabilities=beat_capabilities,
        )
        for candidate in ledger.candidates
    ]
    report = BgmAnalysisReport(
        project_id=project_id,
        source_ledger_fingerprint="sha256:" + hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
        analysis_engine="local_pcm_energy_v1",
        beat_engine_capabilities=beat_capabilities,
        candidates=analyses,
    )
    analysis_path = root / ".artist-portrait" / "data" / "bgm_analysis.json"
    atomic_json(analysis_path, report.model_dump(mode="json"))
    analysis_fingerprint = "sha256:" + hashlib.sha256(analysis_path.read_bytes()).hexdigest()
    by_id = {candidate.music_candidate_id: candidate for candidate in ledger.candidates}
    for analysis in analyses:
        candidate = by_id[analysis.music_candidate_id]
        by_id[analysis.music_candidate_id] = candidate.model_copy(
            update={
                "analysis_status": "technical_only",
                "analysis_ref": analysis_path.relative_to(root).as_posix(),
                "analysis_fingerprint": analysis_fingerprint,
                "beat_analysis_status": analysis.beat_analysis_status,
                "beat_analysis_reason": analysis.beat_analysis_reason,
                "bpm": analysis.bpm,
                "beat_grid_ref": analysis.beat_grid_ref,
                "beat_grid_fingerprint": analysis.beat_grid_fingerprint,
            }
        )
    updated = BgmCandidateLedger(
        project_id=project_id,
        candidates=[by_id[key] for key in sorted(by_id)],
    )
    atomic_json(ledger_path, updated.model_dump(mode="json"))
    return report


def load_analysis_report(path: Path, project_id: str) -> BgmAnalysisReport | None:
    if not path.exists():
        return None
    try:
        report = BgmAnalysisReport.model_validate_json(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise BgmError(f"invalid BgmAnalysisReport JSON: {exc}") from exc
    if report.project_id != project_id:
        raise BgmError("BGM analysis report project_id mismatch")
    return report


def build_bgm_rhythm_intelligence(
    *,
    root: Path,
    project_id: str,
) -> tuple[Path, Path, Path, BgmRhythmIntelligenceReport]:
    ledger_path = root / ".artist-portrait" / "data" / "bgm_candidates.json"
    analysis_path = root / ".artist-portrait" / "data" / "bgm_analysis.json"
    ledger = load_ledger(ledger_path, project_id)
    if not ledger.candidates:
        raise BgmError("BGM rhythm intelligence requires at least one candidate")
    analysis = load_analysis_report(analysis_path, project_id)
    if analysis is None:
        raise BgmError("BGM rhythm intelligence requires .artist-portrait/data/bgm_analysis.json; run bgm analyze first")
    analysis_by_id = {item.music_candidate_id: item for item in analysis.candidates}
    insights = [
        build_bgm_rhythm_candidate_insight(candidate, analysis_by_id.get(candidate.music_candidate_id))
        for candidate in ledger.candidates
    ]
    missing_analysis = [item.music_candidate_id for item in ledger.candidates if item.music_candidate_id not in analysis_by_id]
    for insight in insights:
        if insight.music_candidate_id in missing_analysis:
            insight.warnings.append("candidate is missing from current BGM analysis report")
            insight.next_actions.append("Run bgm analyze again before relying on rhythm intelligence.")
    usable = sum(item.beat_quality_status in {"usable", "strong"} for item in insights)
    beat_completed = sum(item.beat_analysis_status == "completed" for item in insights)
    mixed = sum(item.mixed_audio for item in insights)
    warnings = sum(1 for item in insights if item.warnings or item.next_actions)
    status = "warning" if warnings or usable == 0 else "passed"
    key = (
        f"{project_id}:{hash_file(ledger_path)}:{hash_file(analysis_path)}:"
        f"{beat_completed}:{usable}:{mixed}:{warnings}"
    )
    report = BgmRhythmIntelligenceReport(
        bgm_rhythm_intelligence_id="bgm_rhythm_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=project_id,
        candidate_ledger_fingerprint=hash_file(ledger_path),
        bgm_analysis_fingerprint=hash_file(analysis_path),
        candidate_count=len(insights),
        beat_completed_count=beat_completed,
        usable_beat_candidate_count=usable,
        mixed_audio_candidate_count=mixed,
        source_modes_present=sorted({item.input_mode for item in ledger.candidates}, key=lambda value: value.value),
        status=status,
        summary=bgm_rhythm_summary(insights, usable, mixed),
        candidates=insights,
    )
    json_path = root / ".artist-portrait" / "data" / "bgm_rhythm_intelligence.json"
    md_path = root / "output" / "bgm_rhythm_intelligence.md"
    handoff_path = root / "output" / "bgm_rhythm_handoff.json"
    atomic_json(json_path, report.model_dump(mode="json"))
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_bgm_rhythm_intelligence(report) + "\n", encoding="utf-8")
    atomic_json(handoff_path, bgm_rhythm_handoff(report))
    return json_path, md_path, handoff_path, report


def build_bgm_rhythm_candidate_insight(
    candidate: BgmCandidate,
    analysis: BgmCandidateAnalysis | None,
) -> BgmRhythmCandidateInsight:
    warnings: list[str] = []
    next_actions: list[str] = []
    if analysis is None:
        return BgmRhythmCandidateInsight(
            music_candidate_id=candidate.music_candidate_id,
            input_mode=candidate.input_mode,
            source_ref=candidate.source_ref,
            mixed_audio=candidate.mixed_audio,
            beat_analysis_status="unavailable",
            bpm=None,
            beat_count=0,
            tempo_confidence=None,
            beat_quality_status="unavailable",
            beat_quality_score=0.0,
            phrase_hint_status="unavailable",
            source_risk_status=source_rhythm_risk(candidate),
            warnings=["candidate has no current BGM analysis evidence"],
            next_actions=["Run bgm analyze before rhythm intelligence review."],
        )
    beat_quality, score = beat_quality_from_analysis(analysis)
    bar_seconds = None
    phrase_seconds = None
    phrase_status = "unavailable"
    if analysis.bpm:
        bar_seconds = round((60.0 / analysis.bpm) * 4, 3)
        phrase_seconds = round(bar_seconds * 4, 3)
        phrase_status = "estimated"
    if analysis.beat_analysis_status != "completed":
        warnings.append(analysis.beat_analysis_reason or "validated beat-grid evidence is unavailable")
        next_actions.append("Install/use a validated local beat engine, then rerun bgm analyze.")
    if candidate.mixed_audio:
        warnings.append("candidate audio is a video or source mix and may contain speech, effects, or environment sound")
        next_actions.append("Use direct clean audio or explicit separation evidence before treating this as clean BGM.")
    if beat_quality == "weak":
        warnings.append("validated beat grid exists but beat confidence/count is weak")
        next_actions.append("Review beat grid manually before using it for cut/cue decisions.")
    return BgmRhythmCandidateInsight(
        music_candidate_id=candidate.music_candidate_id,
        input_mode=candidate.input_mode,
        source_ref=candidate.source_ref,
        mixed_audio=candidate.mixed_audio,
        beat_analysis_status=analysis.beat_analysis_status,
        bpm=analysis.bpm,
        beat_count=analysis.beat_count,
        beat_grid_ref=analysis.beat_grid_ref,
        beat_grid_fingerprint=analysis.beat_grid_fingerprint,
        tempo_confidence=analysis.tempo_confidence,
        beat_quality_status=beat_quality,
        beat_quality_score=score,
        phrase_hint_status=phrase_status,
        estimated_bar_seconds=bar_seconds,
        estimated_phrase_seconds=phrase_seconds,
        source_risk_status=source_rhythm_risk(candidate),
        warnings=warnings,
        next_actions=next_actions,
    )


def beat_quality_from_analysis(analysis: BgmCandidateAnalysis) -> tuple[str, float]:
    if analysis.beat_analysis_status != "completed" or analysis.bpm is None:
        return "unavailable", 0.0
    confidence = analysis.tempo_confidence or 0.0
    count_score = min(1.0, analysis.beat_count / 8)
    score = round(confidence * count_score, 3)
    if score >= 0.75:
        return "strong", score
    if score >= 0.5:
        return "usable", score
    return "weak", score


def source_rhythm_risk(candidate: BgmCandidate) -> str:
    if candidate.mixed_audio:
        return "high"
    if candidate.input_mode == BgmInputMode.source_embedded_audio:
        return "medium"
    return "low"


def bgm_rhythm_summary(
    insights: list[BgmRhythmCandidateInsight],
    usable_count: int,
    mixed_count: int,
) -> str:
    if usable_count == 0:
        return "No candidate has usable validated beat evidence; rhythm planning must stay conservative."
    if mixed_count:
        return "Usable beat evidence exists, but mixed-audio candidates require provenance caution."
    return "Usable local beat evidence is available for rhythm review without automatic edit mutation."


def render_bgm_rhythm_intelligence(report: BgmRhythmIntelligenceReport) -> str:
    lines = [
        "# BGM Rhythm Intelligence Report",
        "",
        "This report reviews local BGM rhythm evidence for editing decisions. It does not select music, move edit points, render media, call models, access the network, or fabricate BPM.",
        "",
        f"- Status: `{report.status}`",
        f"- Summary: {report.summary}",
        f"- Candidates: `{report.candidate_count}`",
        f"- Beat completed: `{report.beat_completed_count}`",
        f"- Usable beat candidates: `{report.usable_beat_candidate_count}`",
        f"- Mixed-audio candidates: `{report.mixed_audio_candidate_count}`",
        "",
    ]
    for candidate in report.candidates:
        lines.extend(
            [
                f"## `{candidate.music_candidate_id}`",
                "",
                f"- Input mode: `{candidate.input_mode.value}`",
                f"- Source risk: `{candidate.source_risk_status}`",
                f"- Beat status: `{candidate.beat_analysis_status}`",
                f"- Beat quality: `{candidate.beat_quality_status}` / `{candidate.beat_quality_score}`",
                f"- BPM: `{candidate.bpm}`",
                f"- Beat count: `{candidate.beat_count}`",
                f"- Bar seconds: `{candidate.estimated_bar_seconds}`",
                f"- Phrase seconds: `{candidate.estimated_phrase_seconds}`",
                f"- Beat grid: `{candidate.beat_grid_ref or 'None'}`",
            ]
        )
        for warning in candidate.warnings:
            lines.append(f"- Warning: {warning}")
        for action in candidate.next_actions:
            lines.append(f"- Next action: {action}")
        lines.append("")
    return "\n".join(lines)


def bgm_rhythm_handoff(report: BgmRhythmIntelligenceReport) -> dict:
    return {
        "schema_version": report.schema_version,
        "handoff_id": f"bgm_rhythm_handoff_{report.bgm_rhythm_intelligence_id}",
        "project_id": report.project_id,
        "bgm_rhythm_intelligence_id": report.bgm_rhythm_intelligence_id,
        "status": report.status,
        "summary": report.summary,
        "task": "Review BGM rhythm evidence and propose textual editing guidance only.",
        "forbidden": [
            "do not select music",
            "do not move edit points",
            "do not render media",
            "do not fabricate BPM or beat grids",
            "do not call models from the CLI",
            "do not access the network",
        ],
    }


def analyze_candidate_audio(
    *,
    root: Path,
    project_id: str,
    candidate: BgmCandidate,
    window_seconds: float,
    beat_engine: str,
    beat_reason: str | None,
    beat_capabilities: list[BgmBeatEngineCapability],
) -> BgmCandidateAnalysis:
    cache_path = root / candidate.cache_ref
    if not cache_path.exists():
        raise BgmError(f"BGM candidate cache audio is missing: {candidate.cache_ref}")
    windows = pcm_energy_windows(cache_path, window_seconds=window_seconds)
    if not windows:
        raise BgmError(f"BGM candidate has no analyzable audio frames: {candidate.music_candidate_id}")
    rms_values = [db_to_linear(item.rms_dbfs) for item in windows]
    average_rms = linear_to_db(sum(rms_values) / len(rms_values))
    max_peak = max(item.peak_dbfs for item in windows)
    quiet_head = 0.0
    for item in windows:
        if item.energy_label != "quiet":
            break
        quiet_head = item.end
    quiet_tail = 0.0
    for item in reversed(windows):
        if item.energy_label != "quiet":
            break
        quiet_tail = round(candidate.duration - item.start, 3)
    high_windows = [item for item in windows if item.energy_label == "high"]
    high_start = high_windows[0].start if high_windows else None
    high_end = high_windows[-1].end if high_windows else None
    warnings = []
    if candidate.mixed_audio:
        warnings.append("candidate was extracted from video and may contain speech, effects, or environment audio")
    beat_grid = run_beat_engine_if_available(
        root=root,
        project_id=project_id,
        candidate=candidate,
        cache_path=cache_path,
        beat_engine=beat_engine,
        capabilities=beat_capabilities,
    )
    beat_grid_ref = None
    beat_grid_fingerprint = None
    bpm = None
    beat_status = "unavailable"
    tempo_confidence = None
    beat_count = 0
    effective_beat_reason = beat_reason
    if beat_grid is not None:
        beat_grid_ref = f".artist-portrait/data/bgm_beat_grids/{candidate.music_candidate_id}.json"
        beat_grid_path = root / beat_grid_ref
        atomic_json(beat_grid_path, beat_grid.model_dump(mode="json"))
        beat_grid_fingerprint = "sha256:" + hashlib.sha256(beat_grid_path.read_bytes()).hexdigest()
        bpm = beat_grid.bpm
        beat_status = "completed"
        tempo_confidence = beat_grid.tempo_confidence
        beat_count = beat_grid.beat_count
        effective_beat_reason = None
    elif beat_reason:
        warnings.append(beat_reason)
    return BgmCandidateAnalysis(
        music_candidate_id=candidate.music_candidate_id,
        cache_ref=candidate.cache_ref,
        cache_fingerprint=hash_file(cache_path),
        duration=candidate.duration,
        analysis_engine="local_pcm_energy_v1",
        beat_engine=beat_engine,
        beat_analysis_status=beat_status,
        beat_analysis_reason=effective_beat_reason,
        bpm=bpm,
        beat_grid_ref=beat_grid_ref,
        beat_grid_fingerprint=beat_grid_fingerprint,
        tempo_confidence=tempo_confidence,
        beat_count=beat_count,
        window_seconds=round(window_seconds, 3),
        window_count=len(windows),
        average_rms_dbfs=round(average_rms, 3),
        max_peak_dbfs=round(max_peak, 3),
        quiet_head_seconds=round(quiet_head, 3),
        quiet_tail_seconds=round(quiet_tail, 3),
        high_energy_start=high_start,
        high_energy_end=high_end,
        recommended_loop_safe=quiet_tail <= window_seconds and len(windows) > 1,
        warnings=warnings,
        windows=windows,
    )


def pcm_energy_windows(path: Path, *, window_seconds: float) -> list[BgmEnergyWindow]:
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        sample_width = handle.getsampwidth()
        frame_rate = handle.getframerate()
        frame_count = handle.getnframes()
        if sample_width != 2:
            raise BgmError("BGM analysis expects 16-bit PCM cache audio")
        frames_per_window = max(1, int(frame_rate * window_seconds))
        windows: list[BgmEnergyWindow] = []
        start_frame = 0
        while start_frame < frame_count:
            count = min(frames_per_window, frame_count - start_frame)
            raw = handle.readframes(count)
            sample_count = len(raw) // sample_width
            if sample_count == 0:
                break
            samples = [
                int.from_bytes(raw[index:index + sample_width], "little", signed=True) / 32768.0
                for index in range(0, len(raw), sample_width)
            ]
            mono = []
            for index in range(0, len(samples), channels):
                mono.append(sum(samples[index:index + channels]) / channels)
            rms = math.sqrt(sum(sample * sample for sample in mono) / len(mono))
            peak = max(abs(sample) for sample in mono)
            rms_db = linear_to_db(rms)
            peak_db = linear_to_db(peak)
            start = start_frame / frame_rate
            end = (start_frame + count) / frame_rate
            windows.append(
                BgmEnergyWindow(
                    start=round(start, 3),
                    end=round(end, 3),
                    rms_dbfs=round(rms_db, 3),
                    peak_dbfs=round(peak_db, 3),
                    energy_label=energy_label(rms_db),
                )
            )
            start_frame += count
    return windows


def detect_beat_engine_capabilities() -> list[BgmBeatEngineCapability]:
    capabilities: list[BgmBeatEngineCapability] = []
    for name in BEAT_ENGINE_PACKAGES:
        available = find_spec(name) is not None
        execution_supported = name in EXECUTABLE_BEAT_ENGINES
        if available and execution_supported:
            status = "available"
            reason = None
        elif available:
            status = "unsupported"
            reason = "package detected but no validated local adapter is implemented"
        else:
            status = "unavailable"
            reason = "package is not installed"
        capabilities.append(
            BgmBeatEngineCapability(
                engine=name,
                package_available=available,
                execution_supported=available and execution_supported,
                status=status,
                reason=reason,
            )
        )
    return capabilities


def selected_beat_engine(
    capabilities: list[BgmBeatEngineCapability],
) -> tuple[str, str | None]:
    executable = [item.engine for item in capabilities if item.status == "available"]
    if executable:
        return executable[0], None
    available = [item.engine for item in capabilities if item.package_available]
    if available:
        return ",".join(available), (
            "mature beat-analysis package detected but no validated executable adapter is available"
        )
    return (
        "none",
        "no mature local beat-analysis engine is installed; BPM and beat grid remain unavailable",
    )


def detect_beat_engine() -> tuple[str, str | None]:
    return selected_beat_engine(detect_beat_engine_capabilities())


def run_beat_engine_if_available(
    *,
    root: Path,
    project_id: str,
    candidate: BgmCandidate,
    cache_path: Path,
    beat_engine: str,
    capabilities: list[BgmBeatEngineCapability],
) -> BgmBeatGrid | None:
    selected = next(
        (item for item in capabilities if item.engine == beat_engine and item.status == "available"),
        None,
    )
    if selected is None:
        return None
    if beat_engine == "librosa":
        return analyze_beats_with_librosa(
            project_id=project_id,
            candidate=candidate,
            cache_path=cache_path,
        )
    return None


def analyze_beats_with_librosa(
    *,
    project_id: str,
    candidate: BgmCandidate,
    cache_path: Path,
) -> BgmBeatGrid | None:
    try:
        librosa = importlib.import_module("librosa")
    except Exception:
        return None
    try:
        samples, sample_rate = librosa.load(str(cache_path), sr=None, mono=True)
        tempo, beat_frames = librosa.beat.beat_track(y=samples, sr=sample_rate)
        beat_times = librosa.frames_to_time(beat_frames, sr=sample_rate)
    except Exception:
        return None
    bpm = float(tempo[0] if hasattr(tempo, "__len__") else tempo)
    times = [float(value) for value in beat_times]
    if bpm <= 0 or len(times) < 2:
        return None
    events = [
        BgmBeatEvent(index=index, time=round(value, 3), confidence=0.8)
        for index, value in enumerate(times)
    ]
    return BgmBeatGrid(
        project_id=project_id,
        music_candidate_id=candidate.music_candidate_id,
        cache_ref=candidate.cache_ref,
        cache_fingerprint=hash_file(cache_path),
        beat_engine="librosa",
        bpm=round(bpm, 3),
        tempo_confidence=0.8,
        beat_count=len(events),
        beat_times=events,
    )


def render_bgm_analysis_report(report: BgmAnalysisReport) -> str:
    lines = [
        "# BGM Analysis Report",
        "",
        "This deterministic report analyzes local cached BGM candidates.",
        "It does not recommend music, select candidates, fabricate BPM, call models, or access the network.",
        "",
        "## Summary",
        "",
        f"- Project: `{report.project_id}`",
        f"- Source ledger: `{report.source_ledger_ref}`",
        f"- Analysis engine: `{report.analysis_engine}`",
        f"- Candidates: `{len(report.candidates)}`",
        "",
    ]
    for candidate in report.candidates:
        lines.extend(
            [
                f"## `{candidate.music_candidate_id}`",
                "",
                f"- Cache: `{candidate.cache_ref}`",
                f"- Duration: `{candidate.duration:.3f}s`",
                f"- Average RMS: `{candidate.average_rms_dbfs:.3f} dBFS`",
                f"- Max peak: `{candidate.max_peak_dbfs:.3f} dBFS`",
                f"- Quiet head: `{candidate.quiet_head_seconds:.3f}s`",
                f"- Quiet tail: `{candidate.quiet_tail_seconds:.3f}s`",
                f"- High energy range: `{candidate.high_energy_start}` to `{candidate.high_energy_end}`",
                f"- Loop-safe technical hint: `{str(candidate.recommended_loop_safe).lower()}`",
                f"- Beat engine: `{candidate.beat_engine}`",
                f"- Beat status: `{candidate.beat_analysis_status}`",
                f"- Beat reason: {candidate.beat_analysis_reason or 'None'}",
                f"- BPM: `{candidate.bpm}`",
                f"- Beat grid: `{candidate.beat_grid_ref or 'None'}`",
                f"- Beat count: `{candidate.beat_count}`",
                f"- Warnings: `{len(candidate.warnings)}`",
                "",
            ]
        )
    return "\n".join(lines)


def bgm_analysis_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        report = BgmAnalysisReport.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": f"invalid BgmAnalysisReport JSON: {exc}",
        }
    return {
        "exists": True,
        "valid": True,
        "candidate_count": len(report.candidates),
        "analysis_engine": report.analysis_engine,
        "beat_engine_capabilities": [
            item.model_dump(mode="json") for item in report.beat_engine_capabilities
        ],
        "beat_completed_count": sum(
            item.beat_analysis_status == "completed" for item in report.candidates
        ),
        "bpm_candidate_count": sum(item.bpm is not None for item in report.candidates),
        "network_performed": report.network_performed,
        "model_call_performed": report.model_call_performed,
        "automatic_music_selection": report.automatic_music_selection,
    }


def db_to_linear(value: float) -> float:
    return 10 ** (value / 20)


def linear_to_db(value: float) -> float:
    if value <= 0:
        return -120.0
    return 20 * math.log10(value)


def energy_label(rms_dbfs: float) -> str:
    if rms_dbfs <= -55:
        return "quiet"
    if rms_dbfs <= -35:
        return "low"
    if rms_dbfs <= -20:
        return "medium"
    return "high"


def review_bgm(root: Path, project_id: str) -> list[str]:
    issues: list[str] = []
    ledger = load_ledger(
        root / ".artist-portrait" / "data" / "bgm_candidates.json",
        project_id,
    )
    if not ledger.candidates:
        issues.append("no BGM candidates")
    fit_path = root / ".artist-portrait" / "data" / "bgm_fit.json"
    timeline_path = root / "output" / "timeline_draft.json"
    if not fit_path.exists():
        issues.append("no BGM fit plan")
        return issues
    try:
        plan = BgmFitPlan.model_validate_json(fit_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        issues.append(f"invalid BGM fit plan: {exc}")
        return issues
    candidate = next(
        (item for item in ledger.candidates if item.music_candidate_id == plan.music_candidate_id),
        None,
    )
    if candidate is None:
        issues.append("BGM fit references an unknown candidate")
    elif candidate.content_hash != plan.candidate_content_hash:
        issues.append("BGM fit candidate hash is stale")
    if not timeline_path.exists():
        issues.append("BGM fit timeline is missing")
        return issues
    timeline_hash = "sha256:" + hashlib.sha256(timeline_path.read_bytes()).hexdigest()
    if timeline_hash != plan.timeline_fingerprint:
        issues.append("BGM fit timeline fingerprint is stale")
    try:
        timeline = TimelineDraft.model_validate_json(timeline_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        issues.append(f"invalid fitted timeline: {exc}")
        return issues
    if timeline.timeline_id != plan.timeline_id:
        issues.append("BGM fit timeline_id mismatch")
    if timeline.music_plan.candidate_id != plan.music_candidate_id:
        issues.append("timeline music candidate does not match BGM fit")
    if timeline.music_plan.fit_ref != fit_path.relative_to(root).as_posix():
        issues.append("timeline music fit reference is missing or stale")
    if plan.beat_grid_ref:
        beat_grid_path = root / plan.beat_grid_ref
        if not beat_grid_path.exists():
            issues.append("BGM fit beat grid is missing")
        else:
            beat_grid_hash = "sha256:" + hashlib.sha256(beat_grid_path.read_bytes()).hexdigest()
            if beat_grid_hash != plan.beat_grid_fingerprint:
                issues.append("BGM fit beat grid fingerprint is stale")
    return issues


def extract_audio(
    *,
    input_path: Path,
    output_path: Path,
    extract_in: float,
    extract_out: float,
    stream_index: int,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-ss", f"{extract_in:.3f}", "-to", f"{extract_out:.3f}",
        "-i", str(input_path), "-map", f"0:a:{stream_index}",
        "-vn", "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    if result.returncode != 0 or not output_path.exists():
        raise BgmError((result.stderr or "ffmpeg audio extraction failed").strip())


def integrated_loudness(path: Path) -> float | None:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-filter_complex", "ebur128", "-f", "null", "-"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    matches = re.findall(r"I:\\s*(-?\\d+(?:\\.\\d+)?)\\s+LUFS", result.stderr)
    return float(matches[-1]) if matches else None


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
