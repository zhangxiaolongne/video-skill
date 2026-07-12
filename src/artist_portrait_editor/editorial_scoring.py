from __future__ import annotations

import hashlib
from pathlib import Path

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.editorial_score import EditorialCandidateScore, EditorialDimension, EditorialScoreSet
from artist_portrait_editor.models.evidence_map import EvidenceMap, EvidenceMapUnit
from artist_portrait_editor.models.state import ActiveMode, OverallStatus, StepLedgerEntry, StepStatus
from artist_portrait_editor.run_records import environment_snapshot, new_run_id, utc_now, write_json
from artist_portrait_editor.workspace_state import atomic_write_text, fingerprint_file, fingerprint_inputs, load_state, project_root, save_state, write_run_report


class EditorialScoringError(RuntimeError):
    pass


def build_editorial_scores(project_path: Path) -> tuple[Path, Path, EditorialScoreSet, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise EditorialScoringError("editorial-score requires init first")
    evidence_path = root / WORKSPACE_DIR / DATA_DIR / "evidence_map.json"
    if not evidence_path.exists():
        raise EditorialScoringError("editorial-score requires a current evidence-map")
    evidence = EvidenceMap.model_validate_json(evidence_path.read_text(encoding="utf-8"))
    if evidence.project_id != config.project.id:
        raise EditorialScoringError("evidence-map project binding mismatch")
    eligible_units = [unit for unit in evidence.units if unit.media_kind in {"video", "image"}]
    if not eligible_units:
        raise EditorialScoringError("editorial-score requires at least one visual candidate unit")
    drafts = [_draft(unit) for unit in eligible_units]
    ranks = {
        "highlight": _ranks(drafts, "highlight_score"),
        "hook": _ranks(drafts, "hook_score"),
        "ending": _ranks(drafts, "ending_score"),
    }
    candidates = [EditorialCandidateScore(**item, highlight_rank=ranks["highlight"][item["candidate_id"]], hook_rank=ranks["hook"][item["candidate_id"]], ending_rank=ranks["ending"][item["candidate_id"]]) for item in drafts]
    warnings = list(evidence.warnings)
    if evidence.overall_status != "ready":
        warnings.append("rankings are evidence-limited and require host/editor review before edit selection")
    fp = fingerprint_file(evidence_path)
    score_set = EditorialScoreSet(
        score_set_id="editorial_scores_" + hashlib.sha256(fp.encode()).hexdigest()[:20],
        project_id=config.project.id, evidence_map_id=evidence.evidence_map_id,
        evidence_map_ref=evidence_path.relative_to(root).as_posix(), evidence_map_fingerprint=fp,
        candidate_count=len(candidates), status="degraded" if warnings else "ready",
        candidates=candidates,
        top_highlight_ids=_top(candidates, "highlight_rank"),
        top_hook_ids=_top(candidates, "hook_rank"),
        top_ending_ids=_top(candidates, "ending_rank"), warnings=warnings,
    )
    canonical = root / WORKSPACE_DIR / DATA_DIR / "editorial_scores.json"
    report = root / "output" / "editorial_scores.md"
    atomic_write_text(canonical, score_set.model_dump_json(indent=2) + "\n")
    atomic_write_text(report, _report(score_set))
    run_id = new_run_id(); refs = [canonical.relative_to(root).as_posix(), report.relative_to(root).as_posix()]
    state.steps["editorial_score"] = StepLedgerEntry(status=StepStatus.completed_with_warnings if warnings else StepStatus.completed, input_fingerprint=fingerprint_inputs([("evidence_map", evidence_path)]), output_refs=refs, last_run_id=run_id, warnings=warnings)
    state.active_mode = ActiveMode.creative; state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready
    state.latest_run_id = run_id; state.updated_at = utc_now()
    runs = root / WORKSPACE_DIR / RUNS_DIR / run_id; runs.mkdir(parents=True, exist_ok=True)
    write_json(runs / "command.json", {"command": "editorial-score", "project": str(project_path)})
    write_json(runs / "environment.json", environment_snapshot())
    write_json(runs / "step_result.json", {"step": "editorial_score", "status": score_set.status, "output_refs": refs, "model_call_performed": False, "network_performed": False})
    save_state(root, state); write_run_report(root / config.paths.output_dir, state, warnings)
    return canonical, report, score_set, warnings


def _draft(unit: EvidenceMapUnit) -> dict:
    info = _information(unit); visual = _visual(unit); audio = _audio(unit); emotion = _unknown("emotion", unit)
    rhythm = _rhythm(unit, audio); hook = _combine("hook", [(info, .35), (visual, .25), (audio, .2), (rhythm, .2)])
    ending = _combine("ending resonance", [(audio, .35), (rhythm, .25), (visual, .2), (emotion, .2)])
    risk_value = min(1.0, .1 * len(unit.degradation_reasons) + .12 * len(unit.conflict_risks) + .03 * len(unit.semantic_unknowns))
    risk = EditorialDimension(score=round(risk_value, 4), confidence=1, evidence_status="available", rationale=[f"{len(unit.degradation_reasons)} degraded channels, {len(unit.conflict_risks)} conflicts, {len(unit.semantic_unknowns)} semantic unknowns"], evidence_refs=[unit.unit_id])
    base = _weighted([(info, .2), (visual, .2), (audio, .2), (rhythm, .15), (emotion, .1), (hook, .15)])
    confidence = sum(x.confidence for x in (info, visual, audio, rhythm, emotion)) / 5
    penalty = risk.score * .25
    candidate_id = "editorial_" + hashlib.sha256(unit.unit_id.encode()).hexdigest()[:20]
    goal_ref = unit.user_goal.refs[0] if unit.user_goal.refs else "user_goal_unavailable"
    warnings = list(unit.degradation_reasons) + list(unit.conflict_risks)
    return dict(candidate_id=candidate_id, unit_id=unit.unit_id, clip_id=unit.clip_id, source_id=unit.source_id, start_seconds=unit.start_seconds, end_seconds=unit.end_seconds, hook=hook, emotion=emotion, information_density=info, visual_usability=visual, audio_usability=audio, rhythm=rhythm, ending_resonance=ending, risk_penalty=risk, highlight_score=_clamp(base - penalty), hook_score=_clamp(hook.score - penalty), ending_score=_clamp(ending.score - penalty), ranking_confidence=round(confidence * (1 - risk.score * .4), 4), user_goal_ref=goal_ref, unknowns=unit.semantic_unknowns, warnings=warnings)


def _information(unit: EvidenceMapUnit) -> EditorialDimension:
    if unit.transcript.status == "unavailable": return _neutral("information density", "transcript unavailable", unit.transcript.refs)
    coverage = float(unit.transcript.facts.get("coverage_ratio", 0)); text = str(unit.transcript.facts.get("text", "")); duration = max(.1, unit.end_seconds - unit.start_seconds)
    density = min(1.0, len(text.strip()) / duration / 12)
    return EditorialDimension(score=round(.55 * coverage + .45 * density, 4), confidence=unit.transcript.confidence, evidence_status=unit.transcript.status, rationale=[f"transcript coverage {coverage:.3f}; character density {len(text.strip()) / duration:.3f}/s"], evidence_refs=unit.transcript.refs)


def _visual(unit: EvidenceMapUnit) -> EditorialDimension:
    if unit.vision.status == "unavailable": return _neutral("visual usability", "visual evidence unavailable", unit.vision.refs)
    semantic = bool(unit.vision.facts.get("visual_semantics_available")); score = .65 if semantic else .5
    return EditorialDimension(score=score, confidence=unit.vision.confidence, evidence_status=unit.vision.status, rationale=["visual semantics available" if semantic else "keyframe coverage only; composition/content quality unknown"], evidence_refs=unit.vision.refs)


def _audio(unit: EvidenceMapUnit) -> EditorialDimension:
    if unit.audio.status != "available": return _neutral("audio usability", "audio features unavailable", unit.audio.refs)
    mean = unit.audio.facts.get("mean_volume_db"); silence = float(unit.audio.facts.get("silence_ratio", 0));
    level = .5 if mean is None else max(0, 1 - abs(float(mean) + 18) / 30)
    return EditorialDimension(score=round(.7 * level + .3 * (1 - silence), 4), confidence=unit.audio.confidence, evidence_status="available", rationale=[f"technical mean level {mean} dB; silence ratio {silence:.3f}; no semantic audio claim"], evidence_refs=unit.audio.refs)


def _rhythm(unit: EvidenceMapUnit, audio: EditorialDimension) -> EditorialDimension:
    if unit.audio.status != "available": return _neutral("rhythm", "no timing-compatible audio features", unit.audio.refs)
    silence = float(unit.audio.facts.get("silence_ratio", 0)); score = .55 + min(.15, silence * .3)
    return EditorialDimension(score=round(score, 4), confidence=audio.confidence * .45, evidence_status="partial", rationale=["energy/silence continuity only; beat, tempo, and cadence unavailable"], evidence_refs=unit.audio.refs)


def _unknown(name: str, unit: EvidenceMapUnit) -> EditorialDimension:
    return _neutral(name, f"{name} semantics unavailable", [unit.unit_id])


def _neutral(name: str, reason: str, refs: list[str]) -> EditorialDimension:
    return EditorialDimension(score=.5, confidence=0, evidence_status="unavailable", rationale=[f"neutral prior: {reason}; not zero quality"], evidence_refs=refs)


def _combine(name: str, values: list[tuple[EditorialDimension, float]]) -> EditorialDimension:
    return EditorialDimension(score=_weighted(values), confidence=round(sum(value.confidence * weight for value, weight in values), 4), evidence_status="available" if all(value.evidence_status == "available" for value, _ in values) else "partial", rationale=[f"{name} combines only available dimensions; unknown dimensions remain neutral"], evidence_refs=sorted({ref for value, _ in values for ref in value.evidence_refs}))


def _weighted(values) -> float: return round(sum(value.score * weight for value, weight in values), 4)
def _clamp(value: float) -> float: return round(max(0, min(1, value)), 4)
def _ranks(items: list[dict], key: str) -> dict[str, int]: return {item["candidate_id"]: rank for rank, item in enumerate(sorted(items, key=lambda value: (-value[key], -value["ranking_confidence"], value["candidate_id"])), start=1)}
def _top(items: list[EditorialCandidateScore], key: str) -> list[str]: return [item.candidate_id for item in sorted(items, key=lambda value: getattr(value, key))[:min(5, len(items))]]


def _report(value: EditorialScoreSet) -> str:
    lines = ["# Editorial Scores", "", f"- Score set: `{value.score_set_id}`", f"- Status: `{value.status}`", f"- Candidates: `{value.candidate_count}`", "- Position bonus: `false`", "- Loudness treated as emotion: `false`", "", "## Top Highlights", ""]
    by_id = {item.candidate_id: item for item in value.candidates}
    for cid in value.top_highlight_ids:
        item = by_id[cid]; lines.append(f"- `{cid}` / `{item.start_seconds:.3f}-{item.end_seconds:.3f}s` / score `{item.highlight_score:.4f}` / confidence `{item.ranking_confidence:.4f}`")
    lines.extend(["", "## Top Hooks", ""] + [f"- `{cid}` / score `{by_id[cid].hook_score:.4f}`" for cid in value.top_hook_ids])
    lines.extend(["", "## Top Endings", ""] + [f"- `{cid}` / score `{by_id[cid].ending_score:.4f}`" for cid in value.top_ending_ids])
    lines.extend(["", "## Warnings", ""] + [f"- {item}" for item in value.warnings])
    return "\n".join(lines) + "\n"
