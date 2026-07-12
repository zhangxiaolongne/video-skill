from __future__ import annotations

import hashlib
from pathlib import Path

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.bgm_match import BgmMatchReport
from artist_portrait_editor.models.creative_strategy import CreativeStrategy, CreativeStrategyPackage, StrategyRange
from artist_portrait_editor.models.editorial_score import EditorialCandidateScore, EditorialScoreSet
from artist_portrait_editor.models.first_cut_review import FirstCutSelfReview
from artist_portrait_editor.models.second_cut_render import SecondCutRender
from artist_portrait_editor.models.state import ActiveMode, OverallStatus, StepLedgerEntry, StepStatus
from artist_portrait_editor.models.structure_recommendation import StructureRecommendation
from artist_portrait_editor.models.text_plan import TextTimingPlan
from artist_portrait_editor.run_records import environment_snapshot, new_run_id, utc_now, write_json
from artist_portrait_editor.workspace_state import atomic_write_text, fingerprint_file, fingerprint_inputs, load_state, project_root, save_state, write_run_report


class CreativeStrategiesError(RuntimeError):
    pass


SPECS = {
    "emotional_arc": {
        "title": "Emotional Arc", "intent": "Build toward a resonant payoff while preserving breathing room.",
        "weights": {"emotion": .38, "ending_resonance": .25, "visual_usability": .17, "audio_usability": .12, "hook": .08},
        "ordering": "strong hook first, rising strategy score through the build, strongest ending evidence last",
        "retained": ["ending resonance", "visual breathing room", "source-audio presence"],
        "sacrifices": ["maximum information density", "rapid cut frequency", "coverage breadth"],
        "text": "minimal", "transition": "restrained cuts with breathing pauses; no decorative transition without playback proof",
    },
    "high_energy": {
        "title": "High Energy", "intent": "Front-load hook and technical rhythm evidence with shorter perceived beats.",
        "weights": {"rhythm": .38, "hook": .30, "visual_usability": .17, "audio_usability": .10, "information_density": .05},
        "ordering": "descending energy score with a separate ending-ranked payoff",
        "retained": ["hook pressure", "technical rhythm continuity", "visual change"],
        "sacrifices": ["breathing room", "chronological continuity", "long-form statement completeness"],
        "text": "restrained", "transition": "hard cuts by default; transitions only at verified visual or audio boundaries",
    },
    "narrative_clarity": {
        "title": "Narrative Clarity", "intent": "Protect source chronology and information/audio continuity before spectacle.",
        "weights": {"information_density": .38, "audio_usability": .27, "visual_usability": .15, "hook": .10, "ending_resonance": .10},
        "ordering": "selected ranges remain chronological after a bounded hook; no arbitrary semantic reordering",
        "retained": ["chronology", "source-audio continuity", "statement space"],
        "sacrifices": ["maximum hook score", "aggressive montage", "nonlinear surprise"],
        "text": "moderate", "transition": "sentence/scene boundary cuts required; unavailable boundaries remain manual",
    },
    "portrait_highlight": {
        "title": "Portrait Highlight", "intent": "Maximize performer-focused highlight evidence and a memorable opening/ending pair.",
        "weights": {"visual_usability": .30, "hook": .25, "emotion": .18, "ending_resonance": .17, "rhythm": .10},
        "ordering": "best hook first, highlight-ranked build, ending-ranked payoff last",
        "retained": ["performer visibility", "hook/ending contrast", "high-ranked moments"],
        "sacrifices": ["source chronology", "complete informational context", "secondary coverage"],
        "text": "minimal", "transition": "performer continuity takes priority over transition variety",
    },
}


