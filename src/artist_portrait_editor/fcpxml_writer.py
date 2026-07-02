from __future__ import annotations

import hashlib
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from artist_portrait_editor.constants import DATA_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.fcpxml import (
    FcpxmlDraft,
    FcpxmlDraftClip,
    FcpxmlDraftMarker,
    FcpxmlImportReview,
    FcpxmlImportReviewCandidate,
    FcpxmlRepairApprovalRecord,
    FcpxmlRepairApprovalRequest,
    FcpxmlRepairAction,
    FcpxmlRepairDryRun,
    FcpxmlRepairDryRunStep,
    FcpxmlRepairExecutionActionReview,
    FcpxmlRepairExecutionRecord,
    FcpxmlRepairExecutionReview,
    FcpxmlRepairPlan,
    FcpxmlValidationReport,
)
from artist_portrait_editor.models.nle_interchange import NleInterchangePlan
from artist_portrait_editor.run_records import write_json


class FcpxmlWriterError(RuntimeError):
    pass


def build_fcpxml_draft(
    *,
    root: Path,
    project_id: str,
    draft: bool,
) -> tuple[Path, Path, Path, Path, FcpxmlDraft, FcpxmlValidationReport]:
    if not draft:
        raise FcpxmlWriterError("fcpxml writer requires --draft in V0-047")
    plan_path = root / WORKSPACE_DIR / DATA_DIR / "nle_interchange_plan.json"
    if not plan_path.exists():
        raise FcpxmlWriterError("fcpxml draft requires .artist-portrait/data/nle_interchange_plan.json")
    plan = NleInterchangePlan.model_validate_json(plan_path.read_text(encoding="utf-8"))
    if plan.project_id != project_id:
        raise FcpxmlWriterError("NLE interchange plan project_id does not match project")
    fcpxml_mappings = [item for item in plan.timeline_mappings if item.target == "fcpxml"]
    if not fcpxml_mappings:
        raise FcpxmlWriterError("NLE interchange plan has no fcpxml timeline mappings")

    marker_mappings = [item for item in plan.marker_mappings if item.target == "fcpxml"]
    audio_mappings = [item for item in plan.audio_mappings if item.target == "fcpxml"]
    key = f"{project_id}:{plan.nle_plan_id}:{plan.frame_rate}:{len(fcpxml_mappings)}:{len(marker_mappings)}"
    draft_id = "fcpxml_draft_" + hashlib.sha256(key.encode()).hexdigest()[:20]
    validation_id = "fcpxml_validation_" + hashlib.sha256((key + ":validation").encode()).hexdigest()[:20]

    clips = [
        FcpxmlDraftClip(
            clip_id=f"clip_{index:03d}",
            mapping_id=mapping.mapping_id,
            asset_id=f"asset_{index:03d}",
            name=mapping.clip_id,
            offset_seconds=mapping.timeline_start,
            duration_seconds=mapping.timeline_end - mapping.timeline_start,
            source_start_seconds=mapping.source_in,
            source_duration_seconds=mapping.source_out - mapping.source_in,
            source_id=mapping.source_id,
            relink_required=True,
            warning_count=len(mapping.warnings),
            evidence_refs=mapping.evidence_refs,
        )
        for index, mapping in enumerate(sorted(fcpxml_mappings, key=lambda item: item.order), start=1)
    ]
    markers = [
        FcpxmlDraftMarker(
            marker_id=f"marker_{index:03d}",
            mapping_id=mapping.mapping_id,
            name=mapping.marker_name[:120],
            note=mapping.note,
            offset_seconds=mapping.timeline_start or 0.0,
            duration_seconds=max((mapping.timeline_end or mapping.timeline_start or 0.0) - (mapping.timeline_start or 0.0), 0.0),
            priority=mapping.priority,
            category=mapping.category,
            evidence_refs=mapping.evidence_refs,
        )
        for index, mapping in enumerate(sorted(marker_mappings, key=lambda item: item.order), start=1)
    ]
    audio_notes = [
        f"{mapping.category}: {mapping.instruction}"
        for mapping in sorted(audio_mappings, key=lambda item: item.order)
    ]
    warnings = [
        "FCPXML draft uses relink-required placeholder asset locations; import was not verified.",
        "Audio mix automation is preserved as notes/metadata, not as applied mix operations.",
    ]
    warnings.extend(
        sorted(
            {
                warning
                for mapping in [*fcpxml_mappings, *marker_mappings, *audio_mappings]
                for warning in mapping.warnings
            }
        )
    )

    draft_model = FcpxmlDraft(
        fcpxml_draft_id=draft_id,
        project_id=project_id,
        nle_plan_id=plan.nle_plan_id,
        editor_package_id=plan.editor_package_id,
        status="warning" if warnings else "ready",
        frame_rate=plan.frame_rate,
        fcpxml_version="1.10",
        draft_ref="output/draft.fcpxml",
        validation_ref=".artist-portrait/data/fcpxml_validation.json",
        clip_count=len(clips),
        marker_count=len(markers),
        audio_note_count=len(audio_notes),
        clips=clips,
        markers=markers,
        audio_notes=audio_notes,
        warnings=warnings,
        forbidden_capabilities=[
            "import into NLE",
            "render media",
            "mutate canonical timeline",
            "move edit points",
            "execute editor instructions",
            "select music automatically",
            "fit music automatically",
            "fabricate BPM or beat grids",
            "call models from the CLI",
            "access the network",
            "use image generation or editing",
        ],
    )

    xml_text = _render_fcpxml(draft_model)
    parse_passed = _xml_parse_passed(xml_text)
    validation = FcpxmlValidationReport(
        validation_id=validation_id,
        project_id=project_id,
        fcpxml_draft_id=draft_id,
        status="warning" if parse_passed else "failed",
        xml_parse_passed=parse_passed,
        project_binding_passed=draft_model.project_id == project_id,
        plan_binding_passed=draft_model.nle_plan_id == plan.nle_plan_id,
        timeline_mapping_coverage_passed=draft_model.clip_count == len(fcpxml_mappings),
        relink_required=True,
        warnings=draft_model.warnings,
        errors=[] if parse_passed else ["draft FCPXML did not parse as XML"],
    )

    data_dir = root / WORKSPACE_DIR / DATA_DIR
    output_dir = root / "output"
    data_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    draft_json_path = data_dir / "fcpxml_draft.json"
    validation_path = data_dir / "fcpxml_validation.json"
    fcpxml_path = output_dir / "draft.fcpxml"
    review_path = output_dir / "fcpxml_review.md"
    handoff_path = output_dir / "fcpxml_handoff.json"
    write_json(draft_json_path, draft_model.model_dump(mode="json"))
    write_json(validation_path, validation.model_dump(mode="json"))
    fcpxml_path.write_text(xml_text, encoding="utf-8")
    review_path.write_text(render_fcpxml_review(draft_model, validation) + "\n", encoding="utf-8")
    write_json(handoff_path, _handoff(draft_model, validation))
    return draft_json_path, fcpxml_path, validation_path, review_path, handoff_path, draft_model, validation


