from __future__ import annotations

import json
from pathlib import Path

from artist_portrait_editor.bgm import bgm_analysis_summary
from artist_portrait_editor.bgm_recommendation import (
    bgm_recommendation_doctor_issues,
    bgm_recommendation_selection_summary,
    bgm_recommendation_summary,
)
from artist_portrait_editor.capabilities import detect_capabilities
from artist_portrait_editor.cleanup import project_storage_summary
from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.diagnostics import (
    artifact_issue,
    rebuild_command_for_step,
    render_risk_report,
    risk_issue,
    workspace_issue,
)
from artist_portrait_editor.final_export import (
    final_export_doctor_issues,
    final_export_manifest_summary,
    final_export_status_lines,
    final_export_validation_summary,
)
from artist_portrait_editor.media.scanner import read_sources_jsonl
from artist_portrait_editor.models.clip import ClipRecord
from artist_portrait_editor.models.config import FeatureSwitch
from artist_portrait_editor.models.source import SourceRecord
from artist_portrait_editor.models.state import (
    OverallStatus,
    ProjectState,
    StepLedgerEntry,
    StepStatus,
)
from artist_portrait_editor.preview import (
    preview_manifest_summary,
    preview_validation_summary,
    review_preview,
)
from artist_portrait_editor.proposal_artifacts import (
    proposal_artifact_paths,
    proposal_chain_issues,
    proposal_invalid_artifacts,
)
from artist_portrait_editor.workspace_records import read_clips_jsonl
from artist_portrait_editor.workspace_state import load_state, project_root, state_as_dict
from artist_portrait_editor.workspace_summaries import (
    analysis_summary,
    bgm_candidates_summary,
    bgm_fit_summary,
    count_by_value,
    keyframe_summary,
    proposal_status_summaries,
    timeline_summary,
    timeline_validation_summary,
    transcript_summary,
)


PROPOSAL_INVALID_ARTIFACTS = proposal_invalid_artifacts()

def project_status_payload(project_path: Path) -> dict:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    artifacts = artifact_statuses(root)
    payload: dict
    if state is None:
        payload = {
            "project_id": config.project.id,
            "overall_status": OverallStatus.new.value,
            "state": None,
        }
    else:
        payload = state_as_dict(state)
        payload["artifact_issues"] = [
            *ledger_output_ref_issues(root, state),
            *proposal_chain_issues(root),
        ]
    payload["artifacts"] = artifacts
    payload["summaries"] = status_summaries(root)
    payload["local_storage"] = project_storage_summary(
        root,
        media_dir=config.paths.media_dir,
        annotations_dir=config.paths.annotations_dir,
        output_dir=config.paths.output_dir,
    )
    payload["latest_run"] = latest_run_summary(root, state.latest_run_id if state else None)
    if state is None:
        payload["artifact_issues"] = []
    return payload


