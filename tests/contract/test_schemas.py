import json
from pathlib import Path

from artist_portrait_editor.models.analysis import AnalysisRecord
from artist_portrait_editor.models.bgm import BgmAnalysisReport, BgmCandidateLedger, BgmFitPlan
from artist_portrait_editor.models.bgm_recommendation import (
    BgmRecommendationContext,
    BgmRecommendationRequest,
    BgmRecommendationSet,
    BgmRecommendationValidationReport,
)
from artist_portrait_editor.models.clip import ClipRecord
from artist_portrait_editor.models.config import ProjectConfig
from artist_portrait_editor.models.keyframe import KeyframeRecord
from artist_portrait_editor.models.model_gate import TextModelGate
from artist_portrait_editor.models.proposal import ProposalSet
from artist_portrait_editor.models.proposal_adapter import ProposalAdapterCheck
from artist_portrait_editor.models.proposal_adapter import ProposalCanonicalWriteTransactionPlan
from artist_portrait_editor.models.proposal_adapter import ProposalExecutionApprovalRecord
from artist_portrait_editor.models.proposal_adapter import ProposalExecutionApprovalRequest
from artist_portrait_editor.models.proposal_adapter import ProposalExecutionAuthorization
from artist_portrait_editor.models.proposal_adapter import ProposalExecutionInputBundle
from artist_portrait_editor.models.proposal_adapter import ProposalExecutionReadinessPlan
from artist_portrait_editor.models.proposal_adapter import ProposalMockAdapterHandshake
from artist_portrait_editor.models.proposal_adapter import ProposalPromotionAuthorizationPlan
from artist_portrait_editor.models.proposal_adapter import ProposalPromotionValidationReport
from artist_portrait_editor.models.proposal_adapter import ProposalProviderCallDryRun
from artist_portrait_editor.models.proposal_adapter import ProposalProviderOutputQuarantine
from artist_portrait_editor.models.proposal_adapter import ProposalProviderResponseIntakePlan
from artist_portrait_editor.models.proposal_adapter import ProposalProviderResponseValidationPlan
from artist_portrait_editor.models.proposal_adapter import ProposalProviderResultEnvelope
from artist_portrait_editor.models.proposal_adapter import ProposalProviderRegistry
from artist_portrait_editor.models.proposal_context import ProposalContext
from artist_portrait_editor.models.proposal_request import ProposalRequestPacket
from artist_portrait_editor.models.proposal_validation import ProposalValidationReport
from artist_portrait_editor.models.source import SourceRecord
from artist_portrait_editor.models.state import ProjectState
from artist_portrait_editor.models.transcript import TranscriptRecord
from artist_portrait_editor.models.timeline import TimelineDraft, TimelineValidationReport


