from __future__ import annotations

import hashlib
import json
from pathlib import Path

from artist_portrait_editor.capabilities import capability_warnings, detect_capabilities
from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import CACHE_DIR, DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.diagnostics import (
    artifact_issue,
    rebuild_command_for_step,
    render_risk_report,
    risk_issue,
    workspace_issue,
)
from artist_portrait_editor.bgm import bgm_analysis_summary
from artist_portrait_editor.bgm_recommendation import bgm_recommendation_doctor_issues, bgm_recommendation_summary
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
from artist_portrait_editor.models.bgm import BgmCandidateLedger, BgmFitPlan
from artist_portrait_editor.models.clip import (
    ClipBoundary,
    ClipMethod,
    ClipRecord,
    ClipRiskFlag,
)
from artist_portrait_editor.models.keyframe import KeyframeRecord, KeyframeRiskFlag
from artist_portrait_editor.models.model_gate import TextModelGate, TextModelGateStatus
from artist_portrait_editor.models.proposal import ProposalId, ProposalSet
from artist_portrait_editor.models.timeline import TimelineDraft, TimelineValidationReport
from artist_portrait_editor.models.proposal_adapter import (
    ProposalAdapterCheck,
    ProposalAdapterCheckIssue,
    ProposalAdapterCheckStatus,
    ProposalCanonicalWriteTransactionItem,
    ProposalCanonicalWriteTransactionPlan,
    ProposalCanonicalWriteTransactionStatus,
    ProposalExecutionApprovalRecord,
    ProposalExecutionApprovalRecordStatus,
    ProposalExecutionApprovalRequest,
    ProposalExecutionApprovalRequestStatus,
    ProposalExecutionAuthorization,
    ProposalExecutionAuthorizationStatus,
    ProposalExecutionInputBundle,
    ProposalExecutionInputBundleItem,
    ProposalExecutionInputBundleStatus,
    ProposalExecutionReadinessPlan,
    ProposalExecutionReadinessPlanStatus,
    ProposalExecutionReadinessStage,
    ProposalMockAdapterHandshake,
    ProposalMockAdapterHandshakeStatus,
    ProposalPromotionAuthorizationItem,
    ProposalPromotionAuthorizationPlan,
    ProposalPromotionAuthorizationStatus,
    ProposalPromotionValidationCheck,
    ProposalPromotionValidationReport,
    ProposalPromotionValidationReportStatus,
    ProposalProviderCallDryRun,
    ProposalProviderCallDryRunItem,
    ProposalProviderCallDryRunStatus,
    ProposalProviderOutputQuarantine,
    ProposalProviderOutputQuarantineStatus,
    ProposalProviderResponseIntakeItem,
    ProposalProviderResponseIntakePlan,
    ProposalProviderResponseIntakeStatus,
    ProposalProviderResponseValidationItem,
    ProposalProviderResponseValidationPlan,
    ProposalProviderResponseValidationStatus,
    ProposalProviderResultEnvelope,
    ProposalProviderResultStatus,
    ProposalProviderRecord,
    ProposalProviderRegistry,
)
from artist_portrait_editor.models.proposal_context import (
    ProposalAnalysisContext,
    ProposalClipContext,
    ProposalContext,
    ProposalSourceContext,
)
from artist_portrait_editor.models.proposal_request import (
    ProposalRequestPacket,
    ProposalRequestStatus,
)
from artist_portrait_editor.models.proposal_validation import (
    ProposalValidationIssue,
    ProposalValidationReport,
)
from artist_portrait_editor.models.state import (
    ActiveMode,
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
from artist_portrait_editor.proposal_artifacts import (
    proposal_artifact_paths,
    proposal_chain_issues,
    proposal_invalid_artifacts,
)
from artist_portrait_editor.proposal_io import read_proposal_artifact
from artist_portrait_editor.proposal_review import (
    proposal_validation_issue,
    validate_proposal_set_against_context,
)
from artist_portrait_editor.proposal_handoff import (
    AgentProposalCandidateError,
    parse_quarantined_proposal_set,
    quarantine_agent_candidate,
    require_host_agent_method,
    write_agent_handoff_bundle,
)
from artist_portrait_editor.timeline import (
    TimelineBuildError,
    build_timeline_draft,
    render_timeline_review,
    validate_timeline_draft,
)
from artist_portrait_editor.preview import (
    preview_manifest_summary,
    preview_validation_summary,
    review_preview,
)
from artist_portrait_editor.final_export import (
    final_export_doctor_issues,
    final_export_manifest_summary,
    final_export_status_lines,
    final_export_validation_summary,
)


class WorkspacePrerequisiteError(Exception):
    pass


class WorkspaceDependencyError(Exception):
    pass


class WorkspaceProposalCandidateError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str,
        quarantine_ref: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.quarantine_ref = quarantine_ref


class WorkspaceTimelineError(Exception):
    pass


class WorkspacePreviewError(Exception):
    pass


PROPOSAL_INVALID_ARTIFACTS = proposal_invalid_artifacts()


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
        payload["artifact_issues"] = [
            *ledger_output_ref_issues(root, state),
            *proposal_chain_issues(root),
        ]
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
    proposal_validation = summaries.get("proposal_validation") or {}
    if proposal_validation.get("exists") and proposal_validation.get("valid", True):
        lines.append(
            "proposal_validation: "
            f"{proposal_validation.get('error_count', 0)} errors, "
            f"{proposal_validation.get('warning_count', 0)} warnings"
        )
    elif proposal_validation.get("exists"):
        lines.append("proposal_validation: invalid")
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
    agent_handoff = summaries.get("proposal_agent_handoff") or {}
    if agent_handoff.get("exists"):
        lines.append(
            f"proposal_agent_handoff: present ({agent_handoff.get('bytes', 0)} bytes)"
        )
    agent_quarantine = summaries.get("proposal_agent_quarantine") or {}
    if agent_quarantine.get("exists"):
        lines.append(
            "proposal_agent_quarantine: "
            f"{agent_quarantine.get('file_count', 0)} file(s)"
        )
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
    proposal_request = summaries.get("proposal_request") or {}
    if proposal_request.get("exists") and proposal_request.get("valid", True):
        lines.append(f"proposal_request: {proposal_request.get('status')}")
    elif proposal_request.get("exists"):
        lines.append("proposal_request: invalid")
    else:
        lines.append("proposal_request: missing")
    proposal_adapter_check = summaries.get("proposal_adapter_check") or {}
    if proposal_adapter_check.get("exists") and proposal_adapter_check.get("valid", True):
        lines.append(f"proposal_adapter_check: {proposal_adapter_check.get('status')}")
    elif proposal_adapter_check.get("exists"):
        lines.append("proposal_adapter_check: invalid")
    else:
        lines.append("proposal_adapter_check: missing")
    provider_registry = summaries.get("proposal_provider_registry") or {}
    if provider_registry.get("exists") and provider_registry.get("valid", True):
        lines.append(
            f"proposal_provider_registry: {provider_registry.get('selected_provider_id')}"
        )
    elif provider_registry.get("exists"):
        lines.append("proposal_provider_registry: invalid")
    else:
        lines.append("proposal_provider_registry: missing")
    mock_handshake = summaries.get("proposal_mock_adapter_handshake") or {}
    if mock_handshake.get("exists") and mock_handshake.get("valid", True):
        lines.append(f"proposal_mock_adapter_handshake: {mock_handshake.get('status')}")
    elif mock_handshake.get("exists"):
        lines.append("proposal_mock_adapter_handshake: invalid")
    else:
        lines.append("proposal_mock_adapter_handshake: missing")
    approval_request = summaries.get("proposal_execution_approval_request") or {}
    if approval_request.get("exists") and approval_request.get("valid", True):
        lines.append(
            f"proposal_execution_approval_request: {approval_request.get('status')}"
        )
    elif approval_request.get("exists"):
        lines.append("proposal_execution_approval_request: invalid")
    else:
        lines.append("proposal_execution_approval_request: missing")
    approval_record = summaries.get("proposal_execution_approval_record") or {}
    if approval_record.get("exists") and approval_record.get("valid", True):
        lines.append(
            f"proposal_execution_approval_record: {approval_record.get('status')}"
        )
    elif approval_record.get("exists"):
        lines.append("proposal_execution_approval_record: invalid")
    else:
        lines.append("proposal_execution_approval_record: missing")
    readiness_plan = summaries.get("proposal_execution_readiness_plan") or {}
    if readiness_plan.get("exists") and readiness_plan.get("valid", True):
        lines.append(
            f"proposal_execution_readiness_plan: {readiness_plan.get('status')}"
        )
    elif readiness_plan.get("exists"):
        lines.append("proposal_execution_readiness_plan: invalid")
    else:
        lines.append("proposal_execution_readiness_plan: missing")
    input_bundle = summaries.get("proposal_execution_input_bundle") or {}
    if input_bundle.get("exists") and input_bundle.get("valid", True):
        lines.append(
            f"proposal_execution_input_bundle: {input_bundle.get('status')}"
        )
    elif input_bundle.get("exists"):
        lines.append("proposal_execution_input_bundle: invalid")
    else:
        lines.append("proposal_execution_input_bundle: missing")
    call_dry_run = summaries.get("proposal_provider_call_dry_run") or {}
    if call_dry_run.get("exists") and call_dry_run.get("valid", True):
        lines.append(
            f"proposal_provider_call_dry_run: {call_dry_run.get('status')}"
        )
    elif call_dry_run.get("exists"):
        lines.append("proposal_provider_call_dry_run: invalid")
    else:
        lines.append("proposal_provider_call_dry_run: missing")
    execution_authorization = summaries.get("proposal_execution_authorization") or {}
    if execution_authorization.get("exists") and execution_authorization.get("valid", True):
        lines.append(
            f"proposal_execution_authorization: {execution_authorization.get('status')}"
        )
    elif execution_authorization.get("exists"):
        lines.append("proposal_execution_authorization: invalid")
    else:
        lines.append("proposal_execution_authorization: missing")
    response_intake = summaries.get("proposal_provider_response_intake_plan") or {}
    if response_intake.get("exists") and response_intake.get("valid", True):
        lines.append(
            f"proposal_provider_response_intake_plan: {response_intake.get('status')}"
        )
    elif response_intake.get("exists"):
        lines.append("proposal_provider_response_intake_plan: invalid")
    else:
        lines.append("proposal_provider_response_intake_plan: missing")
    response_validation = summaries.get("proposal_provider_response_validation_plan") or {}
    if response_validation.get("exists") and response_validation.get("valid", True):
        lines.append(
            f"proposal_provider_response_validation_plan: {response_validation.get('status')}"
        )
    elif response_validation.get("exists"):
        lines.append("proposal_provider_response_validation_plan: invalid")
    else:
        lines.append("proposal_provider_response_validation_plan: missing")
    promotion_authorization = summaries.get("proposal_promotion_authorization_plan") or {}
    if promotion_authorization.get("exists") and promotion_authorization.get("valid", True):
        lines.append(
            f"proposal_promotion_authorization_plan: {promotion_authorization.get('status')}"
        )
    elif promotion_authorization.get("exists"):
        lines.append("proposal_promotion_authorization_plan: invalid")
    else:
        lines.append("proposal_promotion_authorization_plan: missing")
    promotion_validation = summaries.get("proposal_promotion_validation_report") or {}
    if promotion_validation.get("exists") and promotion_validation.get("valid", True):
        lines.append(
            f"proposal_promotion_validation_report: {promotion_validation.get('status')}"
        )
    elif promotion_validation.get("exists"):
        lines.append("proposal_promotion_validation_report: invalid")
    else:
        lines.append("proposal_promotion_validation_report: missing")
    write_transaction = summaries.get("proposal_canonical_write_transaction_plan") or {}
    if write_transaction.get("exists") and write_transaction.get("valid", True):
        lines.append(
            f"proposal_canonical_write_transaction_plan: {write_transaction.get('status')}"
        )
    elif write_transaction.get("exists"):
        lines.append("proposal_canonical_write_transaction_plan: invalid")
    else:
        lines.append("proposal_canonical_write_transaction_plan: missing")
    output_quarantine = summaries.get("proposal_provider_output_quarantine") or {}
    if output_quarantine.get("exists") and output_quarantine.get("valid", True):
        lines.append(
            f"proposal_provider_output_quarantine: {output_quarantine.get('status')}"
        )
    elif output_quarantine.get("exists"):
        lines.append("proposal_provider_output_quarantine: invalid")
    else:
        lines.append("proposal_provider_output_quarantine: missing")
    provider_result = summaries.get("proposal_provider_result") or {}
    if provider_result.get("exists") and provider_result.get("valid", True):
        lines.append(f"proposal_provider_result: {provider_result.get('status')}")
    elif provider_result.get("exists"):
        lines.append("proposal_provider_result: invalid")
    else:
        lines.append("proposal_provider_result: missing")
    proposals = summaries.get("proposals") or {}
    if proposals.get("exists") and proposals.get("valid", True):
        lines.append(f"proposals: {proposals.get('count', 0)}")
    elif proposals.get("exists"):
        lines.append("proposals: invalid")
    else:
        lines.append("proposals: missing")
    timeline = summaries.get("timeline") or {}
    if timeline.get("exists") and timeline.get("valid", True):
        lines.append(
            f"timeline: {timeline.get('proposal_id')} "
            f"({timeline.get('segment_count', 0)} segments)"
        )
    elif timeline.get("exists"):
        lines.append("timeline: invalid")
    else:
        lines.append("timeline: missing")
    preview = summaries.get("preview") or {}
    if preview.get("exists") and preview.get("valid", True):
        lines.append(
            f"preview: {preview.get('output_ref')} "
            f"({preview.get('width')}x{preview.get('height')}, "
            f"bgm={str(preview.get('bgm_included')).lower()})"
        )
        preview_validation = summaries.get("preview_validation") or {}
        if preview_validation.get("exists") and preview_validation.get("valid", True):
            lines.append(
                "preview_qc: "
                f"{preview_validation.get('quality_status')} "
                f"(delta={preview_validation.get('duration_delta_seconds')}s)"
            )
    elif preview.get("exists"):
        lines.append("preview: invalid")
    else:
        lines.append("preview: missing")
    lines.extend(final_export_status_lines(summaries))
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
        "propose",
        "timeline",
        "preview",
        "final_export",
        "review_timeline",
        "review_preview",
        "review_final_export",
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
    issues.extend(proposal_chain_issues(root))
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
    timeline = timeline_summary(root / config.paths.output_dir / "timeline_draft.json")
    if timeline.get("valid") is False:
        issues.append(
            workspace_issue(
                code="timeline_invalid",
                severity="error",
                detail=str(timeline.get("error") or "timeline draft is invalid"),
                next_action=(
                    "fix output/timeline_draft.json or rerun artist-portrait timeline "
                    f"--project {project_path} --proposal <selected-proposal-id>"
                ),
            )
        )
    bgm_candidates = bgm_candidates_summary(
        root / WORKSPACE_DIR / DATA_DIR / "bgm_candidates.json"
    )
    if bgm_candidates.get("valid") is False:
        issues.append(
            workspace_issue(
                code="bgm_candidates_invalid",
                severity="error",
                detail=str(bgm_candidates.get("error")),
                next_action="fix or rebuild .artist-portrait/data/bgm_candidates.json",
            )
        )
    bgm_analysis = bgm_analysis_summary(root / ".artist-portrait" / "data" / "bgm_analysis.json")
    if bgm_analysis.get("valid") is False:
        issues.append(
            workspace_issue(
                code="bgm_analysis_invalid",
                severity="error",
                detail=str(bgm_analysis.get("error")),
                next_action=f"rerun artist-portrait bgm analyze --project {project_path}",
            )
        )
    issues.extend(bgm_recommendation_doctor_issues(root, str(project_path)))
    bgm_fit = bgm_fit_summary(root / WORKSPACE_DIR / DATA_DIR / "bgm_fit.json")
    if bgm_fit.get("valid") is False:
        issues.append(
            workspace_issue(
                code="bgm_fit_invalid",
                severity="error",
                detail=str(bgm_fit.get("error")),
                next_action=(
                    f"rerun artist-portrait bgm fit --project {project_path} "
                    "--candidate <candidate-id>"
                ),
            )
        )
    preview_manifest = preview_manifest_summary(
        root / WORKSPACE_DIR / DATA_DIR / "preview_manifest.json"
    )
    if preview_manifest.get("valid") is False:
        issues.append(
            workspace_issue(
                code="preview_manifest_invalid",
                severity="error",
                detail=str(preview_manifest.get("error")),
                next_action=f"rerun artist-portrait preview --project {project_path}",
            )
        )
    preview_validation = preview_validation_summary(
        root / WORKSPACE_DIR / DATA_DIR / "preview_validation.json"
    )
    if preview_validation.get("valid") is False:
        issues.append(
            workspace_issue(
                code="preview_validation_invalid",
                severity="error",
                detail=str(preview_validation.get("error")),
                next_action=f"rerun artist-portrait preview --project {project_path}",
            )
        )
    if preview_manifest.get("valid") is True:
        preview_report = review_preview(root)
        for issue in preview_report.issues:
            issues.append(
                workspace_issue(
                    code=issue.code,
                    severity=issue.severity,
                    detail=issue.detail,
                    next_action=f"artist-portrait preview --project {project_path}",
                )
            )
    issues.extend(final_export_doctor_issues(root, str(project_path)))
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
    summaries = status_summaries(root)
    proposals = summaries["proposals"]
    if sources.get("valid") is True:
        proposal_paths = proposal_artifact_paths(root)
        for name, (code, label) in PROPOSAL_INVALID_ARTIFACTS.items():
            summary = summaries[name]
            if summary.get("valid") is not False:
                continue
            path = proposal_paths[name]
            issues.append(
                workspace_issue(
                    code=code,
                    severity="error",
                    detail=str(summary.get("error") or f"{label} is invalid"),
                    next_action=(
                        f"fix {path.relative_to(root).as_posix()} or rerun "
                        f"artist-portrait propose --project {project_path}"
                    ),
                )
            )
    if (
        sources.get("valid") is True
        and output_summary(root / "output" / "material_map.md").get("exists")
        and state.steps.get("propose", StepLedgerEntry()).status == StepStatus.pending
    ):
        issues.append(
            workspace_issue(
                code="proposal_agent_handoff_pending",
                severity="info",
                detail="material map exists but the host-Agent handoff is not prepared",
                next_action=f"artist-portrait propose --project {project_path}",
            )
        )
    if (
        state.steps.get("propose", StepLedgerEntry()).status == StepStatus.blocked
        and output_summary(root / "output" / "proposal_agent_handoff.json").get("exists")
        and not (root / WORKSPACE_DIR / DATA_DIR / "proposals.json").exists()
    ):
        issues.append(
            workspace_issue(
                code="proposal_agent_candidate_pending",
                severity="info",
                detail=(
                    "host-Agent handoff is ready but no validated ProposalSet has "
                    "been imported"
                ),
                next_action=(
                    f"artist-portrait propose --project {project_path} "
                    "--agent-output <candidate.json>"
                ),
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
    proposal_paths = proposal_artifact_paths(root)
    artifact_paths = {
        "state": root / WORKSPACE_DIR / "state.json",
        "sources": root / WORKSPACE_DIR / DATA_DIR / "sources.jsonl",
        "clips": root / WORKSPACE_DIR / DATA_DIR / "clips.jsonl",
        "transcripts": root / WORKSPACE_DIR / DATA_DIR / "transcripts.jsonl",
        "keyframes": root / WORKSPACE_DIR / DATA_DIR / "keyframes.jsonl",
        "analysis": root / WORKSPACE_DIR / DATA_DIR / "analysis.jsonl",
        "relations": root / WORKSPACE_DIR / DATA_DIR / "relations.jsonl",
        **{
            ("proposals_json" if name == "proposals" else name): path
            for name, path in proposal_paths.items()
        },
        "run_report": root / "output" / "run_report.md",
        "scan_report": root / "output" / "scan_report.md",
        "clip_report": root / "output" / "clip_report.md",
        "analysis_report": root / "output" / "analysis_report.md",
        "material_map": root / "output" / "material_map.md",
        "proposals_md": root / "output" / "proposals.md",
        "proposal_review": root / "output" / "proposal_review.md",
        "proposal_agent_handoff": root / "output" / "proposal_agent_handoff.json",
        "timeline_draft": root / "output" / "timeline_draft.json",
        "bgm_candidates": root / WORKSPACE_DIR / DATA_DIR / "bgm_candidates.json",
        "bgm_analysis": root / ".artist-portrait/data/bgm_analysis.json",
        "bgm_analysis_report": root / "output/bgm_analysis_report.md",
        "bgm_recommendations": root / ".artist-portrait/data/bgm_recommendations.json",
        "bgm_fit": root / WORKSPACE_DIR / DATA_DIR / "bgm_fit.json",
        "preview_manifest": root / WORKSPACE_DIR / DATA_DIR / "preview_manifest.json",
        "preview_validation": root / WORKSPACE_DIR / DATA_DIR / "preview_validation.json",
        "preview_lowres": root / "output" / "preview_lowres.mp4",
        "final_export_manifest": root / WORKSPACE_DIR / DATA_DIR / "final_export_manifest.json",
        "final_export_validation": root / WORKSPACE_DIR / DATA_DIR / "final_export_validation.json",
        "final_export": root / "output" / "final_export.mp4",
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
        StepStatus.blocked,
    }
    for step_name, entry in sorted(state.steps.items()):
        if entry.status not in completed_statuses:
            continue
        seen_refs: set[str] = set()
        for output_ref in entry.output_refs:
            if not output_ref:
                continue
            if output_ref in seen_refs:
                issues.append(
                    artifact_issue(
                        step=step_name,
                        ref=output_ref,
                        code="duplicate_output_ref",
                        severity="warning",
                        detail=(
                            f"step `{step_name}` lists output `{output_ref}` more than once"
                        ),
                    )
                )
                continue
            seen_refs.add(output_ref)
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
    clip_report_path = root / "output" / "clip_report.md"
    material_map_path = root / "output" / "material_map.md"
    risk_report_path = root / "output" / "risk_report.md"
    proposal_agent_handoff_path = root / "output" / "proposal_agent_handoff.json"
    proposal_quarantine_dir = root / WORKSPACE_DIR / "quarantine" / "proposals"
    proposal_paths = proposal_artifact_paths(root)
    timeline_path = root / "output" / "timeline_draft.json"
    timeline_validation_path = root / WORKSPACE_DIR / DATA_DIR / "timeline_validation.json"
    bgm_candidates_path = root / WORKSPACE_DIR / DATA_DIR / "bgm_candidates.json"
    bgm_fit_path = root / WORKSPACE_DIR / DATA_DIR / "bgm_fit.json"
    preview_manifest_path = root / WORKSPACE_DIR / DATA_DIR / "preview_manifest.json"
    preview_validation_path = root / WORKSPACE_DIR / DATA_DIR / "preview_validation.json"
    final_export_manifest_path = root / WORKSPACE_DIR / DATA_DIR / "final_export_manifest.json"
    final_export_validation_path = root / WORKSPACE_DIR / DATA_DIR / "final_export_validation.json"
    return {
        "sources": source_summary(sources_path),
        "clips": clip_summary(clips_path),
        "transcripts": transcript_summary(transcripts_path),
        "keyframes": keyframe_summary(keyframes_path, root=root),
        "analysis": analysis_summary(analysis_path),
        "scan_report": output_summary(root / "output" / "scan_report.md"),
        "clip_report": output_summary(clip_report_path),
        "analysis_report": output_summary(root / "output" / "analysis_report.md"),
        "material_map": output_summary(material_map_path),
        "proposal_agent_handoff": output_summary(proposal_agent_handoff_path),
        "proposal_agent_quarantine": directory_summary(proposal_quarantine_dir),
        **proposal_status_summaries(proposal_paths),
        "timeline": timeline_summary(timeline_path),
        "timeline_validation": timeline_validation_summary(timeline_validation_path),
        "timeline_review": output_summary(root / "output" / "timeline_review.md"),
        "bgm_candidates": bgm_candidates_summary(bgm_candidates_path),
        "bgm_analysis": bgm_analysis_summary(root / ".artist-portrait/data/bgm_analysis.json"),
        "bgm_analysis_report": output_summary(root / "output" / "bgm_analysis_report.md"),
        "bgm_recommendations": bgm_recommendation_summary(root / ".artist-portrait/data/bgm_recommendations.json"),
        "bgm_fit": bgm_fit_summary(bgm_fit_path),
        "preview": preview_manifest_summary(preview_manifest_path),
        "preview_validation": preview_validation_summary(preview_validation_path),
        "preview_review": output_summary(root / "output" / "preview_review.md"),
        "final_export": final_export_manifest_summary(final_export_manifest_path),
        "final_export_validation": final_export_validation_summary(final_export_validation_path),
        "final_export_review": output_summary(root / "output" / "final_export_review.md"),
        "risk_report": output_summary(risk_report_path),
    }


def directory_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    files = sorted(item for item in path.iterdir() if item.is_file())
    return {
        "exists": True,
        "valid": True,
        "file_count": len(files),
        "bytes": sum(item.stat().st_size for item in files),
        "latest": files[-1].name if files else None,
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
        return ProposalSet.model_validate(read_proposal_artifact("proposals", path))
    except ValueError as exc:
        raise WorkspacePrerequisiteError(str(exc)) from exc


def read_proposal_context_json(path: Path) -> ProposalContext:
    try:
        return ProposalContext.model_validate(
            read_proposal_artifact("proposal_context", path)
        )
    except ValueError as exc:
        raise WorkspacePrerequisiteError(str(exc)) from exc


def read_text_model_gate_json(path: Path) -> TextModelGate:
    try:
        return TextModelGate.model_validate(
            read_proposal_artifact("text_model_gate", path)
        )
    except ValueError as exc:
        raise WorkspacePrerequisiteError(str(exc)) from exc


def read_proposal_request_json(path: Path) -> ProposalRequestPacket:
    try:
        return ProposalRequestPacket.model_validate(
            read_proposal_artifact("proposal_request", path)
        )
    except ValueError as exc:
        raise WorkspacePrerequisiteError(str(exc)) from exc


def read_proposal_adapter_check_json(path: Path) -> ProposalAdapterCheck:
    try:
        return ProposalAdapterCheck.model_validate(
            read_proposal_artifact("proposal_adapter_check", path)
        )
    except ValueError as exc:
        raise WorkspacePrerequisiteError(str(exc)) from exc


def read_proposal_provider_registry_json(path: Path) -> ProposalProviderRegistry:
    try:
        return ProposalProviderRegistry.model_validate(
            read_proposal_artifact("proposal_provider_registry", path)
        )
    except ValueError as exc:
        raise WorkspacePrerequisiteError(str(exc)) from exc


def read_proposal_mock_adapter_handshake_json(path: Path) -> ProposalMockAdapterHandshake:
    try:
        return ProposalMockAdapterHandshake.model_validate(
            read_proposal_artifact("proposal_mock_adapter_handshake", path)
        )
    except ValueError as exc:
        raise WorkspacePrerequisiteError(str(exc)) from exc


def read_proposal_execution_approval_request_json(
    path: Path,
) -> ProposalExecutionApprovalRequest:
    try:
        return ProposalExecutionApprovalRequest.model_validate(
            read_proposal_artifact("proposal_execution_approval_request", path)
        )
    except ValueError as exc:
        raise WorkspacePrerequisiteError(str(exc)) from exc


def read_proposal_execution_approval_record_json(
    path: Path,
) -> ProposalExecutionApprovalRecord:
    try:
        return ProposalExecutionApprovalRecord.model_validate(
            read_proposal_artifact("proposal_execution_approval_record", path)
        )
    except ValueError as exc:
        raise WorkspacePrerequisiteError(str(exc)) from exc


def read_proposal_execution_readiness_plan_json(
    path: Path,
) -> ProposalExecutionReadinessPlan:
    try:
        return ProposalExecutionReadinessPlan.model_validate(
            read_proposal_artifact("proposal_execution_readiness_plan", path)
        )
    except ValueError as exc:
        raise WorkspacePrerequisiteError(str(exc)) from exc


def read_proposal_execution_input_bundle_json(
    path: Path,
) -> ProposalExecutionInputBundle:
    try:
        return ProposalExecutionInputBundle.model_validate(
            read_proposal_artifact("proposal_execution_input_bundle", path)
        )
    except ValueError as exc:
        raise WorkspacePrerequisiteError(str(exc)) from exc


def read_proposal_provider_call_dry_run_json(
    path: Path,
) -> ProposalProviderCallDryRun:
    try:
        return ProposalProviderCallDryRun.model_validate(
            read_proposal_artifact("proposal_provider_call_dry_run", path)
        )
    except ValueError as exc:
        raise WorkspacePrerequisiteError(str(exc)) from exc


def read_proposal_execution_authorization_json(path: Path) -> ProposalExecutionAuthorization:
    try:
        return ProposalExecutionAuthorization.model_validate(
            read_proposal_artifact("proposal_execution_authorization", path)
        )
    except ValueError as exc:
        raise WorkspacePrerequisiteError(str(exc)) from exc


def read_proposal_provider_response_intake_plan_json(
    path: Path,
) -> ProposalProviderResponseIntakePlan:
    try:
        return ProposalProviderResponseIntakePlan.model_validate(
            read_proposal_artifact("proposal_provider_response_intake_plan", path)
        )
    except ValueError as exc:
        raise WorkspacePrerequisiteError(str(exc)) from exc


def read_proposal_provider_output_quarantine_json(
    path: Path,
) -> ProposalProviderOutputQuarantine:
    try:
        return ProposalProviderOutputQuarantine.model_validate(
            read_proposal_artifact("proposal_provider_output_quarantine", path)
        )
    except ValueError as exc:
        raise WorkspacePrerequisiteError(str(exc)) from exc


def read_proposal_provider_response_validation_plan_json(
    path: Path,
) -> ProposalProviderResponseValidationPlan:
    try:
        return ProposalProviderResponseValidationPlan.model_validate(
            read_proposal_artifact(
                "proposal_provider_response_validation_plan",
                path,
            )
        )
    except ValueError as exc:
        raise WorkspacePrerequisiteError(str(exc)) from exc


def read_proposal_promotion_authorization_plan_json(
    path: Path,
) -> ProposalPromotionAuthorizationPlan:
    try:
        return ProposalPromotionAuthorizationPlan.model_validate(
            read_proposal_artifact("proposal_promotion_authorization_plan", path)
        )
    except ValueError as exc:
        raise WorkspacePrerequisiteError(str(exc)) from exc


def read_proposal_promotion_validation_report_json(
    path: Path,
) -> ProposalPromotionValidationReport:
    try:
        return ProposalPromotionValidationReport.model_validate(
            read_proposal_artifact("proposal_promotion_validation_report", path)
        )
    except ValueError as exc:
        raise WorkspacePrerequisiteError(str(exc)) from exc


def read_proposal_canonical_write_transaction_plan_json(
    path: Path,
) -> ProposalCanonicalWriteTransactionPlan:
    try:
        return ProposalCanonicalWriteTransactionPlan.model_validate(
            read_proposal_artifact(
                "proposal_canonical_write_transaction_plan",
                path,
            )
        )
    except ValueError as exc:
        raise WorkspacePrerequisiteError(str(exc)) from exc


def read_proposal_provider_result_json(path: Path) -> ProposalProviderResultEnvelope:
    try:
        return ProposalProviderResultEnvelope.model_validate(
            read_proposal_artifact("proposal_provider_result", path)
        )
    except ValueError as exc:
        raise WorkspacePrerequisiteError(str(exc)) from exc


def read_proposal_validation_json(path: Path) -> ProposalValidationReport:
    try:
        return ProposalValidationReport.model_validate(
            read_proposal_artifact("proposal_validation", path)
        )
    except ValueError as exc:
        raise WorkspacePrerequisiteError(str(exc)) from exc


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


def timeline_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        timeline = TimelineDraft.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"exists": True, "valid": False, "error": f"invalid TimelineDraft JSON: {exc}"}
    return {
        "exists": True,
        "valid": True,
        "timeline_id": timeline.timeline_id,
        "proposal_id": timeline.proposal_id.value,
        "segment_count": len(timeline.segments),
        "actual_duration": timeline.actual_duration,
        "music_status": timeline.music_plan.status.value,
    }


def timeline_validation_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        report = TimelineValidationReport.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": f"invalid TimelineValidationReport JSON: {exc}",
        }
    return {
        "exists": True,
        "valid": True,
        "proposal_id": report.proposal_id.value,
        "issue_count": report.issue_count,
        "error_count": report.error_count,
        "warning_count": report.warning_count,
        "timeline_valid": report.valid,
    }


def bgm_candidates_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        ledger = BgmCandidateLedger.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": f"invalid BgmCandidateLedger JSON: {exc}",
        }
    return {
        "exists": True,
        "valid": True,
        "count": len(ledger.candidates),
        "candidate_ids": [item.music_candidate_id for item in ledger.candidates],
    }


def bgm_fit_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        plan = BgmFitPlan.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": f"invalid BgmFitPlan JSON: {exc}",
        }
    return {
        "exists": True,
        "valid": True,
        "fit_id": plan.fit_id,
        "candidate_id": plan.music_candidate_id,
        "fit_mode": plan.fit_mode,
        "target_duration": plan.target_duration,
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


def proposal_request_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        request = read_proposal_request_json(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    return {
        "exists": True,
        "valid": True,
        "request_id": request.request_id,
        "status": request.status.value,
        "target_schema_name": request.target_schema_name,
        "required_proposal_ids": request.required_proposal_ids,
        "blocking_reasons": request.blocking_reasons,
    }


def proposal_adapter_check_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        check = read_proposal_adapter_check_json(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    return {
        "exists": True,
        "valid": True,
        "check_id": check.check_id,
        "status": check.status.value,
        "provider": check.provider,
        "provider_mode": check.provider_mode,
        "issue_count": len(check.issues),
        "model_call_performed": check.model_call_performed,
        "network_performed": check.network_performed,
    }


def proposal_provider_registry_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        registry = read_proposal_provider_registry_json(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    return {
        "exists": True,
        "valid": True,
        "registry_id": registry.registry_id,
        "selected_provider_id": registry.selected_provider_id,
        "provider_count": len(registry.providers),
        "generation_open": registry.generation_open,
        "model_call_performed": registry.model_call_performed,
        "network_performed": registry.network_performed,
    }


def proposal_mock_adapter_handshake_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        handshake = read_proposal_mock_adapter_handshake_json(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    return {
        "exists": True,
        "valid": True,
        "handshake_id": handshake.handshake_id,
        "status": handshake.status.value,
        "provider_id": handshake.provider_id,
        "issue_count": len(handshake.issues),
        "model_call_performed": handshake.model_call_performed,
        "network_performed": handshake.network_performed,
        "proposal_content_generated": handshake.proposal_content_generated,
    }


def proposal_execution_approval_request_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        approval = read_proposal_execution_approval_request_json(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    return {
        "exists": True,
        "valid": True,
        "approval_request_id": approval.approval_request_id,
        "status": approval.status.value,
        "provider_id": approval.provider_id,
        "approval_recorded": approval.approval_recorded,
        "selected_secret_source": approval.selected_secret_source,
        "credential_value_read": approval.credential_value_read,
        "network_allowed": approval.network_allowed,
        "model_call_allowed": approval.model_call_allowed,
        "execution_performed": approval.execution_performed,
        "model_call_performed": approval.model_call_performed,
        "network_performed": approval.network_performed,
        "proposal_content_generated": approval.proposal_content_generated,
        "issue_count": len(approval.issues),
    }


def proposal_execution_approval_record_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        record = read_proposal_execution_approval_record_json(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    return {
        "exists": True,
        "valid": True,
        "approval_record_id": record.approval_record_id,
        "status": record.status.value,
        "provider_id": record.provider_id,
        "approval_granted": record.approval_granted,
        "approval_actor": record.approval_actor,
        "selected_secret_source": record.selected_secret_source,
        "credential_value_read": record.credential_value_read,
        "network_allowed": record.network_allowed,
        "model_call_allowed": record.model_call_allowed,
        "execution_allowed": record.execution_allowed,
        "execution_performed": record.execution_performed,
        "model_call_performed": record.model_call_performed,
        "network_performed": record.network_performed,
        "proposal_content_generated": record.proposal_content_generated,
        "issue_count": len(record.issues),
    }


def proposal_execution_readiness_plan_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        plan = read_proposal_execution_readiness_plan_json(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    stages = [
        plan.secret_source_selection,
        plan.credential_access,
        plan.execution_plan,
        plan.provider_call_preflight,
        plan.output_capture_plan,
    ]
    return {
        "exists": True,
        "valid": True,
        "readiness_plan_id": plan.readiness_plan_id,
        "status": plan.status.value,
        "provider_id": plan.provider_id,
        "stage_count": len(stages),
        "blocked_stage_count": sum(
            1 for stage in stages if stage.status == ProposalExecutionReadinessPlanStatus.blocked
        ),
        "selected_secret_source": plan.selected_secret_source,
        "credential_value_read": plan.credential_value_read,
        "execution_allowed": plan.execution_allowed,
        "execution_performed": plan.execution_performed,
        "model_call_performed": plan.model_call_performed,
        "network_performed": plan.network_performed,
        "raw_output_captured": plan.raw_output_captured,
        "proposal_content_generated": plan.proposal_content_generated,
        "issue_count": len(plan.issues),
    }


def proposal_execution_input_bundle_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        bundle = read_proposal_execution_input_bundle_json(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    items = [
        bundle.provider_identity,
        bundle.request_packet,
        bundle.prompt_contract,
        bundle.schema_contract,
        bundle.approval_chain,
        bundle.secret_reference,
        bundle.credential_access_policy,
        bundle.network_policy,
        bundle.quarantine_target,
        bundle.output_routing,
    ]
    return {
        "exists": True,
        "valid": True,
        "bundle_id": bundle.bundle_id,
        "status": bundle.status.value,
        "provider_id": bundle.provider_id,
        "item_count": len(items),
        "blocked_item_count": sum(
            1
            for item in items
            if item.status == ProposalExecutionInputBundleStatus.blocked
        ),
        "selected_secret_source": bundle.selected_secret_source,
        "credential_value_read": bundle.credential_value_read,
        "execution_allowed": bundle.execution_allowed,
        "execution_performed": bundle.execution_performed,
        "model_call_performed": bundle.model_call_performed,
        "network_performed": bundle.network_performed,
        "raw_output_captured": bundle.raw_output_captured,
        "proposal_content_generated": bundle.proposal_content_generated,
        "prompt_embedded": bundle.prompt_embedded,
        "issue_count": len(bundle.issues),
    }


def proposal_provider_call_dry_run_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        dry_run = read_proposal_provider_call_dry_run_json(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    items = [
        dry_run.endpoint_reference,
        dry_run.auth_header_policy,
        dry_run.request_body_reference,
        dry_run.timeout_policy,
        dry_run.retry_policy,
        dry_run.rate_limit_policy,
        dry_run.idempotency_policy,
        dry_run.network_egress_policy,
        dry_run.response_capture_policy,
        dry_run.failure_handling_policy,
    ]
    return {
        "exists": True,
        "valid": True,
        "dry_run_id": dry_run.dry_run_id,
        "status": dry_run.status.value,
        "provider_id": dry_run.provider_id,
        "item_count": len(items),
        "blocked_item_count": sum(
            1
            for item in items
            if item.status == ProposalProviderCallDryRunStatus.blocked
        ),
        "endpoint_resolved": dry_run.endpoint_resolved,
        "auth_header_materialized": dry_run.auth_header_materialized,
        "request_body_materialized": dry_run.request_body_materialized,
        "credential_value_read": dry_run.credential_value_read,
        "execution_allowed": dry_run.execution_allowed,
        "execution_performed": dry_run.execution_performed,
        "model_call_performed": dry_run.model_call_performed,
        "network_performed": dry_run.network_performed,
        "raw_output_captured": dry_run.raw_output_captured,
        "request_payload_sent": dry_run.request_payload_sent,
        "proposal_content_generated": dry_run.proposal_content_generated,
        "issue_count": len(dry_run.issues),
    }


def proposal_execution_authorization_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        authorization = read_proposal_execution_authorization_json(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    return {
        "exists": True,
        "valid": True,
        "authorization_id": authorization.authorization_id,
        "status": authorization.status.value,
        "provider_id": authorization.provider_id,
        "approved_execution_gate": authorization.approved_execution_gate,
        "user_approval_present": authorization.user_approval_present,
        "network_allowed": authorization.network_allowed,
        "model_call_allowed": authorization.model_call_allowed,
        "execution_performed": authorization.execution_performed,
        "model_call_performed": authorization.model_call_performed,
        "network_performed": authorization.network_performed,
        "proposal_content_generated": authorization.proposal_content_generated,
        "issue_count": len(authorization.issues),
    }


def proposal_provider_response_intake_plan_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        intake = read_proposal_provider_response_intake_plan_json(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    items = [
        intake.response_channel,
        intake.raw_output_location,
        intake.content_type_policy,
        intake.size_limit_policy,
        intake.checksum_policy,
        intake.redaction_policy,
        intake.parser_selection,
        intake.validation_queue,
        intake.promotion_gate,
        intake.audit_trail,
    ]
    return {
        "exists": True,
        "valid": True,
        "intake_id": intake.intake_id,
        "status": intake.status.value,
        "provider_id": intake.provider_id,
        "item_count": len(items),
        "blocked_item_count": sum(
            1
            for item in items
            if item.status == ProposalProviderResponseIntakeStatus.blocked
        ),
        "response_channel_open": intake.response_channel_open,
        "raw_output_location_materialized": intake.raw_output_location_materialized,
        "content_type_validated": intake.content_type_validated,
        "checksum_computed": intake.checksum_computed,
        "redaction_performed": intake.redaction_performed,
        "parser_selected": intake.parser_selected,
        "validation_enqueued": intake.validation_enqueued,
        "promotion_allowed": intake.promotion_allowed,
        "audit_event_written": intake.audit_event_written,
        "raw_output_captured": intake.raw_output_captured,
        "parsed_payload_generated": intake.parsed_payload_generated,
        "validation_performed": intake.validation_performed,
        "promoted_to_proposals": intake.promoted_to_proposals,
        "model_call_performed": intake.model_call_performed,
        "network_performed": intake.network_performed,
        "proposal_content_generated": intake.proposal_content_generated,
        "issue_count": len(intake.issues),
    }


def proposal_provider_output_quarantine_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        quarantine = read_proposal_provider_output_quarantine_json(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    return {
        "exists": True,
        "valid": True,
        "quarantine_id": quarantine.quarantine_id,
        "status": quarantine.status.value,
        "provider_id": quarantine.provider_id,
        "raw_output_captured": quarantine.raw_output_captured,
        "raw_output_bytes": quarantine.raw_output_bytes,
        "parsed_payload_generated": quarantine.parsed_payload_generated,
        "promoted_to_proposals": quarantine.promoted_to_proposals,
        "validation_performed": quarantine.validation_performed,
        "model_call_performed": quarantine.model_call_performed,
        "network_performed": quarantine.network_performed,
        "proposal_content_generated": quarantine.proposal_content_generated,
        "issue_count": len(quarantine.issues),
    }


def proposal_provider_response_validation_plan_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        plan = read_proposal_provider_response_validation_plan_json(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    items = [
        plan.quarantine_input_binding,
        plan.content_type_check,
        plan.size_limit_check,
        plan.checksum_verification,
        plan.redaction_verification,
        plan.parser_contract,
        plan.json_syntax_validation,
        plan.schema_validation,
        plan.semantic_validation,
        plan.promotion_decision,
    ]
    return {
        "exists": True,
        "valid": True,
        "validation_plan_id": plan.validation_plan_id,
        "status": plan.status.value,
        "provider_id": plan.provider_id,
        "item_count": len(items),
        "blocked_item_count": sum(
            1
            for item in items
            if item.status == ProposalProviderResponseValidationStatus.blocked
        ),
        "quarantine_input_bound": plan.quarantine_input_bound,
        "raw_output_read": plan.raw_output_read,
        "parsed_payload_generated": plan.parsed_payload_generated,
        "validation_performed": plan.validation_performed,
        "promoted_to_proposals": plan.promoted_to_proposals,
        "model_call_performed": plan.model_call_performed,
        "network_performed": plan.network_performed,
        "proposal_content_generated": plan.proposal_content_generated,
        "issue_count": len(plan.issues),
    }


def proposal_promotion_authorization_plan_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        plan = read_proposal_promotion_authorization_plan_json(path)
    except Exception as exc:
        return {"exists": True, "valid": False, "error": str(exc)}
    items = [
        plan.validation_report_binding,
        plan.schema_validation_requirement,
        plan.semantic_validation_requirement,
        plan.evidence_validation_requirement,
        plan.risk_acceptance_requirement,
        plan.proposal_identity_requirement,
        plan.overwrite_policy,
        plan.atomic_write_policy,
        plan.provenance_binding,
        plan.final_promotion_authorization,
    ]
    return {
        "exists": True,
        "valid": True,
        "promotion_plan_id": plan.promotion_plan_id,
        "status": plan.status.value,
        "provider_id": plan.provider_id,
        "item_count": len(items),
        "blocked_item_count": sum(
            1
            for item in items
            if item.status == ProposalPromotionAuthorizationStatus.blocked
        ),
        "validation_report_bound": plan.validation_report_bound,
        "promotion_authorized": plan.promotion_authorized,
        "promotion_performed": plan.promotion_performed,
        "proposals_file_written": plan.proposals_file_written,
        "model_call_performed": plan.model_call_performed,
        "network_performed": plan.network_performed,
        "proposal_content_generated": plan.proposal_content_generated,
        "issue_count": len(plan.issues),
    }


def proposal_promotion_validation_report_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        report = read_proposal_promotion_validation_report_json(path)
    except Exception as exc:
        return {"exists": True, "valid": False, "error": str(exc)}
    checks = [
        report.input_binding_check,
        report.schema_result_check,
        report.semantic_result_check,
        report.evidence_traceability_check,
        report.risk_result_check,
        report.proposal_identity_check,
        report.overwrite_conflict_check,
        report.atomic_write_readiness_check,
        report.provenance_integrity_check,
        report.final_authorization_check,
    ]
    return {
        "exists": True,
        "valid": True,
        "report_id": report.report_id,
        "status": report.status.value,
        "provider_id": report.provider_id,
        "check_count": len(checks),
        "blocked_check_count": sum(
            1
            for check in checks
            if check.status == ProposalPromotionValidationReportStatus.blocked
        ),
        "checks_performed": report.checks_performed,
        "checks_passed": report.checks_passed,
        "overall_passed": report.overall_passed,
        "promotion_recommended": report.promotion_recommended,
        "promotion_authorized": report.promotion_authorized,
        "promotion_performed": report.promotion_performed,
        "proposals_file_written": report.proposals_file_written,
        "issue_count": len(report.issues),
    }


def proposal_canonical_write_transaction_plan_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        plan = read_proposal_canonical_write_transaction_plan_json(path)
    except Exception as exc:
        return {"exists": True, "valid": False, "error": str(exc)}
    items = [
        plan.target_lock,
        plan.prewrite_snapshot,
        plan.temporary_file,
        plan.schema_prewrite_check,
        plan.durability_policy,
        plan.atomic_replace,
        plan.conflict_detection,
        plan.rollback_plan,
        plan.audit_commit,
        plan.postcommit_verification,
    ]
    return {
        "exists": True,
        "valid": True,
        "transaction_plan_id": plan.transaction_plan_id,
        "status": plan.status.value,
        "item_count": len(items),
        "blocked_item_count": sum(
            1
            for item in items
            if item.status == ProposalCanonicalWriteTransactionStatus.blocked
        ),
        "transaction_started": plan.transaction_started,
        "transaction_committed": plan.transaction_committed,
        "rollback_performed": plan.rollback_performed,
        "proposals_file_written": plan.proposals_file_written,
        "issue_count": len(plan.issues),
    }


def proposal_provider_result_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        result = read_proposal_provider_result_json(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    return {
        "exists": True,
        "valid": True,
        "result_id": result.result_id,
        "status": result.status.value,
        "provider_id": result.provider_id,
        "issue_count": len(result.issues),
        "payload_generated": result.payload_generated,
        "validation_performed": result.validation_performed,
        "model_call_performed": result.model_call_performed,
        "network_performed": result.network_performed,
        "proposal_content_generated": result.proposal_content_generated,
    }


def proposal_validation_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        report = read_proposal_validation_json(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    return {
        "exists": True,
        "valid": True,
        "report_id": report.report_id,
        "proposal_set_id": report.proposal_set_id,
        "proposal_count": report.proposal_count,
        "issue_count": report.issue_count,
        "error_count": report.error_count,
        "warning_count": report.warning_count,
    }


PROPOSAL_SUMMARY_READERS = {
    "proposal_context": proposal_context_summary,
    "text_model_gate": text_model_gate_summary,
    "proposal_request": proposal_request_summary,
    "proposal_adapter_check": proposal_adapter_check_summary,
    "proposal_provider_registry": proposal_provider_registry_summary,
    "proposal_mock_adapter_handshake": proposal_mock_adapter_handshake_summary,
    "proposal_execution_approval_request": proposal_execution_approval_request_summary,
    "proposal_execution_approval_record": proposal_execution_approval_record_summary,
    "proposal_execution_readiness_plan": proposal_execution_readiness_plan_summary,
    "proposal_execution_input_bundle": proposal_execution_input_bundle_summary,
    "proposal_provider_call_dry_run": proposal_provider_call_dry_run_summary,
    "proposal_execution_authorization": proposal_execution_authorization_summary,
    "proposal_provider_response_intake_plan": proposal_provider_response_intake_plan_summary,
    "proposal_provider_output_quarantine": proposal_provider_output_quarantine_summary,
    "proposal_provider_response_validation_plan": proposal_provider_response_validation_plan_summary,
    "proposal_promotion_authorization_plan": proposal_promotion_authorization_plan_summary,
    "proposal_promotion_validation_report": proposal_promotion_validation_report_summary,
    "proposal_canonical_write_transaction_plan": proposal_canonical_write_transaction_plan_summary,
    "proposal_provider_result": proposal_provider_result_summary,
    "proposals": proposal_summary,
    "proposal_validation": proposal_validation_summary,
}


def proposal_status_summaries(paths: dict[str, Path]) -> dict[str, dict]:
    return {
        name: PROPOSAL_SUMMARY_READERS[name](paths[name])
        for name in PROPOSAL_SUMMARY_READERS
    }


def stable_context_id(project_id: str, input_fingerprint: str) -> str:
    payload = f"{project_id}:{input_fingerprint}"
    return "ctx_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def stable_gate_id(project_id: str, proposal_context_fingerprint: str) -> str:
    payload = f"{project_id}:{proposal_context_fingerprint}"
    return "gate_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def stable_request_id(project_id: str, request_fingerprint: str) -> str:
    payload = f"{project_id}:{request_fingerprint}"
    return "preq_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def stable_adapter_check_id(project_id: str, request_fingerprint: str) -> str:
    payload = f"{project_id}:{request_fingerprint}"
    return "pachk_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def stable_provider_registry_id(project_id: str, registry_fingerprint: str) -> str:
    payload = f"{project_id}:{registry_fingerprint}"
    return "preg_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def stable_mock_handshake_id(project_id: str, handshake_fingerprint: str) -> str:
    payload = f"{project_id}:{handshake_fingerprint}"
    return "pmock_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def stable_execution_approval_request_id(
    project_id: str,
    approval_fingerprint: str,
) -> str:
    payload = f"{project_id}:{approval_fingerprint}"
    return "papp_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def stable_execution_approval_record_id(
    project_id: str,
    approval_record_fingerprint: str,
) -> str:
    payload = f"{project_id}:{approval_record_fingerprint}"
    return "parec_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def stable_execution_readiness_plan_id(
    project_id: str,
    readiness_fingerprint: str,
) -> str:
    payload = f"{project_id}:{readiness_fingerprint}"
    return "pread_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def stable_execution_input_bundle_id(
    project_id: str,
    input_fingerprint: str,
) -> str:
    payload = f"{project_id}:{input_fingerprint}"
    return "pinp_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def stable_provider_call_dry_run_id(
    project_id: str,
    dry_run_fingerprint: str,
) -> str:
    payload = f"{project_id}:{dry_run_fingerprint}"
    return "pcall_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def stable_execution_authorization_id(
    project_id: str,
    authorization_fingerprint: str,
) -> str:
    payload = f"{project_id}:{authorization_fingerprint}"
    return "pexec_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def stable_provider_response_intake_id(
    project_id: str,
    intake_fingerprint: str,
) -> str:
    payload = f"{project_id}:{intake_fingerprint}"
    return "pint_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def stable_provider_output_quarantine_id(
    project_id: str,
    quarantine_fingerprint: str,
) -> str:
    payload = f"{project_id}:{quarantine_fingerprint}"
    return "pquar_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def stable_provider_response_validation_id(
    project_id: str,
    validation_fingerprint: str,
) -> str:
    payload = f"{project_id}:{validation_fingerprint}"
    return "pval_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def stable_promotion_authorization_id(
    project_id: str,
    promotion_fingerprint: str,
) -> str:
    payload = f"{project_id}:{promotion_fingerprint}"
    return "pprom_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def stable_promotion_validation_report_id(
    project_id: str,
    report_fingerprint: str,
) -> str:
    payload = f"{project_id}:{report_fingerprint}"
    return "pvrpt_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def stable_canonical_write_transaction_id(
    project_id: str,
    transaction_fingerprint: str,
) -> str:
    payload = f"{project_id}:{transaction_fingerprint}"
    return "pcwtx_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def stable_provider_result_id(project_id: str, result_fingerprint: str) -> str:
    payload = f"{project_id}:{result_fingerprint}"
    return "pres_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def stable_proposal_validation_report_id(
    project_id: str,
    input_fingerprint: str,
) -> str:
    payload = f"{project_id}:{input_fingerprint}"
    return "pvr_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


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
            "Proposals must describe BGM strategy without selecting or downloading tracks.",
            "BGM strategy must account for mood, BPM, section structure, pacing, transitions, original audio, speech ducking, and rights status.",
        ],
        blocked_capabilities=[
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


def build_proposal_request_packet(
    *,
    context: ProposalContext,
    text_model_gate: TextModelGate,
    proposal_context_ref: str,
    text_model_gate_ref: str,
    proposal_context_fingerprint: str,
    request_fingerprint: str,
) -> ProposalRequestPacket:
    status = (
        ProposalRequestStatus.ready
        if text_model_gate.status == TextModelGateStatus.ready
        else ProposalRequestStatus.blocked
    )
    target_schema_ref = "schemas/proposal_set.schema.json"
    return ProposalRequestPacket(
        request_id=stable_request_id(context.project_id, request_fingerprint),
        project_id=context.project_id,
        status=status,
        proposal_context_ref=proposal_context_ref,
        text_model_gate_ref=text_model_gate_ref,
        proposal_context_fingerprint=proposal_context_fingerprint,
        request_fingerprint=request_fingerprint,
        target_schema_ref=target_schema_ref,
        target_schema_name="ProposalSet",
        required_proposal_ids=context.proposal_ids_required,
        system_prompt=(
            "You generate evidence-grounded artist portrait video proposal JSON. "
            "Return only a ProposalSet object matching the target JSON Schema."
        ),
        developer_prompt=(
            "Use only the referenced proposal context. Do not invent facts, source IDs, "
            "clip IDs, analysis IDs, rights status, dialogue, dates, or timecodes. "
            "Generate exactly the required proposal IDs as a ProposalSet JSON object. "
            "Cite evidence in every proposal. Respect forbidden_by_user sources and all "
            "content policy constraints."
        ),
        user_prompt=(
            "Draft three distinct proposal records for the project using the prepared "
            "proposal context. Each proposal must include story_structure, "
            "sound_structure, visual_motifs, risks, missing_material, and "
            "minimum_viable_timeline fields. The sound_structure must describe BGM "
            "strategy, original audio treatment, pacing, transitions, and speech/music "
            "balance without choosing tracks or fitting a timeline."
        ),
        evidence=[
            {"type": "proposal_context", "ref": proposal_context_ref},
            {"type": "text_model_gate", "ref": text_model_gate_ref},
            {"type": "schema", "ref": target_schema_ref},
        ],
        blocked_capabilities=context.blocked_capabilities,
        bgm_requirements=context.bgm_requirements,
        validation_requirements=[
            "Output must validate as ProposalSet.",
            "Every proposal must cite at least one valid clip and one valid fact ref.",
            "Do not cite sources, clips, analyses, or ledgers absent from proposal_context.",
            "Do not use forbidden_by_user sources.",
            "sound_structure must explicitly include BGM/music strategy.",
        ],
        refusal_requirements=[
            "If evidence is insufficient, state missing_material inside each proposal.",
            "Do not fabricate missing evidence to satisfy a proposal field.",
            "Do not emit prose outside the ProposalSet JSON object.",
        ],
        blocking_reasons=text_model_gate.reasons,
    )


def write_proposal_request_json(root: Path, request: ProposalRequestPacket) -> Path:
    output = root / WORKSPACE_DIR / DATA_DIR / "proposal_request.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(request.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def contains_plaintext_secret(text: str) -> bool:
    markers = (
        "sk-",
        "sk-proj-",
        "OPENAI_API_KEY=",
        "ANTHROPIC_API_KEY=",
        "GEMINI_API_KEY=",
        "api_key:",
        "apiKey",
    )
    return any(marker in text for marker in markers)


def proposal_adapter_issue(
    *,
    code: str,
    severity: str,
    detail: str,
    ref: str | None = None,
) -> ProposalAdapterCheckIssue:
    return ProposalAdapterCheckIssue(
        code=code,
        severity=severity,
        detail=detail,
        ref=ref,
    )


def build_proposal_adapter_check(
    *,
    project_id: str,
    request: ProposalRequestPacket,
    request_ref: str,
    request_path: Path,
    checked_paths: list[tuple[str, Path]],
) -> ProposalAdapterCheck:
    issues: list[ProposalAdapterCheckIssue] = [
        proposal_adapter_issue(
            code="model_execution_closed_current_gate",
            severity="warning",
            detail="current gate prepares adapter inputs but does not execute model calls",
        )
    ]
    if request.status == ProposalRequestStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="proposal_request_blocked",
                severity="error",
                detail="proposal request is blocked by text-model gate reasons",
                ref=request_ref,
            )
        )
    for ref, path in checked_paths:
        if path.exists() and contains_plaintext_secret(path.read_text(encoding="utf-8")):
            issues.append(
                proposal_adapter_issue(
                    code="plaintext_secret_material_detected",
                    severity="error",
                    detail="checked project artifact appears to contain plaintext secret material",
                    ref=ref,
                )
            )
    status = (
        ProposalAdapterCheckStatus.ready_for_future_adapter
        if request.status == ProposalRequestStatus.ready
        and not any(issue.severity == "error" for issue in issues)
        else ProposalAdapterCheckStatus.blocked
    )
    return ProposalAdapterCheck(
        check_id=stable_adapter_check_id(project_id, request.request_fingerprint),
        project_id=project_id,
        status=status,
        provider="unconfigured",
        provider_mode="dry_run_contract_only",
        request_ref=request_ref,
        request_status=request.status.value,
        request_fingerprint=request.request_fingerprint,
        target_schema_ref=request.target_schema_ref,
        secret_policy="future adapters must use environment, keychain, or encrypted secret flow; plaintext project files are rejected",
        allowed_secret_sources=[
            "environment_variable_name_only",
            "os_keychain_reference",
            "encrypted_secret_reference",
        ],
        checked_refs=[ref for ref, _path in checked_paths],
        model_call_performed=False,
        network_performed=False,
        issues=issues,
    )


def write_proposal_adapter_check_json(root: Path, check: ProposalAdapterCheck) -> Path:
    output = root / WORKSPACE_DIR / DATA_DIR / "proposal_adapter_check.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(check.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def build_proposal_provider_registry(
    *,
    project_id: str,
    request_ref: str,
    adapter_check_ref: str,
    request: ProposalRequestPacket,
    registry_fingerprint: str,
) -> ProposalProviderRegistry:
    provider = ProposalProviderRecord(
        provider_id="local_mock",
        provider_type="local_mock_adapter",
        enabled=True,
        execution_mode="dry_run_mock_no_generation",
        secret_source="none_required",
        requires_network=False,
        supports_structured_output=True,
        target_schema_ref=request.target_schema_ref,
        notes=[
            "handshake-only provider for contract validation",
            "does not call a model",
            "does not generate proposals",
        ],
    )
    return ProposalProviderRegistry(
        registry_id=stable_provider_registry_id(project_id, registry_fingerprint),
        project_id=project_id,
        request_ref=request_ref,
        adapter_check_ref=adapter_check_ref,
        registry_fingerprint=registry_fingerprint,
        selected_provider_id=provider.provider_id,
        providers=[provider],
        generation_open=False,
        model_call_performed=False,
        network_performed=False,
    )


