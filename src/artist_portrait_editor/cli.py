from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from artist_portrait_editor.acceptance import build_project_acceptance_report
from artist_portrait_editor.aesthetic_baseline import (
    AestheticBaselineError,
    import_aesthetic_baseline,
    prepare_aesthetic_baseline_handoff,
)
from artist_portrait_editor.capabilities import detect_capabilities
from artist_portrait_editor.clip_scoring import ClipScoringError, score_workspace
from artist_portrait_editor.cleanup import cleanup_workspace
from artist_portrait_editor.composition import (
    CompositionEvidenceError,
    build_composition_evidence,
    import_composition_review,
    render_reframe_candidate_preview,
)
from artist_portrait_editor.edit_brief import EditBriefError, build_edit_brief_workspace
from artist_portrait_editor.evidence_fusion import EvidenceFusionError, build_evidence_map
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
from artist_portrait_editor.cut_review import (
    CutReviewError,
    build_cut_review_workspace,
)
from artist_portrait_editor.creative_strategies import CreativeStrategiesError, build_creative_strategy_package
from artist_portrait_editor.editor_package import EditorPackageError, build_editor_package
from artist_portrait_editor.editorial_scoring import EditorialScoringError, build_editorial_scores
from artist_portrait_editor.bgm_recommendation import (
    BgmRecommendationError,
    import_bgm_recommendation_candidate,
    prepare_bgm_recommendation_handoff,
    review_bgm_recommendation_fit,
    select_bgm_recommendation_for_fit,
)
from artist_portrait_editor.bgm_matching import BgmMatchingError, build_bgm_match
from artist_portrait_editor.benchmark_pack import BenchmarkPackError, build_benchmark_pack
from artist_portrait_editor.exit_codes import ExitCode
from artist_portrait_editor.final_export_workspace import (
    final_export_workspace,
    review_final_export_workspace,
)
from artist_portrait_editor.fcpxml_writer import (
    FcpxmlWriterError,
    build_fcpxml_draft,
    build_fcpxml_repair_plan,
    import_fcpxml_import_review,
)
from artist_portrait_editor.models.source import RightsStatus
from artist_portrait_editor.models.state import OverallStatus, StepLedgerEntry, StepStatus
from artist_portrait_editor.nle_interchange import (
    NleInterchangeError,
    build_nle_interchange_plan,
)
from artist_portrait_editor.nle_roundtrip import NleRoundTripError, build_nle_roundtrip_workspace
from artist_portrait_editor.operator_runbook import build_operator_runbook
from artist_portrait_editor.preview_workspace import (
    preview_workspace,
    review_preview_workspace,
)
from artist_portrait_editor.publishability import (
    PublishabilityError,
    build_publishability_workspace,
)
from artist_portrait_editor.release_hardening import (
    ReleaseHardeningError,
    build_release_hardening_report,
)
from artist_portrait_editor.revision import (
    RevisionPlanError,
    build_revision_plan_workspace,
)
from artist_portrait_editor.revision_application import (
    RevisionApplicationError,
    build_revision_application_workspace,
)
from artist_portrait_editor.revision_promotion import (
    RevisionPromotionError,
    build_revision_promotion_workspace,
)
from artist_portrait_editor.version_review import VersionReviewError, build_version_review_workspace
from artist_portrait_editor.sound_decision import (
    SoundDecisionError,
    build_sound_decision_workspace,
)
from artist_portrait_editor.structure_recommendation import StructureRecommendationError, build_structure_recommendation
from artist_portrait_editor.style_templates import StyleTemplatesError, build_style_template_package
from artist_portrait_editor.text_planning import TextPlanningError, build_text_plan
from artist_portrait_editor.first_cut_review import FirstCutReviewError, build_first_cut_self_review
from artist_portrait_editor.second_cut_render import SecondCutRenderError, render_second_cut
from artist_portrait_editor.second_cut import SecondCutError, build_second_cut_candidate
from artist_portrait_editor.reframe import ReframeError, apply_reframe_selection
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
    analyze_workspace,
    doctor_project_payload,
    init_workspace,
    import_agent_proposal_workspace,
    keyframes_workspace,
    map_workspace,
    propose_workspace,
    project_status_payload,
    render_doctor_panel,
    render_status_panel,
    review_proposal_workspace,
    review_project_workspace,
    review_timeline_workspace,
    scan_workspace,
    segment_workspace,
    transcribe_workspace,
    timeline_workspace,
)
from artist_portrait_editor.workspace_errors import (
    WorkspaceDependencyError,
    WorkspaceProposalCandidateError,
    WorkspacePreviewError,
    WorkspacePrerequisiteError,
    WorkspaceTimelineError,
)
from artist_portrait_editor.workspace_state import (
    load_state,
    project_root,
    save_state,
    state_as_dict,
    write_run_report,
)
from artist_portrait_editor.workflow import (
    WorkflowExecutionReviewError,
    build_workflow_plan,
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

    cleanup_sub = subparsers.add_parser("cleanup")
    cleanup_sub.add_argument("--project", required=True)
    cleanup_sub.add_argument("--json", action="store_true")
    cleanup_sub.add_argument("--quiet", action="store_true")
    cleanup_sub.add_argument("--verbose", action="store_true")

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

    nle_roundtrip_sub = subparsers.add_parser("nle-roundtrip")
    nle_roundtrip_sub.add_argument("--project", required=True)
    nle_roundtrip_sub.add_argument("--frame-rate", type=float, default=25.0)
    nle_roundtrip_sub.add_argument("--json", action="store_true")
    nle_roundtrip_sub.add_argument("--quiet", action="store_true")
    nle_roundtrip_sub.add_argument("--verbose", action="store_true")

    fcpxml_sub = subparsers.add_parser("fcpxml")
    fcpxml_sub.add_argument("--project", required=True)
    fcpxml_sub.add_argument("--draft", action="store_true")
    fcpxml_sub.add_argument("--import-review")
    fcpxml_sub.add_argument("--repair-plan", action="store_true")
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

    brief_sub = subparsers.add_parser("brief")
    brief_sub.add_argument("--project", required=True)
    brief_sub.add_argument("--target-duration-seconds", type=float)
    brief_sub.add_argument("--platform")
    brief_sub.add_argument("--json", action="store_true")
    brief_sub.add_argument("--quiet", action="store_true")
    brief_sub.add_argument("--verbose", action="store_true")

    score_sub = subparsers.add_parser("score")
    score_sub.add_argument("--project", required=True)
    score_sub.add_argument("--json", action="store_true")
    score_sub.add_argument("--quiet", action="store_true")
    score_sub.add_argument("--verbose", action="store_true")

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

    sound_sub = subparsers.add_parser("sound")
    sound_sub.add_argument("--project", required=True)
    sound_sub.add_argument("--json", action="store_true")
    sound_sub.add_argument("--quiet", action="store_true")
    sound_sub.add_argument("--verbose", action="store_true")

    cut_review_sub = subparsers.add_parser("cut-review")
    cut_review_sub.add_argument("--project", required=True)
    cut_review_sub.add_argument("--json", action="store_true")
    cut_review_sub.add_argument("--quiet", action="store_true")
    cut_review_sub.add_argument("--verbose", action="store_true")

    composition_sub = subparsers.add_parser("composition")
    composition_sub.add_argument("--project", required=True)
    composition_sub.add_argument("--samples", type=int, choices=(4, 6, 9), default=9)
    composition_sub.add_argument("--agent-output")
    composition_sub.add_argument("--preview-candidate")
    composition_sub.add_argument("--json", action="store_true")
    composition_sub.add_argument("--quiet", action="store_true")
    composition_sub.add_argument("--verbose", action="store_true")

    reframe_sub = subparsers.add_parser("reframe")
    reframe_sub.add_argument("--project", required=True)
    reframe_sub.add_argument("--selection", required=True)
    reframe_sub.add_argument("--json", action="store_true")
    reframe_sub.add_argument("--quiet", action="store_true")
    reframe_sub.add_argument("--verbose", action="store_true")

    evidence_map_sub = subparsers.add_parser("evidence-map")
    evidence_map_sub.add_argument("--project", required=True)
    evidence_map_sub.add_argument("--json", action="store_true")
    evidence_map_sub.add_argument("--quiet", action="store_true")
    evidence_map_sub.add_argument("--verbose", action="store_true")

    editorial_score_sub = subparsers.add_parser("editorial-score")
    editorial_score_sub.add_argument("--project", required=True)
    editorial_score_sub.add_argument("--json", action="store_true")
    editorial_score_sub.add_argument("--quiet", action="store_true")
    editorial_score_sub.add_argument("--verbose", action="store_true")
    structure_sub = subparsers.add_parser("structure-recommend")
    structure_sub.add_argument("--project", required=True); structure_sub.add_argument("--json", action="store_true"); structure_sub.add_argument("--quiet", action="store_true"); structure_sub.add_argument("--verbose", action="store_true")
    bgm_match_sub=subparsers.add_parser("bgm-match"); bgm_match_sub.add_argument("--project",required=True); bgm_match_sub.add_argument("--json",action="store_true"); bgm_match_sub.add_argument("--quiet",action="store_true"); bgm_match_sub.add_argument("--verbose",action="store_true")
    text_plan_sub = subparsers.add_parser("text-plan")
    text_plan_sub.add_argument("--project", required=True)
    text_plan_sub.add_argument("--json", action="store_true")
    text_plan_sub.add_argument("--quiet", action="store_true")
    text_plan_sub.add_argument("--verbose", action="store_true")
    first_cut_sub = subparsers.add_parser("first-cut-review")
    first_cut_sub.add_argument("--project", required=True)
    first_cut_sub.add_argument("--json", action="store_true")
    first_cut_sub.add_argument("--quiet", action="store_true")
    first_cut_sub.add_argument("--verbose", action="store_true")
    second_cut_render_sub = subparsers.add_parser("second-cut-render")
    second_cut_render_sub.add_argument("--project", required=True)
    second_cut_render_sub.add_argument("--option-id", required=True, choices=("short", "standard", "extended"))
    second_cut_render_sub.add_argument("--json", action="store_true")
    second_cut_render_sub.add_argument("--quiet", action="store_true")
    second_cut_render_sub.add_argument("--verbose", action="store_true")
    benchmark_pack_sub = subparsers.add_parser("benchmark-pack")
    benchmark_pack_sub.add_argument("--benchmark", action="append", required=True)
    benchmark_pack_sub.add_argument("--output-dir", required=True)
    benchmark_pack_sub.add_argument("--json", action="store_true")
    benchmark_pack_sub.add_argument("--quiet", action="store_true")
    benchmark_pack_sub.add_argument("--verbose", action="store_true")
    creative_strategies_sub = subparsers.add_parser("creative-strategies")
    creative_strategies_sub.add_argument("--project", required=True)
    creative_strategies_sub.add_argument("--json", action="store_true")
    creative_strategies_sub.add_argument("--quiet", action="store_true")
    creative_strategies_sub.add_argument("--verbose", action="store_true")
    style_templates_sub = subparsers.add_parser("style-templates")
    style_templates_sub.add_argument("--project", required=True)
    style_templates_sub.add_argument("--json", action="store_true")
    style_templates_sub.add_argument("--quiet", action="store_true")
    style_templates_sub.add_argument("--verbose", action="store_true")

    baseline_sub = subparsers.add_parser("baseline")
    baseline_sub.add_argument("--project", required=True)
    baseline_sub.add_argument("--agent-output")
    baseline_sub.add_argument("--json", action="store_true")
    baseline_sub.add_argument("--quiet", action="store_true")
    baseline_sub.add_argument("--verbose", action="store_true")

    second_cut_sub = subparsers.add_parser("second-cut")
    second_cut_sub.add_argument("--project", required=True)
    second_cut_sub.add_argument("--concept-id", required=True)
    second_cut_sub.add_argument("--json", action="store_true")
    second_cut_sub.add_argument("--quiet", action="store_true")
    second_cut_sub.add_argument("--verbose", action="store_true")

    revise_sub = subparsers.add_parser("revise")
    revise_sub.add_argument("--project", required=True)
    revise_sub.add_argument("--intent", required=True)
    revise_sub.add_argument(
        "--request-type",
        choices=(
            "shorter",
            "longer",
            "stronger_hook",
            "more_emotional",
            "keep_segment",
            "remove_segment",
            "change_ending",
            "reduce_subtitles",
            "reduce_bgm",
            "custom",
        ),
    )
    revise_sub.add_argument("--target-duration-seconds", type=float)
    revise_sub.add_argument("--keep-segment", action="append", default=[])
    revise_sub.add_argument("--remove-segment", action="append", default=[])
    revise_sub.add_argument("--json", action="store_true")
    revise_sub.add_argument("--quiet", action="store_true")
    revise_sub.add_argument("--verbose", action="store_true")

    apply_revision_sub = subparsers.add_parser("apply-revision")
    apply_revision_sub.add_argument("--project", required=True)
    apply_revision_sub.add_argument("--version-id", required=True)
    apply_revision_sub.add_argument("--action-id", action="append", default=[])
    apply_revision_sub.add_argument("--json", action="store_true")
    apply_revision_sub.add_argument("--quiet", action="store_true")
    apply_revision_sub.add_argument("--verbose", action="store_true")

    promote_revision_sub = subparsers.add_parser("promote-revision")
    promote_revision_sub.add_argument("--project", required=True)
    promote_revision_sub.add_argument("--revision-application-id", required=True)
    promote_revision_sub.add_argument("--json", action="store_true")
    promote_revision_sub.add_argument("--quiet", action="store_true")
    promote_revision_sub.add_argument("--verbose", action="store_true")

    version_review_sub = subparsers.add_parser("version-review")
    version_review_sub.add_argument("--project", required=True)
    version_review_sub.add_argument("--json", action="store_true")
    version_review_sub.add_argument("--quiet", action="store_true")
    version_review_sub.add_argument("--verbose", action="store_true")

    publishability_sub = subparsers.add_parser("publishability")
    publishability_sub.add_argument("--project", required=True)
    publishability_sub.add_argument("--json", action="store_true")
    publishability_sub.add_argument("--quiet", action="store_true")
    publishability_sub.add_argument("--verbose", action="store_true")

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


def cmd_cleanup(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)

    result = cleanup_workspace(project_root(project_path))
    payload = {
        "removed_cache_bytes": result.removed_cache_bytes,
        "removed_cache_files": result.removed_cache_files,
        "removed_temp_files": result.removed_temp_files,
        "preserved": ["media", "output", ".artist-portrait/data", ".artist-portrait/runs"],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(
            "cleanup removed "
            f"{result.removed_cache_files} cache files ({result.removed_cache_bytes} bytes)"
        )
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
            write_json(runs_dir / "command.json", {"command": "workflow", "project": str(project_path), "target": args.target, "execution_record": str(args.execution_record)})
            write_json(runs_dir / "environment.json", environment_snapshot())
            write_json(runs_dir / "step_result.json", {"step": "workflow_execution_review", "status": status.value, "output_refs": state.steps["workflow_execution_review"].output_refs, "commands_executed": False, "media_rendered": False, "edit_points_moved": False, "automatic_music_selection": False, "model_call_performed": False, "network_performed": False})
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
            print(f"wrote {payload[report]}")
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
            output_refs=[json_path.relative_to(root).as_posix(), md_path.relative_to(root).as_posix(), handoff_path.relative_to(root).as_posix()],
            last_run_id=run_id,
            warnings=[step.rationale for step in plan.steps if step.status in {"next", "blocked"}],
        )
        state.latest_run_id = run_id
        state.updated_at = utc_now()
        runs_dir = root / ".artist-portrait" / "runs" / run_id
        runs_dir.mkdir(parents=True, exist_ok=True)
        write_json(runs_dir / "command.json", {"command": "workflow", "project": str(project_path), "target": args.target})
        write_json(runs_dir / "environment.json", environment_snapshot())
        write_json(runs_dir / "step_result.json", {"step": "workflow", "status": status.value, "output_refs": state.steps["workflow"].output_refs, "commands_executed": False, "media_rendered": False, "edit_points_moved": False, "automatic_music_selection": False, "model_call_performed": False, "network_performed": False})
        save_state(root, state)
        write_run_report(root / config.paths.output_dir, state, [])
    payload = {"output": json_path.relative_to(root).as_posix(), "report": md_path.relative_to(root).as_posix(), "handoff": handoff_path.relative_to(root).as_posix(), "status": plan.status, "next_command": plan.next_command, "workflow_plan": plan.model_dump(mode="json")}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"workflow {plan.status}")
        print(f"next {plan.next_command or none}")
        print(f"wrote {payload[report]}")
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


