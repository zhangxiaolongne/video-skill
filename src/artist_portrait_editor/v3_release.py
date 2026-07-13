from __future__ import annotations

import hashlib
import json
from pathlib import Path

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.state import ActiveMode, OverallStatus, StepLedgerEntry, StepStatus
from artist_portrait_editor.models.v3_release import (
    V3ReleaseAudit,
    V3ReleaseEvidence,
    V3ReleaseOutcome,
)
from artist_portrait_editor.run_records import environment_snapshot, new_run_id, utc_now, write_json
from artist_portrait_editor.workspace_errors import WorkspacePrerequisiteError
from artist_portrait_editor.workspace_state import (
    atomic_write_text,
    fingerprint_file,
    fingerprint_inputs,
    load_state,
    project_root,
    save_state,
    write_run_report,
)


class V3ReleaseError(RuntimeError):
    pass


REQUIRED_PROJECT_ARTIFACTS = {
    "creative_strategies": "creative_strategy_package.json",
    "revision_plan": "revision_plan.json",
    "revision_application": "revision_application.json",
    "version_review": "version_review.json",
    "publishability": "publishability.json",
    "nle_roundtrip": "nle_roundtrip.json",
    "creative_memory": "creative_memory.json",
    "second_cut": "second_cut_render.json",
    "bgm_match": "bgm_match.json",
    "text_plan": "text_timing_plan.json",
    "rhythm_plan": "rhythm_plan.json",
}

STRATEGY_IDS = {
    "emotional_arc", "high_energy", "narrative_clarity", "portrait_highlight"
}


