from __future__ import annotations

import hashlib
import json
from pathlib import Path

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.final_export import FinalExportManifest, FinalExportValidationReport
from artist_portrait_editor.models.first_cut_review import FirstCutSelfReview
from artist_portrait_editor.models.nle_roundtrip import NleRoundTripPackage
from artist_portrait_editor.models.publishability import PublishabilityIssue, PublishabilityReport, VersionPublishability
from artist_portrait_editor.models.second_cut_render import SecondCutRender
from artist_portrait_editor.models.state import ActiveMode, OverallStatus, StepLedgerEntry, StepStatus
from artist_portrait_editor.models.version_review import ReviewedVersion, VersionReview
from artist_portrait_editor.run_records import environment_snapshot, new_run_id, utc_now, write_json
from artist_portrait_editor.workspace_errors import WorkspacePrerequisiteError
from artist_portrait_editor.workspace_state import atomic_write_text, load_state, project_root, save_state, write_run_report


class PublishabilityError(RuntimeError):
    pass


TIER_ORDER = {
    "unusable": 0,
    "manual_refinement_required": 1,
    "previewable": 2,
    "publishable": 3,
}

DOMAIN_MAP = {
    "opening": "hook",
    "middle_pacing": "information",
    "emotion": "emotion",
    "bgm_voice": "bgm_voice",
    "source_audio_bgm": "bgm_voice",
    "text": "text",
    "ending": "ending",
    "transitions": "transitions",
    "composition": "composition",
    "technical_delivery": "technical",
    "duration_structure": "platform",
    "hook": "hook",
    "emotional_arc": "emotion",
    "information_density": "information",
    "bgm_conflict": "bgm_voice",
    "text_burden": "text",
    "ending_strength": "ending",
    "platform_fit": "platform",
    "semantic_continuity": "information",
}


def build_publishability_workspace(
    project_path: Path,
) -> tuple[Path, Path, PublishabilityReport, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("publishability requires init to complete first")

    data = root / WORKSPACE_DIR / DATA_DIR
    evidence_paths = {
        "version_review": data / "version_review.json",
        "final_manifest": data / "final_export_manifest.json",
        "final_validation": data / "final_export_validation.json",
        "first_cut_review": data / "first_cut_self_review.json",
        "second_cut_render": data / "second_cut_render.json",
        "nle_roundtrip": data / "nle_roundtrip.json",
    }
    version_path = evidence_paths["version_review"]
    if not version_path.exists():
        raise WorkspacePrerequisiteError(
            "publishability requires version-review to complete first"
        )

    review = VersionReview.model_validate_json(version_path.read_text(encoding="utf-8"))
    if review.project_id != config.project.id:
        raise PublishabilityError("version review project_id mismatches project")

    manifest = _read(evidence_paths["final_manifest"], FinalExportManifest)
    final = _read(evidence_paths["final_validation"], FinalExportValidationReport)
    first = _read(evidence_paths["first_cut_review"], FirstCutSelfReview)
    second = _read(evidence_paths["second_cut_render"], SecondCutRender)
    nle = _read(evidence_paths["nle_roundtrip"], NleRoundTripPackage)
    canonical_media_current = bool(
        manifest
        and final
        and (root / manifest.output_ref).exists()
        and _fingerprint(root / manifest.output_ref) == manifest.output_content_hash
    )
    canonical_record_current = bool(
        manifest
        and final
        and manifest.project_id == config.project.id
        and manifest.timeline_fingerprint == final.timeline_fingerprint
        and manifest.output_ref == final.export_ref
        and (not first or first.final_hash == manifest.output_content_hash)
    )
    second_media_current = bool(
        second
        and (root / second.output_ref).exists()
        and _fingerprint(root / second.output_ref) == second.output_hash
    )
    second_record_current = bool(
        second
        and any(
            version.version_kind == "rendered_second_cut"
            and version.artifact_fingerprint == _fingerprint(evidence_paths["second_cut_render"])
            for version in review.versions
        )
    )
    versions = [
        evaluate_version_publishability(
            version,
            final,
            first,
            second,
            nle,
            canonical_media_current=canonical_media_current,
            canonical_record_current=canonical_record_current,
            second_media_current=second_media_current,
            second_record_current=second_record_current,
        )
        for version in review.versions
    ]

    highest_score = max(TIER_ORDER[version.tier] for version in versions)
    highest_tier = next(
        tier for tier, score in TIER_ORDER.items() if score == highest_score
    )
    highest_ids = [
        version.version_id for version in versions if version.tier == highest_tier
    ]
    tier_counts = {
        tier: sum(version.tier == tier for version in versions) for tier in TIER_ORDER
    }
    warnings = []
    if tier_counts["publishable"] == 0:
        warnings.append("no current version has sufficient evidence for publishable status")
    if len(highest_ids) > 1:
        warnings.append(
            "multiple versions share the highest available tier; explicit goal-based "
            "selection remains required"
        )

    report_key = "|".join(
        [config.project.id, _fingerprint(version_path)]
        + [f"{version.version_id}:{version.tier}" for version in versions]
    )
    report = PublishabilityReport(
        report_id="publishability_" + hashlib.sha256(report_key.encode()).hexdigest()[:20],
        project_id=config.project.id,
        status="warning" if warnings else "ready",
        version_review_id=review.review_id,
        version_review_fingerprint=_fingerprint(version_path),
        version_count=len(versions),
        tier_counts=tier_counts,
        highest_available_tier=highest_tier,
        highest_tier_version_ids=highest_ids,
        versions=versions,
        warnings=warnings,
    )

    json_path = data / "publishability.json"
    md_path = root / "output" / "publishability.md"
    atomic_write_text(
        json_path,
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
    )
    atomic_write_text(md_path, render_publishability(report))

    run_id = new_run_id()
    step_status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    refs = [json_path.relative_to(root).as_posix(), md_path.relative_to(root).as_posix()]
    state.steps["publishability"] = StepLedgerEntry(
        status=step_status,
        input_fingerprint=_fingerprint_many(list(evidence_paths.values())),
        output_refs=refs,
        last_run_id=run_id,
        warnings=warnings,
    )
    state.active_mode = ActiveMode.creative
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready
    run_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / "command.json", {"command": "publishability", "project": str(project_path)})
    write_json(run_dir / "environment.json", environment_snapshot())
    write_json(
        run_dir / "step_result.json",
        {
            "step": "publishability",
            "status": step_status.value,
            "output_refs": refs,
            "highest_available_tier": highest_tier,
            "selected_version_id": None,
            "warnings": warnings,
        },
    )
    save_state(root, state)
    write_run_report(root / config.paths.output_dir, state, warnings)
    return json_path, md_path, report, warnings


