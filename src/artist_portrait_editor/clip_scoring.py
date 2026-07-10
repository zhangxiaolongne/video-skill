from __future__ import annotations

import hashlib
import json
import math
import subprocess
from collections import defaultdict
from pathlib import Path

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.analysis import AnalysisRecord
from artist_portrait_editor.models.clip import ClipMethod, ClipRecord
from artist_portrait_editor.models.clip_score import (
    ClipAudioEnergy,
    ClipScoreComponent,
    ClipScoreRecord,
)
from artist_portrait_editor.models.edit_brief import EditBrief
from artist_portrait_editor.models.keyframe import KeyframeRecord
from artist_portrait_editor.models.source import MediaKind
from artist_portrait_editor.models.state import ActiveMode, OverallStatus, StepLedgerEntry, StepStatus
from artist_portrait_editor.models.transcript import TranscriptRecord
from artist_portrait_editor.run_records import environment_snapshot, new_run_id, write_json, utc_now
from artist_portrait_editor.workspace_errors import WorkspacePrerequisiteError
from artist_portrait_editor.workspace_records import (
    read_analysis_jsonl,
    read_clips_jsonl,
    read_keyframes_jsonl,
    read_transcripts_jsonl,
)
from artist_portrait_editor.workspace_state import (
    atomic_write_text,
    fingerprint_file,
    fingerprint_inputs,
    load_state,
    project_root,
    save_state,
    write_run_report,
)


class ClipScoringError(RuntimeError):
    pass