def import_fcpxml_import_review(
    *,
    root: Path,
    project_id: str,
    candidate_path: Path,
) -> tuple[Path, Path, Path, FcpxmlImportReview]:
    draft_path = root / WORKSPACE_DIR / DATA_DIR / "fcpxml_draft.json"
    if not draft_path.exists():
        raise FcpxmlWriterError("FCPXML import review requires .artist-portrait/data/fcpxml_draft.json")
    draft = FcpxmlDraft.model_validate_json(draft_path.read_text(encoding="utf-8"))
    if draft.project_id != project_id:
        raise FcpxmlWriterError("FCPXML draft project_id does not match project")
    if not candidate_path.exists():
        raise FcpxmlWriterError(f"FCPXML import review candidate not found: {candidate_path}")

    data_dir = root / WORKSPACE_DIR / DATA_DIR
    output_dir = root / "output"
    data_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    quarantine_path = data_dir / "fcpxml_import_review_candidate_quarantine.json"
    shutil.copyfile(candidate_path, quarantine_path)
    fingerprint = "sha256:" + hashlib.sha256(quarantine_path.read_bytes()).hexdigest()
    candidate = FcpxmlImportReviewCandidate.model_validate_json(
        quarantine_path.read_text(encoding="utf-8")
    )

    rejected_reasons: list[str] = []
    warnings: list[str] = []
    if candidate.project_id != project_id:
        rejected_reasons.append("candidate project_id does not match project")
    if candidate.fcpxml_draft_id != draft.fcpxml_draft_id:
        rejected_reasons.append("candidate fcpxml_draft_id does not match current draft")
    if candidate.nle_plan_id != draft.nle_plan_id:
        rejected_reasons.append("candidate nle_plan_id does not match current draft")
    if candidate.issue_count != len(candidate.issues):
        rejected_reasons.append("candidate issue_count does not match issues length")
    if candidate.media_rendered:
        rejected_reasons.append("candidate claims media was rendered")
    if candidate.timeline_mutated:
        rejected_reasons.append("candidate claims canonical timeline was mutated")
    if candidate.edit_points_moved:
        rejected_reasons.append("candidate claims edit points were moved")
    if candidate.automatic_music_selection:
        rejected_reasons.append("candidate claims automatic music selection")
    if candidate.automatic_bgm_fit:
        rejected_reasons.append("candidate claims automatic BGM fitting")
    if candidate.model_call_performed_by_cli:
        rejected_reasons.append("candidate claims CLI model call")
    if candidate.network_performed:
        rejected_reasons.append("candidate claims network access")
    if candidate.image_generation_or_editing_used:
        rejected_reasons.append("candidate claims image generation or editing")
    if not candidate.import_attempted:
        warnings.append("candidate says FCPXML import was not attempted")
    if candidate.import_attempted and not candidate.import_succeeded:
        warnings.append("candidate says FCPXML import did not succeed")
    if candidate.relink_attempted and not candidate.relink_succeeded:
        warnings.append("candidate says source relink did not succeed")
    if candidate.import_succeeded:
        warnings.append("import success is external evidence only and is not project acceptance success")

    warning_count = sum(1 for issue in candidate.issues if issue.severity == "warning")
    error_count = sum(1 for issue in candidate.issues if issue.severity == "error")
    if error_count:
        warnings.append("candidate reported FCPXML import errors")
    binding_status = "mismatch" if rejected_reasons else "matched"
    status = "rejected" if rejected_reasons else "warning" if warnings or warning_count or error_count else "accepted"
    review_key = f"{project_id}:{draft.fcpxml_draft_id}:{candidate.import_review_id}:{fingerprint}"
    review = FcpxmlImportReview(
        review_id="fcpxml_import_review_" + hashlib.sha256(review_key.encode()).hexdigest()[:20],
        project_id=project_id,
        fcpxml_draft_id=draft.fcpxml_draft_id,
        nle_plan_id=draft.nle_plan_id,
        candidate_fingerprint=fingerprint,
        quarantine_ref=".artist-portrait/data/fcpxml_import_review_candidate_quarantine.json",
        status=status,
        binding_status=binding_status,
        import_attempted=candidate.import_attempted,
        import_success_claimed=candidate.import_succeeded,
        relink_success_claimed=candidate.relink_succeeded,
        timeline_opened=candidate.timeline_opened,
        playback_checked=candidate.playback_checked,
        issue_count=candidate.issue_count,
        accepted_issue_count=sum(1 for issue in candidate.issues if issue.severity == "info"),
        warning_count=warning_count + len(warnings),
        error_count=error_count + len(rejected_reasons),
        findings=candidate.issues,
        warnings=warnings,
        rejected_reasons=rejected_reasons,
        forbidden_capabilities=[
            "execute FCPXML import from CLI",
            "treat import evidence as project acceptance success",
            "render media",
            "mutate canonical timeline",
            "move edit points",
            "select music automatically",
            "fit music automatically",
            "call models from the CLI",
            "access the network",
            "use image generation or editing",
        ],
    )

    json_path = data_dir / "fcpxml_import_review.json"
    md_path = output_dir / "fcpxml_import_review.md"
    handoff_path = output_dir / "fcpxml_import_review_handoff.json"
    write_json(json_path, review.model_dump(mode="json"))
    md_path.write_text(render_fcpxml_import_review(review) + "\n", encoding="utf-8")
    write_json(handoff_path, _import_review_handoff(review))
    return json_path, md_path, handoff_path, review