def evaluate_version_publishability(
    version: ReviewedVersion,
    final: FinalExportValidationReport | None,
    first: FirstCutSelfReview | None,
    second: SecondCutRender | None,
    nle: NleRoundTripPackage | None,
    *,
    canonical_media_current: bool = True,
    canonical_record_current: bool = True,
    second_media_current: bool = True,
    second_record_current: bool = True,
) -> VersionPublishability:
    issues: list[PublishabilityIssue] = []
    satisfied: list[str] = []

    def add_issue(domain, severity, disposition, detail, refs, next_action):
        issues.append(
            PublishabilityIssue(
                issue_id=f"pub_{version.version_id}_{len(issues) + 1:02d}",
                domain=domain,
                severity=severity,
                disposition=disposition,
                detail=detail,
                evidence_refs=refs,
                next_action=next_action,
            )
        )

    media_present = version.evidence_level == "rendered_media"
    technical_valid = version.media_valid if media_present else None
    aesthetic_review_present = False

    if version.version_kind == "canonical_timeline":
        media_present = bool(final and canonical_media_current)
        technical_valid = final.valid if final else None
        if final and not canonical_media_current:
            add_issue(
                "media", "critical", "blocks_use",
                "canonical final media is missing from the validation-bound output path",
                [final.export_ref, ".artist-portrait/data/final_export_validation.json"],
                "Rerun final export, first-cut-review, version-review, and publishability.",
            )
        if final and not canonical_record_current:
            add_issue(
                "evidence", "critical", "blocks_use",
                "final manifest, validation, timeline, or first-cut review bindings are stale",
                [
                    ".artist-portrait/data/final_export_manifest.json",
                    ".artist-portrait/data/final_export_validation.json",
                    version.artifact_ref,
                ],
                "Rerun final export, first-cut-review, version-review, and publishability.",
            )
        if final and final.timeline_fingerprint != version.artifact_fingerprint:
            add_issue(
                "media", "critical", "blocks_use",
                "canonical final validation is stale relative to the reviewed timeline",
                [".artist-portrait/data/final_export_validation.json", version.artifact_ref],
                "Rerun final export, first-cut-review, version-review, and publishability.",
            )
        if final and final.valid:
            satisfied.append("canonical final passes current technical validation")
        elif final:
            add_issue(
                "technical", "critical", "blocks_use", "canonical final fails technical validation",
                [".artist-portrait/data/final_export_validation.json"], final.recovery_command,
            )
        else:
            add_issue(
                "media", "critical", "blocks_use", "canonical final validation is missing", [],
                "artist-portrait export --project <project.yaml> --profile delivery_1080p",
            )
        aesthetic_review_present = first is not None
        _add_first_cut_issues(first, add_issue, satisfied)
        _add_nle_boundary(nle, add_issue, satisfied)
    elif version.version_kind == "rendered_second_cut":
        media_present = bool(second and version.media_valid and second_media_current)
        technical_valid = version.media_valid if second else None
        aesthetic_review_present = second is not None
        _add_second_cut_issues(
            second, version, add_issue, satisfied,
            second_media_current=second_media_current,
            second_record_current=second_record_current,
        )
    else:
        add_issue(
            "media", "critical", "blocks_use",
            "revision candidate is plan-only and has no playable media",
            [version.artifact_ref],
            "Promote the chosen revision, then rerun preview/final export and version-review.",
        )

    for assessment in version.assessments:
        if assessment.status == "unavailable" or assessment.confidence < 0.5:
            add_issue(
                _map_domain(assessment.domain), "medium", "evidence_gap",
                assessment.finding, assessment.evidence_refs,
                "Perform candidate-specific playback review and regenerate version-review.",
            )
        elif assessment.score is not None and assessment.score < 0.5:
            add_issue(
                _map_domain(assessment.domain), "medium", "requires_refinement",
                assessment.finding, assessment.evidence_refs,
                "Refine this domain, render a new candidate, and compare again.",
            )
        else:
            satisfied.append(f"{assessment.domain} evidence is currently usable")

    blocking_count = sum(
        issue.disposition in {"blocks_use", "blocks_publish"} for issue in issues
    )
    refinement_count = sum(
        issue.disposition == "requires_refinement" for issue in issues
    )
    evidence_gap_count = sum(issue.disposition == "evidence_gap" for issue in issues)
    if (
        any(issue.disposition == "blocks_use" for issue in issues)
        or not media_present
        or technical_valid is False
    ):
        tier = "unusable"
    elif any(issue.disposition == "blocks_publish" for issue in issues):
        tier = "manual_refinement_required"
    elif refinement_count or evidence_gap_count:
        tier = "previewable"
    else:
        tier = "publishable"

    next_commands = []
    for issue in issues:
        if issue.next_action not in next_commands:
            next_commands.append(issue.next_action)
    if not next_commands:
        next_commands.append(
            "Keep this version immutable and complete final human playback approval before publishing."
        )
    scored_confidences = [
        assessment.confidence
        for assessment in version.assessments
        if assessment.score is not None
    ]
    confidence = min(scored_confidences, default=0.0)
    return VersionPublishability(
        version_id=version.version_id,
        version_kind=version.version_kind,
        evidence_level=version.evidence_level,
        tier=tier,
        media_present=media_present,
        technical_valid=technical_valid,
        aesthetic_review_present=aesthetic_review_present,
        ready_for_preview=media_present and technical_valid is not False,
        ready_for_publish=tier == "publishable",
        issue_count=len(issues),
        blocking_issue_count=blocking_count,
        refinement_issue_count=refinement_count,
        evidence_gap_count=evidence_gap_count,
        issues=issues,
        satisfied_requirements=sorted(set(satisfied)),
        next_commands=next_commands,
        confidence=confidence,
    )