def write_proposal_provider_registry_json(
    root: Path,
    registry: ProposalProviderRegistry,
) -> Path:
    output = root / WORKSPACE_DIR / DATA_DIR / "proposal_provider_registry.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(registry.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def build_proposal_mock_adapter_handshake(
    *,
    project_id: str,
    request: ProposalRequestPacket,
    request_ref: str,
    adapter_check: ProposalAdapterCheck,
    adapter_check_ref: str,
    registry: ProposalProviderRegistry,
    registry_ref: str,
    handshake_fingerprint: str,
) -> ProposalMockAdapterHandshake:
    issues: list[ProposalAdapterCheckIssue] = [
        proposal_adapter_issue(
            code="proposal_generation_closed_current_gate",
            severity="warning",
            detail="mock adapter handshake is allowed, but proposal generation remains closed",
        )
    ]
    provider = next(
        item
        for item in registry.providers
        if item.provider_id == registry.selected_provider_id
    )
    if request.status == ProposalRequestStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="proposal_request_blocked",
                severity="error",
                detail="mock adapter cannot proceed because proposal request is blocked",
                ref=request_ref,
            )
        )
    if adapter_check.status == ProposalAdapterCheckStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="adapter_preflight_blocked",
                severity="error",
                detail="mock adapter cannot proceed because adapter preflight is blocked",
                ref=adapter_check_ref,
            )
        )
    if registry.generation_open:
        issues.append(
            proposal_adapter_issue(
                code="generation_unexpectedly_open",
                severity="error",
                detail="mock adapter handshake requires generation_open to remain false",
                ref=registry_ref,
            )
        )
    status = (
        ProposalMockAdapterHandshakeStatus.ready_for_future_execution
        if not any(issue.severity == "error" for issue in issues)
        else ProposalMockAdapterHandshakeStatus.blocked
    )
    return ProposalMockAdapterHandshake(
        handshake_id=stable_mock_handshake_id(project_id, handshake_fingerprint),
        project_id=project_id,
        status=status,
        provider_id=provider.provider_id,
        request_ref=request_ref,
        registry_ref=registry_ref,
        adapter_check_ref=adapter_check_ref,
        handshake_fingerprint=handshake_fingerprint,
        response_contract_ref=request.target_schema_ref,
        model_call_performed=False,
        network_performed=False,
        proposal_content_generated=False,
        issues=issues,
    )


