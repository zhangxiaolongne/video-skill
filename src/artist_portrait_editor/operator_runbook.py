from __future__ import annotations

import hashlib
from pathlib import Path

from pydantic import BaseModel

from artist_portrait_editor.constants import DATA_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.acceptance import ProjectAcceptanceReport
from artist_portrait_editor.models.bgm import (
    BgmAnalysisReport,
    BgmCandidateLedger,
    BgmRhythmIntelligenceReport,
)
from artist_portrait_editor.models.final_export import FinalExportValidationReport
from artist_portrait_editor.models.operator import (
    OperatorArtifactStatus,
    OperatorBgmInputGuidance,
    OperatorRunbook,
    OperatorStage,
)
from artist_portrait_editor.models.preview import PreviewValidationReport
from artist_portrait_editor.models.rhythm import (
    EditGuidanceReport,
    RhythmMediaQcReport,
    RhythmPlan,
    RhythmRepairPlan,
)
from artist_portrait_editor.models.state import ProjectState
from artist_portrait_editor.models.workflow import WorkflowPlan
from artist_portrait_editor.run_records import write_json
from artist_portrait_editor.workflow import build_workflow_plan


OPERATOR_TARGETS = {"core", "preview", "delivery"}


def build_operator_runbook(
    *,
    root: Path,
    project_id: str,
    target: str,
    state: ProjectState | None,
) -> tuple[Path, Path, Path, OperatorRunbook]:
    if target not in OPERATOR_TARGETS:
        raise ValueError(f"unsupported operator target: {target}")

    workflow = _load_or_build_workflow(root=root, project_id=project_id, target=target, state=state)
    acceptance = _read_optional(
        root / WORKSPACE_DIR / DATA_DIR / "acceptance_report.json",
        ProjectAcceptanceReport,
    )
    rhythm_plan = _read_optional(root / WORKSPACE_DIR / DATA_DIR / "rhythm_plan.json", RhythmPlan)
    rhythm_qc = _read_optional(
        root / WORKSPACE_DIR / DATA_DIR / "rhythm_media_qc.json",
        RhythmMediaQcReport,
    )
    rhythm_repair = _read_optional(
        root / WORKSPACE_DIR / DATA_DIR / "rhythm_repair_plan.json",
        RhythmRepairPlan,
    )
    edit_guidance = _read_optional(
        root / WORKSPACE_DIR / DATA_DIR / "edit_guidance.json",
        EditGuidanceReport,
    )
    bgm_ledger = _read_optional(
        root / WORKSPACE_DIR / DATA_DIR / "bgm_candidates.json",
        BgmCandidateLedger,
    )
    bgm_analysis = _read_optional(
        root / WORKSPACE_DIR / DATA_DIR / "bgm_analysis.json",
        BgmAnalysisReport,
    )
    bgm_rhythm = _read_optional(
        root / WORKSPACE_DIR / DATA_DIR / "bgm_rhythm_intelligence.json",
        BgmRhythmIntelligenceReport,
    )
    preview_validation = _read_optional(
        root / WORKSPACE_DIR / DATA_DIR / "preview_validation.json",
        PreviewValidationReport,
    )
    final_validation = _read_optional(
        root / WORKSPACE_DIR / DATA_DIR / "final_export_validation.json",
        FinalExportValidationReport,
    )
    artifact_map = _artifact_map(
        root=root,
        workflow=workflow,
        acceptance=acceptance,
        rhythm_plan=rhythm_plan,
        rhythm_qc=rhythm_qc,
        edit_guidance=edit_guidance,
        bgm_ledger=bgm_ledger,
        bgm_analysis=bgm_analysis,
        bgm_rhythm=bgm_rhythm,
        preview_validation=preview_validation,
        final_validation=final_validation,
    )
    stages = _operator_stages(
        workflow=workflow,
        acceptance=acceptance,
        rhythm_plan=rhythm_plan,
        rhythm_qc=rhythm_qc,
        rhythm_repair=rhythm_repair,
        edit_guidance=edit_guidance,
        bgm_rhythm=bgm_rhythm,
        preview_validation=preview_validation,
        final_validation=final_validation,
    )
    bgm_guidance = _bgm_input_guidance(bgm_ledger=bgm_ledger, bgm_rhythm=bgm_rhythm)
    manual_refs = [
        ref
        for ref in (
            "output/edit_guidance.md" if edit_guidance else None,
            "output/rhythm_report.md" if rhythm_plan else None,
            "output/rhythm_media_qc.md" if rhythm_qc else None,
            "output/workflow_plan.md" if workflow else None,
            "output/acceptance_report.md" if acceptance else None,
        )
        if ref is not None
    ]
    done = sum(stage.status == "done" for stage in stages)
    pending = sum(stage.status in {"current", "pending"} for stage in stages)
    blocked = sum(stage.status == "blocked" for stage in stages)
    warnings = sum(stage.status == "warning" for stage in stages)
    present_artifacts = sum(artifact.status == "present" for artifact in artifact_map)
    next_stage = _next_operator_stage(stages)
    status = (
        "blocked"
        if blocked
        else "warning"
        if warnings
        else "ready"
        if pending == 0 and workflow.status == "ready"
        else "in_progress"
    )
    key = (
        f"{project_id}:{target}:{workflow.workflow_plan_id}:{acceptance.acceptance_id if acceptance else 'none'}:"
        f"{rhythm_plan.rhythm_plan_id if rhythm_plan else 'none'}:{edit_guidance.edit_guidance_id if edit_guidance else 'none'}:"
        f"{done}:{pending}:{blocked}:{warnings}:{next_stage.command if next_stage else 'none'}"
    )
    runbook = OperatorRunbook(
        operator_runbook_id="operator_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=project_id,
        target=target,
        status=status,
        workflow_plan_id=workflow.workflow_plan_id,
        acceptance_id=acceptance.acceptance_id if acceptance else None,
        rhythm_plan_id=rhythm_plan.rhythm_plan_id if rhythm_plan else None,
        rhythm_qc_id=rhythm_qc.rhythm_qc_id if rhythm_qc else None,
        edit_guidance_id=edit_guidance.edit_guidance_id if edit_guidance else None,
        bgm_rhythm_intelligence_id=(
            bgm_rhythm.bgm_rhythm_intelligence_id if bgm_rhythm else None
        ),
        next_command=next_stage.command if next_stage else None,
        stage_count=len(stages),
        done_stage_count=done,
        pending_stage_count=pending,
        blocked_stage_count=blocked,
        warning_stage_count=warnings,
        artifact_count=len(artifact_map),
        present_artifact_count=present_artifacts,
        stages=stages,
        artifact_map=artifact_map,
        bgm_input_guidance=bgm_guidance,
        manual_guidance_refs=manual_refs,
        forbidden_capabilities=[
            "execute workflow or repair commands",
            "auto-run pipeline stages",
            "render preview or final media",
            "mutate the timeline",
            "move edit points",
            "select or fit music automatically",
            "fabricate BPM or beat grids",
            "call models from the CLI",
            "access the network",
            "use image generation or editing",
            "treat mixed extracted video audio as clean BGM",
        ],
    )

    json_path = root / WORKSPACE_DIR / DATA_DIR / "operator_runbook.json"
    md_path = root / "output" / "operator_runbook.md"
    handoff_path = root / "output" / "operator_handoff.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, runbook.model_dump(mode="json"))
    md_path.write_text(render_operator_runbook(runbook) + "\n", encoding="utf-8")
    write_json(handoff_path, _operator_handoff(runbook))
    return json_path, md_path, handoff_path, runbook


