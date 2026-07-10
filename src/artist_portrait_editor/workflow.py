from __future__ import annotations

import hashlib
from pathlib import Path

from artist_portrait_editor.constants import DATA_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.acceptance import ProjectAcceptanceReport
from artist_portrait_editor.models.rhythm import RhythmRepairPlan
from artist_portrait_editor.models.state import ProjectState, StepStatus
from artist_portrait_editor.models.workflow import (
    CreatorWorkflowDeliverable,
    CreatorWorkflowStage,
    WorkflowExecutionRecord,
    WorkflowExecutionReview,
    WorkflowExecutionStepReview,
    WorkflowPlan,
    WorkflowStep,
)
from artist_portrait_editor.run_records import write_json


WORKFLOW_TARGETS = {"core", "preview", "delivery"}


class WorkflowExecutionReviewError(RuntimeError):
    pass


def build_workflow_plan(
    *,
    root: Path,
    project_id: str,
    target: str,
    state: ProjectState | None,
) -> tuple[Path, Path, Path, WorkflowPlan]:
    if target not in WORKFLOW_TARGETS:
        raise ValueError(f"unsupported workflow target: {target}")
    acceptance = _read_optional(root / WORKSPACE_DIR / DATA_DIR / "acceptance_report.json", ProjectAcceptanceReport)
    rhythm_repair = _read_optional(root / WORKSPACE_DIR / DATA_DIR / "rhythm_repair_plan.json", RhythmRepairPlan)
    steps = _workflow_steps(root, target, state, acceptance, rhythm_repair)
    next_step = next((step for step in steps if step.status in {"next", "blocked"}), None)
    creator_stages = _creator_stages(steps, target)
    deliverables = _creator_deliverables(root, target)
    current_stage = next(
        (stage for stage in creator_stages if stage.status in {"current", "blocked"}),
        None,
    )
    completed = sum(step.status == "done" for step in steps)
    blocked = sum(step.status == "blocked" for step in steps)
    remaining = sum(step.status in {"next", "pending", "blocked"} for step in steps)
    status = "ready" if remaining == 0 else "blocked" if blocked else "in_progress"
    key = (
        f"{project_id}:{target}:{completed}:{remaining}:{blocked}:"
        f"{next_step.command if next_step else 'none'}:"
        f"{current_stage.stage_id if current_stage else 'none'}"
    )
    plan = WorkflowPlan(
        workflow_plan_id="workflow_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=project_id,
        target=target,
        status=status,
        next_command=next_step.command if next_step else None,
        completed_step_count=completed,
        remaining_step_count=remaining,
        blocked_step_count=blocked,
        steps=steps,
        creator_stage_count=len(creator_stages),
        current_stage_id=current_stage.stage_id if current_stage else None,
        current_stage_title=current_stage.title if current_stage else None,
        creator_stages=creator_stages,
        deliverables=deliverables,
        bgm_input_guidance=_workflow_bgm_guidance(target),
    )
    json_path = root / WORKSPACE_DIR / DATA_DIR / "workflow_plan.json"
    md_path = root / "output" / "workflow_plan.md"
    handoff_path = root / "output" / "workflow_agent_handoff.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, plan.model_dump(mode="json"))
    md_path.write_text(render_workflow_plan(plan) + "\n", encoding="utf-8")
    write_json(handoff_path, _workflow_handoff(plan))
    return json_path, md_path, handoff_path, plan


