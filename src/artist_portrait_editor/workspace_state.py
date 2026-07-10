from __future__ import annotations

import hashlib
import json
from pathlib import Path

from artist_portrait_editor.capabilities import capability_warnings, detect_capabilities
from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import CACHE_DIR, DATA_DIR, RUNS_DIR, WORKSPACE_DIR
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
    return atomic_write_text(output_dir / "run_report.md", render_run_report(state, warnings))


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
        "brief",
        "score",
        "propose",
        "timeline",
        "review_timeline",
        "bgm_import",
        "bgm_analyze",
        "bgm_fit",
        "preview",
        "review_preview",
        "final_export",
        "review_final_export",
        "review_bgm",
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