def render_operator_runbook(runbook: OperatorRunbook) -> str:
    lines = [
        "# Operator Runbook",
        "",
        "This runbook summarizes the current project state and next manual command. It does not execute commands, render media, mutate the timeline, select music, call models, access the network, or use image generation.",
        "",
        f"- Target: `{runbook.target}`",
        f"- Status: `{runbook.status}`",
        f"- Next command: `{runbook.next_command or 'none'}`",
        f"- Workflow plan: `{runbook.workflow_plan_id or 'none'}`",
        f"- Acceptance: `{runbook.acceptance_id or 'none'}`",
        f"- Rhythm plan: `{runbook.rhythm_plan_id or 'none'}`",
        f"- Edit guidance: `{runbook.edit_guidance_id or 'none'}`",
        f"- Stages: `{runbook.done_stage_count}` done, `{runbook.pending_stage_count}` pending, `{runbook.blocked_stage_count}` blocked, `{runbook.warning_stage_count}` warning",
        "",
        "## Stage Ladder",
        "",
    ]
    for stage in runbook.stages:
        lines.extend(
            [
                f"### `{stage.order:02d}` `{stage.stage_id}`",
                "",
                f"- Phase: `{stage.phase}`",
                f"- Status: `{stage.status}`",
                f"- Source: `{stage.source}`",
                f"- Command: `{stage.command}`",
                f"- Summary: {stage.summary}",
            ]
        )
        if stage.evidence_refs:
            lines.append(f"- Evidence: {', '.join(f'`{ref}`' for ref in stage.evidence_refs)}")
        if stage.blocking_refs:
            lines.append(f"- Blocking refs: {', '.join(f'`{ref}`' for ref in stage.blocking_refs)}")
        lines.append("")
    lines.extend(["## Artifact Map", ""])
    for artifact in runbook.artifact_map:
        lines.append(
            f"- `{artifact.ref}`: `{artifact.status}`; current binding `{artifact.bound_to_current_context}`; {artifact.summary}"
        )
    lines.extend(["", "## BGM Input Guidance", ""])
    for item in runbook.bgm_input_guidance:
        refs = f" Evidence: {', '.join(f'`{ref}`' for ref in item.evidence_refs)}" if item.evidence_refs else ""
        lines.append(f"- `{item.mode}` `{item.status}`: {item.guidance}{refs}")
    lines.extend(["", "## Manual Guidance Refs", ""])
    if runbook.manual_guidance_refs:
        lines.extend(f"- `{ref}`" for ref in runbook.manual_guidance_refs)
    else:
        lines.append("- `none`")
    lines.extend(["", "## Forbidden Capabilities", ""])
    lines.extend(f"- {item}" for item in runbook.forbidden_capabilities)
    return "\n".join(lines)


