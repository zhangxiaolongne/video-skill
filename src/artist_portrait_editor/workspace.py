from __future__ import annotations

import hashlib
import json
from pathlib import Path

from artist_portrait_editor.capabilities import capability_warnings, detect_capabilities
from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import CACHE_DIR, DATA_DIR, RUNS_DIR, WORKSPACE_DIR
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
from artist_portrait_editor.models.clip import (
    ClipBoundary,
    ClipMethod,
    ClipRecord,
    ClipRiskFlag,
)
from artist_portrait_editor.models.state import (
    Capabilities,
    OverallStatus,
    ProjectState,
    StepLedgerEntry,
    StepStatus,
    initial_steps,
)
from artist_portrait_editor.models.source import MediaKind, RightsStatus, SourceRecord
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


def invalidate_downstream_steps_for_sources(
    state: ProjectState,
    *,
    sources_fingerprint: str,
) -> list[str]:
    invalidated: list[str] = []
    for step_name in ("segment", "transcribe", "map", "review_project"):
        entry = state.steps.get(step_name)
        if entry is None:
            continue
        if entry.status not in {StepStatus.completed, StepStatus.completed_with_warnings}:
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
    risk = summaries.get("risk_report") or {}
    if risk.get("exists"):
        lines.append(f"risk_report: present ({risk.get('bytes', 0)} bytes)")
    scan_report = summaries.get("scan_report") or {}
    if scan_report.get("exists"):
        lines.append(f"scan_report: present ({scan_report.get('bytes', 0)} bytes)")
    clip_report = summaries.get("clip_report") or {}
    if clip_report.get("exists"):
        lines.append(f"clip_report: present ({clip_report.get('bytes', 0)} bytes)")
    material_map = summaries.get("material_map") or {}
    if material_map.get("exists"):
        lines.append(f"material_map: present ({material_map.get('bytes', 0)} bytes)")
    artifact_issues = payload.get("artifact_issues") or []
    if artifact_issues:
        lines.append(f"artifact_issues: {len(artifact_issues)}")
    steps = payload.get("steps") or {}
    for step in ("scan", "segment", "transcribe", "map", "review_project"):
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
    elif (
        sources.get("valid") is True
        and state.steps.get("map", StepLedgerEntry()).status == StepStatus.pending
    ):
        issues.append(
            workspace_issue(
                code="map_pending",
                severity="info",
                detail="source ledger exists but material map has not been generated",
                next_action=f"artist-portrait map --project {project_path}",
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
        "relations": root / WORKSPACE_DIR / DATA_DIR / "relations.jsonl",
        "proposals_json": root / WORKSPACE_DIR / DATA_DIR / "proposals.json",
        "run_report": root / "output" / "run_report.md",
        "scan_report": root / "output" / "scan_report.md",
        "clip_report": root / "output" / "clip_report.md",
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
    scan_report_path = root / "output" / "scan_report.md"
    clip_report_path = root / "output" / "clip_report.md"
    material_map_path = root / "output" / "material_map.md"
    risk_report_path = root / "output" / "risk_report.md"
    return {
        "sources": source_summary(sources_path),
        "clips": clip_summary(clips_path),
        "transcripts": transcript_summary(transcripts_path),
        "scan_report": output_summary(scan_report_path),
        "clip_report": output_summary(clip_report_path),
        "material_map": output_summary(material_map_path),
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
    for step_name in ("map", "review_project"):
        entry = state.steps.get(step_name)
        if entry is None:
            continue
        if entry.status not in {StepStatus.completed, StepStatus.completed_with_warnings}:
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
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text("transcribe completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(output_dir, state, warnings)
    return output_path, state, warnings


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
    warnings = ["no sources available for material map"] if not records else []
    run_id = new_run_id()
    output_dir = root / config.paths.output_dir
    output_path = output_dir / "material_map.md"
    atomic_write_text(
        output_path,
        render_material_map(records=records, sources_ref=sources_path.relative_to(root).as_posix()),
    )

    input_fingerprint = fingerprint_file(sources_path)
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
            "output": output_path.relative_to(root).as_posix(),
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text("map completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(output_dir, state, warnings)
    return output_path, state, warnings


def render_material_map(*, records: list[SourceRecord], sources_ref: str) -> str:
    sorted_records = sorted(records, key=lambda record: record.primary_location)
    total_duration = sum(record.media_probe.duration for record in sorted_records)
    media_counts = count_by_value(record.media_kind.value for record in sorted_records)
    source_type_counts = count_by_value(
        str(record.source_type.value) for record in sorted_records
    )
    rights_counts = count_by_value(str(record.rights_status.value) for record in sorted_records)

    return (
        "# Material Map\n\n"
        "This deterministic source inventory is rendered from local scan data only. "
        "No transcription, visual analysis, embeddings, creative proposals, timeline "
        "generation, preview rendering, network calls, or model calls were performed.\n\n"
        "## Summary\n\n"
        f"- Source ledger: `{sources_ref}`\n"
        f"- Source count: `{len(sorted_records)}`\n"
        f"- Total duration seconds: `{total_duration:.3f}`\n\n"
        "## Distribution\n\n"
        "### Media Kind\n\n"
        f"{render_count_lines(media_counts)}\n"
        "### Source Type\n\n"
        f"{render_count_lines(source_type_counts)}\n"
        "### Rights Status\n\n"
        f"{render_count_lines(rights_counts)}\n"
        "## Sources\n\n"
        f"{render_source_sections(sorted_records)}"
    )


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
        "map": "artist-portrait map --project <project.yaml>",
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