def write_proposal_mock_adapter_handshake_json(
    root: Path,
    handshake: ProposalMockAdapterHandshake,
) -> Path:
    output = root / WORKSPACE_DIR / DATA_DIR / "proposal_mock_adapter_handshake.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(handshake.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def build_proposal_execution_approval_request(
    *,
    project_id: str,
    request: ProposalRequestPacket,
    request_ref: str,
    adapter_check: ProposalAdapterCheck,
    adapter_check_ref: str,
    registry: ProposalProviderRegistry,
    registry_ref: str,
    handshake: ProposalMockAdapterHandshake,
    handshake_ref: str,
    approval_fingerprint: str,
) -> ProposalExecutionApprovalRequest:
    issues: list[ProposalAdapterCheckIssue] = [
        proposal_adapter_issue(
            code="execution_approval_not_recorded_current_gate",
            severity="error",
            detail="provider execution approval is requested but cannot be recorded in the current gate",
        ),
        proposal_adapter_issue(
            code="secret_source_not_selected_current_gate",
            severity="error",
            detail="secret source candidates are listed, but no real secret source is selected in the current gate",
        ),
    ]
    if request.status == ProposalRequestStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="proposal_request_blocked",
                severity="error",
                detail="approval request cannot proceed because proposal request is blocked",
                ref=request_ref,
            )
        )
    if adapter_check.status == ProposalAdapterCheckStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="adapter_preflight_blocked",
                severity="error",
                detail="approval request cannot proceed because adapter preflight is blocked",
                ref=adapter_check_ref,
            )
        )
    if handshake.status == ProposalMockAdapterHandshakeStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="mock_adapter_handshake_blocked",
                severity="error",
                detail="approval request cannot proceed because mock adapter handshake is blocked",
                ref=handshake_ref,
            )
        )
    if registry.generation_open:
        issues.append(
            proposal_adapter_issue(
                code="generation_unexpectedly_open",
                severity="error",
                detail="approval request requires generation_open to remain false",
                ref=registry_ref,
            )
        )
    status = (
        ProposalExecutionApprovalRequestStatus.ready_for_future_authorization
        if not any(issue.severity == "error" for issue in issues)
        else ProposalExecutionApprovalRequestStatus.blocked
    )
    return ProposalExecutionApprovalRequest(
        approval_request_id=stable_execution_approval_request_id(
            project_id,
            approval_fingerprint,
        ),
        project_id=project_id,
        status=status,
        provider_id=registry.selected_provider_id,
        request_ref=request_ref,
        registry_ref=registry_ref,
        handshake_ref=handshake_ref,
        adapter_check_ref=adapter_check_ref,
        approval_fingerprint=approval_fingerprint,
        approval_required=True,
        approval_recorded=False,
        approval_record_ref=None,
        secret_source_selection_required=True,
        allowed_secret_sources=adapter_check.allowed_secret_sources,
        selected_secret_source=None,
        credential_value_read=False,
        credential_value_ref=None,
        network_allowed=False,
        model_call_allowed=False,
        execution_performed=False,
        model_call_performed=False,
        network_performed=False,
        proposal_content_generated=False,
        quarantine_required=True,
        issues=issues,
    )