def score_workspace(project_path: Path) -> tuple[Path, Path, list[ClipScoreRecord], list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("score requires init to complete first")

    data_dir = root / WORKSPACE_DIR / DATA_DIR
    clips_path = data_dir / "clips.jsonl"
    if not clips_path.exists():
        raise WorkspacePrerequisiteError("score requires segment to complete first")

    brief_path = data_dir / "edit_brief.json"
    if not brief_path.exists():
        raise WorkspacePrerequisiteError("score requires brief to complete first")
    brief_step = state.steps.get("brief", StepLedgerEntry())
    if brief_step.status in {StepStatus.pending, StepStatus.invalidated}:
        raise WorkspacePrerequisiteError("score requires brief to be current first")

    clips = read_clips_jsonl(clips_path)
    transcripts_path = data_dir / "transcripts.jsonl"
    keyframes_path = data_dir / "keyframes.jsonl"
    analysis_path = data_dir / "analysis.jsonl"
    transcripts = read_transcripts_jsonl(transcripts_path) if transcripts_path.exists() else []
    keyframes = read_keyframes_jsonl(keyframes_path) if keyframes_path.exists() else []
    analyses = read_analysis_jsonl(analysis_path) if analysis_path.exists() else []
    try:
        brief = EditBrief.model_validate_json(brief_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise WorkspacePrerequisiteError(f"invalid EditBrief JSON: {exc}") from exc

    input_fingerprint = fingerprint_inputs(
        [
            ("project", project_path),
            ("clips", clips_path),
            ("transcripts", transcripts_path),
            ("keyframes", keyframes_path),
            ("analysis", analysis_path),
            ("brief", brief_path),
        ]
    )
    records, warnings = build_clip_scores(
        root=root,
        project_id=config.project.id,
        clips=clips,
        transcripts=transcripts,
        keyframes=keyframes,
        analyses=analyses,
        brief=brief,
        scoring_fingerprint=input_fingerprint,
    )

    jsonl_path = write_clip_scores_jsonl(root, records)
    report_path = root / config.paths.output_dir / "clip_score_report.md"
    atomic_write_text(
        report_path,
        render_clip_score_report(
            records=records,
            warnings=warnings,
            scores_ref=jsonl_path.relative_to(root).as_posix(),
            clips_ref=clips_path.relative_to(root).as_posix(),
            transcript_ref=transcripts_path.relative_to(root).as_posix()
            if transcripts_path.exists()
            else None,
            keyframe_ref=keyframes_path.relative_to(root).as_posix()
            if keyframes_path.exists()
            else None,
            analysis_ref=analysis_path.relative_to(root).as_posix()
            if analysis_path.exists()
            else None,
            brief_ref=brief_path.relative_to(root).as_posix(),
        )
        + "\n",
    )

    run_id = new_run_id()
    invalidated = invalidate_downstream_steps_for_scores(
        state,
        score_fingerprint=fingerprint_file(jsonl_path),
    )
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    state.steps["score"] = StepLedgerEntry(
        status=status,
        input_fingerprint=input_fingerprint,
        output_refs=[
            jsonl_path.relative_to(root).as_posix(),
            report_path.relative_to(root).as_posix(),
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
    write_json(runs_dir / "command.json", {"command": "score", "project": str(project_path)})
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "score",
            "status": status.value,
            "clip_scores": len(records),
            "output_refs": state.steps["score"].output_refs,
            "invalidated_steps": invalidated,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text("score completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(root / config.paths.output_dir, state, warnings)
    return jsonl_path, report_path, records, warnings


def build_clip_scores(
    *,
    root: Path,
    project_id: str,
    clips: list[ClipRecord],
    transcripts: list[TranscriptRecord],
    keyframes: list[KeyframeRecord],
    analyses: list[AnalysisRecord],
    brief: EditBrief,
    scoring_fingerprint: str,
) -> tuple[list[ClipScoreRecord], list[str]]:
    transcripts_by_source: dict[str, list[TranscriptRecord]] = defaultdict(list)
    for transcript in transcripts:
        transcripts_by_source[transcript.source_id].append(transcript)
    keyframes_by_clip: dict[str, list[KeyframeRecord]] = defaultdict(list)
    for keyframe in keyframes:
        keyframes_by_clip[keyframe.clip_id].append(keyframe)
    analyses_by_clip: dict[str, list[AnalysisRecord]] = defaultdict(list)
    for analysis in analyses:
        analyses_by_clip[analysis.clip_id].append(analysis)

    records: list[ClipScoreRecord] = []
    warnings: list[str] = []
    if not transcripts:
        warnings.append("transcript ledger is missing or empty; speech scoring uses zero transcript evidence")
    if not keyframes:
        warnings.append("keyframe ledger is missing or empty; visual/keyframe scoring is limited")
    if not analyses:
        warnings.append("analysis ledger is missing or empty; analysis confidence scoring is limited")

    for clip in sorted(clips, key=lambda item: (item.source_location, item.clip_index)):
        clip_transcripts = _overlapping_transcripts(
            transcripts_by_source.get(clip.source_id, []),
            clip.boundary.start_seconds,
            clip.boundary.end_seconds,
        )
        clip_keyframes = keyframes_by_clip.get(clip.clip_id, [])
        clip_analyses = analyses_by_clip.get(clip.clip_id, [])
        speech = _speech_score(clip, clip_transcripts)
        transcript_density = _transcript_density_score(clip, clip_transcripts)
        audio_energy = _audio_energy(root, clip)
        visual_change = _visual_change_score(clip)
        keyframe_coverage = _keyframe_coverage_score(clip, clip_keyframes)
        analysis_confidence = _analysis_confidence_score(clip_analyses)
        duration_fit = _duration_fit_score(clip, brief)
        source_penalty = _source_risk_penalty(clip, clip_analyses)
        overall = _overall_score(
            speech=speech.score,
            transcript_density=transcript_density.score,
            audio=audio_energy.score,
            visual=visual_change.score,
            keyframe=keyframe_coverage.score,
            analysis=analysis_confidence.score,
            duration=duration_fit.score,
            source_penalty=source_penalty,
        )
        tier, recommendation = _selection(overall)
        record_warnings = [
            component.detail
            for component in (speech, transcript_density, visual_change, keyframe_coverage, analysis_confidence, duration_fit)
            if component.status in {"missing", "failed"}
        ]
        if audio_energy.status in {"missing", "failed"}:
            record_warnings.append(audio_energy.detail)
        record = ClipScoreRecord(
            clip_score_id="clip_score_"
            + hashlib.sha256(f"{clip.clip_id}:{scoring_fingerprint}".encode()).hexdigest()[:20],
            project_id=project_id,
            clip_id=clip.clip_id,
            source_id=clip.source_id,
            source_location=clip.source_location,
            source_content_hash=clip.source_content_hash,
            clip_fingerprint=clip.source_fingerprint,
            scoring_fingerprint=scoring_fingerprint,
            media_kind=clip.media_kind,
            start_seconds=clip.boundary.start_seconds,
            end_seconds=clip.boundary.end_seconds,
            duration_seconds=clip.boundary.duration_seconds,
            evidence_level=_evidence_level(clip_transcripts, clip_keyframes, clip_analyses),
            speech_score=speech,
            transcript_density_score=transcript_density,
            audio_energy=audio_energy,
            visual_change_score=visual_change,
            keyframe_coverage_score=keyframe_coverage,
            analysis_confidence_score=analysis_confidence,
            duration_fit_score=duration_fit,
            source_risk_penalty=source_penalty,
            overall_score=overall,
            selection_tier=tier,
            keep_recommendation=recommendation,
            keyframe_cluster_id=_keyframe_cluster_id(root, clip_keyframes),
            transcript_refs=[item.transcript_id for item in clip_transcripts],
            keyframe_refs=[item.keyframe_id for item in clip_keyframes],
            analysis_refs=[item.analysis_id for item in clip_analyses],
            evidence=[
                {"type": "clip", "ref": clip.clip_id},
                *[{"type": "transcript", "ref": item.transcript_id} for item in clip_transcripts],
                *[{"type": "keyframe", "ref": item.keyframe_id} for item in clip_keyframes],
                *[{"type": "analysis", "ref": item.analysis_id} for item in clip_analyses],
                {"type": "edit_brief", "ref": brief.edit_brief_id},
            ],
            reasons=_reasons(
                overall=overall,
                speech=speech,
                transcript_density=transcript_density,
                audio=audio_energy,
                visual=visual_change,
                keyframe=keyframe_coverage,
                analysis=analysis_confidence,
                duration=duration_fit,
                source_penalty=source_penalty,
            ),
            warnings=record_warnings,
        )
        records.append(record)
    return records, warnings


def write_clip_scores_jsonl(root: Path, records: list[ClipScoreRecord]) -> Path:
    output = root / WORKSPACE_DIR / DATA_DIR / "clip_scores.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".jsonl.tmp")
    tmp.write_text(
        "".join(
            json.dumps(record.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) + "\n"
            for record in records
        ),
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def read_clip_scores_jsonl(path: Path) -> list[ClipScoreRecord]:
    scores: list[ClipScoreRecord] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            scores.append(ClipScoreRecord.model_validate_json(line))
        except ValueError as exc:
            raise WorkspacePrerequisiteError(
                f"invalid ClipScoreRecord JSONL at line {line_number}: {exc}"
            ) from exc
    return scores


def render_clip_score_report(
    *,
    records: list[ClipScoreRecord],
    warnings: list[str],
    scores_ref: str,
    clips_ref: str,
    transcript_ref: str | None,
    keyframe_ref: str | None,
    analysis_ref: str | None,
    brief_ref: str,
) -> str:
    sorted_records = sorted(records, key=lambda item: (-item.overall_score, item.source_location, item.start_seconds))
    warning_lines = "\n".join(f"- {item}" for item in warnings) or "- None"
    sections = [
        "# Clip Score Report",
        "",
        "This V1-02 report scores clips from local evidence only. It does not render media, mutate timelines, move edit points, select music, call models, use image generation, or access the network.",
        "",
        "## Inputs",
        "",
        f"- Scores: `{scores_ref}`",
        f"- Clips: `{clips_ref}`",
        f"- Brief: `{brief_ref}`",
        f"- Transcripts: `{transcript_ref or 'missing'}`",
        f"- Keyframes: `{keyframe_ref or 'missing'}`",
        f"- Analysis: `{analysis_ref or 'missing'}`",
        "",
        "## Warnings",
        "",
        warning_lines,
        "",
        "## Selection Map",
        "",
    ]
    if not sorted_records:
        sections.append("- No clips available.")
    for index, record in enumerate(sorted_records, start=1):
        reasons = "; ".join(record.reasons) or "no strong reason recorded"
        sections.extend(
            [
                f"### {index}. `{record.clip_id}`",
                "",
                f"- Overall score: `{record.overall_score:.3f}`",
                f"- Selection tier: `{record.selection_tier}`",
                f"- Keep recommendation: `{record.keep_recommendation}`",
                f"- Time range: `{record.start_seconds:.3f}`-`{record.end_seconds:.3f}` seconds",
                f"- Evidence level: `{record.evidence_level}`",
                f"- Speech score: `{record.speech_score.score:.3f}`",
                f"- Audio energy score: `{record.audio_energy.score:.3f}` ({record.audio_energy.status})",
                f"- Visual change score: `{record.visual_change_score.score:.3f}`",
                f"- Keyframe coverage score: `{record.keyframe_coverage_score.score:.3f}`",
                f"- Analysis confidence score: `{record.analysis_confidence_score.score:.3f}`",
                f"- Duration fit score: `{record.duration_fit_score.score:.3f}`",
                f"- Source risk penalty: `{record.source_risk_penalty:.3f}`",
                f"- Keyframe cluster: `{record.keyframe_cluster_id or 'none'}`",
                f"- Reasons: {reasons}",
                "",
            ]
        )
    return "\n".join(sections)


def invalidate_downstream_steps_for_scores(state, *, score_fingerprint: str) -> list[str]:
    invalidated: list[str] = []
    for step_name in (
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
        if entry.input_fingerprint == score_fingerprint:
            continue
        state.steps[step_name] = StepLedgerEntry(
            status=StepStatus.invalidated,
            input_fingerprint=entry.input_fingerprint,
            output_refs=entry.output_refs,
            last_run_id=entry.last_run_id,
            warnings=[
                *entry.warnings,
                "clip score ledger changed; rerun this step before trusting its output",
            ],
        )
        invalidated.append(step_name)
    return invalidated


def _overlapping_transcripts(
    transcripts: list[TranscriptRecord],
    start: float,
    end: float,
) -> list[TranscriptRecord]:
    return [
        item
        for item in transcripts
        if max(start, item.start_seconds) < min(end, item.end_seconds)
    ]


def _speech_score(clip: ClipRecord, transcripts: list[TranscriptRecord]) -> ClipScoreComponent:
    if not transcripts:
        return ClipScoreComponent(status="missing", score=0.0, detail="no overlapping transcript evidence")
    overlap = sum(
        max(0.0, min(clip.boundary.end_seconds, item.end_seconds) - max(clip.boundary.start_seconds, item.start_seconds))
        for item in transcripts
    )
    score = _clamp(overlap / max(clip.boundary.duration_seconds, 0.001))
    return ClipScoreComponent(status="available", score=round(score, 3), detail=f"{overlap:.3f}s transcript overlap")


def _transcript_density_score(clip: ClipRecord, transcripts: list[TranscriptRecord]) -> ClipScoreComponent:
    if not transcripts:
        return ClipScoreComponent(status="missing", score=0.0, detail="no transcript text density available")
    chars = sum(len(item.text.strip()) for item in transcripts)
    chars_per_second = chars / max(clip.boundary.duration_seconds, 0.001)
    score = _clamp(chars_per_second / 14.0)
    return ClipScoreComponent(status="available", score=round(score, 3), detail=f"{chars_per_second:.3f} chars/s")


def _audio_energy(root: Path, clip: ClipRecord) -> ClipAudioEnergy:
    if clip.media_kind == MediaKind.video:
        method = "ffmpeg_pcm_s16le_rms_v1"
    elif clip.media_kind == MediaKind.audio:
        method = "ffmpeg_pcm_s16le_rms_v1"
    else:
        return ClipAudioEnergy(status="not_applicable", rms=None, dbfs=None, score=0.0, method="not_applicable", detail="unsupported media kind")
    source_path = root / clip.source_location
    if not source_path.exists():
        return ClipAudioEnergy(status="missing", rms=None, dbfs=None, score=0.0, method=method, detail=f"source file missing: {clip.source_location}")
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{clip.boundary.start_seconds:.3f}",
        "-t",
        f"{clip.boundary.duration_seconds:.3f}",
        "-i",
        str(source_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "8000",
        "-f",
        "s16le",
        "pipe:1",
    ]
    try:
        completed = subprocess.run(command, check=False, capture_output=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ClipAudioEnergy(status="failed", rms=None, dbfs=None, score=0.0, method=method, detail=f"ffmpeg audio read failed: {exc}")
    if completed.returncode != 0 or not completed.stdout:
        return ClipAudioEnergy(status="failed", rms=None, dbfs=None, score=0.0, method=method, detail="ffmpeg returned no PCM audio")
    samples = memoryview(completed.stdout)
    count = len(samples) // 2
    if count <= 0:
        return ClipAudioEnergy(status="missing", rms=None, dbfs=None, score=0.0, method=method, detail="no PCM samples decoded")
    total = 0.0
    for index in range(0, count * 2, 2):
        sample = int.from_bytes(samples[index : index + 2], byteorder="little", signed=True)
        normalized = sample / 32768.0
        total += normalized * normalized
    rms = math.sqrt(total / count)
    if rms <= 0:
        return ClipAudioEnergy(status="available", rms=0.0, dbfs=None, score=0.0, method=method, detail="silent PCM audio")
    dbfs = 20.0 * math.log10(rms)
    score = _clamp((dbfs + 60.0) / 48.0)
    return ClipAudioEnergy(status="available", rms=round(rms, 6), dbfs=round(dbfs, 3), score=round(score, 3), method=method, detail=f"{dbfs:.3f} dBFS RMS")


def _visual_change_score(clip: ClipRecord) -> ClipScoreComponent:
    if clip.media_kind != MediaKind.video:
        return ClipScoreComponent(status="not_applicable", score=0.0, detail="audio-only clip")
    if clip.method == ClipMethod.pyscenedetect:
        score = clip.boundary_confidence
        detail = "scene-detection boundary evidence"
    else:
        score = clip.boundary_confidence * 0.25
        detail = "fixed-window boundary; no scene-change engine evidence"
    return ClipScoreComponent(status="available", score=round(_clamp(score), 3), detail=detail)


def _keyframe_coverage_score(clip: ClipRecord, keyframes: list[KeyframeRecord]) -> ClipScoreComponent:
    if clip.media_kind != MediaKind.video:
        return ClipScoreComponent(status="not_applicable", score=0.0, detail="audio-only clip")
    if not keyframes:
        return ClipScoreComponent(status="missing", score=0.0, detail="no keyframe for clip")
    return ClipScoreComponent(status="available", score=1.0, detail=f"{len(keyframes)} keyframe record(s)")


def _analysis_confidence_score(analyses: list[AnalysisRecord]) -> ClipScoreComponent:
    if not analyses:
        return ClipScoreComponent(status="missing", score=0.0, detail="no analysis record for clip")
    scores = []
    for analysis in analyses:
        base = (analysis.material_type.confidence + analysis.original_audio_usability.confidence) / 2.0
        evidence_bonus = min((len(analysis.transcript_refs) + len(analysis.keyframe_refs)) * 0.1, 0.2)
        risk_penalty = min(len(analysis.risk_flags) * 0.08, 0.4)
        scores.append(_clamp(base + evidence_bonus - risk_penalty))
    return ClipScoreComponent(status="available", score=round(sum(scores) / len(scores), 3), detail=f"{len(analyses)} analysis record(s)")


def _duration_fit_score(clip: ClipRecord, brief: EditBrief) -> ClipScoreComponent:
    target = brief.selected_duration_seconds
    if target <= 0:
        return ClipScoreComponent(status="failed", score=0.0, detail="brief target duration is invalid")
    ratio = clip.boundary.duration_seconds / target
    if ratio <= 0.08:
        score = ratio / 0.08
    elif ratio <= 0.35:
        score = 1.0
    else:
        score = max(0.1, 1.0 - min((ratio - 0.35) / 0.65, 0.9))
    return ClipScoreComponent(status="available", score=round(_clamp(score), 3), detail=f"clip/target duration ratio {ratio:.3f}")


def _source_risk_penalty(clip: ClipRecord, analyses: list[AnalysisRecord]) -> float:
    penalty = min(len(clip.inherited_source_risk_flags) * 0.08 + len(clip.risk_flags) * 0.06, 0.35)
    penalty += min(sum(len(item.risk_flags) for item in analyses) * 0.04, 0.25)
    return round(_clamp(penalty), 3)


def _overall_score(
    *,
    speech: float,
    transcript_density: float,
    audio: float,
    visual: float,
    keyframe: float,
    analysis: float,
    duration: float,
    source_penalty: float,
) -> float:
    raw = (
        speech * 0.18
        + transcript_density * 0.12
        + audio * 0.16
        + visual * 0.16
        + keyframe * 0.12
        + analysis * 0.18
        + duration * 0.08
    )
    return round(_clamp(raw - source_penalty), 3)


def _selection(score: float) -> tuple[str, str]:
    if score >= 0.75:
        return "hero", "keep"
    if score >= 0.55:
        return "support", "keep"
    if score >= 0.35:
        return "context", "consider"
    if score >= 0.2:
        return "review", "review"
    return "drop", "drop"


def _evidence_level(
    transcripts: list[TranscriptRecord],
    keyframes: list[KeyframeRecord],
    analyses: list[AnalysisRecord],
) -> str:
    has_t = bool(transcripts)
    has_k = bool(keyframes)
    has_a = bool(analyses)
    if sum((has_t, has_k, has_a)) >= 2:
        return "multi_modal"
    if has_t:
        return "transcript_available"
    if has_k:
        return "keyframe_available"
    if has_a:
        return "analysis_available"
    return "clips_only"


def _keyframe_cluster_id(root: Path, keyframes: list[KeyframeRecord]) -> str | None:
    if not keyframes:
        return None
    digest = hashlib.sha256()
    for keyframe in sorted(keyframes, key=lambda item: item.keyframe_id):
        path = root / keyframe.image_path
        digest.update(keyframe.image_path.encode("utf-8"))
        if path.exists() and path.is_file():
            digest.update(path.read_bytes())
    return "keyframe_cluster_" + digest.hexdigest()[:16]


def _reasons(
    *,
    overall: float,
    speech: ClipScoreComponent,
    transcript_density: ClipScoreComponent,
    audio: ClipAudioEnergy,
    visual: ClipScoreComponent,
    keyframe: ClipScoreComponent,
    analysis: ClipScoreComponent,
    duration: ClipScoreComponent,
    source_penalty: float,
) -> list[str]:
    reasons = [f"overall deterministic score {overall:.3f}"]
    for label, score in (
        ("speech", speech.score),
        ("transcript density", transcript_density.score),
        ("audio energy", audio.score),
        ("visual change", visual.score),
        ("keyframe coverage", keyframe.score),
        ("analysis confidence", analysis.score),
        ("duration fit", duration.score),
    ):
        if score >= 0.7:
            reasons.append(f"strong {label} evidence")
        elif score <= 0.05:
            reasons.append(f"weak or missing {label} evidence")
    if source_penalty:
        reasons.append(f"source/analysis risk penalty {source_penalty:.3f}")
    return reasons


def _clamp(value: float) -> float:
    return min(max(float(value), 0.0), 1.0)