def _next_operator_stage(stages: list[OperatorStage]) -> OperatorStage | None:
    next_stage = next((stage for stage in stages if stage.status in {"blocked", "current"}), None)
    if next_stage is None or next_stage.stage_id != "operator":
        return next_stage
    later_workflow_stage = next(
        (
            stage
            for stage in stages
            if stage.source == "workflow"
            and stage.order > next_stage.order
            and stage.status in {"blocked", "current", "pending"}
        ),
        None,
    )
    return later_workflow_stage or next_stage


def _operator_handoff(runbook: OperatorRunbook) -> dict:
    return {
        "handoff_type": "operator_runbook",
        "project_id": runbook.project_id,
        "target": runbook.target,
        "status": runbook.status,
        "next_command": runbook.next_command,
        "operator_runbook_ref": ".artist-portrait/data/operator_runbook.json",
        "operator_report_ref": "output/operator_runbook.md",
        "manual_guidance_refs": runbook.manual_guidance_refs,
        "forbidden_capabilities": runbook.forbidden_capabilities,
        "commands_executed": False,
        "media_rendered": False,
        "timeline_mutated": False,
        "edit_points_moved": False,
        "automatic_music_selection": False,
        "model_call_performed_by_cli": False,
        "network_performed": False,
    }


def _load_or_build_workflow(
    *,
    root: Path,
    project_id: str,
    target: str,
    state: ProjectState | None,
) -> WorkflowPlan:
    _, _, _, plan = build_workflow_plan(root=root, project_id=project_id, target=target, state=state)
    return plan