def render_workflow_plan(plan: WorkflowPlan) -> str:
    lines = [
        "# Workflow Plan",
        "",
        "This plan orders explicit user-visible commands. It does not execute commands, render media, move edit points, select music, call models, or access the network.",
        "",
        f"- Target: `{plan.target}`",
        f"- Status: `{plan.status}`",
        f"- Next command: `{plan.next_command or 'none'}`",
        f"- Current creator stage: `{plan.current_stage_title or 'none'}`",
        f"- Completed steps: `{plan.completed_step_count}`",
        f"- Remaining steps: `{plan.remaining_step_count}`",
        "",
        "## Creator Path",
        "",
    ]
    for stage in plan.creator_stages:
        lines.extend(
            [
                f"### `{stage.stage_id}` {stage.title}",
                "",
                f"- Status: `{stage.status}`",
                f"- Next command: `{stage.next_command or 'none'}`",
                f"- Summary: {stage.summary}",
            ]
        )
        if stage.deliverable_refs:
            lines.append(
                f"- Deliverables: {', '.join(f'`{ref}`' for ref in stage.deliverable_refs)}"
            )
        lines.append("")
    if plan.deliverables:
        lines.extend(["## Deliverables", ""])
        for deliverable in plan.deliverables:
            lines.extend(
                [
                    f"- `{deliverable.deliverable_id}`: `{deliverable.status}` - {deliverable.summary}",
                ]
            )
        lines.append("")
    if plan.bgm_input_guidance:
        lines.extend(["## BGM Input Guidance", ""])
        for item in plan.bgm_input_guidance:
            lines.append(f"- {item}")
        lines.append("")
    lines.extend(["## Command Steps", ""])
    for step in plan.steps:
        lines.extend(
            [
                f"## `{step.step_id}`",
                "",
                f"- Phase: `{step.phase}`",
                f"- Status: `{step.status}`",
                f"- Source: `{step.source}`",
                f"- Command: `{step.command}`",
                f"- Rationale: {step.rationale}",
            ]
        )
        if step.expected_artifacts:
            lines.append(
                f"- Expected artifacts: {', '.join(f'`{ref}`' for ref in step.expected_artifacts)}"
            )
        lines.append("")
    return "\n".join(lines)


def import_workflow_execution_record(
    *,
    root: Path,
    project_id: str,
    target: str,
    candidate_path: Path,
    state: ProjectState | None,
) -> tuple[Path, Path, Path, WorkflowExecutionReview]:
    plan_path = root / WORKSPACE_DIR / DATA_DIR / "workflow_plan.json"
    if plan_path.exists():
        plan = WorkflowPlan.model_validate_json(plan_path.read_text(encoding="utf-8"))
    else:
        _, _, _, plan = build_workflow_plan(
            root=root,
            project_id=project_id,
            target=target,
            state=state,
        )
    if plan.project_id != project_id or plan.target != target:
        raise WorkflowExecutionReviewError("current workflow plan does not match project or target")
    if not candidate_path.exists():
        raise WorkflowExecutionReviewError(f"workflow execution record not found: {candidate_path}")

    data = candidate_path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    quarantine_path = root / WORKSPACE_DIR / DATA_DIR / "workflow_execution_record_quarantine.json"
    quarantine_path.parent.mkdir(parents=True, exist_ok=True)
    quarantine_path.write_bytes(data)
    record = WorkflowExecutionRecord.model_validate_json(data.decode("utf-8"))
    review = _review_execution_record(
        root=root,
        plan=plan,
        record=record,
        quarantine_ref=quarantine_path.relative_to(root).as_posix(),
        candidate_sha256=digest,
        candidate_bytes=len(data),
    )
    json_path = root / WORKSPACE_DIR / DATA_DIR / "workflow_execution_review.json"
    md_path = root / "output" / "workflow_execution_review.md"
    handoff_path = root / "output" / "workflow_execution_handoff.json"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, review.model_dump(mode="json"))
    md_path.write_text(render_workflow_execution_review(review) + "\n", encoding="utf-8")
    write_json(handoff_path, _workflow_execution_handoff(review))
    return json_path, md_path, handoff_path, review


def render_workflow_execution_review(review: WorkflowExecutionReview) -> str:
    lines = [
        "# Workflow Execution Review",
        "",
        "This review validates an explicit external execution record. It does not execute commands, render media, move edit points, select music, call models, or access the network.",
        "",
        f"- Target: `{review.target}`",
        f"- Status: `{review.status}`",
        f"- Workflow plan: `{review.workflow_plan_id}`",
        f"- Quarantine: `{review.quarantine_ref}`",
        f"- Candidate SHA-256: `{review.candidate_sha256}`",
        f"- Accepted steps: `{review.accepted_step_count}`",
        f"- Rejected steps: `{review.rejected_step_count}`",
        f"- Missing steps: `{review.missing_step_count}`",
        f"- Skipped steps: `{review.skipped_step_count}`",
        "",
    ]
    for step in review.step_reviews:
        lines.extend(
            [
                f"## `{step.step_id}`",
                "",
                f"- Review status: `{step.review_status}`",
                f"- Planned status: `{step.planned_status or 'none'}`",
                f"- Submitted status: `{step.submitted_status or 'none'}`",
                f"- Command matched: `{str(step.command_matched).lower()}`",
                f"- Detail: {step.detail}",
            ]
        )
        if step.evidence_refs:
            lines.append(f"- Evidence refs: {', '.join(f'`{ref}`' for ref in step.evidence_refs)}")
        if step.missing_refs:
            lines.append(f"- Missing refs: {', '.join(f'`{ref}`' for ref in step.missing_refs)}")
        lines.append("")
    return "\n".join(lines)