def build_fcpxml_repair_plan(
    *,
    root: Path,
    project_id: str,
) -> tuple[Path, Path, Path, FcpxmlRepairPlan]:
    draft_path = root / WORKSPACE_DIR / DATA_DIR / "fcpxml_draft.json"
    validation_path = root / WORKSPACE_DIR / DATA_DIR / "fcpxml_validation.json"
    import_review_path = root / WORKSPACE_DIR / DATA_DIR / "fcpxml_import_review.json"
    if not draft_path.exists():
        raise FcpxmlWriterError("FCPXML repair plan requires .artist-portrait/data/fcpxml_draft.json")
    if not validation_path.exists():
        raise FcpxmlWriterError("FCPXML repair plan requires .artist-portrait/data/fcpxml_validation.json")
    if not import_review_path.exists():
        raise FcpxmlWriterError("FCPXML repair plan requires .artist-portrait/data/fcpxml_import_review.json")

    draft = FcpxmlDraft.model_validate_json(draft_path.read_text(encoding="utf-8"))
    validation = FcpxmlValidationReport.model_validate_json(validation_path.read_text(encoding="utf-8"))
    import_review = FcpxmlImportReview.model_validate_json(import_review_path.read_text(encoding="utf-8"))
    binding_errors = []
    if draft.project_id != project_id:
        binding_errors.append("FCPXML draft project_id does not match project")
    if validation.project_id != project_id or validation.fcpxml_draft_id != draft.fcpxml_draft_id:
        binding_errors.append("FCPXML validation does not match current draft")
    if import_review.project_id != project_id or import_review.fcpxml_draft_id != draft.fcpxml_draft_id:
        binding_errors.append("FCPXML import review does not match current draft")
    if import_review.nle_plan_id != draft.nle_plan_id:
        binding_errors.append("FCPXML import review nle_plan_id does not match current draft")
    if binding_errors:
        raise FcpxmlWriterError("; ".join(binding_errors))

    actions: list[FcpxmlRepairAction] = []

    def add_action(
        *,
        source: str,
        category: str,
        severity: str,
        command: str,
        reason: str,
        expected_artifacts: list[str] | None = None,
        evidence_refs: list[str] | None = None,
    ) -> None:
        actions.append(
            FcpxmlRepairAction(
                action_id=f"fcpxml_repair_{len(actions) + 1:03d}_{category}",
                order=len(actions) + 1,
                source=source,
                category=category,
                severity=severity,
                command=command,
                reason=reason,
                expected_artifacts=expected_artifacts or [],
                evidence_refs=evidence_refs or [],
            )
        )

    if draft.relink_required or any(clip.relink_required for clip in draft.clips):
        add_action(
            source="draft",
            category="asset_relink",
            severity="required",
            command="Open output/draft.fcpxml in Final Cut Pro and manually relink placeholder assets to project-local source media.",
            reason="FCPXML draft contains relink-required placeholder assets.",
            expected_artifacts=["external FCPXML import-review candidate with relink_attempted=true"],
            evidence_refs=[".artist-portrait/data/fcpxml_draft.json", "output/draft.fcpxml"],
        )
    if import_review.relink_success_claimed is False:
        add_action(
            source="import_review",
            category="asset_relink",
            severity="required",
            command="Relink missing media in the NLE and export a new explicit FCPXML import-review candidate.",
            reason="Latest import review does not claim relink success.",
            expected_artifacts=["fcpxml_import_review_candidate.json"],
            evidence_refs=[import_review.quarantine_ref],
        )
    if validation.xml_parse_passed is False or validation.errors:
        add_action(
            source="validation",
            category="import_blocker",
            severity="required",
            command="Regenerate the FCPXML draft after resolving XML validation errors.",
            reason="Current FCPXML validation reports parse or validation errors.",
            expected_artifacts=["output/draft.fcpxml", ".artist-portrait/data/fcpxml_validation.json"],
            evidence_refs=[".artist-portrait/data/fcpxml_validation.json"],
        )
    if import_review.import_attempted and not import_review.import_success_claimed:
        add_action(
            source="import_review",
            category="import_blocker",
            severity="required",
            command="Review the NLE import failure and create a corrected external import-review candidate.",
            reason="Latest external evidence says FCPXML import did not succeed.",
            expected_artifacts=["fcpxml_import_review_candidate.json"],
            evidence_refs=[import_review.quarantine_ref],
        )
    if not import_review.import_attempted:
        add_action(
            source="import_review",
            category="operator_review",
            severity="required",
            command="Attempt supervised NLE import of output/draft.fcpxml and record an explicit import-review candidate.",
            reason="Latest external evidence says FCPXML import was not attempted.",
            expected_artifacts=["fcpxml_import_review_candidate.json"],
            evidence_refs=[import_review.quarantine_ref],
        )
    if not import_review.timeline_opened:
        add_action(
            source="playback",
            category="playback_review",
            severity="required",
            command="Open the imported timeline in the NLE and record whether it opens correctly.",
            reason="Latest import review did not confirm the timeline opened.",
            expected_artifacts=["fcpxml_import_review_candidate.json"],
            evidence_refs=[import_review.quarantine_ref],
        )
    if not import_review.playback_checked:
        add_action(
            source="playback",
            category="playback_review",
            severity="optional",
            command="Perform manual playback spot-checks for clip order, marker placement, and audio notes.",
            reason="Latest import review did not confirm playback checks.",
            expected_artifacts=["fcpxml_import_review_candidate.json"],
            evidence_refs=[import_review.quarantine_ref],
        )
    for finding in import_review.findings:
        severity = "required" if finding.severity == "error" else "optional"
        category = "asset_relink" if "relink" in finding.category else "mapping_review"
        add_action(
            source="finding",
            category=category,
            severity=severity,
            command="Review the external FCPXML import finding in the NLE and record the manual resolution evidence.",
            reason=f"{finding.severity} finding `{finding.issue_id}`: {finding.detail}",
            expected_artifacts=["fcpxml_import_review_candidate.json"],
            evidence_refs=[import_review.quarantine_ref],
        )

    required = sum(1 for action in actions if action.severity == "required")
    optional = len(actions) - required
    import_blockers = sum(1 for action in actions if action.category == "import_blocker")
    relink_actions = sum(1 for action in actions if action.category == "asset_relink")
    status = "blocked" if import_blockers else "warning" if actions else "ready"
    key = f"{project_id}:{draft.fcpxml_draft_id}:{import_review.review_id}:{len(actions)}:{required}"
    plan = FcpxmlRepairPlan(
        repair_plan_id="fcpxml_repair_plan_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=project_id,
        fcpxml_draft_id=draft.fcpxml_draft_id,
        fcpxml_validation_id=validation.validation_id,
        fcpxml_import_review_id=import_review.review_id,
        nle_plan_id=draft.nle_plan_id,
        status=status,
        action_count=len(actions),
        required_action_count=required,
        optional_action_count=optional,
        first_required_command=next((action.command for action in actions if action.severity == "required"), None),
        relink_action_count=relink_actions,
        import_blocker_count=import_blockers,
        playback_review_required=any(action.category == "playback_review" for action in actions),
        actions=actions,
        warnings=[
            "FCPXML repair plan is manual guidance only; the CLI did not import, relink, render, or mutate the timeline.",
            *import_review.warnings,
            *import_review.rejected_reasons,
        ],
        forbidden_capabilities=[
            "execute FCPXML import from CLI",
            "relink source media from CLI",
            "render media",
            "mutate canonical timeline",
            "move edit points",
            "select music automatically",
            "fit music automatically",
            "call models from the CLI",
            "access the network",
            "use image generation or editing",
            "claim repair success",
        ],
    )

    data_dir = root / WORKSPACE_DIR / DATA_DIR
    output_dir = root / "output"
    data_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = data_dir / "fcpxml_repair_plan.json"
    md_path = output_dir / "fcpxml_repair_plan.md"
    handoff_path = output_dir / "fcpxml_repair_handoff.json"
    write_json(json_path, plan.model_dump(mode="json"))
    md_path.write_text(render_fcpxml_repair_plan(plan) + "\n", encoding="utf-8")
    write_json(handoff_path, _repair_handoff(plan))
    return json_path, md_path, handoff_path, plan


