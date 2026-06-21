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
from artist_portrait_editor.models.source import RightsStatus, SourceRecord
from artist_portrait_editor.run_records import (
    environment_snapshot,
    new_run_id,
    utc_now,
    write_json,
)


class WorkspacePrerequisiteError(Exception):
    pass


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
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "material_map.md"
    output_path.write_text(
        render_material_map(records=records, sources_ref=sources_path.relative_to(root).as_posix()),
        encoding="utf-8",
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
    warnings = [
        f"{len(issues)} project risk issue(s) found",
    ] if issues else []
    run_id = new_run_id()
    output_dir = root / config.paths.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "risk_report.md"
    output_path.write_text(
        render_risk_report(
            records=records,
            issues=issues,
            sources_ref=sources_path.relative_to(root).as_posix(),
        ),
        encoding="utf-8",
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
        {"command": "review", "scope": "project", "project": str(project_path)},
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
    return output_path, state, warnings, issues


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
        "source_id": source.source_id,
        "location": source.primary_location,
        "code": code,
        "severity": severity,
        "detail": detail,
    }


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
        return "No project risk issues were found in the current scan ledger.\n"
    sections = []
    for index, issue in enumerate(issues, start=1):
        sections.append(
            f"### {index}. `{issue['code']}`\n\n"
            f"- Severity: `{issue['severity']}`\n"
            f"- Source ID: `{issue['source_id']}`\n"
            f"- Location: `{issue['location']}`\n"
            f"- Detail: {issue['detail']}\n"
        )
    return "\n".join(sections)