def build_creative_strategy_package(project_path: Path) -> tuple[Path, Path, CreativeStrategyPackage, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise CreativeStrategiesError("creative-strategies requires init first")
    data = root / WORKSPACE_DIR / DATA_DIR
    paths = {
        "scores": data / "editorial_scores.json", "structure": data / "structure_recommendation.json",
        "bgm": data / "bgm_match.json", "text": data / "text_timing_plan.json",
        "review": data / "first_cut_self_review.json", "second": data / "second_cut_render.json",
    }
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        raise CreativeStrategiesError("creative-strategies missing current evidence: " + ", ".join(missing))
    scores = EditorialScoreSet.model_validate_json(paths["scores"].read_text(encoding="utf-8"))
    structure = StructureRecommendation.model_validate_json(paths["structure"].read_text(encoding="utf-8"))
    bgm = BgmMatchReport.model_validate_json(paths["bgm"].read_text(encoding="utf-8"))
    text = TextTimingPlan.model_validate_json(paths["text"].read_text(encoding="utf-8"))
    review = FirstCutSelfReview.model_validate_json(paths["review"].read_text(encoding="utf-8"))
    second = SecondCutRender.model_validate_json(paths["second"].read_text(encoding="utf-8"))
    if {scores.project_id, structure.project_id, bgm.project_id, text.project_id, review.project_id, second.project_id} != {config.project.id}:
        raise CreativeStrategiesError("creative-strategies project binding mismatch")
    standard = next(item for item in structure.options if item.option_id == "standard")
    target = standard.target_duration_seconds
    strategies = [_strategy(strategy_id, spec, scores.candidates, target, text, bgm) for strategy_id, spec in SPECS.items()]
    signatures = {tuple(item.candidate_id for item in strategy.ranges) for strategy in strategies}
    warnings = [
        "creative strategies are plans; no timeline or media was changed",
        "strategy labels do not prove emotion, narrative meaning, or performance semantics",
        "one exact strategy must be explicitly selected and reviewed before rendering",
    ]
    if text.transcript_coverage_ratio == 0:
        warnings.append("transcript coverage is zero; emotional and narrative strategies are evidence-limited")
    materially_distinct = len(signatures) >= 3
    if not materially_distinct:
        warnings.append("fewer than three materially distinct range signatures were produced")
    key = ":".join(fingerprint_file(path) for path in paths.values())
    package = CreativeStrategyPackage(
        package_id="creative_strategies_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=config.project.id, target_duration_seconds=target,
        editorial_scores_ref=paths["scores"].relative_to(root).as_posix(), editorial_scores_fingerprint=fingerprint_file(paths["scores"]),
        structure_ref=paths["structure"].relative_to(root).as_posix(), structure_fingerprint=fingerprint_file(paths["structure"]),
        bgm_match_ref=paths["bgm"].relative_to(root).as_posix(), bgm_match_fingerprint=fingerprint_file(paths["bgm"]),
        text_plan_ref=paths["text"].relative_to(root).as_posix(), text_plan_fingerprint=fingerprint_file(paths["text"]),
        first_cut_review_ref=paths["review"].relative_to(root).as_posix(), first_cut_review_fingerprint=fingerprint_file(paths["review"]),
        second_cut_ref=paths["second"].relative_to(root).as_posix(), second_cut_fingerprint=fingerprint_file(paths["second"]),
        strategies=strategies, materially_distinct=materially_distinct,
        distinct_range_signatures=len(signatures), transcript_coverage_ratio=text.transcript_coverage_ratio,
        status="degraded" if warnings else "ready", warnings=warnings,
    )
    canonical = data / "creative_strategy_package.json"
    report = root / config.paths.output_dir / "creative_strategy_package.md"
    atomic_write_text(canonical, package.model_dump_json(indent=2) + "\n")
    atomic_write_text(report, _report(package))
    run_id = new_run_id(); refs = [canonical.relative_to(root).as_posix(), report.relative_to(root).as_posix()]
    state.steps["creative_strategies"] = StepLedgerEntry(status=StepStatus.completed_with_warnings, input_fingerprint=fingerprint_inputs(list(paths.items())), output_refs=refs, last_run_id=run_id, warnings=warnings)
    state.active_mode = ActiveMode.creative; state.overall_status = OverallStatus.degraded
    state.latest_run_id = run_id; state.updated_at = utc_now()
    runs = root / WORKSPACE_DIR / RUNS_DIR / run_id; runs.mkdir(parents=True, exist_ok=True)
    write_json(runs / "command.json", {"command": "creative-strategies", "project": str(project_path)})
    write_json(runs / "environment.json", environment_snapshot())
    write_json(runs / "step_result.json", {"step": "creative_strategies", "strategy_count": 4, "distinct_range_signatures": len(signatures), "timeline_mutated": False, "media_rendered": False, "output_refs": refs})
    save_state(root, state); write_run_report(root / config.paths.output_dir, state, warnings)
    return canonical, report, package, warnings


def _strategy(strategy_id: str, spec: dict, candidates: list[EditorialCandidateScore], target: float, text: TextTimingPlan, bgm: BgmMatchReport) -> CreativeStrategy:
    ranked = sorted(candidates, key=lambda item: (-_score(item, spec["weights"]), -item.ranking_confidence, item.start_seconds, item.candidate_id))
    chosen: list[EditorialCandidateScore] = []; total = 0.0
    for item in ranked:
        duration = item.end_seconds - item.start_seconds
        if total >= target - .001: break
        if duration <= 0: continue
        chosen.append(item); total += min(duration, target - total)
    if strategy_id == "narrative_clarity":
        chosen.sort(key=lambda item: (item.source_id, item.start_seconds))
    elif strategy_id == "emotional_arc":
        hook = min(chosen, key=lambda item: item.hook_rank)
        ending_pool = [item for item in chosen if item is not hook] or chosen
        ending = min(ending_pool, key=lambda item: item.ending_rank)
        build = sorted((item for item in chosen if item is not hook and item is not ending), key=lambda item: (_score(item, spec["weights"]), item.start_seconds))
        chosen = [hook] + build + [ending]
    elif strategy_id == "portrait_highlight":
        chosen.sort(key=lambda item: (item.highlight_rank, item.start_seconds))
        ending = min(chosen, key=lambda item: item.ending_rank)
        chosen = [item for item in chosen if item is not ending] + [ending]
    else:
        ending = min(chosen, key=lambda item: item.ending_rank)
        chosen = [item for item in chosen if item is not ending] + [ending]
    ranges: list[StrategyRange] = []; cursor = 0.0
    for index, item in enumerate(chosen):
        duration = min(item.end_seconds - item.start_seconds, target - cursor)
        if duration <= 0: break
        role = "hook" if index == 0 else "payoff" if index == len(chosen) - 1 or cursor + duration >= target - .001 else "build"
        confidence = _confidence(item, spec["weights"])
        ranges.append(StrategyRange(candidate_id=item.candidate_id, source_id=item.source_id, source_in=item.start_seconds, source_out=item.start_seconds + duration, planned_duration=duration, role=role, strategy_score=_score(item, spec["weights"]), evidence_confidence=confidence, selection_reason=f"Selected by {strategy_id} weighted evidence; rank confidence {item.ranking_confidence:.4f}.", semantic_status="available" if confidence >= .65 else "partial" if confidence > 0 else "unavailable"))
        cursor += duration
    no_selected_bgm = bgm.selected_candidate_id is None
    warnings = []
    if any(item.semantic_status == "unavailable" for item in ranges): warnings.append("semantic evidence is unavailable for one or more selected ranges")
    return CreativeStrategy(
        strategy_id=strategy_id, title=spec["title"], creative_intent=spec["intent"],
        target_duration_seconds=target, planned_duration_seconds=round(cursor, 3), ranges=ranges,
        ordering_logic=spec["ordering"], retained_qualities=spec["retained"], sacrifices=spec["sacrifices"],
        source_audio_policy="retain source audio; inspect every reordered cut for discontinuity",
        bgm_policy="no added BGM until explicit candidate selection" if no_selected_bgm else "audition current candidates; do not auto-select or fit",
        text_density_policy=spec["text"], transition_policy=spec["transition"],
        composition_policy="review exact selected ranges; prior sampled reframes cannot be reused as motion-safe proof",
        acceptance_checks=["opening works in playback", "middle has no mechanical drag", "source audio remains intelligible", "text does not cover performance", "composition contains the performer", "ending lands as intended"],
        strategy_confidence=round(sum(item.evidence_confidence for item in ranges) / len(ranges), 4),
        status="degraded" if warnings or text.transcript_coverage_ratio < 1 else "ready", warnings=warnings,
    )


def _score(item: EditorialCandidateScore, weights: dict[str, float]) -> float:
    value = sum(getattr(item, key).score * weight for key, weight in weights.items())
    return round(max(0, min(1, value - item.risk_penalty.score * .20)), 4)


def _confidence(item: EditorialCandidateScore, weights: dict[str, float]) -> float:
    value = sum(getattr(item, key).confidence * weight for key, weight in weights.items())
    return round(max(0, min(1, value * (1 - item.risk_penalty.score * .25))), 4)


def _report(package: CreativeStrategyPackage) -> str:
    lines = ["# Multi-Version Creative Strategies", "", f"- Package: `{package.package_id}`", f"- Target: `{package.target_duration_seconds:.3f}s`", f"- Status: `{package.status}`", f"- Distinct range signatures: `{package.distinct_range_signatures}/4`", f"- Selected strategy: `{package.selected_strategy_id}`", ""]
    for item in package.strategies:
        lines.extend([f"## {item.title}", "", item.creative_intent, "", f"- Planned duration: `{item.planned_duration_seconds:.3f}s`", f"- Confidence: `{item.strategy_confidence:.4f}`", f"- Text density: `{item.text_density_policy}`", f"- Ordering: {item.ordering_logic}", "", "Sacrifices:", ""] + [f"- {value}" for value in item.sacrifices] + [""])
    lines.extend(["## Warnings", ""] + [f"- {item}" for item in package.warnings])
    return "\n".join(lines) + "\n"