def render_fcpxml_repair_plan(plan: FcpxmlRepairPlan) -> str:
    lines = [
        "# FCPXML Repair Plan",
        "",
        "This plan converts the latest FCPXML draft and external import-review evidence into manual repair actions. The CLI did not import into an NLE, relink media, render media, mutate the canonical timeline, move edit points, call models, access the network, or claim repair success.",
        "",
        f"- Status: `{plan.status}`",
        f"- Draft: `{plan.fcpxml_draft_id}`",
        f"- Import review: `{plan.fcpxml_import_review_id}`",
        f"- Required actions: `{plan.required_action_count}`",
        f"- Optional actions: `{plan.optional_action_count}`",
        f"- First required command: `{plan.first_required_command or 'none'}`",
        "",
        "## Actions",
        "",
    ]
    if plan.actions:
        lines.extend(
            f"- `{action.severity}` `{action.category}` `{action.action_id}`: {action.command} Reason: {action.reason}"
            for action in plan.actions
        )
    else:
        lines.append("- `none`")
    if plan.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in plan.warnings)
    lines.extend(["", "## Forbidden Capabilities", ""])
    lines.extend(f"- {item}" for item in plan.forbidden_capabilities)
    return "\n".join(lines)


def build_fcpxml_repair_approval_request(
    *,
    root: Path,
    project_id: str,
) -> tuple[Path, Path, Path, FcpxmlRepairApprovalRequest]:
    plan = _load_fcpxml_repair_plan(root, project_id)
    required = [action.action_id for action in plan.actions if action.severity == "required"]
    optional = [action.action_id for action in plan.actions if action.severity == "optional"]
    key = f"{plan.repair_plan_id}:{len(required)}:{len(optional)}"
    request = FcpxmlRepairApprovalRequest(
        approval_request_id="fcpxml_repair_approval_request_"
        + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=plan.project_id,
        fcpxml_repair_plan_id=plan.repair_plan_id,
        fcpxml_draft_id=plan.fcpxml_draft_id,
        fcpxml_import_review_id=plan.fcpxml_import_review_id,
        required_action_ids=required,
        optional_action_ids=optional,
    )
    data_dir = root / WORKSPACE_DIR / DATA_DIR
    output_dir = root / "output"
    data_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = data_dir / "fcpxml_repair_approval_request.json"
    md_path = output_dir / "fcpxml_repair_approval_request.md"
    handoff_path = output_dir / "fcpxml_repair_approval_handoff.json"
    write_json(json_path, request.model_dump(mode="json"))
    md_path.write_text(render_fcpxml_repair_approval_request(request) + "\n", encoding="utf-8")
    write_json(handoff_path, _repair_approval_handoff(request, plan))
    return json_path, md_path, handoff_path, request


def render_fcpxml_repair_approval_request(request: FcpxmlRepairApprovalRequest) -> str:
    return "\n".join(
        [
            "# FCPXML Repair Approval Request",
            "",
            "This request asks for explicit approval of manual FCPXML repair actions. It does not execute commands, import into an NLE, relink media, render media, mutate timelines, or claim repair success.",
            "",
            f"- Repair plan: `{request.fcpxml_repair_plan_id}`",
            f"- Draft: `{request.fcpxml_draft_id}`",
            f"- Import review: `{request.fcpxml_import_review_id}`",
            f"- Required action ids: {', '.join(f'`{item}`' for item in request.required_action_ids) or '`none`'}",
            f"- Optional action ids: {', '.join(f'`{item}`' for item in request.optional_action_ids) or '`none`'}",
            f"- Approval required: `{str(request.approval_required).lower()}`",
        ]
    )


def import_fcpxml_repair_approval_record(
    *,
    root: Path,
    project_id: str,
    candidate_path: Path,
) -> tuple[Path, Path, FcpxmlRepairApprovalRecord]:
    plan = _load_fcpxml_repair_plan(root, project_id)
    if not candidate_path.exists():
        raise FcpxmlWriterError(f"FCPXML repair approval record not found: {candidate_path}")
    data = candidate_path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    quarantine_path = root / WORKSPACE_DIR / DATA_DIR / "fcpxml_repair_approval_record_quarantine.json"
    quarantine_path.parent.mkdir(parents=True, exist_ok=True)
    quarantine_path.write_bytes(data)
    candidate = FcpxmlRepairApprovalRecord.model_validate_json(data.decode("utf-8"))
    valid_action_ids = {action.action_id for action in plan.actions}
    invalid: list[str] = []
    if candidate.project_id != plan.project_id:
        invalid.append("project_id does not match FCPXML repair plan")
    if candidate.fcpxml_repair_plan_id != plan.repair_plan_id:
        invalid.append("fcpxml_repair_plan_id does not match current repair plan")
    if candidate.fcpxml_draft_id != plan.fcpxml_draft_id:
        invalid.append("fcpxml_draft_id does not match current repair plan")
    if candidate.fcpxml_import_review_id != plan.fcpxml_import_review_id:
        invalid.append("fcpxml_import_review_id does not match current repair plan")
    unknown = sorted((set(candidate.approved_action_ids) | set(candidate.rejected_action_ids)) - valid_action_ids)
    if unknown:
        invalid.append("approval record references unknown action ids: " + ", ".join(unknown))
    if any(
        (
            candidate.commands_executed_by_cli,
            candidate.media_rendered_by_cli,
            candidate.timeline_mutated_by_cli,
            candidate.edit_points_moved_by_cli,
            candidate.nle_import_performed_by_cli,
            candidate.source_relink_performed_by_cli,
            candidate.automatic_music_selection_by_cli,
            candidate.automatic_bgm_fit_by_cli,
            candidate.model_call_performed_by_cli,
            candidate.network_performed_by_cli,
            candidate.image_generation_or_editing_used_by_cli,
            candidate.repair_success_claimed_by_cli,
        )
    ):
        invalid.append("approval record claims forbidden CLI-side execution")
    record = candidate.model_copy(
        update={
            "status": "failed" if invalid else "passed",
            "invalid_reasons": invalid,
            "quarantine_ref": quarantine_path.relative_to(root).as_posix(),
            "candidate_sha256": digest,
            "candidate_bytes": len(data),
            "commands_executed_by_cli": False,
            "media_rendered_by_cli": False,
            "timeline_mutated_by_cli": False,
            "edit_points_moved_by_cli": False,
            "nle_import_performed_by_cli": False,
            "source_relink_performed_by_cli": False,
            "automatic_music_selection_by_cli": False,
            "automatic_bgm_fit_by_cli": False,
            "model_call_performed_by_cli": False,
            "network_performed_by_cli": False,
            "image_generation_or_editing_used_by_cli": False,
            "repair_success_claimed_by_cli": False,
        }
    )
    data_dir = root / WORKSPACE_DIR / DATA_DIR
    output_dir = root / "output"
    data_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = data_dir / "fcpxml_repair_approval_record.json"
    md_path = output_dir / "fcpxml_repair_approval_record.md"
    write_json(json_path, record.model_dump(mode="json"))
    md_path.write_text(render_fcpxml_repair_approval_record(record) + "\n", encoding="utf-8")
    return json_path, md_path, record


