from __future__ import annotations

import hashlib
import json
from pathlib import Path

from artist_portrait_editor.capabilities import capability_warnings, detect_capabilities
from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import CACHE_DIR, DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.media.keyframes import (
    KeyframeExtractionError,
    extract_keyframe_image,
    ffmpeg_version,
)
from artist_portrait_editor.media.scene_detection import (
    SceneDetectionError,
    detect_scenes_pyscenedetect,
    pyscenedetect_version,
)
from artist_portrait_editor.media.transcription import (
    TranscribedSegment,
    TranscriptionError,
    faster_whisper_version,
    transcribe_source_faster_whisper,
)
from artist_portrait_editor.media.scanner import (
    ScanResult,
    read_sources_jsonl,
    scan_project_sources,
    write_sources_jsonl,
)
from artist_portrait_editor.models.config import FeatureSwitch
from artist_portrait_editor.models.analysis import AnalysisRecord, AnalysisRiskFlag
from artist_portrait_editor.models.clip import (
    ClipBoundary,
    ClipMethod,
    ClipRecord,
    ClipRiskFlag,
)
from artist_portrait_editor.models.keyframe import KeyframeRecord, KeyframeRiskFlag
from artist_portrait_editor.models.model_gate import TextModelGate, TextModelGateStatus
from artist_portrait_editor.models.proposal import ProposalSet
from artist_portrait_editor.models.proposal_context import (
    ProposalAnalysisContext,
    ProposalClipContext,
    ProposalContext,
    ProposalSourceContext,
)
from artist_portrait_editor.models.state import (
    Capabilities,
    OverallStatus,
    ProjectState,
    StepLedgerEntry,
    StepStatus,
    initial_steps,
)
from artist_portrait_editor.models.source import (
    Assertion,
    MediaKind,
    RightsStatus,
    SourceRecord,
)
from artist_portrait_editor.models.transcript import (
    TranscriptRecord,
    TranscriptRiskFlag,
    WordTimestamp,
)
from artist_portrait_editor.run_records import (
    environment_snapshot,
    new_run_id,
    utc_now,
    write_json,
)


class WorkspacePrerequisiteError(Exception):
    pass


class WorkspaceDependencyError(Exception):
    pass


def project_root(project_path: Path) -> Path:
    return project_path.resolve().parent


def fingerprint_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint_inputs(paths: list[tuple[str, Path]]) -> str:
    digest = hashlib.sha256()
    for label, path in sorted(paths, key=lambda item: item[0]):
        digest.update(label.encode("utf-8"))
        digest.update(b"\0")
        if path.exists():
            digest.update(fingerprint_file(path).encode("utf-8"))
        else:
            digest.update(b"missing")
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def atomic_write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)
    return path


def state_path(root: Path) -> Path:
    return root / WORKSPACE_DIR / "state.json"


def load_state(root: Path) -> ProjectState | None:
    path = state_path(root)
    if not path.exists():
        return None
    return ProjectState.model_validate_json(path.read_text(encoding="utf-8"))


def save_state(root: Path, state: ProjectState) -> None:
    path = state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        state.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def init_workspace(project_path: Path, dry_run: bool = False) -> tuple[ProjectState, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    run_id = new_run_id()
    capabilities = detect_capabilities()
    warnings = capability_warnings(capabilities)
    input_fingerprint = fingerprint_file(project_path)

    steps = initial_steps()
    steps["validate"] = StepLedgerEntry(
        status=StepStatus.completed,
        input_fingerprint=input_fingerprint,
        output_refs=[],
        last_run_id=run_id,
        warnings=[],
    )
    steps["init"] = StepLedgerEntry(
        status=StepStatus.completed_with_warnings if warnings else StepStatus.completed,
        input_fingerprint=input_fingerprint,
        output_refs=[
            ".artist-portrait/state.json",
            f".artist-portrait/runs/{run_id}",
            f"{config.paths.output_dir.removeprefix('./')}/run_report.md",
        ],
        last_run_id=run_id,
        warnings=warnings,
    )
    state = ProjectState(
        project_id=config.project.id,
        overall_status=OverallStatus.degraded if warnings else OverallStatus.ready,
        capabilities=capabilities,
        steps=steps,
        latest_run_id=run_id,
        updated_at=utc_now(),
    )

    if dry_run:
        return state, warnings

    workspace = root / WORKSPACE_DIR
    runs_dir = workspace / RUNS_DIR / run_id
    output_dir = root / config.paths.output_dir
    for path in [
        workspace / CACHE_DIR,
        workspace / DATA_DIR,
        workspace / RUNS_DIR,
        runs_dir,
        output_dir,
    ]:
        path.mkdir(parents=True, exist_ok=True)

    write_json(runs_dir / "command.json", {"command": "init", "project": str(project_path)})
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(runs_dir / "step_result.json", {"step": "init", "status": steps["init"].status.value})
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text("init completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(output_dir, state, warnings)
    return state, warnings


def render_run_report(state: ProjectState, warnings: list[str]) -> str:
    warning_lines = "\n".join(f"- {warning}" for warning in warnings) or "- None"
    step_lines = "\n".join(
        f"- `{name}`: `{entry.status.value}`"
        for name, entry in sorted(state.steps.items())
    )
    return (
        "# Run Report\n\n"
        f"- Project ID: `{state.project_id}`\n"
        f"- Run ID: `{state.latest_run_id}`\n"
        f"- Overall Status: `{state.overall_status.value}`\n"
        f"- Updated At: `{state.updated_at}`\n\n"
        "## Boundary\n\n"
        "This report is generated from local project state and deterministic local "
        "artifacts. No transcription, visual analysis, embeddings, creative proposals, "
        "timeline generation, preview rendering, network calls, or model calls were "
        "performed by this report step.\n\n"
        "## Steps\n\n"
        f"{step_lines}\n\n"
        "## Warnings\n\n"
        f"{warning_lines}\n"
    )


def write_run_report(output_dir: Path, state: ProjectState, warnings: list[str]) -> Path:
    output_path = output_dir / "run_report.md"
    return atomic_write_text(output_path, render_run_report(state, warnings))


def stable_clip_id(source_id: str, clip_index: int, start_seconds: float, end_seconds: float) -> str:
    payload = f"{source_id}:{clip_index}:{start_seconds:.3f}:{end_seconds:.3f}"
    return "clip_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def stable_transcript_id(
    source_id: str,
    segment_index: int,
    start_seconds: float,
    end_seconds: float,
) -> str:
    payload = f"{source_id}:{segment_index}:{start_seconds:.3f}:{end_seconds:.3f}"
    return "trn_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def stable_keyframe_id(clip_id: str, frame_index: int, timestamp_seconds: float) -> str:
    payload = f"{clip_id}:{frame_index}:{timestamp_seconds:.3f}"
    return "kf_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def stable_analysis_id(clip_id: str, analysis_fingerprint: str) -> str:
    payload = f"{clip_id}:{analysis_fingerprint}"
    return "ana_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def invalidate_downstream_steps_for_sources(
    state: ProjectState,
    *,
    sources_fingerprint: str,
) -> list[str]:
    invalidated: list[str] = []
    for step_name in (
        "segment",
        "transcribe",
        "keyframes",
        "analyze",
        "map",
        "propose",
        "review_project",
    ):
        entry = state.steps.get(step_name)
        if entry is None:
            continue
        if entry.status not in {
            StepStatus.completed,
            StepStatus.completed_with_warnings,
            StepStatus.blocked,
        }:
            continue
        if entry.input_fingerprint == sources_fingerprint:
            continue
        state.steps[step_name] = StepLedgerEntry(
            status=StepStatus.invalidated,
            input_fingerprint=entry.input_fingerprint,
            output_refs=entry.output_refs,
            last_run_id=entry.last_run_id,
            warnings=[
                *entry.warnings,
                "source ledger changed; rerun this step before trusting its output",
            ],
        )
        invalidated.append(step_name)
    return invalidated