def write_proposal_execution_approval_request_json(
    root: Path,
    approval: ProposalExecutionApprovalRequest,
) -> Path:
    output = root / WORKSPACE_DIR / DATA_DIR / "proposal_execution_approval_request.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(
            approval.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def build_proposal_execution_approval_record(
    *,
    project_id: str,
    approval_request: ProposalExecutionApprovalRequest,
    approval_request_ref: str,
    approval_record_fingerprint: str,
) -> ProposalExecutionApprovalRecord:
    issues: list[ProposalAdapterCheckIssue] = [
        proposal_adapter_issue(
            code="approval_not_granted_current_gate",
            severity="error",
            detail="approval record contract exists, but approval is not granted in the current gate",
            ref=approval_request_ref,
        ),
        proposal_adapter_issue(
            code="secret_source_not_selected_current_gate",
            severity="error",
            detail="approval record cannot select a real secret source in the current gate",
            ref=approval_request_ref,
        ),
    ]
    if approval_request.status == ProposalExecutionApprovalRequestStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="execution_approval_request_blocked",
                severity="error",
                detail="approval record cannot proceed because approval request is blocked",
                ref=approval_request_ref,
            )
        )
    status = (
        ProposalExecutionApprovalRecordStatus.ready_for_future_execution_authorization
        if not any(issue.severity == "error" for issue in issues)
        else ProposalExecutionApprovalRecordStatus.blocked
    )
    return ProposalExecutionApprovalRecord(
        approval_record_id=stable_execution_approval_record_id(
            project_id,
            approval_record_fingerprint,
        ),
        project_id=project_id,
        status=status,
        provider_id=approval_request.provider_id,
        approval_request_ref=approval_request_ref,
        request_ref=approval_request.request_ref,
        registry_ref=approval_request.registry_ref,
        handshake_ref=approval_request.handshake_ref,
        adapter_check_ref=approval_request.adapter_check_ref,
        approval_record_fingerprint=approval_record_fingerprint,
        approval_granted=False,
        approval_actor=None,
        approval_recorded_at=None,
        approval_scope="none_current_gate",
        allowed_secret_sources=approval_request.allowed_secret_sources,
        selected_secret_source=None,
        credential_value_read=False,
        credential_value_ref=None,
        network_allowed=False,
        model_call_allowed=False,
        execution_allowed=False,
        execution_performed=False,
        model_call_performed=False,
        network_performed=False,
        proposal_content_generated=False,
        quarantine_required=True,
        issues=issues,
    )


def write_proposal_execution_approval_record_json(
    root: Path,
    record: ProposalExecutionApprovalRecord,
) -> Path:
    output = root / WORKSPACE_DIR / DATA_DIR / "proposal_execution_approval_record.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(
            record.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def readiness_stage(
    *,
    stage_id: str,
    code: str,
    detail: str,
    ref: str | None = None,
) -> ProposalExecutionReadinessStage:
    return ProposalExecutionReadinessStage(
        stage_id=stage_id,
        status=ProposalExecutionReadinessPlanStatus.blocked,
        allowed=False,
        performed=False,
        ref=ref,
        issues=[
            proposal_adapter_issue(
                code=code,
                severity="error",
                detail=detail,
                ref=ref,
            )
        ],
    )


def build_proposal_execution_readiness_plan(
    *,
    project_id: str,
    approval_request: ProposalExecutionApprovalRequest,
    approval_request_ref: str,
    approval_record: ProposalExecutionApprovalRecord,
    approval_record_ref: str,
    readiness_fingerprint: str,
) -> ProposalExecutionReadinessPlan:
    stages = {
        "secret_source_selection": readiness_stage(
            stage_id="secret_source_selection",
            code="secret_source_selection_closed_current_gate",
            detail="secret-source selection is planned but not allowed in the current gate",
            ref=approval_record_ref,
        ),
        "credential_access": readiness_stage(
            stage_id="credential_access",
            code="credential_access_closed_current_gate",
            detail="credential access is planned but credential values must not be read in the current gate",
            ref=approval_record_ref,
        ),
        "execution_plan": readiness_stage(
            stage_id="execution_plan",
            code="execution_plan_closed_current_gate",
            detail="provider execution planning remains blocked until approval and credentials are valid",
            ref=approval_record_ref,
        ),
        "provider_call_preflight": readiness_stage(
            stage_id="provider_call_preflight",
            code="provider_call_preflight_closed_current_gate",
            detail="provider call preflight remains blocked before model/network execution opens",
            ref=approval_record_ref,
        ),
        "output_capture_plan": readiness_stage(
            stage_id="output_capture_plan",
            code="output_capture_closed_current_gate",
            detail="provider output capture remains blocked before provider execution opens",
            ref=approval_record_ref,
        ),
    }
    issues: list[ProposalAdapterCheckIssue] = [
        proposal_adapter_issue(
            code="execution_readiness_blocked_current_gate",
            severity="error",
            detail="execution readiness plan records five closed sub-stages without opening execution",
            ref=approval_record_ref,
        )
    ]
    if approval_record.status == ProposalExecutionApprovalRecordStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="execution_approval_record_blocked",
                severity="error",
                detail="execution readiness cannot proceed because approval record is blocked",
                ref=approval_record_ref,
            )
        )
    return ProposalExecutionReadinessPlan(
        readiness_plan_id=stable_execution_readiness_plan_id(
            project_id,
            readiness_fingerprint,
        ),
        project_id=project_id,
        status=ProposalExecutionReadinessPlanStatus.blocked,
        provider_id=approval_record.provider_id,
        approval_record_ref=approval_record_ref,
        approval_request_ref=approval_request_ref,
        request_ref=approval_record.request_ref,
        registry_ref=approval_record.registry_ref,
        handshake_ref=approval_record.handshake_ref,
        adapter_check_ref=approval_record.adapter_check_ref,
        readiness_fingerprint=readiness_fingerprint,
        secret_source_selection=stages["secret_source_selection"],
        credential_access=stages["credential_access"],
        execution_plan=stages["execution_plan"],
        provider_call_preflight=stages["provider_call_preflight"],
        output_capture_plan=stages["output_capture_plan"],
        selected_secret_source=None,
        credential_value_read=False,
        network_allowed=False,
        model_call_allowed=False,
        execution_allowed=False,
        execution_performed=False,
        model_call_performed=False,
        network_performed=False,
        raw_output_capture_allowed=False,
        raw_output_captured=False,
        proposal_content_generated=False,
        quarantine_required=True,
        issues=issues,
    )


def write_proposal_execution_readiness_plan_json(
    root: Path,
    plan: ProposalExecutionReadinessPlan,
) -> Path:
    output = root / WORKSPACE_DIR / DATA_DIR / "proposal_execution_readiness_plan.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(
            plan.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def input_bundle_item(
    *,
    item_id: str,
    code: str,
    detail: str,
    ref: str | None = None,
) -> ProposalExecutionInputBundleItem:
    return ProposalExecutionInputBundleItem(
        item_id=item_id,
        status=ProposalExecutionInputBundleStatus.blocked,
        allowed=False,
        materialized=False,
        ref=ref,
        issues=[
            proposal_adapter_issue(
                code=code,
                severity="error",
                detail=detail,
                ref=ref,
            )
        ],
    )


def build_proposal_execution_input_bundle(
    *,
    project_id: str,
    request_ref: str,
    adapter_check_ref: str,
    registry: ProposalProviderRegistry,
    registry_ref: str,
    handshake_ref: str,
    approval_request_ref: str,
    approval_record_ref: str,
    readiness_plan: ProposalExecutionReadinessPlan,
    readiness_plan_ref: str,
    input_fingerprint: str,
) -> ProposalExecutionInputBundle:
    items = {
        "provider_identity": input_bundle_item(
            item_id="provider_identity",
            code="provider_identity_closed_current_gate",
            detail="provider identity is referenced but not executable in the current gate",
            ref=registry_ref,
        ),
        "request_packet": input_bundle_item(
            item_id="request_packet",
            code="request_packet_closed_current_gate",
            detail="proposal request packet is referenced but not submitted to a provider",
            ref=request_ref,
        ),
        "prompt_contract": input_bundle_item(
            item_id="prompt_contract",
            code="prompt_contract_closed_current_gate",
            detail="prompt contract is referenced only; no execution prompt is embedded",
            ref=request_ref,
        ),
        "schema_contract": input_bundle_item(
            item_id="schema_contract",
            code="schema_contract_closed_current_gate",
            detail="target schema is referenced only; no provider output validation is run",
            ref=request_ref,
        ),
        "approval_chain": input_bundle_item(
            item_id="approval_chain",
            code="approval_chain_closed_current_gate",
            detail="approval chain is referenced but no approval grant opens execution",
            ref=approval_record_ref,
        ),
        "secret_reference": input_bundle_item(
            item_id="secret_reference",
            code="secret_reference_closed_current_gate",
            detail="secret references are not selected or resolved in the current gate",
            ref=approval_record_ref,
        ),
        "credential_access_policy": input_bundle_item(
            item_id="credential_access_policy",
            code="credential_access_policy_closed_current_gate",
            detail="credential access policy is recorded without reading credential values",
            ref=readiness_plan_ref,
        ),
        "network_policy": input_bundle_item(
            item_id="network_policy",
            code="network_policy_closed_current_gate",
            detail="network policy remains closed; provider calls are not allowed",
            ref=readiness_plan_ref,
        ),
        "quarantine_target": input_bundle_item(
            item_id="quarantine_target",
            code="quarantine_target_closed_current_gate",
            detail="quarantine target is required but no raw provider output is captured",
            ref=readiness_plan_ref,
        ),
        "output_routing": input_bundle_item(
            item_id="output_routing",
            code="output_routing_closed_current_gate",
            detail="output routing remains blocked before provider execution opens",
            ref=readiness_plan_ref,
        ),
    }
    issues: list[ProposalAdapterCheckIssue] = [
        proposal_adapter_issue(
            code="execution_input_bundle_blocked_current_gate",
            severity="error",
            detail="execution input bundle records ten closed input sub-items without opening execution",
            ref=readiness_plan_ref,
        )
    ]
    if readiness_plan.status == ProposalExecutionReadinessPlanStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="execution_readiness_plan_blocked",
                severity="error",
                detail="execution input bundle cannot proceed because readiness plan is blocked",
                ref=readiness_plan_ref,
            )
        )
    return ProposalExecutionInputBundle(
        bundle_id=stable_execution_input_bundle_id(
            project_id,
            input_fingerprint,
        ),
        project_id=project_id,
        status=ProposalExecutionInputBundleStatus.blocked,
        provider_id=registry.selected_provider_id,
        request_ref=request_ref,
        registry_ref=registry_ref,
        handshake_ref=handshake_ref,
        adapter_check_ref=adapter_check_ref,
        approval_request_ref=approval_request_ref,
        approval_record_ref=approval_record_ref,
        readiness_plan_ref=readiness_plan_ref,
        input_fingerprint=input_fingerprint,
        provider_identity=items["provider_identity"],
        request_packet=items["request_packet"],
        prompt_contract=items["prompt_contract"],
        schema_contract=items["schema_contract"],
        approval_chain=items["approval_chain"],
        secret_reference=items["secret_reference"],
        credential_access_policy=items["credential_access_policy"],
        network_policy=items["network_policy"],
        quarantine_target=items["quarantine_target"],
        output_routing=items["output_routing"],
        selected_secret_source=None,
        credential_value_read=False,
        network_allowed=False,
        model_call_allowed=False,
        execution_allowed=False,
        execution_performed=False,
        model_call_performed=False,
        network_performed=False,
        raw_output_capture_allowed=False,
        raw_output_captured=False,
        proposal_content_generated=False,
        prompt_embedded=False,
        quarantine_required=True,
        issues=issues,
    )


def write_proposal_execution_input_bundle_json(
    root: Path,
    bundle: ProposalExecutionInputBundle,
) -> Path:
    output = root / WORKSPACE_DIR / DATA_DIR / "proposal_execution_input_bundle.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(
            bundle.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def provider_call_dry_run_item(
    *,
    item_id: str,
    code: str,
    detail: str,
    ref: str | None = None,
) -> ProposalProviderCallDryRunItem:
    return ProposalProviderCallDryRunItem(
        item_id=item_id,
        status=ProposalProviderCallDryRunStatus.blocked,
        allowed=False,
        materialized=False,
        ref=ref,
        issues=[
            proposal_adapter_issue(
                code=code,
                severity="error",
                detail=detail,
                ref=ref,
            )
        ],
    )