def render_fcpxml_repair_approval_record(record: FcpxmlRepairApprovalRecord) -> str:
    lines = [
        "# FCPXML Repair Approval Record",
        "",
        "This record validates explicit approval choices for manual FCPXML repair actions. It does not execute repair commands.",
        "",
        f"- Status: `{record.status}`",
        f"- Repair plan: `{record.fcpxml_repair_plan_id}`",
        f"- Approved action ids: {', '.join(f'`{item}`' for item in record.approved_action_ids) or '`none`'}",
        f"- Rejected action ids: {', '.join(f'`{item}`' for item in record.rejected_action_ids) or '`none`'}",
    ]
    if record.invalid_reasons:
        lines.append(f"- Invalid reasons: {'; '.join(record.invalid_reasons)}")
    return "\n".join(lines)


def build_fcpxml_repair_dry_run(
    *,
    root: Path,
    project_id: str,
) -> tuple[Path, Path, Path, FcpxmlRepairDryRun]:
    plan = _load_fcpxml_repair_plan(root, project_id)
    record_path = root / WORKSPACE_DIR / DATA_DIR / "fcpxml_repair_approval_record.json"
    if not record_path.exists():
        raise FcpxmlWriterError("FCPXML repair approval record is required before dry-run")
    record = FcpxmlRepairApprovalRecord.model_validate_json(record_path.read_text(encoding="utf-8"))
    if record.status != "passed":
        raise FcpxmlWriterError("FCPXML repair approval record must pass before dry-run")
    if record.project_id != plan.project_id or record.fcpxml_repair_plan_id != plan.repair_plan_id:
        raise FcpxmlWriterError("FCPXML repair approval record does not match current repair plan")
    approved = set(record.approved_action_ids)
    rejected = set(record.rejected_action_ids)
    steps: list[FcpxmlRepairDryRunStep] = []
    for action in plan.actions:
        if action.action_id in approved:
            status = "approved"
            reason = "approved for manual execution"
        else:
            status = "rejected"
            reason = "not approved for manual execution"
            rejected.add(action.action_id)
        steps.append(
            FcpxmlRepairDryRunStep(
                action_id=action.action_id,
                command=action.command,
                status=status,
                reason=reason,
                expected_artifacts=action.expected_artifacts,
                evidence_refs=action.evidence_refs,
            )
        )
    key = f"{plan.repair_plan_id}:{record.approval_record_id}:{len(approved)}:{len(rejected)}"
    dry_run = FcpxmlRepairDryRun(
        dry_run_id="fcpxml_repair_dry_run_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=plan.project_id,
        fcpxml_repair_plan_id=plan.repair_plan_id,
        approval_record_id=record.approval_record_id,
        fcpxml_draft_id=plan.fcpxml_draft_id,
        fcpxml_import_review_id=plan.fcpxml_import_review_id,
        approved_action_count=sum(step.status == "approved" for step in steps),
        rejected_action_count=sum(step.status == "rejected" for step in steps),
        steps=steps,
    )
    data_dir = root / WORKSPACE_DIR / DATA_DIR
    output_dir = root / "output"
    data_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = data_dir / "fcpxml_repair_dry_run.json"
    md_path = output_dir / "fcpxml_repair_dry_run.md"
    handoff_path = output_dir / "fcpxml_repair_dry_run_handoff.json"
    write_json(json_path, dry_run.model_dump(mode="json"))
    md_path.write_text(render_fcpxml_repair_dry_run(dry_run) + "\n", encoding="utf-8")
    write_json(handoff_path, _repair_dry_run_handoff(dry_run))
    return json_path, md_path, handoff_path, dry_run


def render_fcpxml_repair_dry_run(dry_run: FcpxmlRepairDryRun) -> str:
    lines = [
        "# FCPXML Repair Dry Run",
        "",
        "This dry run enumerates approved manual FCPXML repair commands. It does not execute commands, import into an NLE, relink media, render media, mutate timelines, or claim repair success.",
        "",
        f"- Approved actions: `{dry_run.approved_action_count}`",
        f"- Rejected actions: `{dry_run.rejected_action_count}`",
        "",
    ]
    for step in dry_run.steps:
        lines.extend(
            [
                f"## `{step.action_id}`",
                "",
                f"- Status: `{step.status}`",
                f"- Command: `{step.command}`",
                f"- Reason: {step.reason}",
                "",
            ]
        )
    return "\n".join(lines)


def import_fcpxml_repair_execution_record(
    *,
    root: Path,
    project_id: str,
    candidate_path: Path,
) -> tuple[Path, Path, Path, FcpxmlRepairExecutionReview]:
    dry_run_path = root / WORKSPACE_DIR / DATA_DIR / "fcpxml_repair_dry_run.json"
    if not dry_run_path.exists():
        raise FcpxmlWriterError("FCPXML repair dry-run is required before execution review")
    dry_run = FcpxmlRepairDryRun.model_validate_json(dry_run_path.read_text(encoding="utf-8"))
    if dry_run.project_id != project_id:
        raise FcpxmlWriterError("FCPXML repair dry-run project_id does not match project")
    if not candidate_path.exists():
        raise FcpxmlWriterError(f"FCPXML repair execution record not found: {candidate_path}")

    data = candidate_path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    quarantine_path = root / WORKSPACE_DIR / DATA_DIR / "fcpxml_repair_execution_record_quarantine.json"
    quarantine_path.parent.mkdir(parents=True, exist_ok=True)
    quarantine_path.write_bytes(data)
    record = FcpxmlRepairExecutionRecord.model_validate_json(data.decode("utf-8"))
    review = _review_fcpxml_repair_execution_record(
        dry_run=dry_run,
        record=record,
        quarantine_ref=quarantine_path.relative_to(root).as_posix(),
        candidate_sha256=digest,
        candidate_bytes=len(data),
    )
    data_dir = root / WORKSPACE_DIR / DATA_DIR
    output_dir = root / "output"
    data_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = data_dir / "fcpxml_repair_execution_review.json"
    md_path = output_dir / "fcpxml_repair_execution_review.md"
    handoff_path = output_dir / "fcpxml_repair_execution_handoff.json"
    write_json(json_path, review.model_dump(mode="json"))
    md_path.write_text(render_fcpxml_repair_execution_review(review) + "\n", encoding="utf-8")
    write_json(handoff_path, _repair_execution_handoff(review))
    return json_path, md_path, handoff_path, review


