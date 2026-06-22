from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from artist_portrait_editor.capabilities import detect_capabilities
from artist_portrait_editor.config_loader import ConfigLoadError, load_project_config
from artist_portrait_editor.exit_codes import ExitCode
from artist_portrait_editor.media.scanner import ScanError, SourceLedgerError
from artist_portrait_editor.schemas import write_schema_files
from artist_portrait_editor.workspace import (
    WorkspaceDependencyError,
    WorkspacePrerequisiteError,
    analyze_workspace,
    doctor_project_payload,
    init_workspace,
    keyframes_workspace,
    load_state,
    map_workspace,
    propose_workspace,
    project_status_payload,
    project_root,
    render_doctor_panel,
    render_status_panel,
    review_project_workspace,
    scan_workspace,
    segment_workspace,
    state_as_dict,
    transcribe_workspace,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="artist-portrait")
    parser.add_argument("--version", action="store_true")
    subparsers = parser.add_subparsers(dest="command")

    for command in ("validate", "init", "status", "doctor"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--project", required=True)
        sub.add_argument("--json", action="store_true")
        sub.add_argument("--quiet", action="store_true")
        sub.add_argument("--verbose", action="store_true")
        if command == "init":
            sub.add_argument("--dry-run", action="store_true")

    schema_sub = subparsers.add_parser("generate-schema")
    schema_sub.add_argument("--output-dir", default="schemas")

    scan_sub = subparsers.add_parser("scan")
    scan_sub.add_argument("--project", required=True)
    scan_sub.add_argument("--json", action="store_true")
    scan_sub.add_argument("--quiet", action="store_true")
    scan_sub.add_argument("--verbose", action="store_true")

    segment_sub = subparsers.add_parser("segment")
    segment_sub.add_argument("--project", required=True)
    segment_sub.add_argument("--json", action="store_true")
    segment_sub.add_argument("--quiet", action="store_true")
    segment_sub.add_argument("--verbose", action="store_true")

    transcribe_sub = subparsers.add_parser("transcribe")
    transcribe_sub.add_argument("--project", required=True)
    transcribe_sub.add_argument("--json", action="store_true")
    transcribe_sub.add_argument("--quiet", action="store_true")
    transcribe_sub.add_argument("--verbose", action="store_true")

    keyframes_sub = subparsers.add_parser("keyframes")
    keyframes_sub.add_argument("--project", required=True)
    keyframes_sub.add_argument("--json", action="store_true")
    keyframes_sub.add_argument("--quiet", action="store_true")
    keyframes_sub.add_argument("--verbose", action="store_true")

    analyze_sub = subparsers.add_parser("analyze")
    analyze_sub.add_argument("--project", required=True)
    analyze_sub.add_argument("--json", action="store_true")
    analyze_sub.add_argument("--quiet", action="store_true")
    analyze_sub.add_argument("--verbose", action="store_true")

    map_sub = subparsers.add_parser("map")
    map_sub.add_argument("--project", required=True)
    map_sub.add_argument("--json", action="store_true")
    map_sub.add_argument("--quiet", action="store_true")
    map_sub.add_argument("--verbose", action="store_true")

    review_sub = subparsers.add_parser("review")
    review_sub.add_argument("--project", required=True)
    review_sub.add_argument(
        "--scope",
        default="project",
        choices=("project", "proposal", "timeline", "all"),
    )
    review_sub.add_argument("--json", action="store_true")
    review_sub.add_argument("--quiet", action="store_true")
    review_sub.add_argument("--verbose", action="store_true")

    propose_sub = subparsers.add_parser("propose")
    propose_sub.add_argument("--project", required=True)
    propose_sub.add_argument("--json", action="store_true")
    propose_sub.add_argument("--quiet", action="store_true")
    propose_sub.add_argument("--verbose", action="store_true")

    for command in ("relate", "timeline", "run"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--project", required=True)

    return parser


def _validate_common_flags(args: argparse.Namespace) -> int | None:
    if getattr(args, "quiet", False) and getattr(args, "verbose", False):
        print("--quiet and --verbose are mutually exclusive", file=sys.stderr)
        return ExitCode.invalid_arguments
    return None


def cmd_validate(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    try:
        config = load_project_config(Path(args.project))
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    if args.json:
        print(config.model_dump_json(indent=2))
    elif not args.quiet:
        print("valid")
    return int(ExitCode.success)


def cmd_init(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    try:
        state, warnings = init_workspace(Path(args.project), dry_run=args.dry_run)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    if args.json:
        print(json.dumps(state_as_dict(state), ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print("dry-run ok" if args.dry_run else "initialized")
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_status(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    payload = project_status_payload(project_path)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(render_status_panel(payload), end="")
    return int(ExitCode.success)


def cmd_doctor(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    payload = doctor_project_payload(project_path)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(render_doctor_panel(payload), end="")
    return int(
        ExitCode.success_with_warnings
        if payload.get("issue_count")
        else ExitCode.success
    )


def cmd_generate_schema(args: argparse.Namespace) -> int:
    write_schema_files(Path(args.output_dir))
    print(f"schemas written to {args.output_dir}")
    return int(ExitCode.success)


def cmd_scan(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    state = load_state(project_root(project_path))
    if state is None or state.steps.get("init") is None:
        print("scan requires init to complete first", file=sys.stderr)
        return int(ExitCode.prerequisite_step_missing)
    capabilities = detect_capabilities()
    missing = [
        name
        for name in ("ffmpeg", "ffprobe")
        if not getattr(capabilities, name)
    ]
    if missing:
        print(
            "missing required media dependencies for scan: " + ", ".join(missing),
            file=sys.stderr,
        )
        return int(ExitCode.missing_required_dependency_for_command)
    try:
        result, state = scan_workspace(project_path)
    except SourceLedgerError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    except ScanError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.media_operation_failed)
    payload = {
        "sources": len(result.records),
        "warnings": result.warnings,
        "errors": result.errors,
        "output_refs": state.steps["scan"].output_refs,
        "invalidated_steps": [
            name
            for name in (
                "segment",
                "transcribe",
                "keyframes",
                "analyze",
                "map",
                "propose",
                "review_project",
            )
            if state.steps.get(name) and state.steps[name].status.value == "invalidated"
        ],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"scanned {len(result.records)} source(s)")
        for warning in result.warnings:
            print(f"warning: {warning}", file=sys.stderr)
    if result.errors:
        return int(ExitCode.media_operation_failed)
    if result.warnings:
        return int(ExitCode.success_with_warnings)
    return int(ExitCode.success)


def cmd_segment(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    try:
        output_path, state, warnings = segment_workspace(project_path)
    except WorkspacePrerequisiteError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.prerequisite_step_missing)
    except WorkspaceDependencyError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.missing_required_dependency_for_command)
    except SourceLedgerError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    step = state.steps["segment"]
    payload = {
        "output": output_path.relative_to(root).as_posix(),
        "output_refs": step.output_refs,
        "warnings": warnings,
        "invalidated_steps": [
            name
            for name in ("keyframes", "analyze", "map", "propose", "review_project")
            if state.steps.get(name) and state.steps[name].status.value == "invalidated"
        ],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"wrote {payload['output']}")
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_map(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    try:
        output_path, _state, warnings = map_workspace(project_path)
    except WorkspacePrerequisiteError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.prerequisite_step_missing)
    except SourceLedgerError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    payload = {
        "output": output_path.relative_to(root).as_posix(),
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"wrote {payload['output']}")
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_transcribe(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    try:
        output_path, state, warnings = transcribe_workspace(project_path)
    except WorkspacePrerequisiteError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.prerequisite_step_missing)
    except WorkspaceDependencyError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.missing_required_dependency_for_command)
    except SourceLedgerError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    step = state.steps["transcribe"]
    payload = {
        "output": output_path.relative_to(root).as_posix() if output_path else None,
        "output_refs": step.output_refs,
        "status": step.status.value,
        "warnings": warnings,
        "invalidated_steps": [
            name
            for name in ("map", "propose", "review_project")
            if state.steps.get(name) and state.steps[name].status.value == "invalidated"
        ],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"wrote {payload['output']}" if output_path else f"transcribe {step.status.value}")
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_keyframes(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    try:
        output_path, state, warnings = keyframes_workspace(project_path)
    except WorkspacePrerequisiteError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.prerequisite_step_missing)
    except WorkspaceDependencyError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.missing_required_dependency_for_command)
    root = project_root(project_path)
    step = state.steps["keyframes"]
    payload = {
        "output": output_path.relative_to(root).as_posix(),
        "output_refs": step.output_refs,
        "status": step.status.value,
        "warnings": warnings,
        "invalidated_steps": [
            name
            for name in ("analyze", "map", "propose", "review_project")
            if state.steps.get(name) and state.steps[name].status.value == "invalidated"
        ],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"wrote {payload['output']}")
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_analyze(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    try:
        output_path, report_path, state, warnings = analyze_workspace(project_path)
    except WorkspacePrerequisiteError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.prerequisite_step_missing)
    except SourceLedgerError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    step = state.steps["analyze"]
    payload = {
        "output": output_path.relative_to(root).as_posix(),
        "report": report_path.relative_to(root).as_posix(),
        "output_refs": step.output_refs,
        "status": step.status.value,
        "warnings": warnings,
        "invalidated_steps": [
            name
            for name in ("analyze", "map", "review_project")
            if state.steps.get(name) and state.steps[name].status.value == "invalidated"
        ],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"wrote {payload['output']}")
        print(f"wrote {payload['report']}")
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_review(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    if args.scope in {"proposal", "timeline"}:
        print(
            f"review --scope {args.scope} is outside the current gate and is not implemented",
            file=sys.stderr,
        )
        return int(ExitCode.prerequisite_step_missing)
    project_path = Path(args.project)
    try:
        load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    try:
        output_path, _state, warnings, issues = review_project_workspace(
            project_path,
            scope=args.scope,
        )
    except WorkspacePrerequisiteError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.prerequisite_step_missing)
    except SourceLedgerError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    payload = {
        "output": output_path.relative_to(root).as_posix(),
        "warnings": warnings,
        "issues": issues,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"wrote {payload['output']}")
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_propose(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    try:
        state = propose_workspace(project_path)
    except WorkspacePrerequisiteError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.prerequisite_step_missing)
    except WorkspaceDependencyError as exc:
        state = load_state(project_root(project_path))
        if args.json and state and "propose" in state.steps:
            step = state.steps["propose"]
            print(
                json.dumps(
                    {
                        "error": str(exc),
                        "output": None,
                        "output_refs": step.output_refs,
                        "status": step.status.value,
                        "warnings": step.warnings,
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            print(str(exc), file=sys.stderr)
        return int(ExitCode.missing_required_dependency_for_command)
    step = state.steps["propose"]
    payload = {
        "output": None,
        "output_refs": step.output_refs,
        "status": step.status.value,
        "warnings": step.warnings,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"propose {step.status.value}")
        for warning in step.warnings:
            print(f"warning: {warning}", file=sys.stderr)
    return int(ExitCode.success_with_warnings if step.warnings else ExitCode.success)


def blocked_stage_a_command(args: argparse.Namespace) -> int:
    print(
        f"{args.command} is outside the current V0-010a gate and is not implemented",
        file=sys.stderr,
    )
    return int(ExitCode.prerequisite_step_missing)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        from artist_portrait_editor import __version__

        print(__version__)
        return int(ExitCode.success)
    if args.command is None:
        parser.print_help()
        return int(ExitCode.invalid_arguments)
    handlers = {
        "validate": cmd_validate,
        "init": cmd_init,
        "status": cmd_status,
        "doctor": cmd_doctor,
        "generate-schema": cmd_generate_schema,
        "scan": cmd_scan,
        "segment": cmd_segment,
        "transcribe": cmd_transcribe,
        "keyframes": cmd_keyframes,
        "analyze": cmd_analyze,
        "map": cmd_map,
        "review": cmd_review,
        "propose": cmd_propose,
    }
    handler = handlers.get(args.command, blocked_stage_a_command)
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