def build_proposal_provider_call_dry_run(
    *,
    project_id: str,
    request_ref: str,
    adapter_check_ref: str,
    registry: ProposalProviderRegistry,
    registry_ref: str,
    handshake_ref: str,
    approval_request_ref: str,
    approval_record_ref: str,
    readiness_plan_ref: str,
    input_bundle: ProposalExecutionInputBundle,
    input_bundle_ref: str,
    dry_run_fingerprint: str,
) -> ProposalProviderCallDryRun:
    items = {
        "endpoint_reference": provider_call_dry_run_item(
            item_id="endpoint_reference",
            code="endpoint_reference_closed_current_gate",
            detail="provider endpoint reference is not resolved in the current gate",
            ref=registry_ref,
        ),
        "auth_header_policy": provider_call_dry_run_item(
            item_id="auth_header_policy",
            code="auth_header_policy_closed_current_gate",
            detail="authorization headers are not materialized in the current gate",
            ref=input_bundle_ref,
        ),
        "request_body_reference": provider_call_dry_run_item(
            item_id="request_body_reference",
            code="request_body_reference_closed_current_gate",
            detail="request body is referenced but not materialized or sent",
            ref=request_ref,
        ),
        "timeout_policy": provider_call_dry_run_item(
            item_id="timeout_policy",
            code="timeout_policy_closed_current_gate",
            detail="timeout policy is recorded but no provider call is attempted",
            ref=input_bundle_ref,
        ),
        "retry_policy": provider_call_dry_run_item(
            item_id="retry_policy",
            code="retry_policy_closed_current_gate",
            detail="retry policy is recorded with zero retries because execution is closed",
            ref=input_bundle_ref,
        ),
        "rate_limit_policy": provider_call_dry_run_item(
            item_id="rate_limit_policy",
            code="rate_limit_policy_closed_current_gate",
            detail="rate-limit policy is recorded without network execution",
            ref=input_bundle_ref,
        ),
        "idempotency_policy": provider_call_dry_run_item(
            item_id="idempotency_policy",
            code="idempotency_policy_closed_current_gate",
            detail="idempotency policy is recorded without materializing a key",
            ref=input_bundle_ref,
        ),
        "network_egress_policy": provider_call_dry_run_item(
            item_id="network_egress_policy",
            code="network_egress_policy_closed_current_gate",
            detail="network egress remains blocked in the current gate",
            ref=input_bundle_ref,
        ),
        "response_capture_policy": provider_call_dry_run_item(
            item_id="response_capture_policy",
            code="response_capture_policy_closed_current_gate",
            detail="response capture remains blocked until provider execution opens",
            ref=input_bundle_ref,
        ),
        "failure_handling_policy": provider_call_dry_run_item(
            item_id="failure_handling_policy",
            code="failure_handling_policy_closed_current_gate",
            detail="failure handling is recorded without attempting provider execution",
            ref=input_bundle_ref,
        ),
    }
    issues: list[ProposalAdapterCheckIssue] = [
        proposal_adapter_issue(
            code="provider_call_dry_run_blocked_current_gate",
            severity="error",
            detail="provider call dry-run manifest records ten closed call sub-items without opening execution",
            ref=input_bundle_ref,
        )
    ]
    if input_bundle.status == ProposalExecutionInputBundleStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="execution_input_bundle_blocked",
                severity="error",
                detail="provider call dry run cannot proceed because execution input bundle is blocked",
                ref=input_bundle_ref,
            )
        )
    return ProposalProviderCallDryRun(
        dry_run_id=stable_provider_call_dry_run_id(
            project_id,
            dry_run_fingerprint,
        ),
        project_id=project_id,
        status=ProposalProviderCallDryRunStatus.blocked,
        provider_id=registry.selected_provider_id,
        request_ref=request_ref,
        registry_ref=registry_ref,
        handshake_ref=handshake_ref,
        adapter_check_ref=adapter_check_ref,
        approval_request_ref=approval_request_ref,
        approval_record_ref=approval_record_ref,
        readiness_plan_ref=readiness_plan_ref,
        input_bundle_ref=input_bundle_ref,
        dry_run_fingerprint=dry_run_fingerprint,
        endpoint_reference=items["endpoint_reference"],
        auth_header_policy=items["auth_header_policy"],
        request_body_reference=items["request_body_reference"],
        timeout_policy=items["timeout_policy"],
        retry_policy=items["retry_policy"],
        rate_limit_policy=items["rate_limit_policy"],
        idempotency_policy=items["idempotency_policy"],
        network_egress_policy=items["network_egress_policy"],
        response_capture_policy=items["response_capture_policy"],
        failure_handling_policy=items["failure_handling_policy"],
        endpoint_resolved=False,
        auth_header_materialized=False,
        request_body_materialized=False,
        timeout_seconds=None,
        retry_count=0,
        idempotency_key_materialized=False,
        selected_secret_source=None,
        credential_value_read=False,
        network_allowed=False,
        model_call_allowed=False,
        execution_allowed=False,
        execution_performed=False,
        model_call_performed=False,
        network_performed=False,
        raw_output_capture_allowed=False,
        raw_output_captured=False,
        request_payload_sent=False,
        proposal_content_generated=False,
        quarantine_required=True,
        issues=issues,
    )


def write_proposal_provider_call_dry_run_json(
    root: Path,
    dry_run: ProposalProviderCallDryRun,
) -> Path:
    output = root / WORKSPACE_DIR / DATA_DIR / "proposal_provider_call_dry_run.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(
            dry_run.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def build_proposal_execution_authorization(
    *,
    project_id: str,
    request: ProposalRequestPacket,
    request_ref: str,
    adapter_check: ProposalAdapterCheck,
    adapter_check_ref: str,
    registry: ProposalProviderRegistry,
    registry_ref: str,
    handshake: ProposalMockAdapterHandshake,
    handshake_ref: str,
    approval_request: ProposalExecutionApprovalRequest,
    approval_request_ref: str,
    approval_record: ProposalExecutionApprovalRecord,
    approval_record_ref: str,
    readiness_plan: ProposalExecutionReadinessPlan,
    readiness_plan_ref: str,
    input_bundle: ProposalExecutionInputBundle,
    input_bundle_ref: str,
    call_dry_run: ProposalProviderCallDryRun,
    call_dry_run_ref: str,
    authorization_fingerprint: str,
) -> ProposalExecutionAuthorization:
    issues: list[ProposalAdapterCheckIssue] = [
        proposal_adapter_issue(
            code="execution_gate_closed_current_gate",
            severity="error",
            detail="provider execution is not open in the current gate",
        ),
        proposal_adapter_issue(
            code="user_execution_approval_missing",
            severity="error",
            detail="explicit user approval is required before any provider execution",
        ),
    ]
    if request.status == ProposalRequestStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="proposal_request_blocked",
                severity="error",
                detail="provider execution cannot be authorized because proposal request is blocked",
                ref=request_ref,
            )
        )
    if adapter_check.status == ProposalAdapterCheckStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="adapter_preflight_blocked",
                severity="error",
                detail="provider execution cannot be authorized because adapter preflight is blocked",
                ref=adapter_check_ref,
            )
        )
    if handshake.status == ProposalMockAdapterHandshakeStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="mock_adapter_handshake_blocked",
                severity="error",
                detail="provider execution cannot be authorized because mock adapter handshake is blocked",
                ref=handshake_ref,
            )
        )
    if approval_request.status == ProposalExecutionApprovalRequestStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="execution_approval_request_blocked",
                severity="error",
                detail="provider execution cannot be authorized because approval request is blocked",
                ref=approval_request_ref,
            )
        )
    if approval_record.status == ProposalExecutionApprovalRecordStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="execution_approval_record_blocked",
                severity="error",
                detail="provider execution cannot be authorized because approval record is blocked",
                ref=approval_record_ref,
            )
        )
    if readiness_plan.status == ProposalExecutionReadinessPlanStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="execution_readiness_plan_blocked",
                severity="error",
                detail="provider execution cannot be authorized because execution readiness plan is blocked",
                ref=readiness_plan_ref,
            )
        )
    if input_bundle.status == ProposalExecutionInputBundleStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="execution_input_bundle_blocked",
                severity="error",
                detail="provider execution cannot be authorized because execution input bundle is blocked",
                ref=input_bundle_ref,
            )
        )
    if call_dry_run.status == ProposalProviderCallDryRunStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="provider_call_dry_run_blocked",
                severity="error",
                detail="provider execution cannot be authorized because provider call dry run is blocked",
                ref=call_dry_run_ref,
            )
        )
    if registry.generation_open:
        issues.append(
            proposal_adapter_issue(
                code="generation_unexpectedly_open",
                severity="error",
                detail="provider execution authorization requires generation_open to remain false",
                ref=registry_ref,
            )
        )
    status = (
        ProposalExecutionAuthorizationStatus.ready_for_future_execution
        if not any(issue.severity == "error" for issue in issues)
        else ProposalExecutionAuthorizationStatus.blocked
    )
    return ProposalExecutionAuthorization(
        authorization_id=stable_execution_authorization_id(
            project_id,
            authorization_fingerprint,
        ),
        project_id=project_id,
        status=status,
        provider_id=registry.selected_provider_id,
        request_ref=request_ref,
        registry_ref=registry_ref,
        handshake_ref=handshake_ref,
        approval_request_ref=approval_request_ref,
        approval_record_ref=approval_record_ref,
        execution_readiness_ref=readiness_plan_ref,
        execution_input_bundle_ref=input_bundle_ref,
        provider_call_dry_run_ref=call_dry_run_ref,
        adapter_check_ref=adapter_check_ref,
        authorization_fingerprint=authorization_fingerprint,
        approved_execution_gate=False,
        user_approval_required=True,
        user_approval_present=False,
        credential_policy="no_credentials_allowed_current_gate",
        allowed_secret_sources=[],
        selected_secret_source=None,
        network_required=False,
        network_allowed=False,
        model_call_allowed=False,
        execution_performed=False,
        model_call_performed=False,
        network_performed=False,
        proposal_content_generated=False,
        quarantine_required=True,
        issues=issues,
    )


def write_proposal_execution_authorization_json(
    root: Path,
    authorization: ProposalExecutionAuthorization,
) -> Path:
    output = root / WORKSPACE_DIR / DATA_DIR / "proposal_execution_authorization.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(
            authorization.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def response_intake_item(
    *,
    item_id: str,
    code: str,
    detail: str,
    ref: str | None = None,
) -> ProposalProviderResponseIntakeItem:
    return ProposalProviderResponseIntakeItem(
        item_id=item_id,
        status=ProposalProviderResponseIntakeStatus.blocked,
        allowed=False,
        materialized=False,
        ref=ref,
        issues=[
            proposal_adapter_issue(
                code=code,
                severity="error",
                detail=detail,
                ref=ref,
            )
        ],
    )


def build_proposal_provider_response_intake_plan(
    *,
    project_id: str,
    request_ref: str,
    adapter_check_ref: str,
    registry: ProposalProviderRegistry,
    registry_ref: str,
    handshake_ref: str,
    authorization: ProposalExecutionAuthorization,
    authorization_ref: str,
    call_dry_run_ref: str,
    intake_fingerprint: str,
) -> ProposalProviderResponseIntakePlan:
    items = {
        "response_channel": response_intake_item(
            item_id="response_channel",
            code="response_channel_closed_current_gate",
            detail="response channel remains closed because provider execution is not open",
            ref=authorization_ref,
        ),
        "raw_output_location": response_intake_item(
            item_id="raw_output_location",
            code="raw_output_location_closed_current_gate",
            detail="raw output location is not materialized in the current gate",
            ref=authorization_ref,
        ),
        "content_type_policy": response_intake_item(
            item_id="content_type_policy",
            code="content_type_policy_closed_current_gate",
            detail="content type policy is recorded without validating provider output",
            ref=authorization_ref,
        ),
        "size_limit_policy": response_intake_item(
            item_id="size_limit_policy",
            code="size_limit_policy_closed_current_gate",
            detail="size limit policy is recorded without capturing provider output",
            ref=authorization_ref,
        ),
        "checksum_policy": response_intake_item(
            item_id="checksum_policy",
            code="checksum_policy_closed_current_gate",
            detail="checksum policy is recorded without computing a raw output checksum",
            ref=authorization_ref,
        ),
        "redaction_policy": response_intake_item(
            item_id="redaction_policy",
            code="redaction_policy_closed_current_gate",
            detail="redaction policy is recorded without processing provider output",
            ref=authorization_ref,
        ),
        "parser_selection": response_intake_item(
            item_id="parser_selection",
            code="parser_selection_closed_current_gate",
            detail="parser selection remains blocked before raw output exists",
            ref=authorization_ref,
        ),
        "validation_queue": response_intake_item(
            item_id="validation_queue",
            code="validation_queue_closed_current_gate",
            detail="validation queue remains blocked before parsed payload exists",
            ref=authorization_ref,
        ),
        "promotion_gate": response_intake_item(
            item_id="promotion_gate",
            code="promotion_gate_closed_current_gate",
            detail="promotion to proposals remains blocked before validation passes",
            ref=authorization_ref,
        ),
        "audit_trail": response_intake_item(
            item_id="audit_trail",
            code="audit_trail_closed_current_gate",
            detail="audit event is not written because no provider response is received",
            ref=authorization_ref,
        ),
    }
    issues: list[ProposalAdapterCheckIssue] = [
        proposal_adapter_issue(
            code="provider_response_intake_blocked_current_gate",
            severity="error",
            detail="provider response intake plan records ten closed intake sub-items without opening response capture",
            ref=authorization_ref,
        )
    ]
    if authorization.status == ProposalExecutionAuthorizationStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="execution_authorization_blocked",
                severity="error",
                detail="provider response intake cannot proceed because execution authorization is blocked",
                ref=authorization_ref,
            )
        )
    return ProposalProviderResponseIntakePlan(
        intake_id=stable_provider_response_intake_id(
            project_id,
            intake_fingerprint,
        ),
        project_id=project_id,
        status=ProposalProviderResponseIntakeStatus.blocked,
        provider_id=registry.selected_provider_id,
        request_ref=request_ref,
        registry_ref=registry_ref,
        handshake_ref=handshake_ref,
        adapter_check_ref=adapter_check_ref,
        execution_authorization_ref=authorization_ref,
        provider_call_dry_run_ref=call_dry_run_ref,
        intake_fingerprint=intake_fingerprint,
        response_channel=items["response_channel"],
        raw_output_location=items["raw_output_location"],
        content_type_policy=items["content_type_policy"],
        size_limit_policy=items["size_limit_policy"],
        checksum_policy=items["checksum_policy"],
        redaction_policy=items["redaction_policy"],
        parser_selection=items["parser_selection"],
        validation_queue=items["validation_queue"],
        promotion_gate=items["promotion_gate"],
        audit_trail=items["audit_trail"],
        response_channel_open=False,
        raw_output_location_materialized=False,
        content_type_validated=False,
        size_limit_bytes=0,
        checksum_computed=False,
        redaction_performed=False,
        parser_selected=False,
        validation_enqueued=False,
        promotion_allowed=False,
        audit_event_written=False,
        raw_output_captured=False,
        parsed_payload_generated=False,
        validation_performed=False,
        promoted_to_proposals=False,
        model_call_performed=False,
        network_performed=False,
        proposal_content_generated=False,
        quarantine_required=True,
        issues=issues,
    )


def write_proposal_provider_response_intake_plan_json(
    root: Path,
    intake: ProposalProviderResponseIntakePlan,
) -> Path:
    output = root / WORKSPACE_DIR / DATA_DIR / "proposal_provider_response_intake_plan.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(
            intake.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def build_proposal_provider_output_quarantine(
    *,
    project_id: str,
    request_ref: str,
    adapter_check_ref: str,
    registry: ProposalProviderRegistry,
    registry_ref: str,
    handshake_ref: str,
    authorization: ProposalExecutionAuthorization,
    authorization_ref: str,
    response_intake: ProposalProviderResponseIntakePlan,
    response_intake_ref: str,
    quarantine_fingerprint: str,
) -> ProposalProviderOutputQuarantine:
    issues: list[ProposalAdapterCheckIssue] = [
        proposal_adapter_issue(
            code="provider_output_not_captured_current_gate",
            severity="warning",
            detail="provider output quarantine is declared, but no provider output is captured in the current gate",
        )
    ]
    if authorization.status == ProposalExecutionAuthorizationStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="execution_authorization_blocked",
                severity="error",
                detail="provider output cannot be captured because execution authorization is blocked",
                ref=authorization_ref,
            )
        )
    if not authorization.quarantine_required:
        issues.append(
            proposal_adapter_issue(
                code="quarantine_required_missing",
                severity="error",
                detail="provider output quarantine requires quarantine_required to remain true",
                ref=authorization_ref,
            )
        )
    if response_intake.status == ProposalProviderResponseIntakeStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="provider_response_intake_blocked",
                severity="error",
                detail="provider output cannot be quarantined because response intake plan is blocked",
                ref=response_intake_ref,
            )
        )
    status = (
        ProposalProviderOutputQuarantineStatus.ready_for_future_ingest
        if not any(issue.severity == "error" for issue in issues)
        else ProposalProviderOutputQuarantineStatus.blocked
    )
    return ProposalProviderOutputQuarantine(
        quarantine_id=stable_provider_output_quarantine_id(
            project_id,
            quarantine_fingerprint,
        ),
        project_id=project_id,
        status=status,
        provider_id=registry.selected_provider_id,
        request_ref=request_ref,
        registry_ref=registry_ref,
        handshake_ref=handshake_ref,
        execution_authorization_ref=authorization_ref,
        response_intake_ref=response_intake_ref,
        adapter_check_ref=adapter_check_ref,
        quarantine_fingerprint=quarantine_fingerprint,
        raw_output_captured=False,
        raw_output_ref=None,
        raw_output_sha256=None,
        raw_output_bytes=0,
        parsed_payload_generated=False,
        parsed_payload_ref=None,
        promoted_to_proposals=False,
        validation_performed=False,
        model_call_performed=False,
        network_performed=False,
        proposal_content_generated=False,
        quarantine_required=True,
        issues=issues,
    )


def write_proposal_provider_output_quarantine_json(
    root: Path,
    quarantine: ProposalProviderOutputQuarantine,
) -> Path:
    output = root / WORKSPACE_DIR / DATA_DIR / "proposal_provider_output_quarantine.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(
            quarantine.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def response_validation_item(
    *,
    item_id: str,
    code: str,
    detail: str,
    ref: str | None = None,
) -> ProposalProviderResponseValidationItem:
    return ProposalProviderResponseValidationItem(
        item_id=item_id,
        status=ProposalProviderResponseValidationStatus.blocked,
        allowed=False,
        materialized=False,
        ref=ref,
        issues=[
            proposal_adapter_issue(
                code=code,
                severity="error",
                detail=detail,
                ref=ref,
            )
        ],
    )


def build_proposal_provider_response_validation_plan(
    *,
    project_id: str,
    request: ProposalRequestPacket,
    request_ref: str,
    adapter_check_ref: str,
    registry: ProposalProviderRegistry,
    registry_ref: str,
    handshake_ref: str,
    response_intake: ProposalProviderResponseIntakePlan,
    response_intake_ref: str,
    output_quarantine: ProposalProviderOutputQuarantine,
    output_quarantine_ref: str,
    validation_fingerprint: str,
) -> ProposalProviderResponseValidationPlan:
    item_details = {
        "quarantine_input_binding": (
            "quarantine input binding remains blocked because no raw provider output exists"
        ),
        "content_type_check": (
            "content type checking remains blocked before quarantined output exists"
        ),
        "size_limit_check": (
            "size limit checking remains blocked before quarantined output exists"
        ),
        "checksum_verification": (
            "checksum verification remains blocked because no raw output checksum exists"
        ),
        "redaction_verification": (
            "redaction verification remains blocked because no provider output was processed"
        ),
        "parser_contract": (
            "parser contract selection remains blocked before validated quarantine input exists"
        ),
        "json_syntax_validation": (
            "JSON syntax validation remains blocked before a parsed payload exists"
        ),
        "schema_validation": (
            "ProposalSet schema validation remains blocked before a parsed payload exists"
        ),
        "semantic_validation": (
            "semantic and evidence validation remains blocked before schema validation passes"
        ),
        "promotion_decision": (
            "promotion decision remains blocked before every validation stage passes"
        ),
    }
    items = {
        item_id: response_validation_item(
            item_id=item_id,
            code=f"{item_id}_blocked_current_gate",
            detail=detail,
            ref=output_quarantine_ref,
        )
        for item_id, detail in item_details.items()
    }
    issues = [
        proposal_adapter_issue(
            code="provider_response_validation_blocked_current_gate",
            severity="error",
            detail=(
                "provider response validation plan records ten closed validation "
                "sub-items without reading or parsing provider output"
            ),
            ref=output_quarantine_ref,
        )
    ]
    if response_intake.status == ProposalProviderResponseIntakeStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="provider_response_intake_blocked",
                severity="error",
                detail="response validation cannot proceed because response intake is blocked",
                ref=response_intake_ref,
            )
        )
    if output_quarantine.status == ProposalProviderOutputQuarantineStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="provider_output_quarantine_blocked",
                severity="error",
                detail="response validation cannot proceed because provider output quarantine is blocked",
                ref=output_quarantine_ref,
            )
        )
    return ProposalProviderResponseValidationPlan(
        validation_plan_id=stable_provider_response_validation_id(
            project_id,
            validation_fingerprint,
        ),
        project_id=project_id,
        status=ProposalProviderResponseValidationStatus.blocked,
        provider_id=registry.selected_provider_id,
        request_ref=request_ref,
        registry_ref=registry_ref,
        handshake_ref=handshake_ref,
        adapter_check_ref=adapter_check_ref,
        response_intake_ref=response_intake_ref,
        output_quarantine_ref=output_quarantine_ref,
        target_schema_ref=request.target_schema_ref,
        validation_fingerprint=validation_fingerprint,
        quarantine_input_binding=items["quarantine_input_binding"],
        content_type_check=items["content_type_check"],
        size_limit_check=items["size_limit_check"],
        checksum_verification=items["checksum_verification"],
        redaction_verification=items["redaction_verification"],
        parser_contract=items["parser_contract"],
        json_syntax_validation=items["json_syntax_validation"],
        schema_validation=items["schema_validation"],
        semantic_validation=items["semantic_validation"],
        promotion_decision=items["promotion_decision"],
        quarantine_input_bound=False,
        content_type_checked=False,
        size_limit_checked=False,
        checksum_verified=False,
        redaction_verified=False,
        parser_contract_selected=False,
        json_syntax_validated=False,
        schema_validated=False,
        semantic_validation_performed=False,
        promotion_decided=False,
        raw_output_read=False,
        parsed_payload_generated=False,
        validation_performed=False,
        promoted_to_proposals=False,
        audit_event_written=False,
        model_call_performed=False,
        network_performed=False,
        proposal_content_generated=False,
        quarantine_required=True,
        issues=issues,
    )


