from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from artist_portrait_editor.bgm import load_analysis_report, load_ledger
from artist_portrait_editor.constants import WORKSPACE_DIR
from artist_portrait_editor.media.scanner import hash_file
from artist_portrait_editor.models.bgm import BgmFitPlan
from artist_portrait_editor.models.final_export import FinalExportManifest
from artist_portrait_editor.models.preview import PreviewRenderManifest
from artist_portrait_editor.models.bgm_recommendation import (
    BgmRecommendationContext,
    BgmRecommendationContextCandidate,
    BgmRecommendationFitReview,
    BgmRecommendationRequest,
    BgmRecommendationSelection,
    BgmRecommendationSet,
    BgmRecommendationValidationIssue,
    BgmRecommendationValidationReport,
)
from artist_portrait_editor.models.timeline import TimelineDraft


MAX_BGM_RECOMMENDATION_BYTES = 512 * 1024


class BgmRecommendationError(ValueError):
    def __init__(self, message: str, *, code: str = "bgm_recommendation_error", quarantine_ref: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.quarantine_ref = quarantine_ref


@dataclass(frozen=True)
class QuarantinedBgmRecommendation:
    path: Path
    ref: str
    sha256: str
    byte_count: int
    raw_bytes: bytes


def prepare_bgm_recommendation_handoff(*, root: Path, project_id: str) -> tuple[Path, Path, Path]:
    context = build_bgm_recommendation_context(root=root, project_id=project_id)
    request = BgmRecommendationRequest(
        request_id="bgmreq_" + hashlib.sha256(context.context_id.encode()).hexdigest()[:20],
        project_id=project_id,
        context_id=context.context_id,
        instructions=[
            "Return one JSON object and no surrounding prose.",
            "The root object must match BgmRecommendationSet.",
            "Rank existing music_candidate_id values only; do not invent candidates.",
            "Do not perform final selection; this is recommendation review only.",
            "Do not use network search or paid APIs unless a later project gate explicitly allows it.",
            "Use BGM analysis evidence, timeline duration, proposal sound structure, and risk notes.",
        ],
    )
    data_dir = root / WORKSPACE_DIR / "data"
    output_dir = root / "output"
    context_path = data_dir / "bgm_recommendation_context.json"
    request_path = data_dir / "bgm_recommendation_request.json"
    handoff_path = output_dir / "bgm_recommendation_agent_handoff.json"
    atomic_json(context_path, context.model_dump(mode="json"))
    atomic_json(request_path, request.model_dump(mode="json"))
    atomic_json(
        handoff_path,
        {
            "handoff_version": "1.0",
            "mode": "host_agent_local_model_or_third_party_tool",
            "project_id": project_id,
            "context_id": context.context_id,
            "request_id": request.request_id,
            "instructions": request.instructions,
            "next_command": "artist-portrait bgm recommend --project <project.yaml> --agent-output <candidate.json>",
            "bgm_recommendation_context": context.model_dump(mode="json"),
            "bgm_recommendation_request": request.model_dump(mode="json"),
            "bgm_recommendation_set_json_schema": BgmRecommendationSet.model_json_schema(),
        },
    )
    return context_path, request_path, handoff_path


def build_bgm_recommendation_context(*, root: Path, project_id: str) -> BgmRecommendationContext:
    timeline_path = root / "output" / "timeline_draft.json"
    if not timeline_path.exists():
        raise BgmRecommendationError("BGM recommendation requires output/timeline_draft.json")
    timeline = TimelineDraft.model_validate_json(timeline_path.read_text(encoding="utf-8"))
    if timeline.project_id != project_id:
        raise BgmRecommendationError("timeline project_id mismatch")
    ledger_path = root / WORKSPACE_DIR / "data" / "bgm_candidates.json"
    ledger = load_ledger(ledger_path, project_id)
    if not ledger.candidates:
        raise BgmRecommendationError("BGM recommendation requires at least one candidate")
    analysis_path = root / WORKSPACE_DIR / "data" / "bgm_analysis.json"
    analysis = load_analysis_report(analysis_path, project_id) if analysis_path.exists() else None
    analysis_by_id = {item.music_candidate_id: item for item in analysis.candidates} if analysis else {}
    candidates = []
    for candidate in ledger.candidates:
        analyzed = analysis_by_id.get(candidate.music_candidate_id)
        candidates.append(
            BgmRecommendationContextCandidate(
                music_candidate_id=candidate.music_candidate_id,
                input_mode=candidate.input_mode.value,
                source_ref=candidate.source_ref,
                duration=candidate.duration,
                rights_status=candidate.rights_status.value,
                mixed_audio=candidate.mixed_audio,
                user_intent=candidate.user_intent,
                integrated_loudness_lufs=candidate.integrated_loudness_lufs,
                bpm=candidate.bpm,
                beat_analysis_status=candidate.beat_analysis_status,
                analysis_summary=(
                    analyzed.model_dump(mode="json", exclude={"windows"})
                    if analyzed is not None
                    else {}
                ),
            )
        )
    timeline_hash = hash_file(timeline_path)
    ledger_hash = hash_file(ledger_path)
    analysis_hash = hash_file(analysis_path) if analysis_path.exists() else None
    context_id = "bgmctx_" + hashlib.sha256(
        f"{timeline_hash}:{ledger_hash}:{analysis_hash or 'no-analysis'}".encode()
    ).hexdigest()[:20]
    return BgmRecommendationContext(
        context_id=context_id,
        project_id=project_id,
        timeline_id=timeline.timeline_id,
        timeline_ref=timeline_path.relative_to(root).as_posix(),
        timeline_fingerprint=timeline_hash,
        proposal_id=timeline.proposal_id.value,
        target_duration=timeline.actual_duration,
        timeline_music_status=timeline.music_plan.status.value,
        proposal_sound_structure=timeline.music_plan.proposal_sound_structure,
        candidate_ledger_fingerprint=ledger_hash,
        analysis_ref=analysis_path.relative_to(root).as_posix() if analysis_path.exists() else None,
        analysis_fingerprint=analysis_hash,
        candidates=candidates,
        recommendation_policy=[
            "rank only existing candidates",
            "do not perform selection",
            "preserve mixed-audio contamination risk",
            "do not fabricate BPM or beat grids",
            "do not use network or paid APIs in the CLI",
        ],
    )


def quarantine_bgm_recommendation_candidate(*, root: Path, candidate_path: Path) -> QuarantinedBgmRecommendation:
    if candidate_path.is_symlink():
        raise BgmRecommendationError("BGM recommendation candidate must not be a symlink", code="bgm_recommendation_symlink_forbidden")
    if not candidate_path.exists():
        raise BgmRecommendationError("BGM recommendation candidate does not exist", code="bgm_recommendation_missing")
    if not candidate_path.is_file():
        raise BgmRecommendationError("BGM recommendation candidate must be a regular file", code="bgm_recommendation_not_file")
    byte_count = candidate_path.stat().st_size
    if byte_count > MAX_BGM_RECOMMENDATION_BYTES:
        raise BgmRecommendationError("BGM recommendation candidate is too large", code="bgm_recommendation_too_large")
    raw = candidate_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    quarantine_path = root / WORKSPACE_DIR / "quarantine" / "bgm_recommendations" / f"host_agent_{digest}.json"
    quarantine_path.parent.mkdir(parents=True, exist_ok=True)
    if not quarantine_path.exists():
        tmp = quarantine_path.with_suffix(".json.tmp")
        tmp.write_bytes(raw)
        tmp.replace(quarantine_path)
    return QuarantinedBgmRecommendation(
        path=quarantine_path,
        ref=quarantine_path.relative_to(root).as_posix(),
        sha256=digest,
        byte_count=byte_count,
        raw_bytes=raw,
    )


def import_bgm_recommendation_candidate(*, root: Path, project_id: str, candidate_path: Path) -> tuple[Path, Path, BgmRecommendationValidationReport]:
    quarantined = quarantine_bgm_recommendation_candidate(root=root, candidate_path=candidate_path)
    recommendation = parse_bgm_recommendation_set(quarantined)
    context_path = root / WORKSPACE_DIR / "data" / "bgm_recommendation_context.json"
    if not context_path.exists():
        raise BgmRecommendationError("BGM recommendation context is missing", code="bgm_recommendation_context_missing", quarantine_ref=quarantined.ref)
    context = BgmRecommendationContext.model_validate_json(context_path.read_text(encoding="utf-8"))
    validation = validate_bgm_recommendation_set(recommendation=recommendation, context=context, project_id=project_id)
    validation_path = root / WORKSPACE_DIR / "data" / "bgm_recommendation_validation.json"
    recommendation_path = root / WORKSPACE_DIR / "data" / "bgm_recommendations.json"
    review_path = root / "output" / "bgm_recommendation_review.md"
    atomic_json(validation_path, validation.model_dump(mode="json"))
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(render_bgm_recommendation_review(validation, recommendation) + "\n", encoding="utf-8")
    if not validation.valid:
        raise BgmRecommendationError("BGM recommendation candidate failed validation", code="bgm_recommendation_validation_failed", quarantine_ref=quarantined.ref)
    atomic_json(recommendation_path, recommendation.model_dump(mode="json"))
    return recommendation_path, review_path, validation


def select_bgm_recommendation_for_fit(
    *,
    root: Path,
    project_id: str,
    recommendation_id: str | None = None,
    rank: int | None = None,
) -> tuple[BgmRecommendationSelection, BgmRecommendationItem]:
    if bool(recommendation_id) == bool(rank):
        raise BgmRecommendationError(
            "provide exactly one of --recommendation-id or --rank",
            code="bgm_recommendation_selection_invalid",
        )
    recommendation_path = root / WORKSPACE_DIR / "data" / "bgm_recommendations.json"
    context_path = root / WORKSPACE_DIR / "data" / "bgm_recommendation_context.json"
    if not recommendation_path.exists():
        raise BgmRecommendationError(
            "BGM recommendation selection requires canonical bgm_recommendations.json",
            code="bgm_recommendation_missing",
        )
    if not context_path.exists():
        raise BgmRecommendationError(
            "BGM recommendation selection requires current bgm_recommendation_context.json",
            code="bgm_recommendation_context_missing",
        )
    recommendation = BgmRecommendationSet.model_validate_json(
        recommendation_path.read_text(encoding="utf-8")
    )
    context = BgmRecommendationContext.model_validate_json(
        context_path.read_text(encoding="utf-8")
    )
    if recommendation.project_id != project_id or context.project_id != project_id:
        raise BgmRecommendationError(
            "BGM recommendation selection project_id mismatch",
            code="bgm_recommendation_project_mismatch",
        )
    if recommendation.context_id != context.context_id:
        raise BgmRecommendationError(
            "BGM recommendation selection context is stale",
            code="bgm_recommendation_context_mismatch",
        )
    if recommendation.selection_performed or recommendation.automatic_selection_performed:
        raise BgmRecommendationError(
            "canonical recommendations must not already claim selection",
            code="bgm_recommendation_selection_policy_violation",
        )
    if recommendation_id:
        item = next(
            (
                value
                for value in recommendation.recommendations
                if value.recommendation_id == recommendation_id
            ),
            None,
        )
        selection_source = "recommendation_id"
    else:
        item = next(
            (value for value in recommendation.recommendations if value.rank == rank),
            None,
        )
        selection_source = "rank"
    if item is None:
        raise BgmRecommendationError(
            "BGM recommendation selection target was not found",
            code="bgm_recommendation_selection_not_found",
        )
    candidate_ids = {candidate.music_candidate_id for candidate in context.candidates}
    if item.music_candidate_id not in candidate_ids:
        raise BgmRecommendationError(
            f"selected recommendation references unknown candidate: {item.music_candidate_id}",
            code="bgm_recommendation_unknown_candidate",
        )
    recommendation_hash = hash_file(recommendation_path)
    context_hash = hash_file(context_path)
    selection_key = (
        f"{recommendation.recommendation_set_id}:{context.context_id}:"
        f"{item.recommendation_id}:{item.music_candidate_id}:{recommendation_hash}:{context_hash}"
    )
    selection = BgmRecommendationSelection(
        selection_id="bgmsel_" + hashlib.sha256(selection_key.encode()).hexdigest()[:20],
        project_id=project_id,
        recommendation_set_id=recommendation.recommendation_set_id,
        recommendation_ref=recommendation_path.relative_to(root).as_posix(),
        recommendation_fingerprint=recommendation_hash,
        context_id=context.context_id,
        context_ref=context_path.relative_to(root).as_posix(),
        context_fingerprint=context_hash,
        recommendation_id=item.recommendation_id,
        selected_rank=item.rank,
        music_candidate_id=item.music_candidate_id,
        selection_source=selection_source,
        fit_rationale=item.fit_rationale,
        timing_rationale=item.timing_rationale,
        risk_notes=item.risk_notes,
        evidence_refs=item.evidence_refs,
        confidence=item.confidence,
    )
    selection_path = root / WORKSPACE_DIR / "data" / "bgm_recommendation_selection.json"
    review_path = root / "output" / "bgm_recommendation_selection_review.md"
    atomic_json(selection_path, selection.model_dump(mode="json"))
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(render_bgm_recommendation_selection_review(selection) + "\n", encoding="utf-8")
    return selection, item


def parse_bgm_recommendation_set(candidate: QuarantinedBgmRecommendation) -> BgmRecommendationSet:
    try:
        text = candidate.raw_bytes.decode("utf-8")
        payload = json.loads(text)
        return BgmRecommendationSet.model_validate(payload)
    except UnicodeDecodeError as exc:
        raise BgmRecommendationError("BGM recommendation candidate must be UTF-8 JSON", code="bgm_recommendation_invalid_utf8", quarantine_ref=candidate.ref) from exc
    except json.JSONDecodeError as exc:
        raise BgmRecommendationError(f"BGM recommendation candidate is invalid JSON: {exc.msg}", code="bgm_recommendation_invalid_json", quarantine_ref=candidate.ref) from exc
    except ValidationError as exc:
        raise BgmRecommendationError(f"BGM recommendation candidate schema is invalid: {exc}", code="bgm_recommendation_schema_invalid", quarantine_ref=candidate.ref) from exc


def validate_bgm_recommendation_set(*, recommendation: BgmRecommendationSet, context: BgmRecommendationContext, project_id: str) -> BgmRecommendationValidationReport:
    issues: list[BgmRecommendationValidationIssue] = []
    candidate_ids = {item.music_candidate_id for item in context.candidates}
    if recommendation.project_id != project_id or recommendation.project_id != context.project_id:
        issues.append(issue("bgm_recommendation_project_mismatch", "error", "project_id does not match context"))
    if recommendation.context_id != context.context_id:
        issues.append(issue("bgm_recommendation_context_mismatch", "error", "context_id does not match current context"))
    method = recommendation.method.lower().replace("-", "_").replace(" ", "_")
    if not any(token in method for token in ("host_agent", "codex", "chatgpt", "local_model", "third_party_tool")):
        issues.append(issue("bgm_recommendation_method_invalid", "error", "method must identify host Agent, local model, or third-party tool"))
    for item in recommendation.recommendations:
        if item.music_candidate_id not in candidate_ids:
            issues.append(issue("bgm_recommendation_unknown_candidate", "error", f"unknown music_candidate_id: {item.music_candidate_id}"))
        if not item.evidence_refs:
            issues.append(issue("bgm_recommendation_missing_evidence", "warning", f"{item.recommendation_id} has no evidence_refs"))
    errors = sum(item.severity == "error" for item in issues)
    warnings = sum(item.severity == "warning" for item in issues)
    return BgmRecommendationValidationReport(
        recommendation_ref=".artist-portrait/data/bgm_recommendations.json",
        context_ref=".artist-portrait/data/bgm_recommendation_context.json",
        candidate_count=len(candidate_ids),
        recommendation_count=len(recommendation.recommendations),
        issue_count=len(issues),
        error_count=errors,
        warning_count=warnings,
        issues=issues,
        valid=errors == 0,
    )


def render_bgm_recommendation_review(validation: BgmRecommendationValidationReport, recommendation: BgmRecommendationSet) -> str:
    lines = [
        "# BGM Recommendation Review",
        "",
        "This review validates imported BGM recommendations. It does not select music, fit music, render media, call models, or access the network.",
        "",
        f"- Valid: `{str(validation.valid).lower()}`",
        f"- Recommendations: `{validation.recommendation_count}`",
        f"- Issues: `{validation.issue_count}`",
        "",
    ]
    for item in sorted(recommendation.recommendations, key=lambda value: value.rank):
        lines.extend([
            f"## {item.rank}. `{item.music_candidate_id}`",
            "",
            f"- Recommendation ID: `{item.recommendation_id}`",
            f"- Confidence: `{item.confidence:.3f}`",
            f"- Fit rationale: {item.fit_rationale}",
            f"- Timing rationale: {item.timing_rationale}",
            "",
        ])
    if validation.issues:
        lines.append("## Issues\n")
        for item in validation.issues:
            lines.extend([f"- `{item.code}` `{item.severity}`: {item.detail}"])
    return "\n".join(lines)


def render_bgm_recommendation_selection_review(selection: BgmRecommendationSelection) -> str:
    lines = [
        "# BGM Recommendation Selection Review",
        "",
        "This review records an explicit user selection from imported BGM recommendations.",
        "It triggers fitting for the selected candidate but does not automatically select music, call models, access the network, or render media.",
        "",
        f"- Selection ID: `{selection.selection_id}`",
        f"- Recommendation set: `{selection.recommendation_set_id}`",
        f"- Recommendation ID: `{selection.recommendation_id}`",
        f"- Selected rank: `{selection.selected_rank}`",
        f"- Candidate: `{selection.music_candidate_id}`",
        f"- Selection source: `{selection.selection_source}`",
        f"- Explicit user selection: `{str(selection.explicit_user_selection).lower()}`",
        f"- Automatic selection: `{str(selection.automatic_selection_performed).lower()}`",
        f"- Fit triggered: `{str(selection.fit_triggered).lower()}`",
        f"- Fit ref: `{selection.bgm_fit_ref}`",
        f"- Confidence: `{selection.confidence:.3f}`",
        "",
        "## Rationale",
        "",
        f"- Fit: {selection.fit_rationale}",
        f"- Timing: {selection.timing_rationale}",
        "",
    ]
    if selection.risk_notes:
        lines.append("## Risk Notes\n")
        for note in selection.risk_notes:
            lines.append(f"- {note}")
        lines.append("")
    if selection.evidence_refs:
        lines.append("## Evidence Refs\n")
        for ref in selection.evidence_refs:
            lines.append(f"- `{ref}`")
    return "\n".join(lines)


def review_bgm_recommendation_fit(
    *,
    root: Path,
    project_id: str,
    bgm_issues: list[str] | None = None,
) -> tuple[Path, Path, BgmRecommendationFitReview]:
    data_dir = root / WORKSPACE_DIR / "data"
    selection_path = data_dir / "bgm_recommendation_selection.json"
    recommendation_path = data_dir / "bgm_recommendations.json"
    context_path = data_dir / "bgm_recommendation_context.json"
    fit_path = data_dir / "bgm_fit.json"
    timeline_path = root / "output" / "timeline_draft.json"
    preview_path = data_dir / "preview_manifest.json"
    final_path = data_dir / "final_export_manifest.json"
    issues: list[BgmRecommendationValidationIssue] = [
        issue("bgm_fit_review_existing_bgm_issue", "error", value)
        for value in (bgm_issues or [])
    ]
    selection: BgmRecommendationSelection | None = None
    recommendation: BgmRecommendationSet | None = None
    context: BgmRecommendationContext | None = None
    fit: BgmFitPlan | None = None
    timeline: TimelineDraft | None = None
    selection_exists = selection_path.exists()
    if not selection_exists:
        severity = "warning" if fit_path.exists() else "error"
        issues.append(issue("bgm_recommendation_selection_missing", severity, "recommendation selection is missing"))
    else:
        try:
            selection = BgmRecommendationSelection.model_validate_json(selection_path.read_text(encoding="utf-8"))
        except Exception as exc:
            issues.append(issue("bgm_recommendation_selection_invalid", "error", f"selection artifact is invalid: {exc}"))
    if not recommendation_path.exists() and selection_exists:
        issues.append(issue("bgm_recommendation_missing", "error", "canonical BGM recommendations are missing"))
    elif recommendation_path.exists():
        try:
            recommendation = BgmRecommendationSet.model_validate_json(recommendation_path.read_text(encoding="utf-8"))
        except Exception as exc:
            issues.append(issue("bgm_recommendation_invalid", "error", f"recommendation artifact is invalid: {exc}"))
    if not context_path.exists() and selection_exists:
        issues.append(issue("bgm_recommendation_context_missing", "error", "BGM recommendation context is missing"))
    elif context_path.exists():
        try:
            context = BgmRecommendationContext.model_validate_json(context_path.read_text(encoding="utf-8"))
        except Exception as exc:
            issues.append(issue("bgm_recommendation_context_invalid", "error", f"context artifact is invalid: {exc}"))
    if not fit_path.exists():
        issues.append(issue("bgm_fit_missing", "error", "BGM fit plan is missing"))
    else:
        try:
            fit = BgmFitPlan.model_validate_json(fit_path.read_text(encoding="utf-8"))
        except Exception as exc:
            issues.append(issue("bgm_fit_invalid", "error", f"BGM fit plan is invalid: {exc}"))
    if not timeline_path.exists():
        issues.append(issue("timeline_missing", "error", "timeline draft is missing"))
    else:
        try:
            timeline = TimelineDraft.model_validate_json(timeline_path.read_text(encoding="utf-8"))
        except Exception as exc:
            issues.append(issue("timeline_invalid", "error", f"timeline draft is invalid: {exc}"))
    if selection is not None:
        if selection.project_id != project_id:
            issues.append(issue("selection_project_mismatch", "error", "selection project_id does not match project"))
        if not selection.explicit_user_selection or selection.automatic_selection_performed:
            issues.append(issue("selection_not_explicit", "error", "selection must be explicit and non-automatic"))
        if hash_file(selection_path) == "":
            issues.append(issue("selection_fingerprint_unavailable", "error", "selection fingerprint is unavailable"))
    if selection is not None and recommendation is not None:
        if recommendation.project_id != project_id:
            issues.append(issue("recommendation_project_mismatch", "error", "recommendation project_id does not match project"))
        if selection.recommendation_set_id != recommendation.recommendation_set_id:
            issues.append(issue("recommendation_set_mismatch", "error", "selection points to a different recommendation set"))
        if selection.recommendation_fingerprint != hash_file(recommendation_path):
            issues.append(issue("recommendation_stale", "error", "selection recommendation fingerprint is stale"))
        item = next((value for value in recommendation.recommendations if value.recommendation_id == selection.recommendation_id), None)
        if item is None:
            issues.append(issue("recommendation_item_missing", "error", "selected recommendation no longer exists"))
        elif item.music_candidate_id != selection.music_candidate_id or item.rank != selection.selected_rank:
            issues.append(issue("recommendation_item_changed", "error", "selected recommendation candidate or rank changed"))
        if recommendation.selection_performed or recommendation.automatic_selection_performed:
            issues.append(issue("recommendation_policy_violation", "error", "recommendation set must not claim selection"))
    if selection is not None and context is not None:
        if selection.context_id != context.context_id:
            issues.append(issue("context_id_mismatch", "error", "selection context_id does not match current context"))
        if selection.context_fingerprint != hash_file(context_path):
            issues.append(issue("context_stale", "error", "selection context fingerprint is stale"))
        context_candidates = {candidate.music_candidate_id for candidate in context.candidates}
        if selection.music_candidate_id not in context_candidates:
            issues.append(issue("context_candidate_missing", "error", "selected candidate is missing from recommendation context"))
    if selection is not None and fit is not None:
        if fit.project_id != project_id:
            issues.append(issue("fit_project_mismatch", "error", "BGM fit project_id does not match project"))
        if fit.music_candidate_id != selection.music_candidate_id:
            issues.append(issue("fit_candidate_mismatch", "error", "BGM fit candidate does not match selected recommendation"))
    if fit is not None and timeline is not None:
        timeline_hash = hash_file(timeline_path)
        if fit.timeline_id != timeline.timeline_id:
            issues.append(issue("fit_timeline_id_mismatch", "error", "BGM fit timeline_id does not match current timeline"))
        if fit.timeline_fingerprint != timeline_hash:
            issues.append(issue("fit_timeline_stale", "error", "BGM fit timeline fingerprint is stale"))
        if timeline.music_plan.status.value == "fitted":
            if timeline.music_plan.candidate_id != fit.music_candidate_id or timeline.music_plan.fit_ref != ".artist-portrait/data/bgm_fit.json":
                issues.append(issue("timeline_music_binding_mismatch", "error", "timeline music plan does not bind the current BGM fit"))
        else:
            issues.append(issue("timeline_music_not_fitted", "warning", "timeline music plan is not marked fitted"))
    beat_state = _evidence_state(root, fit.beat_grid_ref, fit.beat_grid_fingerprint) if fit else "not_checked"
    analysis_state = _evidence_state(root, fit.analysis_ref, fit.analysis_fingerprint) if fit else "not_checked"
    if beat_state == "stale":
        issues.append(issue("beat_grid_stale", "error", "BGM fit beat-grid evidence fingerprint is stale"))
    if analysis_state == "stale":
        issues.append(issue("bgm_analysis_stale", "error", "BGM fit analysis evidence fingerprint is stale"))
    fit_hash = hash_file(fit_path) if fit_path.exists() else None
    preview_state = _media_output_state(preview_path, PreviewRenderManifest, fit_hash)
    final_state = _media_output_state(final_path, FinalExportManifest, fit_hash)
    if fit is not None and preview_state == "missing":
        issues.append(issue("preview_missing_after_fit", "warning", "preview has not been rendered for the current selected BGM fit"))
    if fit is not None and final_state == "missing":
        issues.append(issue("final_export_missing_after_fit", "warning", "final export has not been rendered for the current selected BGM fit"))
    if preview_state == "stale":
        issues.append(issue("preview_stale_after_fit", "warning", "preview was rendered against a different BGM fit fingerprint"))
    if final_state == "stale":
        issues.append(issue("final_export_stale_after_fit", "warning", "final export was rendered against a different BGM fit fingerprint"))
    errors = sum(value.severity == "error" for value in issues)
    warnings = sum(value.severity == "warning" for value in issues)
    status = "failed" if errors else "warning" if warnings else "passed"
    review_key = ":".join([
        project_id,
        hash_file(selection_path) if selection_path.exists() else "missing-selection",
        fit_hash or "missing-fit",
        hash_file(timeline_path) if timeline_path.exists() else "missing-timeline",
    ])
    report = BgmRecommendationFitReview(
        review_id="bgmfitrev_" + hashlib.sha256(review_key.encode()).hexdigest()[:20],
        project_id=project_id,
        status=status,
        selection_id=selection.selection_id if selection else None,
        selection_fingerprint=hash_file(selection_path) if selection_path.exists() else None,
        recommendation_id=selection.recommendation_id if selection else None,
        recommendation_fingerprint=hash_file(recommendation_path) if recommendation_path.exists() else None,
        context_id=context.context_id if context else None,
        context_fingerprint=hash_file(context_path) if context_path.exists() else None,
        fit_id=fit.fit_id if fit else None,
        fit_fingerprint=fit_hash,
        timeline_id=timeline.timeline_id if timeline else None,
        timeline_fingerprint=hash_file(timeline_path) if timeline_path.exists() else None,
        music_candidate_id=selection.music_candidate_id if selection else fit.music_candidate_id if fit else None,
        selected_rank=selection.selected_rank if selection else None,
        fit_control_policy=fit.controls.control_policy if fit else None,
        requested_fit_mode=fit.controls.requested_fit_mode if fit else None,
        ducking_enabled=fit.controls.ducking_enabled if fit else None,
        beat_alignment_requested=fit.controls.beat_alignment_requested if fit else None,
        preview_state=preview_state,
        final_export_state=final_state,
        beat_evidence_status=beat_state,
        analysis_evidence_status=analysis_state,
        issue_count=len(issues),
        error_count=errors,
        warning_count=warnings,
        issues=issues,
    )
    review_json = data_dir / "bgm_fit_review.json"
    review_md = root / "output" / "bgm_fit_review.md"
    atomic_json(review_json, report.model_dump(mode="json"))
    review_md.parent.mkdir(parents=True, exist_ok=True)
    review_md.write_text(render_bgm_fit_review(report) + "\n", encoding="utf-8")
    return review_json, review_md, report


def render_bgm_fit_review(report: BgmRecommendationFitReview) -> str:
    lines = [
        "# BGM Recommendation Fit Review",
        "",
        "This review checks whether an explicit BGM recommendation selection, current fit plan, timeline, evidence, preview, and final export agree.",
        "It does not select music, move edit points, render media, call models, or access the network.",
        "",
        f"- Status: `{report.status}`",
        f"- Review ID: `{report.review_id}`",
        f"- Selection ID: `{report.selection_id or 'missing'}`",
        f"- Recommendation ID: `{report.recommendation_id or 'missing'}`",
        f"- Candidate: `{report.music_candidate_id or 'missing'}`",
        f"- BGM fit: `{report.fit_id or 'missing'}`",
        f"- Fit control policy: `{report.fit_control_policy or 'missing'}`",
        f"- Requested fit mode: `{report.requested_fit_mode or 'missing'}`",
        f"- Ducking enabled: `{str(report.ducking_enabled).lower() if report.ducking_enabled is not None else 'missing'}`",
        f"- Beat alignment requested: `{str(report.beat_alignment_requested).lower() if report.beat_alignment_requested is not None else 'missing'}`",
        f"- Timeline: `{report.timeline_id or 'missing'}`",
        f"- Preview state: `{report.preview_state}`",
        f"- Final export state: `{report.final_export_state}`",
        f"- Beat evidence: `{report.beat_evidence_status}`",
        f"- Analysis evidence: `{report.analysis_evidence_status}`",
        f"- Issues: `{report.issue_count}`",
        "",
    ]
    if report.issues:
        lines.append("## Issues\n")
        for item in report.issues:
            lines.append(f"- `{item.code}` `{item.severity}`: {item.detail}")
    return "\n".join(lines)


def _evidence_state(root: Path, ref: str | None, fingerprint: str | None) -> str:
    if not ref:
        return "unavailable"
    path = root / ref
    if not path.exists() or not fingerprint:
        return "stale"
    return "bound" if hash_file(path) == fingerprint else "stale"


def _media_output_state(path: Path, model: type, fit_fingerprint: str | None) -> str:
    if fit_fingerprint is None:
        return "not_checked"
    if not path.exists():
        return "missing"
    try:
        manifest = model.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception:
        return "stale"
    return "current" if getattr(manifest, "bgm_fit_fingerprint", None) == fit_fingerprint else "stale"


def bgm_recommendation_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        payload = BgmRecommendationSet.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"exists": True, "valid": False, "error": f"invalid BgmRecommendationSet JSON: {exc}"}
    return {
        "exists": True,
        "valid": True,
        "recommendation_set_id": payload.recommendation_set_id,
        "recommendation_count": len(payload.recommendations),
        "selection_performed": payload.selection_performed,
    }