def cmd_nle_roundtrip(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        json_path, md_path, package, warnings = build_nle_roundtrip_workspace(
            project_path, frame_rate=args.frame_rate
        )
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    except WorkspacePrerequisiteError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.prerequisite_step_missing)
    except (NleRoundTripError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    payload = {
        "output": json_path.relative_to(root).as_posix(),
        "report": md_path.relative_to(root).as_posix(),
        "status": package.status,
        "nle_roundtrip": package.model_dump(mode="json"),
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"nle-roundtrip {package.status}")
        print(f"wrote {payload['output']}")
        print(f"wrote {payload['report']}")
    if package.status == "blocked":
        return int(ExitCode.output_or_reference_validation_failed)
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_fcpxml(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    selected_modes = sum(bool(item) for item in (args.draft, args.import_review, args.repair_plan))
    if selected_modes != 1:
        print("fcpxml requires exactly one of --draft, --import-review, or --repair-plan", file=sys.stderr)
        return int(ExitCode.invalid_cli_usage)
    project_path = Path(args.project)
    try:
        config = load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    root = project_root(project_path)
    state = load_state(root)
    try:
        if args.repair_plan:
            json_path, md_path, handoff_path, result = build_fcpxml_repair_plan(root=root, project_id=config.project.id)
            step = "fcpxml_repair_plan"
            report_status = result.status
            warnings = result.warnings
            output_refs = [json_path, md_path, handoff_path]
            payload = {
                "output": json_path.relative_to(root).as_posix(),
                "report": md_path.relative_to(root).as_posix(),
                "handoff": handoff_path.relative_to(root).as_posix(),
                "status": result.status,
                "first_required_command": result.first_required_command,
                "fcpxml_repair_plan": result.model_dump(mode="json"),
            }
        elif args.import_review:
            json_path, md_path, handoff_path, result = import_fcpxml_import_review(root=root, project_id=config.project.id, candidate_path=Path(args.import_review))
            step = "fcpxml_import_review"
            report_status = result.status
            warnings = result.warnings + result.rejected_reasons
            output_refs = [json_path, md_path, handoff_path]
            payload = {
                "output": json_path.relative_to(root).as_posix(),
                "report": md_path.relative_to(root).as_posix(),
                "handoff": handoff_path.relative_to(root).as_posix(),
                "status": result.status,
                "fcpxml_import_review": result.model_dump(mode="json"),
            }
        else:
            draft_json_path, fcpxml_path, validation_path, review_path, handoff_path, draft, validation = build_fcpxml_draft(root=root, project_id=config.project.id, draft=True)
            step = "fcpxml_draft"
            result = draft
            report_status = draft.status
            warnings = draft.warnings + draft.blocked_reasons + validation.errors
            output_refs = [draft_json_path, fcpxml_path, validation_path, review_path, handoff_path]
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
    except FcpxmlWriterError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    if report_status in {"blocked", "rejected", "failed"}:
        status = StepStatus.failed
    elif report_status == "warning":
        status = StepStatus.completed_with_warnings
    else:
        status = StepStatus.completed
    if state is not None:
        run_id = new_run_id()
        state.steps[step] = StepLedgerEntry(status=status, output_refs=[path.relative_to(root).as_posix() for path in output_refs], last_run_id=run_id, warnings=warnings)
        state.latest_run_id = run_id
        state.updated_at = utc_now()
        runs_dir = root / ".artist-portrait" / "runs" / run_id
        runs_dir.mkdir(parents=True, exist_ok=True)
        write_json(runs_dir / "command.json", {"command": "fcpxml", "project": str(project_path), "mode": step})
        write_json(runs_dir / "environment.json", environment_snapshot())
        write_json(runs_dir / "step_result.json", {
            "step": step,
            "status": status.value,
            "output_refs": state.steps[step].output_refs,
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
        })
        save_state(root, state)
        write_run_report(root / config.paths.output_dir, state, [])
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"fcpxml {report_status}")
        print(f"wrote {payload['report']}")
    if report_status in {"blocked", "rejected", "failed"}:
        return int(ExitCode.output_or_reference_validation_failed)
    return int(ExitCode.success_with_warnings if report_status == "warning" else ExitCode.success)


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
    json_path, md_path, report = build_project_acceptance_report(root=root, project_id=config.project.id, state=state, profile=args.profile)
    if state is not None:
        run_id = new_run_id()
        warnings = [item.detail for stage in report.stages for item in stage.issues if item.severity == "warning"]
        errors = [item.detail for stage in report.stages for item in stage.issues if item.severity == "error"]
        status = StepStatus.failed if report.status == "failed" else StepStatus.completed_with_warnings if report.status == "warning" else StepStatus.completed
        state.steps["acceptance"] = StepLedgerEntry(status=status, output_refs=[json_path.relative_to(root).as_posix(), md_path.relative_to(root).as_posix()], last_run_id=run_id, warnings=warnings)
        state.latest_run_id = run_id
        state.updated_at = utc_now()
        state.overall_status = OverallStatus.blocked if report.status == "failed" else OverallStatus.degraded if report.status == "warning" else OverallStatus.ready
        runs_dir = root / ".artist-portrait" / "runs" / run_id
        runs_dir.mkdir(parents=True, exist_ok=True)
        write_json(runs_dir / "command.json", {"command": "acceptance", "project": str(project_path), "profile": args.profile})
        write_json(runs_dir / "environment.json", environment_snapshot())
        write_json(runs_dir / "step_result.json", {
            "step": "acceptance",
            "status": status.value,
            "output_refs": state.steps["acceptance"].output_refs,
            "network_performed": False,
            "model_call_performed": False,
            "media_rendered": False,
            "commands_executed": False,
        })
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
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"acceptance {report.acceptance_profile} {report.status}")
        print(f"wrote {payload['report']}")
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
                "brief",
                "score",
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
            for name in ("keyframes", "analyze", "map", "brief", "score", "propose", "review_project")
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


