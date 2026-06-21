from __future__ import annotations

import hashlib
import json
from pathlib import Path

from artist_portrait_editor.capabilities import capability_warnings, detect_capabilities
from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import CACHE_DIR, DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.media.scanner import (
    ScanResult,
    read_sources_jsonl,
    scan_project_sources,
    write_sources_jsonl,
)
from artist_portrait_editor.models.state import (
    OverallStatus,
    ProjectState,
    StepLedgerEntry,
    StepStatus,
    initial_steps,
)
from artist_portrait_editor.run_records import (
    environment_snapshot,
    new_run_id,
    utc_now,
    write_json,
)


def project_root(project_path: Path) -> Path:
    return project_path.resolve().parent


def fingerprint_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


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
    (output_dir / "run_report.md").write_text(render_run_report(state, warnings), encoding="utf-8")
    return state, warnings


def render_run_report(state: ProjectState, warnings: list[str]) -> str:
    warning_lines = "\n".join(f"- {warning}" for warning in warnings) or "- None"
    return (
        "# Run Report\n\n"
        f"- Project ID: `{state.project_id}`\n"
        f"- Run ID: `{state.latest_run_id}`\n"
        f"- Overall Status: `{state.overall_status.value}`\n"
        f"- Updated At: `{state.updated_at}`\n\n"
        "## Stage A\n\n"
        "No media scanning, transcription, visual analysis, proposals, or timeline "
        "generation was performed.\n\n"
        "## Warnings\n\n"
        f"{warning_lines}\n"
    )


def state_as_dict(state: ProjectState) -> dict:
    return json.loads(state.model_dump_json())


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
    if result.records or not result.errors:
        output_path = write_sources_jsonl(root, result.records)
        output_refs.append(output_path.relative_to(root).as_posix())

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
        },
    )
    write_json(runs_dir / "warnings.json", result.warnings)
    write_json(runs_dir / "errors.json", result.errors)
    (runs_dir / "log.txt").write_text("scan completed\n", encoding="utf-8")
    save_state(root, state)
    return result, state