def _add_first_cut_issues(first, add_issue, satisfied):
    if not first:
        add_issue(
            "evidence", "high", "blocks_publish", "first-cut aesthetic self-review is missing", [],
            "artist-portrait first-cut-review --project <project.yaml>",
        )
        return
    for domain in first.domains:
        if domain.status == "usable" and domain.severity in {"none", "low"}:
            continue
        disposition = (
            "blocks_publish" if domain.severity in {"high", "critical"}
            else "requires_refinement"
        )
        add_issue(
            _map_domain(domain.domain),
            domain.severity if domain.severity != "none" else "low",
            disposition,
            domain.diagnosis,
            domain.evidence_refs,
            domain.required_change,
        )
    if first.publishability != "publishable":
        add_issue(
            "evidence", "high", "blocks_publish",
            f"first-cut self review is {first.publishability} at maturity {first.maturity_score:.2f}",
            [".artist-portrait/data/first_cut_self_review.json"],
            "artist-portrait second-cut-render --project <project.yaml> --option-id <short|standard|extended>",
        )
    else:
        satisfied.append("host-reviewed first cut is publishable")


def _add_second_cut_issues(
    second, version, add_issue, satisfied, *, second_media_current, second_record_current
):
    if not second:
        add_issue(
            "media", "critical", "blocks_use", "rendered second-cut evidence is missing", [],
            "artist-portrait second-cut-render --project <project.yaml> --option-id <id>",
        )
        return
    if not second_record_current:
        add_issue(
            "evidence", "critical", "blocks_use",
            "version review is stale relative to the current second-cut render record",
            [version.artifact_ref, ".artist-portrait/data/second_cut_render.json"],
            "Rerun version-review and publishability.",
        )
    if not second_media_current:
        add_issue(
            "media", "critical", "blocks_use",
            "second-cut media is missing or its hash no longer matches the render record",
            [second.output_ref, ".artist-portrait/data/second_cut_render.json"],
            "Rerun second-cut-render, version-review, and publishability.",
        )
    for comparison in second.comparisons:
        if comparison.status not in {"unresolved", "regressed"}:
            continue
        add_issue(
            _map_domain(comparison.domain),
            "high" if comparison.status == "regressed" else "medium",
            "blocks_publish" if comparison.status == "regressed" else "requires_refinement",
            comparison.finding,
            comparison.evidence_refs,
            comparison.next_action,
        )
    if second.publishability != "publishable":
        add_issue(
            "evidence", "high", "blocks_publish",
            f"second-cut review is {second.publishability}",
            [".artist-portrait/data/second_cut_render.json"],
            f"Review {second.output_ref} in full and record host aesthetic approval.",
        )
    else:
        satisfied.append("second-cut review marks media publishable")


