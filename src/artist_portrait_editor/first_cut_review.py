from __future__ import annotations

import hashlib
import json
from pathlib import Path

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.bgm_match import BgmMatchReport
from artist_portrait_editor.models.editorial_score import EditorialScoreSet
from artist_portrait_editor.models.final_export import FinalExportManifest, FinalExportValidationReport
from artist_portrait_editor.models.first_cut_review import FirstCutDomainReview, FirstCutSelfReview
from artist_portrait_editor.models.reframe import ReframeApplication
from artist_portrait_editor.models.state import ActiveMode, OverallStatus, StepLedgerEntry, StepStatus
from artist_portrait_editor.models.structure_recommendation import StructureRecommendation
from artist_portrait_editor.models.text_plan import TextTimingPlan
from artist_portrait_editor.run_records import environment_snapshot, new_run_id, utc_now, write_json
from artist_portrait_editor.workspace_state import atomic_write_text, fingerprint_file, fingerprint_inputs, load_state, project_root, save_state, write_run_report


class FirstCutReviewError(RuntimeError):
    pass


def build_first_cut_self_review(project_path: Path) -> tuple[Path, Path, FirstCutSelfReview, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise FirstCutReviewError("first-cut-review requires init first")
    data = root / WORKSPACE_DIR / DATA_DIR
    paths = {
        "manifest": data / "final_export_manifest.json",
        "validation": data / "final_export_validation.json",
        "baseline": data / "aesthetic_baseline.json",
        "scores": data / "editorial_scores.json",
        "structure": data / "structure_recommendation.json",
        "bgm": data / "bgm_match.json",
        "text": data / "text_timing_plan.json",
        "reframe": data / "reframe_application.json",
    }
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        raise FirstCutReviewError("first-cut-review missing current evidence: " + ", ".join(missing))
    manifest = FinalExportManifest.model_validate_json(paths["manifest"].read_text(encoding="utf-8"))
    validation = FinalExportValidationReport.model_validate_json(paths["validation"].read_text(encoding="utf-8"))
    baseline = json.loads(paths["baseline"].read_text(encoding="utf-8"))
    scores = EditorialScoreSet.model_validate_json(paths["scores"].read_text(encoding="utf-8"))
    structure = StructureRecommendation.model_validate_json(paths["structure"].read_text(encoding="utf-8"))
    bgm = BgmMatchReport.model_validate_json(paths["bgm"].read_text(encoding="utf-8"))
    text = TextTimingPlan.model_validate_json(paths["text"].read_text(encoding="utf-8"))
    reframe = ReframeApplication.model_validate_json(paths["reframe"].read_text(encoding="utf-8"))
    if {manifest.project_id, scores.project_id, structure.project_id, bgm.project_id, text.project_id, reframe.project_id} != {config.project.id}:
        raise FirstCutReviewError("first-cut-review project binding mismatch")
    old_review = baseline["first_cut_review"]
    issue_by_domain = {item["domain"]: item for item in old_review["issues"]}
    domains = [
        _domain("opening", issue_by_domain.get("opening") or issue_by_domain.get("selection"), "Select the current top hook with semantic/playback verification; do not apply the plan silently."),
        _domain("middle_pacing", issue_by_domain.get("pacing"), "Apply and render one selected duration/structure option, then review drag in playback."),
        FirstCutDomainReview(domain="emotion", status="unavailable", severity="high", diagnosis="Emotion semantics remain unavailable; technical energy and ranking priors cannot prove emotional continuity.", evidence_refs=[scores.score_set_id], required_change="Obtain transcript/visual/audio semantic review and compare emotional continuity in playback."),
        _bgm_domain(bgm),
        _text_domain(text),
        _domain("ending", issue_by_domain.get("ending"), "Choose and render an evidence-backed complete ending, then review its audio-visual cadence."),
        _domain("transitions", None, "Review every cut against shot, sentence, lyric, or phrase boundaries after semantic evidence exists."),
        _composition_domain(reframe),
        FirstCutDomainReview(domain="technical_delivery", status="usable" if validation.valid else "conflict", severity="none" if validation.valid else "critical", diagnosis="Final media passes technical validation, which does not prove aesthetic publishability." if validation.valid else "Final media fails technical validation.", evidence_refs=[paths["validation"].relative_to(root).as_posix(), manifest.output_content_hash], required_change="Preserve technical validity through the second cut and rerun media QC.", resolved_in_canonical_final=validation.valid),
    ]
    severity_weight = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    highest = max(domains, key=lambda item: severity_weight[item.severity]).domain
    warnings = ["technical delivery validity is not aesthetic publishability", "structure, reframe, text, and BGM-match artifacts are plans or separate playback evidence, not canonical-final edits"]
    review = FirstCutSelfReview(
        review_id="first_cut_review_" + hashlib.sha256(":".join(fingerprint_file(path) for path in paths.values()).encode()).hexdigest()[:20],
        project_id=config.project.id, final_ref=manifest.output_ref, final_hash=manifest.output_content_hash,
        final_validation_ref=paths["validation"].relative_to(root).as_posix(),
        baseline_ref=paths["baseline"].relative_to(root).as_posix(), baseline_fingerprint=fingerprint_file(paths["baseline"]),
        editorial_scores_ref=paths["scores"].relative_to(root).as_posix(), editorial_scores_fingerprint=fingerprint_file(paths["scores"]),
        structure_ref=paths["structure"].relative_to(root).as_posix(), structure_fingerprint=fingerprint_file(paths["structure"]),
        bgm_match_ref=paths["bgm"].relative_to(root).as_posix(), bgm_match_fingerprint=fingerprint_file(paths["bgm"]),
        text_plan_ref=paths["text"].relative_to(root).as_posix(), text_plan_fingerprint=fingerprint_file(paths["text"]),
        reframe_application_ref=paths["reframe"].relative_to(root).as_posix(), reframe_application_fingerprint=fingerprint_file(paths["reframe"]),
        publishability=old_review["publishability"], maturity_score=old_review["maturity_score"],
        technical_delivery_valid=validation.valid, second_cut_required=True, domains=domains,
        highest_priority_domain=highest,
        planned_but_unapplied=["ranked hook/highlight/ending candidates", "39/60/90-second structures", "BGM mood/rhythm pressure decisions", "text/subtitle timing plan", "independent reframe playback candidate"],
        next_actions=["Select one structure option explicitly.", "Obtain transcript or manual semantic boundaries.", "Resolve source-audio/BGM strategy.", "Apply supervised reframes and text to a second-cut candidate.", "Render and compare the second cut against this canonical final."],
        warnings=warnings,
    )
    canonical = data / "first_cut_self_review.json"
    report = root / "output" / "first_cut_self_review.md"
    atomic_write_text(canonical, review.model_dump_json(indent=2) + "\n")
    atomic_write_text(report, _report(review))
    run_id = new_run_id()
    refs = [canonical.relative_to(root).as_posix(), report.relative_to(root).as_posix()]
    state.steps["first_cut_review"] = StepLedgerEntry(status=StepStatus.completed_with_warnings, input_fingerprint=fingerprint_inputs(list(paths.items())), output_refs=refs, last_run_id=run_id, warnings=warnings)
    state.active_mode = ActiveMode.creative
    state.overall_status = OverallStatus.degraded
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    runs = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs.mkdir(parents=True, exist_ok=True)
    write_json(runs / "command.json", {"command": "first-cut-review", "project": str(project_path)})
    write_json(runs / "environment.json", environment_snapshot())
    write_json(runs / "step_result.json", {"step": "first_cut_review", "publishability": review.publishability, "edits_applied": False, "media_rendered": False})
    save_state(root, state)
    write_run_report(root / config.paths.output_dir, state, warnings)
    return canonical, report, review, warnings


def _domain(domain: str, issue: dict | None, required_change: str) -> FirstCutDomainReview:
    if issue:
        severity = issue["severity"]
        return FirstCutDomainReview(domain=domain, status="conflict", severity=severity, diagnosis=issue["diagnosis"], evidence_refs=issue["evidence_refs"], required_change=required_change)
    return FirstCutDomainReview(domain=domain, status="review", severity="medium", diagnosis=f"No current evidence proves {domain.replace('_', ' ')} is aesthetically resolved in the canonical final.", evidence_refs=["aesthetic_baseline:first_cut_review"], required_change=required_change)


def _bgm_domain(bgm: BgmMatchReport) -> FirstCutDomainReview:
    if not bgm.candidates:
        return FirstCutDomainReview(domain="bgm_voice", status="review", severity="medium", diagnosis="No added BGM candidate exists; source-audio speech/vocal continuity still lacks semantic boundaries.", evidence_refs=[bgm.bgm_match_id], required_change="Review source-audio continuity and retain no-added-music unless an explicit clean candidate is supplied.")
    high = any(item.ducking_pressure == "high" for item in bgm.candidates)
    return FirstCutDomainReview(domain="bgm_voice", status="conflict" if high else "review", severity="high" if high else "medium", diagnosis="Current candidates have unresolved mood/rhythm and voice-conflict pressure; no candidate is aesthetically selected.", evidence_refs=[bgm.bgm_match_id] + [item.music_candidate_id for item in bgm.candidates], required_change="Choose source-audio-only or audition one explicit clean BGM candidate with ducking and vocal review.")


def _text_domain(text: TextTimingPlan) -> FirstCutDomainReview:
    unavailable = sum(item.unavailable_subtitle_slot_count for item in text.options)
    return FirstCutDomainReview(domain="text", status="unavailable" if unavailable else "review", severity="high" if unavailable else "medium", diagnosis=f"Text plan has {unavailable} unavailable subtitle slots because transcript coverage is {text.transcript_coverage_ratio:.3f}; no text has been rendered.", evidence_refs=[text.text_plan_id], required_change="Obtain transcript or explicit user text, validate reading/safe regions, and render text only in the supervised second cut.")


def _composition_domain(reframe: ReframeApplication) -> FirstCutDomainReview:
    visible = sum(item.visible_crop_applied for item in reframe.segments)
    return FirstCutDomainReview(domain="composition", status="conflict" if visible else "review", severity="critical" if visible else "medium", diagnosis=f"A separate reframe playback contains {visible} visibly reframed segments, but canonical_final_overwritten is false; the canonical final composition is unchanged.", evidence_refs=[reframe.application_id, reframe.output_ref], required_change="Review the independent playback, approve per-shot reframes, and render them into a supervised second-cut candidate without overwriting the first-cut evidence.")


def _report(review: FirstCutSelfReview) -> str:
    lines = ["# First-Cut Aesthetic Self-Review", "", f"- Review: `{review.review_id}`", f"- Publishability: `{review.publishability}`", f"- Maturity: `{review.maturity_score:.3f}`", f"- Technical delivery valid: `{str(review.technical_delivery_valid).lower()}`", f"- Second cut required: `{str(review.second_cut_required).lower()}`", "", "## Domains", ""]
    for item in review.domains:
        lines.append(f"- `{item.domain}`: `{item.status}` / `{item.severity}` / resolved in canonical final `{str(item.resolved_in_canonical_final).lower()}`")
    lines.extend(["", "## Planned But Unapplied", ""] + [f"- {item}" for item in review.planned_but_unapplied])
    lines.extend(["", "## Next Actions", ""] + [f"- {item}" for item in review.next_actions])
    return "\n".join(lines) + "\n"