def render_fcpxml_repair_execution_review(review: FcpxmlRepairExecutionReview) -> str:
    lines = [
        "# FCPXML Repair Execution Review",
        "",
        "This review validates explicit external FCPXML repair execution evidence against the current dry-run. The CLI did not execute commands, import into an NLE, relink media, render media, mutate timelines, or promote repair/acceptance success.",
        "",
        f"- Status: `{review.status}`",
        f"- Repair plan: `{review.fcpxml_repair_plan_id}`",
        f"- Approval record: `{review.approval_record_id}`",
        f"- Dry run: `{review.dry_run_id}`",
        f"- Accepted actions: `{review.accepted_action_count}`",
        f"- Rejected actions: `{review.rejected_action_count}`",
        f"- Missing actions: `{review.missing_action_count}`",
        f"- Skipped actions: `{review.skipped_action_count}`",
        "",
    ]
    for action in review.action_reviews:
        lines.extend(
            [
                f"## `{action.action_id}`",
                "",
                f"- Dry-run status: `{action.dry_run_status or 'none'}`",
                f"- Submitted status: `{action.submitted_status or 'none'}`",
                f"- Review status: `{action.review_status}`",
                f"- Command matched: `{str(action.command_matched).lower()}`",
                f"- Detail: {action.detail}",
            ]
        )
        if action.evidence_refs:
            lines.append(f"- Evidence refs: {', '.join(f'`{ref}`' for ref in action.evidence_refs)}")
        if action.output_refs:
            lines.append(f"- Output refs: {', '.join(f'`{ref}`' for ref in action.output_refs)}")
        if action.missing_refs:
            lines.append(f"- Missing refs: {', '.join(f'`{ref}`' for ref in action.missing_refs)}")
        lines.append("")
    return "\n".join(lines)


def render_fcpxml_import_review(review: FcpxmlImportReview) -> str:
    lines = [
        "# FCPXML Import Review",
        "",
        "This review validates an explicit external FCPXML import-review record. The CLI did not import into an NLE, render media, mutate the canonical timeline, move edit points, call models, access the network, or treat external evidence as project acceptance success.",
        "",
        f"- Status: `{review.status}`",
        f"- Binding: `{review.binding_status}`",
        f"- Draft: `{review.fcpxml_draft_id}`",
        f"- Import attempted: `{review.import_attempted}`",
        f"- Import success claimed: `{review.import_success_claimed}`",
        f"- Relink success claimed: `{review.relink_success_claimed}`",
        f"- Timeline opened: `{review.timeline_opened}`",
        f"- Playback checked: `{review.playback_checked}`",
        f"- Import success accepted as project success: `{review.import_success_accepted_as_project_success}`",
        "",
        "## Findings",
        "",
    ]
    if review.findings:
        lines.extend(
            f"- `{item.severity}` `{item.category}` `{item.issue_id}`: {item.detail}"
            for item in review.findings
        )
    else:
        lines.append("- `none`")
    if review.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {item}" for item in review.warnings)
    if review.rejected_reasons:
        lines.extend(["", "## Rejected Reasons", ""])
        lines.extend(f"- {item}" for item in review.rejected_reasons)
    lines.extend(["", "## Forbidden Capabilities", ""])
    lines.extend(f"- {item}" for item in review.forbidden_capabilities)
    return "\n".join(lines)


def render_fcpxml_review(draft: FcpxmlDraft, validation: FcpxmlValidationReport) -> str:
    lines = [
        "# FCPXML Draft Review",
        "",
        "This is a supervised FCPXML draft generated from the current NLE interchange plan. It has not been imported into Final Cut Pro, does not render media, does not mutate the canonical timeline, and uses relink-required placeholder assets.",
        "",
        f"- Status: `{draft.status}`",
        f"- Draft id: `{draft.fcpxml_draft_id}`",
        f"- NLE plan: `{draft.nle_plan_id}`",
        f"- Clips: `{draft.clip_count}`",
        f"- Markers: `{draft.marker_count}`",
        f"- Audio notes: `{draft.audio_note_count}`",
        f"- XML parse passed: `{validation.xml_parse_passed}`",
        f"- Import verified: `{draft.import_verified}`",
        f"- Relink required: `{draft.relink_required}`",
        "",
        "## Clips",
        "",
    ]
    for clip in draft.clips:
        lines.append(
            f"- `{clip.clip_id}` `{clip.name}` offset `{clip.offset_seconds:.3f}` duration `{clip.duration_seconds:.3f}` asset `{clip.asset_id}` relink `{clip.relink_required}`"
        )
    lines.extend(["", "## Markers", ""])
    for marker in draft.markers:
        lines.append(
            f"- `{marker.priority}` `{marker.category}` at `{marker.offset_seconds:.3f}`: {marker.note}"
        )
    lines.extend(["", "## Audio Notes", ""])
    lines.extend(f"- {note}" for note in draft.audio_notes) if draft.audio_notes else lines.append("- `none`")
    if draft.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in draft.warnings)
    lines.extend(["", "## Forbidden Capabilities", ""])
    lines.extend(f"- {item}" for item in draft.forbidden_capabilities)
    return "\n".join(lines)


def _render_fcpxml(draft: FcpxmlDraft) -> str:
    ET.register_namespace("", "")
    root = ET.Element("fcpxml", {"version": draft.fcpxml_version})
    resources = ET.SubElement(root, "resources")
    frame_duration = _frame_duration(draft.frame_rate)
    ET.SubElement(
        resources,
        "format",
        {
            "id": "fmt_001",
            "name": f"ArtistPortraitDraft{int(round(draft.frame_rate))}p",
            "frameDuration": frame_duration,
        },
    )
    for clip in draft.clips:
        ET.SubElement(
            resources,
            "asset",
            {
                "id": clip.asset_id,
                "name": clip.name,
                "src": f"file://localhost/ARTIST_PORTRAIT_RELINK_REQUIRED/{clip.source_id}",
                "start": _seconds(clip.source_start_seconds),
                "duration": _seconds(clip.source_duration_seconds),
                "hasVideo": "1",
                "hasAudio": "1",
            },
        )
    library = ET.SubElement(root, "library")
    event = ET.SubElement(library, "event", {"name": "artist-portrait-draft"})
    project = ET.SubElement(event, "project", {"name": draft.project_id})
    sequence = ET.SubElement(
        project,
        "sequence",
        {
            "format": "fmt_001",
            "duration": _seconds(max((clip.offset_seconds + clip.duration_seconds for clip in draft.clips), default=0.0)),
            "tcStart": "0s",
            "tcFormat": "NDF",
        },
    )
    spine = ET.SubElement(sequence, "spine")
    for clip in draft.clips:
        asset_clip = ET.SubElement(
            spine,
            "asset-clip",
            {
                "name": clip.name,
                "ref": clip.asset_id,
                "offset": _seconds(clip.offset_seconds),
                "start": _seconds(clip.source_start_seconds),
                "duration": _seconds(clip.duration_seconds),
            },
        )
        for marker in draft.markers:
            if clip.offset_seconds <= marker.offset_seconds < clip.offset_seconds + clip.duration_seconds:
                ET.SubElement(
                    asset_clip,
                    "marker",
                    {
                        "start": _seconds(marker.offset_seconds - clip.offset_seconds),
                        "duration": _seconds(max(marker.duration_seconds, 0.01)),
                        "value": marker.name,
                        "note": marker.note,
                    },
                )
    for index, note in enumerate(draft.audio_notes, start=1):
        ET.SubElement(
            spine,
            "marker",
            {
                "start": "0s",
                "duration": "1/100s",
                "value": f"audio_note_{index:03d}",
                "note": note,
            },
        )
    xml_body = ET.tostring(root, encoding="unicode", short_empty_elements=True)
    return '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n' + xml_body + "\n"