def _artifact_map(
    *,
    root: Path,
    workflow: WorkflowPlan,
    acceptance: ProjectAcceptanceReport | None,
    rhythm_plan: RhythmPlan | None,
    rhythm_qc: RhythmMediaQcReport | None,
    edit_guidance: EditGuidanceReport | None,
    bgm_ledger: BgmCandidateLedger | None,
    bgm_analysis: BgmAnalysisReport | None,
    bgm_rhythm: BgmRhythmIntelligenceReport | None,
    preview_validation: PreviewValidationReport | None,
    final_validation: FinalExportValidationReport | None,
) -> list[OperatorArtifactStatus]:
    specs = [
        ("workflow_plan", ".artist-portrait/data/workflow_plan.json", workflow, True),
        ("workflow_plan_md", "output/workflow_plan.md", workflow, True),
        ("acceptance", ".artist-portrait/data/acceptance_report.json", acceptance, acceptance is not None),
        ("rhythm_plan", ".artist-portrait/data/rhythm_plan.json", rhythm_plan, rhythm_plan is not None),
        ("rhythm_qc", ".artist-portrait/data/rhythm_media_qc.json", rhythm_qc, rhythm_qc is not None),
        ("edit_guidance", ".artist-portrait/data/edit_guidance.json", edit_guidance, edit_guidance is not None),
        ("bgm_candidates", ".artist-portrait/data/bgm_candidates.json", bgm_ledger, bgm_ledger is not None),
        ("bgm_analysis", ".artist-portrait/data/bgm_analysis.json", bgm_analysis, bgm_analysis is not None),
        (
            "bgm_rhythm_intelligence",
            ".artist-portrait/data/bgm_rhythm_intelligence.json",
            bgm_rhythm,
            bgm_rhythm is not None,
        ),
        ("preview_validation", ".artist-portrait/data/preview_validation.json", preview_validation, preview_validation is not None),
        ("final_export_validation", ".artist-portrait/data/final_export_validation.json", final_validation, final_validation is not None),
        ("workflow_execution_review", ".artist-portrait/data/workflow_execution_review.json", None, True),
        ("editor_package", ".artist-portrait/data/editor_package.json", None, True),
        ("editor_package_md", "output/editor_package.md", None, True),
        ("cue_sheet", "output/cue_sheet.csv", None, True),
        ("nle_interchange_plan", ".artist-portrait/data/nle_interchange_plan.json", None, True),
        ("nle_interchange_map", "output/nle_interchange_map.csv", None, True),
        ("fcpxml_draft", ".artist-portrait/data/fcpxml_draft.json", None, True),
        ("fcpxml_file", "output/draft.fcpxml", None, True),
        ("fcpxml_validation", ".artist-portrait/data/fcpxml_validation.json", None, True),
        ("fcpxml_import_review", ".artist-portrait/data/fcpxml_import_review.json", None, True),
        ("fcpxml_repair_plan", ".artist-portrait/data/fcpxml_repair_plan.json", None, True),
    ]
    artifacts: list[OperatorArtifactStatus] = []
    for artifact_id, ref, model, bound in specs:
        exists = (root / ref).exists()
        status = "present" if exists else "missing"
        if exists and model is None and not bound:
            status = "stale_or_unknown"
        artifacts.append(
            OperatorArtifactStatus(
                artifact_id=artifact_id,
                ref=ref,
                status=status,
                bound_to_current_context=bound if exists else None,
                summary=_artifact_summary(artifact_id, model),
            )
        )
    return artifacts


