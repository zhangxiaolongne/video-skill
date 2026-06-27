from __future__ import annotations

import hashlib
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
    BgmCandidate,
    BgmCandidateAnalysis,
    BgmCandidateLedger,
    BgmDuckingInterval,
    BgmEnergyWindow,
    BgmFitPlan,
    BgmFitSegment,
    BgmInputMode,
)
from artist_portrait_editor.models.source import MediaKind, RightsStatus
from artist_portrait_editor.models.timeline import MusicSlotStatus, TimelineDraft


class BgmError(ValueError):
    pass


BEAT_ENGINE_PACKAGES = ("librosa", "aubio", "essentia", "madmom")


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
) -> tuple[BgmFitPlan, TimelineDraft]:
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
    fit_mode = "single_pass" if abs(duration - target) <= 0.001 else "trim" if duration > target else "loop"
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
    ducking = [
        BgmDuckingInterval(
            start=segment.timeline_start,
            end=segment.timeline_end,
            gain_db=-9.0,
            reason="preserve original audio, dialogue, or performance sound",
        )
        for segment in timeline.segments
        if segment.media_role.value in {"audio", "both"}
    ]
    analysis_report = load_analysis_report(
        root / ".artist-portrait" / "data" / "bgm_analysis.json",
        project_id,
    )
    candidate_analysis = None
    analysis_fingerprint = None
    analysis_ref = None
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
    timeline_fingerprint = "sha256:" + hashlib.sha256(timeline_path.read_bytes()).hexdigest()
    fit_key = f"{timeline.timeline_id}:{candidate_id}:{timeline_fingerprint}"
    warnings = [candidate.beat_analysis_reason] if candidate.beat_analysis_reason else []
    if candidate_analysis is None:
        warnings.append("BGM analysis report is missing or does not include this candidate")
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
        fade_in_seconds=min(0.5, target / 4),
        fade_out_seconds=min(1.0, target / 4),
        ducking_intervals=ducking,
        target_gain_db=-3.0 if candidate.integrated_loudness_lufs is None else round(
            min(0.0, -16.0 - candidate.integrated_loudness_lufs), 2
        ),
        beat_alignment_status="unavailable",
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
    beat_engine, beat_reason = detect_beat_engine()
    analyses = [
        analyze_candidate_audio(
            root=root,
            candidate=candidate,
            window_seconds=window_seconds,
            beat_engine=beat_engine,
            beat_reason=beat_reason,
        )
        for candidate in ledger.candidates
    ]
    report = BgmAnalysisReport(
        project_id=project_id,
        source_ledger_fingerprint="sha256:" + hashlib.sha256(ledger_path.read_bytes()).hexdigest(),
        analysis_engine="local_pcm_energy_v1",
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


def analyze_candidate_audio(
    *,
    root: Path,
    candidate: BgmCandidate,
    window_seconds: float,
    beat_engine: str,
    beat_reason: str | None,
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
    if beat_reason:
        warnings.append(beat_reason)
    return BgmCandidateAnalysis(
        music_candidate_id=candidate.music_candidate_id,
        cache_ref=candidate.cache_ref,
        cache_fingerprint=hash_file(cache_path),
        duration=candidate.duration,
        analysis_engine="local_pcm_energy_v1",
        beat_engine=beat_engine,
        beat_analysis_status="unavailable",
        beat_analysis_reason=beat_reason,
        bpm=None,
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


def detect_beat_engine() -> tuple[str, str | None]:
    available = [name for name in BEAT_ENGINE_PACKAGES if find_spec(name) is not None]
    if not available:
        return (
            "none",
            "no mature local beat-analysis engine is installed; BPM and beat grid remain unavailable",
        )
    return ",".join(available), (
        "mature beat-analysis package detected but V0-017 does not execute beat-grid extraction yet"
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