def _handoff(draft: FcpxmlDraft, validation: FcpxmlValidationReport) -> dict:
    return {
        "handoff_type": "fcpxml_draft",
        "project_id": draft.project_id,
        "status": draft.status,
        "fcpxml_draft_ref": ".artist-portrait/data/fcpxml_draft.json",
        "fcpxml_file_ref": "output/draft.fcpxml",
        "validation_ref": ".artist-portrait/data/fcpxml_validation.json",
        "review_ref": "output/fcpxml_review.md",
        "nle_plan_id": draft.nle_plan_id,
        "clip_count": draft.clip_count,
        "marker_count": draft.marker_count,
        "audio_note_count": draft.audio_note_count,
        "xml_parse_passed": validation.xml_parse_passed,
        "relink_required": draft.relink_required,
        "import_verified": draft.import_verified,
        "warnings": draft.warnings,
        "forbidden_capabilities": draft.forbidden_capabilities,
        "commands_executed": False,
        "media_rendered": False,
        "timeline_mutated": False,
        "edit_points_moved": False,
        "nle_import_performed": False,
        "automatic_music_selection": False,
        "automatic_bgm_fit": False,
        "model_call_performed_by_cli": False,
        "network_performed": False,
        "image_generation_or_editing_used": False,
    }


def _import_review_handoff(review: FcpxmlImportReview) -> dict:
    return {
        "handoff_type": "fcpxml_import_review",
        "project_id": review.project_id,
        "status": review.status,
        "binding_status": review.binding_status,
        "review_ref": ".artist-portrait/data/fcpxml_import_review.json",
        "review_report_ref": "output/fcpxml_import_review.md",
        "candidate_quarantine_ref": review.quarantine_ref,
        "fcpxml_draft_id": review.fcpxml_draft_id,
        "nle_plan_id": review.nle_plan_id,
        "import_attempted": review.import_attempted,
        "import_success_claimed": review.import_success_claimed,
        "relink_success_claimed": review.relink_success_claimed,
        "timeline_opened": review.timeline_opened,
        "playback_checked": review.playback_checked,
        "import_success_accepted_as_project_success": False,
        "warnings": review.warnings,
        "rejected_reasons": review.rejected_reasons,
        "forbidden_capabilities": review.forbidden_capabilities,
        "commands_executed": False,
        "media_rendered": False,
        "timeline_mutated": False,
        "edit_points_moved": False,
        "automatic_music_selection": False,
        "automatic_bgm_fit": False,
        "model_call_performed_by_cli": False,
        "network_performed": False,
        "image_generation_or_editing_used": False,
    }


def _repair_handoff(plan: FcpxmlRepairPlan) -> dict:
    return {
        "handoff_type": "fcpxml_repair_plan",
        "project_id": plan.project_id,
        "status": plan.status,
        "fcpxml_draft_id": plan.fcpxml_draft_id,
        "fcpxml_import_review_id": plan.fcpxml_import_review_id,
        "fcpxml_repair_plan_id": plan.repair_plan_id,
        "repair_plan_ref": ".artist-portrait/data/fcpxml_repair_plan.json",
        "repair_report_ref": "output/fcpxml_repair_plan.md",
        "first_required_command": plan.first_required_command,
        "required_action_count": plan.required_action_count,
        "optional_action_count": plan.optional_action_count,
        "relink_action_count": plan.relink_action_count,
        "import_blocker_count": plan.import_blocker_count,
        "task": "Guide manual FCPXML import, relink, playback, and mapping repair evidence collection only.",
        "forbidden_capabilities": plan.forbidden_capabilities,
        "commands_executed": False,
        "media_rendered": False,
        "timeline_mutated": False,
        "edit_points_moved": False,
        "nle_import_performed": False,
        "source_relink_performed": False,
        "automatic_music_selection": False,
        "automatic_bgm_fit": False,
        "model_call_performed_by_cli": False,
        "network_performed": False,
        "image_generation_or_editing_used": False,
        "repair_success_claimed": False,
    }


def _repair_approval_handoff(
    request: FcpxmlRepairApprovalRequest,
    plan: FcpxmlRepairPlan,
) -> dict:
    return {
        "handoff_type": "fcpxml_repair_approval_request",
        "project_id": request.project_id,
        "fcpxml_repair_plan_id": request.fcpxml_repair_plan_id,
        "approval_request_id": request.approval_request_id,
        "required_action_count": len(request.required_action_ids),
        "optional_action_count": len(request.optional_action_ids),
        "first_required_command": plan.first_required_command,
        "task": "Collect explicit approval for manual FCPXML repair actions only.",
        "forbidden": [
            "do not execute repair commands",
            "do not import into an NLE from the CLI",
            "do not relink source media from the CLI",
            "do not render media",
            "do not mutate the canonical timeline",
            "do not claim repair success",
        ],
    }


def _repair_dry_run_handoff(dry_run: FcpxmlRepairDryRun) -> dict:
    return {
        "handoff_type": "fcpxml_repair_dry_run",
        "project_id": dry_run.project_id,
        "fcpxml_repair_plan_id": dry_run.fcpxml_repair_plan_id,
        "approval_record_id": dry_run.approval_record_id,
        "dry_run_id": dry_run.dry_run_id,
        "approved_action_count": dry_run.approved_action_count,
        "rejected_action_count": dry_run.rejected_action_count,
        "task": "Review approved manual FCPXML repair commands without executing them.",
        "forbidden": [
            "do not execute dry-run commands",
            "do not import into an NLE from the CLI",
            "do not relink source media from the CLI",
            "do not render media",
            "do not mutate the canonical timeline",
            "do not claim repair success",
        ],
    }


def _repair_execution_handoff(review: FcpxmlRepairExecutionReview) -> dict:
    return {
        "handoff_type": "fcpxml_repair_execution_review",
        "project_id": review.project_id,
        "fcpxml_repair_plan_id": review.fcpxml_repair_plan_id,
        "approval_record_id": review.approval_record_id,
        "dry_run_id": review.dry_run_id,
        "execution_review_id": review.execution_review_id,
        "status": review.status,
        "accepted_action_count": review.accepted_action_count,
        "rejected_action_count": review.rejected_action_count,
        "missing_action_count": review.missing_action_count,
        "skipped_action_count": review.skipped_action_count,
        "task": "Review external manual FCPXML repair execution evidence without treating it as repair or acceptance success.",
        "forbidden": [
            "do not execute repair commands from this review",
            "do not import into an NLE from the CLI",
            "do not relink source media from the CLI",
            "do not render media",
            "do not mutate the canonical timeline",
            "do not treat repair execution evidence as repair success",
            "do not treat repair execution evidence as acceptance success",
        ],
    }