def test_schema_generation_from_pydantic_models():
    analysis_schema = AnalysisRecord.model_json_schema()
    bgm_analysis_schema = BgmAnalysisReport.model_json_schema()
    bgm_recommendation_context_schema = BgmRecommendationContext.model_json_schema()
    bgm_recommendation_request_schema = BgmRecommendationRequest.model_json_schema()
    bgm_recommendation_set_schema = BgmRecommendationSet.model_json_schema()
    bgm_recommendation_validation_schema = BgmRecommendationValidationReport.model_json_schema()
    bgm_ledger_schema = BgmCandidateLedger.model_json_schema()
    bgm_fit_schema = BgmFitPlan.model_json_schema()
    config_schema = ProjectConfig.model_json_schema()
    clip_schema = ClipRecord.model_json_schema()
    keyframe_schema = KeyframeRecord.model_json_schema()
    proposal_schema = ProposalSet.model_json_schema()
    proposal_context_schema = ProposalContext.model_json_schema()
    proposal_request_schema = ProposalRequestPacket.model_json_schema()
    proposal_validation_schema = ProposalValidationReport.model_json_schema()
    text_model_gate_schema = TextModelGate.model_json_schema()
    state_schema = ProjectState.model_json_schema()
    proposal_adapter_schema = ProposalAdapterCheck.model_json_schema()
    canonical_write_schema = ProposalCanonicalWriteTransactionPlan.model_json_schema()
    execution_approval_record_schema = ProposalExecutionApprovalRecord.model_json_schema()
    execution_approval_schema = ProposalExecutionApprovalRequest.model_json_schema()
    execution_authorization_schema = ProposalExecutionAuthorization.model_json_schema()
    execution_input_bundle_schema = ProposalExecutionInputBundle.model_json_schema()
    execution_readiness_schema = ProposalExecutionReadinessPlan.model_json_schema()
    provider_registry_schema = ProposalProviderRegistry.model_json_schema()
    promotion_authorization_schema = ProposalPromotionAuthorizationPlan.model_json_schema()
    promotion_validation_schema = ProposalPromotionValidationReport.model_json_schema()
    output_quarantine_schema = ProposalProviderOutputQuarantine.model_json_schema()
    response_intake_schema = ProposalProviderResponseIntakePlan.model_json_schema()
    response_validation_schema = ProposalProviderResponseValidationPlan.model_json_schema()
    mock_handshake_schema = ProposalMockAdapterHandshake.model_json_schema()
    provider_call_dry_run_schema = ProposalProviderCallDryRun.model_json_schema()
    provider_result_schema = ProposalProviderResultEnvelope.model_json_schema()
    source_schema = SourceRecord.model_json_schema()
    transcript_schema = TranscriptRecord.model_json_schema()
    timeline_schema = TimelineDraft.model_json_schema()
    timeline_validation_schema = TimelineValidationReport.model_json_schema()

    assert analysis_schema["title"] == "AnalysisRecord"
    assert bgm_analysis_schema["title"] == "BgmAnalysisReport"
    assert bgm_recommendation_context_schema["title"] == "BgmRecommendationContext"
    assert bgm_recommendation_request_schema["title"] == "BgmRecommendationRequest"
    assert bgm_recommendation_set_schema["title"] == "BgmRecommendationSet"
    assert bgm_recommendation_validation_schema["title"] == "BgmRecommendationValidationReport"
    assert bgm_ledger_schema["title"] == "BgmCandidateLedger"
    assert bgm_fit_schema["title"] == "BgmFitPlan"
    assert config_schema["title"] == "ProjectConfig"
    assert clip_schema["title"] == "ClipRecord"
    assert keyframe_schema["title"] == "KeyframeRecord"
    assert proposal_schema["title"] == "ProposalSet"
    assert proposal_context_schema["title"] == "ProposalContext"
    assert proposal_request_schema["title"] == "ProposalRequestPacket"
    assert proposal_validation_schema["title"] == "ProposalValidationReport"
    assert text_model_gate_schema["title"] == "TextModelGate"
    assert state_schema["title"] == "ProjectState"
    assert proposal_adapter_schema["title"] == "ProposalAdapterCheck"
    assert canonical_write_schema["title"] == "ProposalCanonicalWriteTransactionPlan"
    assert execution_approval_record_schema["title"] == "ProposalExecutionApprovalRecord"
    assert execution_approval_schema["title"] == "ProposalExecutionApprovalRequest"
    assert execution_authorization_schema["title"] == "ProposalExecutionAuthorization"
    assert execution_input_bundle_schema["title"] == "ProposalExecutionInputBundle"
    assert execution_readiness_schema["title"] == "ProposalExecutionReadinessPlan"
    assert provider_registry_schema["title"] == "ProposalProviderRegistry"
    assert promotion_authorization_schema["title"] == "ProposalPromotionAuthorizationPlan"
    assert promotion_validation_schema["title"] == "ProposalPromotionValidationReport"
    assert output_quarantine_schema["title"] == "ProposalProviderOutputQuarantine"
    assert response_intake_schema["title"] == "ProposalProviderResponseIntakePlan"
    assert response_validation_schema["title"] == "ProposalProviderResponseValidationPlan"
    assert mock_handshake_schema["title"] == "ProposalMockAdapterHandshake"
    assert provider_call_dry_run_schema["title"] == "ProposalProviderCallDryRun"
    assert provider_result_schema["title"] == "ProposalProviderResultEnvelope"
    assert source_schema["title"] == "SourceRecord"
    assert transcript_schema["title"] == "TranscriptRecord"
    assert timeline_schema["title"] == "TimelineDraft"
    assert timeline_validation_schema["title"] == "TimelineValidationReport"
    assert "analysis_id" in analysis_schema["properties"]
    assert "project" in config_schema["properties"]
    assert "clip_id" in clip_schema["properties"]
    assert "keyframe_id" in keyframe_schema["properties"]
    assert "proposals" in proposal_schema["properties"]
    assert "bgm_requirements" in proposal_context_schema["properties"]
    assert "developer_prompt" in proposal_request_schema["properties"]
    assert "issues" in proposal_validation_schema["properties"]
    assert "reasons" in text_model_gate_schema["properties"]
    assert "steps" in state_schema["properties"]
    assert "model_call_performed" in proposal_adapter_schema["properties"]
    assert "target_lock" in canonical_write_schema["properties"]
    assert "approval_granted" in execution_approval_record_schema["properties"]
    assert "approval_recorded" in execution_approval_schema["properties"]
    assert "approved_execution_gate" in execution_authorization_schema["properties"]
    assert "provider_identity" in execution_input_bundle_schema["properties"]
    assert "secret_source_selection" in execution_readiness_schema["properties"]
    assert "providers" in provider_registry_schema["properties"]
    assert "validation_report_binding" in promotion_authorization_schema["properties"]
    assert "input_binding_check" in promotion_validation_schema["properties"]
    assert "raw_output_captured" in output_quarantine_schema["properties"]
    assert "response_channel" in response_intake_schema["properties"]
    assert "quarantine_input_binding" in response_validation_schema["properties"]
    assert "proposal_content_generated" in mock_handshake_schema["properties"]
    assert "endpoint_reference" in provider_call_dry_run_schema["properties"]
    assert "payload_generated" in provider_result_schema["properties"]
    assert "source_id" in source_schema["properties"]
    assert "transcript_id" in transcript_schema["properties"]
    assert "music_plan" in timeline_schema["properties"]
    assert "issues" in timeline_validation_schema["properties"]


