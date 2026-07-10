from __future__ import annotations

import json
from pathlib import Path

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.state import (
    ActiveMode,
    OverallStatus,
    ProjectState,
    StepLedgerEntry,
    StepStatus,
)
from artist_portrait_editor.preview import (
    PreviewError,
    render_preview,
    render_preview_review,
    review_preview,
)
from artist_portrait_editor.run_records import (
    environment_snapshot,
    new_run_id,
    utc_now,
    write_json,
)
from artist_portrait_editor.workspace_errors import (
    WorkspacePrerequisiteError,
    WorkspacePreviewError,
)
from artist_portrait_editor.workspace_state import (
    atomic_write_text,
    fingerprint_inputs,
    load_state,
    project_root,
    save_state,
    write_run_report,
)


def preview_workspace(
    project_path: Path,
    *,
    width: int = 480,
    fps: int = 12,
) -> tuple[Path, Path, Path, Path, ProjectState, list[str], list[dict]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("preview requires init to complete first")
    timeline_step = state.steps.get("timeline", StepLedgerEntry())
    if timeline_step.status not in {
        StepStatus.completed,
        StepStatus.completed_with_warnings,
    }:
        raise WorkspacePrerequisiteError("preview requires a current timeline first")
    timeline_path = root / config.paths.output_dir / "timeline_draft.json"
    if not timeline_path.exists():
        raise WorkspacePrerequisiteError("preview requires output/timeline_draft.json")
    try:
        preview_path, manifest_path, validation_path, manifest, validation = render_preview(
            root=root,
            project_id=config.project.id,
            width=width,
            fps=fps,
        )
    except PreviewError as exc:
        raise WorkspacePreviewError(str(exc)) from exc
    review_path = root / config.paths.output_dir / "preview_review.md"
    atomic_write_text(review_path, render_preview_review(validation))
    warnings = list(manifest.warnings)
    warnings.extend(issue.detail for issue in validation.issues if issue.severity == "warning")
    warnings = list(dict.fromkeys(warnings))
    run_id = new_run_id()
    input_fingerprint = fingerprint_inputs(
        [
            ("timeline", timeline_path),
            ("bgm_fit", root / WORKSPACE_DIR / DATA_DIR / "bgm_fit.json"),
        ]
    )
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    output_refs = [
        preview_path.relative_to(root).as_posix(),
        manifest_path.relative_to(root).as_posix(),
        validation_path.relative_to(root).as_posix(),
        review_path.relative_to(root).as_posix(),
    ]
    state.steps["preview"] = StepLedgerEntry(
        status=status,
        input_fingerprint=input_fingerprint,
        output_refs=output_refs,
        last_run_id=run_id,
        warnings=warnings,
    )
    state.steps["review_preview"] = StepLedgerEntry(
        status=status,
        input_fingerprint=input_fingerprint,
        output_refs=[
            validation_path.relative_to(root).as_posix(),
            review_path.relative_to(root).as_posix(),
        ],
        last_run_id=run_id,
        warnings=warnings,
    )
    state.active_mode = ActiveMode.creative
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready
    _write_preview_run(
        root=root,
        run_id=run_id,
        project_path=project_path,
        status=status,
        preview_ref=preview_path.relative_to(root).as_posix(),
        manifest_ref=manifest_path.relative_to(root).as_posix(),
        validation_ref=validation_path.relative_to(root).as_posix(),
        output_refs=output_refs,
        bgm_included=manifest.bgm_included,
        ducking_applied=manifest.ducking_applied,
        requested_width=manifest.requested_width,
        requested_fps=manifest.requested_fps,
        warnings=warnings,
        errors=[issue.code for issue in validation.issues if issue.severity == "error"],
    )
    save_state(root, state)
    write_run_report(root / config.paths.output_dir, state, warnings)
    return (
        preview_path,
        manifest_path,
        validation_path,
        review_path,
        state,
        warnings,
        [issue.model_dump(mode="json") for issue in validation.issues],
    )


def review_preview_workspace(
    project_path: Path,
) -> tuple[Path, Path, ProjectState, list[str], list[dict]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("review --scope preview requires init to complete first")
    manifest_path = root / WORKSPACE_DIR / DATA_DIR / "preview_manifest.json"
    if not manifest_path.exists():
        raise WorkspacePrerequisiteError("review --scope preview requires preview first")
    validation = review_preview(root)
    validation_path = root / WORKSPACE_DIR / DATA_DIR / "preview_validation.json"
    atomic_write_text(
        validation_path,
        json.dumps(
            validation.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    report_path = root / config.paths.output_dir / "preview_review.md"
    atomic_write_text(report_path, render_preview_review(validation))
    warnings = [f"{validation.issue_count} preview issue(s) found"] if validation.issue_count else []
    run_id = new_run_id()
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    input_fingerprint = fingerprint_inputs(
        [
            ("manifest", manifest_path),
            ("timeline", root / config.paths.output_dir / "timeline_draft.json"),
            ("bgm_fit", root / WORKSPACE_DIR / DATA_DIR / "bgm_fit.json"),
        ]
    )
    state.steps["review_preview"] = StepLedgerEntry(
        status=status,
        input_fingerprint=input_fingerprint,
        output_refs=[
            validation_path.relative_to(root).as_posix(),
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
    write_json(
        runs_dir / "command.json",
        {"command": "review", "scope": "preview", "project": str(project_path)},
    )
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "review_preview",
            "status": status.value,
            "issues": validation.issue_count,
            "errors": validation.error_count,
            "warnings": validation.warning_count,
            "output_refs": state.steps["review_preview"].output_refs,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(
        runs_dir / "errors.json",
        [issue.code for issue in validation.issues if issue.severity == "error"],
    )
    (runs_dir / "log.txt").write_text("review preview completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(root / config.paths.output_dir, state, warnings)
    return (
        validation_path,
        report_path,
        state,
        warnings,
        [issue.model_dump(mode="json") for issue in validation.issues],
    )


def _write_preview_run(
    *,
    root: Path,
    run_id: str,
    project_path: Path,
    status: StepStatus,
    preview_ref: str,
    manifest_ref: str,
    validation_ref: str,
    output_refs: list[str],
    bgm_included: bool,
    ducking_applied: bool,
    requested_width: int,
    requested_fps: int,
    warnings: list[str],
    errors: list[str],
) -> None:
    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(runs_dir / "command.json", {"command": "preview", "project": str(project_path)})
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "preview",
            "status": status.value,
            "preview_ref": preview_ref,
            "manifest_ref": manifest_ref,
            "validation_ref": validation_ref,
            "bgm_included": bgm_included,
            "ducking_applied": ducking_applied,
            "requested_width": requested_width,
            "requested_fps": requested_fps,
            "final_export": False,
            "network_performed": False,
            "model_call_performed": False,
            "output_refs": output_refs,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", errors)
    (runs_dir / "log.txt").write_text("preview completed\n", encoding="utf-8")
