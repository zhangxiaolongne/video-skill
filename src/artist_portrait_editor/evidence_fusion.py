from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.analysis import AnalysisRecord
from artist_portrait_editor.models.clip import ClipRecord
from artist_portrait_editor.models.edit_brief import EditBrief
from artist_portrait_editor.models.evidence_map import EvidenceChannel, EvidenceMap, EvidenceMapUnit
from artist_portrait_editor.models.keyframe import KeyframeRecord
from artist_portrait_editor.models.state import ActiveMode, OverallStatus, StepLedgerEntry, StepStatus
from artist_portrait_editor.models.transcript import TranscriptRecord
from artist_portrait_editor.run_records import environment_snapshot, new_run_id, utc_now, write_json
from artist_portrait_editor.workspace_records import read_clips_jsonl, read_keyframes_jsonl, read_transcripts_jsonl
from artist_portrait_editor.workspace_state import atomic_write_text, fingerprint_inputs, load_state, project_root, save_state, write_run_report


class EvidenceFusionError(RuntimeError):
    pass


def build_evidence_map(project_path: Path) -> tuple[Path, Path, EvidenceMap, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise EvidenceFusionError("evidence-map requires init first")
    data = root / WORKSPACE_DIR / DATA_DIR
    paths = {
        "sources": data / "sources.jsonl", "clips": data / "clips.jsonl",
        "transcripts": data / "transcripts.jsonl", "keyframes": data / "keyframes.jsonl",
        "analysis": data / "analysis.jsonl", "brief": data / "edit_brief.json",
    }
    required = ("sources", "clips", "keyframes", "analysis", "brief")
    missing = [name for name in required if not paths[name].exists()]
    if missing:
        raise EvidenceFusionError("evidence-map missing: " + ", ".join(missing))
    clips = read_clips_jsonl(paths["clips"])
    transcripts = read_transcripts_jsonl(paths["transcripts"]) if paths["transcripts"].exists() else []
    keyframes = read_keyframes_jsonl(paths["keyframes"])
    analyses = _read_jsonl(paths["analysis"], AnalysisRecord)
    brief = EditBrief.model_validate_json(paths["brief"].read_text(encoding="utf-8"))
    analysis_by_clip = {item.clip_id: item for item in analyses}
    keyframes_by_clip: dict[str, list[KeyframeRecord]] = {}
    for item in keyframes:
        keyframes_by_clip.setdefault(item.clip_id, []).append(item)
    units: list[EvidenceMapUnit] = []
    warnings: list[str] = []
    for clip in clips:
        related_text = [item for item in transcripts if item.source_id == clip.source_id and item.start_seconds < clip.boundary.end_seconds and item.end_seconds > clip.boundary.start_seconds]
        related_frames = keyframes_by_clip.get(clip.clip_id, [])
        analysis = analysis_by_clip.get(clip.clip_id)
        audio = _audio_channel(root / clip.source_location, clip)
        transcript = _transcript_channel(related_text, clip)
        vision = _vision_channel(related_frames, analysis)
        unknowns = []
        if transcript.status != "available":
            unknowns.extend(["spoken_words", "speaker_identity", "lyrics"])
        unknowns.extend(["applause", "music_presence", "emotion", "bpm"])
        conflicts = []
        if audio.status == "available" and transcript.status != "available":
            conflicts.append("audio_present_but_speech_overlap_unknown")
        if "mixed" in " ".join(brief.sound_strategy).lower():
            conflicts.append("mixed_source_audio_must_not_be_treated_as_clean_bgm")
        degradation = []
        if transcript.status != "available": degradation.append("transcript_unavailable")
        if vision.status != "available": degradation.append("visual_semantics_unavailable")
        if audio.status != "available": degradation.append("audio_features_unavailable")
        usable = ["clip_boundary", "source_provenance"]
        if related_frames: usable.append("keyframe_timestamp")
        if audio.status == "available": usable.extend(["mean_volume_db", "peak_volume_db", "silence_ratio"])
        if related_text: usable.extend(["transcript_text", "transcript_timing"])
        units.append(EvidenceMapUnit(
            unit_id="evidence_" + hashlib.sha256(clip.clip_id.encode()).hexdigest()[:20],
            source_id=clip.source_id, source_content_hash=clip.source_content_hash,
            clip_id=clip.clip_id, clip_fingerprint=analysis.clip_fingerprint if analysis else clip.source_fingerprint,
            start_seconds=clip.boundary.start_seconds, end_seconds=clip.boundary.end_seconds,
            scene_method=clip.method.value, scene_confidence=clip.boundary_confidence,
            transcript=transcript, vision=vision, audio=audio,
            user_goal=EvidenceChannel(status="available", confidence=1.0, refs=[brief.edit_brief_id], facts={"theme": brief.theme, "audience": brief.audience, "tone": brief.tone, "target_platform": brief.target_platform, "target_duration_seconds": brief.selected_duration_seconds}),
            semantic_unknowns=sorted(set(unknowns)), conflict_risks=conflicts,
            downstream_usable_features=usable, degradation_reasons=degradation,
        ))
    if not units:
        raise EvidenceFusionError("evidence-map requires at least one clip")
    ratios = {
        "transcript": _ratio(units, lambda item: item.transcript.status == "available"),
        "keyframe": _ratio(units, lambda item: bool(item.vision.refs)),
        "audio": _ratio(units, lambda item: item.audio.status == "available"),
        "scene": _ratio(units, lambda item: item.scene_method == "pyscenedetect"),
    }
    global_unknowns = sorted({value for item in units for value in item.semantic_unknowns})
    if ratios["transcript"] < 1: warnings.append("transcript coverage is incomplete; missing text is not silence")
    if any(item.vision.status != "available" for item in units): warnings.append("keyframes are samples; visual semantics remain unavailable where not explicitly analyzed")
    warnings.append("audio energy does not classify speech, music, applause, emotion, lyrics, or BPM")
    fingerprints = {name: _fingerprint(path) for name, path in paths.items() if path.exists()}
    map_id = "evidence_map_" + hashlib.sha256(json.dumps(fingerprints, sort_keys=True).encode()).hexdigest()[:20]
    evidence_map = EvidenceMap(
        evidence_map_id=map_id, project_id=config.project.id, input_fingerprints=fingerprints,
        unit_count=len(units), transcript_coverage_ratio=ratios["transcript"],
        keyframe_coverage_ratio=ratios["keyframe"], audio_feature_coverage_ratio=ratios["audio"],
        scene_detection_ratio=ratios["scene"], overall_status="degraded" if warnings else "ready",
        units=units, global_unknowns=global_unknowns, warnings=warnings,
    )
    canonical = data / "evidence_map.json"
    report = root / "output" / "evidence_map.md"
    atomic_write_text(canonical, evidence_map.model_dump_json(indent=2) + "\n")
    atomic_write_text(report, _report(evidence_map))
    run_id = new_run_id()
    refs = [canonical.relative_to(root).as_posix(), report.relative_to(root).as_posix()]
    state.steps["evidence_map"] = StepLedgerEntry(status=StepStatus.completed_with_warnings if warnings else StepStatus.completed, input_fingerprint=fingerprint_inputs([(name, path) for name, path in paths.items() if path.exists()]), output_refs=refs, last_run_id=run_id, warnings=warnings)
    state.active_mode = ActiveMode.creative; state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready
    state.latest_run_id = run_id; state.updated_at = utc_now()
    runs = root / WORKSPACE_DIR / RUNS_DIR / run_id; runs.mkdir(parents=True, exist_ok=True)
    write_json(runs / "command.json", {"command": "evidence-map", "project": str(project_path)})
    write_json(runs / "environment.json", environment_snapshot())
    write_json(runs / "step_result.json", {"step": "evidence_map", "status": evidence_map.overall_status, "output_refs": refs, "network_performed": False, "model_call_performed": False})
    save_state(root, state); write_run_report(root / config.paths.output_dir, state, warnings)
    return canonical, report, evidence_map, warnings


def _transcript_channel(items: list[TranscriptRecord], clip: ClipRecord) -> EvidenceChannel:
    if not items:
        return EvidenceChannel(status="unavailable", confidence=0, missing_reason="no overlapping transcript records", limitations=["absence does not prove silence"])
    overlap = sum(max(0, min(item.end_seconds, clip.boundary.end_seconds) - max(item.start_seconds, clip.boundary.start_seconds)) for item in items)
    coverage = min(1.0, overlap / clip.boundary.duration_seconds)
    return EvidenceChannel(status="available" if coverage >= 0.8 else "partial", confidence=sum(item.confidence for item in items) / len(items), refs=[item.transcript_id for item in items], facts={"coverage_ratio": round(coverage, 4), "text": " ".join(item.text for item in items), "languages": sorted({item.language for item in items if item.language})}, limitations=[] if coverage >= 0.8 else ["transcript only partially overlaps clip"])


def _vision_channel(items: list[KeyframeRecord], analysis: AnalysisRecord | None) -> EvidenceChannel:
    if not items:
        return EvidenceChannel(status="unavailable", confidence=0, missing_reason="no keyframe sample", limitations=["missing keyframe does not prove blank video"])
    semantic = bool(analysis and analysis.visual_quality.level > 0)
    return EvidenceChannel(status="available" if semantic else "partial", confidence=analysis.visual_quality.confidence if semantic else 0.4, refs=[item.keyframe_id for item in items], facts={"sample_count": len(items), "timestamps": [item.timestamp_seconds for item in items], "visual_semantics_available": semantic}, limitations=[] if semantic else ["sampled pixels exist but visual semantics were not analyzed"])


def _audio_channel(path: Path, clip: ClipRecord) -> EvidenceChannel:
    if not path.exists() or clip.media_kind.value == "image":
        return EvidenceChannel(status="unavailable", confidence=0, missing_reason="source audio unavailable")
    command = ["ffmpeg", "-hide_banner", "-nostats", "-ss", f"{clip.boundary.start_seconds:.3f}", "-t", f"{clip.boundary.duration_seconds:.3f}", "-i", str(path), "-af", "silencedetect=n=-45dB:d=0.25,volumedetect", "-vn", "-f", "null", "-"]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        return EvidenceChannel(status="unavailable", confidence=0, missing_reason="local ffmpeg audio analysis failed")
    text = result.stderr
    mean = _db(text, r"mean_volume:\s*(-?[0-9.]+) dB")
    peak = _db(text, r"max_volume:\s*(-?[0-9.]+) dB")
    silence = sum(float(value) for value in re.findall(r"silence_duration:\s*([0-9.]+)", text))
    return EvidenceChannel(status="available", confidence=0.9, refs=[clip.clip_id], facts={"mean_volume_db": mean, "peak_volume_db": peak, "silence_ratio": round(min(1.0, silence / clip.boundary.duration_seconds), 4), "method": "ffmpeg_volumedetect_silencedetect_v1"}, limitations=["energy cannot classify speech, music, applause, emotion, lyrics, or BPM"])


def _db(text: str, pattern: str) -> float | None:
    match = re.search(pattern, text)
    return float(match.group(1)) if match else None


def _read_jsonl(path: Path, model):
    return [model.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _fingerprint(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _ratio(items, predicate) -> float:
    return round(sum(1 for item in items if predicate(item)) / len(items), 4)


def _report(value: EvidenceMap) -> str:
    lines = ["# Evidence Map", "", f"- ID: `{value.evidence_map_id}`", f"- Status: `{value.overall_status}`", f"- Units: `{value.unit_count}`", f"- Transcript coverage: `{value.transcript_coverage_ratio:.4f}`", f"- Keyframe coverage: `{value.keyframe_coverage_ratio:.4f}`", f"- Audio feature coverage: `{value.audio_feature_coverage_ratio:.4f}`", f"- Detected-scene ratio: `{value.scene_detection_ratio:.4f}`", "", "## Truth Boundary", ""]
    lines.extend(f"- Unknown: `{item}`" for item in value.global_unknowns)
    lines.extend(["", "## Warnings", ""] + [f"- {item}" for item in value.warnings])
    return "\n".join(lines) + "\n"