def render_status_panel(payload: dict) -> str:
    lines = [
        f"project: {payload.get('project_id')}",
        f"overall_status: {payload.get('overall_status')}",
    ]
    latest_run = payload.get("latest_run") or {}
    if latest_run.get("run_id"):
        command = latest_run.get("command") or "unknown"
        lines.append(f"latest_run: {latest_run['run_id']} ({command})")
    local_storage = payload.get("local_storage") or {}
    if local_storage:
        lines.append(
            "local_storage: "
            f"{local_storage.get('bytes', 0)} bytes, "
            f"{local_storage.get('files', 0)} files"
        )
        cache = (local_storage.get("categories") or {}).get("rebuildable_cache") or {}
        if cache.get("exists"):
            lines.append(
                "rebuildable_cache: "
                f"{cache.get('bytes', 0)} bytes, {cache.get('files', 0)} files"
            )
    summaries = payload.get("summaries") or {}
    sources = summaries.get("sources") or {}
    if sources.get("exists"):
        lines.append(f"sources: {sources.get('count', 0)}")
    else:
        lines.append("sources: missing")
    clips = summaries.get("clips") or {}
    if clips.get("exists") and clips.get("valid", True):
        lines.append(f"clips: {clips.get('count', 0)}")
        method_counts = clips.get("method_counts") or {}
        if method_counts:
            methods = ", ".join(
                f"{method}={count}" for method, count in sorted(method_counts.items())
            )
            lines.append(f"clip_methods: {methods}")
    elif clips.get("exists"):
        lines.append("clips: invalid")
    else:
        lines.append("clips: missing")
    transcripts = summaries.get("transcripts") or {}
    if transcripts.get("exists") and transcripts.get("valid", True):
        lines.append(f"transcripts: {transcripts.get('count', 0)}")
    elif transcripts.get("exists"):
        lines.append("transcripts: invalid")
    else:
        lines.append("transcripts: missing")
    keyframes = summaries.get("keyframes") or {}
    if keyframes.get("exists") and keyframes.get("valid", True):
        lines.append(f"keyframes: {keyframes.get('count', 0)}")
        if keyframes.get("missing_cache_count"):
            lines.append(f"keyframe_cache_missing: {keyframes.get('missing_cache_count')}")
    elif keyframes.get("exists"):
        lines.append("keyframes: invalid")
    else:
        lines.append("keyframes: missing")
    analysis = summaries.get("analysis") or {}
    if analysis.get("exists") and analysis.get("valid", True):
        lines.append(f"analysis: {analysis.get('count', 0)}")
    elif analysis.get("exists"):
        lines.append("analysis: invalid")
    else:
        lines.append("analysis: missing")
    risk = summaries.get("risk_report") or {}
    if risk.get("exists"):
        lines.append(f"risk_report: present ({risk.get('bytes', 0)} bytes)")
    proposal_validation = summaries.get("proposal_validation") or {}
    if proposal_validation.get("exists") and proposal_validation.get("valid", True):
        lines.append(
            "proposal_validation: "
            f"{proposal_validation.get('error_count', 0)} errors, "
            f"{proposal_validation.get('warning_count', 0)} warnings"
        )
    elif proposal_validation.get("exists"):
        lines.append("proposal_validation: invalid")
    scan_report = summaries.get("scan_report") or {}
    if scan_report.get("exists"):
        lines.append(f"scan_report: present ({scan_report.get('bytes', 0)} bytes)")
    clip_report = summaries.get("clip_report") or {}
    if clip_report.get("exists"):
        lines.append(f"clip_report: present ({clip_report.get('bytes', 0)} bytes)")
    analysis_report = summaries.get("analysis_report") or {}
    if analysis_report.get("exists"):
        lines.append(
            f"analysis_report: present ({analysis_report.get('bytes', 0)} bytes)"
        )
    material_map = summaries.get("material_map") or {}
    if material_map.get("exists"):
        lines.append(f"material_map: present ({material_map.get('bytes', 0)} bytes)")
    agent_handoff = summaries.get("proposal_agent_handoff") or {}
    if agent_handoff.get("exists"):
        lines.append(
            f"proposal_agent_handoff: present ({agent_handoff.get('bytes', 0)} bytes)"
        )
    agent_quarantine = summaries.get("proposal_agent_quarantine") or {}
    if agent_quarantine.get("exists"):
        lines.append(
            "proposal_agent_quarantine: "
            f"{agent_quarantine.get('file_count', 0)} file(s)"
        )
    proposal_context = summaries.get("proposal_context") or {}
    if proposal_context.get("exists") and proposal_context.get("valid", True):
        lines.append(f"proposal_context: {proposal_context.get('analysis_count', 0)} analyses")
    elif proposal_context.get("exists"):
        lines.append("proposal_context: invalid")
    else:
        lines.append("proposal_context: missing")
    proposals = summaries.get("proposals") or {}
    if proposals.get("exists") and proposals.get("valid", True):
        lines.append(f"proposals: {proposals.get('count', 0)}")
    elif proposals.get("exists"):
        lines.append("proposals: invalid")
    else:
        lines.append("proposals: missing")
    timeline = summaries.get("timeline") or {}
    if timeline.get("exists") and timeline.get("valid", True):
        lines.append(
            f"timeline: {timeline.get('proposal_id')} "
            f"({timeline.get('segment_count', 0)} segments)"
        )
    elif timeline.get("exists"):
        lines.append("timeline: invalid")
    else:
        lines.append("timeline: missing")
    preview = summaries.get("preview") or {}
    if preview.get("exists") and preview.get("valid", True):
        lines.append(
            f"preview: {preview.get('output_ref')} "
            f"({preview.get('width')}x{preview.get('height')}, "
            f"bgm={str(preview.get('bgm_included')).lower()})"
        )
        preview_validation = summaries.get("preview_validation") or {}
        if preview_validation.get("exists") and preview_validation.get("valid", True):
            lines.append(
                "preview_qc: "
                f"{preview_validation.get('quality_status')} "
                f"(delta={preview_validation.get('duration_delta_seconds')}s)"
            )
    elif preview.get("exists"):
        lines.append("preview: invalid")
    else:
        lines.append("preview: missing")
    lines.extend(final_export_status_lines(summaries))
    artifact_issues = payload.get("artifact_issues") or []
    if artifact_issues:
        lines.append(f"artifact_issues: {len(artifact_issues)}")
    steps = payload.get("steps") or {}
    for step in (
        "scan",
        "segment",
        "transcribe",
        "keyframes",
        "analyze",
        "map",
        "brief",
        "score",
        "propose",
        "timeline",
        "preview",
        "final_export",
        "review_timeline",
        "review_preview",
        "review_final_export",
        "review_project",
    ):
        if step in steps:
            lines.append(f"{step}: {steps[step].get('status')}")
    return "\n".join(lines) + "\n"