def build_v3_release_audit_workspace(
    project_path: Path, *, benchmark_pack_path: Path
) -> tuple[Path, Path, V3ReleaseAudit, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("v3-release-audit requires init to complete first")
    data = root / WORKSPACE_DIR / DATA_DIR
    paths = {label: data / name for label, name in REQUIRED_PROJECT_ARTIFACTS.items()}
    missing = [label for label, path in paths.items() if not path.exists()]
    if missing:
        raise WorkspacePrerequisiteError(
            "v3-release-audit requires current V3 artifacts: " + ", ".join(missing)
        )
    benchmark_path = benchmark_pack_path.expanduser().resolve()
    if not benchmark_path.exists():
        raise WorkspacePrerequisiteError("v3-release-audit requires a real benchmark pack")

    payloads = {label: _read_json(path) for label, path in paths.items()}
    benchmark = _read_json(benchmark_path)
    outcomes = [
        _workflow_chain(config.project.id, payloads),
        _real_media_binding(root, payloads["second_cut"], paths["second_cut"]),
        _multi_version_strategies(payloads["creative_strategies"]),
        _human_revision_truth(payloads["revision_plan"], payloads["revision_application"]),
        _ab_review_truth(payloads["version_review"]),
        _publishability_truth(payloads["publishability"]),
        _nle_handoff_truth(root, payloads["nle_roundtrip"]),
        _creative_memory_boundary(payloads["creative_memory"], config.project.id),
        _audiovisual_coupling(
            payloads["second_cut"], payloads["bgm_match"],
            payloads["text_plan"], payloads["rhythm_plan"],
        ),
        _benchmark_package_boundary(benchmark),
    ]
    evidence = [
        V3ReleaseEvidence(
            label=label,
            ref=path.relative_to(root).as_posix(),
            fingerprint=fingerprint_file(path),
            current=payloads[label].get("project_id", config.project.id) == config.project.id,
            limitation=_limitation(label),
        )
        for label, path in paths.items()
    ]
    evidence.append(
        V3ReleaseEvidence(
            label="real_benchmark_pack",
            ref=benchmark_path.name,
            fingerprint=fingerprint_file(benchmark_path),
            current=True,
            limitation="benchmark media remains local and is not distributable release content",
        )
    )
    failed = sum(item.status == "failed" for item in outcomes)
    warnings = sum(item.status == "warning" for item in outcomes)
    known_gaps = _known_gaps(payloads, benchmark)
    key = json.dumps(
        {
            "project": config.project.id,
            "outcomes": [item.model_dump(mode="json") for item in outcomes],
            "evidence": [item.fingerprint for item in evidence],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    audit = V3ReleaseAudit(
        audit_id="v3_release_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=config.project.id,
        release_version="0.50.0",
        status="blocked" if failed else "release_ready_with_known_gaps",
        outcome_count=len(outcomes),
        passed_count=sum(item.status == "passed" for item in outcomes),
        warning_count=warnings,
        failed_count=failed,
        outcomes=outcomes,
        evidence=evidence,
        known_gaps=known_gaps,
        release_statement=(
            "V3 releases a mature assistant workflow with auditable human control, "
            "not a claim that current media equals a mature human editor's final cut."
        ),
    )
    json_path = data / "v3_release_audit.json"
    md_path = root / config.paths.output_dir / "v3_release_audit.md"
    atomic_write_text(json_path, audit.model_dump_json(indent=2) + "\n")
    atomic_write_text(md_path, render_v3_release_audit(audit))

    warnings_text = [
        item.summary for item in outcomes if item.status == "warning"
    ]
    run_id = new_run_id()
    step_status = (
        StepStatus.blocked if failed else
        StepStatus.completed_with_warnings if warnings else StepStatus.completed
    )
    refs = [json_path.relative_to(root).as_posix(), md_path.relative_to(root).as_posix()]
    inputs = [(label, path) for label, path in paths.items()]
    inputs.append(("real_benchmark_pack", benchmark_path))
    state.steps["v3_release_audit"] = StepLedgerEntry(
        status=step_status,
        input_fingerprint=fingerprint_inputs(inputs),
        output_refs=refs,
        last_run_id=run_id,
        warnings=warnings_text,
    )
    state.active_mode = ActiveMode.creative
    state.overall_status = (
        OverallStatus.blocked if failed else
        OverallStatus.degraded if warnings else OverallStatus.ready
    )
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    run_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        run_dir / "command.json",
        {
            "command": "v3-release-audit",
            "project": project_path.resolve().relative_to(root).as_posix(),
            "benchmark_pack": benchmark_path.name,
        },
    )
    write_json(run_dir / "environment.json", environment_snapshot())
    write_json(
        run_dir / "step_result.json",
        {
            "step": "v3_release_audit",
            "status": step_status.value,
            "release_version": "0.50.0",
            "mature_editor_claimed": False,
            "output_refs": refs,
        },
    )
    save_state(root, state)
    write_run_report(root / config.paths.output_dir, state, warnings_text)
    return json_path, md_path, audit, warnings_text


def _workflow_chain(project_id, payloads):
    mismatches = sorted(
        label for label, payload in payloads.items()
        if payload.get("project_id") not in {None, project_id}
    )
    return _outcome(
        "workflow_chain", "failed" if mismatches else "passed",
        "V3-01 through V3-07 canonical evidence is present and project-bound."
        if not mismatches else "V3 evidence contains project identity mismatches.",
        list(REQUIRED_PROJECT_ARTIFACTS.values()),
        ["mismatched artifacts: " + ", ".join(mismatches)] if mismatches else [],
        ["Regenerate mismatched artifacts from the current project."] if mismatches else [],
    )


def _real_media_binding(root, second, artifact_path):
    output_ref = str(second.get("output_ref") or "")
    output = root / output_ref
    actual = fingerprint_file(output) if output.is_file() else None
    current = bool(
        second.get("media_valid") is True
        and actual == second.get("output_hash")
    )
    return _outcome(
        "real_media_binding", "passed" if current else "failed",
        "Rendered second-cut media exists and matches its recorded content hash."
        if current else "Rendered second-cut media is missing, invalid, or stale.",
        [artifact_path.name, output_ref or "missing output_ref"],
        [] if current else ["technical media binding is required but does not prove aesthetics"],
        [] if current else ["Rerender the second cut and regenerate downstream V3 evidence."],
    )


def _multi_version_strategies(package):
    strategies = package.get("strategies") or []
    ids = {item.get("strategy_id") for item in strategies}
    signatures = {
        tuple(
            (item.get("source_id"), item.get("source_in"), item.get("source_out"))
            for item in strategy.get("ranges") or []
        )
        for strategy in strategies
    }
    valid = (
        ids == STRATEGY_IDS and len(signatures) == 4
        and package.get("selected_strategy_id") is None
    )
    return _outcome(
        "multi_version_strategies", "passed" if valid else "failed",
        "Four materially distinct strategy range signatures remain available without auto-selection."
        if valid else "The four-strategy contract or non-selection boundary is broken.",
        ["creative_strategy_package.json"],
        ["strategy semantics remain degraded where transcript or vision evidence is absent"],
        [] if valid else ["Regenerate V3 creative strategies from current evidence."],
    )


def _human_revision_truth(plan, application):
    clauses = plan.get("semantic_clauses") or []
    outcomes = application.get("semantic_outcomes") or []
    clause_ids = {item.get("clause_id") for item in clauses}
    outcome_ids = {item.get("clause_id") for item in outcomes}
    valid = bool(
        plan.get("intent", {}).get("request_text")
        and application.get("revision_plan_id") == plan.get("revision_plan_id")
        and clause_ids and clause_ids == outcome_ids
        and application.get("canonical_timeline_mutated") is False
        and application.get("media_rendered") is False
    )
    manual = sum(item.get("status") == "manual_only" for item in outcomes)
    status = "failed" if not valid else "warning" if manual == len(outcomes) else "passed"
    return _outcome(
        "human_revision_truth", status,
        f"One explicit human revision is preserved across {len(clauses)} clauses; {manual} remain manual-only."
        if valid else "Human revision plan/application evidence is incomplete or overstated.",
        ["revision_plan.json", "revision_application.json"],
        ["manual-only clauses are tracked requirements, not successful edits"] if manual else [],
        ["Apply and playback-review manual clauses before claiming satisfaction."] if manual else [],
    )


def _ab_review_truth(review):
    versions = review.get("versions") or []
    comparisons = review.get("pairwise_comparisons") or []
    valid = len(versions) >= 2 and bool(comparisons) and review.get("selected_version_id") is None
    return _outcome(
        "ab_review_truth", "passed" if valid else "failed",
        f"A/B review compares {len(versions)} versions and leaves the overall selection empty."
        if valid else "A/B evidence lacks comparable versions or silently selects a winner.",
        ["version_review.json"],
        ["goal-specific proxy advantages do not equal universal aesthetic superiority"],
        [] if valid else ["Regenerate version-review with at least two current candidates."],
    )


def _publishability_truth(report):
    versions = report.get("versions") or []
    tiers = {"publishable", "previewable", "manual_refinement_required", "unusable"}
    valid = bool(versions) and all(item.get("tier") in tiers for item in versions)
    valid = valid and report.get("selected_version_id") is None
    false_publish = any(
        item.get("tier") == "publishable" and item.get("ready_for_publish") is not True
        for item in versions
    )
    valid = valid and not false_publish
    highest = report.get("highest_available_tier")
    return _outcome(
        "publishability_truth", "passed" if valid else "failed",
        f"Every reviewed version has one truthful tier; highest available is {highest}."
        if valid else "Publishability evidence contains invalid tiers or false publication claims.",
        ["publishability.json"],
        ["current real cuts still require manual refinement"] if highest != "publishable" else [],
        ["Complete listed candidate-specific refinements and human playback review."]
        if highest != "publishable" else [],
    )


def _nle_handoff_truth(root, package):
    deliverables = package.get("deliverables") or []
    written = all(
        item.get("status") == "written" and (root / str(item.get("ref") or "")).is_file()
        for item in deliverables
    )
    sources = package.get("source_bindings") or []
    sources_current = bool(sources) and all(
        item.get("exists") is True and item.get("hash_matches") is True for item in sources
    )
    pending = [item for item in package.get("acceptance_checks") or [] if item.get("status") == "pending"]
    truthful = (
        len(deliverables) >= 6 and written and sources_current
        and package.get("roundtrip_verified") is False
        and package.get("import_performed") is False
    )
    status = "warning" if truthful and pending else "failed" if not truthful else "passed"
    return _outcome(
        "nle_handoff_truth", status,
        f"Six editable handoff files are source-bound; {len(pending)} external checks remain pending."
        if truthful else "NLE package files, source bindings, or round-trip truth are invalid.",
        ["nle_roundtrip.json", *[str(item.get("ref")) for item in deliverables]],
        ["written interchange files are not proof of NLE import or round-trip success"] if pending else [],
        ["Complete external import, relink, playback, marker, audio, and re-export checks."] if pending else [],
    )


def _creative_memory_boundary(memory, project_id):
    guards = (
        "memory_applied_to_edit", "timeline_mutated", "media_rendered",
        "automatic_style_selection", "automatic_bgm_selection",
        "model_call_performed_by_cli", "network_performed",
    )
    valid = (
        memory.get("project_id") == project_id
        and int(memory.get("entry_count") or 0) > 0
        and all(memory.get(key) is False for key in guards)
    )
    return _outcome(
        "creative_memory_boundary", "passed" if valid else "failed",
        f"Creative memory retains {memory.get('entry_count', 0)} sourced entries without applying them."
        if valid else "Creative memory is missing, mismatched, or crossed an application boundary.",
        ["creative_memory.json"],
        ["requested and observed memory remains distinct from user-confirmed taste"],
        [] if valid else ["Regenerate memory and inspect every guardrail field."],
    )


def _audiovisual_coupling(second, bgm, text, rhythm):
    valid = (
        second.get("source_audio_retained") is True
        and second.get("text_applied") is False
        and bgm.get("project_id") == second.get("project_id")
        and text.get("project_id") == second.get("project_id")
        and rhythm.get("project_id") == second.get("project_id")
        and rhythm.get("model_call_performed_by_cli") is False
        and rhythm.get("network_performed") is False
    )
    return _outcome(
        "audiovisual_coupling", "passed" if valid else "failed",
        "Source audio, BGM state, text availability, rhythm evidence, and rendered application state remain coupled."
        if valid else "Audiovisual planning and rendered application state are inconsistent.",
        ["second_cut_render.json", "bgm_match.json", "text_timing_plan.json", "rhythm_plan.json"],
        ["no selected BGM and unavailable transcript correctly remain unresolved"],
        [] if valid else ["Regenerate sound, text, rhythm, second-cut, and review evidence together."],
    )


def _benchmark_package_boundary(pack):
    required = {"stage_person", "interview_talking_head", "event_promo_mix"}
    benchmarks = pack.get("benchmarks") or []
    classes = {item.get("benchmark_class") for item in benchmarks}
    valid = (
        classes == required and pack.get("class_coverage_complete") is True
        and int(pack.get("closed_loop_count") or 0) >= 2
        and int(pack.get("input_baseline_count") or 0) >= 1
        and pack.get("synthetic_fixture_counted_as_real") is False
        and pack.get("distributable_media_included") is False
        and pack.get("model_call_performed_by_cli") is False
        and pack.get("network_performed_by_cli") is False
    )
    return _outcome(
        "benchmark_package_boundary", "passed" if valid else "failed",
        "Three real benchmark classes are visible, with two closed loops and one explicit input-only baseline."
        if valid else "Real benchmark coverage or offline/package boundaries are incomplete.",
        ["real_video_benchmark_pack.json"],
        ["event/promo remains input-only and local media is intentionally excluded from the release"],
        [] if valid else ["Rebuild the real benchmark pack before V3 publication."],
    )


def _known_gaps(payloads, benchmark):
    gaps = []
    publishability = payloads["publishability"]
    if publishability.get("highest_available_tier") != "publishable":
        gaps.append("No current real candidate is aesthetically publishable without manual refinement.")
    if payloads["nle_roundtrip"].get("roundtrip_verified") is not True:
        gaps.append("NLE import, relink, playback, and re-export remain externally unverified.")
    manual = sum(
        item.get("status") == "manual_only"
        for item in payloads["revision_application"].get("semantic_outcomes") or []
    )
    if manual:
        gaps.append(f"{manual} human revision clauses remain manual-only.")
    if int(benchmark.get("input_baseline_count") or 0):
        gaps.append("Event/promo benchmark coverage remains an input baseline without a second-cut loop.")
    return gaps or ["Human playback approval remains required before publishing any final media."]


def render_v3_release_audit(audit):
    lines = [
        "# V3 Release Audit", "", f"- Audit: `{audit.audit_id}`",
        f"- Project: `{audit.project_id}`", f"- Release: `{audit.release_tag}`",
        f"- Status: `{audit.status}`", f"- Product claim: `{audit.product_claim}`",
        f"- Mature editor claimed: `{str(audit.mature_editor_claimed).lower()}`",
        f"- Outcomes: `{audit.passed_count}` passed, `{audit.warning_count}` warning, `{audit.failed_count}` failed",
        "", "## Release Statement", "", audit.release_statement, "", "## Outcomes", "",
    ]
    for item in audit.outcomes:
        lines.append(f"- `{item.outcome_id}` `{item.status}`: {item.summary}")
        for limitation in item.limitations:
            lines.append(f"  - Limitation: {limitation}")
        for action in item.next_actions:
            lines.append(f"  - Next: {action}")
    lines.extend(["", "## Known Gaps", ""] + [f"- {item}" for item in audit.known_gaps])
    lines.extend([
        "", "## Guardrails", "", "- Selected version: `null`",
        "- Timeline mutation/render/memory application: `false`",
        "- Automatic version or music selection: `false`",
        "- Human playback and NLE round-trip claims: `false`",
        "- Model/network access by CLI: `false`", "",
    ])
    return "\n".join(lines)


def _outcome(outcome_id, status, summary, refs, limitations, actions):
    return V3ReleaseOutcome(
        outcome_id=outcome_id, status=status, summary=summary,
        evidence_refs=refs, limitations=limitations, next_actions=actions,
    )


def _read_json(path):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise V3ReleaseError(f"invalid V3 evidence {path.name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise V3ReleaseError(f"V3 evidence must be an object: {path.name}")
    return payload


def _limitation(label):
    return {
        "creative_strategies": "strategy proxies do not prove semantic or playback quality",
        "revision_plan": "human request is not an applied edit",
        "revision_application": "application state is not user satisfaction",
        "version_review": "goal-specific comparison does not select a winner",
        "publishability": "technical validity is not aesthetic publishability",
        "nle_roundtrip": "written files are not external NLE acceptance",
        "creative_memory": "memory remains advisory until explicit use",
        "second_cut": "valid media still requires human aesthetic review",
        "bgm_match": "no-file-yet and mixed-audio states remain unresolved",
        "text_plan": "missing transcript cannot be replaced with invented text",
        "rhythm_plan": "technical energy cannot establish emotion or BPM",
    }[label]