def _workflow_steps(
    root: Path,
    target: str,
    state: ProjectState | None,
    acceptance: ProjectAcceptanceReport | None,
    rhythm_repair: RhythmRepairPlan | None,
) -> list[WorkflowStep]:
    base = [
        ("init", "foundation", "artist-portrait init --project <project.yaml>", [".artist-portrait/state.json"], "Initialize the project workspace."),
        ("scan", "media", "artist-portrait scan --project <project.yaml>", [".artist-portrait/data/sources.jsonl", "output/scan_report.md"], "Scan source media into the canonical source ledger."),
        ("segment", "media", "artist-portrait segment --project <project.yaml>", [".artist-portrait/data/clips.jsonl", "output/clip_report.md"], "Create deterministic clip records from sources."),
        ("analyze", "evidence", "artist-portrait analyze --project <project.yaml>", [".artist-portrait/data/analysis.jsonl", "output/analysis_report.md"], "Create evidence-only analysis records."),
        ("map", "evidence", "artist-portrait map --project <project.yaml>", ["output/material_map.md"], "Create the analysis-led material map."),
        ("brief", "creative", "artist-portrait brief --project <project.yaml>", [".artist-portrait/data/edit_brief.json", "output/edit_brief.md"], "Decide target duration and editing intent before proposal generation."),
        ("score", "creative", "artist-portrait score --project <project.yaml>", [".artist-portrait/data/clip_scores.jsonl", "output/clip_score_report.md"], "Score clips from transcript, audio, scene, keyframe, analysis, and brief evidence."),
        ("propose", "creative", "artist-portrait propose --project <project.yaml>", ["output/proposal_agent_handoff.json"], "Prepare the host-Agent proposal handoff."),
        ("proposal_import", "creative", "artist-portrait propose --project <project.yaml> --agent-output <candidate.json>", [".artist-portrait/data/proposals.json", ".artist-portrait/data/proposal_validation.json"], "Import and validate an explicit host-Agent proposal candidate."),
        ("timeline", "timeline", "artist-portrait timeline --project <project.yaml> --proposal <id>", ["output/timeline_draft.json"], "Generate a score-aware hook/build/payoff canonical timeline from the selected proposal, edit brief, and clip scores."),
        ("sound", "sound", "artist-portrait sound --project <project.yaml>", [".artist-portrait/data/sound_decision.json", "output/sound_decision.md"], "Choose original audio, BGM input mode, silence, ducking, fades, and beat fallback before rhythm or rendering."),
    ]
    if target in {"preview", "delivery"}:
        base.extend(
            [
                ("bgm_import_or_fit", "sound", "artist-portrait bgm import --project <project.yaml> --file <audio-or-video> --rights-status <status>", [".artist-portrait/data/bgm_candidates.json"], "Import or select BGM evidence when the sound decision requires music."),
                ("bgm_fit", "sound", "artist-portrait bgm fit --project <project.yaml> --candidate <id>", [".artist-portrait/data/bgm_fit.json"], "Fit the explicit BGM candidate to the timeline when needed."),
                ("rhythm", "rhythm", "artist-portrait rhythm --project <project.yaml>", [".artist-portrait/data/rhythm_plan.json", "output/rhythm_report.md"], "Plan BGM/edit rhythm before preview review."),
                ("preview", "media", "artist-portrait preview --project <project.yaml>", [".artist-portrait/data/preview_validation.json", "output/preview_lowres.mp4"], "Render and validate low-resolution preview media."),
                ("rhythm_qc_preview", "rhythm", "artist-portrait rhythm --project <project.yaml> --qc", [".artist-portrait/data/rhythm_media_qc.json", "output/rhythm_media_qc.md"], "Check preview media against rhythm evidence."),
                ("cut_review", "review", "artist-portrait cut-review --project <project.yaml>", [".artist-portrait/data/cut_review.json", "output/cut_review.md"], "Review the rendered preview as an editorial cut and propose a manual second pass."),
                ("revision", "revision", 'artist-portrait revise --project <project.yaml> --intent "<user note>"', [".artist-portrait/data/revision_plan.json", "output/revision_plan.md"], "Convert the user's explicit revision note into comparable manual revision candidates without applying edits."),
                ("revision_application", "revision", "artist-portrait apply-revision --project <project.yaml> --version-id revision_candidate_1", [".artist-portrait/data/revision_application.json", "output/revision_application.md"], "Apply an explicit revision candidate into a controlled revised timeline candidate without mutating the canonical timeline or rendering media."),
                ("revision_promotion", "revision", "artist-portrait promote-revision --project <project.yaml> --revision-application-id <id>", [".artist-portrait/data/revision_promotion.json", "output/revision_promotion.md", "output/timeline_draft.json"], "Promote the explicit revised timeline candidate into the canonical timeline, then rerun media review steps."),
                ("acceptance_preview", "acceptance", "artist-portrait acceptance --project <project.yaml> --profile preview", [".artist-portrait/data/acceptance_report.json", "output/acceptance_report.md"], "Evaluate preview readiness."),
            ]
        )
    if target == "delivery":
        base.extend(
            [
                ("final_export", "delivery", "artist-portrait export --project <project.yaml> --profile review_720p", [".artist-portrait/data/final_export_validation.json", "output/final_export.mp4"], "Render and validate delivery-review export."),
                ("rhythm_qc_delivery", "rhythm", "artist-portrait rhythm --project <project.yaml> --qc", [".artist-portrait/data/rhythm_media_qc.json", "output/rhythm_media_qc.md"], "Refresh rhythm QC against final export."),
                ("cut_review", "review", "artist-portrait cut-review --project <project.yaml>", [".artist-portrait/data/cut_review.json", "output/cut_review.md"], "Review the final cut evidence and propose a manual second pass."),
                ("acceptance_delivery", "acceptance", "artist-portrait acceptance --project <project.yaml> --profile delivery", [".artist-portrait/data/acceptance_report.json", "output/acceptance_report.md"], "Evaluate delivery readiness."),
                ("operator", "handoff", "artist-portrait operator --project <project.yaml> --target delivery", [".artist-portrait/data/operator_runbook.json", "output/operator_runbook.md"], "Summarize the project into one operator-facing runbook."),
                ("editor_package", "handoff", "artist-portrait editor-package --project <project.yaml>", [".artist-portrait/data/editor_package.json", "output/editor_package.md", "output/cue_sheet.csv"], "Create editor-facing package, cue sheet, and handoff instructions."),
                ("nle_plan", "handoff", "artist-portrait nle-plan --project <project.yaml> --target all", [".artist-portrait/data/nle_interchange_plan.json", "output/nle_interchange_plan.md", "output/nle_interchange_map.csv"], "Map the editor package into NLE interchange targets."),
                ("fcpxml_draft", "handoff", "artist-portrait fcpxml --project <project.yaml> --draft", [".artist-portrait/data/fcpxml_draft.json", ".artist-portrait/data/fcpxml_validation.json", "output/draft.fcpxml", "output/fcpxml_review.md"], "Write a supervised relink-required FCPXML draft for editor review."),
            ]
        )
    steps: list[WorkflowStep] = []
    first_open_seen = False
    for index, (step_id, phase, command, artifacts, rationale) in enumerate(base, start=1):
        done = _step_done(root, state, step_id, artifacts)
        status = "done" if done else "next" if not first_open_seen else "pending"
        if not done:
            first_open_seen = True
        steps.append(
            WorkflowStep(
                step_id=step_id,
                order=index,
                phase=phase,
                status=status,
                command=command,
                rationale=rationale,
                expected_artifacts=artifacts,
                source="workflow",
            )
        )
    if acceptance and acceptance.status == "failed":
        for stage in acceptance.stages:
            if stage.stage_id in set(acceptance.required_stage_ids) and stage.status != "passed":
                for issue in stage.issues:
                    steps.append(
                        WorkflowStep(
                            step_id=f"acceptance_{stage.stage_id}_{len(steps) + 1}",
                            order=len(steps) + 1,
                            phase="acceptance",
                            status="blocked",
                            command=issue.next_action,
                            rationale=issue.detail,
                            expected_artifacts=stage.artifact_refs,
                            source="acceptance",
                        )
                    )
    if rhythm_repair:
        for action in rhythm_repair.actions:
            steps.append(
                WorkflowStep(
                    step_id=f"rhythm_repair_{action.action_id}",
                    order=len(steps) + 1,
                    phase="rhythm",
                    status="blocked" if action.severity == "required" else "optional",
                    command=action.command,
                    rationale=action.rationale,
                    expected_artifacts=action.expected_artifacts,
                    source="rhythm_repair",
                )
            )
    return steps