def write_proposal_provider_response_validation_plan_json(
    root: Path,
    plan: ProposalProviderResponseValidationPlan,
) -> Path:
    output = (
        root
        / WORKSPACE_DIR
        / DATA_DIR
        / "proposal_provider_response_validation_plan.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(
            plan.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def promotion_authorization_item(
    *,
    item_id: str,
    detail: str,
    ref: str,
) -> ProposalPromotionAuthorizationItem:
    return ProposalPromotionAuthorizationItem(
        item_id=item_id,
        status=ProposalPromotionAuthorizationStatus.blocked,
        allowed=False,
        materialized=False,
        ref=ref,
        issues=[
            proposal_adapter_issue(
                code=f"{item_id}_blocked_current_gate",
                severity="error",
                detail=detail,
                ref=ref,
            )
        ],
    )


def build_proposal_promotion_authorization_plan(
    *,
    project_id: str,
    request: ProposalRequestPacket,
    request_ref: str,
    adapter_check_ref: str,
    registry: ProposalProviderRegistry,
    registry_ref: str,
    response_validation: ProposalProviderResponseValidationPlan,
    response_validation_ref: str,
    output_quarantine_ref: str,
    promotion_fingerprint: str,
) -> ProposalPromotionAuthorizationPlan:
    item_details = {
        "validation_report_binding": (
            "validation report binding remains blocked because validation has not run"
        ),
        "schema_validation_requirement": (
            "schema validation must pass before promotion can be authorized"
        ),
        "semantic_validation_requirement": (
            "semantic validation must pass before promotion can be authorized"
        ),
        "evidence_validation_requirement": (
            "evidence traceability validation must pass before promotion can be authorized"
        ),
        "risk_acceptance_requirement": (
            "risk acceptance must be explicitly recorded before promotion"
        ),
        "proposal_identity_requirement": (
            "proposal identifiers must be validated as unique before promotion"
        ),
        "overwrite_policy": (
            "overwriting an existing canonical proposal set remains forbidden"
        ),
        "atomic_write_policy": (
            "atomic canonical write preparation remains blocked before authorization"
        ),
        "provenance_binding": (
            "provider, request, quarantine, and validation provenance must be bound"
        ),
        "final_promotion_authorization": (
            "final promotion authorization remains blocked in the current gate"
        ),
    }
    items = {
        item_id: promotion_authorization_item(
            item_id=item_id,
            detail=detail,
            ref=response_validation_ref,
        )
        for item_id, detail in item_details.items()
    }
    issues = [
        proposal_adapter_issue(
            code="proposal_promotion_authorization_blocked_current_gate",
            severity="error",
            detail=(
                "promotion authorization records ten closed conditions without "
                "writing or replacing canonical proposals"
            ),
            ref=response_validation_ref,
        )
    ]
    if response_validation.status == ProposalProviderResponseValidationStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="provider_response_validation_blocked",
                severity="error",
                detail="promotion cannot be authorized because response validation is blocked",
                ref=response_validation_ref,
            )
        )
    return ProposalPromotionAuthorizationPlan(
        promotion_plan_id=stable_promotion_authorization_id(
            project_id,
            promotion_fingerprint,
        ),
        project_id=project_id,
        status=ProposalPromotionAuthorizationStatus.blocked,
        provider_id=registry.selected_provider_id,
        request_ref=request_ref,
        registry_ref=registry_ref,
        adapter_check_ref=adapter_check_ref,
        response_validation_ref=response_validation_ref,
        output_quarantine_ref=output_quarantine_ref,
        target_schema_ref=request.target_schema_ref,
        promotion_target_ref=".artist-portrait/data/proposals.json",
        promotion_fingerprint=promotion_fingerprint,
        validation_report_binding=items["validation_report_binding"],
        schema_validation_requirement=items["schema_validation_requirement"],
        semantic_validation_requirement=items["semantic_validation_requirement"],
        evidence_validation_requirement=items["evidence_validation_requirement"],
        risk_acceptance_requirement=items["risk_acceptance_requirement"],
        proposal_identity_requirement=items["proposal_identity_requirement"],
        overwrite_policy=items["overwrite_policy"],
        atomic_write_policy=items["atomic_write_policy"],
        provenance_binding=items["provenance_binding"],
        final_promotion_authorization=items["final_promotion_authorization"],
        validation_report_bound=False,
        schema_validation_passed=False,
        semantic_validation_passed=False,
        evidence_validation_passed=False,
        risk_acceptance_recorded=False,
        proposal_ids_unique=False,
        overwrite_allowed=False,
        atomic_write_ready=False,
        provenance_bound=False,
        promotion_authorized=False,
        promotion_performed=False,
        proposals_file_written=False,
        audit_event_written=False,
        model_call_performed=False,
        network_performed=False,
        proposal_content_generated=False,
        quarantine_required=True,
        issues=issues,
    )


def write_proposal_promotion_authorization_plan_json(
    root: Path,
    plan: ProposalPromotionAuthorizationPlan,
) -> Path:
    output = (
        root / WORKSPACE_DIR / DATA_DIR / "proposal_promotion_authorization_plan.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(
            plan.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def promotion_validation_check(
    *,
    check_id: str,
    detail: str,
    ref: str,
) -> ProposalPromotionValidationCheck:
    return ProposalPromotionValidationCheck(
        check_id=check_id,
        status=ProposalPromotionValidationReportStatus.blocked,
        performed=False,
        passed=False,
        issue_count=1,
        ref=ref,
        issues=[
            proposal_adapter_issue(
                code=f"{check_id}_not_performed_current_gate",
                severity="error",
                detail=detail,
                ref=ref,
            )
        ],
    )


def build_proposal_promotion_validation_report(
    *,
    project_id: str,
    request: ProposalRequestPacket,
    request_ref: str,
    registry: ProposalProviderRegistry,
    response_validation_ref: str,
    promotion_authorization: ProposalPromotionAuthorizationPlan,
    promotion_authorization_ref: str,
    output_quarantine_ref: str,
    report_fingerprint: str,
) -> ProposalPromotionValidationReport:
    check_details = {
        "input_binding_check": (
            "promotion validation input binding was not performed"
        ),
        "schema_result_check": (
            "ProposalSet schema validation result does not exist"
        ),
        "semantic_result_check": (
            "semantic validation result does not exist"
        ),
        "evidence_traceability_check": (
            "evidence traceability validation result does not exist"
        ),
        "risk_result_check": (
            "risk validation and acceptance result does not exist"
        ),
        "proposal_identity_check": (
            "proposal identifier uniqueness was not validated"
        ),
        "overwrite_conflict_check": (
            "canonical proposal overwrite conflicts were not evaluated"
        ),
        "atomic_write_readiness_check": (
            "atomic canonical write readiness was not evaluated"
        ),
        "provenance_integrity_check": (
            "provider and validation provenance integrity was not validated"
        ),
        "final_authorization_check": (
            "final promotion authorization was not granted"
        ),
    }
    checks = {
        check_id: promotion_validation_check(
            check_id=check_id,
            detail=detail,
            ref=promotion_authorization_ref,
        )
        for check_id, detail in check_details.items()
    }
    issues = [
        proposal_adapter_issue(
            code="promotion_validation_not_performed_current_gate",
            severity="error",
            detail=(
                "promotion validation report is a blocked contract only; "
                "no validation result is fabricated"
            ),
            ref=promotion_authorization_ref,
        )
    ]
    if promotion_authorization.status == ProposalPromotionAuthorizationStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="promotion_authorization_blocked",
                severity="error",
                detail="promotion validation cannot pass while authorization is blocked",
                ref=promotion_authorization_ref,
            )
        )
    return ProposalPromotionValidationReport(
        report_id=stable_promotion_validation_report_id(
            project_id,
            report_fingerprint,
        ),
        project_id=project_id,
        status=ProposalPromotionValidationReportStatus.blocked,
        provider_id=registry.selected_provider_id,
        request_ref=request_ref,
        response_validation_ref=response_validation_ref,
        promotion_authorization_ref=promotion_authorization_ref,
        output_quarantine_ref=output_quarantine_ref,
        target_schema_ref=request.target_schema_ref,
        promotion_target_ref=promotion_authorization.promotion_target_ref,
        report_fingerprint=report_fingerprint,
        input_binding_check=checks["input_binding_check"],
        schema_result_check=checks["schema_result_check"],
        semantic_result_check=checks["semantic_result_check"],
        evidence_traceability_check=checks["evidence_traceability_check"],
        risk_result_check=checks["risk_result_check"],
        proposal_identity_check=checks["proposal_identity_check"],
        overwrite_conflict_check=checks["overwrite_conflict_check"],
        atomic_write_readiness_check=checks["atomic_write_readiness_check"],
        provenance_integrity_check=checks["provenance_integrity_check"],
        final_authorization_check=checks["final_authorization_check"],
        checks_performed=0,
        checks_passed=0,
        error_count=0,
        warning_count=0,
        overall_passed=False,
        promotion_recommended=False,
        promotion_authorized=False,
        promotion_performed=False,
        proposals_file_written=False,
        model_call_performed=False,
        network_performed=False,
        proposal_content_generated=False,
        quarantine_required=True,
        issues=issues,
    )


def write_proposal_promotion_validation_report_json(
    root: Path,
    report: ProposalPromotionValidationReport,
) -> Path:
    output = (
        root / WORKSPACE_DIR / DATA_DIR / "proposal_promotion_validation_report.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(
            report.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def canonical_write_transaction_item(
    *,
    item_id: str,
    detail: str,
    ref: str,
) -> ProposalCanonicalWriteTransactionItem:
    return ProposalCanonicalWriteTransactionItem(
        item_id=item_id,
        status=ProposalCanonicalWriteTransactionStatus.blocked,
        allowed=False,
        materialized=False,
        ref=ref,
        issues=[
            proposal_adapter_issue(
                code=f"{item_id}_blocked_current_gate",
                severity="error",
                detail=detail,
                ref=ref,
            )
        ],
    )


def build_proposal_canonical_write_transaction_plan(
    *,
    project_id: str,
    request_ref: str,
    promotion_authorization_ref: str,
    promotion_validation_report: ProposalPromotionValidationReport,
    promotion_validation_report_ref: str,
    transaction_fingerprint: str,
) -> ProposalCanonicalWriteTransactionPlan:
    details = {
        "target_lock": "canonical proposal target lock is not acquired",
        "prewrite_snapshot": "prewrite canonical snapshot is not created",
        "temporary_file": "temporary proposal file is not created",
        "schema_prewrite_check": "schema prewrite validation is not performed",
        "durability_policy": "fsync and durability policy is not executed",
        "atomic_replace": "atomic canonical replacement is not performed",
        "conflict_detection": "concurrent write conflict detection is not performed",
        "rollback_plan": "rollback plan is not prepared or executed",
        "audit_commit": "transaction audit commit is not written",
        "postcommit_verification": "postcommit canonical verification is not performed",
    }
    items = {
        item_id: canonical_write_transaction_item(
            item_id=item_id,
            detail=detail,
            ref=promotion_validation_report_ref,
        )
        for item_id, detail in details.items()
    }
    issues = [
        proposal_adapter_issue(
            code="canonical_write_transaction_blocked_current_gate",
            severity="error",
            detail=(
                "canonical proposal write transaction remains a plan only; "
                "no lock, temporary file, replacement, or rollback is materialized"
            ),
            ref=promotion_validation_report_ref,
        )
    ]
    if not promotion_validation_report.overall_passed:
        issues.append(
            proposal_adapter_issue(
                code="promotion_validation_not_passed",
                severity="error",
                detail="canonical write cannot start because promotion validation did not pass",
                ref=promotion_validation_report_ref,
            )
        )
    return ProposalCanonicalWriteTransactionPlan(
        transaction_plan_id=stable_canonical_write_transaction_id(
            project_id,
            transaction_fingerprint,
        ),
        project_id=project_id,
        status=ProposalCanonicalWriteTransactionStatus.blocked,
        request_ref=request_ref,
        promotion_authorization_ref=promotion_authorization_ref,
        promotion_validation_report_ref=promotion_validation_report_ref,
        canonical_target_ref=".artist-portrait/data/proposals.json",
        transaction_fingerprint=transaction_fingerprint,
        target_lock=items["target_lock"],
        prewrite_snapshot=items["prewrite_snapshot"],
        temporary_file=items["temporary_file"],
        schema_prewrite_check=items["schema_prewrite_check"],
        durability_policy=items["durability_policy"],
        atomic_replace=items["atomic_replace"],
        conflict_detection=items["conflict_detection"],
        rollback_plan=items["rollback_plan"],
        audit_commit=items["audit_commit"],
        postcommit_verification=items["postcommit_verification"],
        lock_acquired=False,
        snapshot_created=False,
        temporary_file_created=False,
        schema_prewrite_passed=False,
        fsync_performed=False,
        atomic_replace_performed=False,
        conflict_check_performed=False,
        rollback_prepared=False,
        rollback_performed=False,
        audit_commit_written=False,
        postcommit_verified=False,
        transaction_started=False,
        transaction_committed=False,
        proposals_file_written=False,
        model_call_performed=False,
        network_performed=False,
        proposal_content_generated=False,
        issues=issues,
    )


def write_proposal_canonical_write_transaction_plan_json(
    root: Path,
    plan: ProposalCanonicalWriteTransactionPlan,
) -> Path:
    output = (
        root
        / WORKSPACE_DIR
        / DATA_DIR
        / "proposal_canonical_write_transaction_plan.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(
            plan.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def build_proposal_provider_result_envelope(
    *,
    project_id: str,
    request: ProposalRequestPacket,
    request_ref: str,
    adapter_check_ref: str,
    registry: ProposalProviderRegistry,
    registry_ref: str,
    handshake: ProposalMockAdapterHandshake,
    handshake_ref: str,
    authorization: ProposalExecutionAuthorization,
    authorization_ref: str,
    output_quarantine: ProposalProviderOutputQuarantine,
    output_quarantine_ref: str,
    response_validation: ProposalProviderResponseValidationPlan,
    response_validation_ref: str,
    promotion_authorization: ProposalPromotionAuthorizationPlan,
    promotion_authorization_ref: str,
    promotion_validation_report: ProposalPromotionValidationReport,
    promotion_validation_report_ref: str,
    canonical_write_transaction: ProposalCanonicalWriteTransactionPlan,
    canonical_write_transaction_ref: str,
    result_fingerprint: str,
) -> ProposalProviderResultEnvelope:
    issues: list[ProposalAdapterCheckIssue] = [
        proposal_adapter_issue(
            code="proposal_generation_closed_current_gate",
            severity="warning",
            detail="provider result envelope is dry-run only; no proposal payload is generated",
        )
    ]
    if handshake.status == ProposalMockAdapterHandshakeStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="mock_adapter_handshake_blocked",
                severity="error",
                detail="provider result envelope cannot proceed because mock adapter handshake is blocked",
                ref=handshake_ref,
            )
        )
    if authorization.status == ProposalExecutionAuthorizationStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="execution_authorization_blocked",
                severity="error",
                detail="provider result envelope cannot proceed because execution authorization is blocked",
                ref=authorization_ref,
            )
        )
    if output_quarantine.status == ProposalProviderOutputQuarantineStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="provider_output_quarantine_blocked",
                severity="error",
                detail="provider result envelope cannot proceed because provider output quarantine is blocked",
                ref=output_quarantine_ref,
            )
        )
    if response_validation.status == ProposalProviderResponseValidationStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="provider_response_validation_blocked",
                severity="error",
                detail=(
                    "provider result envelope cannot proceed because provider "
                    "response validation is blocked"
                ),
                ref=response_validation_ref,
            )
        )
    if promotion_authorization.status == ProposalPromotionAuthorizationStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="proposal_promotion_authorization_blocked",
                severity="error",
                detail=(
                    "provider result envelope cannot proceed because proposal "
                    "promotion authorization is blocked"
                ),
                ref=promotion_authorization_ref,
            )
        )
    if (
        promotion_validation_report.status
        == ProposalPromotionValidationReportStatus.blocked
    ):
        issues.append(
            proposal_adapter_issue(
                code="proposal_promotion_validation_blocked",
                severity="error",
                detail=(
                    "provider result envelope cannot proceed because promotion "
                    "validation is blocked"
                ),
                ref=promotion_validation_report_ref,
            )
        )
    if canonical_write_transaction.status == ProposalCanonicalWriteTransactionStatus.blocked:
        issues.append(
            proposal_adapter_issue(
                code="canonical_write_transaction_blocked",
                severity="error",
                detail=(
                    "provider result envelope cannot proceed because canonical "
                    "write transaction is blocked"
                ),
                ref=canonical_write_transaction_ref,
            )
        )
    if registry.generation_open:
        issues.append(
            proposal_adapter_issue(
                code="generation_unexpectedly_open",
                severity="error",
                detail="provider result envelope requires generation_open to remain false",
                ref=registry_ref,
            )
        )
    status = (
        ProposalProviderResultStatus.ready_for_future_result_validation
        if not any(issue.severity == "error" for issue in issues)
        else ProposalProviderResultStatus.blocked
    )
    return ProposalProviderResultEnvelope(
        result_id=stable_provider_result_id(project_id, result_fingerprint),
        project_id=project_id,
        status=status,
        provider_id=registry.selected_provider_id,
        request_ref=request_ref,
        registry_ref=registry_ref,
        handshake_ref=handshake_ref,
        execution_authorization_ref=authorization_ref,
        output_quarantine_ref=output_quarantine_ref,
        response_validation_ref=response_validation_ref,
        promotion_authorization_ref=promotion_authorization_ref,
        promotion_validation_report_ref=promotion_validation_report_ref,
        canonical_write_transaction_ref=canonical_write_transaction_ref,
        adapter_check_ref=adapter_check_ref,
        result_fingerprint=result_fingerprint,
        expected_output_kind="ProposalSet",
        target_schema_ref=request.target_schema_ref,
        payload_generated=False,
        payload_json_ref=None,
        validation_performed=False,
        model_call_performed=False,
        network_performed=False,
        proposal_content_generated=False,
        issues=issues,
    )


