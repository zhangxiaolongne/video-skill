from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from artist_portrait_editor.acceptance import (
    build_acceptance_repair_approval_request,
    build_acceptance_repair_execution_bundle,
    build_acceptance_repair_execution_dry_run,
    build_acceptance_repair_plan,
    build_project_acceptance_report,
    import_acceptance_repair_approval_record,
    import_acceptance_repair_execution_record,
)
from artist_portrait_editor.capabilities import detect_capabilities
from artist_portrait_editor.bgm import (
    BgmError,
    analyze_candidates,
    build_bgm_rhythm_intelligence,
    build_fit_plan,
    import_candidate,
    load_ledger,
    render_bgm_analysis_report,
    review_bgm,
)
from artist_portrait_editor.config_loader import ConfigLoadError, load_project_config
from artist_portrait_editor.editor_package import EditorPackageError, build_editor_package
from artist_portrait_editor.bgm_recommendation import (
    BgmRecommendationError,
    import_bgm_recommendation_candidate,
    prepare_bgm_recommendation_handoff,
    review_bgm_recommendation_fit,
    select_bgm_recommendation_for_fit,
)
from artist_portrait_editor.exit_codes import ExitCode
from artist_portrait_editor.final_export_workspace import (
    final_export_workspace,
    review_final_export_workspace,
)
from artist_portrait_editor.fcpxml_writer import (
    FcpxmlWriterError,
    build_fcpxml_draft,
    build_fcpxml_repair_approval_request,
    build_fcpxml_repair_dry_run,
    build_fcpxml_repair_plan,
    import_fcpxml_import_review,
    import_fcpxml_repair_execution_record,
    import_fcpxml_repair_approval_record,
)
from artist_portrait_editor.models.source import RightsStatus
from artist_portrait_editor.models.acceptance import (
    AcceptanceRepairApprovalRecord,
    AcceptanceRepairExecutionDryRun,
)
from artist_portrait_editor.models.state import OverallStatus, StepLedgerEntry, StepStatus
from artist_portrait_editor.nle_interchange import (
    NleInterchangeError,
    build_nle_interchange_plan,
)
from artist_portrait_editor.operator_runbook import build_operator_runbook
from artist_portrait_editor.preview_workspace import (
    preview_workspace,
    review_preview_workspace,
)
from artist_portrait_editor.release_hardening import (
    ReleaseHardeningError,
    build_release_hardening_report,
)
from artist_portrait_editor.run_records import (
    environment_snapshot,
    new_run_id,
    utc_now,
    write_json,
)
from artist_portrait_editor.rhythm import (
    RhythmError,
    build_edit_guidance,
    build_rhythm_media_qc,
    build_rhythm_plan,
    build_rhythm_repair_plan,
)
from artist_portrait_editor.media.scanner import ScanError, SourceLedgerError
from artist_portrait_editor.schemas import write_schema_files
from artist_portrait_editor.workspace import (
    WorkspaceDependencyError,
    WorkspaceProposalCandidateError,
    WorkspacePreviewError,
    WorkspacePrerequisiteError,
    WorkspaceTimelineError,
    analyze_workspace,
    doctor_project_payload,
    init_workspace,
    import_agent_proposal_workspace,
    keyframes_workspace,
    load_state,
    map_workspace,
    propose_workspace,
    project_status_payload,
    project_root,
    render_doctor_panel,
    render_status_panel,
    review_proposal_workspace,
    review_project_workspace,
    review_timeline_workspace,
    scan_workspace,
    segment_workspace,
    state_as_dict,
    save_state,
    transcribe_workspace,
    timeline_workspace,
    write_run_report,
)
from artist_portrait_editor.workflow import (
    WorkflowExecutionReviewError,
    build_workflow_plan,
    build_workflow_repair_approval_request,
    build_workflow_repair_dry_run,
    build_workflow_repair_refresh_plan,
    build_workflow_repair_plan,
    import_workflow_repair_execution_record,
    import_workflow_repair_approval_record,
    import_workflow_execution_record,
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

    release_sub = subparsers.add_parser("release-check")
    release_sub.add_argument("--project", required=True)
    release_sub.add_argument("--json", action="store_true")
    release_sub.add_argument("--quiet", action="store_true")
    release_sub.add_argument("--verbose", action="store_true")

    workflow_sub = subparsers.add_parser("workflow")
    workflow_sub.add_argument("--project", required=True)
    workflow_sub.add_argument("--target", choices=("core", "preview", "delivery"), default="delivery")
    workflow_sub.add_argument("--execution-record")
    workflow_sub.add_argument("--repair-plan", action="store_true")
    workflow_sub.add_argument("--approval-request", action="store_true")
    workflow_sub.add_argument("--approval-record")
    workflow_sub.add_argument("--repair-dry-run", action="store_true")
    workflow_sub.add_argument("--repair-execution-record")
    workflow_sub.add_argument("--repair-refresh-plan", action="store_true")
    workflow_sub.add_argument("--json", action="store_true")
    workflow_sub.add_argument("--quiet", action="store_true")
    workflow_sub.add_argument("--verbose", action="store_true")

    operator_sub = subparsers.add_parser("operator")
    operator_sub.add_argument("--project", required=True)
    operator_sub.add_argument("--target", choices=("core", "preview", "delivery"), default="delivery")
    operator_sub.add_argument("--json", action="store_true")
    operator_sub.add_argument("--quiet", action="store_true")
    operator_sub.add_argument("--verbose", action="store_true")

    editor_package_sub = subparsers.add_parser("editor-package")
    editor_package_sub.add_argument("--project", required=True)
    editor_package_sub.add_argument("--json", action="store_true")
    editor_package_sub.add_argument("--quiet", action="store_true")
    editor_package_sub.add_argument("--verbose", action="store_true")

    nle_plan_sub = subparsers.add_parser("nle-plan")
    nle_plan_sub.add_argument("--project", required=True)
    nle_plan_sub.add_argument(
        "--target",
        choices=("fcpxml", "edl", "resolve_csv", "all"),
        default="all",
    )
    nle_plan_sub.add_argument("--frame-rate", type=float, default=24.0)
    nle_plan_sub.add_argument("--json", action="store_true")
    nle_plan_sub.add_argument("--quiet", action="store_true")
    nle_plan_sub.add_argument("--verbose", action="store_true")

    fcpxml_sub = subparsers.add_parser("fcpxml")
    fcpxml_sub.add_argument("--project", required=True)
    fcpxml_sub.add_argument("--draft", action="store_true")
    fcpxml_sub.add_argument("--import-review")
    fcpxml_sub.add_argument("--repair-plan", action="store_true")
    fcpxml_sub.add_argument("--approval-request", action="store_true")
    fcpxml_sub.add_argument("--approval-record")
    fcpxml_sub.add_argument("--repair-dry-run", action="store_true")
    fcpxml_sub.add_argument("--repair-execution-record")
    fcpxml_sub.add_argument("--json", action="store_true")
    fcpxml_sub.add_argument("--quiet", action="store_true")
    fcpxml_sub.add_argument("--verbose", action="store_true")

    acceptance_sub = subparsers.add_parser("acceptance")
    acceptance_sub.add_argument("--project", required=True)
    acceptance_sub.add_argument(
        "--profile",
        choices=("standard", "core", "preview", "delivery"),
        default="standard",
    )
    acceptance_sub.add_argument("--json", action="store_true")
    acceptance_sub.add_argument("--quiet", action="store_true")
    acceptance_sub.add_argument("--verbose", action="store_true")
    acceptance_sub.add_argument("--repair-plan", action="store_true")
    acceptance_sub.add_argument("--approval-request", action="store_true")
    acceptance_sub.add_argument("--approval-record")
    acceptance_sub.add_argument("--execution-dry-run", action="store_true")
    acceptance_sub.add_argument("--execution-bundle", action="store_true")
    acceptance_sub.add_argument("--execution-record")

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
        choices=("project", "proposal", "timeline", "preview", "final_export", "all"),
    )
    review_sub.add_argument("--json", action="store_true")
    review_sub.add_argument("--quiet", action="store_true")
    review_sub.add_argument("--verbose", action="store_true")

    propose_sub = subparsers.add_parser("propose")
    propose_sub.add_argument("--project", required=True)
    propose_sub.add_argument("--json", action="store_true")
    propose_sub.add_argument("--quiet", action="store_true")
    propose_sub.add_argument("--verbose", action="store_true")
    propose_sub.add_argument(
        "--agent-output",
        help="Host-Agent ProposalSet JSON candidate to quarantine, validate, and promote",
    )

    timeline_sub = subparsers.add_parser("timeline")
    timeline_sub.add_argument("--project", required=True)
    timeline_sub.add_argument(
        "--proposal",
        required=True,
        choices=("proposal_safe", "proposal_advanced", "proposal_risky"),
    )
    timeline_sub.add_argument("--json", action="store_true")
    timeline_sub.add_argument("--quiet", action="store_true")
    timeline_sub.add_argument("--verbose", action="store_true")

    bgm_sub = subparsers.add_parser("bgm")
    bgm_sub.add_argument("action", choices=("import", "list", "analyze", "rhythm", "recommend", "select", "fit", "review"))
    bgm_sub.add_argument("--project", required=True)
    bgm_sub.add_argument("--file")
    bgm_sub.add_argument("--source-id")
    bgm_sub.add_argument("--candidate")
    bgm_sub.add_argument("--recommendation-id")
    bgm_sub.add_argument("--rank", type=int)
    bgm_sub.add_argument("--extract-in", type=float, default=0.0)
    bgm_sub.add_argument("--extract-out", type=float)
    bgm_sub.add_argument("--stream-index", type=int, default=0)
    bgm_sub.add_argument("--window-seconds", type=float, default=0.5)
    bgm_sub.add_argument("--fit-mode", choices=("auto", "single_pass", "trim", "loop"), default="auto")
    bgm_sub.add_argument("--fade-in-seconds", type=float)
    bgm_sub.add_argument("--fade-out-seconds", type=float)
    bgm_sub.add_argument("--target-gain-db", type=float)
    bgm_sub.add_argument("--ducking-gain-db", type=float, default=-9.0)
    bgm_sub.add_argument("--no-ducking", action="store_true")
    bgm_sub.add_argument("--beat-align", action="store_true")
    bgm_sub.add_argument("--agent-output")
    bgm_sub.add_argument(
        "--rights-status",
        choices=tuple(item.value for item in RightsStatus),
        default=RightsStatus.permission_unknown.value,
    )
    bgm_sub.add_argument("--intent", default="user-provided BGM candidate")
    bgm_sub.add_argument("--json", action="store_true")
    bgm_sub.add_argument("--quiet", action="store_true")
    bgm_sub.add_argument("--verbose", action="store_true")

    preview_sub = subparsers.add_parser("preview")
    preview_sub.add_argument("--project", required=True)
    preview_sub.add_argument("--width", type=int, default=480)
    preview_sub.add_argument("--fps", type=int, default=12)
    preview_sub.add_argument("--json", action="store_true")
    preview_sub.add_argument("--quiet", action="store_true")
    preview_sub.add_argument("--verbose", action="store_true")

    export_sub = subparsers.add_parser("export")
    export_sub.add_argument("--project", required=True)
    export_sub.add_argument(
        "--profile",
        choices=("review_720p", "delivery_1080p"),
        default="review_720p",
    )
    export_sub.add_argument("--json", action="store_true")
    export_sub.add_argument("--quiet", action="store_true")
    export_sub.add_argument("--verbose", action="store_true")

    rhythm_sub = subparsers.add_parser("rhythm")
    rhythm_sub.add_argument("--project", required=True)
    rhythm_sub.add_argument("--intent")
    rhythm_sub.add_argument("--agent-output")
    rhythm_sub.add_argument("--qc", action="store_true")
    rhythm_sub.add_argument("--repair-plan", action="store_true")
    rhythm_sub.add_argument("--edit-guidance", action="store_true")
    rhythm_sub.add_argument(
        "--acceptance-profile",
        choices=("standard", "core", "preview", "delivery"),
        default="delivery",
    )
    rhythm_sub.add_argument("--json", action="store_true")
    rhythm_sub.add_argument("--quiet", action="store_true")
    rhythm_sub.add_argument("--verbose", action="store_true")

    for command in ("relate", "run"):
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