def _creator_stages(steps: list[WorkflowStep], target: str) -> list[CreatorWorkflowStage]:
    definitions = [
        (
            "setup",
            "Project setup",
            ["init", "scan"],
            "Initialize the workspace and canonical source ledger.",
            [".artist-portrait/state.json", ".artist-portrait/data/sources.jsonl"],
        ),
        (
            "material_research",
            "Material research",
            ["segment", "analyze", "map"],
            "Turn scanned sources into clips, evidence, and a material map.",
            ["output/clip_report.md", "output/analysis_report.md", "output/material_map.md"],
        ),
        (
            "creative_decision",
            "Brief, proposal, and timeline",
            ["brief", "score", "propose", "proposal_import", "timeline", "sound"],
            "Lock target duration, score clips from local evidence, prepare host-Agent proposals, import the selected proposal, build a score-aware hook/build/payoff timeline, and choose the sound strategy.",
            [
                "output/edit_brief.md",
                "output/clip_score_report.md",
                "output/proposal_agent_handoff.json",
                ".artist-portrait/data/proposals.json",
                "output/timeline_draft.json",
                "output/sound_decision.md",
            ],
        ),
    ]
    if target in {"preview", "delivery"}:
        definitions.extend(
            [
                (
                    "music_rhythm",
                    "Music and rhythm",
                    ["bgm_import_or_fit", "bgm_fit", "rhythm"],
                    "Bind explicit BGM input, fit it to the timeline, and plan edit rhythm.",
                    [
                        ".artist-portrait/data/bgm_candidates.json",
                        ".artist-portrait/data/bgm_fit.json",
                        "output/rhythm_report.md",
                    ],
                ),
                (
                    "preview_review",
                    "Preview review",
                    ["preview", "rhythm_qc_preview", "cut_review", "revision", "revision_application", "revision_promotion", "acceptance_preview"],
                    "Render a low-resolution preview, evaluate preview readiness, review the cut aesthetically, plan user-directed revisions, generate a revised timeline candidate, and promote it when explicitly selected.",
                    ["output/preview_lowres.mp4", "output/rhythm_media_qc.md", "output/acceptance_report.md", "output/cut_review.md", "output/revision_plan.md", "output/revision_application.md", "output/revision_promotion.md"],
                ),
            ]
        )
    if target == "delivery":
        definitions.extend(
            [
                (
                    "delivery_review",
                    "Delivery review",
                    ["final_export", "rhythm_qc_delivery", "cut_review", "acceptance_delivery"],
                    "Render final review media, evaluate delivery readiness, and create an aesthetic second-pass review.",
                    ["output/final_export.mp4", "output/rhythm_media_qc.md", "output/acceptance_report.md", "output/cut_review.md"],
                ),
                (
                    "editor_handoff",
                    "Editor and NLE handoff",
                    ["operator", "editor_package", "nle_plan", "fcpxml_draft"],
                    "Package the accepted edit for operator review and NLE follow-up.",
                    [
                        "output/operator_runbook.md",
                        "output/editor_package.md",
                        "output/nle_interchange_plan.md",
                        "output/draft.fcpxml",
                    ],
                ),
            ]
        )
    by_id = {step.step_id: step for step in steps}
    stages: list[CreatorWorkflowStage] = []
    for order, (stage_id, title, step_ids, summary, deliverables) in enumerate(definitions, start=1):
        stage_steps = [by_id[step_id] for step_id in step_ids if step_id in by_id]
        statuses = [step.status for step in stage_steps]
        if statuses and all(status == "done" for status in statuses):
            status = "done"
        elif any(item == "blocked" for item in statuses):
            status = "blocked"
        elif any(item == "next" for item in statuses):
            status = "current"
        else:
            status = "pending"
        next_step = next((step for step in stage_steps if step.status in {"next", "blocked"}), None)
        stages.append(
            CreatorWorkflowStage(
                stage_id=stage_id,
                order=order,
                title=title,
                status=status,
                next_command=next_step.command if next_step else None,
                summary=summary,
                step_ids=step_ids,
                deliverable_refs=deliverables,
                blocking_step_ids=[step.step_id for step in stage_steps if step.status == "blocked"],
            )
        )
    return stages