def state_as_dict(state: ProjectState) -> dict:
    return json.loads(state.model_dump_json())


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
        payload["artifact_issues"] = ledger_output_ref_issues(root, state)
    payload["artifacts"] = artifacts
    payload["summaries"] = status_summaries(root)
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
    proposal_context = summaries.get("proposal_context") or {}
    if proposal_context.get("exists") and proposal_context.get("valid", True):
        lines.append(f"proposal_context: {proposal_context.get('analysis_count', 0)} analyses")
    elif proposal_context.get("exists"):
        lines.append("proposal_context: invalid")
    else:
        lines.append("proposal_context: missing")
    text_model_gate = summaries.get("text_model_gate") or {}
    if text_model_gate.get("exists") and text_model_gate.get("valid", True):
        lines.append(f"text_model_gate: {text_model_gate.get('status')}")
    elif text_model_gate.get("exists"):
        lines.append("text_model_gate: invalid")
    else:
        lines.append("text_model_gate: missing")
    proposals = summaries.get("proposals") or {}
    if proposals.get("exists") and proposals.get("valid", True):
        lines.append(f"proposals: {proposals.get('count', 0)}")
    elif proposals.get("exists"):
        lines.append("proposals: invalid")
    else:
        lines.append("proposals: missing")
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
    proposals = proposal_summary(root / WORKSPACE_DIR / DATA_DIR / "proposals.json")
    proposal_context = proposal_context_summary(
        root / WORKSPACE_DIR / DATA_DIR / "proposal_context.json"
    )
    text_model_gate = text_model_gate_summary(
        root / WORKSPACE_DIR / DATA_DIR / "text_model_gate.json"
    )
    if (
        sources.get("valid") is True
        and proposal_context.get("valid") is False
    ):
        context_path = root / WORKSPACE_DIR / DATA_DIR / "proposal_context.json"
        issues.append(
            workspace_issue(
                code="proposal_context_invalid",
                severity="error",
                detail=str(proposal_context.get("error") or "proposal context is invalid"),
                next_action=(
                    f"fix {context_path.relative_to(root).as_posix()} or rerun "
                    f"artist-portrait propose --project {project_path}"
                ),
            )
        )
    if (
        sources.get("valid") is True
        and text_model_gate.get("valid") is False
    ):
        gate_path = root / WORKSPACE_DIR / DATA_DIR / "text_model_gate.json"
        issues.append(
            workspace_issue(
                code="text_model_gate_invalid",
                severity="error",
                detail=str(text_model_gate.get("error") or "text model gate is invalid"),
                next_action=(
                    f"fix {gate_path.relative_to(root).as_posix()} or rerun "
                    f"artist-portrait propose --project {project_path}"
                ),
            )
        )
    if (
        sources.get("valid") is True
        and proposals.get("valid") is False
    ):
        proposals_path = root / WORKSPACE_DIR / DATA_DIR / "proposals.json"
        issues.append(
            workspace_issue(
                code="proposals_invalid",
                severity="error",
                detail=str(proposals.get("error") or "proposals ledger is invalid"),
                next_action=(
                    f"fix {proposals_path.relative_to(root).as_posix()} or rerun "
                    f"artist-portrait propose --project {project_path}"
                ),
            )
        )
    elif (
        sources.get("valid") is True
        and output_summary(root / "output" / "material_map.md").get("exists")
        and state.steps.get("propose", StepLedgerEntry()).status == StepStatus.pending
        and (
            not config.data_policy.allow_remote_text_model
            or not current_capabilities.text_model
            or config.data_policy.include_absolute_paths_in_remote_requests
        )
    ):
        gate_reasons = []
        if not config.data_policy.allow_remote_text_model:
            gate_reasons.append("remote_text_model_not_allowed")
        if not current_capabilities.text_model:
            gate_reasons.append("text_model_capability_missing")
        if config.data_policy.include_absolute_paths_in_remote_requests:
            gate_reasons.append("absolute_paths_in_remote_requests_enabled")
        issues.append(
            workspace_issue(
                code="propose_text_model_missing",
                severity="warning",
                detail=(
                    "material map exists but proposal text-model gate is blocked: "
                    + ", ".join(gate_reasons)
                ),
                next_action="approve and configure the text-model proposal gate before generation",
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
    artifact_paths = {
        "state": root / WORKSPACE_DIR / "state.json",
        "sources": root / WORKSPACE_DIR / DATA_DIR / "sources.jsonl",
        "clips": root / WORKSPACE_DIR / DATA_DIR / "clips.jsonl",
        "transcripts": root / WORKSPACE_DIR / DATA_DIR / "transcripts.jsonl",
        "keyframes": root / WORKSPACE_DIR / DATA_DIR / "keyframes.jsonl",
        "analysis": root / WORKSPACE_DIR / DATA_DIR / "analysis.jsonl",
        "relations": root / WORKSPACE_DIR / DATA_DIR / "relations.jsonl",
        "proposal_context": root / WORKSPACE_DIR / DATA_DIR / "proposal_context.json",
        "text_model_gate": root / WORKSPACE_DIR / DATA_DIR / "text_model_gate.json",
        "proposals_json": root / WORKSPACE_DIR / DATA_DIR / "proposals.json",
        "run_report": root / "output" / "run_report.md",
        "scan_report": root / "output" / "scan_report.md",
        "clip_report": root / "output" / "clip_report.md",
        "analysis_report": root / "output" / "analysis_report.md",
        "material_map": root / "output" / "material_map.md",
        "proposals_md": root / "output" / "proposals.md",
        "timeline_draft": root / "output" / "timeline_draft.json",
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
    }
    for step_name, entry in sorted(state.steps.items()):
        if entry.status not in completed_statuses:
            continue
        for output_ref in entry.output_refs:
            if not output_ref:
                continue
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
    scan_report_path = root / "output" / "scan_report.md"
    clip_report_path = root / "output" / "clip_report.md"
    analysis_report_path = root / "output" / "analysis_report.md"
    material_map_path = root / "output" / "material_map.md"
    risk_report_path = root / "output" / "risk_report.md"
    proposals_path = root / WORKSPACE_DIR / DATA_DIR / "proposals.json"
    proposal_context_path = root / WORKSPACE_DIR / DATA_DIR / "proposal_context.json"
    text_model_gate_path = root / WORKSPACE_DIR / DATA_DIR / "text_model_gate.json"
    return {
        "sources": source_summary(sources_path),
        "clips": clip_summary(clips_path),
        "transcripts": transcript_summary(transcripts_path),
        "keyframes": keyframe_summary(keyframes_path, root=root),
        "analysis": analysis_summary(analysis_path),
        "scan_report": output_summary(scan_report_path),
        "clip_report": output_summary(clip_report_path),
        "analysis_report": output_summary(analysis_report_path),
        "material_map": output_summary(material_map_path),
        "proposal_context": proposal_context_summary(proposal_context_path),
        "text_model_gate": text_model_gate_summary(text_model_gate_path),
        "proposals": proposal_summary(proposals_path),
        "risk_report": output_summary(risk_report_path),
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


def write_clips_jsonl(root: Path, clips: list[ClipRecord]) -> Path:
    output = root / WORKSPACE_DIR / DATA_DIR / "clips.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".jsonl.tmp")
    tmp.write_text(
        "".join(
            json.dumps(clip.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
            + "\n"
            for clip in clips
        ),
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def read_clips_jsonl(path: Path) -> list[ClipRecord]:
    clips: list[ClipRecord] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            clips.append(ClipRecord.model_validate_json(line))
        except ValueError as exc:
            raise WorkspacePrerequisiteError(
                f"invalid ClipRecord JSONL at line {line_number}: {exc}"
            ) from exc
    return clips


def write_transcripts_jsonl(root: Path, transcripts: list[TranscriptRecord]) -> Path:
    output = root / WORKSPACE_DIR / DATA_DIR / "transcripts.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".jsonl.tmp")
    tmp.write_text(
        "".join(
            json.dumps(transcript.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
            + "\n"
            for transcript in transcripts
        ),
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def read_transcripts_jsonl(path: Path) -> list[TranscriptRecord]:
    transcripts: list[TranscriptRecord] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            transcripts.append(TranscriptRecord.model_validate_json(line))
        except ValueError as exc:
            raise WorkspacePrerequisiteError(
                f"invalid TranscriptRecord JSONL at line {line_number}: {exc}"
            ) from exc
    return transcripts


def write_keyframes_jsonl(root: Path, keyframes: list[KeyframeRecord]) -> Path:
    output = root / WORKSPACE_DIR / DATA_DIR / "keyframes.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".jsonl.tmp")
    tmp.write_text(
        "".join(
            json.dumps(keyframe.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
            + "\n"
            for keyframe in keyframes
        ),
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def read_keyframes_jsonl(path: Path) -> list[KeyframeRecord]:
    keyframes: list[KeyframeRecord] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            keyframes.append(KeyframeRecord.model_validate_json(line))
        except ValueError as exc:
            raise WorkspacePrerequisiteError(
                f"invalid KeyframeRecord JSONL at line {line_number}: {exc}"
            ) from exc
    return keyframes


def write_analysis_jsonl(root: Path, analyses: list[AnalysisRecord]) -> Path:
    output = root / WORKSPACE_DIR / DATA_DIR / "analysis.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".jsonl.tmp")
    tmp.write_text(
        "".join(
            json.dumps(analysis.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
            + "\n"
            for analysis in analyses
        ),
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def read_analysis_jsonl(path: Path) -> list[AnalysisRecord]:
    analyses: list[AnalysisRecord] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            analyses.append(AnalysisRecord.model_validate_json(line))
        except ValueError as exc:
            raise WorkspacePrerequisiteError(
                f"invalid AnalysisRecord JSONL at line {line_number}: {exc}"
            ) from exc
    return analyses


def read_proposals_json(path: Path) -> ProposalSet:
    try:
        return ProposalSet.model_validate_json(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise WorkspacePrerequisiteError(f"invalid ProposalSet JSON: {exc}") from exc


def read_proposal_context_json(path: Path) -> ProposalContext:
    try:
        return ProposalContext.model_validate_json(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise WorkspacePrerequisiteError(f"invalid ProposalContext JSON: {exc}") from exc


def read_text_model_gate_json(path: Path) -> TextModelGate:
    try:
        return TextModelGate.model_validate_json(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise WorkspacePrerequisiteError(f"invalid TextModelGate JSON: {exc}") from exc


def transcript_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        transcripts = read_transcripts_jsonl(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    language_counts = count_by_value(
        transcript.language or "unknown" for transcript in transcripts
    )
    return {
        "exists": True,
        "valid": True,
        "count": len(transcripts),
        "language_counts": language_counts,
        "total_duration_seconds": round(
            sum(
                transcript.end_seconds - transcript.start_seconds
                for transcript in transcripts
            ),
            3,
        ),
    }


def keyframe_summary(path: Path, *, root: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        keyframes = read_keyframes_jsonl(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    missing_cache = [
        keyframe.image_path
        for keyframe in keyframes
        if not (root / keyframe.image_path).exists()
    ]
    method_counts = count_by_value(keyframe.method for keyframe in keyframes)
    return {
        "exists": True,
        "valid": True,
        "count": len(keyframes),
        "method_counts": method_counts,
        "missing_cache_count": len(missing_cache),
        "missing_cache_refs": missing_cache[:10],
    }


def analysis_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        analyses = read_analysis_jsonl(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    risk_counts = count_by_value(
        flag.value
        for analysis in analyses
        for flag in analysis.risk_flags
    )
    audio_counts = count_by_value(
        str(analysis.original_audio_usability.value) for analysis in analyses
    )
    return {
        "exists": True,
        "valid": True,
        "count": len(analyses),
        "risk_counts": risk_counts,
        "original_audio_usability_counts": audio_counts,
    }


def proposal_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        proposal_set = read_proposals_json(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    return {
        "exists": True,
        "valid": True,
        "count": len(proposal_set.proposals),
        "proposal_ids": [proposal.proposal_id.value for proposal in proposal_set.proposals],
        "method": proposal_set.method,
    }


def proposal_context_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        context = read_proposal_context_json(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    return {
        "exists": True,
        "valid": True,
        "context_id": context.context_id,
        "source_count": len(context.sources),
        "clip_count": len(context.clips),
        "analysis_count": len(context.analyses),
        "material_map_fingerprint": context.material_map_fingerprint,
    }


def text_model_gate_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        gate = read_text_model_gate_json(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    return {
        "exists": True,
        "valid": True,
        "gate_id": gate.gate_id,
        "status": gate.status.value,
        "reasons": gate.reasons,
        "remote_text_model_allowed": gate.remote_text_model_allowed,
        "text_model_capability": gate.text_model_capability,
    }


def stable_context_id(project_id: str, input_fingerprint: str) -> str:
    payload = f"{project_id}:{input_fingerprint}"
    return "ctx_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def stable_gate_id(project_id: str, proposal_context_fingerprint: str) -> str:
    payload = f"{project_id}:{proposal_context_fingerprint}"
    return "gate_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def pending_visual_fields(analysis: AnalysisRecord) -> list[str]:
    pending = []
    if analysis.shot_size.value is None:
        pending.append("shot_size")
    if analysis.camera_motion.value is None:
        pending.append("camera_motion")
    if analysis.visual_quality.value is None:
        pending.append("visual_quality")
    if not analysis.emotion_candidates.value:
        pending.append("emotion_candidates")
    if not analysis.action_candidates.value:
        pending.append("action_candidates")
    return pending


def build_proposal_context(
    *,
    config,
    sources: list[SourceRecord],
    clips: list[ClipRecord],
    analyses: list[AnalysisRecord],
    sources_ref: str,
    clips_ref: str,
    analysis_ref: str,
    material_map_ref: str,
    material_map_fingerprint: str,
    input_fingerprint: str,
) -> ProposalContext:
    sorted_sources = sorted(sources, key=lambda item: item.primary_location)
    sorted_clips = sorted(clips, key=lambda item: (item.source_location, item.clip_index))
    sorted_analyses = sorted(
        analyses,
        key=lambda item: (item.source_location, item.start_seconds, item.clip_id),
    )
    return ProposalContext(
        context_id=stable_context_id(config.project.id, input_fingerprint),
        project_id=config.project.id,
        material_map_ref=material_map_ref,
        material_map_fingerprint=material_map_fingerprint,
        sources_ref=sources_ref,
        clips_ref=clips_ref,
        analysis_ref=analysis_ref,
        input_fingerprint=input_fingerprint,
        creative_brief=config.creative_brief,
        content_policy=config.content_policy,
        proposal_ids_required=[
            "proposal_safe",
            "proposal_advanced",
            "proposal_risky",
        ],
        sources=[
            ProposalSourceContext(
                source_id=source.source_id,
                primary_location=source.primary_location,
                media_kind=source.media_kind,
                source_type=str(source.source_type.value),
                rights_status=str(source.rights_status.value),
                duration_seconds=source.media_probe.duration,
                forbidden_by_user=source.forbidden_by_user,
                risk_flags=[flag.value for flag in source.risk_flags],
            )
            for source in sorted_sources
        ],
        clips=[
            ProposalClipContext(
                clip_id=clip.clip_id,
                source_id=clip.source_id,
                source_location=clip.source_location,
                media_kind=clip.media_kind,
                start_seconds=clip.boundary.start_seconds,
                end_seconds=clip.boundary.end_seconds,
                duration_seconds=clip.boundary.duration_seconds,
                method=clip.method.value,
                risk_flags=[flag.value for flag in clip.risk_flags],
            )
            for clip in sorted_clips
        ],
        analyses=[
            ProposalAnalysisContext(
                analysis_id=analysis.analysis_id,
                clip_id=analysis.clip_id,
                source_id=analysis.source_id,
                material_type=str(analysis.material_type.value),
                original_audio_usability=str(analysis.original_audio_usability.value),
                transcript_refs=analysis.transcript_refs,
                keyframe_refs=analysis.keyframe_refs,
                pending_visual_fields=pending_visual_fields(analysis),
                risk_flags=[flag.value for flag in analysis.risk_flags],
                review_score=analysis_review_score(analysis),
            )
            for analysis in sorted_analyses
        ],
        evidence=[
            {"type": "source_ledger", "ref": sources_ref},
            {"type": "clip_ledger", "ref": clips_ref},
            {"type": "analysis_ledger", "ref": analysis_ref},
            {"type": "material_map", "ref": material_map_ref},
        ],
        constraints=[
            "Generate exactly proposal_safe, proposal_advanced, and proposal_risky.",
            "Every factual claim must cite source, clip, analysis, or material_map evidence.",
            "Do not use forbidden_by_user sources.",
            "Do not infer visual semantics from keyframes in the current gate.",
            "Do not fabricate missing material, identity, dates, rights, dialogue, or timecodes.",
        ],
        bgm_requirements=[
            "Future proposals must describe BGM strategy without selecting tracks in this gate.",
            "Future BGM strategy must account for mood, BPM, section structure, pacing, transitions, original audio, speech ducking, and rights status.",
        ],
        blocked_capabilities=[
            "full_creative_proposal_generation",
            "timeline_generation",
            "bgm_selection",
            "beat_analysis",
            "preview_rendering",
            "vision_analysis",
            "network_search",
            "image_generation_or_editing",
        ],
    )


def write_proposal_context_json(root: Path, context: ProposalContext) -> Path:
    output = root / WORKSPACE_DIR / DATA_DIR / "proposal_context.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(context.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def build_text_model_gate(
    *,
    config,
    capabilities: Capabilities,
    proposal_context_ref: str,
    proposal_context_fingerprint: str,
) -> TextModelGate:
    reasons: list[str] = []
    next_steps: list[str] = []
    if not config.data_policy.allow_remote_text_model:
        reasons.append("remote_text_model_not_allowed")
        next_steps.append("set data_policy.allow_remote_text_model only after a proposal model gate is approved")
    if not capabilities.text_model:
        reasons.append("text_model_capability_missing")
        next_steps.append("provide an approved local or remote text model adapter")
    if config.data_policy.include_absolute_paths_in_remote_requests:
        reasons.append("absolute_paths_in_remote_requests_enabled")
        next_steps.append("disable absolute project paths for proposal model requests")
    status = TextModelGateStatus.ready if not reasons else TextModelGateStatus.blocked
    return TextModelGate(
        gate_id=stable_gate_id(config.project.id, proposal_context_fingerprint),
        project_id=config.project.id,
        proposal_context_ref=proposal_context_ref,
        proposal_context_fingerprint=proposal_context_fingerprint,
        status=status,
        remote_text_model_allowed=config.data_policy.allow_remote_text_model,
        text_model_capability=capabilities.text_model,
        include_absolute_paths_in_remote_requests=(
            config.data_policy.include_absolute_paths_in_remote_requests
        ),
        reasons=reasons,
        required_next_steps=next_steps,
    )


def write_text_model_gate_json(root: Path, gate: TextModelGate) -> Path:
    output = root / WORKSPACE_DIR / DATA_DIR / "text_model_gate.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(gate.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def build_transcript_records_for_source(
    *,
    record: SourceRecord,
    source_fingerprint: str,
    segments: list[TranscribedSegment],
    method_version: str,
) -> list[TranscriptRecord]:
    transcripts: list[TranscriptRecord] = []
    for segment_index, segment in enumerate(segments):
        risk_flags: list[TranscriptRiskFlag] = []
        text = segment.text.strip()
        if not text:
            risk_flags.append(TranscriptRiskFlag.empty_text)
        if segment.confidence < 0.5:
            risk_flags.append(TranscriptRiskFlag.low_confidence)
        risk_flags.append(TranscriptRiskFlag.unclassified_text_type)
        transcripts.append(
            TranscriptRecord(
                transcript_id=stable_transcript_id(
                    record.source_id,
                    segment_index,
                    segment.start_seconds,
                    segment.end_seconds,
                ),
                source_id=record.source_id,
                source_location=record.primary_location,
                source_content_hash=record.content_hash,
                source_fingerprint=source_fingerprint,
                segment_index=segment_index,
                start_seconds=segment.start_seconds,
                end_seconds=segment.end_seconds,
                text=text,
                language=segment.language,
                speaker=None,
                text_type=None,
                word_timestamps=[
                    WordTimestamp(
                        word=word.word,
                        start_seconds=word.start_seconds,
                        end_seconds=word.end_seconds,
                        confidence=word.confidence,
                    )
                    for word in segment.words
                ],
                method="faster_whisper",
                method_version=method_version,
                confidence=segment.confidence,
                evidence=[
                    {"type": "source", "ref": record.source_id},
                    {"type": "tool", "ref": method_version},
                ],
                user_confirmed=False,
                risk_flags=risk_flags,
                notes=(
                    "ASR text is an audible-content candidate only; it does not "
                    "classify interview, lyrics, role dialogue, or captions"
                ),
            )
        )
    return transcripts


def build_transcripts(
    *,
    root: Path,
    records: list[SourceRecord],
    source_fingerprint: str,
) -> list[TranscriptRecord]:
    transcripts: list[TranscriptRecord] = []
    method_version = f"faster-whisper-{faster_whisper_version()}"
    for record in sorted(records, key=lambda item: item.primary_location):
        segments = transcribe_source_faster_whisper(root / record.primary_location)
        transcripts.extend(
            build_transcript_records_for_source(
                record=record,
                source_fingerprint=source_fingerprint,
                segments=segments,
                method_version=method_version,
            )
        )
    return transcripts


def build_keyframes(
    *,
    root: Path,
    clips: list[ClipRecord],
    clips_fingerprint: str,
) -> tuple[list[KeyframeRecord], list[str]]:
    keyframes: list[KeyframeRecord] = []
    warnings: list[str] = []
    video_clips = [clip for clip in clips if clip.media_kind == MediaKind.video]
    if not video_clips:
        return [], ["no video clips available for keyframe extraction"]

    method_version = ffmpeg_version()
    cache_dir = root / WORKSPACE_DIR / CACHE_DIR / "keyframes"
    for frame_index, clip in enumerate(
        sorted(video_clips, key=lambda item: (item.source_location, item.clip_index))
    ):
        timestamp = round(
            clip.boundary.start_seconds + (clip.boundary.duration_seconds / 2.0),
            3,
        )
        keyframe_id = stable_keyframe_id(clip.clip_id, frame_index, timestamp)
        output_path = cache_dir / f"{keyframe_id}.jpg"
        extract_keyframe_image(
            source_path=root / clip.source_location,
            output_path=output_path,
            timestamp_seconds=timestamp,
        )
        keyframes.append(
            KeyframeRecord(
                keyframe_id=keyframe_id,
                clip_id=clip.clip_id,
                source_id=clip.source_id,
                source_location=clip.source_location,
                source_content_hash=clip.source_content_hash,
                clip_fingerprint=clips_fingerprint,
                frame_index=frame_index,
                timestamp_seconds=timestamp,
                image_path=output_path.relative_to(root).as_posix(),
                method="ffmpeg",
                method_version=method_version,
                evidence=[
                    {"type": "clip", "ref": clip.clip_id},
                    {"type": "tool", "ref": method_version},
                ],
                risk_flags=[],
                notes=(
                    "deterministic midpoint frame extraction; this is visual "
                    "sampling only, not visual analysis"
                ),
            )
        )
    return keyframes, warnings


def not_run_assertion(*, evidence: list[dict[str, str]]) -> Assertion:
    return Assertion(
        value=None,
        method="not_run_current_gate",
        level=0,
        confidence=0.0,
        evidence=evidence,
        user_confirmed=False,
    )


def copied_assertion(assertion: Assertion, *, fallback_evidence: list[dict[str, str]]) -> Assertion:
    return Assertion(
        value=assertion.value,
        method=assertion.method,
        level=assertion.level,
        confidence=assertion.confidence,
        evidence=assertion.evidence or fallback_evidence,
        user_confirmed=assertion.user_confirmed,
    )


def original_audio_assertion(
    *,
    source: SourceRecord,
    transcript_refs: list[str],
) -> Assertion:
    evidence = [{"type": "source", "ref": source.source_id}]
    evidence.extend({"type": "transcript", "ref": ref} for ref in transcript_refs)
    if not source.media_probe.audio_present:
        value = "not_present"
        confidence = 1.0
    elif transcript_refs:
        value = "present_transcript_available"
        confidence = 0.9
    else:
        value = "present_untranscribed"
        confidence = 0.75
    return Assertion(
        value=value,
        method="ffprobe_transcript_presence",
        level=0,
        confidence=confidence,
        evidence=evidence,
        user_confirmed=False,
    )


def transcript_refs_for_clip(
    clip: ClipRecord,
    transcripts: list[TranscriptRecord],
) -> list[str]:
    refs: list[str] = []
    for transcript in transcripts:
        if transcript.source_id != clip.source_id:
            continue
        if transcript.end_seconds <= clip.boundary.start_seconds:
            continue
        if transcript.start_seconds >= clip.boundary.end_seconds:
            continue
        refs.append(transcript.transcript_id)
    return sorted(refs)


def build_analysis(
    *,
    clips: list[ClipRecord],
    sources: list[SourceRecord],
    transcripts: list[TranscriptRecord],
    keyframes: list[KeyframeRecord],
    clip_fingerprint: str,
    analysis_fingerprint: str,
) -> tuple[list[AnalysisRecord], list[str]]:
    source_by_id = {source.source_id: source for source in sources}
    keyframes_by_clip: dict[str, list[str]] = {}
    for keyframe in keyframes:
        keyframes_by_clip.setdefault(keyframe.clip_id, []).append(keyframe.keyframe_id)

    analyses: list[AnalysisRecord] = []
    warnings: list[str] = []
    for clip in sorted(clips, key=lambda item: (item.source_location, item.clip_index)):
        source = source_by_id.get(clip.source_id)
        if source is None:
            warnings.append(f"missing source for clip {clip.clip_id}; skipped analysis")
            continue

        transcript_refs = transcript_refs_for_clip(clip, transcripts)
        keyframe_refs = sorted(keyframes_by_clip.get(clip.clip_id, []))
        evidence = [
            {"type": "source", "ref": source.source_id},
            {"type": "clip", "ref": clip.clip_id},
        ]
        evidence.extend({"type": "transcript", "ref": ref} for ref in transcript_refs)
        evidence.extend({"type": "keyframe", "ref": ref} for ref in keyframe_refs)

        risk_flags: list[AnalysisRiskFlag] = [AnalysisRiskFlag.visual_analysis_not_run]
        if source.risk_flags:
            risk_flags.append(AnalysisRiskFlag.inherited_source_risk)
        if clip.media_kind == MediaKind.video and not keyframe_refs:
            risk_flags.append(AnalysisRiskFlag.keyframe_missing)
        if source.media_probe.audio_present and not transcript_refs:
            risk_flags.append(AnalysisRiskFlag.transcript_missing)
        if not source.media_probe.audio_present:
            risk_flags.append(AnalysisRiskFlag.audio_missing)
        if clip.media_kind == MediaKind.audio:
            risk_flags.append(AnalysisRiskFlag.audio_only_clip)
        if clip.boundary.duration_seconds < 3:
            risk_flags.append(AnalysisRiskFlag.short_clip)

        analyses.append(
            AnalysisRecord(
                analysis_id=stable_analysis_id(clip.clip_id, analysis_fingerprint),
                clip_id=clip.clip_id,
                source_id=clip.source_id,
                source_location=clip.source_location,
                source_content_hash=clip.source_content_hash,
                clip_fingerprint=clip_fingerprint,
                analysis_fingerprint=analysis_fingerprint,
                media_kind=clip.media_kind,
                start_seconds=clip.boundary.start_seconds,
                end_seconds=clip.boundary.end_seconds,
                duration_seconds=clip.boundary.duration_seconds,
                material_type=copied_assertion(
                    source.source_type,
                    fallback_evidence=[{"type": "source", "ref": source.source_id}],
                ),
                shot_size=not_run_assertion(evidence=evidence),
                camera_motion=not_run_assertion(evidence=evidence),
                emotion_candidates=Assertion(
                    value=[],
                    method="not_run_current_gate",
                    level=0,
                    confidence=0.0,
                    evidence=evidence,
                    user_confirmed=False,
                ),
                action_candidates=Assertion(
                    value=[],
                    method="not_run_current_gate",
                    level=0,
                    confidence=0.0,
                    evidence=evidence,
                    user_confirmed=False,
                ),
                visual_quality=not_run_assertion(evidence=evidence),
                original_audio_usability=original_audio_assertion(
                    source=source,
                    transcript_refs=transcript_refs,
                ),
                transcript_refs=transcript_refs,
                keyframe_refs=keyframe_refs,
                evidence=evidence,
                risk_flags=sorted(set(risk_flags), key=lambda flag: flag.value),
                notes=(
                    "V0-008 records deterministic and context-derived analysis only; "
                    "shot size, motion, emotion, action, and visual quality remain "
                    "unclassified until a later visual-analysis gate opens"
                ),
            )
        )
    if not analyses:
        warnings.append("no analysis records generated")
    return analyses, warnings


def build_fixed_window_clips(
    *,
    records: list[SourceRecord],
    sources_fingerprint: str,
    window_seconds: float = 10.0,
    fallback: bool = False,
) -> list[ClipRecord]:
    clips: list[ClipRecord] = []
    for record in sorted(records, key=lambda item: item.primary_location):
        clips.extend(
            build_fixed_window_clips_for_record(
                record=record,
                sources_fingerprint=sources_fingerprint,
                window_seconds=window_seconds,
                fallback=fallback,
            )
        )
    return clips


def build_fixed_window_clips_for_record(
    *,
    record: SourceRecord,
    sources_fingerprint: str,
    window_seconds: float = 10.0,
    fallback: bool = False,
) -> list[ClipRecord]:
    clips: list[ClipRecord] = []
    duration = record.media_probe.duration
    start = 0.0
    clip_index = 0
    while start < duration:
        end = min(start + window_seconds, duration)
        clip_duration = end - start
        risk_flags: list[ClipRiskFlag] = []
        if record.risk_flags:
            risk_flags.append(ClipRiskFlag.inherited_source_risk)
        if fallback:
            risk_flags.append(ClipRiskFlag.scene_detection_fallback)
        if clip_duration < min(window_seconds, duration):
            risk_flags.append(ClipRiskFlag.short_tail)
        clips.append(
            ClipRecord(
                clip_id=stable_clip_id(record.source_id, clip_index, start, end),
                source_id=record.source_id,
                source_location=record.primary_location,
                source_content_hash=record.content_hash,
                source_fingerprint=sources_fingerprint,
                clip_index=clip_index,
                media_kind=record.media_kind,
                boundary=ClipBoundary(
                    start_seconds=round(start, 3),
                    end_seconds=round(end, 3),
                    duration_seconds=round(clip_duration, 3),
                ),
                method=ClipMethod.fixed_window,
                method_version="fixed-window-v1",
                boundary_confidence=0.5,
                evidence=[{"type": "source", "ref": record.source_id}],
                inherited_source_risk_flags=record.risk_flags,
                risk_flags=risk_flags,
                notes=(
                    "deterministic fixed-window segmentation after scene detection fallback"
                    if fallback
                    else "deterministic fixed-window segmentation"
                ),
            )
        )
        clip_index += 1
        start = end
    return clips


def build_pyscenedetect_clips_for_record(
    *,
    record: SourceRecord,
    sources_fingerprint: str,
    boundaries: list[tuple[float, float]],
    method_version: str,
) -> list[ClipRecord]:
    clips: list[ClipRecord] = []
    duration = record.media_probe.duration
    for clip_index, (raw_start, raw_end) in enumerate(boundaries):
        start = max(0.0, round(raw_start, 3))
        end = min(duration, round(raw_end, 3))
        if end <= start:
            continue
        clip_duration = round(end - start, 3)
        risk_flags: list[ClipRiskFlag] = []
        if record.risk_flags:
            risk_flags.append(ClipRiskFlag.inherited_source_risk)
        clips.append(
            ClipRecord(
                clip_id=stable_clip_id(record.source_id, clip_index, start, end),
                source_id=record.source_id,
                source_location=record.primary_location,
                source_content_hash=record.content_hash,
                source_fingerprint=sources_fingerprint,
                clip_index=clip_index,
                media_kind=record.media_kind,
                boundary=ClipBoundary(
                    start_seconds=start,
                    end_seconds=end,
                    duration_seconds=clip_duration,
                ),
                method=ClipMethod.pyscenedetect,
                method_version=method_version,
                boundary_confidence=0.75,
                evidence=[
                    {"type": "source", "ref": record.source_id},
                    {"type": "tool", "ref": method_version},
                ],
                inherited_source_risk_flags=record.risk_flags,
                risk_flags=risk_flags,
                notes="PySceneDetect content-detector scene segmentation",
            )
        )
    if not clips:
        raise SceneDetectionError(
            f"PySceneDetect produced no in-range scenes for {record.primary_location}"
        )
    return clips


def build_segment_clips(
    *,
    root: Path,
    capabilities: Capabilities,
    scene_detection: FeatureSwitch,
    records: list[SourceRecord],
    sources_fingerprint: str,
) -> tuple[list[ClipRecord], list[str]]:
    clips: list[ClipRecord] = []
    warnings: list[str] = []
    method_version = f"pyscenedetect-{pyscenedetect_version()}"

    for record in sorted(records, key=lambda item: item.primary_location):
        if record.media_kind != MediaKind.video or scene_detection == FeatureSwitch.off:
            clips.extend(
                build_fixed_window_clips_for_record(
                    record=record,
                    sources_fingerprint=sources_fingerprint,
                )
            )
            continue

        if not capabilities.pyscenedetect:
            if scene_detection == FeatureSwitch.required:
                raise WorkspaceDependencyError(
                    "scene_detection is required but PySceneDetect is not available"
                )
            warnings.append(
                "pyscenedetect_missing: using fixed_window for "
                f"{record.primary_location}"
            )
            clips.extend(
                build_fixed_window_clips_for_record(
                    record=record,
                    sources_fingerprint=sources_fingerprint,
                    fallback=True,
                )
            )
            continue

        try:
            boundaries = detect_scenes_pyscenedetect(root / record.primary_location)
            clips.extend(
                build_pyscenedetect_clips_for_record(
                    record=record,
                    sources_fingerprint=sources_fingerprint,
                    boundaries=boundaries,
                    method_version=method_version,
                )
            )
        except SceneDetectionError as exc:
            if scene_detection == FeatureSwitch.required:
                raise WorkspaceDependencyError(
                    f"scene_detection is required but PySceneDetect failed: {exc}"
                ) from exc
            warnings.append(
                "pyscenedetect_failed_fallback: using fixed_window for "
                f"{record.primary_location}: {exc}"
            )
            clips.extend(
                build_fixed_window_clips_for_record(
                    record=record,
                    sources_fingerprint=sources_fingerprint,
                    fallback=True,
                )
            )
    return clips, warnings


def invalidate_downstream_steps_for_clips(
    state: ProjectState,
    *,
    clips_fingerprint: str,
) -> list[str]:
    invalidated: list[str] = []
    for step_name in ("keyframes", "analyze", "map", "propose", "review_project"):
        entry = state.steps.get(step_name)
        if entry is None:
            continue
        if entry.status not in {
            StepStatus.completed,
            StepStatus.completed_with_warnings,
            StepStatus.blocked,
        }:
            continue
        if entry.input_fingerprint == clips_fingerprint:
            continue
        state.steps[step_name] = StepLedgerEntry(
            status=StepStatus.invalidated,
            input_fingerprint=entry.input_fingerprint,
            output_refs=entry.output_refs,
            last_run_id=entry.last_run_id,
            warnings=[
                *entry.warnings,
                "clips ledger changed; rerun this step before trusting its output",
            ],
        )
        invalidated.append(step_name)
    return invalidated


def invalidate_downstream_steps_for_analysis_input(
    state: ProjectState,
    *,
    input_fingerprint: str,
    reason: str,
) -> list[str]:
    invalidated: list[str] = []
    for step_name in ("analyze", "map", "propose", "review_project"):
        entry = state.steps.get(step_name)
        if entry is None:
            continue
        if entry.status not in {
            StepStatus.completed,
            StepStatus.completed_with_warnings,
            StepStatus.blocked,
        }:
            continue
        if entry.input_fingerprint == input_fingerprint:
            continue
        state.steps[step_name] = StepLedgerEntry(
            status=StepStatus.invalidated,
            input_fingerprint=entry.input_fingerprint,
            output_refs=entry.output_refs,
            last_run_id=entry.last_run_id,
            warnings=[
                *entry.warnings,
                f"{reason}; rerun this step before trusting its output",
            ],
        )
        invalidated.append(step_name)
    return invalidated


def invalidate_downstream_steps_for_analysis(
    state: ProjectState,
    *,
    analysis_fingerprint: str,
) -> list[str]:
    invalidated: list[str] = []
    for step_name in ("map", "propose", "review_project"):
        entry = state.steps.get(step_name)
        if entry is None:
            continue
        if entry.status not in {
            StepStatus.completed,
            StepStatus.completed_with_warnings,
            StepStatus.blocked,
        }:
            continue
        if entry.input_fingerprint == analysis_fingerprint:
            continue
        state.steps[step_name] = StepLedgerEntry(
            status=StepStatus.invalidated,
            input_fingerprint=entry.input_fingerprint,
            output_refs=entry.output_refs,
            last_run_id=entry.last_run_id,
            warnings=[
                *entry.warnings,
                "analysis ledger changed; rerun this step before trusting its output",
            ],
        )
        invalidated.append(step_name)
    return invalidated


def invalidate_downstream_steps_for_map(
    state: ProjectState,
    *,
    map_fingerprint: str,
) -> list[str]:
    invalidated: list[str] = []
    for step_name in ("propose",):
        entry = state.steps.get(step_name)
        if entry is None:
            continue
        if entry.status not in {
            StepStatus.completed,
            StepStatus.completed_with_warnings,
            StepStatus.blocked,
        }:
            continue
        if entry.input_fingerprint == map_fingerprint:
            continue
        state.steps[step_name] = StepLedgerEntry(
            status=StepStatus.invalidated,
            input_fingerprint=entry.input_fingerprint,
            output_refs=entry.output_refs,
            last_run_id=entry.last_run_id,
            warnings=[
                *entry.warnings,
                "material map changed; rerun this step before trusting its output",
            ],
        )
        invalidated.append(step_name)
    return invalidated


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


def scan_workspace(project_path: Path) -> tuple[ScanResult, ProjectState]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise RuntimeError("scan requires initialized state")

    run_id = new_run_id()
    previous_sources_path = root / WORKSPACE_DIR / DATA_DIR / "sources.jsonl"
    previous_records = (
        read_sources_jsonl(previous_sources_path)
        if previous_sources_path.exists()
        else []
    )
    result = scan_project_sources(root=root, config=config, previous_records=previous_records)
    output_refs: list[str] = []
    output_dir = root / config.paths.output_dir
    invalidated_steps: list[str] = []
    if result.records or not result.errors:
        output_path = write_sources_jsonl(root, result.records)
        output_refs.append(output_path.relative_to(root).as_posix())
        sources_fingerprint = fingerprint_file(output_path)
        invalidated_steps = invalidate_downstream_steps_for_sources(
            state,
            sources_fingerprint=sources_fingerprint,
        )
        scan_report_path = output_dir / "scan_report.md"
        atomic_write_text(
            scan_report_path,
            render_scan_report(
                records=result.records,
                warnings=result.warnings,
                errors=result.errors,
                sources_ref=output_path.relative_to(root).as_posix(),
                invalidated_steps=invalidated_steps,
            ),
        )
        output_refs.append(scan_report_path.relative_to(root).as_posix())

    input_fingerprint = fingerprint_file(project_path)
    if result.errors:
        status = StepStatus.failed
    elif result.warnings:
        status = StepStatus.completed_with_warnings
    else:
        status = StepStatus.completed
    state.steps["scan"] = StepLedgerEntry(
        status=status,
        input_fingerprint=input_fingerprint,
        output_refs=output_refs,
        last_run_id=run_id,
        warnings=result.warnings + result.errors,
    )
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    if result.errors:
        state.overall_status = OverallStatus.blocked
    elif result.warnings:
        state.overall_status = OverallStatus.degraded
    else:
        state.overall_status = OverallStatus.ready

    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(runs_dir / "command.json", {"command": "scan", "project": str(project_path)})
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "scan",
            "status": status.value,
            "sources": len(result.records),
            "output_refs": output_refs,
            "invalidated_steps": invalidated_steps,
        },
    )
    write_json(runs_dir / "warnings.json", result.warnings)
    write_json(runs_dir / "errors.json", result.errors)
    (runs_dir / "log.txt").write_text("scan completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(output_dir, state, result.warnings + result.errors)
    return result, state


def render_scan_report(
    *,
    records: list[SourceRecord],
    warnings: list[str],
    errors: list[str],
    sources_ref: str,
    invalidated_steps: list[str],
) -> str:
    sorted_records = sorted(records, key=lambda record: record.primary_location)
    media_counts = count_by_value(record.media_kind.value for record in sorted_records)
    rights_counts = count_by_value(str(record.rights_status.value) for record in sorted_records)
    total_duration = sum(record.media_probe.duration for record in sorted_records)
    warning_lines = "\n".join(f"- {warning}" for warning in warnings) or "- None"
    error_lines = "\n".join(f"- {error}" for error in errors) or "- None"
    invalidated_lines = "\n".join(f"- `{step}`" for step in invalidated_steps) or "- None"
    return (
        "# Scan Report\n\n"
        "This deterministic scan report is rendered from local filesystem, content "
        "hashes, sources.csv metadata, and ffprobe-derived media facts only. No "
        "transcription, visual analysis, embeddings, creative proposals, timeline "
        "generation, preview rendering, network calls, image generation/editing, or "
        "model calls were performed.\n\n"
        "## Summary\n\n"
        f"- Source ledger: `{sources_ref}`\n"
        f"- Source count: `{len(sorted_records)}`\n"
        f"- Total duration seconds: `{total_duration:.3f}`\n\n"
        "## Distribution\n\n"
        "### Media Kind\n\n"
        f"{render_count_lines(media_counts)}"
        "### Rights Status\n\n"
        f"{render_count_lines(rights_counts)}"
        "## Invalidated Downstream Steps\n\n"
        f"{invalidated_lines}\n\n"
        "## Warnings\n\n"
        f"{warning_lines}\n\n"
        "## Errors\n\n"
        f"{error_lines}\n\n"
        "## Sources\n\n"
        f"{render_scan_source_sections(sorted_records)}"
    )


def render_scan_source_sections(records: list[SourceRecord]) -> str:
    if not records:
        return "No sources were found in the current scan ledger.\n"
    sections = []
    for index, record in enumerate(records, start=1):
        probe = record.media_probe
        frame_rate = f"{probe.frame_rate:.3f}" if probe.frame_rate else "n/a"
        locations = ", ".join(f"`{location}`" for location in record.locations)
        sections.append(
            f"### {index}. `{record.primary_location}`\n\n"
            f"- Source ID: `{record.source_id}`\n"
            f"- Content hash: `{record.content_hash}`\n"
            f"- Media kind: `{record.media_kind.value}`\n"
            f"- Duration seconds: `{probe.duration:.3f}`\n"
            f"- Width: `{probe.width or 'n/a'}`\n"
            f"- Height: `{probe.height or 'n/a'}`\n"
            f"- Frame rate: `{frame_rate}`\n"
            f"- Video codec: `{probe.video_codec or 'n/a'}`\n"
            f"- Audio present: `{str(probe.audio_present).lower()}`\n"
            f"- Audio codec: `{probe.audio_codec or 'n/a'}`\n"
            f"- Rights status: `{record.rights_status.value}`\n"
            f"- Supersedes source ID: `{record.supersedes_source_id or 'none'}`\n"
            f"- Locations: {locations}\n"
        )
    return "\n".join(sections)


def segment_workspace(project_path: Path) -> tuple[Path, ProjectState, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("segment requires init to complete first")

    sources_path = root / WORKSPACE_DIR / DATA_DIR / "sources.jsonl"
    if not sources_path.exists():
        raise WorkspacePrerequisiteError("segment requires scan to complete first")

    records = read_sources_jsonl(sources_path)
    sources_fingerprint = fingerprint_file(sources_path)
    capabilities = detect_capabilities()
    state.capabilities = capabilities
    clips, segmentation_warnings = build_segment_clips(
        root=root,
        capabilities=capabilities,
        scene_detection=config.features.scene_detection,
        records=records,
        sources_fingerprint=sources_fingerprint,
    )
    warnings = segmentation_warnings
    if not records:
        warnings.append("no sources available for segmentation")
    run_id = new_run_id()
    output_dir = root / config.paths.output_dir
    clips_path = write_clips_jsonl(root, clips)
    clips_fingerprint = fingerprint_file(clips_path)
    invalidated_steps = invalidate_downstream_steps_for_clips(
        state,
        clips_fingerprint=clips_fingerprint,
    )
    clip_report_path = output_dir / "clip_report.md"
    atomic_write_text(
        clip_report_path,
        render_clip_report(
            clips=clips,
            warnings=warnings,
            clips_ref=clips_path.relative_to(root).as_posix(),
            sources_ref=sources_path.relative_to(root).as_posix(),
            invalidated_steps=invalidated_steps,
        ),
    )

    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    state.steps["segment"] = StepLedgerEntry(
        status=status,
        input_fingerprint=sources_fingerprint,
        output_refs=[
            clips_path.relative_to(root).as_posix(),
            clip_report_path.relative_to(root).as_posix(),
        ],
        last_run_id=run_id,
        warnings=warnings,
    )
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready

    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(runs_dir / "command.json", {"command": "segment", "project": str(project_path)})
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "segment",
            "status": status.value,
            "sources": len(records),
            "clips": len(clips),
            "scene_detection": config.features.scene_detection.value,
            "method_counts": count_by_value(clip.method.value for clip in clips),
            "output_refs": state.steps["segment"].output_refs,
            "invalidated_steps": invalidated_steps,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text("segment completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(output_dir, state, warnings)
    return clip_report_path, state, warnings


def render_clip_report(
    *,
    clips: list[ClipRecord],
    warnings: list[str],
    clips_ref: str,
    sources_ref: str,
    invalidated_steps: list[str],
) -> str:
    sorted_clips = sorted(clips, key=lambda clip: (clip.source_location, clip.clip_index))
    method_counts = count_by_value(clip.method.value for clip in sorted_clips)
    media_counts = count_by_value(clip.media_kind.value for clip in sorted_clips)
    source_counts = count_by_value(clip.source_location for clip in sorted_clips)
    total_duration = sum(clip.boundary.duration_seconds for clip in sorted_clips)
    warning_lines = "\n".join(f"- {warning}" for warning in warnings) or "- None"
    invalidated_lines = "\n".join(f"- `{step}`" for step in invalidated_steps) or "- None"
    return (
        "# Clip Report\n\n"
        "This deterministic clip report is rendered from local source ledger data "
        "and the configured local segmentation method. It may use PySceneDetect "
        "only when `features.scene_detection` allows it and the dependency is "
        "available; otherwise it uses fixed-window segmentation. No transcription, "
        "visual analysis, embeddings, creative proposals, timeline generation, "
        "preview rendering, network calls, BGM selection, image generation/editing, "
        "or model calls were performed.\n\n"
        "## Summary\n\n"
        f"- Source ledger: `{sources_ref}`\n"
        f"- Clip ledger: `{clips_ref}`\n"
        f"- Clip count: `{len(sorted_clips)}`\n"
        f"- Source count: `{len(source_counts)}`\n"
        f"- Total clip duration seconds: `{total_duration:.3f}`\n\n"
        "## Distribution\n\n"
        "### Method\n\n"
        f"{render_count_lines(method_counts)}"
        "### Media Kind\n\n"
        f"{render_count_lines(media_counts)}"
        "## Invalidated Downstream Steps\n\n"
        f"{invalidated_lines}\n\n"
        "## Warnings\n\n"
        f"{warning_lines}\n\n"
        "## Clips\n\n"
        f"{render_clip_sections(sorted_clips)}"
    )


def render_clip_sections(clips: list[ClipRecord]) -> str:
    if not clips:
        return "No clips were generated from the current source ledger.\n"
    sections = []
    for index, clip in enumerate(clips, start=1):
        sections.append(
            f"### {index}. `{clip.clip_id}`\n\n"
            f"- Source ID: `{clip.source_id}`\n"
            f"- Source location: `{clip.source_location}`\n"
            f"- Clip index: `{clip.clip_index}`\n"
            f"- Start seconds: `{clip.boundary.start_seconds:.3f}`\n"
            f"- End seconds: `{clip.boundary.end_seconds:.3f}`\n"
            f"- Duration seconds: `{clip.boundary.duration_seconds:.3f}`\n"
            f"- Method: `{clip.method.value}`\n"
            f"- Boundary confidence: `{clip.boundary_confidence:.3f}`\n"
        )
    return "\n".join(sections)


def transcribe_workspace(project_path: Path) -> tuple[Path | None, ProjectState, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("transcribe requires init to complete first")

    sources_path = root / WORKSPACE_DIR / DATA_DIR / "sources.jsonl"
    if not sources_path.exists():
        raise WorkspacePrerequisiteError("transcribe requires scan to complete first")

    records = read_sources_jsonl(sources_path)
    source_fingerprint = fingerprint_file(sources_path)
    capabilities = detect_capabilities()
    state.capabilities = capabilities
    run_id = new_run_id()
    output_dir = root / config.paths.output_dir
    warnings: list[str] = []
    output_path: Path | None = None
    output_refs: list[str] = []

    if config.features.transcription == FeatureSwitch.off:
        status = StepStatus.skipped
        warnings = []
    elif not capabilities.faster_whisper:
        if config.features.transcription == FeatureSwitch.required:
            raise WorkspaceDependencyError(
                "transcription is required but faster-whisper is not available"
            )
        status = StepStatus.skipped
        warnings = ["faster_whisper_missing: transcription skipped"]
    else:
        try:
            transcripts = build_transcripts(
                root=root,
                records=records,
                source_fingerprint=source_fingerprint,
            )
        except TranscriptionError as exc:
            if config.features.transcription == FeatureSwitch.required:
                raise WorkspaceDependencyError(
                    f"transcription is required but faster-whisper failed: {exc}"
                ) from exc
            status = StepStatus.skipped
            warnings = [f"faster_whisper_failed: transcription skipped: {exc}"]
        else:
            output_path = write_transcripts_jsonl(root, transcripts)
            output_refs = [output_path.relative_to(root).as_posix()]
            warnings = ["no transcript segments generated"] if not transcripts else []
            status = StepStatus.completed_with_warnings if warnings else StepStatus.completed

    analysis_invalidated_steps: list[str] = []
    clips_path = root / WORKSPACE_DIR / DATA_DIR / "clips.jsonl"
    if output_path and clips_path.exists():
        analysis_input_fingerprint = fingerprint_inputs(
            [
                ("clips", clips_path),
                ("transcripts", output_path),
                ("keyframes", root / WORKSPACE_DIR / DATA_DIR / "keyframes.jsonl"),
            ]
        )
        analysis_invalidated_steps = invalidate_downstream_steps_for_analysis_input(
            state,
            input_fingerprint=analysis_input_fingerprint,
            reason="transcript ledger changed",
        )

    state.steps["transcribe"] = StepLedgerEntry(
        status=status,
        input_fingerprint=source_fingerprint,
        output_refs=output_refs,
        last_run_id=run_id,
        warnings=warnings,
    )
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    state.overall_status = (
        OverallStatus.degraded
        if warnings
        else OverallStatus.ready
    )

    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(runs_dir / "command.json", {"command": "transcribe", "project": str(project_path)})
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "transcribe",
            "status": status.value,
            "sources": len(records),
            "transcripts": transcript_summary(output_path).get("count", 0)
            if output_path
            else 0,
            "transcription": config.features.transcription.value,
            "output_refs": output_refs,
            "invalidated_steps": analysis_invalidated_steps,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text("transcribe completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(output_dir, state, warnings)
    return output_path, state, warnings


def keyframes_workspace(project_path: Path) -> tuple[Path, ProjectState, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("keyframes requires init to complete first")

    clips_path = root / WORKSPACE_DIR / DATA_DIR / "clips.jsonl"
    if not clips_path.exists():
        raise WorkspacePrerequisiteError("keyframes requires segment to complete first")

    clips = read_clips_jsonl(clips_path)
    clips_fingerprint = fingerprint_file(clips_path)
    capabilities = detect_capabilities()
    state.capabilities = capabilities
    if any(clip.media_kind == MediaKind.video for clip in clips) and not capabilities.ffmpeg:
        raise WorkspaceDependencyError("keyframes requires ffmpeg for video clips")

    try:
        keyframes, warnings = build_keyframes(
            root=root,
            clips=clips,
            clips_fingerprint=clips_fingerprint,
        )
    except KeyframeExtractionError as exc:
        raise WorkspaceDependencyError(f"keyframe extraction failed: {exc}") from exc

    run_id = new_run_id()
    output_dir = root / config.paths.output_dir
    output_path = write_keyframes_jsonl(root, keyframes)
    analysis_input_fingerprint = fingerprint_inputs(
        [
            ("clips", clips_path),
            ("transcripts", root / WORKSPACE_DIR / DATA_DIR / "transcripts.jsonl"),
            ("keyframes", output_path),
        ]
    )
    invalidated_steps = invalidate_downstream_steps_for_analysis_input(
        state,
        input_fingerprint=analysis_input_fingerprint,
        reason="keyframe ledger changed",
    )
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    state.steps["keyframes"] = StepLedgerEntry(
        status=status,
        input_fingerprint=clips_fingerprint,
        output_refs=[output_path.relative_to(root).as_posix()],
        last_run_id=run_id,
        warnings=warnings,
    )
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready

    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(runs_dir / "command.json", {"command": "keyframes", "project": str(project_path)})
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "keyframes",
            "status": status.value,
            "clips": len(clips),
            "keyframes": len(keyframes),
            "output_refs": state.steps["keyframes"].output_refs,
            "invalidated_steps": invalidated_steps,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text("keyframes completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(output_dir, state, warnings)
    return output_path, state, warnings


def analyze_workspace(project_path: Path) -> tuple[Path, Path, ProjectState, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("analyze requires init to complete first")

    sources_path = root / WORKSPACE_DIR / DATA_DIR / "sources.jsonl"
    clips_path = root / WORKSPACE_DIR / DATA_DIR / "clips.jsonl"
    if not sources_path.exists():
        raise WorkspacePrerequisiteError("analyze requires scan to complete first")
    if not clips_path.exists():
        raise WorkspacePrerequisiteError("analyze requires segment to complete first")

    sources = read_sources_jsonl(sources_path)
    clips = read_clips_jsonl(clips_path)
    transcripts_path = root / WORKSPACE_DIR / DATA_DIR / "transcripts.jsonl"
    keyframes_path = root / WORKSPACE_DIR / DATA_DIR / "keyframes.jsonl"
    transcripts = read_transcripts_jsonl(transcripts_path) if transcripts_path.exists() else []
    keyframes = read_keyframes_jsonl(keyframes_path) if keyframes_path.exists() else []
    clip_fingerprint = fingerprint_file(clips_path)
    analysis_fingerprint = fingerprint_inputs(
        [
            ("clips", clips_path),
            ("transcripts", transcripts_path),
            ("keyframes", keyframes_path),
        ]
    )
    analyses, warnings = build_analysis(
        clips=clips,
        sources=sources,
        transcripts=transcripts,
        keyframes=keyframes,
        clip_fingerprint=clip_fingerprint,
        analysis_fingerprint=analysis_fingerprint,
    )
    run_id = new_run_id()
    output_dir = root / config.paths.output_dir
    output_path = write_analysis_jsonl(root, analyses)
    report_path = output_dir / "analysis_report.md"
    atomic_write_text(
        report_path,
        render_analysis_report(
            analyses=analyses,
            analysis_ref=output_path.relative_to(root).as_posix(),
            clips_ref=clips_path.relative_to(root).as_posix(),
            transcripts_ref=transcripts_path.relative_to(root).as_posix()
            if transcripts_path.exists()
            else None,
            keyframes_ref=keyframes_path.relative_to(root).as_posix()
            if keyframes_path.exists()
            else None,
            warnings=warnings,
        ),
    )
    invalidated_steps = invalidate_downstream_steps_for_analysis(
        state,
        analysis_fingerprint=fingerprint_file(output_path),
    )

    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    state.steps["analyze"] = StepLedgerEntry(
        status=status,
        input_fingerprint=analysis_fingerprint,
        output_refs=[
            output_path.relative_to(root).as_posix(),
            report_path.relative_to(root).as_posix(),
        ],
        last_run_id=run_id,
        warnings=warnings,
    )
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready

    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(runs_dir / "command.json", {"command": "analyze", "project": str(project_path)})
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "analyze",
            "status": status.value,
            "clips": len(clips),
            "analysis_records": len(analyses),
            "transcripts": len(transcripts),
            "keyframes": len(keyframes),
            "output_refs": state.steps["analyze"].output_refs,
            "invalidated_steps": invalidated_steps,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text("analyze completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(output_dir, state, warnings)
    return output_path, report_path, state, warnings


def render_analysis_report(
    *,
    analyses: list[AnalysisRecord],
    analysis_ref: str,
    clips_ref: str,
    transcripts_ref: str | None,
    keyframes_ref: str | None,
    warnings: list[str],
) -> str:
    media_counts = count_by_value(analysis.media_kind.value for analysis in analyses)
    risk_counts = count_by_value(
        flag.value
        for analysis in analyses
        for flag in analysis.risk_flags
    )
    audio_counts = count_by_value(
        str(analysis.original_audio_usability.value) for analysis in analyses
    )
    warning_lines = "\n".join(f"- {warning}" for warning in warnings) or "- None"
    return (
        "# Analysis Report\n\n"
        "This V0-008 report is rendered from local source, clip, transcript, and "
        "keyframe ledgers. It records deterministic and context-derived evidence "
        "only. Shot size, camera motion, emotion, action, and visual quality remain "
        "`null` or empty candidates until a later visual-analysis gate opens. No "
        "OpenCV analysis, embeddings, creative proposals, timeline generation, "
        "preview rendering, network calls, BGM selection, image generation/editing, "
        "or model calls were performed.\n\n"
        "## Inputs\n\n"
        f"- Analysis ledger: `{analysis_ref}`\n"
        f"- Clip ledger: `{clips_ref}`\n"
        f"- Transcript ledger: `{transcripts_ref or 'missing'}`\n"
        f"- Keyframe ledger: `{keyframes_ref or 'missing'}`\n\n"
        "## Summary\n\n"
        f"- Analysis record count: `{len(analyses)}`\n\n"
        "### Media Kind\n\n"
        f"{render_count_lines(media_counts)}"
        "### Original Audio Usability\n\n"
        f"{render_count_lines(audio_counts)}"
        "### Risk Flags\n\n"
        f"{render_count_lines(risk_counts)}"
        "## Warnings\n\n"
        f"{warning_lines}\n\n"
        "## Records\n\n"
        f"{render_analysis_sections(analyses)}"
    )


def render_analysis_sections(analyses: list[AnalysisRecord]) -> str:
    if not analyses:
        return "No analysis records were generated.\n"
    sections = []
    for index, analysis in enumerate(
        sorted(analyses, key=lambda item: (item.source_location, item.start_seconds)),
        start=1,
    ):
        risks = ", ".join(f"`{flag.value}`" for flag in analysis.risk_flags) or "None"
        transcript_refs = ", ".join(f"`{ref}`" for ref in analysis.transcript_refs) or "None"
        keyframe_refs = ", ".join(f"`{ref}`" for ref in analysis.keyframe_refs) or "None"
        sections.append(
            f"### {index}. `{analysis.analysis_id}`\n\n"
            f"- Clip ID: `{analysis.clip_id}`\n"
            f"- Source location: `{analysis.source_location}`\n"
            f"- Start seconds: `{analysis.start_seconds:.3f}`\n"
            f"- End seconds: `{analysis.end_seconds:.3f}`\n"
            f"- Media kind: `{analysis.media_kind.value}`\n"
            f"- Material type: `{analysis.material_type.value}` "
            f"(method `{analysis.material_type.method}`, "
            f"confidence `{analysis.material_type.confidence:.3f}`)\n"
            f"- Original audio usability: `{analysis.original_audio_usability.value}` "
            f"(confidence `{analysis.original_audio_usability.confidence:.3f}`)\n"
            f"- Transcript refs: {transcript_refs}\n"
            f"- Keyframe refs: {keyframe_refs}\n"
            f"- Risk flags: {risks}\n"
        )
    return "\n".join(sections)


def map_workspace(project_path: Path) -> tuple[Path, ProjectState, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("map requires init to complete first")

    sources_path = root / WORKSPACE_DIR / DATA_DIR / "sources.jsonl"
    if not sources_path.exists():
        raise WorkspacePrerequisiteError("map requires scan to complete first")
    records = read_sources_jsonl(sources_path)
    analysis_path = root / WORKSPACE_DIR / DATA_DIR / "analysis.jsonl"
    if not analysis_path.exists():
        raise WorkspacePrerequisiteError("map requires analyze to complete first")
    analyze_step = state.steps.get("analyze", StepLedgerEntry())
    if analyze_step.status in {StepStatus.pending, StepStatus.invalidated}:
        raise WorkspacePrerequisiteError("map requires analyze to be current first")

    analyses = read_analysis_jsonl(analysis_path)
    warnings = ["no analysis records available for material map"] if not analyses else []
    run_id = new_run_id()
    output_dir = root / config.paths.output_dir
    output_path = output_dir / "material_map.md"
    atomic_write_text(
        output_path,
        render_material_map(
            records=records,
            analyses=analyses,
            sources_ref=sources_path.relative_to(root).as_posix(),
            analysis_ref=analysis_path.relative_to(root).as_posix(),
        ),
    )

    input_fingerprint = fingerprint_inputs(
        [
            ("sources", sources_path),
            ("analysis", analysis_path),
        ]
    )
    invalidated_steps = invalidate_downstream_steps_for_map(
        state,
        map_fingerprint=fingerprint_file(output_path),
    )
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    state.steps["map"] = StepLedgerEntry(
        status=status,
        input_fingerprint=input_fingerprint,
        output_refs=[output_path.relative_to(root).as_posix()],
        last_run_id=run_id,
        warnings=warnings,
    )
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready

    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(runs_dir / "command.json", {"command": "map", "project": str(project_path)})
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "map",
            "status": status.value,
            "sources": len(records),
            "analysis_records": len(analyses),
            "output": output_path.relative_to(root).as_posix(),
            "invalidated_steps": invalidated_steps,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text("map completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(output_dir, state, warnings)
    return output_path, state, warnings


def propose_workspace(project_path: Path) -> ProjectState:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("propose requires init to complete first")

    material_map_path = root / config.paths.output_dir / "material_map.md"
    if not material_map_path.exists():
        raise WorkspacePrerequisiteError("propose requires map to complete first")
    sources_path = root / WORKSPACE_DIR / DATA_DIR / "sources.jsonl"
    clips_path = root / WORKSPACE_DIR / DATA_DIR / "clips.jsonl"
    analysis_path = root / WORKSPACE_DIR / DATA_DIR / "analysis.jsonl"
    if not sources_path.exists():
        raise WorkspacePrerequisiteError("propose requires scan to complete first")
    if not clips_path.exists():
        raise WorkspacePrerequisiteError("propose requires segment to complete first")
    if not analysis_path.exists():
        raise WorkspacePrerequisiteError("propose requires analyze to complete first")
    map_step = state.steps.get("map", StepLedgerEntry())
    if map_step.status in {StepStatus.pending, StepStatus.invalidated}:
        raise WorkspacePrerequisiteError("propose requires map to be current first")

    sources = read_sources_jsonl(sources_path)
    clips = read_clips_jsonl(clips_path)
    analyses = read_analysis_jsonl(analysis_path)
    input_fingerprint = fingerprint_inputs(
        [
            ("sources", sources_path),
            ("clips", clips_path),
            ("analysis", analysis_path),
            ("material_map", material_map_path),
        ]
    )
    proposal_context = build_proposal_context(
        config=config,
        sources=sources,
        clips=clips,
        analyses=analyses,
        sources_ref=sources_path.relative_to(root).as_posix(),
        clips_ref=clips_path.relative_to(root).as_posix(),
        analysis_ref=analysis_path.relative_to(root).as_posix(),
        material_map_ref=material_map_path.relative_to(root).as_posix(),
        material_map_fingerprint=fingerprint_file(material_map_path),
        input_fingerprint=input_fingerprint,
    )
    context_path = write_proposal_context_json(root, proposal_context)
    context_ref = context_path.relative_to(root).as_posix()

    capabilities = detect_capabilities()
    state.capabilities = capabilities
    text_model_gate = build_text_model_gate(
        config=config,
        capabilities=capabilities,
        proposal_context_ref=context_ref,
        proposal_context_fingerprint=fingerprint_file(context_path),
    )
    gate_path = write_text_model_gate_json(root, text_model_gate)
    gate_ref = gate_path.relative_to(root).as_posix()
    run_id = new_run_id()
    warnings: list[str] = []
    output_dir = root / config.paths.output_dir
    if text_model_gate.status == TextModelGateStatus.blocked:
        warnings = [
            (
                "text_model_gate_blocked: "
                + ", ".join(text_model_gate.reasons)
                + "; fake proposals were not generated"
            )
        ]
        state.steps["propose"] = StepLedgerEntry(
            status=StepStatus.blocked,
            input_fingerprint=input_fingerprint,
            output_refs=[context_ref, gate_ref],
            last_run_id=run_id,
            warnings=warnings,
        )
        state.latest_run_id = run_id
        state.updated_at = utc_now()
        state.overall_status = OverallStatus.blocked
        runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
        runs_dir.mkdir(parents=True, exist_ok=True)
        write_json(runs_dir / "command.json", {"command": "propose", "project": str(project_path)})
        write_json(runs_dir / "environment.json", environment_snapshot())
        write_json(
            runs_dir / "step_result.json",
            {
                "step": "propose",
                "status": StepStatus.blocked.value,
                "output_refs": [context_ref, gate_ref],
                "proposal_context": context_ref,
                "text_model_gate": gate_ref,
                "reasons": text_model_gate.reasons,
                "reason": "text_model_gate_blocked",
            },
        )
        write_json(runs_dir / "warnings.json", warnings)
        write_json(runs_dir / "errors.json", text_model_gate.reasons)
        (runs_dir / "log.txt").write_text("propose blocked\n", encoding="utf-8")
        save_state(root, state)
        write_run_report(output_dir, state, warnings)
        raise WorkspaceDependencyError(
            "propose requires an approved text model gate; no fake proposals were generated"
        )

    warnings = [
        "proposal_generation_not_implemented: text model gate is ready but generation remains closed"
    ]
    state.steps["propose"] = StepLedgerEntry(
        status=StepStatus.blocked,
        input_fingerprint=input_fingerprint,
        output_refs=[context_ref, gate_ref],
        last_run_id=run_id,
        warnings=warnings,
    )
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    state.overall_status = OverallStatus.blocked
    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(runs_dir / "command.json", {"command": "propose", "project": str(project_path)})
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "propose",
            "status": StepStatus.blocked.value,
            "output_refs": [context_ref, gate_ref],
            "proposal_context": context_ref,
            "text_model_gate": gate_ref,
            "reason": "proposal_generation_not_implemented",
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", ["proposal_generation_not_implemented"])
    (runs_dir / "log.txt").write_text("propose blocked\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(output_dir, state, warnings)
    raise WorkspaceDependencyError(
        "proposal context was prepared, but generation is not implemented until the text-model proposal gate opens"
    )


def render_material_map(
    *,
    records: list[SourceRecord],
    analyses: list[AnalysisRecord],
    sources_ref: str,
    analysis_ref: str,
) -> str:
    sorted_records = sorted(records, key=lambda record: record.primary_location)
    sorted_analyses = sorted(analyses, key=lambda item: (item.source_location, item.start_seconds))
    total_duration = sum(record.media_probe.duration for record in sorted_records)
    media_counts = count_by_value(record.media_kind.value for record in sorted_records)
    source_type_counts = count_by_value(
        str(record.source_type.value) for record in sorted_records
    )
    rights_counts = count_by_value(str(record.rights_status.value) for record in sorted_records)
    analysis_material_counts = count_by_value(
        str(analysis.material_type.value) for analysis in sorted_analyses
    )
    audio_counts = count_by_value(
        str(analysis.original_audio_usability.value) for analysis in sorted_analyses
    )
    risk_counts = count_by_value(
        flag.value
        for analysis in sorted_analyses
        for flag in analysis.risk_flags
    )

    return (
        "# Material Map\n\n"
        "This deterministic material map is rendered from local source and analysis "
        "ledgers. It ranks clips for human review using evidence coverage and risk "
        "signals only. It does not perform OpenCV/vision-model visual classification, "
        "embeddings, creative proposals, timeline generation, preview rendering, "
        "network calls, BGM selection, image generation/editing, or model calls.\n\n"
        "## Summary\n\n"
        f"- Source ledger: `{sources_ref}`\n"
        f"- Analysis ledger: `{analysis_ref}`\n"
        f"- Source count: `{len(sorted_records)}`\n"
        f"- Analysis record count: `{len(sorted_analyses)}`\n"
        f"- Total duration seconds: `{total_duration:.3f}`\n\n"
        "## Distribution\n\n"
        "### Media Kind\n\n"
        f"{render_count_lines(media_counts)}\n"
        "### Source Type\n\n"
        f"{render_count_lines(source_type_counts)}\n"
        "### Analysis Material Type\n\n"
        f"{render_count_lines(analysis_material_counts)}\n"
        "### Original Audio Usability\n\n"
        f"{render_count_lines(audio_counts)}\n"
        "### Rights Status\n\n"
        f"{render_count_lines(rights_counts)}\n"
        "### Risk Flags\n\n"
        f"{render_count_lines(risk_counts)}\n"
        "## Priority Review Queue\n\n"
        f"{render_priority_review_queue(sorted_analyses)}"
        "## Pending Confirmation\n\n"
        f"{render_pending_confirmation(sorted_analyses)}"
        "## Risk Items\n\n"
        f"{render_material_map_risks(sorted_analyses)}"
        "## Sources\n\n"
        f"{render_source_sections(sorted_records)}"
    )


def analysis_review_score(analysis: AnalysisRecord) -> float:
    score = analysis.duration_seconds
    if analysis.keyframe_refs:
        score += 2.0
    if analysis.transcript_refs:
        score += 2.0
    score -= len(analysis.risk_flags) * 0.5
    return round(max(score, 0.0), 3)


def render_priority_review_queue(analyses: list[AnalysisRecord]) -> str:
    if not analyses:
        return "No analysis records are available for review prioritization.\n\n"
    ranked = sorted(
        analyses,
        key=lambda analysis: (
            -analysis_review_score(analysis),
            analysis.source_location,
            analysis.start_seconds,
        ),
    )
    lines = []
    for index, analysis in enumerate(ranked, start=1):
        reasons = []
        if analysis.keyframe_refs:
            reasons.append("has keyframe evidence")
        if analysis.transcript_refs:
            reasons.append("has transcript evidence")
        if not reasons:
            reasons.append("needs manual evidence review")
        risk_count = len(analysis.risk_flags)
        lines.append(
            f"{index}. `{analysis.clip_id}` score `{analysis_review_score(analysis):.3f}` - "
            f"{analysis.source_location} "
            f"{analysis.start_seconds:.3f}-{analysis.end_seconds:.3f}s; "
            f"{', '.join(reasons)}; risks `{risk_count}`"
        )
    return "\n".join(lines) + "\n\n"


def render_pending_confirmation(analyses: list[AnalysisRecord]) -> str:
    if not analyses:
        return "- None\n\n"
    lines = []
    for analysis in analyses:
        pending = []
        if analysis.shot_size.value is None:
            pending.append("shot_size")
        if analysis.camera_motion.value is None:
            pending.append("camera_motion")
        if analysis.visual_quality.value is None:
            pending.append("visual_quality")
        if not analysis.emotion_candidates.value:
            pending.append("emotion_candidates")
        if not analysis.action_candidates.value:
            pending.append("action_candidates")
        if pending:
            lines.append(
                f"- `{analysis.clip_id}` requires confirmation for "
                f"{', '.join(pending)}"
            )
    return ("\n".join(lines) if lines else "- None") + "\n\n"


def render_material_map_risks(analyses: list[AnalysisRecord]) -> str:
    rows = []
    for analysis in analyses:
        if not analysis.risk_flags:
            continue
        risks = ", ".join(f"`{flag.value}`" for flag in analysis.risk_flags)
        rows.append(f"- `{analysis.clip_id}`: {risks}")
    return ("\n".join(rows) if rows else "- None") + "\n\n"


def count_by_value(values) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def render_count_lines(counts: dict[str, int]) -> str:
    if not counts:
        return "- None\n\n"
    return "".join(f"- `{key}`: {value}\n" for key, value in counts.items()) + "\n"


def render_source_sections(records: list[SourceRecord]) -> str:
    if not records:
        return "No sources were found in the current scan ledger.\n"
    sections = []
    for index, record in enumerate(records, start=1):
        sections.append(render_source_section(index, record))
    return "\n".join(sections)


def render_source_section(index: int, record: SourceRecord) -> str:
    probe = record.media_probe
    dimensions = f"{probe.width}x{probe.height}" if probe.width and probe.height else "n/a"
    frame_rate = f"{probe.frame_rate:.3f}" if probe.frame_rate else "n/a"
    supersedes = f"`{record.supersedes_source_id}`" if record.supersedes_source_id else "None"
    risk_flags = ", ".join(f"`{flag.value}`" for flag in record.risk_flags) or "None"
    locations = "".join(f"  - `{location}`\n" for location in record.locations)
    notes = record.notes or "None"
    return (
        f"### {index}. `{record.primary_location}`\n\n"
        f"- Source ID: `{record.source_id}`\n"
        f"- Media kind: `{record.media_kind.value}`\n"
        f"- Duration seconds: `{probe.duration:.3f}`\n"
        f"- Dimensions: `{dimensions}`\n"
        f"- Frame rate: `{frame_rate}`\n"
        f"- Video codec: `{probe.video_codec or 'n/a'}`\n"
        f"- Audio present: `{str(probe.audio_present).lower()}`\n"
        f"- Audio codec: `{probe.audio_codec or 'n/a'}`\n"
        f"- Source type: `{record.source_type.value}` "
        f"(method `{record.source_type.method}`, confidence `{record.source_type.confidence:.3f}`)\n"
        f"- Rights status: `{record.rights_status.value}` "
        f"(method `{record.rights_status.method}`, confidence `{record.rights_status.confidence:.3f}`)\n"
        f"- Provenance confidence: `{record.provenance_confidence:.3f}`\n"
        f"- Forbidden by user: `{str(record.forbidden_by_user).lower()}`\n"
        f"- Supersedes source ID: {supersedes}\n"
        f"- Risk flags: {risk_flags}\n"
        f"- Notes: {notes}\n"
        "- Locations:\n"
        f"{locations}"
    )


def review_project_workspace(
    project_path: Path,
    *,
    scope: str = "project",
) -> tuple[Path, ProjectState, list[str], list[dict[str, str]]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("review requires init to complete first")

    sources_path = root / WORKSPACE_DIR / DATA_DIR / "sources.jsonl"
    if not sources_path.exists():
        raise WorkspacePrerequisiteError(
            "review --scope project requires scan to complete first"
        )

    records = read_sources_jsonl(sources_path)
    issues = review_source_risks(
        records,
        allow_restricted_rights=config.content_policy.allow_restricted_rights,
    )
    issues.extend(ledger_output_ref_issues(root, state))
    issues.extend(
        issue
        for issue in invalidated_step_issues(project_path, state)
        if issue.get("code") != "review_project_invalidated"
    )
    if scope == "all":
        issues.extend(review_all_scope_issues())
    warnings = [f"{len(issues)} project review issue(s) found"] if issues else []
    run_id = new_run_id()
    output_dir = root / config.paths.output_dir
    output_path = output_dir / "risk_report.md"
    atomic_write_text(
        output_path,
        render_risk_report(
            records=records,
            issues=issues,
            sources_ref=sources_path.relative_to(root).as_posix(),
        ),
    )

    input_fingerprint = fingerprint_file(sources_path)
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    state.steps["review_project"] = StepLedgerEntry(
        status=status,
        input_fingerprint=input_fingerprint,
        output_refs=[output_path.relative_to(root).as_posix()],
        last_run_id=run_id,
        warnings=warnings,
    )
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready

    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        runs_dir / "command.json",
        {"command": "review", "scope": scope, "project": str(project_path)},
    )
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "review_project",
            "status": status.value,
            "sources": len(records),
            "issues": len(issues),
            "output": output_path.relative_to(root).as_posix(),
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text("review project completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(output_dir, state, warnings)
    return output_path, state, warnings, issues


def review_all_scope_issues() -> list[dict[str, str]]:
    return [
        review_scope_issue(
            scope="proposal",
            detail="proposal review is not implemented in the current local foundation gate",
        ),
        review_scope_issue(
            scope="timeline",
            detail="timeline review is not implemented in the current local foundation gate",
        ),
    ]


def review_source_risks(
    records: list[SourceRecord],
    *,
    allow_restricted_rights: bool,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for record in sorted(records, key=lambda item: item.primary_location):
        if record.provenance_confidence < 0.7:
            issues.append(
                risk_issue(
                    source=record,
                    code="low_provenance_confidence",
                    severity="warning",
                    detail=(
                        "provenance_confidence is below 0.7; do not use this source "
                        "as a confirmed factual basis without user confirmation"
                    ),
                )
            )
        if record.rights_status.value == RightsStatus.permission_unknown:
            issues.append(
                risk_issue(
                    source=record,
                    code="rights_unknown",
                    severity="warning",
                    detail="rights_status is permission_unknown",
                )
            )
        if record.rights_status.value == RightsStatus.restricted and not allow_restricted_rights:
            issues.append(
                risk_issue(
                    source=record,
                    code="rights_restricted",
                    severity="error",
                    detail="rights_status is restricted and project policy does not allow restricted rights",
                )
            )
        if record.forbidden_by_user:
            issues.append(
                risk_issue(
                    source=record,
                    code="forbidden_by_user",
                    severity="error",
                    detail="source is marked forbidden_by_user and must not enter proposals, timelines, or previews",
                )
            )
    return issues


def risk_issue(
    *,
    source: SourceRecord,
    code: str,
    severity: str,
    detail: str,
) -> dict[str, str]:
    return {
        "scope": "source",
        "source_id": source.source_id,
        "location": source.primary_location,
        "code": code,
        "severity": severity,
        "detail": detail,
    }


def artifact_issue(
    *,
    step: str,
    ref: str,
    code: str,
    severity: str,
    detail: str,
) -> dict[str, str]:
    next_action = rebuild_command_for_step(step)
    return {
        "scope": "artifact",
        "step": step,
        "ref": ref,
        "location": ref,
        "code": code,
        "severity": severity,
        "detail": detail,
        "next_action": next_action,
    }


def review_scope_issue(*, scope: str, detail: str) -> dict[str, str]:
    return {
        "scope": "review_scope",
        "review_scope": scope,
        "code": "review_scope_skipped",
        "severity": "warning",
        "detail": detail,
    }


def workspace_issue(
    *,
    code: str,
    severity: str,
    detail: str,
    next_action: str,
) -> dict[str, str]:
    return {
        "scope": "workspace",
        "code": code,
        "severity": severity,
        "detail": detail,
        "next_action": next_action,
    }


def rebuild_command_for_step(step: str) -> str:
    commands = {
        "init": "artist-portrait init --project <project.yaml>",
        "scan": "artist-portrait scan --project <project.yaml>",
        "transcribe": "artist-portrait transcribe --project <project.yaml>",
        "segment": "artist-portrait segment --project <project.yaml>",
        "keyframes": "artist-portrait keyframes --project <project.yaml>",
        "analyze": "artist-portrait analyze --project <project.yaml>",
        "map": "artist-portrait map --project <project.yaml>",
        "propose": "artist-portrait propose --project <project.yaml>",
        "review_project": "artist-portrait review --project <project.yaml> --scope project",
    }
    return commands.get(step, "rerun the command that produced this output")


def render_risk_report(
    *,
    records: list[SourceRecord],
    issues: list[dict[str, str]],
    sources_ref: str,
) -> str:
    severity_counts = count_by_value(issue["severity"] for issue in issues)
    code_counts = count_by_value(issue["code"] for issue in issues)
    return (
        "# Risk Report\n\n"
        "This deterministic project review is rendered from local scan data only. "
        "No transcription, visual analysis, embeddings, creative proposals, timeline "
        "generation, preview rendering, network calls, or model calls were performed.\n\n"
        "## Summary\n\n"
        f"- Source ledger: `{sources_ref}`\n"
        f"- Source count: `{len(records)}`\n"
        f"- Issue count: `{len(issues)}`\n\n"
        "## Severity Counts\n\n"
        f"{render_count_lines(severity_counts)}"
        "## Issue Counts\n\n"
        f"{render_count_lines(code_counts)}"
        "## Issues\n\n"
        f"{render_issue_sections(issues)}"
    )


def render_issue_sections(issues: list[dict[str, str]]) -> str:
    if not issues:
        return "No project review issues were found in the current scan ledger.\n"
    sections = []
    for index, issue in enumerate(issues, start=1):
        optional_lines = ""
        if issue.get("source_id"):
            optional_lines += f"- Source ID: `{issue['source_id']}`\n"
        if issue.get("step"):
            optional_lines += f"- Step: `{issue['step']}`\n"
        if issue.get("review_scope"):
            optional_lines += f"- Review scope: `{issue['review_scope']}`\n"
        if issue.get("location"):
            optional_lines += f"- Location: `{issue['location']}`\n"
        if issue.get("ref"):
            optional_lines += f"- Output ref: `{issue['ref']}`\n"
        if issue.get("next_action"):
            optional_lines += f"- Next action: `{issue['next_action']}`\n"
        sections.append(
            f"### {index}. `{issue['code']}`\n\n"
            f"- Severity: `{issue['severity']}`\n"
            f"- Scope: `{issue.get('scope', 'source')}`\n"
            f"{optional_lines}"
            f"- Detail: {issue['detail']}\n"
        )
    return "\n".join(sections)