def cmd_release_check(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        config = load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    root = project_root(project_path)
    repo_root = Path(__file__).resolve().parents[2]
    try:
        json_path, md_path, report = build_release_hardening_report(
            project_root=root,
            project_id=config.project.id,
            repo_root=repo_root,
        )
    except ReleaseHardeningError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    payload = {
        "output": json_path.relative_to(root).as_posix(),
        "report": md_path.relative_to(root).as_posix(),
        "status": report.status,
        "release_hardening_report": report.model_dump(mode="json"),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"release-check {report.status}")
        print(f"wrote {payload['report']}")
    return int(
        ExitCode.success
        if report.status == "ready_for_local_release"
        else ExitCode.success_with_warnings
        if report.status == "warning"
        else ExitCode.output_or_reference_validation_failed
    )


def cmd_workflow(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        config = load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    root = project_root(project_path)
    state = load_state(root)
    mode_count = sum(
        bool(value)
        for value in (
            args.execution_record,
            args.repair_plan,
            args.approval_request,
            args.approval_record,
            args.repair_dry_run,
            args.repair_execution_record,
            args.repair_refresh_plan,
        )
    )
    if mode_count > 1:
        print("workflow mutation/review modes are mutually exclusive", file=sys.stderr)
        return int(ExitCode.invalid_cli_usage)
    if args.approval_request:
        try:
            json_path, md_path, handoff_path, request = build_workflow_repair_approval_request(
                root=root,
                project_id=config.project.id,
                target=args.target,
            )
        except WorkflowExecutionReviewError as exc:
            print(str(exc), file=sys.stderr)
            return int(ExitCode.output_or_reference_validation_failed)
        payload = {
            "output": json_path.relative_to(root).as_posix(),
            "report": md_path.relative_to(root).as_posix(),
            "handoff": handoff_path.relative_to(root).as_posix(),
            "workflow_repair_approval_request": request.model_dump(mode="json"),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        elif not args.quiet:
            print(f"wrote {payload['report']}")
        return int(ExitCode.success_with_warnings)
    if args.approval_record:
        try:
            json_path, md_path, record = import_workflow_repair_approval_record(
                root=root,
                project_id=config.project.id,
                target=args.target,
                candidate_path=Path(args.approval_record),
            )
        except WorkflowExecutionReviewError as exc:
            print(str(exc), file=sys.stderr)
            return int(ExitCode.output_or_reference_validation_failed)
        payload = {
            "output": json_path.relative_to(root).as_posix(),
            "report": md_path.relative_to(root).as_posix(),
            "status": record.status,
            "workflow_repair_approval_record": record.model_dump(mode="json"),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        elif not args.quiet:
            print(f"workflow repair approval record {record.status}")
            print(f"wrote {payload['report']}")
        return int(ExitCode.success if record.status == "passed" else ExitCode.success_with_warnings)
    if args.repair_dry_run:
        try:
            json_path, md_path, handoff_path, dry_run = build_workflow_repair_dry_run(
                root=root,
                project_id=config.project.id,
                target=args.target,
            )
        except WorkflowExecutionReviewError as exc:
            print(str(exc), file=sys.stderr)
            return int(ExitCode.output_or_reference_validation_failed)
        payload = {
            "output": json_path.relative_to(root).as_posix(),
            "report": md_path.relative_to(root).as_posix(),
            "handoff": handoff_path.relative_to(root).as_posix(),
            "workflow_repair_dry_run": dry_run.model_dump(mode="json"),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        elif not args.quiet:
            print(f"workflow repair dry run {dry_run.approved_step_count} approved")
            print(f"wrote {payload['report']}")
        return int(ExitCode.success_with_warnings if dry_run.rejected_step_count else ExitCode.success)
    if args.repair_execution_record:
        try:
            json_path, md_path, handoff_path, review = import_workflow_repair_execution_record(
                root=root,
                project_id=config.project.id,
                target=args.target,
                candidate_path=Path(args.repair_execution_record),
            )
        except WorkflowExecutionReviewError as exc:
            print(str(exc), file=sys.stderr)
            return int(ExitCode.output_or_reference_validation_failed)
        if state is not None:
            run_id = new_run_id()
            status = (
                StepStatus.completed
                if review.status == "passed"
                else StepStatus.completed_with_warnings
                if review.status == "warning"
                else StepStatus.failed
            )
            state.steps["workflow_repair_execution_review"] = StepLedgerEntry(
                status=status,
                output_refs=[
                    json_path.relative_to(root).as_posix(),
                    md_path.relative_to(root).as_posix(),
                    handoff_path.relative_to(root).as_posix(),
                ],
                last_run_id=run_id,
                warnings=[action.detail for action in review.action_reviews if action.review_status != "accepted"],
            )
            state.latest_run_id = run_id
            state.updated_at = utc_now()
            runs_dir = root / ".artist-portrait" / "runs" / run_id
            runs_dir.mkdir(parents=True, exist_ok=True)
            write_json(
                runs_dir / "command.json",
                {
                    "command": "workflow",
                    "project": str(project_path),
                    "target": args.target,
                    "repair_execution_record": str(args.repair_execution_record),
                },
            )
            write_json(runs_dir / "environment.json", environment_snapshot())
            write_json(
                runs_dir / "step_result.json",
                {
                    "step": "workflow_repair_execution_review",
                    "status": status.value,
                    "output_refs": state.steps["workflow_repair_execution_review"].output_refs,
                    "commands_executed": False,
                    "media_rendered": False,
                    "edit_points_moved": False,
                    "automatic_music_selection": False,
                    "model_call_performed": False,
                    "network_performed": False,
                    "acceptance_success_promoted": False,
                },
            )
            save_state(root, state)
            write_run_report(root / config.paths.output_dir, state, [])
        payload = {
            "output": json_path.relative_to(root).as_posix(),
            "report": md_path.relative_to(root).as_posix(),
            "handoff": handoff_path.relative_to(root).as_posix(),
            "status": review.status,
            "workflow_repair_execution_review": review.model_dump(mode="json"),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        elif not args.quiet:
            print(f"workflow repair execution review {review.status}")
            print(f"wrote {payload['report']}")
        return int(
            ExitCode.success
            if review.status == "passed"
            else ExitCode.success_with_warnings
            if review.status == "warning"
            else ExitCode.output_or_reference_validation_failed
        )
    if args.repair_refresh_plan:
        try:
            json_path, md_path, handoff_path, refresh_plan = build_workflow_repair_refresh_plan(
                root=root,
                project_id=config.project.id,
                target=args.target,
            )
        except WorkflowExecutionReviewError as exc:
            print(str(exc), file=sys.stderr)
            return int(ExitCode.output_or_reference_validation_failed)
        if state is not None:
            run_id = new_run_id()
            status = (
                StepStatus.completed
                if refresh_plan.status == "ready"
                else StepStatus.completed_with_warnings
                if refresh_plan.status == "no_actions"
                else StepStatus.failed
            )
            state.steps["workflow_repair_refresh_plan"] = StepLedgerEntry(
                status=status,
                output_refs=[
                    json_path.relative_to(root).as_posix(),
                    md_path.relative_to(root).as_posix(),
                    handoff_path.relative_to(root).as_posix(),
                ],
                last_run_id=run_id,
                warnings=[step.rationale for step in refresh_plan.steps if step.refresh_status != "ready_to_resubmit"],
            )
            state.latest_run_id = run_id
            state.updated_at = utc_now()
            runs_dir = root / ".artist-portrait" / "runs" / run_id
            runs_dir.mkdir(parents=True, exist_ok=True)
            write_json(
                runs_dir / "command.json",
                {
                    "command": "workflow",
                    "project": str(project_path),
                    "target": args.target,
                    "repair_refresh_plan": True,
                },
            )
            write_json(runs_dir / "environment.json", environment_snapshot())
            write_json(
                runs_dir / "step_result.json",
                {
                    "step": "workflow_repair_refresh_plan",
                    "status": status.value,
                    "output_refs": state.steps["workflow_repair_refresh_plan"].output_refs,
                    "commands_executed": False,
                    "media_rendered": False,
                    "workflow_plan_mutated": False,
                    "acceptance_success_promoted": False,
                },
            )
            save_state(root, state)
            write_run_report(root / config.paths.output_dir, state, [])
        payload = {
            "output": json_path.relative_to(root).as_posix(),
            "report": md_path.relative_to(root).as_posix(),
            "handoff": handoff_path.relative_to(root).as_posix(),
            "status": refresh_plan.status,
            "workflow_repair_refresh_plan": refresh_plan.model_dump(mode="json"),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        elif not args.quiet:
            print(f"workflow repair refresh plan {refresh_plan.status}")
            print(f"wrote {payload['report']}")
        return int(
            ExitCode.success
            if refresh_plan.status == "ready"
            else ExitCode.success_with_warnings
            if refresh_plan.status == "no_actions"
            else ExitCode.output_or_reference_validation_failed
        )
    if args.repair_plan:
        try:
            json_path, md_path, handoff_path, repair_plan = build_workflow_repair_plan(
                root=root,
                project_id=config.project.id,
                target=args.target,
                state=state,
            )
        except WorkflowExecutionReviewError as exc:
            print(str(exc), file=sys.stderr)
            return int(ExitCode.output_or_reference_validation_failed)
        if state is not None:
            run_id = new_run_id()
            status = (
                StepStatus.completed
                if repair_plan.status == "no_actions"
                else StepStatus.completed_with_warnings
                if repair_plan.status == "ready"
                else StepStatus.failed
            )
            state.steps["workflow_repair_plan"] = StepLedgerEntry(
                status=status,
                output_refs=[
                    json_path.relative_to(root).as_posix(),
                    md_path.relative_to(root).as_posix(),
                    handoff_path.relative_to(root).as_posix(),
                ],
                last_run_id=run_id,
                warnings=[action.rationale for action in repair_plan.actions],
            )
            state.latest_run_id = run_id
            state.updated_at = utc_now()
            runs_dir = root / ".artist-portrait" / "runs" / run_id
            runs_dir.mkdir(parents=True, exist_ok=True)
            write_json(
                runs_dir / "command.json",
                {
                    "command": "workflow",
                    "project": str(project_path),
                    "target": args.target,
                    "repair_plan": True,
                },
            )
            write_json(runs_dir / "environment.json", environment_snapshot())
            write_json(
                runs_dir / "step_result.json",
                {
                    "step": "workflow_repair_plan",
                    "status": status.value,
                    "output_refs": state.steps["workflow_repair_plan"].output_refs,
                    "commands_executed": False,
                    "media_rendered": False,
                    "edit_points_moved": False,
                    "automatic_music_selection": False,
                    "model_call_performed": False,
                    "network_performed": False,
                    "acceptance_success_promoted": False,
                },
            )
            save_state(root, state)
            write_run_report(root / config.paths.output_dir, state, [])
        payload = {
            "output": json_path.relative_to(root).as_posix(),
            "report": md_path.relative_to(root).as_posix(),
            "handoff": handoff_path.relative_to(root).as_posix(),
            "status": repair_plan.status,
            "workflow_repair_plan": repair_plan.model_dump(mode="json"),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        elif not args.quiet:
            print(f"workflow repair plan {repair_plan.status}")
            print(f"next {repair_plan.first_required_command or 'none'}")
            print(f"wrote {payload['report']}")
        return int(
            ExitCode.success
            if repair_plan.status == "no_actions"
            else ExitCode.success_with_warnings
        )
    if args.execution_record:
        try:
            json_path, md_path, handoff_path, review = import_workflow_execution_record(
                root=root,
                project_id=config.project.id,
                target=args.target,
                candidate_path=Path(args.execution_record),
                state=state,
            )
        except WorkflowExecutionReviewError as exc:
            print(str(exc), file=sys.stderr)
            return int(ExitCode.output_or_reference_validation_failed)
        if state is not None:
            run_id = new_run_id()
            status = (
                StepStatus.completed
                if review.status == "passed"
                else StepStatus.completed_with_warnings
                if review.status == "warning"
                else StepStatus.failed
            )
            state.steps["workflow_execution_review"] = StepLedgerEntry(
                status=status,
                output_refs=[
                    json_path.relative_to(root).as_posix(),
                    md_path.relative_to(root).as_posix(),
                    handoff_path.relative_to(root).as_posix(),
                    review.quarantine_ref,
                ],
                last_run_id=run_id,
                warnings=[
                    step.detail
                    for step in review.step_reviews
                    if step.review_status in {"rejected", "missing", "skipped"}
                ],
            )
            state.latest_run_id = run_id
            state.updated_at = utc_now()
            runs_dir = root / ".artist-portrait" / "runs" / run_id
            runs_dir.mkdir(parents=True, exist_ok=True)
            write_json(
                runs_dir / "command.json",
                {
                    "command": "workflow",
                    "project": str(project_path),
                    "target": args.target,
                    "execution_record": str(args.execution_record),
                },
            )
            write_json(runs_dir / "environment.json", environment_snapshot())
            write_json(
                runs_dir / "step_result.json",
                {
                    "step": "workflow_execution_review",
                    "status": status.value,
                    "output_refs": state.steps["workflow_execution_review"].output_refs,
                    "commands_executed": False,
                    "media_rendered": False,
                    "edit_points_moved": False,
                    "automatic_music_selection": False,
                    "model_call_performed": False,
                    "network_performed": False,
                },
            )
            save_state(root, state)
            write_run_report(root / config.paths.output_dir, state, [])
        payload = {
            "output": json_path.relative_to(root).as_posix(),
            "report": md_path.relative_to(root).as_posix(),
            "handoff": handoff_path.relative_to(root).as_posix(),
            "quarantine": review.quarantine_ref,
            "status": review.status,
            "workflow_execution_review": review.model_dump(mode="json"),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        elif not args.quiet:
            print(f"workflow execution review {review.status}")
            print(f"wrote {payload['report']}")
        return int(ExitCode.success if review.status == "passed" else ExitCode.success_with_warnings)
    json_path, md_path, handoff_path, plan = build_workflow_plan(
        root=root,
        project_id=config.project.id,
        target=args.target,
        state=state,
    )
    if state is not None:
        run_id = new_run_id()
        status = (
            StepStatus.completed
            if plan.status == "ready"
            else StepStatus.completed_with_warnings
            if plan.status == "in_progress"
            else StepStatus.failed
        )
        state.steps["workflow"] = StepLedgerEntry(
            status=status,
            output_refs=[
                json_path.relative_to(root).as_posix(),
                md_path.relative_to(root).as_posix(),
                handoff_path.relative_to(root).as_posix(),
            ],
            last_run_id=run_id,
            warnings=[step.rationale for step in plan.steps if step.status in {"next", "blocked"}],
        )
        state.latest_run_id = run_id
        state.updated_at = utc_now()
        runs_dir = root / ".artist-portrait" / "runs" / run_id
        runs_dir.mkdir(parents=True, exist_ok=True)
        write_json(runs_dir / "command.json", {"command": "workflow", "project": str(project_path), "target": args.target})
        write_json(runs_dir / "environment.json", environment_snapshot())
        write_json(
            runs_dir / "step_result.json",
            {
                "step": "workflow",
                "status": status.value,
                "output_refs": state.steps["workflow"].output_refs,
                "commands_executed": False,
                "media_rendered": False,
                "edit_points_moved": False,
                "automatic_music_selection": False,
                "model_call_performed": False,
                "network_performed": False,
            },
        )
        save_state(root, state)
        write_run_report(root / config.paths.output_dir, state, [])
    payload = {
        "output": json_path.relative_to(root).as_posix(),
        "report": md_path.relative_to(root).as_posix(),
        "handoff": handoff_path.relative_to(root).as_posix(),
        "status": plan.status,
        "next_command": plan.next_command,
        "workflow_plan": plan.model_dump(mode="json"),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"workflow {plan.status}")
        print(f"next {plan.next_command or 'none'}")
        print(f"wrote {payload['report']}")
    return int(ExitCode.success if plan.status == "ready" else ExitCode.success_with_warnings)


def cmd_operator(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        config = load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    root = project_root(project_path)
    state = load_state(root)
    json_path, md_path, handoff_path, runbook = build_operator_runbook(
        root=root,
        project_id=config.project.id,
        target=args.target,
        state=state,
    )
    if state is not None:
        run_id = new_run_id()
        status = (
            StepStatus.completed
            if runbook.status == "ready"
            else StepStatus.completed_with_warnings
            if runbook.status in {"in_progress", "warning"}
            else StepStatus.failed
        )
        state.steps["operator"] = StepLedgerEntry(
            status=status,
            output_refs=[
                json_path.relative_to(root).as_posix(),
                md_path.relative_to(root).as_posix(),
                handoff_path.relative_to(root).as_posix(),
            ],
            last_run_id=run_id,
            warnings=[
                stage.summary
                for stage in runbook.stages
                if stage.status in {"current", "blocked", "warning"}
            ][:12],
        )
        state.latest_run_id = run_id
        state.updated_at = utc_now()
        runs_dir = root / ".artist-portrait" / "runs" / run_id
        runs_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            runs_dir / "command.json",
            {"command": "operator", "project": str(project_path), "target": args.target},
        )
        write_json(runs_dir / "environment.json", environment_snapshot())
        write_json(
            runs_dir / "step_result.json",
            {
                "step": "operator",
                "status": status.value,
                "output_refs": state.steps["operator"].output_refs,
                "commands_executed": False,
                "media_rendered": False,
                "timeline_mutated": False,
                "edit_points_moved": False,
                "automatic_music_selection": False,
                "model_call_performed": False,
                "network_performed": False,
            },
        )
        save_state(root, state)
        write_run_report(root / config.paths.output_dir, state, [])
    payload = {
        "output": json_path.relative_to(root).as_posix(),
        "report": md_path.relative_to(root).as_posix(),
        "handoff": handoff_path.relative_to(root).as_posix(),
        "status": runbook.status,
        "next_command": runbook.next_command,
        "operator_runbook": runbook.model_dump(mode="json"),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"operator {runbook.status}")
        print(f"next {runbook.next_command or 'none'}")
        print(f"wrote {payload['report']}")
    return int(ExitCode.success if runbook.status == "ready" else ExitCode.success_with_warnings)


def cmd_editor_package(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        config = load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    root = project_root(project_path)
    state = load_state(root)
    try:
        json_path, md_path, csv_path, handoff_path, package = build_editor_package(
            root=root,
            project_id=config.project.id,
            state=state,
        )
    except EditorPackageError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    if state is not None:
        run_id = new_run_id()
        status = (
            StepStatus.completed
            if package.status == "ready"
            else StepStatus.completed_with_warnings
            if package.status == "warning"
            else StepStatus.failed
        )
        state.steps["editor_package"] = StepLedgerEntry(
            status=status,
            output_refs=[
                json_path.relative_to(root).as_posix(),
                md_path.relative_to(root).as_posix(),
                csv_path.relative_to(root).as_posix(),
                handoff_path.relative_to(root).as_posix(),
            ],
            last_run_id=run_id,
            warnings=package.warnings,
        )
        state.latest_run_id = run_id
        state.updated_at = utc_now()
        runs_dir = root / ".artist-portrait" / "runs" / run_id
        runs_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            runs_dir / "command.json",
            {"command": "editor-package", "project": str(project_path)},
        )
        write_json(runs_dir / "environment.json", environment_snapshot())
        write_json(
            runs_dir / "step_result.json",
            {
                "step": "editor_package",
                "status": status.value,
                "output_refs": state.steps["editor_package"].output_refs,
                "commands_executed": False,
                "media_rendered": False,
                "timeline_mutated": False,
                "edit_points_moved": False,
                "automatic_music_selection": False,
                "automatic_bgm_fit": False,
                "model_call_performed": False,
                "network_performed": False,
                "image_generation_or_editing_used": False,
            },
        )
        save_state(root, state)
        write_run_report(root / config.paths.output_dir, state, [])
    payload = {
        "output": json_path.relative_to(root).as_posix(),
        "report": md_path.relative_to(root).as_posix(),
        "cue_sheet": csv_path.relative_to(root).as_posix(),
        "handoff": handoff_path.relative_to(root).as_posix(),
        "status": package.status,
        "editor_package": package.model_dump(mode="json"),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"editor-package {package.status}")
        print(f"wrote {payload['report']}")
        print(f"wrote {payload['cue_sheet']}")
    return int(ExitCode.success if package.status == "ready" else ExitCode.success_with_warnings)


def cmd_nle_plan(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        config = load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    root = project_root(project_path)
    state = load_state(root)
    try:
        json_path, md_path, csv_path, handoff_path, plan = build_nle_interchange_plan(
            root=root,
            project_id=config.project.id,
            target=args.target,
            frame_rate=args.frame_rate,
        )
    except NleInterchangeError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    if state is not None:
        run_id = new_run_id()
        status = (
            StepStatus.completed
            if plan.status == "ready"
            else StepStatus.completed_with_warnings
            if plan.status == "warning"
            else StepStatus.failed
        )
        state.steps["nle_plan"] = StepLedgerEntry(
            status=status,
            output_refs=[
                json_path.relative_to(root).as_posix(),
                md_path.relative_to(root).as_posix(),
                csv_path.relative_to(root).as_posix(),
                handoff_path.relative_to(root).as_posix(),
            ],
            last_run_id=run_id,
            warnings=plan.warnings + plan.blocked_reasons,
        )
        state.latest_run_id = run_id
        state.updated_at = utc_now()
        runs_dir = root / ".artist-portrait" / "runs" / run_id
        runs_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            runs_dir / "command.json",
            {
                "command": "nle-plan",
                "project": str(project_path),
                "target": args.target,
                "frame_rate": args.frame_rate,
            },
        )
        write_json(runs_dir / "environment.json", environment_snapshot())
        write_json(
            runs_dir / "step_result.json",
            {
                "step": "nle_plan",
                "status": status.value,
                "output_refs": state.steps["nle_plan"].output_refs,
                "commands_executed": False,
                "media_rendered": False,
                "timeline_mutated": False,
                "edit_points_moved": False,
                "nle_project_written": False,
                "automatic_music_selection": False,
                "automatic_bgm_fit": False,
                "model_call_performed": False,
                "network_performed": False,
                "image_generation_or_editing_used": False,
            },
        )
        save_state(root, state)
        write_run_report(root / config.paths.output_dir, state, [])
    payload = {
        "output": json_path.relative_to(root).as_posix(),
        "report": md_path.relative_to(root).as_posix(),
        "mapping_csv": csv_path.relative_to(root).as_posix(),
        "handoff": handoff_path.relative_to(root).as_posix(),
        "status": plan.status,
        "nle_interchange_plan": plan.model_dump(mode="json"),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"nle-plan {plan.status}")
        print(f"wrote {payload['report']}")
        print(f"wrote {payload['mapping_csv']}")
    return int(ExitCode.success if plan.status == "ready" else ExitCode.success_with_warnings)


def cmd_fcpxml(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    selected_modes = sum(
        bool(item)
        for item in (
            args.draft,
            args.import_review,
            args.repair_plan,
            args.approval_request,
            args.approval_record,
            args.repair_dry_run,
            args.repair_execution_record,
        )
    )
    if selected_modes != 1:
        print(
            "fcpxml requires exactly one of --draft, --import-review, --repair-plan, --approval-request, --approval-record, --repair-dry-run, or --repair-execution-record",
            file=sys.stderr,
        )
        return int(ExitCode.invalid_cli_usage)
    project_path = Path(args.project)
    try:
        config = load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    root = project_root(project_path)
    state = load_state(root)
    if args.repair_execution_record:
        try:
            json_path, md_path, handoff_path, review = import_fcpxml_repair_execution_record(
                root=root,
                project_id=config.project.id,
                candidate_path=Path(args.repair_execution_record),
            )
        except FcpxmlWriterError as exc:
            print(str(exc), file=sys.stderr)
            return int(ExitCode.output_or_reference_validation_failed)
        if state is not None:
            run_id = new_run_id()
            status = (
                StepStatus.completed
                if review.status == "passed"
                else StepStatus.completed_with_warnings
                if review.status == "warning"
                else StepStatus.failed
            )
            state.steps["fcpxml_repair_execution_review"] = StepLedgerEntry(
                status=status,
                output_refs=[
                    json_path.relative_to(root).as_posix(),
                    md_path.relative_to(root).as_posix(),
                    handoff_path.relative_to(root).as_posix(),
                ],
                last_run_id=run_id,
                warnings=[item.detail for item in review.action_reviews if item.review_status != "accepted"],
            )
            state.latest_run_id = run_id
            state.updated_at = utc_now()
            runs_dir = root / ".artist-portrait" / "runs" / run_id
            runs_dir.mkdir(parents=True, exist_ok=True)
            write_json(runs_dir / "command.json", {"command": "fcpxml", "project": str(project_path), "repair_execution_record": str(args.repair_execution_record)})
            write_json(runs_dir / "environment.json", environment_snapshot())
            write_json(
                runs_dir / "step_result.json",
                {
                    "step": "fcpxml_repair_execution_review",
                    "status": status.value,
                    "output_refs": state.steps["fcpxml_repair_execution_review"].output_refs,
                    "commands_executed_by_cli": False,
                    "media_rendered_by_cli": False,
                    "timeline_mutated_by_cli": False,
                    "edit_points_moved_by_cli": False,
                    "nle_import_performed_by_cli": False,
                    "source_relink_performed_by_cli": False,
                    "repair_success_promoted_by_cli": False,
                    "acceptance_success_promoted_by_cli": False,
                },
            )
            save_state(root, state)
            write_run_report(root / config.paths.output_dir, state, [])
        payload = {
            "output": json_path.relative_to(root).as_posix(),
            "report": md_path.relative_to(root).as_posix(),
            "handoff": handoff_path.relative_to(root).as_posix(),
            "status": review.status,
            "fcpxml_repair_execution_review": review.model_dump(mode="json"),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        elif not args.quiet:
            print(f"fcpxml repair execution-review {review.status}")
            print(f"wrote {payload['report']}")
        return int(
            ExitCode.success
            if review.status == "passed"
            else ExitCode.success_with_warnings
            if review.status == "warning"
            else ExitCode.output_or_reference_validation_failed
        )
    if args.approval_request:
        try:
            json_path, md_path, handoff_path, request = build_fcpxml_repair_approval_request(
                root=root,
                project_id=config.project.id,
            )
        except FcpxmlWriterError as exc:
            print(str(exc), file=sys.stderr)
            return int(ExitCode.output_or_reference_validation_failed)
        if state is not None:
            run_id = new_run_id()
            state.steps["fcpxml_repair_approval_request"] = StepLedgerEntry(
                status=StepStatus.completed,
                output_refs=[
                    json_path.relative_to(root).as_posix(),
                    md_path.relative_to(root).as_posix(),
                    handoff_path.relative_to(root).as_posix(),
                ],
                last_run_id=run_id,
                warnings=[],
            )
            state.latest_run_id = run_id
            state.updated_at = utc_now()
            runs_dir = root / ".artist-portrait" / "runs" / run_id
            runs_dir.mkdir(parents=True, exist_ok=True)
            write_json(runs_dir / "command.json", {"command": "fcpxml", "project": str(project_path), "approval_request": True})
            write_json(runs_dir / "environment.json", environment_snapshot())
            write_json(
                runs_dir / "step_result.json",
                {
                    "step": "fcpxml_repair_approval_request",
                    "status": StepStatus.completed.value,
                    "output_refs": state.steps["fcpxml_repair_approval_request"].output_refs,
                    "commands_executed": False,
                    "media_rendered": False,
                    "timeline_mutated": False,
                    "edit_points_moved": False,
                    "nle_import_performed": False,
                    "source_relink_performed": False,
                    "repair_success_claimed": False,
                },
            )
            save_state(root, state)
            write_run_report(root / config.paths.output_dir, state, [])
        payload = {
            "output": json_path.relative_to(root).as_posix(),
            "report": md_path.relative_to(root).as_posix(),
            "handoff": handoff_path.relative_to(root).as_posix(),
            "fcpxml_repair_approval_request": request.model_dump(mode="json"),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        elif not args.quiet:
            print("fcpxml repair approval-request")
            print(f"wrote {payload['report']}")
        return int(ExitCode.success)
    if args.approval_record:
        try:
            json_path, md_path, record = import_fcpxml_repair_approval_record(
                root=root,
                project_id=config.project.id,
                candidate_path=Path(args.approval_record),
            )
        except FcpxmlWriterError as exc:
            print(str(exc), file=sys.stderr)
            return int(ExitCode.output_or_reference_validation_failed)
        if state is not None:
            run_id = new_run_id()
            status = StepStatus.completed if record.status == "passed" else StepStatus.failed
            state.steps["fcpxml_repair_approval_record"] = StepLedgerEntry(
                status=status,
                output_refs=[
                    json_path.relative_to(root).as_posix(),
                    md_path.relative_to(root).as_posix(),
                ],
                last_run_id=run_id,
                warnings=record.invalid_reasons,
            )
            state.latest_run_id = run_id
            state.updated_at = utc_now()
            runs_dir = root / ".artist-portrait" / "runs" / run_id
            runs_dir.mkdir(parents=True, exist_ok=True)
            write_json(runs_dir / "command.json", {"command": "fcpxml", "project": str(project_path), "approval_record": str(args.approval_record)})
            write_json(runs_dir / "environment.json", environment_snapshot())
            write_json(
                runs_dir / "step_result.json",
                {
                    "step": "fcpxml_repair_approval_record",
                    "status": status.value,
                    "output_refs": state.steps["fcpxml_repair_approval_record"].output_refs,
                    "commands_executed_by_cli": False,
                    "media_rendered_by_cli": False,
                    "timeline_mutated_by_cli": False,
                    "edit_points_moved_by_cli": False,
                    "nle_import_performed_by_cli": False,
                    "source_relink_performed_by_cli": False,
                    "repair_success_claimed_by_cli": False,
                },
            )
            save_state(root, state)
            write_run_report(root / config.paths.output_dir, state, [])
        payload = {
            "output": json_path.relative_to(root).as_posix(),
            "report": md_path.relative_to(root).as_posix(),
            "status": record.status,
            "fcpxml_repair_approval_record": record.model_dump(mode="json"),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        elif not args.quiet:
            print(f"fcpxml repair approval-record {record.status}")
            print(f"wrote {payload['report']}")
        return int(ExitCode.success if record.status == "passed" else ExitCode.output_or_reference_validation_failed)
    if args.repair_dry_run:
        try:
            json_path, md_path, handoff_path, dry_run = build_fcpxml_repair_dry_run(
                root=root,
                project_id=config.project.id,
            )
        except FcpxmlWriterError as exc:
            print(str(exc), file=sys.stderr)
            return int(ExitCode.output_or_reference_validation_failed)
        if state is not None:
            run_id = new_run_id()
            state.steps["fcpxml_repair_dry_run"] = StepLedgerEntry(
                status=StepStatus.completed,
                output_refs=[
                    json_path.relative_to(root).as_posix(),
                    md_path.relative_to(root).as_posix(),
                    handoff_path.relative_to(root).as_posix(),
                ],
                last_run_id=run_id,
                warnings=[],
            )
            state.latest_run_id = run_id
            state.updated_at = utc_now()
            runs_dir = root / ".artist-portrait" / "runs" / run_id
            runs_dir.mkdir(parents=True, exist_ok=True)
            write_json(runs_dir / "command.json", {"command": "fcpxml", "project": str(project_path), "repair_dry_run": True})
            write_json(runs_dir / "environment.json", environment_snapshot())
            write_json(
                runs_dir / "step_result.json",
                {
                    "step": "fcpxml_repair_dry_run",
                    "status": StepStatus.completed.value,
                    "output_refs": state.steps["fcpxml_repair_dry_run"].output_refs,
                    "commands_executed": False,
                    "media_rendered": False,
                    "timeline_mutated": False,
                    "edit_points_moved": False,
                    "nle_import_performed": False,
                    "source_relink_performed": False,
                    "repair_success_claimed": False,
                },
            )
            save_state(root, state)
            write_run_report(root / config.paths.output_dir, state, [])
        payload = {
            "output": json_path.relative_to(root).as_posix(),
            "report": md_path.relative_to(root).as_posix(),
            "handoff": handoff_path.relative_to(root).as_posix(),
            "fcpxml_repair_dry_run": dry_run.model_dump(mode="json"),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        elif not args.quiet:
            print("fcpxml repair dry-run")
            print(f"wrote {payload['report']}")
        return int(ExitCode.success)
    if args.repair_plan:
        try:
            json_path, md_path, handoff_path, plan = build_fcpxml_repair_plan(
                root=root,
                project_id=config.project.id,
            )
        except FcpxmlWriterError as exc:
            print(str(exc), file=sys.stderr)
            return int(ExitCode.output_or_reference_validation_failed)
        if state is not None:
            run_id = new_run_id()
            status = (
                StepStatus.completed
                if plan.status == "ready"
                else StepStatus.completed_with_warnings
                if plan.status == "warning"
                else StepStatus.failed
            )
            state.steps["fcpxml_repair_plan"] = StepLedgerEntry(
                status=status,
                output_refs=[
                    json_path.relative_to(root).as_posix(),
                    md_path.relative_to(root).as_posix(),
                    handoff_path.relative_to(root).as_posix(),
                ],
                last_run_id=run_id,
                warnings=plan.warnings,
            )
            state.latest_run_id = run_id
            state.updated_at = utc_now()
            runs_dir = root / ".artist-portrait" / "runs" / run_id
            runs_dir.mkdir(parents=True, exist_ok=True)
            write_json(
                runs_dir / "command.json",
                {"command": "fcpxml", "project": str(project_path), "repair_plan": True},
            )
            write_json(runs_dir / "environment.json", environment_snapshot())
            write_json(
                runs_dir / "step_result.json",
                {
                    "step": "fcpxml_repair_plan",
                    "status": status.value,
                    "output_refs": state.steps["fcpxml_repair_plan"].output_refs,
                    "commands_executed": False,
                    "media_rendered": False,
                    "timeline_mutated": False,
                    "edit_points_moved": False,
                    "nle_import_performed": False,
                    "source_relink_performed": False,
                    "automatic_music_selection": False,
                    "automatic_bgm_fit": False,
                    "model_call_performed": False,
                    "network_performed": False,
                    "image_generation_or_editing_used": False,
                    "repair_success_claimed": False,
                },
            )
            save_state(root, state)
            write_run_report(root / config.paths.output_dir, state, [])
        payload = {
            "output": json_path.relative_to(root).as_posix(),
            "report": md_path.relative_to(root).as_posix(),
            "handoff": handoff_path.relative_to(root).as_posix(),
            "status": plan.status,
            "first_required_command": plan.first_required_command,
            "fcpxml_repair_plan": plan.model_dump(mode="json"),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        elif not args.quiet:
            print(f"fcpxml repair-plan {plan.status}")
            print(f"next {plan.first_required_command or 'none'}")
            print(f"wrote {payload['report']}")
        return int(
            ExitCode.success
            if plan.status == "ready"
            else ExitCode.success_with_warnings
            if plan.status == "warning"
            else ExitCode.output_or_reference_validation_failed
        )
    if args.import_review:
        try:
            json_path, md_path, handoff_path, review = import_fcpxml_import_review(
                root=root,
                project_id=config.project.id,
                candidate_path=Path(args.import_review),
            )
        except FcpxmlWriterError as exc:
            print(str(exc), file=sys.stderr)
            return int(ExitCode.output_or_reference_validation_failed)
        if state is not None:
            run_id = new_run_id()
            status = (
                StepStatus.completed
                if review.status == "accepted"
                else StepStatus.completed_with_warnings
                if review.status == "warning"
                else StepStatus.failed
            )
            state.steps["fcpxml_import_review"] = StepLedgerEntry(
                status=status,
                output_refs=[
                    json_path.relative_to(root).as_posix(),
                    md_path.relative_to(root).as_posix(),
                    handoff_path.relative_to(root).as_posix(),
                ],
                last_run_id=run_id,
                warnings=review.warnings + review.rejected_reasons,
            )
            state.latest_run_id = run_id
            state.updated_at = utc_now()
            runs_dir = root / ".artist-portrait" / "runs" / run_id
            runs_dir.mkdir(parents=True, exist_ok=True)
            write_json(
                runs_dir / "command.json",
                {
                    "command": "fcpxml",
                    "project": str(project_path),
                    "import_review": str(args.import_review),
                },
            )
            write_json(runs_dir / "environment.json", environment_snapshot())
            write_json(
                runs_dir / "step_result.json",
                {
                    "step": "fcpxml_import_review",
                    "status": status.value,
                    "output_refs": state.steps["fcpxml_import_review"].output_refs,
                    "commands_executed": False,
                    "media_rendered": False,
                    "timeline_mutated": False,
                    "edit_points_moved": False,
                    "automatic_music_selection": False,
                    "automatic_bgm_fit": False,
                    "model_call_performed": False,
                    "network_performed": False,
                    "image_generation_or_editing_used": False,
                    "import_success_accepted_as_project_success": False,
                },
            )
            save_state(root, state)
            write_run_report(root / config.paths.output_dir, state, [])
        payload = {
            "output": json_path.relative_to(root).as_posix(),
            "report": md_path.relative_to(root).as_posix(),
            "handoff": handoff_path.relative_to(root).as_posix(),
            "status": review.status,
            "fcpxml_import_review": review.model_dump(mode="json"),
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        elif not args.quiet:
            print(f"fcpxml import-review {review.status}")
            print(f"wrote {payload['report']}")
        return int(
            ExitCode.success
            if review.status == "accepted"
            else ExitCode.success_with_warnings
            if review.status == "warning"
            else ExitCode.output_or_reference_validation_failed
        )
    try:
        (
            draft_json_path,
            fcpxml_path,
            validation_path,
            review_path,
            handoff_path,
            draft,
            validation,
        ) = build_fcpxml_draft(
            root=root,
            project_id=config.project.id,
            draft=args.draft,
        )
    except FcpxmlWriterError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    if state is not None:
        run_id = new_run_id()
        status = (
            StepStatus.completed
            if draft.status == "ready"
            else StepStatus.completed_with_warnings
            if draft.status == "warning"
            else StepStatus.failed
        )
        state.steps["fcpxml_draft"] = StepLedgerEntry(
            status=status,
            output_refs=[
                draft_json_path.relative_to(root).as_posix(),
                fcpxml_path.relative_to(root).as_posix(),
                validation_path.relative_to(root).as_posix(),
                review_path.relative_to(root).as_posix(),
                handoff_path.relative_to(root).as_posix(),
            ],
            last_run_id=run_id,
            warnings=draft.warnings + draft.blocked_reasons + validation.errors,
        )
        state.latest_run_id = run_id
        state.updated_at = utc_now()
        runs_dir = root / ".artist-portrait" / "runs" / run_id
        runs_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            runs_dir / "command.json",
            {"command": "fcpxml", "project": str(project_path), "draft": args.draft},
        )
        write_json(runs_dir / "environment.json", environment_snapshot())
        write_json(
            runs_dir / "step_result.json",
            {
                "step": "fcpxml_draft",
                "status": status.value,
                "output_refs": state.steps["fcpxml_draft"].output_refs,
                "commands_executed": False,
                "media_rendered": False,
                "timeline_mutated": False,
                "edit_points_moved": False,
                "nle_import_performed": False,
                "automatic_music_selection": False,
                "automatic_bgm_fit": False,
                "model_call_performed": False,
                "network_performed": False,
                "image_generation_or_editing_used": False,
            },
        )
        save_state(root, state)
        write_run_report(root / config.paths.output_dir, state, [])
    payload = {
        "output": draft_json_path.relative_to(root).as_posix(),
        "fcpxml": fcpxml_path.relative_to(root).as_posix(),
        "validation": validation_path.relative_to(root).as_posix(),
        "report": review_path.relative_to(root).as_posix(),
        "handoff": handoff_path.relative_to(root).as_posix(),
        "status": draft.status,
        "fcpxml_draft": draft.model_dump(mode="json"),
        "fcpxml_validation": validation.model_dump(mode="json"),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"fcpxml {draft.status}")
        print(f"wrote {payload['fcpxml']}")
        print(f"wrote {payload['report']}")
    return int(ExitCode.success if draft.status == "ready" else ExitCode.success_with_warnings)


def cmd_rhythm(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    selected_modes = sum(bool(item) for item in (args.qc, args.repair_plan, args.edit_guidance))
    if selected_modes > 1:
        print("rhythm --qc, --repair-plan, and --edit-guidance are mutually exclusive", file=sys.stderr)
        return int(ExitCode.invalid_cli_usage)
    project_path = Path(args.project)
    try:
        config = load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    root = project_root(project_path)
    try:
        if args.repair_plan:
            json_path, md_path, handoff_path, result = build_rhythm_repair_plan(
                root=root,
                project_id=config.project.id,
                acceptance_profile=args.acceptance_profile,
            )
        elif args.edit_guidance:
            json_path, md_path, handoff_path, result = build_edit_guidance(
                root=root,
                project_id=config.project.id,
            )
        elif args.qc:
            json_path, md_path, handoff_path, result = build_rhythm_media_qc(
                root=root,
                project_id=config.project.id,
            )
        else:
            json_path, md_path, handoff_path, result = build_rhythm_plan(
                root=root,
                project_id=config.project.id,
                intent_path=Path(args.intent) if args.intent else None,
                agent_output_path=Path(args.agent_output) if args.agent_output else None,
            )
    except (RhythmError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    state = load_state(root)
    if state is not None:
        run_id = new_run_id()
        if args.repair_plan:
            warnings = [
                action.rationale
                for action in result.actions
                if action.severity == "optional"
            ]
            errors = [
                action.rationale
                for action in result.actions
                if action.severity == "required"
            ]
        elif args.edit_guidance:
            warnings = [
                action.rationale
                for action in result.actions
                if action.priority == "high"
            ]
            errors = []
        else:
            domains = (
                [
                    result.preview_binding,
                    result.final_export_binding,
                    result.timeline_freshness,
                    result.bgm_freshness,
                    result.preview_duration_qc,
                    result.final_duration_qc,
                    result.audio_expectation_qc,
                    result.ducking_render_qc,
                    result.ending_render_qc,
                    result.media_qc_summary,
                ]
                if args.qc
                else [
                    result.timeline_profile,
                    result.bgm_profile,
                    result.compatibility_audit,
                    result.intent_audit,
                    result.cut_cue_audit,
                    result.transition_audit,
                    result.text_audit,
                    result.ducking_silence_audit,
                    result.ending_audit,
                ]
            )
            warnings = [
                issue.detail
                for domain in domains
                for issue in domain.issues
                if issue.severity == "warning"
            ]
            errors = [
                issue.detail
                for domain in domains
                for issue in domain.issues
                if issue.severity == "error"
            ]
        if (
            not args.qc
            and not args.repair_plan
            and not args.edit_guidance
            and result.agent_candidate_audit
        ):
            warnings.extend(
                issue.detail
                for issue in result.agent_candidate_audit.issues
                if issue.severity == "warning"
            )
            errors.extend(
                issue.detail
                for issue in result.agent_candidate_audit.issues
                if issue.severity == "error"
            )
        status = (
            StepStatus.failed
            if result.status == "blocked"
            else StepStatus.completed_with_warnings
            if result.status == "warning"
            else StepStatus.completed
        )
        state.steps["rhythm"] = StepLedgerEntry(
            status=status,
            output_refs=[
                json_path.relative_to(root).as_posix(),
                md_path.relative_to(root).as_posix(),
                handoff_path.relative_to(root).as_posix(),
            ],
            last_run_id=run_id,
            warnings=warnings,
        )
        state.latest_run_id = run_id
        state.updated_at = utc_now()
        runs_dir = root / ".artist-portrait" / "runs" / run_id
        runs_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            runs_dir / "command.json",
            {
                "command": "rhythm",
                "project": str(project_path),
                "intent": str(args.intent) if args.intent else None,
                "agent_output": str(args.agent_output) if args.agent_output else None,
                "qc": bool(args.qc),
                "repair_plan": bool(args.repair_plan),
                "edit_guidance": bool(args.edit_guidance),
                "acceptance_profile": args.acceptance_profile,
            },
        )
        write_json(runs_dir / "environment.json", environment_snapshot())
        write_json(
            runs_dir / "step_result.json",
            {
                "step": "rhythm",
                "status": status.value,
                "output_refs": state.steps["rhythm"].output_refs,
                "edit_points_moved": False,
                "automatic_music_selection": False,
                "media_rendered": False,
                "model_call_performed": False,
                "network_performed": False,
                "commands_executed": False,
            },
        )
        write_json(runs_dir / "warnings.json", warnings)
        write_json(runs_dir / "errors.json", errors)
        save_state(root, state)
        write_run_report(root / config.paths.output_dir, state, warnings)
    payload = {
        "output": json_path.relative_to(root).as_posix(),
        "report": md_path.relative_to(root).as_posix(),
        "handoff": handoff_path.relative_to(root).as_posix(),
        "status": result.status,
    }
    if args.qc:
        payload["rhythm_media_qc"] = result.model_dump(mode="json")
    elif args.repair_plan:
        payload["rhythm_repair_plan"] = result.model_dump(mode="json")
    elif args.edit_guidance:
        payload["edit_guidance"] = result.model_dump(mode="json")
    else:
        payload["rhythm_plan"] = result.model_dump(mode="json")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"rhythm {result.status}")
        print(f"wrote {payload['report']}")
        print(f"wrote {payload['handoff']}")
    if result.status == "blocked":
        return int(ExitCode.output_or_reference_validation_failed)
    return int(ExitCode.success_with_warnings if result.status == "warning" else ExitCode.success)


def cmd_acceptance(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        config = load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    root = project_root(project_path)
    state = load_state(root)
    json_path, md_path, report = build_project_acceptance_report(
        root=root,
        project_id=config.project.id,
        state=state,
        profile=args.profile,
    )
    repair_json_path = None
    repair_md_path = None
    repair_plan = None
    approval_request_json_path = None
    approval_request_md_path = None
    approval_request = None
    approval_record_json_path = None
    approval_record_md_path = None
    approval_record = None
    dry_run_json_path = None
    dry_run_md_path = None
    dry_run = None
    bundle_json_path = None
    bundle_md_path = None
    bundle = None
    execution_record_json_path = None
    execution_record_md_path = None
    execution_record = None
    if (
        args.repair_plan
        or args.approval_request
        or args.approval_record
        or args.execution_dry_run
        or args.execution_bundle
        or args.execution_record
    ):
        repair_json_path, repair_md_path, repair_plan = build_acceptance_repair_plan(
            root=root,
            report=report,
        )
    if args.approval_request and repair_plan:
        (
            approval_request_json_path,
            approval_request_md_path,
            approval_request,
        ) = build_acceptance_repair_approval_request(root=root, plan=repair_plan)
    if args.approval_record and repair_plan:
        try:
            (
                approval_record_json_path,
                approval_record_md_path,
                approval_record,
            ) = import_acceptance_repair_approval_record(
                root=root,
                plan=repair_plan,
                candidate_path=Path(args.approval_record),
            )
        except Exception as exc:
            print(str(exc), file=sys.stderr)
            return int(ExitCode.output_or_reference_validation_failed)
    if args.execution_dry_run and repair_plan:
        if approval_record is None:
            record_path = root / ".artist-portrait" / "data" / "acceptance_repair_approval_record.json"
            if not record_path.exists():
                print("execution dry-run requires a current acceptance repair approval record", file=sys.stderr)
                return int(ExitCode.output_or_reference_validation_failed)
            try:
                approval_record = AcceptanceRepairApprovalRecord.model_validate_json(
                    record_path.read_text(encoding="utf-8")
                )
            except Exception as exc:
                print(str(exc), file=sys.stderr)
                return int(ExitCode.output_or_reference_validation_failed)
        dry_run_json_path, dry_run_md_path, dry_run = build_acceptance_repair_execution_dry_run(
            root=root,
            plan=repair_plan,
            approval_record=approval_record,
        )
    if (args.execution_bundle or args.execution_record) and repair_plan:
        if dry_run is None:
            dry_run_path = root / ".artist-portrait" / "data" / "acceptance_repair_execution_dry_run.json"
            if not dry_run_path.exists():
                print("execution bundle/record requires a current acceptance repair execution dry-run", file=sys.stderr)
                return int(ExitCode.output_or_reference_validation_failed)
            try:
                dry_run = AcceptanceRepairExecutionDryRun.model_validate_json(
                    dry_run_path.read_text(encoding="utf-8")
                )
            except Exception as exc:
                print(str(exc), file=sys.stderr)
                return int(ExitCode.output_or_reference_validation_failed)
    if args.execution_bundle and repair_plan and dry_run:
        bundle_json_path, bundle_md_path, bundle = build_acceptance_repair_execution_bundle(
            root=root,
            plan=repair_plan,
            dry_run=dry_run,
        )
    if args.execution_record and dry_run:
        try:
            (
                execution_record_json_path,
                execution_record_md_path,
                execution_record,
            ) = import_acceptance_repair_execution_record(
                root=root,
                dry_run=dry_run,
                candidate_path=Path(args.execution_record),
            )
        except Exception as exc:
            print(str(exc), file=sys.stderr)
            return int(ExitCode.output_or_reference_validation_failed)
    if state is not None:
        run_id = new_run_id()
        warnings = [
            item.detail
            for stage in report.stages
            for item in stage.issues
            if item.severity == "warning"
        ]
        errors = [
            item.detail
            for stage in report.stages
            for item in stage.issues
            if item.severity == "error"
        ]
        status = (
            StepStatus.failed
            if report.status == "failed"
            else StepStatus.completed_with_warnings
            if report.status == "warning"
            else StepStatus.completed
        )
        state.steps["acceptance"] = StepLedgerEntry(
            status=status,
            output_refs=[
                json_path.relative_to(root).as_posix(),
                md_path.relative_to(root).as_posix(),
                *(
                    [
                        repair_json_path.relative_to(root).as_posix(),
                        repair_md_path.relative_to(root).as_posix(),
                    ]
                    if repair_json_path and repair_md_path
                    else []
                ),
                *(
                    [
                        approval_request_json_path.relative_to(root).as_posix(),
                        approval_request_md_path.relative_to(root).as_posix(),
                    ]
                    if approval_request_json_path and approval_request_md_path
                    else []
                ),
                *(
                    [
                        approval_record_json_path.relative_to(root).as_posix(),
                        approval_record_md_path.relative_to(root).as_posix(),
                    ]
                    if approval_record_json_path and approval_record_md_path
                    else []
                ),
                *(
                    [
                        dry_run_json_path.relative_to(root).as_posix(),
                        dry_run_md_path.relative_to(root).as_posix(),
                    ]
                    if dry_run_json_path and dry_run_md_path
                    else []
                ),
                *(
                    [
                        bundle_json_path.relative_to(root).as_posix(),
                        bundle_md_path.relative_to(root).as_posix(),
                    ]
                    if bundle_json_path and bundle_md_path
                    else []
                ),
                *(
                    [
                        execution_record_json_path.relative_to(root).as_posix(),
                        execution_record_md_path.relative_to(root).as_posix(),
                    ]
                    if execution_record_json_path and execution_record_md_path
                    else []
                ),
            ],
            last_run_id=run_id,
            warnings=warnings,
        )
        state.latest_run_id = run_id
        state.updated_at = utc_now()
        state.overall_status = (
            OverallStatus.blocked
            if report.status == "failed"
            else OverallStatus.degraded
            if report.status == "warning"
            else OverallStatus.ready
        )
        runs_dir = root / ".artist-portrait" / "runs" / run_id
        runs_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            runs_dir / "command.json",
            {
                "command": "acceptance",
                "project": str(project_path),
                "profile": args.profile,
                "repair_plan": bool(args.repair_plan),
                "approval_request": bool(args.approval_request),
                "approval_record": str(args.approval_record) if args.approval_record else None,
                "execution_dry_run": bool(args.execution_dry_run),
                "execution_bundle": bool(args.execution_bundle),
                "execution_record": str(args.execution_record) if args.execution_record else None,
            },
        )
        write_json(runs_dir / "environment.json", environment_snapshot())
        write_json(
            runs_dir / "step_result.json",
            {
                "step": "acceptance",
                "status": status.value,
                "output_refs": state.steps["acceptance"].output_refs,
                "network_performed": False,
                "model_call_performed": False,
                "media_rendered": False,
                "automatic_repair_performed": False,
                "approval_record_valid": approval_record.valid if approval_record else None,
                "commands_executed": False,
                "execution_bundle_blocked": bundle.blocked if bundle else None,
                "execution_record_valid": execution_record.valid if execution_record else None,
            },
        )
        write_json(runs_dir / "warnings.json", warnings)
        write_json(runs_dir / "errors.json", errors)
        save_state(root, state)
        write_run_report(root / config.paths.output_dir, state, warnings)
    payload = {
        "output": json_path.relative_to(root).as_posix(),
        "report": md_path.relative_to(root).as_posix(),
        "status": report.status,
        "profile": report.acceptance_profile,
        "profile_passed": report.profile_passed,
        "required_stage_ids": report.required_stage_ids,
        "core_ready": report.core_ready,
        "preview_ready": report.preview_ready,
        "final_export_ready": report.final_export_ready,
        "acceptance": report.model_dump(mode="json"),
    }
    if repair_json_path and repair_md_path and repair_plan:
        payload["repair_plan_output"] = repair_json_path.relative_to(root).as_posix()
        payload["repair_plan_report"] = repair_md_path.relative_to(root).as_posix()
        payload["repair_plan"] = repair_plan.model_dump(mode="json")
    if approval_request_json_path and approval_request_md_path and approval_request:
        payload["approval_request_output"] = approval_request_json_path.relative_to(root).as_posix()
        payload["approval_request_report"] = approval_request_md_path.relative_to(root).as_posix()
        payload["approval_request"] = approval_request.model_dump(mode="json")
    if approval_record_json_path and approval_record_md_path and approval_record:
        payload["approval_record_output"] = approval_record_json_path.relative_to(root).as_posix()
        payload["approval_record_report"] = approval_record_md_path.relative_to(root).as_posix()
        payload["approval_record"] = approval_record.model_dump(mode="json")
    if dry_run_json_path and dry_run_md_path and dry_run:
        payload["execution_dry_run_output"] = dry_run_json_path.relative_to(root).as_posix()
        payload["execution_dry_run_report"] = dry_run_md_path.relative_to(root).as_posix()
        payload["execution_dry_run"] = dry_run.model_dump(mode="json")
    if bundle_json_path and bundle_md_path and bundle:
        payload["execution_bundle_output"] = bundle_json_path.relative_to(root).as_posix()
        payload["execution_bundle_report"] = bundle_md_path.relative_to(root).as_posix()
        payload["execution_bundle"] = bundle.model_dump(mode="json")
    if execution_record_json_path and execution_record_md_path and execution_record:
        payload["execution_record_output"] = execution_record_json_path.relative_to(root).as_posix()
        payload["execution_record_report"] = execution_record_md_path.relative_to(root).as_posix()
        payload["execution_record"] = execution_record.model_dump(mode="json")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"acceptance {report.acceptance_profile} {report.status}")
        print(f"wrote {payload['report']}")
        if repair_json_path and repair_md_path:
            print(f"wrote {repair_md_path.relative_to(root).as_posix()}")
        if approval_request_md_path:
            print(f"wrote {approval_request_md_path.relative_to(root).as_posix()}")
        if approval_record_md_path:
            print(f"wrote {approval_record_md_path.relative_to(root).as_posix()}")
        if dry_run_md_path:
            print(f"wrote {dry_run_md_path.relative_to(root).as_posix()}")
        if bundle_md_path:
            print(f"wrote {bundle_md_path.relative_to(root).as_posix()}")
        if execution_record_md_path:
            print(f"wrote {execution_record_md_path.relative_to(root).as_posix()}")
    if report.status == "failed":
        return int(ExitCode.output_or_reference_validation_failed)
    return int(ExitCode.success_with_warnings if report.status == "warning" else ExitCode.success)


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
    project_path = Path(args.project)
    try:
        load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    try:
        if args.scope == "proposal":
            validation_path, report_path, _state, warnings, issues = review_proposal_workspace(
                project_path
            )
            root = project_root(project_path)
            payload = {
                "output": report_path.relative_to(root).as_posix(),
                "validation": validation_path.relative_to(root).as_posix(),
                "warnings": warnings,
                "issues": issues,
            }
        elif args.scope == "timeline":
            validation_path, report_path, _state, warnings, issues = (
                review_timeline_workspace(project_path)
            )
            root = project_root(project_path)
            payload = {
                "output": report_path.relative_to(root).as_posix(),
                "validation": validation_path.relative_to(root).as_posix(),
                "warnings": warnings,
                "issues": issues,
            }
        elif args.scope == "preview":
            validation_path, report_path, _state, warnings, issues = (
                review_preview_workspace(project_path)
            )
            root = project_root(project_path)
            payload = {
                "output": report_path.relative_to(root).as_posix(),
                "validation": validation_path.relative_to(root).as_posix(),
                "warnings": warnings,
                "issues": issues,
            }
        elif args.scope == "final_export":
            validation_path, report_path, _state, warnings, issues = (
                review_final_export_workspace(project_path)
            )
            root = project_root(project_path)
            payload = {
                "output": report_path.relative_to(root).as_posix(),
                "validation": validation_path.relative_to(root).as_posix(),
                "warnings": warnings,
                "issues": issues,
            }
        else:
            output_path, _state, warnings, issues = review_project_workspace(
                project_path,
                scope=args.scope,
            )
            root = project_root(project_path)
            payload = {
                "output": output_path.relative_to(root).as_posix(),
                "warnings": warnings,
                "issues": issues,
            }
    except WorkspacePrerequisiteError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.prerequisite_step_missing)
    except SourceLedgerError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    except WorkspaceTimelineError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    except WorkspacePreviewError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"wrote {payload['output']}")
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_timeline(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    try:
        timeline_path, validation_path, review_path, state, warnings, issues = (
            timeline_workspace(project_path, proposal_id=args.proposal)
        )
    except WorkspacePrerequisiteError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.prerequisite_step_missing)
    except (WorkspaceTimelineError, SourceLedgerError) as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    payload = {
        "output": timeline_path.relative_to(root).as_posix(),
        "validation": validation_path.relative_to(root).as_posix(),
        "review": review_path.relative_to(root).as_posix(),
        "proposal": args.proposal,
        "status": state.steps["timeline"].status.value,
        "warnings": warnings,
        "issues": issues,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"wrote {payload['output']}")
        print(f"wrote {payload['review']}")
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_preview(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    try:
        preview_path, manifest_path, validation_path, review_path, state, warnings, issues = (
            preview_workspace(project_path, width=args.width, fps=args.fps)
        )
    except WorkspacePrerequisiteError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.prerequisite_step_missing)
    except (WorkspacePreviewError, SourceLedgerError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    payload = {
        "output": preview_path.relative_to(root).as_posix(),
        "manifest": manifest_path.relative_to(root).as_posix(),
        "validation": validation_path.relative_to(root).as_posix(),
        "review": review_path.relative_to(root).as_posix(),
        "status": state.steps["preview"].status.value,
        "warnings": warnings,
        "issues": issues,
        "final_export": False,
        "network_performed": False,
        "model_call_performed": False,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"wrote {payload['output']}")
        print(f"wrote {payload['review']}")
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_export(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    try:
        export_path, manifest_path, validation_path, review_path, state, warnings, issues = (
            final_export_workspace(project_path, profile=args.profile)
        )
    except WorkspacePrerequisiteError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.prerequisite_step_missing)
    except (WorkspacePreviewError, SourceLedgerError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    payload = {
        "output": export_path.relative_to(root).as_posix(),
        "manifest": manifest_path.relative_to(root).as_posix(),
        "validation": validation_path.relative_to(root).as_posix(),
        "review": review_path.relative_to(root).as_posix(),
        "profile": args.profile,
        "status": state.steps["final_export"].status.value,
        "warnings": warnings,
        "issues": issues,
        "final_export": True,
        "automatic_music_selection": False,
        "network_performed": False,
        "model_call_performed": False,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"wrote {payload['output']}")
        print(f"wrote {payload['review']}")
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_bgm(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        config = load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    if not config.content_policy.allow_music:
        print("BGM operations are disabled by content_policy.allow_music", file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        print("bgm requires init to complete first", file=sys.stderr)
        return int(ExitCode.prerequisite_step_missing)
    try:
        if args.action == "import":
            ledger, candidate = import_candidate(
                root=root,
                project_id=config.project.id,
                file_ref=args.file,
                source_id=args.source_id,
                extract_in=args.extract_in,
                extract_out=args.extract_out,
                stream_index=args.stream_index,
                rights_status=RightsStatus(args.rights_status),
                user_intent=args.intent,
            )
            payload = {
                "candidate": candidate.model_dump(mode="json"),
                "candidate_count": len(ledger.candidates),
                "output": ".artist-portrait/data/bgm_candidates.json",
            }
            step_name = "bgm_import"
            output_refs = [
                ".artist-portrait/data/bgm_candidates.json",
                candidate.cache_ref,
            ]
            warnings = [candidate.beat_analysis_reason] if candidate.beat_analysis_reason else []
            existing_analysis = state.steps.get("bgm_analyze")
            if existing_analysis and existing_analysis.status in {
                StepStatus.completed,
                StepStatus.completed_with_warnings,
            }:
                state.steps["bgm_analyze"] = StepLedgerEntry(
                    status=StepStatus.invalidated,
                    input_fingerprint=existing_analysis.input_fingerprint,
                    output_refs=existing_analysis.output_refs,
                    last_run_id=existing_analysis.last_run_id,
                    warnings=[*existing_analysis.warnings, "BGM candidate ledger changed"],
                )
            existing_fit = state.steps.get("bgm_fit")
            if existing_fit and existing_fit.status in {
                StepStatus.completed,
                StepStatus.completed_with_warnings,
            }:
                state.steps["bgm_fit"] = StepLedgerEntry(
                    status=StepStatus.invalidated,
                    input_fingerprint=existing_fit.input_fingerprint,
                    output_refs=existing_fit.output_refs,
                    last_run_id=existing_fit.last_run_id,
                    warnings=[*existing_fit.warnings, "BGM candidate ledger changed"],
                )
            existing_preview = state.steps.get("preview")
            if existing_preview and existing_preview.status in {
                StepStatus.completed,
                StepStatus.completed_with_warnings,
            }:
                state.steps["preview"] = StepLedgerEntry(
                    status=StepStatus.invalidated,
                    input_fingerprint=existing_preview.input_fingerprint,
                    output_refs=existing_preview.output_refs,
                    last_run_id=existing_preview.last_run_id,
                    warnings=[*existing_preview.warnings, "BGM candidate ledger changed"],
                )
            existing_review = state.steps.get("review_preview")
            if existing_review and existing_review.status in {
                StepStatus.completed,
                StepStatus.completed_with_warnings,
            }:
                state.steps["review_preview"] = StepLedgerEntry(
                    status=StepStatus.invalidated,
                    input_fingerprint=existing_review.input_fingerprint,
                    output_refs=existing_review.output_refs,
                    last_run_id=existing_review.last_run_id,
                    warnings=[*existing_review.warnings, "BGM candidate ledger changed"],
                )
            for dependent_step in ("final_export", "review_final_export"):
                existing_export = state.steps.get(dependent_step)
                if existing_export and existing_export.status in {
                    StepStatus.completed,
                    StepStatus.completed_with_warnings,
                }:
                    state.steps[dependent_step] = StepLedgerEntry(
                        status=StepStatus.invalidated,
                        input_fingerprint=existing_export.input_fingerprint,
                        output_refs=existing_export.output_refs,
                        last_run_id=existing_export.last_run_id,
                        warnings=[
                            *existing_export.warnings,
                            "BGM candidate ledger changed",
                        ],
                    )
        elif args.action == "list":
            ledger = load_ledger(
                root / ".artist-portrait" / "data" / "bgm_candidates.json",
                config.project.id,
            )
            payload = ledger.model_dump(mode="json")
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
            elif not args.quiet:
                for candidate in ledger.candidates:
                    print(f"{candidate.music_candidate_id} {candidate.input_mode.value} {candidate.duration:.3f}s")
            return int(ExitCode.success)
        elif args.action == "analyze":
            report = analyze_candidates(
                root=root,
                project_id=config.project.id,
                window_seconds=args.window_seconds,
            )
            report_ref = "output/bgm_analysis_report.md"
            report_path = root / report_ref
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(render_bgm_analysis_report(report) + "\n", encoding="utf-8")
            payload = {
                "analysis": report.model_dump(mode="json"),
                "output": ".artist-portrait/data/bgm_analysis.json",
                "report": report_ref,
            }
            step_name = "bgm_analyze"
            output_refs = [".artist-portrait/data/bgm_analysis.json", report_ref]
            warnings = [
                warning
                for candidate in report.candidates
                for warning in candidate.warnings
            ]
            for dependent in (
                "bgm_fit",
                "preview",
                "review_preview",
                "final_export",
                "review_final_export",
            ):
                existing = state.steps.get(dependent)
                if existing and existing.status in {
                    StepStatus.completed,
                    StepStatus.completed_with_warnings,
                }:
                    state.steps[dependent] = StepLedgerEntry(
                        status=StepStatus.invalidated,
                        input_fingerprint=existing.input_fingerprint,
                        output_refs=existing.output_refs,
                        last_run_id=existing.last_run_id,
                        warnings=[*existing.warnings, "BGM analysis changed"],
                        )
        elif args.action == "rhythm":
            json_path, md_path, handoff_path, report = build_bgm_rhythm_intelligence(
                root=root,
                project_id=config.project.id,
            )
            payload = {
                "bgm_rhythm_intelligence": report.model_dump(mode="json"),
                "output": json_path.relative_to(root).as_posix(),
                "report": md_path.relative_to(root).as_posix(),
                "handoff": handoff_path.relative_to(root).as_posix(),
                "status": report.status,
            }
            step_name = "bgm_rhythm"
            output_refs = [
                json_path.relative_to(root).as_posix(),
                md_path.relative_to(root).as_posix(),
                handoff_path.relative_to(root).as_posix(),
            ]
            warnings = [
                warning
                for candidate in report.candidates
                for warning in candidate.warnings
            ]
            for dependent in (
                "rhythm",
                "rhythm_qc",
                "rhythm_repair_plan",
                "preview",
                "review_preview",
                "final_export",
                "review_final_export",
            ):
                existing = state.steps.get(dependent)
                if existing and existing.status in {
                    StepStatus.completed,
                    StepStatus.completed_with_warnings,
                }:
                    state.steps[dependent] = StepLedgerEntry(
                        status=StepStatus.invalidated,
                        input_fingerprint=existing.input_fingerprint,
                        output_refs=existing.output_refs,
                        last_run_id=existing.last_run_id,
                        warnings=[*existing.warnings, "BGM rhythm intelligence changed"],
                    )
        elif args.action == "recommend":
            if args.agent_output:
                recommendation_path, review_path, validation = import_bgm_recommendation_candidate(
                    root=root,
                    project_id=config.project.id,
                    candidate_path=Path(args.agent_output),
                )
                payload = {
                    "output": recommendation_path.relative_to(root).as_posix(),
                    "review": review_path.relative_to(root).as_posix(),
                    "validation": validation.model_dump(mode="json"),
                }
                step_name = "bgm_recommend"
                output_refs = [
                    recommendation_path.relative_to(root).as_posix(),
                    review_path.relative_to(root).as_posix(),
                    ".artist-portrait/data/bgm_recommendation_validation.json",
                ]
                warnings = [issue.detail for issue in validation.issues if issue.severity == "warning"]
                state.steps["review_bgm_recommendation"] = StepLedgerEntry(
                    status=StepStatus.completed_with_warnings if warnings else StepStatus.completed,
                    output_refs=[
                        review_path.relative_to(root).as_posix(),
                        ".artist-portrait/data/bgm_recommendation_validation.json",
                    ],
                    warnings=warnings,
                )
                for dependent in ("bgm_fit", "preview", "review_preview", "final_export", "review_final_export"):
                    existing = state.steps.get(dependent)
                    if existing and existing.status in {
                        StepStatus.completed,
                        StepStatus.completed_with_warnings,
                    }:
                        state.steps[dependent] = StepLedgerEntry(
                            status=StepStatus.invalidated,
                            input_fingerprint=existing.input_fingerprint,
                            output_refs=existing.output_refs,
                            last_run_id=existing.last_run_id,
                            warnings=[*existing.warnings, "BGM recommendation changed"],
                        )
            else:
                context_path, request_path, handoff_path = prepare_bgm_recommendation_handoff(
                    root=root,
                    project_id=config.project.id,
                )
                payload = {
                    "context": context_path.relative_to(root).as_posix(),
                    "request": request_path.relative_to(root).as_posix(),
                    "handoff": handoff_path.relative_to(root).as_posix(),
                    "next_command": "artist-portrait bgm recommend --project <project.yaml> --agent-output <candidate.json>",
                }
                step_name = "bgm_recommend"
                output_refs = [
                    context_path.relative_to(root).as_posix(),
                    request_path.relative_to(root).as_posix(),
                    handoff_path.relative_to(root).as_posix(),
                ]
                warnings = ["BGM recommendation handoff is ready; no recommendation imported yet"]
        elif args.action == "fit":
            if not args.candidate:
                raise BgmError("bgm fit requires --candidate")
            plan, timeline = build_fit_plan(
                root=root,
                project_id=config.project.id,
                candidate_id=args.candidate,
                requested_fit_mode=args.fit_mode,
                fade_in_seconds=args.fade_in_seconds,
                fade_out_seconds=args.fade_out_seconds,
                target_gain_db=args.target_gain_db,
                ducking_gain_db=args.ducking_gain_db,
                ducking_enabled=not args.no_ducking,
                beat_alignment_requested=args.beat_align,
            )
            payload = {
                "fit": plan.model_dump(mode="json"),
                "timeline": "output/timeline_draft.json",
                "output": ".artist-portrait/data/bgm_fit.json",
            }
            step_name = "bgm_fit"
            output_refs = [
                ".artist-portrait/data/bgm_fit.json",
                "output/timeline_draft.json",
            ]
            warnings = plan.warnings
            existing_preview = state.steps.get("preview")
            if existing_preview and existing_preview.status in {
                StepStatus.completed,
                StepStatus.completed_with_warnings,
            }:
                state.steps["preview"] = StepLedgerEntry(
                    status=StepStatus.invalidated,
                    input_fingerprint=existing_preview.input_fingerprint,
                    output_refs=existing_preview.output_refs,
                    last_run_id=existing_preview.last_run_id,
                    warnings=[*existing_preview.warnings, "BGM fit plan changed"],
                )
            existing_review = state.steps.get("review_preview")
            if existing_review and existing_review.status in {
                StepStatus.completed,
                StepStatus.completed_with_warnings,
            }:
                state.steps["review_preview"] = StepLedgerEntry(
                    status=StepStatus.invalidated,
                    input_fingerprint=existing_review.input_fingerprint,
                    output_refs=existing_review.output_refs,
                    last_run_id=existing_review.last_run_id,
                    warnings=[*existing_review.warnings, "BGM fit plan changed"],
                )
            for dependent_step in ("final_export", "review_final_export"):
                existing_export = state.steps.get(dependent_step)
                if existing_export and existing_export.status in {
                    StepStatus.completed,
                    StepStatus.completed_with_warnings,
                }:
                    state.steps[dependent_step] = StepLedgerEntry(
                        status=StepStatus.invalidated,
                        input_fingerprint=existing_export.input_fingerprint,
                        output_refs=existing_export.output_refs,
                        last_run_id=existing_export.last_run_id,
                        warnings=[*existing_export.warnings, "BGM fit plan changed"],
                    )
        elif args.action == "select":
            selection, _item = select_bgm_recommendation_for_fit(
                root=root,
                project_id=config.project.id,
                recommendation_id=args.recommendation_id,
                rank=args.rank,
            )
            plan, timeline = build_fit_plan(
                root=root,
                project_id=config.project.id,
                candidate_id=selection.music_candidate_id,
                requested_fit_mode=args.fit_mode,
                fade_in_seconds=args.fade_in_seconds,
                fade_out_seconds=args.fade_out_seconds,
                target_gain_db=args.target_gain_db,
                ducking_gain_db=args.ducking_gain_db,
                ducking_enabled=not args.no_ducking,
                beat_alignment_requested=args.beat_align,
            )
            payload = {
                "selection": selection.model_dump(mode="json"),
                "fit": plan.model_dump(mode="json"),
                "timeline": "output/timeline_draft.json",
                "output": ".artist-portrait/data/bgm_recommendation_selection.json",
            }
            step_name = "bgm_select"
            output_refs = [
                ".artist-portrait/data/bgm_recommendation_selection.json",
                "output/bgm_recommendation_selection_review.md",
                ".artist-portrait/data/bgm_fit.json",
                "output/timeline_draft.json",
            ]
            warnings = plan.warnings
            existing_preview = state.steps.get("preview")
            if existing_preview and existing_preview.status in {
                StepStatus.completed,
                StepStatus.completed_with_warnings,
            }:
                state.steps["preview"] = StepLedgerEntry(
                    status=StepStatus.invalidated,
                    input_fingerprint=existing_preview.input_fingerprint,
                    output_refs=existing_preview.output_refs,
                    last_run_id=existing_preview.last_run_id,
                    warnings=[*existing_preview.warnings, "BGM recommendation selection changed"],
                )
            existing_review = state.steps.get("review_preview")
            if existing_review and existing_review.status in {
                StepStatus.completed,
                StepStatus.completed_with_warnings,
            }:
                state.steps["review_preview"] = StepLedgerEntry(
                    status=StepStatus.invalidated,
                    input_fingerprint=existing_review.input_fingerprint,
                    output_refs=existing_review.output_refs,
                    last_run_id=existing_review.last_run_id,
                    warnings=[*existing_review.warnings, "BGM recommendation selection changed"],
                )
            for dependent_step in ("final_export", "review_final_export"):
                existing_export = state.steps.get(dependent_step)
                if existing_export and existing_export.status in {
                    StepStatus.completed,
                    StepStatus.completed_with_warnings,
                }:
                    state.steps[dependent_step] = StepLedgerEntry(
                        status=StepStatus.invalidated,
                        input_fingerprint=existing_export.input_fingerprint,
                        output_refs=existing_export.output_refs,
                        last_run_id=existing_export.last_run_id,
                        warnings=[
                            *existing_export.warnings,
                            "BGM recommendation selection changed",
                        ],
                    )
        else:
            ledger = load_ledger(
                root / ".artist-portrait" / "data" / "bgm_candidates.json",
                config.project.id,
            )
            issues = review_bgm(root, config.project.id)
            review_json, review_md, report = review_bgm_recommendation_fit(
                root=root,
                project_id=config.project.id,
                bgm_issues=issues,
            )
            payload = {
                "issues": [item.model_dump(mode="json") for item in report.issues],
                "candidate_count": len(ledger.candidates),
                "review": review_md.relative_to(root).as_posix(),
                "output": review_json.relative_to(root).as_posix(),
                "status": report.status,
            }
            step_name = "review_bgm"
            output_refs = [
                review_json.relative_to(root).as_posix(),
                review_md.relative_to(root).as_posix(),
            ]
            warnings = [item.detail for item in report.issues]
    except (BgmError, BgmRecommendationError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    run_id = new_run_id()
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    state.steps[step_name] = StepLedgerEntry(
        status=status,
        output_refs=output_refs,
        last_run_id=run_id,
        warnings=warnings,
    )
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready
    runs_dir = root / ".artist-portrait" / "runs" / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        runs_dir / "command.json",
        {"command": "bgm", "action": args.action, "project": str(project_path)},
    )
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": step_name,
            "status": status.value,
            "output_refs": output_refs,
            "network_performed": False,
            "model_call_performed": False,
            "preview_rendered": False,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text(
        f"bgm {args.action} completed\n",
        encoding="utf-8",
    )
    save_state(root, state)
    write_run_report(root / config.paths.output_dir, state, warnings)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"bgm {args.action} completed")
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
        if args.agent_output:
            result = import_agent_proposal_workspace(
                project_path,
                Path(args.agent_output),
            )
            payload = {
                "output": result["proposals_ref"],
                "handoff": result["handoff_ref"],
                "quarantine": result["quarantine_ref"],
                "validation": result["validation_ref"],
                "review": result["review_ref"],
                "status": result["status"],
                "warnings": result["warnings"],
            }
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
            elif not args.quiet:
                print(f"wrote {payload['output']}")
                print(f"quarantined {payload['quarantine']}")
                print(f"wrote {payload['review']}")
            return int(
                ExitCode.success_with_warnings
                if result["warnings"]
                else ExitCode.success
            )
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
    except WorkspaceProposalCandidateError as exc:
        payload = {
            "error": str(exc),
            "error_code": exc.code,
            "quarantine": exc.quarantine_ref,
            "status": "failed",
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
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
        "release-check": cmd_release_check,
        "workflow": cmd_workflow,
        "operator": cmd_operator,
        "editor-package": cmd_editor_package,
        "nle-plan": cmd_nle_plan,
        "fcpxml": cmd_fcpxml,
        "acceptance": cmd_acceptance,
        "scan": cmd_scan,
        "segment": cmd_segment,
        "transcribe": cmd_transcribe,
        "keyframes": cmd_keyframes,
        "analyze": cmd_analyze,
        "map": cmd_map,
        "review": cmd_review,
        "propose": cmd_propose,
        "timeline": cmd_timeline,
        "preview": cmd_preview,
        "export": cmd_export,
        "rhythm": cmd_rhythm,
        "bgm": cmd_bgm,
    }
    handler = handlers.get(args.command, blocked_stage_a_command)
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