def cmd_brief(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    try:
        json_path, md_path, brief = build_edit_brief_workspace(
            project_path,
            target_duration_seconds=args.target_duration_seconds,
            platform=args.platform,
        )
    except WorkspacePrerequisiteError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.prerequisite_step_missing)
    except SourceLedgerError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    except EditBriefError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_arguments)
    root = project_root(project_path)
    payload = {
        "output": json_path.relative_to(root).as_posix(),
        "report": md_path.relative_to(root).as_posix(),
        "status": brief.status,
        "selected_duration_seconds": brief.selected_duration_seconds,
        "duration_source": brief.duration_source,
        "selected_option_id": brief.selected_option_id,
        "warnings": brief.warnings,
        "edit_brief": brief.model_dump(mode="json"),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(
            f"brief {brief.status}: {brief.selected_duration_seconds:.3f}s "
            f"({brief.duration_source}, {brief.selected_option_id})"
        )
        print(f"wrote {payload['report']}")
        for warning in brief.warnings:
            print(f"warning: {warning}", file=sys.stderr)
    return int(ExitCode.success_with_warnings if brief.warnings else ExitCode.success)


def cmd_score(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    try:
        jsonl_path, report_path, records, warnings = score_workspace(project_path)
    except WorkspacePrerequisiteError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.prerequisite_step_missing)
    except ClipScoringError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    payload = {
        "output": jsonl_path.relative_to(root).as_posix(),
        "report": report_path.relative_to(root).as_posix(),
        "clip_scores": [record.model_dump(mode="json") for record in records],
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"score completed: {len(records)} clip(s)")
        print(f"wrote {payload['report']}")
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
            for name in ("map", "brief", "score", "propose", "review_project")
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
            for name in ("analyze", "map", "brief", "score", "propose", "review_project")
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
            for name in ("analyze", "map", "brief", "score", "review_project")
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


def cmd_sound(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    try:
        json_path, md_path, decision, warnings = build_sound_decision_workspace(project_path)
    except WorkspacePrerequisiteError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.prerequisite_step_missing)
    except (SoundDecisionError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    payload = {
        "output": json_path.relative_to(root).as_posix(),
        "report": md_path.relative_to(root).as_posix(),
        "status": decision.status,
        "sound_decision": decision.model_dump(mode="json"),
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"wrote {payload['output']}")
        print(f"wrote {payload['report']}")
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_cut_review(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    try:
        json_path, md_path, review, warnings = build_cut_review_workspace(project_path)
    except WorkspacePrerequisiteError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.prerequisite_step_missing)
    except (CutReviewError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    payload = {
        "output": json_path.relative_to(root).as_posix(),
        "report": md_path.relative_to(root).as_posix(),
        "status": review.status,
        "cut_review": review.model_dump(mode="json"),
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"wrote {payload['output']}")
        print(f"wrote {payload['report']}")
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_composition(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        if args.agent_output and args.preview_candidate:
            print("--agent-output and --preview-candidate are mutually exclusive", file=sys.stderr)
            return int(ExitCode.invalid_arguments)
        if args.preview_candidate:
            preview_path, preview = render_reframe_candidate_preview(
                project_path,
                candidate_id=args.preview_candidate,
            )
            payload = {
                "preview": preview_path.relative_to(project_root(project_path)).as_posix(),
                "reframe_preview": preview,
            }
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
            elif not args.quiet:
                print(f"wrote {payload['preview']}")
            return int(ExitCode.success)
        if args.agent_output:
            canonical_path, report_path, review, warnings = import_composition_review(
                project_path,
                candidate_path=Path(args.agent_output),
            )
            root = project_root(project_path)
            payload = {
                "output": canonical_path.relative_to(root).as_posix(),
                "report": report_path.relative_to(root).as_posix(),
                "composition_review": review.model_dump(mode="json"),
                "warnings": warnings,
            }
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
            elif not args.quiet:
                print(f"wrote {payload['output']}")
                print(f"wrote {payload['report']}")
            return int(ExitCode.success_with_warnings if warnings else ExitCode.success)
        contact_sheet, handoff_path, handoff, warnings = build_composition_evidence(
            project_path,
            sample_count=args.samples,
        )
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    except (CompositionEvidenceError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    payload = {
        "contact_sheet": contact_sheet.relative_to(root).as_posix(),
        "handoff": handoff_path.relative_to(root).as_posix(),
        "composition_evidence": handoff,
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"wrote {payload['contact_sheet']}")
        print(f"wrote {payload['handoff']}")
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_reframe(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        canonical, report, application, warnings = apply_reframe_selection(
            project_path, selection_path=Path(args.selection)
        )
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    except (ReframeError, CompositionEvidenceError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    payload = {
        "output": canonical.relative_to(root).as_posix(),
        "report": report.relative_to(root).as_posix(),
        "playback": application.output_ref,
        "reframe_application": application.model_dump(mode="json"),
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"wrote {payload['output']}")
        print(f"wrote {payload['playback']}")
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_evidence_map(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        canonical, report, evidence_map, warnings = build_evidence_map(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    except (EvidenceFusionError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    payload = {
        "output": canonical.relative_to(root).as_posix(),
        "report": report.relative_to(root).as_posix(),
        "evidence_map": evidence_map.model_dump(mode="json"),
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"wrote {payload['output']}")
        print(f"wrote {payload['report']}")
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_editorial_score(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args): return int(error)
    project_path = Path(args.project)
    try:
        canonical, report, scores, warnings = build_editorial_scores(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr); return int(ExitCode.invalid_project_config)
    except (EditorialScoringError, ValueError) as exc:
        print(str(exc), file=sys.stderr); return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    payload = {"output": canonical.relative_to(root).as_posix(), "report": report.relative_to(root).as_posix(), "editorial_scores": scores.model_dump(mode="json"), "warnings": warnings}
    if args.json: print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"wrote {payload['output']}"); print(f"wrote {payload['report']}")
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_structure_recommend(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args): return int(error)
    project_path=Path(args.project)
    try: canonical,report,rec,warnings=build_structure_recommendation(project_path)
    except ConfigLoadError as exc: print(str(exc),file=sys.stderr); return int(ExitCode.invalid_project_config)
    except (StructureRecommendationError,ValueError) as exc: print(str(exc),file=sys.stderr); return int(ExitCode.output_or_reference_validation_failed)
    root=project_root(project_path); payload={"output":canonical.relative_to(root).as_posix(),"report":report.relative_to(root).as_posix(),"structure_recommendation":rec.model_dump(mode="json"),"warnings":warnings}
    if args.json: print(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True))
    elif not args.quiet: print(f"wrote {payload['output']}"); print(f"wrote {payload['report']}")
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)

def cmd_bgm_match(args:argparse.Namespace)->int:
    project_path=Path(args.project)
    try: canonical,report,result,warnings=build_bgm_match(project_path)
    except (BgmMatchingError,ConfigLoadError,ValueError) as exc: print(str(exc),file=sys.stderr); return int(ExitCode.output_or_reference_validation_failed)
    root=project_root(project_path); payload={"output":canonical.relative_to(root).as_posix(),"report":report.relative_to(root).as_posix(),"bgm_match":result.model_dump(mode="json"),"warnings":warnings}
    if args.json: print(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True))
    elif not args.quiet: print(f"wrote {payload['output']}")
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_text_plan(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        canonical, report, plan, warnings = build_text_plan(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    except (TextPlanningError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    payload = {"output": canonical.relative_to(root).as_posix(), "report": report.relative_to(root).as_posix(), "text_plan": plan.model_dump(mode="json"), "warnings": warnings}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"wrote {payload['output']}")
        print(f"wrote {payload['report']}")
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_first_cut_review(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        canonical, report, review, warnings = build_first_cut_self_review(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    except (FirstCutReviewError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    payload = {"output": canonical.relative_to(root).as_posix(), "report": report.relative_to(root).as_posix(), "first_cut_review": review.model_dump(mode="json"), "warnings": warnings}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"wrote {payload['output']}")
        print(f"wrote {payload['report']}")
    return int(ExitCode.success_with_warnings)


def cmd_second_cut_render(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        canonical, report, media, result, warnings = render_second_cut(project_path, args.option_id)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    except (SecondCutRenderError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    payload = {
        "output": canonical.relative_to(root).as_posix(),
        "report": report.relative_to(root).as_posix(),
        "media": media.relative_to(root).as_posix(),
        "second_cut_render": result.model_dump(mode="json"),
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"wrote {payload['output']}")
        print(f"wrote {payload['report']}")
        print(f"rendered {payload['media']}")
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_benchmark_pack(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    try:
        canonical, report, pack, warnings = build_benchmark_pack(args.benchmark, Path(args.output_dir))
    except (BenchmarkPackError, ConfigLoadError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    payload = {
        "output": str(canonical), "report": str(report),
        "benchmark_pack": pack.model_dump(mode="json"), "warnings": warnings,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"wrote {canonical}")
        print(f"wrote {report}")
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_creative_strategies(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        canonical, report, package, warnings = build_creative_strategy_package(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    except (CreativeStrategiesError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    payload = {"output": canonical.relative_to(root).as_posix(), "report": report.relative_to(root).as_posix(), "creative_strategy_package": package.model_dump(mode="json"), "warnings": warnings}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"wrote {payload['output']}")
        print(f"wrote {payload['report']}")
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_style_templates(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        canonical, report, package, warnings = build_style_template_package(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    except (StyleTemplatesError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    payload = {"output": canonical.relative_to(root).as_posix(), "report": report.relative_to(root).as_posix(), "style_template_package": package.model_dump(mode="json"), "warnings": warnings}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"wrote {payload['output']}")
        print(f"wrote {payload['report']}")
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_baseline(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        if args.agent_output:
            canonical, report, baseline, warnings = import_aesthetic_baseline(
                project_path, candidate_path=Path(args.agent_output)
            )
            root = project_root(project_path)
            payload = {
                "output": canonical.relative_to(root).as_posix(),
                "report": report.relative_to(root).as_posix(),
                "aesthetic_baseline": baseline.model_dump(mode="json"),
                "warnings": warnings,
            }
        else:
            handoff_path, handoff, warnings = prepare_aesthetic_baseline_handoff(project_path)
            root = project_root(project_path)
            payload = {
                "handoff": handoff_path.relative_to(root).as_posix(),
                "aesthetic_baseline_context": handoff,
                "warnings": warnings,
            }
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    except (AestheticBaselineError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        for key in ("handoff", "output", "report"):
            if key in payload:
                print(f"wrote {payload[key]}")
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_second_cut(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        json_path, report_path, candidate, warnings = build_second_cut_candidate(
            project_path, concept_id=args.concept_id
        )
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    except (SecondCutError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    payload = {
        "output": json_path.relative_to(root).as_posix(),
        "report": report_path.relative_to(root).as_posix(),
        "status": candidate.status,
        "second_cut_candidate": candidate.model_dump(mode="json"),
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"second-cut candidate {candidate.status}")
        print(f"wrote {payload['output']}")
        print(f"wrote {payload['report']}")
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_revise(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    try:
        json_path, md_path, plan, warnings = build_revision_plan_workspace(
            project_path,
            request_text=args.intent,
            request_type=args.request_type,
            target_duration_seconds=args.target_duration_seconds,
            keep_segment_ids=args.keep_segment,
            remove_segment_ids=args.remove_segment,
        )
    except WorkspacePrerequisiteError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.prerequisite_step_missing)
    except (RevisionPlanError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    payload = {
        "output": json_path.relative_to(root).as_posix(),
        "report": md_path.relative_to(root).as_posix(),
        "status": plan.status,
        "revision_plan": plan.model_dump(mode="json"),
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"revision {plan.status}")
        print(f"wrote {payload['output']}")
        print(f"wrote {payload['report']}")
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_apply_revision(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    try:
        json_path, md_path, application, warnings = build_revision_application_workspace(
            project_path,
            version_id=args.version_id,
            action_ids=args.action_id,
        )
    except WorkspacePrerequisiteError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.prerequisite_step_missing)
    except (RevisionApplicationError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    payload = {
        "output": json_path.relative_to(root).as_posix(),
        "report": md_path.relative_to(root).as_posix(),
        "status": application.status,
        "revision_application": application.model_dump(mode="json"),
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"revision application {application.status}")
        print(f"wrote {payload['output']}")
        print(f"wrote {payload['report']}")
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
    return int(
        ExitCode.output_or_reference_validation_failed
        if application.status == "blocked"
        else ExitCode.success_with_warnings
        if warnings
        else ExitCode.success
    )


def cmd_promote_revision(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        load_project_config(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    try:
        timeline_path, json_path, md_path, promotion, warnings = build_revision_promotion_workspace(
            project_path,
            revision_application_id=args.revision_application_id,
        )
    except WorkspacePrerequisiteError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.prerequisite_step_missing)
    except (RevisionPromotionError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    payload = {
        "timeline": timeline_path.relative_to(root).as_posix(),
        "output": json_path.relative_to(root).as_posix(),
        "report": md_path.relative_to(root).as_posix(),
        "status": promotion.status,
        "revision_promotion": promotion.model_dump(mode="json"),
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"revision promotion {promotion.status}")
        print(f"updated {payload['timeline']}")
        print(f"wrote {payload['output']}")
        print(f"wrote {payload['report']}")
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_version_review(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args): return int(error)
    project_path = Path(args.project)
    try:
        json_path, md_path, review, warnings = build_version_review_workspace(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr); return int(ExitCode.invalid_project_config)
    except WorkspacePrerequisiteError as exc:
        print(str(exc), file=sys.stderr); return int(ExitCode.prerequisite_step_missing)
    except (VersionReviewError, ValueError) as exc:
        print(str(exc), file=sys.stderr); return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    payload = {"output": json_path.relative_to(root).as_posix(), "report": md_path.relative_to(root).as_posix(), "status": review.status, "version_review": review.model_dump(mode="json"), "warnings": warnings}
    if args.json: print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"version review {review.status}"); print(f"wrote {payload['output']}"); print(f"wrote {payload['report']}")
    return int(ExitCode.success_with_warnings if warnings else ExitCode.success)


def cmd_publishability(args: argparse.Namespace) -> int:
    if error := _validate_common_flags(args):
        return int(error)
    project_path = Path(args.project)
    try:
        json_path, md_path, report, warnings = build_publishability_workspace(project_path)
    except ConfigLoadError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.invalid_project_config)
    except WorkspacePrerequisiteError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.prerequisite_step_missing)
    except (PublishabilityError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.output_or_reference_validation_failed)
    root = project_root(project_path)
    payload = {
        "output": json_path.relative_to(root).as_posix(),
        "report": md_path.relative_to(root).as_posix(),
        "status": report.status,
        "highest_available_tier": report.highest_available_tier,
        "highest_tier_version_ids": report.highest_tier_version_ids,
        "selected_version_id": None,
        "publishability": report.model_dump(mode="json"),
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    elif not args.quiet:
        print(f"publishability {report.status}")
        print(f"highest available tier: {report.highest_available_tier}")
        print("selected version: none")
        print(f"wrote {payload['output']}")
        print(f"wrote {payload['report']}")
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
                context_path, handoff_path = prepare_bgm_recommendation_handoff(
                    root=root,
                    project_id=config.project.id,
                )
                payload = {
                    "context": context_path.relative_to(root).as_posix(),
                    "handoff": handoff_path.relative_to(root).as_posix(),
                    "next_command": "artist-portrait bgm recommend --project <project.yaml> --agent-output <candidate.json>",
                }
                step_name = "bgm_recommend"
                output_refs = [
                    context_path.relative_to(root).as_posix(),
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
        "cleanup": cmd_cleanup,
        "release-check": cmd_release_check,
        "workflow": cmd_workflow,
        "operator": cmd_operator,
        "editor-package": cmd_editor_package,
        "nle-plan": cmd_nle_plan,
        "nle-roundtrip": cmd_nle_roundtrip,
        "fcpxml": cmd_fcpxml,
        "acceptance": cmd_acceptance,
        "scan": cmd_scan,
        "segment": cmd_segment,
        "transcribe": cmd_transcribe,
        "keyframes": cmd_keyframes,
        "analyze": cmd_analyze,
        "map": cmd_map,
        "brief": cmd_brief,
        "score": cmd_score,
        "review": cmd_review,
        "propose": cmd_propose,
        "timeline": cmd_timeline,
        "sound": cmd_sound,
        "cut-review": cmd_cut_review,
        "composition": cmd_composition,
        "reframe": cmd_reframe,
        "evidence-map": cmd_evidence_map,
        "editorial-score": cmd_editorial_score,
        "structure-recommend": cmd_structure_recommend,
        "bgm-match": cmd_bgm_match,
        "text-plan": cmd_text_plan,
        "first-cut-review": cmd_first_cut_review,
        "second-cut-render": cmd_second_cut_render,
        "benchmark-pack": cmd_benchmark_pack,
        "creative-strategies": cmd_creative_strategies,
        "style-templates": cmd_style_templates,
        "baseline": cmd_baseline,
        "second-cut": cmd_second_cut,
        "revise": cmd_revise,
        "apply-revision": cmd_apply_revision,
        "promote-revision": cmd_promote_revision,
        "version-review": cmd_version_review,
        "publishability": cmd_publishability,
        "preview": cmd_preview,
        "export": cmd_export,
        "rhythm": cmd_rhythm,
        "bgm": cmd_bgm,
    }
    handler = handlers.get(args.command, blocked_stage_a_command)
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