def _operator_stages(
    *,
    workflow: WorkflowPlan,
    acceptance: ProjectAcceptanceReport | None,
    rhythm_plan: RhythmPlan | None,
    rhythm_qc: RhythmMediaQcReport | None,
    rhythm_repair: RhythmRepairPlan | None,
    edit_guidance: EditGuidanceReport | None,
    bgm_rhythm: BgmRhythmIntelligenceReport | None,
    preview_validation: PreviewValidationReport | None,
    final_validation: FinalExportValidationReport | None,
) -> list[OperatorStage]:
    stages: list[OperatorStage] = []
    for workflow_step in workflow.steps:
        status = {
            "done": "done",
            "next": "current",
            "pending": "pending",
            "blocked": "blocked",
            "optional": "warning",
        }[workflow_step.status]
        stages.append(
            OperatorStage(
                stage_id=workflow_step.step_id,
                order=len(stages) + 1,
                phase=workflow_step.phase,
                status=status,
                command=workflow_step.command,
                summary=workflow_step.rationale,
                evidence_refs=workflow_step.expected_artifacts,
                blocking_refs=[] if status in {"done", "pending"} else workflow_step.expected_artifacts,
                source=workflow_step.source if workflow_step.source in {"workflow", "acceptance"} else "rhythm",
            )
        )
    _append_if_present(
        stages,
        "bgm_rhythm_intelligence",
        "sound",
        "bgm",
        bgm_rhythm.status if bgm_rhythm else None,
        "artist-portrait bgm rhythm --project <project.yaml>",
        "BGM rhythm risk and phrase hints are available for manual rhythm planning.",
        [".artist-portrait/data/bgm_rhythm_intelligence.json", "output/bgm_rhythm_intelligence.md"],
    )
    _append_if_present(
        stages,
        "rhythm_plan",
        "rhythm",
        "rhythm",
        rhythm_plan.status if rhythm_plan else None,
        "artist-portrait rhythm --project <project.yaml>",
        "Timeline/BGM rhythm plan is available for preview and manual edit review.",
        [".artist-portrait/data/rhythm_plan.json", "output/rhythm_report.md"],
    )
    _append_if_present(
        stages,
        "edit_guidance",
        "manual_edit",
        "rhythm",
        edit_guidance.status if edit_guidance else None,
        "artist-portrait rhythm --project <project.yaml> --edit-guidance",
        "Phrase-level manual edit guidance is available.",
        [".artist-portrait/data/edit_guidance.json", "output/edit_guidance.md"],
    )
    _append_if_present(
        stages,
        "rhythm_media_qc",
        "qc",
        "rhythm",
        rhythm_qc.status if rhythm_qc else None,
        "artist-portrait rhythm --project <project.yaml> --qc",
        "Rendered media can be reviewed against rhythm evidence.",
        [".artist-portrait/data/rhythm_media_qc.json", "output/rhythm_media_qc.md"],
    )
    _append_if_present(
        stages,
        "rhythm_repair_plan",
        "repair",
        "rhythm",
        rhythm_repair.status if rhythm_repair else None,
        "artist-portrait rhythm --project <project.yaml> --repair-plan",
        "Rhythm gaps have an ordered manual repair plan.",
        [".artist-portrait/data/rhythm_repair_plan.json", "output/rhythm_repair_plan.md"],
    )
    _append_if_present(
        stages,
        "preview_validation",
        "media",
        "operator",
        preview_validation.quality_status if preview_validation else None,
        "artist-portrait preview --project <project.yaml>",
        "Preview media validation evidence is available.",
        [".artist-portrait/data/preview_validation.json", "output/preview_validation.md"],
    )
    _append_if_present(
        stages,
        "final_export_validation",
        "delivery",
        "operator",
        final_validation.quality_status if final_validation else None,
        "artist-portrait export --project <project.yaml> --profile review_720p",
        "Final export validation evidence is available.",
        [".artist-portrait/data/final_export_validation.json", "output/final_export_validation.md"],
    )
    _append_if_present(
        stages,
        "acceptance",
        "acceptance",
        "acceptance",
        acceptance.status if acceptance else None,
        "artist-portrait acceptance --project <project.yaml> --profile delivery",
        "Acceptance profile status is available.",
        [".artist-portrait/data/acceptance_report.json", "output/acceptance_report.md"],
    )
    return stages