def write_proposal_provider_result_json(
    root: Path,
    result: ProposalProviderResultEnvelope,
) -> Path:
    output = root / WORKSPACE_DIR / DATA_DIR / "proposal_provider_result.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def write_proposal_validation_json(root: Path, report: ProposalValidationReport) -> Path:
    output = root / WORKSPACE_DIR / DATA_DIR / "proposal_validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def build_proposal_validation_report(
    *,
    proposal_set: ProposalSet,
    context: ProposalContext,
    proposal_context_ref: str,
    proposals_ref: str,
    input_fingerprint: str,
) -> ProposalValidationReport:
    issues = validate_proposal_set_against_context(
        proposal_set=proposal_set,
        context=context,
    )
    error_count = sum(1 for issue in issues if issue.severity == "error")
    warning_count = sum(1 for issue in issues if issue.severity == "warning")
    return ProposalValidationReport(
        report_id=stable_proposal_validation_report_id(
            context.project_id,
            input_fingerprint,
        ),
        project_id=context.project_id,
        proposal_set_id=proposal_set.proposal_set_id,
        proposal_context_ref=proposal_context_ref,
        proposals_ref=proposals_ref,
        input_fingerprint=input_fingerprint,
        proposal_count=len(proposal_set.proposals),
        issue_count=len(issues),
        error_count=error_count,
        warning_count=warning_count,
        issues=issues,
    )


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
    for step_name in (
        "keyframes",
        "analyze",
        "map",
        "propose",
        "timeline",
        "review_timeline",
        "preview",
        "review_preview",
        "final_export",
        "review_final_export",
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
    for step_name in (
        "analyze",
        "map",
        "propose",
        "timeline",
        "review_timeline",
        "preview",
        "review_preview",
        "final_export",
        "review_final_export",
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
    for step_name in (
        "map",
        "propose",
        "timeline",
        "review_timeline",
        "preview",
        "review_preview",
        "final_export",
        "review_final_export",
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
    for step_name in (
        "propose",
        "timeline",
        "review_timeline",
        "preview",
        "review_preview",
        "final_export",
        "review_final_export",
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
    request_fingerprint = fingerprint_inputs(
        [
            ("proposal_context", context_path),
            ("text_model_gate", gate_path),
            ("proposal_set_schema", root / "schemas" / "proposal_set.schema.json"),
        ]
    )
    proposal_request = build_proposal_request_packet(
        context=proposal_context,
        text_model_gate=text_model_gate,
        proposal_context_ref=context_ref,
        text_model_gate_ref=gate_ref,
        proposal_context_fingerprint=fingerprint_file(context_path),
        request_fingerprint=request_fingerprint,
    )
    request_path = write_proposal_request_json(root, proposal_request)
    request_ref = request_path.relative_to(root).as_posix()
    handoff_path = write_agent_handoff_bundle(
        root=root,
        output_dir=config.paths.output_dir,
        context=proposal_context,
        request=proposal_request,
    )
    handoff_ref = handoff_path.relative_to(root).as_posix()
    adapter_check = build_proposal_adapter_check(
        project_id=config.project.id,
        request=proposal_request,
        request_ref=request_ref,
        request_path=request_path,
        checked_paths=[
            ("project_config", project_path),
            (context_ref, context_path),
            (gate_ref, gate_path),
            (request_ref, request_path),
        ],
    )
    adapter_check_path = write_proposal_adapter_check_json(root, adapter_check)
    adapter_check_ref = adapter_check_path.relative_to(root).as_posix()
    registry_fingerprint = fingerprint_inputs(
        [
            ("proposal_request", request_path),
            ("proposal_adapter_check", adapter_check_path),
        ]
    )
    provider_registry = build_proposal_provider_registry(
        project_id=config.project.id,
        request_ref=request_ref,
        adapter_check_ref=adapter_check_ref,
        request=proposal_request,
        registry_fingerprint=registry_fingerprint,
    )
    registry_path = write_proposal_provider_registry_json(root, provider_registry)
    registry_ref = registry_path.relative_to(root).as_posix()
    handshake_fingerprint = fingerprint_inputs(
        [
            ("proposal_request", request_path),
            ("proposal_adapter_check", adapter_check_path),
            ("proposal_provider_registry", registry_path),
        ]
    )
    mock_handshake = build_proposal_mock_adapter_handshake(
        project_id=config.project.id,
        request=proposal_request,
        request_ref=request_ref,
        adapter_check=adapter_check,
        adapter_check_ref=adapter_check_ref,
        registry=provider_registry,
        registry_ref=registry_ref,
        handshake_fingerprint=handshake_fingerprint,
    )
    handshake_path = write_proposal_mock_adapter_handshake_json(root, mock_handshake)
    handshake_ref = handshake_path.relative_to(root).as_posix()
    approval_fingerprint = fingerprint_inputs(
        [
            ("proposal_request", request_path),
            ("proposal_adapter_check", adapter_check_path),
            ("proposal_provider_registry", registry_path),
            ("proposal_mock_adapter_handshake", handshake_path),
        ]
    )
    approval_request = build_proposal_execution_approval_request(
        project_id=config.project.id,
        request=proposal_request,
        request_ref=request_ref,
        adapter_check=adapter_check,
        adapter_check_ref=adapter_check_ref,
        registry=provider_registry,
        registry_ref=registry_ref,
        handshake=mock_handshake,
        handshake_ref=handshake_ref,
        approval_fingerprint=approval_fingerprint,
    )
    approval_path = write_proposal_execution_approval_request_json(
        root,
        approval_request,
    )
    approval_ref = approval_path.relative_to(root).as_posix()
    approval_record_fingerprint = fingerprint_inputs(
        [
            ("proposal_execution_approval_request", approval_path),
            ("proposal_adapter_check", adapter_check_path),
            ("proposal_provider_registry", registry_path),
            ("proposal_mock_adapter_handshake", handshake_path),
        ]
    )
    approval_record = build_proposal_execution_approval_record(
        project_id=config.project.id,
        approval_request=approval_request,
        approval_request_ref=approval_ref,
        approval_record_fingerprint=approval_record_fingerprint,
    )
    approval_record_path = write_proposal_execution_approval_record_json(
        root,
        approval_record,
    )
    approval_record_ref = approval_record_path.relative_to(root).as_posix()
    readiness_fingerprint = fingerprint_inputs(
        [
            ("proposal_execution_approval_request", approval_path),
            ("proposal_execution_approval_record", approval_record_path),
            ("proposal_adapter_check", adapter_check_path),
            ("proposal_provider_registry", registry_path),
            ("proposal_mock_adapter_handshake", handshake_path),
        ]
    )
    readiness_plan = build_proposal_execution_readiness_plan(
        project_id=config.project.id,
        approval_request=approval_request,
        approval_request_ref=approval_ref,
        approval_record=approval_record,
        approval_record_ref=approval_record_ref,
        readiness_fingerprint=readiness_fingerprint,
    )
    readiness_path = write_proposal_execution_readiness_plan_json(
        root,
        readiness_plan,
    )
    readiness_ref = readiness_path.relative_to(root).as_posix()
    input_bundle_fingerprint = fingerprint_inputs(
        [
            ("proposal_request", request_path),
            ("proposal_adapter_check", adapter_check_path),
            ("proposal_provider_registry", registry_path),
            ("proposal_mock_adapter_handshake", handshake_path),
            ("proposal_execution_approval_request", approval_path),
            ("proposal_execution_approval_record", approval_record_path),
            ("proposal_execution_readiness_plan", readiness_path),
        ]
    )
    input_bundle = build_proposal_execution_input_bundle(
        project_id=config.project.id,
        request_ref=request_ref,
        adapter_check_ref=adapter_check_ref,
        registry=provider_registry,
        registry_ref=registry_ref,
        handshake_ref=handshake_ref,
        approval_request_ref=approval_ref,
        approval_record_ref=approval_record_ref,
        readiness_plan=readiness_plan,
        readiness_plan_ref=readiness_ref,
        input_fingerprint=input_bundle_fingerprint,
    )
    input_bundle_path = write_proposal_execution_input_bundle_json(
        root,
        input_bundle,
    )
    input_bundle_ref = input_bundle_path.relative_to(root).as_posix()
    call_dry_run_fingerprint = fingerprint_inputs(
        [
            ("proposal_request", request_path),
            ("proposal_adapter_check", adapter_check_path),
            ("proposal_provider_registry", registry_path),
            ("proposal_mock_adapter_handshake", handshake_path),
            ("proposal_execution_approval_request", approval_path),
            ("proposal_execution_approval_record", approval_record_path),
            ("proposal_execution_readiness_plan", readiness_path),
            ("proposal_execution_input_bundle", input_bundle_path),
        ]
    )
    call_dry_run = build_proposal_provider_call_dry_run(
        project_id=config.project.id,
        request_ref=request_ref,
        adapter_check_ref=adapter_check_ref,
        registry=provider_registry,
        registry_ref=registry_ref,
        handshake_ref=handshake_ref,
        approval_request_ref=approval_ref,
        approval_record_ref=approval_record_ref,
        readiness_plan_ref=readiness_ref,
        input_bundle=input_bundle,
        input_bundle_ref=input_bundle_ref,
        dry_run_fingerprint=call_dry_run_fingerprint,
    )
    call_dry_run_path = write_proposal_provider_call_dry_run_json(
        root,
        call_dry_run,
    )
    call_dry_run_ref = call_dry_run_path.relative_to(root).as_posix()
    authorization_fingerprint = fingerprint_inputs(
        [
            ("proposal_request", request_path),
            ("proposal_adapter_check", adapter_check_path),
            ("proposal_provider_registry", registry_path),
            ("proposal_mock_adapter_handshake", handshake_path),
            ("proposal_execution_approval_request", approval_path),
            ("proposal_execution_approval_record", approval_record_path),
            ("proposal_execution_readiness_plan", readiness_path),
            ("proposal_execution_input_bundle", input_bundle_path),
            ("proposal_provider_call_dry_run", call_dry_run_path),
        ]
    )
    execution_authorization = build_proposal_execution_authorization(
        project_id=config.project.id,
        request=proposal_request,
        request_ref=request_ref,
        adapter_check=adapter_check,
        adapter_check_ref=adapter_check_ref,
        registry=provider_registry,
        registry_ref=registry_ref,
        handshake=mock_handshake,
        handshake_ref=handshake_ref,
        approval_request=approval_request,
        approval_request_ref=approval_ref,
        approval_record=approval_record,
        approval_record_ref=approval_record_ref,
        readiness_plan=readiness_plan,
        readiness_plan_ref=readiness_ref,
        input_bundle=input_bundle,
        input_bundle_ref=input_bundle_ref,
        call_dry_run=call_dry_run,
        call_dry_run_ref=call_dry_run_ref,
        authorization_fingerprint=authorization_fingerprint,
    )
    authorization_path = write_proposal_execution_authorization_json(
        root,
        execution_authorization,
    )
    authorization_ref = authorization_path.relative_to(root).as_posix()
    response_intake_fingerprint = fingerprint_inputs(
        [
            ("proposal_request", request_path),
            ("proposal_adapter_check", adapter_check_path),
            ("proposal_provider_registry", registry_path),
            ("proposal_mock_adapter_handshake", handshake_path),
            ("proposal_provider_call_dry_run", call_dry_run_path),
            ("proposal_execution_authorization", authorization_path),
        ]
    )
    response_intake = build_proposal_provider_response_intake_plan(
        project_id=config.project.id,
        request_ref=request_ref,
        adapter_check_ref=adapter_check_ref,
        registry=provider_registry,
        registry_ref=registry_ref,
        handshake_ref=handshake_ref,
        authorization=execution_authorization,
        authorization_ref=authorization_ref,
        call_dry_run_ref=call_dry_run_ref,
        intake_fingerprint=response_intake_fingerprint,
    )
    response_intake_path = write_proposal_provider_response_intake_plan_json(
        root,
        response_intake,
    )
    response_intake_ref = response_intake_path.relative_to(root).as_posix()
    quarantine_fingerprint = fingerprint_inputs(
        [
            ("proposal_request", request_path),
            ("proposal_adapter_check", adapter_check_path),
            ("proposal_provider_registry", registry_path),
            ("proposal_mock_adapter_handshake", handshake_path),
            ("proposal_execution_authorization", authorization_path),
            ("proposal_provider_response_intake_plan", response_intake_path),
        ]
    )
    output_quarantine = build_proposal_provider_output_quarantine(
        project_id=config.project.id,
        request_ref=request_ref,
        adapter_check_ref=adapter_check_ref,
        registry=provider_registry,
        registry_ref=registry_ref,
        handshake_ref=handshake_ref,
        authorization=execution_authorization,
        authorization_ref=authorization_ref,
        response_intake=response_intake,
        response_intake_ref=response_intake_ref,
        quarantine_fingerprint=quarantine_fingerprint,
    )
    quarantine_path = write_proposal_provider_output_quarantine_json(
        root,
        output_quarantine,
    )
    quarantine_ref = quarantine_path.relative_to(root).as_posix()
    response_validation_fingerprint = fingerprint_inputs(
        [
            ("proposal_request", request_path),
            ("proposal_adapter_check", adapter_check_path),
            ("proposal_provider_registry", registry_path),
            ("proposal_mock_adapter_handshake", handshake_path),
            ("proposal_provider_response_intake_plan", response_intake_path),
            ("proposal_provider_output_quarantine", quarantine_path),
        ]
    )
    response_validation = build_proposal_provider_response_validation_plan(
        project_id=config.project.id,
        request=proposal_request,
        request_ref=request_ref,
        adapter_check_ref=adapter_check_ref,
        registry=provider_registry,
        registry_ref=registry_ref,
        handshake_ref=handshake_ref,
        response_intake=response_intake,
        response_intake_ref=response_intake_ref,
        output_quarantine=output_quarantine,
        output_quarantine_ref=quarantine_ref,
        validation_fingerprint=response_validation_fingerprint,
    )
    response_validation_path = write_proposal_provider_response_validation_plan_json(
        root,
        response_validation,
    )
    response_validation_ref = response_validation_path.relative_to(root).as_posix()
    promotion_fingerprint = fingerprint_inputs(
        [
            ("proposal_request", request_path),
            ("proposal_adapter_check", adapter_check_path),
            ("proposal_provider_registry", registry_path),
            ("proposal_provider_output_quarantine", quarantine_path),
            ("proposal_provider_response_validation_plan", response_validation_path),
        ]
    )
    promotion_authorization = build_proposal_promotion_authorization_plan(
        project_id=config.project.id,
        request=proposal_request,
        request_ref=request_ref,
        adapter_check_ref=adapter_check_ref,
        registry=provider_registry,
        registry_ref=registry_ref,
        response_validation=response_validation,
        response_validation_ref=response_validation_ref,
        output_quarantine_ref=quarantine_ref,
        promotion_fingerprint=promotion_fingerprint,
    )
    promotion_path = write_proposal_promotion_authorization_plan_json(
        root,
        promotion_authorization,
    )
    promotion_ref = promotion_path.relative_to(root).as_posix()
    promotion_report_fingerprint = fingerprint_inputs(
        [
            ("proposal_request", request_path),
            ("proposal_provider_output_quarantine", quarantine_path),
            ("proposal_provider_response_validation_plan", response_validation_path),
            ("proposal_promotion_authorization_plan", promotion_path),
        ]
    )
    promotion_validation_report = build_proposal_promotion_validation_report(
        project_id=config.project.id,
        request=proposal_request,
        request_ref=request_ref,
        registry=provider_registry,
        response_validation_ref=response_validation_ref,
        promotion_authorization=promotion_authorization,
        promotion_authorization_ref=promotion_ref,
        output_quarantine_ref=quarantine_ref,
        report_fingerprint=promotion_report_fingerprint,
    )
    promotion_report_path = write_proposal_promotion_validation_report_json(
        root,
        promotion_validation_report,
    )
    promotion_report_ref = promotion_report_path.relative_to(root).as_posix()
    transaction_fingerprint = fingerprint_inputs(
        [
            ("proposal_request", request_path),
            ("proposal_promotion_authorization_plan", promotion_path),
            ("proposal_promotion_validation_report", promotion_report_path),
        ]
    )
    write_transaction = build_proposal_canonical_write_transaction_plan(
        project_id=config.project.id,
        request_ref=request_ref,
        promotion_authorization_ref=promotion_ref,
        promotion_validation_report=promotion_validation_report,
        promotion_validation_report_ref=promotion_report_ref,
        transaction_fingerprint=transaction_fingerprint,
    )
    transaction_path = write_proposal_canonical_write_transaction_plan_json(
        root,
        write_transaction,
    )
    transaction_ref = transaction_path.relative_to(root).as_posix()
    result_fingerprint = fingerprint_inputs(
        [
            ("proposal_request", request_path),
            ("proposal_adapter_check", adapter_check_path),
            ("proposal_provider_registry", registry_path),
            ("proposal_mock_adapter_handshake", handshake_path),
            ("proposal_execution_authorization", authorization_path),
            ("proposal_provider_output_quarantine", quarantine_path),
            ("proposal_provider_response_validation_plan", response_validation_path),
            ("proposal_promotion_authorization_plan", promotion_path),
            ("proposal_promotion_validation_report", promotion_report_path),
            ("proposal_canonical_write_transaction_plan", transaction_path),
        ]
    )
    provider_result = build_proposal_provider_result_envelope(
        project_id=config.project.id,
        request=proposal_request,
        request_ref=request_ref,
        adapter_check_ref=adapter_check_ref,
        registry=provider_registry,
        registry_ref=registry_ref,
        handshake=mock_handshake,
        handshake_ref=handshake_ref,
        authorization=execution_authorization,
        authorization_ref=authorization_ref,
        output_quarantine=output_quarantine,
        output_quarantine_ref=quarantine_ref,
        response_validation=response_validation,
        response_validation_ref=response_validation_ref,
        promotion_authorization=promotion_authorization,
        promotion_authorization_ref=promotion_ref,
        promotion_validation_report=promotion_validation_report,
        promotion_validation_report_ref=promotion_report_ref,
        canonical_write_transaction=write_transaction,
        canonical_write_transaction_ref=transaction_ref,
        result_fingerprint=result_fingerprint,
    )
    result_path = write_proposal_provider_result_json(root, provider_result)
    result_ref = result_path.relative_to(root).as_posix()
    output_refs = [
        context_ref,
        gate_ref,
        request_ref,
        handoff_ref,
        adapter_check_ref,
        registry_ref,
        handshake_ref,
        approval_ref,
        approval_record_ref,
        readiness_ref,
        input_bundle_ref,
        call_dry_run_ref,
        authorization_ref,
        response_intake_ref,
        quarantine_ref,
        response_validation_ref,
        promotion_ref,
        promotion_report_ref,
        transaction_ref,
        result_ref,
    ]
    run_id = new_run_id()
    warnings: list[str] = []
    output_dir = root / config.paths.output_dir
    if text_model_gate.status == TextModelGateStatus.blocked:
        warnings = [
            (
                "host_agent_candidate_required: proposal handoff is ready; "
                "generate a ProposalSet with the active Codex/ChatGPT Agent and "
                "import it with --agent-output; paid APIs were not used"
            )
        ]
        state.steps["propose"] = StepLedgerEntry(
            status=StepStatus.blocked,
            input_fingerprint=input_fingerprint,
            output_refs=output_refs,
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
                "output_refs": output_refs,
                "proposal_context": context_ref,
                "text_model_gate": gate_ref,
                "proposal_request": request_ref,
                "proposal_agent_handoff": handoff_ref,
                "proposal_adapter_check": adapter_check_ref,
                "proposal_provider_registry": registry_ref,
                "proposal_mock_adapter_handshake": handshake_ref,
                "proposal_execution_approval_request": approval_ref,
                "proposal_execution_approval_record": approval_record_ref,
                "proposal_execution_readiness_plan": readiness_ref,
                "proposal_execution_input_bundle": input_bundle_ref,
                "proposal_provider_call_dry_run": call_dry_run_ref,
                "proposal_execution_authorization": authorization_ref,
                "proposal_provider_response_intake_plan": response_intake_ref,
                "proposal_provider_output_quarantine": quarantine_ref,
                "proposal_provider_response_validation_plan": response_validation_ref,
                "proposal_promotion_authorization_plan": promotion_ref,
                "proposal_promotion_validation_report": promotion_report_ref,
                "proposal_canonical_write_transaction_plan": transaction_ref,
                "proposal_provider_result": result_ref,
                "reasons": text_model_gate.reasons,
                "reason": "host_agent_candidate_required",
            },
        )
        write_json(runs_dir / "warnings.json", warnings)
        write_json(runs_dir / "errors.json", [])
        (runs_dir / "log.txt").write_text(
            "host Agent proposal handoff prepared\n",
            encoding="utf-8",
        )
        save_state(root, state)
        write_run_report(output_dir, state, warnings)
        return state

    warnings = [
        "host_agent_candidate_required: proposal handoff is ready; import a "
        "Codex/ChatGPT-generated ProposalSet with --agent-output"
    ]
    state.steps["propose"] = StepLedgerEntry(
        status=StepStatus.blocked,
        input_fingerprint=input_fingerprint,
        output_refs=output_refs,
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
            "output_refs": output_refs,
            "proposal_context": context_ref,
            "text_model_gate": gate_ref,
            "proposal_request": request_ref,
            "proposal_agent_handoff": handoff_ref,
            "proposal_adapter_check": adapter_check_ref,
            "proposal_provider_registry": registry_ref,
            "proposal_mock_adapter_handshake": handshake_ref,
            "proposal_execution_approval_request": approval_ref,
            "proposal_execution_approval_record": approval_record_ref,
            "proposal_execution_readiness_plan": readiness_ref,
            "proposal_execution_input_bundle": input_bundle_ref,
            "proposal_provider_call_dry_run": call_dry_run_ref,
            "proposal_execution_authorization": authorization_ref,
            "proposal_provider_response_intake_plan": response_intake_ref,
            "proposal_provider_output_quarantine": quarantine_ref,
            "proposal_provider_response_validation_plan": response_validation_ref,
            "proposal_promotion_authorization_plan": promotion_ref,
            "proposal_promotion_validation_report": promotion_report_ref,
            "proposal_canonical_write_transaction_plan": transaction_ref,
            "proposal_provider_result": result_ref,
            "reason": "host_agent_candidate_required",
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text(
        "host Agent proposal handoff prepared\n",
        encoding="utf-8",
    )
    save_state(root, state)
    write_run_report(output_dir, state, warnings)
    return state


def import_agent_proposal_workspace(
    project_path: Path,
    candidate_path: Path,
) -> dict[str, object]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError(
            "agent proposal import requires init to complete first"
        )

    context_path = root / WORKSPACE_DIR / DATA_DIR / "proposal_context.json"
    request_path = root / WORKSPACE_DIR / DATA_DIR / "proposal_request.json"
    handoff_path = root / config.paths.output_dir / "proposal_agent_handoff.json"
    if not context_path.exists() or not request_path.exists() or not handoff_path.exists():
        raise WorkspacePrerequisiteError(
            "agent proposal import requires propose to prepare the Agent handoff first"
        )

    context = read_proposal_context_json(context_path)
    request = read_proposal_request_json(request_path)
    if request.project_id != context.project_id:
        raise WorkspacePrerequisiteError(
            "agent proposal handoff request and context project IDs disagree"
        )

    try:
        quarantined = quarantine_agent_candidate(
            root=root,
            candidate_path=candidate_path,
        )
        proposal_set = parse_quarantined_proposal_set(quarantined)
        require_host_agent_method(
            proposal_set=proposal_set,
            candidate=quarantined,
        )
    except AgentProposalCandidateError as exc:
        raise WorkspaceProposalCandidateError(
            str(exc),
            code=exc.code,
            quarantine_ref=exc.quarantine_ref,
        ) from exc

    quarantine_validation = build_proposal_validation_report(
        proposal_set=proposal_set,
        context=context,
        proposal_context_ref=context_path.relative_to(root).as_posix(),
        proposals_ref=quarantined.ref,
        input_fingerprint=fingerprint_inputs(
            [
                ("proposal_context", context_path),
                ("agent_candidate", quarantined.path),
            ]
        ),
    )
    if quarantine_validation.error_count:
        validation_path = quarantined.path.with_suffix(".validation.json")
        validation_path.write_text(
            json.dumps(
                quarantine_validation.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        codes = sorted(
            {
                issue.code
                for issue in quarantine_validation.issues
                if issue.severity == "error"
            }
        )
        raise WorkspaceProposalCandidateError(
            "agent proposal candidate failed semantic validation: "
            + ", ".join(codes),
            code="agent_candidate_semantic_invalid",
            quarantine_ref=quarantined.ref,
        )

    proposals_path = root / WORKSPACE_DIR / DATA_DIR / "proposals.json"
    atomic_write_text(
        proposals_path,
        json.dumps(
            proposal_set.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    validation = build_proposal_validation_report(
        proposal_set=proposal_set,
        context=context,
        proposal_context_ref=context_path.relative_to(root).as_posix(),
        proposals_ref=proposals_path.relative_to(root).as_posix(),
        input_fingerprint=fingerprint_inputs(
            [
                ("proposal_context", context_path),
                ("proposals", proposals_path),
            ]
        ),
    )
    validation_path = write_proposal_validation_json(root, validation)
    review_path = root / config.paths.output_dir / "proposal_review.md"
    atomic_write_text(review_path, render_proposal_review_report(validation))

    warnings = (
        [f"{validation.warning_count} proposal validation warning(s) found"]
        if validation.warning_count
        else []
    )
    run_id = new_run_id()
    output_refs = [
        handoff_path.relative_to(root).as_posix(),
        quarantined.ref,
        proposals_path.relative_to(root).as_posix(),
        validation_path.relative_to(root).as_posix(),
        review_path.relative_to(root).as_posix(),
    ]
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    state.steps["propose"] = StepLedgerEntry(
        status=status,
        input_fingerprint="sha256:" + quarantined.sha256,
        output_refs=output_refs,
        last_run_id=run_id,
        warnings=warnings,
    )
    state.steps["review_proposal"] = StepLedgerEntry(
        status=status,
        input_fingerprint=validation.input_fingerprint,
        output_refs=[
            validation_path.relative_to(root).as_posix(),
            review_path.relative_to(root).as_posix(),
        ],
        last_run_id=run_id,
        warnings=warnings,
    )
    for step_name in (
        "timeline",
        "review_timeline",
        "bgm_fit",
        "preview",
        "review_preview",
        "final_export",
        "review_final_export",
    ):
        existing = state.steps.get(step_name)
        if existing and existing.status in {
            StepStatus.completed,
            StepStatus.completed_with_warnings,
        }:
            state.steps[step_name] = StepLedgerEntry(
                status=StepStatus.invalidated,
                input_fingerprint=existing.input_fingerprint,
                output_refs=existing.output_refs,
                last_run_id=existing.last_run_id,
                warnings=[
                    *existing.warnings,
                    "canonical proposals changed; regenerate the selected-proposal timeline",
                ],
            )
    state.active_mode = ActiveMode.creative
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready

    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        runs_dir / "command.json",
        {
            "command": "propose",
            "mode": "host_agent_import",
            "project": str(project_path),
            "candidate": str(candidate_path),
        },
    )
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "propose",
            "status": status.value,
            "host_agent": True,
            "paid_api_call_performed": False,
            "network_performed": False,
            "candidate_sha256": quarantined.sha256,
            "candidate_bytes": quarantined.byte_count,
            "output_refs": output_refs,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text(
        "host Agent proposal imported, validated, and promoted\n",
        encoding="utf-8",
    )
    save_state(root, state)
    write_run_report(root / config.paths.output_dir, state, warnings)
    return {
        "status": status.value,
        "handoff_ref": handoff_path.relative_to(root).as_posix(),
        "quarantine_ref": quarantined.ref,
        "proposals_ref": proposals_path.relative_to(root).as_posix(),
        "validation_ref": validation_path.relative_to(root).as_posix(),
        "review_ref": review_path.relative_to(root).as_posix(),
        "warnings": warnings,
    }


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


def read_timeline_draft(path: Path) -> TimelineDraft:
    try:
        return TimelineDraft.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise WorkspaceTimelineError(f"invalid TimelineDraft JSON: {exc}") from exc


def timeline_workspace(
    project_path: Path,
    *,
    proposal_id: str,
) -> tuple[Path, Path, Path, ProjectState, list[str], list[dict]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("timeline requires init to complete first")
    if state.steps.get("propose", StepLedgerEntry()).status not in {
        StepStatus.completed,
        StepStatus.completed_with_warnings,
    }:
        raise WorkspacePrerequisiteError(
            "timeline requires a validated canonical proposal import first"
        )
    proposals_path = root / WORKSPACE_DIR / DATA_DIR / "proposals.json"
    clips_path = root / WORKSPACE_DIR / DATA_DIR / "clips.jsonl"
    sources_path = root / WORKSPACE_DIR / DATA_DIR / "sources.jsonl"
    if not proposals_path.exists():
        raise WorkspacePrerequisiteError("timeline requires canonical proposals.json first")
    if not clips_path.exists() or not sources_path.exists():
        raise WorkspacePrerequisiteError("timeline requires current sources and clips first")
    try:
        selected_id = ProposalId(proposal_id)
    except ValueError as exc:
        raise WorkspaceTimelineError(
            "timeline proposal must be proposal_safe, proposal_advanced, or proposal_risky"
        ) from exc

    proposal_set = read_proposals_json(proposals_path)
    clips = read_clips_jsonl(clips_path)
    sources = read_sources_jsonl(sources_path)
    input_fingerprint = fingerprint_inputs(
        [
            ("project", project_path),
            ("proposals", proposals_path),
            ("clips", clips_path),
            ("sources", sources_path),
        ]
    )
    try:
        timeline = build_timeline_draft(
            config=config,
            proposal_set=proposal_set,
            clips=clips,
            sources=sources,
            proposal_id=selected_id,
            input_fingerprint=input_fingerprint,
        )
    except TimelineBuildError as exc:
        raise WorkspaceTimelineError(str(exc)) from exc

    output_dir = root / config.paths.output_dir
    timeline_path = output_dir / "timeline_draft.json"
    timeline_ref = timeline_path.relative_to(root).as_posix()
    validation = validate_timeline_draft(
        timeline=timeline,
        proposal_set=proposal_set,
        clips=clips,
        sources=sources,
        timeline_ref=timeline_ref,
        input_fingerprint=input_fingerprint,
    )
    if validation.error_count:
        raise WorkspaceTimelineError(
            "generated timeline failed validation: "
            + ", ".join(
                sorted(
                    {
                        issue.code
                        for issue in validation.issues
                        if issue.severity == "error"
                    }
                )
            )
        )

    atomic_write_text(
        timeline_path,
        json.dumps(
            timeline.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    validation_path = root / WORKSPACE_DIR / DATA_DIR / "timeline_validation.json"
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
    review_path = output_dir / "timeline_review.md"
    atomic_write_text(review_path, render_timeline_review(validation))

    warnings = list(timeline.warnings)
    warnings.extend(
        issue.detail for issue in validation.issues if issue.severity == "warning"
    )
    warnings = list(dict.fromkeys(warnings))
    run_id = new_run_id()
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    output_refs = [
        timeline_ref,
        validation_path.relative_to(root).as_posix(),
        review_path.relative_to(root).as_posix(),
    ]
    state.steps["timeline"] = StepLedgerEntry(
        status=status,
        input_fingerprint=input_fingerprint,
        output_refs=output_refs,
        last_run_id=run_id,
        warnings=warnings,
    )
    state.steps["review_timeline"] = StepLedgerEntry(
        status=status,
        input_fingerprint=input_fingerprint,
        output_refs=[
            validation_path.relative_to(root).as_posix(),
            review_path.relative_to(root).as_posix(),
        ],
        last_run_id=run_id,
        warnings=warnings,
    )
    timeline_dependents = {
        "bgm_fit": "canonical timeline changed; rerun BGM fitting",
        "preview": "canonical timeline changed; rerun preview",
        "review_preview": "canonical timeline changed; rerun preview review",
        "final_export": "canonical timeline changed; rerun final export",
        "review_final_export": "canonical timeline changed; rerun final export review",
    }
    for step_name, reason in timeline_dependents.items():
        existing = state.steps.get(step_name)
        if existing and existing.status in {
            StepStatus.completed,
            StepStatus.completed_with_warnings,
        }:
            state.steps[step_name] = StepLedgerEntry(
                status=StepStatus.invalidated,
                input_fingerprint=existing.input_fingerprint,
                output_refs=existing.output_refs,
                last_run_id=existing.last_run_id,
                warnings=[*existing.warnings, reason],
            )
    state.active_mode = ActiveMode.creative
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready

    runs_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        runs_dir / "command.json",
        {
            "command": "timeline",
            "project": str(project_path),
            "proposal": selected_id.value,
        },
    )
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "timeline",
            "status": status.value,
            "proposal_id": selected_id.value,
            "segments": len(timeline.segments),
            "actual_duration": timeline.actual_duration,
            "music_status": timeline.music_plan.status.value,
            "bgm_selection_performed": False,
            "beat_analysis_performed": False,
            "render_performed": False,
            "network_performed": False,
            "output_refs": output_refs,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(runs_dir / "errors.json", [])
    (runs_dir / "log.txt").write_text("timeline completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(output_dir, state, warnings)
    return (
        timeline_path,
        validation_path,
        review_path,
        state,
        warnings,
        [issue.model_dump(mode="json") for issue in validation.issues],
    )


def review_timeline_workspace(
    project_path: Path,
) -> tuple[Path, Path, ProjectState, list[str], list[dict]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError(
            "review --scope timeline requires init to complete first"
        )
    timeline_path = root / config.paths.output_dir / "timeline_draft.json"
    proposals_path = root / WORKSPACE_DIR / DATA_DIR / "proposals.json"
    clips_path = root / WORKSPACE_DIR / DATA_DIR / "clips.jsonl"
    sources_path = root / WORKSPACE_DIR / DATA_DIR / "sources.jsonl"
    if not timeline_path.exists():
        raise WorkspacePrerequisiteError(
            "review --scope timeline requires timeline generation first"
        )
    if not proposals_path.exists() or not clips_path.exists() or not sources_path.exists():
        raise WorkspacePrerequisiteError(
            "review --scope timeline requires proposals, clips, and sources"
        )
    timeline = read_timeline_draft(timeline_path)
    proposal_set = read_proposals_json(proposals_path)
    clips = read_clips_jsonl(clips_path)
    sources = read_sources_jsonl(sources_path)
    input_fingerprint = fingerprint_inputs(
        [
            ("project", project_path),
            ("proposals", proposals_path),
            ("clips", clips_path),
            ("sources", sources_path),
        ]
    )
    validation = validate_timeline_draft(
        timeline=timeline,
        proposal_set=proposal_set,
        clips=clips,
        sources=sources,
        timeline_ref=timeline_path.relative_to(root).as_posix(),
        input_fingerprint=input_fingerprint,
    )
    validation_path = root / WORKSPACE_DIR / DATA_DIR / "timeline_validation.json"
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
    report_path = root / config.paths.output_dir / "timeline_review.md"
    atomic_write_text(report_path, render_timeline_review(validation))
    warnings = [f"{validation.issue_count} timeline issue(s) found"] if validation.issue_count else []
    run_id = new_run_id()
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    state.steps["review_timeline"] = StepLedgerEntry(
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
        {"command": "review", "scope": "timeline", "project": str(project_path)},
    )
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "review_timeline",
            "status": status.value,
            "issues": validation.issue_count,
            "errors": validation.error_count,
            "warnings": validation.warning_count,
            "output_refs": state.steps["review_timeline"].output_refs,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(
        runs_dir / "errors.json",
        [issue.code for issue in validation.issues if issue.severity == "error"],
    )
    (runs_dir / "log.txt").write_text("review timeline completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(root / config.paths.output_dir, state, warnings)
    return (
        validation_path,
        report_path,
        state,
        warnings,
        [issue.model_dump(mode="json") for issue in validation.issues],
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


def review_proposal_workspace(
    project_path: Path,
) -> tuple[Path, Path, ProjectState, list[str], list[dict[str, str]]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("review --scope proposal requires init to complete first")

    context_path = root / WORKSPACE_DIR / DATA_DIR / "proposal_context.json"
    proposals_path = root / WORKSPACE_DIR / DATA_DIR / "proposals.json"
    if not context_path.exists():
        raise WorkspacePrerequisiteError(
            "review --scope proposal requires propose to prepare proposal context first"
        )
    if not proposals_path.exists():
        raise WorkspacePrerequisiteError(
            "review --scope proposal requires proposals.json to exist first"
        )

    context = read_proposal_context_json(context_path)
    proposal_set = read_proposals_json(proposals_path)
    input_fingerprint = fingerprint_inputs(
        [
            ("proposal_context", context_path),
            ("proposals", proposals_path),
        ]
    )
    validation = build_proposal_validation_report(
        proposal_set=proposal_set,
        context=context,
        proposal_context_ref=context_path.relative_to(root).as_posix(),
        proposals_ref=proposals_path.relative_to(root).as_posix(),
        input_fingerprint=input_fingerprint,
    )
    validation_path = write_proposal_validation_json(root, validation)
    output_dir = root / config.paths.output_dir
    report_path = output_dir / "proposal_review.md"
    atomic_write_text(report_path, render_proposal_review_report(validation))

    warnings = (
        [f"{validation.issue_count} proposal validation issue(s) found"]
        if validation.issue_count
        else []
    )
    run_id = new_run_id()
    status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    state.steps["review_proposal"] = StepLedgerEntry(
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
        {"command": "review", "scope": "proposal", "project": str(project_path)},
    )
    write_json(runs_dir / "environment.json", environment_snapshot())
    write_json(
        runs_dir / "step_result.json",
        {
            "step": "review_proposal",
            "status": status.value,
            "proposal_count": validation.proposal_count,
            "issues": validation.issue_count,
            "errors": validation.error_count,
            "warnings": validation.warning_count,
            "output_refs": state.steps["review_proposal"].output_refs,
        },
    )
    write_json(runs_dir / "warnings.json", warnings)
    write_json(
        runs_dir / "errors.json",
        [issue.code for issue in validation.issues if issue.severity == "error"],
    )
    (runs_dir / "log.txt").write_text("review proposal completed\n", encoding="utf-8")
    save_state(root, state)
    write_run_report(output_dir, state, warnings)
    return (
        validation_path,
        report_path,
        state,
        warnings,
        [issue.model_dump(mode="json") for issue in validation.issues],
    )


def review_all_scope_issues() -> list[dict[str, str]]:
    return []


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


def render_proposal_review_report(report: ProposalValidationReport) -> str:
    severity_counts = count_by_value(issue.severity for issue in report.issues)
    code_counts = count_by_value(issue.code for issue in report.issues)
    return (
        "# Proposal Review\n\n"
        "This deterministic proposal review validates an existing proposals.json "
        "against the local proposal context. It does not generate proposals, call "
        "models, choose BGM, create timelines, or render previews.\n\n"
        "## Summary\n\n"
        f"- Proposal context: `{report.proposal_context_ref}`\n"
        f"- Proposals: `{report.proposals_ref}`\n"
        f"- Proposal count: `{report.proposal_count}`\n"
        f"- Issue count: `{report.issue_count}`\n"
        f"- Error count: `{report.error_count}`\n"
        f"- Warning count: `{report.warning_count}`\n\n"
        "## Severity Counts\n\n"
        f"{render_count_lines(severity_counts)}"
        "## Issue Counts\n\n"
        f"{render_count_lines(code_counts)}"
        "## Issues\n\n"
        f"{render_proposal_validation_issue_sections(report.issues)}"
    )


def render_proposal_validation_issue_sections(
    issues: list[ProposalValidationIssue],
) -> str:
    if not issues:
        return "No proposal validation issues were found.\n"
    sections = []
    for index, issue in enumerate(issues, start=1):
        optional_lines = ""
        if issue.proposal_id:
            optional_lines += f"- Proposal ID: `{issue.proposal_id}`\n"
        if issue.ref:
            optional_lines += f"- Ref: `{issue.ref}`\n"
        sections.append(
            f"### {index}. `{issue.code}`\n\n"
            f"- Severity: `{issue.severity}`\n"
            f"{optional_lines}"
            f"- Detail: {issue.detail}\n"
        )
    return "\n".join(sections)