def _review_fcpxml_repair_execution_record(
    *,
    dry_run: FcpxmlRepairDryRun,
    record: FcpxmlRepairExecutionRecord,
    quarantine_ref: str,
    candidate_sha256: str,
    candidate_bytes: int,
) -> FcpxmlRepairExecutionReview:
    binding_errors: list[str] = []
    if record.project_id != dry_run.project_id:
        binding_errors.append("project_id does not match FCPXML repair dry-run")
    if record.fcpxml_repair_plan_id != dry_run.fcpxml_repair_plan_id:
        binding_errors.append("fcpxml_repair_plan_id does not match FCPXML repair dry-run")
    if record.approval_record_id != dry_run.approval_record_id:
        binding_errors.append("approval_record_id does not match FCPXML repair dry-run")
    if record.dry_run_id != dry_run.dry_run_id:
        binding_errors.append("dry_run_id does not match FCPXML repair dry-run")
    if record.fcpxml_draft_id != dry_run.fcpxml_draft_id:
        binding_errors.append("fcpxml_draft_id does not match FCPXML repair dry-run")
    if record.fcpxml_import_review_id != dry_run.fcpxml_import_review_id:
        binding_errors.append("fcpxml_import_review_id does not match FCPXML repair dry-run")
    if any(
        (
            record.commands_executed_by_cli,
            record.media_rendered_by_cli,
            record.timeline_mutated_by_cli,
            record.edit_points_moved_by_cli,
            record.nle_import_performed_by_cli,
            record.source_relink_performed_by_cli,
            record.automatic_music_selection_by_cli,
            record.automatic_bgm_fit_by_cli,
            record.model_call_performed_by_cli,
            record.network_performed_by_cli,
            record.image_generation_or_editing_used_by_cli,
            record.repair_success_promoted_by_cli,
            record.acceptance_success_promoted_by_cli,
        )
    ):
        binding_errors.append("execution record claims forbidden CLI-side execution or success promotion")

    dry_run_by_action = {step.action_id: step for step in dry_run.steps}
    submitted_by_action = {action.action_id: action for action in record.actions}
    reviews: list[FcpxmlRepairExecutionActionReview] = []
    for action_id, submitted in sorted(submitted_by_action.items()):
        dry_step = dry_run_by_action.get(action_id)
        if dry_step is None:
            reviews.append(
                FcpxmlRepairExecutionActionReview(
                    action_id=action_id,
                    submitted_status=submitted.status,
                    review_status="rejected",
                    detail="submitted action is not present in the current FCPXML repair dry-run",
                    evidence_refs=submitted.evidence_refs,
                    output_refs=submitted.output_refs,
                )
            )
            continue
        command_matched = submitted.command == dry_step.command
        if dry_step.status != "approved":
            review_status = "rejected"
            detail = "submitted action was not approved in the FCPXML repair dry-run"
        elif submitted.status == "skipped":
            review_status = "skipped"
            detail = "external execution record skipped this approved action"
        elif submitted.status == "failed":
            review_status = "rejected"
            detail = "external execution record reports this action failed"
        elif not command_matched:
            review_status = "rejected"
            detail = "submitted command does not match FCPXML repair dry-run command"
        elif not submitted.evidence_refs:
            review_status = "rejected"
            detail = "submitted action lacks external evidence refs"
        else:
            review_status = "accepted"
            detail = "submitted repair execution evidence is bound to an approved action, matching command, and evidence refs"
        reviews.append(
            FcpxmlRepairExecutionActionReview(
                action_id=action_id,
                dry_run_status=dry_step.status,
                submitted_status=submitted.status,
                review_status=review_status,
                command_matched=command_matched,
                evidence_refs=submitted.evidence_refs,
                output_refs=submitted.output_refs,
                missing_refs=[] if submitted.evidence_refs else ["evidence_refs"],
                detail=detail,
            )
        )
    for dry_step in dry_run.steps:
        if dry_step.status == "approved" and dry_step.action_id not in submitted_by_action:
            reviews.append(
                FcpxmlRepairExecutionActionReview(
                    action_id=dry_step.action_id,
                    dry_run_status=dry_step.status,
                    review_status="missing",
                    detail="no external repair execution evidence was submitted for this approved action",
                    missing_refs=dry_step.expected_artifacts,
                )
            )

    accepted = sum(item.review_status == "accepted" for item in reviews)
    rejected = sum(item.review_status == "rejected" for item in reviews)
    missing = sum(item.review_status == "missing" for item in reviews)
    skipped = sum(item.review_status == "skipped" for item in reviews)
    status = "failed" if binding_errors or rejected else "warning" if missing or skipped else "passed"
    if binding_errors:
        reviews.insert(
            0,
            FcpxmlRepairExecutionActionReview(
                action_id="binding",
                review_status="rejected",
                detail="; ".join(binding_errors),
            ),
        )
        rejected += 1
    key = f"{dry_run.dry_run_id}:{record.execution_record_id}:{accepted}:{rejected}:{missing}:{skipped}:{candidate_sha256}"
    return FcpxmlRepairExecutionReview(
        execution_review_id="fcpxml_repair_execution_review_"
        + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=dry_run.project_id,
        fcpxml_repair_plan_id=dry_run.fcpxml_repair_plan_id,
        approval_record_id=dry_run.approval_record_id,
        dry_run_id=dry_run.dry_run_id,
        fcpxml_draft_id=dry_run.fcpxml_draft_id,
        fcpxml_import_review_id=dry_run.fcpxml_import_review_id,
        status=status,
        quarantine_ref=quarantine_ref,
        candidate_sha256=candidate_sha256,
        candidate_bytes=candidate_bytes,
        accepted_action_count=accepted,
        rejected_action_count=rejected,
        missing_action_count=missing,
        skipped_action_count=skipped,
        action_reviews=reviews,
    )


def _load_fcpxml_repair_plan(root: Path, project_id: str) -> FcpxmlRepairPlan:
    path = root / WORKSPACE_DIR / DATA_DIR / "fcpxml_repair_plan.json"
    if not path.exists():
        raise FcpxmlWriterError("FCPXML repair plan is required")
    plan = FcpxmlRepairPlan.model_validate_json(path.read_text(encoding="utf-8"))
    if plan.project_id != project_id:
        raise FcpxmlWriterError("FCPXML repair plan project_id does not match project")
    return plan


def _xml_parse_passed(xml_text: str) -> bool:
    try:
        ET.fromstring(xml_text.split("\n", 2)[2])
    except ET.ParseError:
        return False
    return True


def _frame_duration(frame_rate: float) -> str:
    fps = max(int(round(frame_rate)), 1)
    return f"1/{fps}s"


def _seconds(value: float) -> str:
    return f"{max(value, 0.0):.6f}s"