def _append_if_present(
    stages: list[OperatorStage],
    stage_id: str,
    phase: str,
    source: str,
    raw_status: str | None,
    command: str,
    summary: str,
    evidence_refs: list[str],
) -> None:
    if raw_status is None:
        return
    status = _normalize_status(raw_status)
    stages.append(
        OperatorStage(
            stage_id=stage_id,
            order=len(stages) + 1,
            phase=phase,
            status=status,
            command=command,
            summary=summary,
            evidence_refs=evidence_refs,
            blocking_refs=evidence_refs if status in {"blocked", "warning", "current"} else [],
            source=source,
        )
    )


def _normalize_status(raw_status: str) -> str:
    if raw_status in {"ready", "passed", "no_actions"}:
        return "done"
    if raw_status in {"warning", "in_progress"}:
        return "warning"
    if raw_status in {"failed", "blocked"}:
        return "blocked"
    return "warning"


def _bgm_input_guidance(
    *,
    bgm_ledger: BgmCandidateLedger | None,
    bgm_rhythm: BgmRhythmIntelligenceReport | None,
) -> list[OperatorBgmInputGuidance]:
    modes = {candidate.input_mode.value for candidate in bgm_ledger.candidates} if bgm_ledger else set()
    mixed_refs = []
    if bgm_ledger:
        mixed_refs = [
            f".artist-portrait/data/bgm_candidates.json#{candidate.music_candidate_id}"
            for candidate in bgm_ledger.candidates
            if candidate.mixed_audio
        ]
    guidance = [
        OperatorBgmInputGuidance(
            mode="direct_audio",
            status="available" if "direct_audio" in modes else "missing",
            guidance="Use uploaded local audio when the user supplies a clean music file.",
            evidence_refs=[".artist-portrait/data/bgm_candidates.json"] if "direct_audio" in modes else [],
        ),
        OperatorBgmInputGuidance(
            mode="video_audio_extract",
            status="warning" if mixed_refs else "available" if "video_audio_extract" in modes else "missing",
            guidance="Extracted video audio must preserve stream, range, hash, and mixed-audio risk; never treat a mixed video track as clean BGM.",
            evidence_refs=mixed_refs or ([".artist-portrait/data/bgm_candidates.json"] if "video_audio_extract" in modes else []),
        ),
        OperatorBgmInputGuidance(
            mode="source_embedded_audio",
            status="available" if "source_embedded_audio" in modes else "missing",
            guidance="Embedded source audio can be retained when it is part of the selected canonical source evidence.",
            evidence_refs=[".artist-portrait/data/bgm_candidates.json"] if "source_embedded_audio" in modes else [],
        ),
        OperatorBgmInputGuidance(
            mode="no_file_yet",
            status="warning" if not bgm_ledger or not bgm_ledger.candidates else "available",
            guidance="If no BGM file exists yet, keep music slots unresolved and use host-Agent/local-model handoff only for explicit recommendation review.",
            evidence_refs=[".artist-portrait/data/bgm_rhythm_intelligence.json"] if bgm_rhythm else [],
        ),
    ]
    return guidance


def _artifact_summary(artifact_id: str, model: BaseModel | None) -> str:
    if model is None:
        return "artifact is absent or could not be parsed into the current model"
    for attr in (
        "status",
        "quality_status",
        "acceptance_profile",
        "target",
        "project_id",
    ):
        if hasattr(model, attr):
            return f"{attr}={getattr(model, attr)}"
    return artifact_id


def _read_optional(path: Path, model: type[BaseModel]):
    if not path.exists():
        return None
    return model.model_validate_json(path.read_text(encoding="utf-8"))
