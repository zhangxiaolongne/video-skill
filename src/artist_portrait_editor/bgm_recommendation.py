from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from artist_portrait_editor.bgm import load_analysis_report, load_ledger
from artist_portrait_editor.constants import WORKSPACE_DIR
from artist_portrait_editor.media.scanner import hash_file
from artist_portrait_editor.models.bgm_recommendation import (
    BgmRecommendationContext,
    BgmRecommendationContextCandidate,
    BgmRecommendationRequest,
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


def bgm_recommendation_doctor_issues(root: Path, project_path: str) -> list[dict[str, str]]:
    summary = bgm_recommendation_summary(root / ".artist-portrait/data/bgm_recommendations.json")
    if summary.get("valid") is not False:
        return []
    return [
        {
            "code": "bgm_recommendations_invalid",
            "severity": "error",
            "detail": str(summary.get("error")),
            "next_action": f"rerun artist-portrait bgm recommend --project {project_path}",
        }
    ]


def issue(code: str, severity: str, detail: str) -> BgmRecommendationValidationIssue:
    return BgmRecommendationValidationIssue(code=code, severity=severity, detail=detail)


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
