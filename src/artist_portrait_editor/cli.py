from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from artist_portrait_editor.config_loader import ConfigLoadError, load_project_config
from artist_portrait_editor.exit_codes import ExitCode
from artist_portrait_editor.schemas import write_schema_files
from artist_portrait_editor.workspace import init_workspace, load_state, project_root, state_as_dict


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="artist-portrait")
    parser.add_argument("--version", action="store_true")
    subparsers = parser.add_subparsers(dest="command")

    for command in ("validate", "init", "status"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--project", required=True)
        sub.add_argument("--json", action="store_true")
        sub.add_argument("--quiet", action="store_true")
        sub.add_argument("--verbose", action="store_true")
        if command == "init":
            sub.add_argument("--dry-run", action="store_true")

    schema_sub = subparsers.add_parser("generate-schema")
    schema_sub.add_argument("--output-dir", default="schemas")

    for command in (
        "scan",
        "segment",
        "transcribe",
        "analyze",
        "relate",
        "map",
        "propose",
        "timeline",
        "review",
        "run",
    ):
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
    try:
        load_project_config(Path(args.project))
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    state = load_state(project_root(Path(args.project)))
    if state is None:
        payload = {"overall_status": "new", "state": None}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        elif not args.quiet:
            print("new")
        return int(ExitCode.success)
    if args.json:
        print(json.dumps(state_as_dict(state), ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(state.overall_status)
    return int(ExitCode.success)


def cmd_generate_schema(args: argparse.Namespace) -> int:
    write_schema_files(Path(args.output_dir))
    print(f"schemas written to {args.output_dir}")
    return int(ExitCode.success)


def blocked_stage_a_command(args: argparse.Namespace) -> int:
    print(
        f"{args.command} is outside the Stage A gate and is not implemented",
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
        "generate-schema": cmd_generate_schema,
    }
    handler = handlers.get(args.command, blocked_stage_a_command)
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
