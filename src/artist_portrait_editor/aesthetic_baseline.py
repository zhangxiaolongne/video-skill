from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.aesthetic_baseline import AestheticBaseline
from artist_portrait_editor.models.clip_score import ClipScoreRecord
from artist_portrait_editor.models.composition import CompositionReview
from artist_portrait_editor.models.cut_review import CutReviewReport
from artist_portrait_editor.models.edit_brief import EditBrief
from artist_portrait_editor.models.final_export import FinalExportValidationReport
from artist_portrait_editor.models.rhythm import RhythmPlan
from artist_portrait_editor.models.sound import SoundDecision
from artist_portrait_editor.models.state import ActiveMode, OverallStatus, StepLedgerEntry, StepStatus
from artist_portrait_editor.models.timeline import TimelineDraft
from artist_portrait_editor.run_records import environment_snapshot, new_run_id, utc_now, write_json
from artist_portrait_editor.workspace_state import (
    atomic_write_text,
    fingerprint_file,
    fingerprint_inputs,
    load_state,
    project_root,
    save_state,
    write_run_report,
)


class AestheticBaselineError(RuntimeError):
    pass


MAX_BASELINE_CANDIDATE_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class QuarantinedBaselineCandidate:
    ref: str
    sha256: str
    raw_bytes: bytes