def test_committed_schemas_match_pydantic_generation():
    schema_dir = Path(__file__).resolve().parents[2] / "schemas"
    committed_analysis = json.loads(
        (schema_dir / "analysis_record.schema.json").read_text(encoding="utf-8")
    )
    committed_bgm_analysis = json.loads(
        (schema_dir / "bgm_analysis_report.schema.json").read_text(encoding="utf-8")
    )
    committed_bgm_recommendation_context = json.loads(
        (schema_dir / "bgm_recommendation_context.schema.json").read_text(encoding="utf-8")
    )
    committed_bgm_recommendation_request = json.loads(
        (schema_dir / "bgm_recommendation_request.schema.json").read_text(encoding="utf-8")
    )
    committed_bgm_recommendation_set = json.loads(
        (schema_dir / "bgm_recommendation_set.schema.json").read_text(encoding="utf-8")
    )
    committed_bgm_recommendation_validation = json.loads(
        (schema_dir / "bgm_recommendation_validation_report.schema.json").read_text(encoding="utf-8")
    )
    committed_config = json.loads(
        (schema_dir / "project_config.schema.json").read_text(encoding="utf-8")
    )
    committed_clip = json.loads(
        (schema_dir / "clip_record.schema.json").read_text(encoding="utf-8")
    )
    committed_keyframe = json.loads(
        (schema_dir / "keyframe_record.schema.json").read_text(encoding="utf-8")
    )
    committed_proposal = json.loads(
        (schema_dir / "proposal_set.schema.json").read_text(encoding="utf-8")
    )
    committed_proposal_context = json.loads(
        (schema_dir / "proposal_context.schema.json").read_text(encoding="utf-8")
    )
    committed_proposal_request = json.loads(
        (schema_dir / "proposal_request_packet.schema.json").read_text(
            encoding="utf-8"
        )
    )
    committed_proposal_validation = json.loads(
        (schema_dir / "proposal_validation_report.schema.json").read_text(
            encoding="utf-8"
        )
    )
    committed_state = json.loads(
        (schema_dir / "project_state.schema.json").read_text(encoding="utf-8")
    )
    committed_proposal_adapter = json.loads(
        (schema_dir / "proposal_adapter_check.schema.json").read_text(
            encoding="utf-8"
        )
    )
    committed_canonical_write = json.loads(
        (
            schema_dir / "proposal_canonical_write_transaction_plan.schema.json"
        ).read_text(encoding="utf-8")
    )
    committed_execution_approval_record = json.loads(
        (schema_dir / "proposal_execution_approval_record.schema.json").read_text(
            encoding="utf-8"
        )
    )
    committed_execution_approval = json.loads(
        (schema_dir / "proposal_execution_approval_request.schema.json").read_text(
            encoding="utf-8"
        )
    )
    committed_execution_authorization = json.loads(
        (schema_dir / "proposal_execution_authorization.schema.json").read_text(
            encoding="utf-8"
        )
    )
    committed_execution_input_bundle = json.loads(
        (schema_dir / "proposal_execution_input_bundle.schema.json").read_text(
            encoding="utf-8"
        )
    )
    committed_execution_readiness = json.loads(
        (schema_dir / "proposal_execution_readiness_plan.schema.json").read_text(
            encoding="utf-8"
        )
    )
    committed_provider_registry = json.loads(
        (schema_dir / "proposal_provider_registry.schema.json").read_text(
            encoding="utf-8"
        )
    )
    committed_promotion_authorization = json.loads(
        (
            schema_dir / "proposal_promotion_authorization_plan.schema.json"
        ).read_text(encoding="utf-8")
    )
    committed_promotion_validation = json.loads(
        (
            schema_dir / "proposal_promotion_validation_report.schema.json"
        ).read_text(encoding="utf-8")
    )
    committed_output_quarantine = json.loads(
        (schema_dir / "proposal_provider_output_quarantine.schema.json").read_text(
            encoding="utf-8"
        )
    )
    committed_response_intake = json.loads(
        (schema_dir / "proposal_provider_response_intake_plan.schema.json").read_text(
            encoding="utf-8"
        )
    )
    committed_response_validation = json.loads(
        (
            schema_dir / "proposal_provider_response_validation_plan.schema.json"
        ).read_text(encoding="utf-8")
    )
    committed_mock_handshake = json.loads(
        (schema_dir / "proposal_mock_adapter_handshake.schema.json").read_text(
            encoding="utf-8"
        )
    )
    committed_provider_call_dry_run = json.loads(
        (schema_dir / "proposal_provider_call_dry_run.schema.json").read_text(
            encoding="utf-8"
        )
    )
    committed_provider_result = json.loads(
        (schema_dir / "proposal_provider_result_envelope.schema.json").read_text(
            encoding="utf-8"
        )
    )
    committed_source = json.loads(
        (schema_dir / "source_record.schema.json").read_text(encoding="utf-8")
    )
    committed_transcript = json.loads(
        (schema_dir / "transcript_record.schema.json").read_text(encoding="utf-8")
    )
    committed_text_model_gate = json.loads(
        (schema_dir / "text_model_gate.schema.json").read_text(encoding="utf-8")
    )
    committed_timeline = json.loads(
        (schema_dir / "timeline_draft.schema.json").read_text(encoding="utf-8")
    )
    committed_timeline_validation = json.loads(
        (schema_dir / "timeline_validation_report.schema.json").read_text(
            encoding="utf-8"
        )
    )

    assert committed_analysis == json.loads(
        json.dumps(AnalysisRecord.model_json_schema(), sort_keys=True)
    )
    assert committed_bgm_analysis == json.loads(
        json.dumps(BgmAnalysisReport.model_json_schema(), sort_keys=True)
    )
    assert committed_bgm_recommendation_context == json.loads(
        json.dumps(BgmRecommendationContext.model_json_schema(), sort_keys=True)
    )
    assert committed_bgm_recommendation_request == json.loads(
        json.dumps(BgmRecommendationRequest.model_json_schema(), sort_keys=True)
    )
    assert committed_bgm_recommendation_set == json.loads(
        json.dumps(BgmRecommendationSet.model_json_schema(), sort_keys=True)
    )
    assert committed_bgm_recommendation_validation == json.loads(
        json.dumps(BgmRecommendationValidationReport.model_json_schema(), sort_keys=True)
    )
    assert committed_config == json.loads(
        json.dumps(ProjectConfig.model_json_schema(), sort_keys=True)
    )
    assert committed_clip == json.loads(
        json.dumps(ClipRecord.model_json_schema(), sort_keys=True)
    )
    assert committed_keyframe == json.loads(
        json.dumps(KeyframeRecord.model_json_schema(), sort_keys=True)
    )
    assert committed_proposal == json.loads(
        json.dumps(ProposalSet.model_json_schema(), sort_keys=True)
    )
    assert committed_proposal_context == json.loads(
        json.dumps(ProposalContext.model_json_schema(), sort_keys=True)
    )
    assert committed_proposal_request == json.loads(
        json.dumps(ProposalRequestPacket.model_json_schema(), sort_keys=True)
    )
    assert committed_proposal_validation == json.loads(
        json.dumps(ProposalValidationReport.model_json_schema(), sort_keys=True)
    )
    assert committed_state == json.loads(
        json.dumps(ProjectState.model_json_schema(), sort_keys=True)
    )
    assert committed_proposal_adapter == json.loads(
        json.dumps(ProposalAdapterCheck.model_json_schema(), sort_keys=True)
    )
    assert committed_canonical_write == json.loads(
        json.dumps(
            ProposalCanonicalWriteTransactionPlan.model_json_schema(),
            sort_keys=True,
        )
    )
    assert committed_execution_approval_record == json.loads(
        json.dumps(ProposalExecutionApprovalRecord.model_json_schema(), sort_keys=True)
    )
    assert committed_execution_approval == json.loads(
        json.dumps(ProposalExecutionApprovalRequest.model_json_schema(), sort_keys=True)
    )
    assert committed_execution_authorization == json.loads(
        json.dumps(ProposalExecutionAuthorization.model_json_schema(), sort_keys=True)
    )
    assert committed_execution_input_bundle == json.loads(
        json.dumps(ProposalExecutionInputBundle.model_json_schema(), sort_keys=True)
    )
    assert committed_execution_readiness == json.loads(
        json.dumps(ProposalExecutionReadinessPlan.model_json_schema(), sort_keys=True)
    )
    assert committed_provider_registry == json.loads(
        json.dumps(ProposalProviderRegistry.model_json_schema(), sort_keys=True)
    )
    assert committed_promotion_authorization == json.loads(
        json.dumps(
            ProposalPromotionAuthorizationPlan.model_json_schema(),
            sort_keys=True,
        )
    )
    assert committed_promotion_validation == json.loads(
        json.dumps(
            ProposalPromotionValidationReport.model_json_schema(),
            sort_keys=True,
        )
    )
    assert committed_output_quarantine == json.loads(
        json.dumps(ProposalProviderOutputQuarantine.model_json_schema(), sort_keys=True)
    )
    assert committed_response_intake == json.loads(
        json.dumps(ProposalProviderResponseIntakePlan.model_json_schema(), sort_keys=True)
    )
    assert committed_response_validation == json.loads(
        json.dumps(
            ProposalProviderResponseValidationPlan.model_json_schema(),
            sort_keys=True,
        )
    )
    assert committed_mock_handshake == json.loads(
        json.dumps(ProposalMockAdapterHandshake.model_json_schema(), sort_keys=True)
    )
    assert committed_provider_call_dry_run == json.loads(
        json.dumps(ProposalProviderCallDryRun.model_json_schema(), sort_keys=True)
    )
    assert committed_provider_result == json.loads(
        json.dumps(ProposalProviderResultEnvelope.model_json_schema(), sort_keys=True)
    )
    assert committed_source == json.loads(
        json.dumps(SourceRecord.model_json_schema(), sort_keys=True)
    )
    assert committed_transcript == json.loads(
        json.dumps(TranscriptRecord.model_json_schema(), sort_keys=True)
    )
    assert committed_text_model_gate == json.loads(
        json.dumps(TextModelGate.model_json_schema(), sort_keys=True)
    )
    assert committed_timeline == json.loads(
        json.dumps(TimelineDraft.model_json_schema(), sort_keys=True)
    )
    assert committed_timeline_validation == json.loads(
        json.dumps(TimelineValidationReport.model_json_schema(), sort_keys=True)
    )