def _creator_deliverables(root: Path, target: str) -> list[CreatorWorkflowDeliverable]:
    definitions = [
        (
            "material_map",
            "material_research",
            "Material map",
            ["output/material_map.md"],
            "Analysis-led source and clip review map.",
        ),
        (
            "edit_brief",
            "creative_decision",
            "Edit brief",
            ["output/edit_brief.md", ".artist-portrait/data/edit_brief.json"],
            "Target duration decision and editing intent before creative proposal generation.",
        ),
        (
            "clip_scores",
            "creative_decision",
            "Clip score map",
            ["output/clip_score_report.md", ".artist-portrait/data/clip_scores.jsonl"],
            "Local evidence score map for keep/drop and proposal selection.",
        ),
        (
            "timeline",
            "creative_decision",
            "Canonical timeline",
            ["output/timeline_draft.json"],
            "Selected proposal, edit brief, and clip scores converted into a hook/build/payoff canonical timeline draft.",
        ),
        (
            "sound_decision",
            "creative_decision",
            "Sound decision",
            ["output/sound_decision.md", ".artist-portrait/data/sound_decision.json"],
            "Original audio, BGM input modes, silence, ducking, fades, and beat fallback converted into a documented sound strategy.",
        ),
    ]
    if target in {"preview", "delivery"}:
        definitions.extend(
            [
                (
                    "rhythm_plan",
                    "music_rhythm",
                    "Rhythm plan",
                    ["output/rhythm_report.md"],
                    "BGM/edit rhythm planning report.",
                ),
                (
                    "preview_media",
                    "preview_review",
                    "Preview media",
                    ["output/preview_lowres.mp4", ".artist-portrait/data/preview_validation.json"],
                    "Low-resolution preview plus validation.",
                ),
                (
                    "cut_review",
                    "preview_review" if target == "preview" else "delivery_review",
                    "Cut review",
                    ["output/cut_review.md", ".artist-portrait/data/cut_review.json"],
                    "Aesthetic cut review and manual second-pass action plan.",
                ),
                (
                    "revision_plan",
                    "preview_review" if target == "preview" else "delivery_review",
                    "User revision plan",
                    ["output/revision_plan.md", ".artist-portrait/data/revision_plan.json"],
                    "Explicit user revision intent, manual actions, and current-vs-revised version comparison.",
                ),
                (
                    "revision_application",
                    "preview_review" if target == "preview" else "delivery_review",
                    "Revision application",
                    ["output/revision_application.md", ".artist-portrait/data/revision_application.json"],
                    "Selected revision candidate applied into a revised timeline candidate without mutating the canonical timeline.",
                ),
                (
                    "revision_promotion",
                    "preview_review" if target == "preview" else "delivery_review",
                    "Revision promotion",
                    ["output/revision_promotion.md", ".artist-portrait/data/revision_promotion.json", "output/timeline_draft.json"],
                    "Explicit revised candidate promotion into the canonical timeline before revised media is rerendered.",
                ),
            ]
        )
    if target == "delivery":
        definitions.extend(
            [
                (
                    "final_export",
                    "delivery_review",
                    "Final review export",
                    ["output/final_export.mp4", ".artist-portrait/data/final_export_validation.json"],
                    "Bounded local final MP4 export plus validation.",
                ),
                (
                    "editor_package",
                    "editor_handoff",
                    "Editor package",
                    ["output/editor_package.md", "output/cue_sheet.csv", "output/editor_handoff.json"],
                    "Editor-facing instructions, cue sheet, and handoff.",
                ),
                (
                    "nle_package",
                    "editor_handoff",
                    "NLE package",
                    ["output/nle_interchange_plan.md", "output/nle_interchange_map.csv", "output/draft.fcpxml"],
                    "NLE mapping plan and supervised FCPXML draft.",
                ),
            ]
        )
    deliverables: list[CreatorWorkflowDeliverable] = []
    for deliverable_id, stage_id, label, refs, summary in definitions:
        present = all((root / ref).exists() for ref in refs)
        deliverables.append(
            CreatorWorkflowDeliverable(
                deliverable_id=deliverable_id,
                stage_id=stage_id,
                label=label,
                status="present" if present else "missing",
                refs=refs,
                summary=summary,
            )
        )
    return deliverables