def doctor_project_payload(project_path: Path) -> dict:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    issues: list[dict[str, str]] = []

    if state is None:
        issues.append(
            workspace_issue(
                code="workspace_not_initialized",
                severity="warning",
                detail="project workspace state is missing",
                next_action=f"artist-portrait init --project {project_path}",
            )
        )
        return {
            "project_id": config.project.id,
            "overall_status": OverallStatus.new.value,
            "initialized": False,
            "issues": issues,
            "issue_count": len(issues),
            "recommended_commands": recommended_commands(issues),
            "artifacts": artifact_statuses(root),
            "summaries": status_summaries(root),
        }

    issues.extend(ledger_output_ref_issues(root, state))
    issues.extend(proposal_chain_issues(root))
    issues.extend(invalidated_step_issues(project_path, state))
    current_capabilities = detect_capabilities()
    if (
        config.features.scene_detection == FeatureSwitch.required
        and not current_capabilities.pyscenedetect
    ):
        issues.append(
            workspace_issue(
                code="scene_detection_required_missing",
                severity="error",
                detail="project requires PySceneDetect but it is not available",
                next_action="install PySceneDetect or set features.scene_detection to auto/off",
            )
        )
    if (
        config.features.transcription == FeatureSwitch.required
        and not current_capabilities.faster_whisper
    ):
        issues.append(
            workspace_issue(
                code="transcription_required_missing",
                severity="error",
                detail="project requires faster-whisper but it is not available",
                next_action="install faster-whisper or set features.transcription to auto/off",
            )
        )
    sources_path = root / WORKSPACE_DIR / DATA_DIR / "sources.jsonl"
    sources = source_summary(sources_path)
    if sources.get("valid") is False:
        issues.append(
            workspace_issue(
                code="source_ledger_invalid",
                severity="error",
                detail=str(sources.get("error") or "source ledger is invalid"),
                next_action=(
                    f"fix {sources_path.relative_to(root).as_posix()} or rerun "
                    f"artist-portrait scan --project {project_path}"
                ),
            )
        )
    if (
        sources.get("valid") is True
        and clips_summary(root).get("valid") is False
    ):
        clips_path = root / WORKSPACE_DIR / DATA_DIR / "clips.jsonl"
        issues.append(
            workspace_issue(
                code="clips_invalid",
                severity="error",
                detail=str(clips_summary(root).get("error") or "clips ledger is invalid"),
                next_action=(
                    f"fix {clips_path.relative_to(root).as_posix()} or rerun "
                    f"artist-portrait segment --project {project_path}"
                ),
            )
        )
    timeline = timeline_summary(root / config.paths.output_dir / "timeline_draft.json")
    if timeline.get("valid") is False:
        issues.append(
            workspace_issue(
                code="timeline_invalid",
                severity="error",
                detail=str(timeline.get("error") or "timeline draft is invalid"),
                next_action=(
                    "fix output/timeline_draft.json or rerun artist-portrait timeline "
                    f"--project {project_path} --proposal <selected-proposal-id>"
                ),
            )
        )
    bgm_candidates = bgm_candidates_summary(
        root / WORKSPACE_DIR / DATA_DIR / "bgm_candidates.json"
    )
    if bgm_candidates.get("valid") is False:
        issues.append(
            workspace_issue(
                code="bgm_candidates_invalid",
                severity="error",
                detail=str(bgm_candidates.get("error")),
                next_action="fix or rebuild .artist-portrait/data/bgm_candidates.json",
            )
        )
    bgm_analysis = bgm_analysis_summary(root / ".artist-portrait" / "data" / "bgm_analysis.json")
    if bgm_analysis.get("valid") is False:
        issues.append(
            workspace_issue(
                code="bgm_analysis_invalid",
                severity="error",
                detail=str(bgm_analysis.get("error")),
                next_action=f"rerun artist-portrait bgm analyze --project {project_path}",
            )
        )
    issues.extend(bgm_recommendation_doctor_issues(root, str(project_path)))
    bgm_fit = bgm_fit_summary(root / WORKSPACE_DIR / DATA_DIR / "bgm_fit.json")
    if bgm_fit.get("valid") is False:
        issues.append(
            workspace_issue(
                code="bgm_fit_invalid",
                severity="error",
                detail=str(bgm_fit.get("error")),
                next_action=(
                    f"rerun artist-portrait bgm fit --project {project_path} "
                    "--candidate <candidate-id>"
                ),
            )
        )
    preview_manifest = preview_manifest_summary(
        root / WORKSPACE_DIR / DATA_DIR / "preview_manifest.json"
    )
    if preview_manifest.get("valid") is False:
        issues.append(
            workspace_issue(
                code="preview_manifest_invalid",
                severity="error",
                detail=str(preview_manifest.get("error")),
                next_action=f"rerun artist-portrait preview --project {project_path}",
            )
        )
    preview_validation = preview_validation_summary(
        root / WORKSPACE_DIR / DATA_DIR / "preview_validation.json"
    )
    if preview_validation.get("valid") is False:
        issues.append(
            workspace_issue(
                code="preview_validation_invalid",
                severity="error",
                detail=str(preview_validation.get("error")),
                next_action=f"rerun artist-portrait preview --project {project_path}",
            )
        )
    if preview_manifest.get("valid") is True:
        preview_report = review_preview(root)
        for issue in preview_report.issues:
            issues.append(
                workspace_issue(
                    code=issue.code,
                    severity=issue.severity,
                    detail=issue.detail,
                    next_action=f"artist-portrait preview --project {project_path}",
                )
            )
    issues.extend(final_export_doctor_issues(root, str(project_path)))
    transcripts = transcript_summary(root / WORKSPACE_DIR / DATA_DIR / "transcripts.jsonl")
    if (
        sources.get("valid") is True
        and transcripts.get("valid") is False
    ):
        transcripts_path = root / WORKSPACE_DIR / DATA_DIR / "transcripts.jsonl"
        issues.append(
            workspace_issue(
                code="transcripts_invalid",
                severity="error",
                detail=str(transcripts.get("error") or "transcripts ledger is invalid"),
                next_action=(
                    f"fix {transcripts_path.relative_to(root).as_posix()} or rerun "
                    f"artist-portrait transcribe --project {project_path}"
                ),
            )
        )
    elif (
        sources.get("valid") is True
        and config.features.transcription != FeatureSwitch.off
        and state.steps.get("transcribe", StepLedgerEntry()).status == StepStatus.pending
    ):
        issues.append(
            workspace_issue(
                code="transcribe_pending",
                severity="info",
                detail="source ledger exists but transcription has not been run",
                next_action=f"artist-portrait transcribe --project {project_path}",
            )
        )
    keyframes = keyframe_summary(
        root / WORKSPACE_DIR / DATA_DIR / "keyframes.jsonl",
        root=root,
    )
    if (
        sources.get("valid") is True
        and keyframes.get("valid") is False
    ):
        keyframes_path = root / WORKSPACE_DIR / DATA_DIR / "keyframes.jsonl"
        issues.append(
            workspace_issue(
                code="keyframes_invalid",
                severity="error",
                detail=str(keyframes.get("error") or "keyframes ledger is invalid"),
                next_action=(
                    f"fix {keyframes_path.relative_to(root).as_posix()} or rerun "
                    f"artist-portrait keyframes --project {project_path}"
                ),
            )
        )
    elif (
        sources.get("valid") is True
        and keyframes.get("missing_cache_count", 0) > 0
    ):
        issues.append(
            workspace_issue(
                code="keyframe_cache_missing",
                severity="warning",
                detail=(
                    f"{keyframes.get('missing_cache_count')} keyframe cache image(s) "
                    "are missing and can be rebuilt"
                ),
                next_action=f"artist-portrait keyframes --project {project_path}",
            )
        )
    analysis = analysis_summary(root / WORKSPACE_DIR / DATA_DIR / "analysis.jsonl")
    if (
        sources.get("valid") is True
        and analysis.get("valid") is False
    ):
        analysis_path = root / WORKSPACE_DIR / DATA_DIR / "analysis.jsonl"
        issues.append(
            workspace_issue(
                code="analysis_invalid",
                severity="error",
                detail=str(analysis.get("error") or "analysis ledger is invalid"),
                next_action=(
                    f"fix {analysis_path.relative_to(root).as_posix()} or rerun "
                    f"artist-portrait analyze --project {project_path}"
                ),
            )
        )
    if (
        sources.get("valid") is True
        and state.steps.get("segment", StepLedgerEntry()).status == StepStatus.pending
    ):
        issues.append(
            workspace_issue(
                code="segment_pending",
                severity="info",
                detail="source ledger exists but clips have not been generated",
                next_action=f"artist-portrait segment --project {project_path}",
            )
        )
    if (
        sources.get("valid") is True
        and clips_summary(root).get("valid") is True
        and state.steps.get("analyze", StepLedgerEntry()).status == StepStatus.pending
    ):
        issues.append(
            workspace_issue(
                code="analysis_pending",
                severity="info",
                detail="clip ledger exists but analysis has not been generated",
                next_action=f"artist-portrait analyze --project {project_path}",
            )
        )
    elif (
        sources.get("valid") is True
        and analysis.get("valid") is True
        and state.steps.get("map", StepLedgerEntry()).status == StepStatus.pending
    ):
        issues.append(
            workspace_issue(
                code="map_pending",
                severity="info",
                detail="analysis ledger exists but material map has not been generated",
                next_action=f"artist-portrait map --project {project_path}",
            )
        )
    summaries = status_summaries(root)
    proposals = summaries["proposals"]
    if sources.get("valid") is True:
        proposal_paths = proposal_artifact_paths(root)
        for name, (code, label) in PROPOSAL_INVALID_ARTIFACTS.items():
            summary = summaries[name]
            if summary.get("valid") is not False:
                continue
            path = proposal_paths[name]
            issues.append(
                workspace_issue(
                    code=code,
                    severity="error",
                    detail=str(summary.get("error") or f"{label} is invalid"),
                    next_action=(
                        f"fix {path.relative_to(root).as_posix()} or rerun "
                        f"artist-portrait propose --project {project_path}"
                    ),
                )
            )
    if (
        sources.get("valid") is True
        and output_summary(root / "output" / "material_map.md").get("exists")
        and state.steps.get("propose", StepLedgerEntry()).status == StepStatus.pending
    ):
        issues.append(
            workspace_issue(
                code="proposal_agent_handoff_pending",
                severity="info",
                detail="material map exists but the host-Agent handoff is not prepared",
                next_action=f"artist-portrait propose --project {project_path}",
            )
        )
    if (
        state.steps.get("propose", StepLedgerEntry()).status == StepStatus.blocked
        and output_summary(root / "output" / "proposal_agent_handoff.json").get("exists")
        and not (root / WORKSPACE_DIR / DATA_DIR / "proposals.json").exists()
    ):
        issues.append(
            workspace_issue(
                code="proposal_agent_candidate_pending",
                severity="info",
                detail=(
                    "host-Agent handoff is ready but no validated ProposalSet has "
                    "been imported"
                ),
                next_action=(
                    f"artist-portrait propose --project {project_path} "
                    "--agent-output <candidate.json>"
                ),
            )
        )
    if (
        sources.get("valid") is True
        and clips_summary(root).get("valid") is True
        and state.steps.get("keyframes", StepLedgerEntry()).status == StepStatus.pending
    ):
        issues.append(
            workspace_issue(
                code="keyframes_pending",
                severity="info",
                detail="clip ledger exists but keyframes have not been generated",
                next_action=f"artist-portrait keyframes --project {project_path}",
            )
        )
    if (
        sources.get("valid") is True
        and state.steps.get("review_project", StepLedgerEntry()).status == StepStatus.pending
    ):
        issues.append(
            workspace_issue(
                code="review_project_pending",
                severity="info",
                detail="source ledger exists but project review has not been generated",
                next_action=f"artist-portrait review --project {project_path} --scope project",
            )
        )

    return {
        "project_id": state.project_id,
        "overall_status": state.overall_status.value,
        "initialized": True,
        "issues": issues,
        "issue_count": len(issues),
        "recommended_commands": recommended_commands(issues),
        "artifacts": artifact_statuses(root),
        "capabilities_current": current_capabilities.model_dump(mode="json"),
        "summaries": {
            **status_summaries(root),
            "state": {"exists": True, "steps": len(state.steps)},
        },
        "latest_run": latest_run_summary(root, state.latest_run_id),
    }