def _add_nle_boundary(nle, add_issue, satisfied):
    if not nle:
        return
    if nle.unresolved_source_count:
        add_issue(
            "nle", "medium", "evidence_gap",
            "editable NLE delivery has unresolved source bindings; this does not invalidate MP4 playback",
            [".artist-portrait/data/nle_roundtrip.json"],
            "Resolve source hashes/relink and rerun nle-roundtrip when editable delivery is required.",
        )
    elif not nle.roundtrip_verified:
        add_issue(
            "nle", "low", "evidence_gap", "NLE round-trip remains externally unverified",
            [".artist-portrait/data/nle_roundtrip.json"],
            "Complete the NLE import/relink/playback/re-export checklist when editable delivery is required.",
        )
    else:
        satisfied.append("canonical editable NLE round-trip is externally verified")


def render_publishability(report: PublishabilityReport) -> str:
    lines = [
        "# Publishability Tiers", "", f"- Status: `{report.status}`",
        f"- Highest available tier: `{report.highest_available_tier}`",
        f"- Highest-tier versions: `{', '.join(report.highest_tier_version_ids)}`",
        "- Selected version: `none`", "",
        "Technical validity is necessary for use, but never sufficient for aesthetic publishing.",
        "`manual_refinement_required` means playable evidence has a publish blocker; "
        "`previewable` means no known publish blocker remains but refinement or evidence gaps do.",
        "", "## Versions", "",
    ]
    for version in report.versions:
        lines.extend(
            [
                f"### {version.version_id}", "", f"- Tier: `{version.tier}`",
                f"- Media present: `{version.media_present}`",
                f"- Technical valid: `{version.technical_valid}`",
                f"- Ready for preview: `{version.ready_for_preview}`",
                f"- Ready for publish: `{version.ready_for_publish}`",
                f"- Confidence floor: `{version.confidence:.2f}`", "", "Issues:",
            ]
        )
        if not version.issues:
            lines.append("- None.")
        for issue in version.issues:
            lines.append(
                f"- `{issue.severity}` `{issue.domain}` `{issue.disposition}`: "
                f"{issue.detail} Next: {issue.next_action}"
            )
        lines.append("")
    if report.warnings:
        lines.extend(["## Warnings", ""] + [f"- {warning}" for warning in report.warnings] + [""])
    lines.extend(
        [
            "## Guardrails", "", "- Selected version: `none`",
            "- Canonical timeline mutated: `false`", "- Media rendered: `false`",
            "- Automatic version/music selection: `false`",
            "- Model/network access by CLI: `false`", "",
        ]
    )
    return "\n".join(lines)


def _map_domain(domain: str) -> str:
    return DOMAIN_MAP.get(domain, "evidence")


def _read(path: Path, model):
    return model.model_validate_json(path.read_text(encoding="utf-8")) if path.exists() else None


def _fingerprint(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _fingerprint_many(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        if path.exists():
            digest.update(path.read_bytes())
    return "sha256:" + digest.hexdigest()