def prepare_aesthetic_baseline_handoff(project_path: Path) -> tuple[Path, dict, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise AestheticBaselineError("baseline requires init first")
    data = root / WORKSPACE_DIR / DATA_DIR
    paths = {
        "timeline": root / "output" / "timeline_draft.json",
        "edit_brief": data / "edit_brief.json",
        "clip_scores": data / "clip_scores.jsonl",
        "composition_review": data / "composition_review.json",
        "sound_decision": data / "sound_decision.json",
        "rhythm_plan": data / "rhythm_plan.json",
        "cut_review": data / "cut_review.json",
        "final_validation": data / "final_export_validation.json",
    }
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        raise AestheticBaselineError("baseline requires current artifacts: " + ", ".join(missing))
    timeline = TimelineDraft.model_validate_json(paths["timeline"].read_text(encoding="utf-8"))
    brief = EditBrief.model_validate_json(paths["edit_brief"].read_text(encoding="utf-8"))
    composition = CompositionReview.model_validate_json(
        paths["composition_review"].read_text(encoding="utf-8")
    )
    sound = SoundDecision.model_validate_json(paths["sound_decision"].read_text(encoding="utf-8"))
    rhythm = RhythmPlan.model_validate_json(paths["rhythm_plan"].read_text(encoding="utf-8"))
    cut_review = CutReviewReport.model_validate_json(paths["cut_review"].read_text(encoding="utf-8"))
    final_validation = FinalExportValidationReport.model_validate_json(
        paths["final_validation"].read_text(encoding="utf-8")
    )
    scores = _load_clip_scores(paths["clip_scores"])
    score_by_clip = {item.clip_id: item for item in scores}
    samples_by_segment: dict[str, list[dict]] = {item.segment_id: [] for item in timeline.segments}
    for frame in composition.frame_reviews:
        segment = next(
            (item for item in timeline.segments if item.timeline_start <= frame.timestamp_seconds < item.timeline_end),
            timeline.segments[-1] if abs(frame.timestamp_seconds - timeline.actual_duration) <= 0.001 else None,
        )
        if segment is not None:
            samples_by_segment[segment.segment_id].append(frame.model_dump(mode="json"))

    timeline_segments = []
    for segment in timeline.segments:
        score = score_by_clip.get(segment.clip_id)
        timeline_segments.append({
            "segment": segment.model_dump(mode="json"),
            "clip_score": score.model_dump(mode="json") if score else None,
            "composition_samples": samples_by_segment[segment.segment_id],
        })
    handoff = {
        "handoff_version": "1.0",
        "mode": "codex_chatgpt_host_agent_aesthetic_baseline",
        "project_id": config.project.id,
        "timeline_id": timeline.timeline_id,
        "timeline_ref": paths["timeline"].relative_to(root).as_posix(),
        "timeline_fingerprint": fingerprint_file(paths["timeline"]),
        "edit_brief_ref": paths["edit_brief"].relative_to(root).as_posix(),
        "edit_brief_fingerprint": fingerprint_file(paths["edit_brief"]),
        "clip_scores_ref": paths["clip_scores"].relative_to(root).as_posix(),
        "clip_scores_fingerprint": fingerprint_file(paths["clip_scores"]),
        "composition_review_ref": paths["composition_review"].relative_to(root).as_posix(),
        "composition_review_fingerprint": fingerprint_file(paths["composition_review"]),
        "composition_review_id": composition.review_id,
        "sound_decision_ref": paths["sound_decision"].relative_to(root).as_posix(),
        "sound_decision_fingerprint": fingerprint_file(paths["sound_decision"]),
        "sound_decision_id": sound.sound_decision_id,
        "rhythm_plan_ref": paths["rhythm_plan"].relative_to(root).as_posix(),
        "rhythm_plan_fingerprint": fingerprint_file(paths["rhythm_plan"]),
        "rhythm_plan_id": rhythm.rhythm_plan_id,
        "cut_review_ref": paths["cut_review"].relative_to(root).as_posix(),
        "cut_review_fingerprint": fingerprint_file(paths["cut_review"]),
        "cut_review_id": cut_review.cut_review_id,
        "final_validation_ref": paths["final_validation"].relative_to(root).as_posix(),
        "final_validation_fingerprint": fingerprint_file(paths["final_validation"]),
        "duration_options": [item.model_dump(mode="json") for item in brief.duration_options],
        "timeline_segments": timeline_segments,
        "reframe_candidates": [item.model_dump(mode="json") for item in composition.reframe_candidates],
        "sound_decision": sound.model_dump(mode="json"),
        "rhythm_plan": rhythm.model_dump(mode="json"),
        "legacy_cut_review": cut_review.model_dump(mode="json"),
        "final_export_validation": final_validation.model_dump(mode="json"),
        "instructions": {
            "range_coverage": "Assess every supplied timeline segment exactly once; preserve exact ranges.",
            "truth_boundary": "Use only supplied frames and local evidence; name uncertainty for unseen intervals.",
            "concepts": "Create exactly three materially distinct short, standard, and extended concepts.",
            "selection_boundary": "Leave selected_concept_id null; the user must select explicitly.",
            "extended_boundary": "Set requires_source_expansion when target duration exceeds current selected ranges.",
            "audiovisual_boundary": "Judge source audio, BGM, speech/vocal, text, cuts, transitions, pauses, composition, and ending together.",
            "review_boundary": "Technical media validity is not publishability; explicitly supersede unsupported legacy aesthetic claims.",
        },
        "aesthetic_baseline_json_schema": AestheticBaseline.model_json_schema(),
        "model_call_performed_by_cli": False,
        "network_performed": False,
        "media_rendered": False,
        "timeline_mutated": False,
    }
    handoff_path = root / "output" / "aesthetic_baseline_handoff.json"
    atomic_write_text(handoff_path, json.dumps(handoff, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    run_id = _record_step(
        root, config.paths.output_dir, state, "aesthetic_baseline_context",
        fingerprint_inputs(list(paths.items())), [handoff_path.relative_to(root).as_posix()], [],
        {"command": "baseline", "project": str(project_path)},
    )
    handoff["run_id"] = run_id
    return handoff_path, handoff, []


def import_aesthetic_baseline(
    project_path: Path, *, candidate_path: Path
) -> tuple[Path, Path, AestheticBaseline, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise AestheticBaselineError("baseline import requires init first")
    handoff_path = root / "output" / "aesthetic_baseline_handoff.json"
    if not handoff_path.exists():
        raise AestheticBaselineError("baseline import requires baseline handoff first")
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    candidate = _quarantine(root, candidate_path)
    try:
        baseline = AestheticBaseline.model_validate_json(candidate.raw_bytes)
    except ValidationError as exc:
        raise AestheticBaselineError(f"aesthetic baseline candidate is invalid: {exc}") from exc
    _validate_binding(root, baseline, handoff)
    canonical = root / WORKSPACE_DIR / DATA_DIR / "aesthetic_baseline.json"
    report = root / "output" / "aesthetic_baseline.md"
    atomic_write_text(canonical, json.dumps(baseline.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    atomic_write_text(report, render_aesthetic_baseline(baseline))
    warnings = list(dict.fromkeys(baseline.warnings))
    _record_step(
        root, config.paths.output_dir, state, "aesthetic_baseline",
        fingerprint_inputs([("handoff", handoff_path), ("candidate", root / candidate.ref)]),
        [candidate.ref, canonical.relative_to(root).as_posix(), report.relative_to(root).as_posix()],
        warnings, {"command": "baseline", "project": str(project_path), "agent_output": str(candidate_path)},
    )
    return canonical, report, baseline, warnings


def render_aesthetic_baseline(baseline: AestheticBaseline) -> str:
    lines = [
        "# Real Video Aesthetic Baseline", "",
        f"- Baseline: `{baseline.baseline_id}`", f"- Timeline: `{baseline.timeline_id}`",
        f"- Assessed ranges: `{len(baseline.range_assessments)}`",
        f"- Edit concepts: `{len(baseline.edit_concepts)}`",
        "- Selected concept: `none - explicit user selection required`", "",
        "## Highlight And Weak-Area Map", "",
    ]
    for item in baseline.range_assessments:
        lines.append(
            f"- `{item.segment_id}` `{item.timeline_start:.2f}-{item.timeline_end:.2f}s` / "
            f"source `{item.source_in:.2f}-{item.source_out:.2f}s`: `{item.category}` -> "
            f"`{item.keep_or_drop}` (confidence `{item.confidence:.2f}`). {' '.join(item.rationale)}"
        )
        if item.uncertainty:
            lines.append(f"  Uncertainty: {' '.join(item.uncertainty)}")
    lines.extend(["", "## Edit Concepts", ""])
    for concept in baseline.edit_concepts:
        lines.append(
            f"### {concept.name}\n\n- ID: `{concept.concept_id}`\n- Target: "
            f"`{concept.target_duration_seconds:.2f}s` (`{concept.duration_option_id}`)\n"
            f"- Requires source expansion: `{str(concept.requires_source_expansion).lower()}`\n"
            f"- Segments: {', '.join(concept.selected_segment_ids)}\n\n"
            f"Hook: {' '.join(concept.hook_strategy)}\n\n"
            f"Build: {' '.join(concept.build_strategy)}\n\n"
            f"Payoff: {' '.join(concept.payoff_strategy)}\n"
        )
    decision = baseline.audiovisual_rhythm_decision
    lines.extend(["", "## Audiovisual Rhythm Decision", ""])
    lines.append(f"- Overall status: `{decision.overall_status}`")
    lines.append(f"- Beat sync available: `{str(decision.beat_sync_available).lower()}`")
    lines.append(f"- Transcript timing available: `{str(decision.transcript_timing_available).lower()}`")
    lines.append(f"- Clean BGM available: `{str(decision.clean_bgm_available).lower()}`")
    for domain in decision.domains:
        lines.append(
            f"- `{domain.domain}` `{domain.status}`: {' '.join(domain.decision)} "
            f"Risks: {' '.join(domain.risks) if domain.risks else 'none'}"
        )
    review = baseline.first_cut_review
    lines.extend(["", "## First-Cut Aesthetic Review", ""])
    lines.extend([
        f"- Technical delivery: `{review.technical_delivery_status}`",
        f"- Publishability: `{review.publishability}`",
        f"- Aesthetic maturity: `{review.maturity_score:.2f}`",
        f"- Second cut required: `{str(review.second_cut_required).lower()}`",
        "",
    ])
    for issue in review.issues:
        lines.append(
            f"- P{issue.priority} `{issue.severity}` `{issue.domain}`: {issue.diagnosis} "
            f"Required: {issue.required_change}"
        )
    lines.extend(["", "## Conclusions", ""])
    lines.extend(f"- {item}" for item in baseline.conclusions)
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {item}" for item in baseline.warnings] or ["- None"])
    return "\n".join(lines) + "\n"


def _load_clip_scores(path: Path) -> list[ClipScoreRecord]:
    return [
        ClipScoreRecord.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _quarantine(root: Path, candidate_path: Path) -> QuarantinedBaselineCandidate:
    if candidate_path.is_symlink() or not candidate_path.is_file():
        raise AestheticBaselineError("aesthetic baseline candidate must be a regular non-symlink file")
    if candidate_path.stat().st_size > MAX_BASELINE_CANDIDATE_BYTES:
        raise AestheticBaselineError("aesthetic baseline candidate exceeds 2 MiB")
    raw = candidate_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    path = root / WORKSPACE_DIR / "quarantine" / "aesthetic_baseline" / f"host_agent_{digest}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        temporary = path.with_suffix(".json.tmp")
        temporary.write_bytes(raw)
        temporary.replace(path)
    return QuarantinedBaselineCandidate(path.relative_to(root).as_posix(), digest, raw)


def _validate_binding(root: Path, baseline: AestheticBaseline, handoff: dict) -> None:
    expected = {
        "project_id": handoff["project_id"], "timeline_id": handoff["timeline_id"],
        "timeline_ref": handoff["timeline_ref"], "timeline_fingerprint": handoff["timeline_fingerprint"],
        "edit_brief_ref": handoff["edit_brief_ref"], "edit_brief_fingerprint": handoff["edit_brief_fingerprint"],
        "clip_scores_ref": handoff["clip_scores_ref"], "clip_scores_fingerprint": handoff["clip_scores_fingerprint"],
        "composition_review_ref": handoff["composition_review_ref"],
        "composition_review_fingerprint": handoff["composition_review_fingerprint"],
        "composition_review_id": handoff["composition_review_id"],
        "sound_decision_ref": handoff["sound_decision_ref"],
        "sound_decision_fingerprint": handoff["sound_decision_fingerprint"],
        "sound_decision_id": handoff["sound_decision_id"],
        "rhythm_plan_ref": handoff["rhythm_plan_ref"],
        "rhythm_plan_fingerprint": handoff["rhythm_plan_fingerprint"],
        "rhythm_plan_id": handoff["rhythm_plan_id"],
        "cut_review_ref": handoff["cut_review_ref"],
        "cut_review_fingerprint": handoff["cut_review_fingerprint"],
        "cut_review_id": handoff["cut_review_id"],
        "final_validation_ref": handoff["final_validation_ref"],
        "final_validation_fingerprint": handoff["final_validation_fingerprint"],
    }
    for field, value in expected.items():
        if getattr(baseline, field) != value:
            raise AestheticBaselineError(f"aesthetic baseline {field} binding mismatch")
    for ref_field, hash_field in (
        ("timeline_ref", "timeline_fingerprint"), ("edit_brief_ref", "edit_brief_fingerprint"),
        ("clip_scores_ref", "clip_scores_fingerprint"),
        ("composition_review_ref", "composition_review_fingerprint"),
        ("sound_decision_ref", "sound_decision_fingerprint"),
        ("rhythm_plan_ref", "rhythm_plan_fingerprint"),
        ("cut_review_ref", "cut_review_fingerprint"),
        ("final_validation_ref", "final_validation_fingerprint"),
    ):
        if fingerprint_file(root / getattr(baseline, ref_field)) != getattr(baseline, hash_field):
            raise AestheticBaselineError(f"aesthetic baseline {ref_field} is stale")
    method = baseline.method.lower().replace("-", "_").replace(" ", "_")
    if not any(token in method for token in ("host_agent", "codex", "chatgpt", "human")):
        raise AestheticBaselineError("aesthetic baseline method must identify host Agent or human")
    supplied = {item["segment"]["segment_id"]: item["segment"] for item in handoff["timeline_segments"]}
    if {item.segment_id for item in baseline.range_assessments} != set(supplied):
        raise AestheticBaselineError("aesthetic baseline must assess every timeline segment exactly once")
    for item in baseline.range_assessments:
        source = supplied[item.segment_id]
        for field in ("structural_role", "timeline_start", "timeline_end", "source_id", "clip_id", "source_in", "source_out"):
            if getattr(item, field) != source[field]:
                raise AestheticBaselineError(f"aesthetic range binding mismatch: {item.segment_id}.{field}")
    options = {item["option_id"]: item["duration_seconds"] for item in handoff["duration_options"]}
    if {item.duration_option_id for item in baseline.edit_concepts} != {"short_cut", "standard_cut", "extended_cut"}:
        raise AestheticBaselineError("baseline requires short, standard, and extended concepts")
    for concept in baseline.edit_concepts:
        if abs(concept.target_duration_seconds - options[concept.duration_option_id]) > 0.001:
            raise AestheticBaselineError(f"edit concept duration mismatch: {concept.concept_id}")
    forbidden = (
        baseline.timeline_mutated, baseline.edit_points_moved, baseline.media_rendered,
        baseline.automatic_concept_selection, baseline.automatic_music_selection,
        baseline.automatic_bgm_fit, baseline.model_call_performed_by_cli,
        baseline.network_performed, baseline.image_generation_or_editing_used,
        baseline.audiovisual_rhythm_decision.edits_applied,
        baseline.first_cut_review.edits_applied,
    )
    if any(forbidden) or not baseline.reviewed_only_supplied_evidence:
        raise AestheticBaselineError("aesthetic baseline violates V2-01 truth boundaries")


def _record_step(root: Path, output_dir: str, state, step: str, input_fingerprint: str,
                 refs: list[str], warnings: list[str], command: dict) -> str:
    run_id = new_run_id()
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    state.steps[step] = StepLedgerEntry(status=status, input_fingerprint=input_fingerprint,
                                        output_refs=refs, last_run_id=run_id, warnings=warnings)
    state.active_mode = ActiveMode.creative
    state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    run_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / "command.json", command)
    write_json(run_dir / "environment.json", environment_snapshot())
    write_json(run_dir / "step_result.json", {"step": step, "status": status.value, "output_refs": refs})
    save_state(root, state)
    write_run_report(root / output_dir, state, warnings)
    return run_id
