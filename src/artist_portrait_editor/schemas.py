from __future__ import annotations

import json
from pathlib import Path

from artist_portrait_editor.models.acceptance import ProjectAcceptanceReport
from artist_portrait_editor.models.analysis import AnalysisRecord
from artist_portrait_editor.models.bgm import (
    BgmAnalysisReport,
    BgmBeatGrid,
    BgmCandidateLedger,
    BgmFitPlan,
)
from artist_portrait_editor.models.bgm_recommendation import (
    BgmRecommendationContext,
    BgmRecommendationFitReview,
    BgmRecommendationRequest,
    BgmRecommendationSelection,
    BgmRecommendationSet,
    BgmRecommendationValidationReport,
)
from artist_portrait_editor.models.clip import ClipRecord
from artist_portrait_editor.models.config import ProjectConfig
from artist_portrait_editor.models.keyframe import KeyframeRecord
from artist_portrait_editor.models.final_export import (
    FinalExportManifest,
    FinalExportValidationReport,
)
from artist_portrait_editor.models.model_gate import TextModelGate
from artist_portrait_editor.models.proposal import ProposalSet
from artist_portrait_editor.models.proposal_adapter import (
    ProposalAdapterCheck,
    ProposalCanonicalWriteTransactionPlan,
    ProposalExecutionApprovalRecord,
    ProposalExecutionApprovalRequest,
    ProposalExecutionAuthorization,
    ProposalExecutionInputBundle,
    ProposalExecutionReadinessPlan,
    ProposalMockAdapterHandshake,
    ProposalPromotionAuthorizationPlan,
    ProposalPromotionValidationReport,
    ProposalProviderCallDryRun,
    ProposalProviderOutputQuarantine,
    ProposalProviderResponseIntakePlan,
    ProposalProviderResponseValidationPlan,
    ProposalProviderResultEnvelope,
    ProposalProviderRegistry,
)
from artist_portrait_editor.models.proposal_context import ProposalContext
from artist_portrait_editor.models.proposal_request import ProposalRequestPacket
from artist_portrait_editor.models.proposal_validation import ProposalValidationReport
from artist_portrait_editor.models.preview import PreviewRenderManifest, PreviewValidationReport
from artist_portrait_editor.models.source import SourceRecord
from artist_portrait_editor.models.state import ProjectState
from artist_portrait_editor.models.transcript import TranscriptRecord
from artist_portrait_editor.models.timeline import TimelineDraft, TimelineValidationReport


def write_schema_files(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    schemas = {
        "analysis_record.schema.json": AnalysisRecord.model_json_schema(),
        "project_acceptance_report.schema.json": ProjectAcceptanceReport.model_json_schema(),
        "bgm_analysis_report.schema.json": BgmAnalysisReport.model_json_schema(),
        "bgm_beat_grid.schema.json": BgmBeatGrid.model_json_schema(),
        "bgm_candidate_ledger.schema.json": BgmCandidateLedger.model_json_schema(),
        "bgm_fit_plan.schema.json": BgmFitPlan.model_json_schema(),
        "bgm_recommendation_context.schema.json": BgmRecommendationContext.model_json_schema(),
        "bgm_recommendation_fit_review.schema.json": BgmRecommendationFitReview.model_json_schema(),
        "bgm_recommendation_request.schema.json": BgmRecommendationRequest.model_json_schema(),
        "bgm_recommendation_selection.schema.json": BgmRecommendationSelection.model_json_schema(),
        "bgm_recommendation_set.schema.json": BgmRecommendationSet.model_json_schema(),
        "bgm_recommendation_validation_report.schema.json": (
            BgmRecommendationValidationReport.model_json_schema()
        ),
        "final_export_manifest.schema.json": FinalExportManifest.model_json_schema(),
        "final_export_validation_report.schema.json": (
            FinalExportValidationReport.model_json_schema()
        ),
        "project_config.schema.json": ProjectConfig.model_json_schema(),
        "project_state.schema.json": ProjectState.model_json_schema(),
        "preview_render_manifest.schema.json": PreviewRenderManifest.model_json_schema(),
        "preview_validation_report.schema.json": PreviewValidationReport.model_json_schema(),
        "proposal_adapter_check.schema.json": ProposalAdapterCheck.model_json_schema(),
        "proposal_canonical_write_transaction_plan.schema.json": (
            ProposalCanonicalWriteTransactionPlan.model_json_schema()
        ),
        "proposal_execution_approval_record.schema.json": (
            ProposalExecutionApprovalRecord.model_json_schema()
        ),
        "proposal_execution_approval_request.schema.json": (
            ProposalExecutionApprovalRequest.model_json_schema()
        ),
        "proposal_execution_authorization.schema.json": (
            ProposalExecutionAuthorization.model_json_schema()
        ),
        "proposal_execution_input_bundle.schema.json": (
            ProposalExecutionInputBundle.model_json_schema()
        ),
        "proposal_execution_readiness_plan.schema.json": (
            ProposalExecutionReadinessPlan.model_json_schema()
        ),
        "proposal_mock_adapter_handshake.schema.json": (
            ProposalMockAdapterHandshake.model_json_schema()
        ),
        "proposal_promotion_authorization_plan.schema.json": (
            ProposalPromotionAuthorizationPlan.model_json_schema()
        ),
        "proposal_promotion_validation_report.schema.json": (
            ProposalPromotionValidationReport.model_json_schema()
        ),
        "proposal_provider_call_dry_run.schema.json": (
            ProposalProviderCallDryRun.model_json_schema()
        ),
        "proposal_provider_registry.schema.json": ProposalProviderRegistry.model_json_schema(),
        "proposal_provider_output_quarantine.schema.json": (
            ProposalProviderOutputQuarantine.model_json_schema()
        ),
        "proposal_provider_response_intake_plan.schema.json": (
            ProposalProviderResponseIntakePlan.model_json_schema()
        ),
        "proposal_provider_response_validation_plan.schema.json": (
            ProposalProviderResponseValidationPlan.model_json_schema()
        ),
        "proposal_provider_result_envelope.schema.json": (
            ProposalProviderResultEnvelope.model_json_schema()
        ),
        "proposal_set.schema.json": ProposalSet.model_json_schema(),
        "proposal_context.schema.json": ProposalContext.model_json_schema(),
        "proposal_request_packet.schema.json": ProposalRequestPacket.model_json_schema(),
        "proposal_validation_report.schema.json": ProposalValidationReport.model_json_schema(),
        "source_record.schema.json": SourceRecord.model_json_schema(),
        "clip_record.schema.json": ClipRecord.model_json_schema(),
        "keyframe_record.schema.json": KeyframeRecord.model_json_schema(),
        "transcript_record.schema.json": TranscriptRecord.model_json_schema(),
        "text_model_gate.schema.json": TextModelGate.model_json_schema(),
        "timeline_draft.schema.json": TimelineDraft.model_json_schema(),
        "timeline_validation_report.schema.json": TimelineValidationReport.model_json_schema(),
    }
    for filename, schema in schemas.items():
        (output_dir / filename).write_text(
            json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