def render_doctor_panel(payload: dict) -> str:
    lines = [
        f"project: {payload.get('project_id')}",
        f"overall_status: {payload.get('overall_status')}",
        f"initialized: {str(payload.get('initialized')).lower()}",
        f"issues: {payload.get('issue_count', 0)}",
    ]
    issues = payload.get("issues") or []
    for issue in issues:
        lines.append(
            f"- {issue.get('severity')}: {issue.get('code')} - {issue.get('detail')}"
        )
        if issue.get("next_action"):
            lines.append(f"  next: {issue['next_action']}")
    if not issues:
        lines.append("next: none")
    return "\n".join(lines) + "\n"


def recommended_commands(issues: list[dict[str, str]]) -> list[str]:
    commands = []
    for issue in issues:
        command = issue.get("next_action")
        if command and command.startswith("artist-portrait ") and command not in commands:
            commands.append(command)
    return commands


def invalidated_step_issues(
    project_path: Path,
    state: ProjectState,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for step_name, entry in sorted(state.steps.items()):
        if entry.status != StepStatus.invalidated:
            continue
        issues.append(
            workspace_issue(
                code=f"{step_name}_invalidated",
                severity="warning",
                detail=f"step `{step_name}` was invalidated by newer source data",
                next_action=rebuild_command_for_step(step_name).replace(
                    "<project.yaml>",
                    str(project_path),
                ),
            )
        )
    return issues


def artifact_statuses(root: Path) -> dict[str, dict]:
    proposal_paths = proposal_artifact_paths(root)
    artifact_paths = {
        "state": root / WORKSPACE_DIR / "state.json",
        "sources": root / WORKSPACE_DIR / DATA_DIR / "sources.jsonl",
        "clips": root / WORKSPACE_DIR / DATA_DIR / "clips.jsonl",
        "transcripts": root / WORKSPACE_DIR / DATA_DIR / "transcripts.jsonl",
        "keyframes": root / WORKSPACE_DIR / DATA_DIR / "keyframes.jsonl",
        "analysis": root / WORKSPACE_DIR / DATA_DIR / "analysis.jsonl",
        "relations": root / WORKSPACE_DIR / DATA_DIR / "relations.jsonl",
        **{
            ("proposals_json" if name == "proposals" else name): path
            for name, path in proposal_paths.items()
        },
        "run_report": root / "output" / "run_report.md",
        "scan_report": root / "output" / "scan_report.md",
        "clip_report": root / "output" / "clip_report.md",
        "analysis_report": root / "output" / "analysis_report.md",
        "material_map": root / "output" / "material_map.md",
        "edit_brief": root / WORKSPACE_DIR / DATA_DIR / "edit_brief.json",
        "edit_brief_report": root / "output" / "edit_brief.md",
        "clip_scores": root / WORKSPACE_DIR / DATA_DIR / "clip_scores.jsonl",
        "clip_score_report": root / "output" / "clip_score_report.md",
        "proposals_md": root / "output" / "proposals.md",
        "proposal_review": root / "output" / "proposal_review.md",
        "proposal_agent_handoff": root / "output" / "proposal_agent_handoff.json",
        "timeline_draft": root / "output" / "timeline_draft.json",
        "bgm_candidates": root / WORKSPACE_DIR / DATA_DIR / "bgm_candidates.json",
        "bgm_analysis": root / ".artist-portrait/data/bgm_analysis.json",
        "bgm_analysis_report": root / "output/bgm_analysis_report.md",
        "bgm_recommendations": root / ".artist-portrait/data/bgm_recommendations.json",
        "bgm_fit": root / WORKSPACE_DIR / DATA_DIR / "bgm_fit.json",
        "preview_manifest": root / WORKSPACE_DIR / DATA_DIR / "preview_manifest.json",
        "preview_validation": root / WORKSPACE_DIR / DATA_DIR / "preview_validation.json",
        "preview_lowres": root / "output" / "preview_lowres.mp4",
        "final_export_manifest": root / WORKSPACE_DIR / DATA_DIR / "final_export_manifest.json",
        "final_export_validation": root / WORKSPACE_DIR / DATA_DIR / "final_export_validation.json",
        "final_export": root / "output" / "final_export.mp4",
        "risk_report": root / "output" / "risk_report.md",
    }
    return {
        name: artifact_status(root, path)
        for name, path in artifact_paths.items()
    }


def artifact_status(root: Path, path: Path) -> dict:
    exists = path.exists()
    payload = {
        "path": path.relative_to(root).as_posix(),
        "exists": exists,
    }
    if exists and path.is_file():
        payload["bytes"] = path.stat().st_size
    return payload


def ledger_output_ref_issues(
    root: Path,
    state: ProjectState,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    completed_statuses = {
        StepStatus.completed,
        StepStatus.completed_with_warnings,
        StepStatus.blocked,
    }
    for step_name, entry in sorted(state.steps.items()):
        if entry.status not in completed_statuses:
            continue
        seen_refs: set[str] = set()
        for output_ref in entry.output_refs:
            if not output_ref:
                continue
            if output_ref in seen_refs:
                issues.append(
                    artifact_issue(
                        step=step_name,
                        ref=output_ref,
                        code="duplicate_output_ref",
                        severity="warning",
                        detail=(
                            f"step `{step_name}` lists output `{output_ref}` more than once"
                        ),
                    )
                )
                continue
            seen_refs.add(output_ref)
            output_path = root / output_ref
            if output_path.exists():
                continue
            issues.append(
                artifact_issue(
                    step=step_name,
                    ref=output_ref,
                    code="missing_output_ref",
                    severity="warning",
                    detail=(
                        f"step `{step_name}` is marked `{entry.status.value}` but "
                        f"referenced output `{output_ref}` is missing"
                    ),
                )
            )
    return issues


def status_summaries(root: Path) -> dict:
    sources_path = root / WORKSPACE_DIR / DATA_DIR / "sources.jsonl"
    clips_path = root / WORKSPACE_DIR / DATA_DIR / "clips.jsonl"
    transcripts_path = root / WORKSPACE_DIR / DATA_DIR / "transcripts.jsonl"
    keyframes_path = root / WORKSPACE_DIR / DATA_DIR / "keyframes.jsonl"
    analysis_path = root / WORKSPACE_DIR / DATA_DIR / "analysis.jsonl"
    clip_report_path = root / "output" / "clip_report.md"
    material_map_path = root / "output" / "material_map.md"
    risk_report_path = root / "output" / "risk_report.md"
    proposal_agent_handoff_path = root / "output" / "proposal_agent_handoff.json"
    proposal_quarantine_dir = root / WORKSPACE_DIR / "quarantine" / "proposals"
    proposal_paths = proposal_artifact_paths(root)
    timeline_path = root / "output" / "timeline_draft.json"
    timeline_validation_path = root / WORKSPACE_DIR / DATA_DIR / "timeline_validation.json"
    bgm_candidates_path = root / WORKSPACE_DIR / DATA_DIR / "bgm_candidates.json"
    bgm_fit_path = root / WORKSPACE_DIR / DATA_DIR / "bgm_fit.json"
    preview_manifest_path = root / WORKSPACE_DIR / DATA_DIR / "preview_manifest.json"
    preview_validation_path = root / WORKSPACE_DIR / DATA_DIR / "preview_validation.json"
    final_export_manifest_path = root / WORKSPACE_DIR / DATA_DIR / "final_export_manifest.json"
    final_export_validation_path = root / WORKSPACE_DIR / DATA_DIR / "final_export_validation.json"
    return {
        "sources": source_summary(sources_path),
        "clips": clip_summary(clips_path),
        "transcripts": transcript_summary(transcripts_path),
        "keyframes": keyframe_summary(keyframes_path, root=root),
        "analysis": analysis_summary(analysis_path),
        "scan_report": output_summary(root / "output" / "scan_report.md"),
        "clip_report": output_summary(clip_report_path),
        "analysis_report": output_summary(root / "output" / "analysis_report.md"),
        "material_map": output_summary(material_map_path),
        "proposal_agent_handoff": output_summary(proposal_agent_handoff_path),
        "proposal_agent_quarantine": directory_summary(proposal_quarantine_dir),
        **proposal_status_summaries(proposal_paths),
        "timeline": timeline_summary(timeline_path),
        "timeline_validation": timeline_validation_summary(timeline_validation_path),
        "timeline_review": output_summary(root / "output" / "timeline_review.md"),
        "bgm_candidates": bgm_candidates_summary(bgm_candidates_path),
        "bgm_analysis": bgm_analysis_summary(root / ".artist-portrait/data/bgm_analysis.json"),
        "bgm_analysis_report": output_summary(root / "output" / "bgm_analysis_report.md"),
        "bgm_recommendations": bgm_recommendation_summary(root / ".artist-portrait/data/bgm_recommendations.json"),
        "bgm_recommendation_selection": bgm_recommendation_selection_summary(root / ".artist-portrait/data/bgm_recommendation_selection.json"),
        "bgm_fit": bgm_fit_summary(bgm_fit_path),
        "preview": preview_manifest_summary(preview_manifest_path),
        "preview_validation": preview_validation_summary(preview_validation_path),
        "preview_review": output_summary(root / "output" / "preview_review.md"),
        "final_export": final_export_manifest_summary(final_export_manifest_path),
        "final_export_validation": final_export_validation_summary(final_export_validation_path),
        "final_export_review": output_summary(root / "output" / "final_export_review.md"),
        "risk_report": output_summary(risk_report_path),
    }


def directory_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    files = sorted(item for item in path.iterdir() if item.is_file())
    return {
        "exists": True,
        "valid": True,
        "file_count": len(files),
        "bytes": sum(item.stat().st_size for item in files),
        "latest": files[-1].name if files else None,
    }


def source_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        records = read_sources_jsonl(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    media_counts = count_by_value(record.media_kind.value for record in records)
    rights_counts = count_by_value(str(record.rights_status.value) for record in records)
    return {
        "exists": True,
        "valid": True,
        "count": len(records),
        "media_kind_counts": media_counts,
        "rights_status_counts": rights_counts,
        "total_duration_seconds": round(
            sum(record.media_probe.duration for record in records),
            3,
        ),
    }


def output_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    return {
        "exists": True,
        "bytes": path.stat().st_size,
    }


def clips_summary(root: Path) -> dict:
    return clip_summary(root / WORKSPACE_DIR / DATA_DIR / "clips.jsonl")


def clip_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        clips = read_clips_jsonl(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    method_counts = count_by_value(clip.method.value for clip in clips)
    media_counts = count_by_value(clip.media_kind.value for clip in clips)
    return {
        "exists": True,
        "valid": True,
        "count": len(clips),
        "method_counts": method_counts,
        "media_kind_counts": media_counts,
        "total_duration_seconds": round(
            sum(clip.boundary.duration_seconds for clip in clips),
            3,
        ),
    }


def latest_run_summary(root: Path, run_id: str | None) -> dict:
    if not run_id:
        return {"run_id": None}
    run_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    payload = {
        "run_id": run_id,
        "exists": run_dir.exists(),
    }
    command_path = run_dir / "command.json"
    if command_path.exists():
        try:
            command = json.loads(command_path.read_text(encoding="utf-8"))
            payload["command"] = command.get("command")
            if "scope" in command:
                payload["scope"] = command["scope"]
        except json.JSONDecodeError as exc:
            payload["command_error"] = str(exc)
    step_result_path = run_dir / "step_result.json"
    if step_result_path.exists():
        try:
            payload["step_result"] = json.loads(step_result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            payload["step_result_error"] = str(exc)
    return payload