def _workflow_bgm_guidance(target: str) -> list[str]:
    if target == "core":
        return [
            "Core target does not require BGM, but unresolved music intent should remain explicit.",
        ]
    return [
        "Direct audio: import a project-local audio file with `bgm import --file <audio>`.",
        "Video audio extract: import from project-local video only with source/range/stream/hash provenance; never treat a mixed video track as clean BGM.",
        "Source embedded audio: retained original source audio remains separate from selected BGM.",
        "Multiple candidates: keep candidates distinct until the user explicitly chooses one for fitting.",
        "No file yet: preserve an unresolved music slot and continue planning without fabricating BPM or beat grids.",
    ]


def _step_done(root: Path, state: ProjectState | None, step_id: str, artifacts: list[str]) -> bool:
    if step_id == "init":
        return state is not None
    if step_id == "proposal_import":
        return all((root / ref).exists() for ref in artifacts)
    if step_id == "bgm_import_or_fit":
        return (root / WORKSPACE_DIR / DATA_DIR / "bgm_candidates.json").exists() or (
            root / WORKSPACE_DIR / DATA_DIR / "bgm_fit.json"
        ).exists()
    if step_id == "rhythm_qc_preview":
        return (root / WORKSPACE_DIR / DATA_DIR / "rhythm_media_qc.json").exists()
    if step_id == "rhythm_qc_delivery":
        return (root / WORKSPACE_DIR / DATA_DIR / "rhythm_media_qc.json").exists() and (
            root / WORKSPACE_DIR / DATA_DIR / "final_export_validation.json"
        ).exists()
    if step_id == "operator":
        return (root / WORKSPACE_DIR / DATA_DIR / "operator_runbook.json").exists()
    if step_id == "editor_package":
        return (root / WORKSPACE_DIR / DATA_DIR / "editor_package.json").exists()
    if step_id == "nle_plan":
        return (root / WORKSPACE_DIR / DATA_DIR / "nle_interchange_plan.json").exists()
    if step_id == "fcpxml_draft":
        return (root / WORKSPACE_DIR / DATA_DIR / "fcpxml_draft.json").exists() and (
            root / WORKSPACE_DIR / DATA_DIR / "fcpxml_validation.json"
        ).exists()
    if step_id.startswith("acceptance_"):
        report_path = root / WORKSPACE_DIR / DATA_DIR / "acceptance_report.json"
        if not report_path.exists():
            return False
        report = ProjectAcceptanceReport.model_validate_json(report_path.read_text(encoding="utf-8"))
        expected = step_id.removeprefix("acceptance_")
        if report.acceptance_profile == expected and report.profile_passed:
            return True
        if expected == "preview" and report.acceptance_profile == "delivery" and report.profile_passed:
            return True
        return False
    if all((root / ref).exists() for ref in artifacts):
        return True
    if state and step_id in state.steps:
        return state.steps[step_id].status in {StepStatus.completed, StepStatus.completed_with_warnings}
    return False