def bgm_recommendation_selection_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        payload = BgmRecommendationSelection.model_validate_json(
            path.read_text(encoding="utf-8")
        )
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": f"invalid BgmRecommendationSelection JSON: {exc}",
        }
    return {
        "exists": True,
        "valid": True,
        "selection_id": payload.selection_id,
        "recommendation_id": payload.recommendation_id,
        "selected_rank": payload.selected_rank,
        "candidate_id": payload.music_candidate_id,
        "explicit_user_selection": payload.explicit_user_selection,
        "automatic_selection_performed": payload.automatic_selection_performed,
        "fit_triggered": payload.fit_triggered,
    }


def bgm_recommendation_doctor_issues(root: Path, project_path: str) -> list[dict[str, str]]:
    summary = bgm_recommendation_summary(root / ".artist-portrait/data/bgm_recommendations.json")
    issues = []
    if summary.get("valid") is False:
        issues.append(
            {
                "code": "bgm_recommendations_invalid",
                "severity": "error",
                "detail": str(summary.get("error")),
                "next_action": f"rerun artist-portrait bgm recommend --project {project_path}",
            }
        )
    selection = bgm_recommendation_selection_summary(
        root / ".artist-portrait/data/bgm_recommendation_selection.json"
    )
    if selection.get("valid") is False:
        issues.append(
            {
                "code": "bgm_recommendation_selection_invalid",
                "severity": "error",
                "detail": str(selection.get("error")),
                "next_action": f"rerun artist-portrait bgm select --project {project_path} --recommendation-id <id>",
            }
        )
    return issues


def issue(code: str, severity: str, detail: str) -> BgmRecommendationValidationIssue:
    return BgmRecommendationValidationIssue(code=code, severity=severity, detail=detail)


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
