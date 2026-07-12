from __future__ import annotations

import hashlib
import json
from pathlib import Path

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.aesthetic_baseline import AestheticBaseline
from artist_portrait_editor.models.second_cut import SecondCutAction, SecondCutCandidate
from artist_portrait_editor.models.state import ActiveMode, OverallStatus, StepLedgerEntry, StepStatus
from artist_portrait_editor.run_records import environment_snapshot, new_run_id, utc_now, write_json
from artist_portrait_editor.workspace_state import (
    atomic_write_text, fingerprint_file, fingerprint_inputs, load_state,
    project_root, save_state, write_run_report,
)


class SecondCutError(RuntimeError):
    pass


def build_second_cut_candidate(
    project_path: Path, *, concept_id: str
) -> tuple[Path, Path, SecondCutCandidate, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise SecondCutError("second-cut requires init first")
    baseline_path = root / WORKSPACE_DIR / DATA_DIR / "aesthetic_baseline.json"
    if not baseline_path.exists():
        raise SecondCutError("second-cut requires the current aesthetic baseline")
    baseline = AestheticBaseline.model_validate_json(baseline_path.read_text(encoding="utf-8"))
    concept = next((item for item in baseline.edit_concepts if item.concept_id == concept_id), None)
    if concept is None:
        known = ", ".join(item.concept_id for item in baseline.edit_concepts)
        raise SecondCutError(f"unknown concept_id: {concept_id}; choose one of: {known}")
    timeline_path = root / baseline.timeline_ref
    if fingerprint_file(timeline_path) != baseline.timeline_fingerprint:
        raise SecondCutError("aesthetic baseline timeline binding is stale")

    configured_duration = (
        float(config.creative_brief.target_duration_seconds)
        if config.creative_brief.target_duration_seconds is not None
        else 0.0
    )
    target_duration = configured_duration if configured_duration > 0 else concept.target_duration_seconds
    duration_source = "project_config" if configured_duration > 0 else "aesthetic_concept"
    duration_overridden = abs(target_duration - concept.target_duration_seconds) > 0.001
    assessments = {item.segment_id: item for item in baseline.range_assessments}
    actions: list[SecondCutAction] = []

    def add(domain: str, operation: str, *, segments: list[str] | None = None,
            status: str = "manual_boundary_required", evidence: list[str], rationale: str,
            effect: str, prerequisites: list[str] | None = None,
            reframes: list[str] | None = None, duration: float | None = None,
            impacts: list[str] | None = None) -> None:
        actions.append(SecondCutAction(
            action_id=f"second_cut_action_{len(actions) + 1:02d}", order=len(actions) + 1,
            domain=domain, operation=operation, target_segment_ids=segments or [],
            requested_duration_seconds=duration, reframe_candidate_ids=reframes or [],
            execution_status=status, prerequisites=prerequisites or [], evidence_refs=evidence,
            owns_issue_ids=[],
            rationale=rationale, expected_effect=effect, downstream_impacts=impacts or [],
        ))

    rejected = [item.segment_id for item in baseline.range_assessments if item.category == "reject"]
    if rejected:
        add("selection", "remove_rejected_ranges_after_full_interval_verification",
            segments=rejected, status="manual_boundary_required",
            evidence=rejected + [baseline.first_cut_review.highest_impact_issue_id],
            rationale="The highest-impact first-cut issue is a non-performance promotional range.",
            effect="Restores performer continuity and removes the clearest unusable material.",
            prerequisites=["Verify each complete source interval before removal."],
            impacts=["Retiming", "Source-audio continuity", "Preview and final rerender"])
        actions[-1].owns_issue_ids = ["aesthetic_issue_01"]

    add("structure", "reorder_selected_ranges_to_concept_arc",
        segments=concept.selected_segment_ids, status="manual_boundary_required",
        evidence=[concept.concept_id, baseline.baseline_id],
        rationale="The selected concept defines a materially different hook/build/payoff order.",
        effect="Makes the second cut follow the explicitly selected editorial direction.",
        prerequisites=["Recover musical phrase boundaries before non-contiguous source reorder."],
        impacts=["Timeline timing", "Audio continuity", "Transitions", "Text timing"])
    actions[-1].owns_issue_ids = ["aesthetic_issue_03"]

    trim_ids = [item.segment_id for item in baseline.range_assessments
                if item.keep_or_drop in {"trim", "replace"} and item.segment_id in concept.selected_segment_ids]
    if trim_ids:
        add("trim", "locate_and_trim_weak_subranges", segments=trim_ids,
            evidence=trim_ids, rationale="These ranges contain weak wides, static framing, or excess duration.",
            effect="Breaks the mechanical nine-second grid while preserving useful performance moments.",
            prerequisites=["Shot-boundary review", "Phrase-safe in/out points"],
            impacts=["Target-duration fit", "Reframe applicability", "Audio cross-boundaries"])
        actions[-1].owns_issue_ids = ["aesthetic_issue_04"]

    reframe_ids = sorted({candidate for segment_id in concept.selected_segment_ids
                          for candidate in assessments[segment_id].reframe_candidate_ids
                          if "rejected" not in candidate})
    add("reframe", "bind_reframes_per_shot", segments=concept.selected_segment_ids,
        reframes=reframe_ids, evidence=[baseline.composition_review_id] + reframe_ids,
        rationale="Broadcast bands dominate the portrait canvas and subject position changes by shot.",
        effect="Produces intentional mobile composition without clipping face or microphone.",
        prerequisites=["Per-shot boundary recovery", "Explicit crop selection", "Playback validation"],
        impacts=["Text safe zones", "Visual rhythm", "Final render"])
    actions[-1].owns_issue_ids = ["aesthetic_issue_02"]

    add("source_audio", "preserve_and_audition_source_audio_continuity",
        segments=concept.selected_segment_ids, evidence=[baseline.sound_decision_id, baseline.rhythm_plan_id],
        rationale="Mixed live-performance audio is the narrative spine and reordered ranges may create audible jumps.",
        effect="Prevents broken words, breaths, notes, and musical phrases.",
        prerequisites=["Manual phrase/cadence marks", "Audition every reordered boundary"],
        impacts=["Cut positions", "Transition choice", "BGM policy"])
    actions[-1].owns_issue_ids = ["aesthetic_issue_05"]

    add("bgm", "choose_source_audio_only_or_explicitly_auditioned_bgm",
        status="manual_boundary_required", evidence=[baseline.sound_decision_id, "aesthetic_issue_05"],
        rationale="Current fitted BGM has no beat evidence or ducking and may conflict with mixed performance music.",
        effect="Makes music support rather than mask or clash with the performance.",
        prerequisites=["Explicit user BGM decision", "Vocal conflict and loudness audition"],
        impacts=["Ducking", "Fades", "Ending", "Preview and final rerender"])
    actions[-1].owns_issue_ids = ["aesthetic_issue_05"]

    add("text", "place_sparse_text_in_selected_crop_safe_zones",
        segments=concept.selected_segment_ids, evidence=[concept.concept_id, baseline.composition_review_id],
        rationale="No transcript timing exists and crop-safe regions vary by shot.",
        effect="Adds necessary identity/context without covering the performance or fighting vocal timing.",
        prerequisites=["Selected per-shot reframes", "Manual reading-time review"],
        impacts=["Composition", "Pause duration", "Transition timing"])

    add("transition", "assign_transitions_after_phrase_and_shot_boundaries",
        segments=concept.selected_segment_ids, evidence=[baseline.rhythm_plan_id, concept.concept_id],
        rationale="Technical hard cuts and fades are not yet aesthetically bound to performance changes.",
        effect="Uses cuts and fades as structural punctuation instead of decoration.",
        prerequisites=["Verified shot changes", "Verified phrase boundaries"],
        impacts=["Audio continuity", "Visual rhythm", "Render support"])

    add("pause", "locate_breathing_room_before_peak",
        segments=[item.segment_id for item in baseline.range_assessments if item.category == "highlight"],
        evidence=[baseline.audiovisual_rhythm_decision.decision_id],
        rationale="RMS alone cannot identify a meaningful pause, but the emotional peak needs contrast.",
        effect="Creates dynamic range without preserving arbitrary dead space.",
        prerequisites=["Playback review of breath, gesture, and musical release"],
        impacts=["Target duration", "Text timing", "BGM automation"])

    add("ending", "select_verified_audio_visual_cadence",
        segments=["segment_008"], evidence=["segment_008", "aesthetic_issue_06"],
        rationale="The current endpoint is fixed-length and not bound to cadence, applause, or a clean stop.",
        effect="Creates an intentional emotional landing.",
        prerequisites=["Locate cadence", "Choose clean stop versus fade"],
        impacts=["Final duration", "BGM fade", "Last text exit"])
    actions[-1].owns_issue_ids = ["aesthetic_issue_06"]

    if concept.requires_source_expansion:
        add("selection", "select_additional_contiguous_source_ranges",
            status="blocked", evidence=[concept.concept_id],
            rationale="The extended target exceeds the duration of current selected ranges.",
            effect="Supplies enough continuity-backed material for the extended cut.",
            prerequisites=["Host-Agent or human review of additional source ranges"],
            impacts=["All downstream timing and acceptance"])

    add("verification", "render_and_review_second_cut_candidate",
        status="blocked", evidence=[baseline.baseline_id],
        rationale="No edit, reframe, audio decision, or media change is applied by this planning command.",
        effect="Provides the media evidence required for aesthetic comparison with the first cut.",
        prerequisites=["Apply approved actions through supervised editing boundary"],
        impacts=["Preview", "Final export", "Rhythm QC", "Aesthetic acceptance"])

    blocked = sum(item.execution_status == "blocked" for item in actions)
    manual = sum(item.execution_status == "manual_boundary_required" for item in actions)
    deterministic = sum(item.execution_status == "deterministic" for item in actions)
    owned_issue_ids = sorted({issue_id for action in actions for issue_id in action.owns_issue_ids})
    required_issue_ids = {
        issue.issue_id for issue in baseline.first_cut_review.issues
        if issue.severity in {"critical", "high"}
    }
    unowned_high_priority = sorted(required_issue_ids - set(owned_issue_ids))
    status = "blocked" if concept.requires_source_expansion else "warning" if manual else "ready"
    warnings = ["second-cut actions are plans only; no edit was applied"]
    if duration_overridden:
        warnings.append(
            f"project-config duration {target_duration:.3f}s overrides stale concept duration "
            f"{concept.target_duration_seconds:.3f}s"
        )
    if concept.requires_source_expansion:
        warnings.append("selected extended concept requires additional source-range selection")
    key = f"{baseline.baseline_id}:{concept.concept_id}:{fingerprint_file(baseline_path)}"
    candidate = SecondCutCandidate(
        candidate_id="second_cut_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=config.project.id, aesthetic_baseline_id=baseline.baseline_id,
        aesthetic_baseline_ref=baseline_path.relative_to(root).as_posix(),
        aesthetic_baseline_fingerprint=fingerprint_file(baseline_path),
        baseline_timeline_id=baseline.timeline_id, baseline_timeline_ref=baseline.timeline_ref,
        baseline_timeline_fingerprint=baseline.timeline_fingerprint,
        selected_concept_id=concept.concept_id, selected_concept_name=concept.name,
        target_duration_seconds=target_duration, target_duration_source=duration_source,
        concept_duration_seconds=concept.target_duration_seconds,
        concept_duration_overridden=duration_overridden, status=status,
        action_count=len(actions), deterministic_action_count=deterministic,
        manual_boundary_action_count=manual, blocked_action_count=blocked, actions=actions,
        ordered_segment_ids=concept.selected_segment_ids,
        owned_issue_ids=owned_issue_ids,
        unowned_high_priority_issue_ids=unowned_high_priority,
        acceptance_requirements=[
            "Every manual boundary has explicit in/out evidence.",
            "Selected reframes pass full-motion protected-region review.",
            "Source audio and optional BGM pass vocal/conflict audition.",
            "Rendered second cut is compared against the first-cut ranked issues.",
        ], warnings=warnings,
    )
    data_dir = root / WORKSPACE_DIR / DATA_DIR
    json_path = data_dir / "second_cut_candidate.json"
    report_path = root / "output" / "second_cut_candidate.md"
    atomic_write_text(json_path, json.dumps(candidate.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    atomic_write_text(report_path, render_second_cut_candidate(candidate))
    run_id = new_run_id()
    state_status = StepStatus.blocked if status == "blocked" else StepStatus.completed_with_warnings if warnings else StepStatus.completed
    refs = [json_path.relative_to(root).as_posix(), report_path.relative_to(root).as_posix()]
    state.steps["second_cut"] = StepLedgerEntry(
        status=state_status, input_fingerprint=fingerprint_inputs([("aesthetic_baseline", baseline_path), ("timeline", timeline_path)]),
        output_refs=refs, last_run_id=run_id, warnings=warnings,
    )
    state.active_mode = ActiveMode.creative
    state.overall_status = OverallStatus.degraded
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    run_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / "command.json", {"command": "second-cut", "project": str(project_path), "concept_id": concept_id})
    write_json(run_dir / "environment.json", environment_snapshot())
    write_json(run_dir / "step_result.json", {"step": "second_cut", "status": state_status.value, "output_refs": refs, "edits_applied": False})
    save_state(root, state)
    write_run_report(root / config.paths.output_dir, state, warnings)
    return json_path, report_path, candidate, warnings


def render_second_cut_candidate(candidate: SecondCutCandidate) -> str:
    lines = [
        "# Second-Cut Candidate", "", f"- Candidate: `{candidate.candidate_id}`",
        f"- Selected concept: `{candidate.selected_concept_id}` - {candidate.selected_concept_name}",
        f"- Target duration: `{candidate.target_duration_seconds:.2f}s`", f"- Status: `{candidate.status}`",
        "- Edits applied: `false`", "", "## Ordered Actions", "",
    ]
    for action in candidate.actions:
        lines.append(
            f"{action.order}. `{action.domain}` `{action.execution_status}` - {action.operation}: "
            f"{action.rationale} Expected: {action.expected_effect}"
        )
    lines.extend(["", "## Acceptance Requirements", ""])
    lines.extend(f"- {item}" for item in candidate.acceptance_requirements)
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {item}" for item in candidate.warnings)
    return "\n".join(lines) + "\n"