def _review_execution_record(
    *,
    root: Path,
    plan: WorkflowPlan,
    record: WorkflowExecutionRecord,
    quarantine_ref: str,
    candidate_sha256: str,
    candidate_bytes: int,
) -> WorkflowExecutionReview:
    planned = {step.step_id: step for step in plan.steps}
    submitted = {step.step_id: step for step in record.steps}
    reviews: list[WorkflowExecutionStepReview] = []

    binding_errors: list[str] = []
    if record.project_id != plan.project_id:
        binding_errors.append("project_id does not match current workflow plan")
    if record.workflow_plan_id != plan.workflow_plan_id:
        binding_errors.append("workflow_plan_id does not match current workflow plan")
    if record.target != plan.target:
        binding_errors.append("target does not match current workflow plan")
    if any(
        (
            record.commands_executed_by_cli,
            record.media_rendered_by_cli,
            record.edit_points_moved_by_cli,
            record.automatic_music_selection_by_cli,
            record.model_call_performed_by_cli,
            record.network_performed_by_cli,
        )
    ):
        binding_errors.append("record claims a forbidden CLI-side execution capability")

    for submitted_step in record.steps:
        plan_step = planned.get(submitted_step.step_id)
        refs = submitted_step.output_refs + submitted_step.evidence_refs
        missing_refs = [ref for ref in refs if not (root / ref).exists()]
        if plan_step is None:
            reviews.append(
                WorkflowExecutionStepReview(
                    step_id=submitted_step.step_id,
                    submitted_status=submitted_step.status,
                    review_status="rejected",
                    evidence_refs=refs,
                    missing_refs=missing_refs,
                    detail="submitted step is not present in the current workflow plan",
                )
            )
            continue
        command_matched = submitted_step.command == plan_step.command
        if binding_errors:
            review_status = "rejected"
            detail = "; ".join(binding_errors)
        elif submitted_step.status == "skipped":
            review_status = "skipped"
            detail = "external record explicitly skipped this step"
        elif submitted_step.status == "failed":
            review_status = "rejected"
            detail = "external record reports this step failed"
        elif not command_matched:
            review_status = "rejected"
            detail = "submitted command does not match workflow plan command"
        elif not refs:
            review_status = "rejected"
            detail = "succeeded step did not provide output_refs or evidence_refs"
        elif missing_refs:
            review_status = "rejected"
            detail = "one or more submitted evidence refs are missing"
        else:
            review_status = "accepted"
            detail = "submitted success is bound to matching command and existing evidence refs"
        reviews.append(
            WorkflowExecutionStepReview(
                step_id=submitted_step.step_id,
                planned_status=plan_step.status,
                submitted_status=submitted_step.status,
                review_status=review_status,
                command_matched=command_matched,
                evidence_refs=refs,
                missing_refs=missing_refs,
                detail=detail,
            )
        )

    for step_id, plan_step in planned.items():
        if step_id not in submitted:
            review_status = "skipped" if plan_step.status == "optional" else "missing"
            detail = (
                "no external execution evidence was submitted for this optional workflow step"
                if plan_step.status == "optional"
                else "no external execution evidence was submitted for this workflow step"
            )
            reviews.append(
                WorkflowExecutionStepReview(
                    step_id=step_id,
                    planned_status=plan_step.status,
                    review_status=review_status,
                    command_matched=False,
                    detail=detail,
                )
            )

    accepted = sum(step.review_status == "accepted" for step in reviews)
    rejected = sum(step.review_status == "rejected" for step in reviews)
    missing = sum(step.review_status == "missing" for step in reviews)
    skipped = sum(step.review_status == "skipped" for step in reviews)
    required_skipped = any(
        step.review_status == "skipped" and step.planned_status != "optional"
        for step in reviews
    )
    status = "failed" if rejected else "warning" if missing or required_skipped else "passed"
    key = f"{plan.workflow_plan_id}:{candidate_sha256}:{accepted}:{rejected}:{missing}:{skipped}"
    return WorkflowExecutionReview(
        workflow_execution_review_id="workflow_execution_review_"
        + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=plan.project_id,
        workflow_plan_id=plan.workflow_plan_id,
        target=plan.target,
        status=status,
        quarantine_ref=quarantine_ref,
        candidate_sha256=candidate_sha256,
        candidate_bytes=candidate_bytes,
        accepted_step_count=accepted,
        rejected_step_count=rejected,
        missing_step_count=missing,
        skipped_step_count=skipped,
        step_reviews=reviews,
    )


def _workflow_handoff(plan: WorkflowPlan) -> dict:
    return {
        "schema_version": plan.schema_version,
        "handoff_id": f"workflow_handoff_{plan.workflow_plan_id}",
        "project_id": plan.project_id,
        "workflow_plan_id": plan.workflow_plan_id,
        "target": plan.target,
        "task": "Review the workflow plan and guide the user through explicit commands only.",
        "next_command": plan.next_command,
        "current_stage_id": plan.current_stage_id,
        "current_stage_title": plan.current_stage_title,
        "creator_stages": [stage.model_dump(mode="json") for stage in plan.creator_stages],
        "deliverables": [item.model_dump(mode="json") for item in plan.deliverables],
        "bgm_input_guidance": plan.bgm_input_guidance,
        "steps": [step.model_dump(mode="json") for step in plan.steps],
        "forbidden": [
            "do not execute commands without explicit user action",
            "do not render media from the workflow command",
            "do not move edit points",
            "do not select music",
            "do not call models from the CLI",
            "do not access the network",
        ],
    }


def _workflow_execution_handoff(review: WorkflowExecutionReview) -> dict:
    return {
        "schema_version": review.schema_version,
        "handoff_id": f"workflow_execution_handoff_{review.workflow_execution_review_id}",
        "project_id": review.project_id,
        "workflow_plan_id": review.workflow_plan_id,
        "workflow_execution_review_id": review.workflow_execution_review_id,
        "target": review.target,
        "task": "Review external workflow execution evidence without treating it as automatic acceptance success.",
        "status": review.status,
        "quarantine_ref": review.quarantine_ref,
        "step_reviews": [step.model_dump(mode="json") for step in review.step_reviews],
        "forbidden": [
            "do not execute commands from this review",
            "do not render media from this review",
            "do not move edit points",
            "do not select music",
            "do not call models from the CLI",
            "do not access the network",
            "do not treat execution evidence as acceptance success",
        ],
    }


def _read_optional(path: Path, model):
    if not path.exists():
        return None
    return model.model_validate_json(path.read_text(encoding="utf-8"))
