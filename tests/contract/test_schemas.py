import json
from pathlib import Path

from artist_portrait_editor.models.analysis import AnalysisRecord
from artist_portrait_editor.models.clip import ClipRecord
from artist_portrait_editor.models.config import ProjectConfig
from artist_portrait_editor.models.keyframe import KeyframeRecord
from artist_portrait_editor.models.model_gate import TextModelGate
from artist_portrait_editor.models.proposal import ProposalSet
from artist_portrait_editor.models.proposal_adapter import ProposalAdapterCheck
from artist_portrait_editor.models.proposal_adapter import ProposalMockAdapterHandshake
from artist_portrait_editor.models.proposal_adapter import ProposalProviderResultEnvelope
from artist_portrait_editor.models.proposal_adapter import ProposalProviderRegistry
from artist_portrait_editor.models.proposal_context import ProposalContext
from artist_portrait_editor.models.proposal_request import ProposalRequestPacket
from artist_portrait_editor.models.proposal_validation import ProposalValidationReport
from artist_portrait_editor.models.source import SourceRecord
from artist_portrait_editor.models.state import ProjectState
from artist_portrait_editor.models.transcript import TranscriptRecord


def test_schema_generation_from_pydantic_models():
    analysis_schema = AnalysisRecord.model_json_schema()
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
    provider_registry_schema = ProposalProviderRegistry.model_json_schema()
    mock_handshake_schema = ProposalMockAdapterHandshake.model_json_schema()
    provider_result_schema = ProposalProviderResultEnvelope.model_json_schema()
    source_schema = SourceRecord.model_json_schema()
    transcript_schema = TranscriptRecord.model_json_schema()

    assert analysis_schema["title"] == "AnalysisRecord"
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
    assert provider_registry_schema["title"] == "ProposalProviderRegistry"
    assert mock_handshake_schema["title"] == "ProposalMockAdapterHandshake"
    assert provider_result_schema["title"] == "ProposalProviderResultEnvelope"
    assert source_schema["title"] == "SourceRecord"
    assert transcript_schema["title"] == "TranscriptRecord"
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
    assert "providers" in provider_registry_schema["properties"]
    assert "proposal_content_generated" in mock_handshake_schema["properties"]
    assert "payload_generated" in provider_result_schema["properties"]
    assert "source_id" in source_schema["properties"]
    assert "transcript_id" in transcript_schema["properties"]


def test_committed_schemas_match_pydantic_generation():
    schema_dir = Path(__file__).resolve().parents[2] / "schemas"
    committed_analysis = json.loads(
        (schema_dir / "analysis_record.schema.json").read_text(encoding="utf-8")
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
    committed_provider_registry = json.loads(
        (schema_dir / "proposal_provider_registry.schema.json").read_text(
            encoding="utf-8"
        )
    )
    committed_mock_handshake = json.loads(
        (schema_dir / "proposal_mock_adapter_handshake.schema.json").read_text(
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

    assert committed_analysis == json.loads(
        json.dumps(AnalysisRecord.model_json_schema(), sort_keys=True)
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
    assert committed_provider_registry == json.loads(
        json.dumps(ProposalProviderRegistry.model_json_schema(), sort_keys=True)
    )
    assert committed_mock_handshake == json.loads(
        json.dumps(ProposalMockAdapterHandshake.model_json_schema(), sort_keys=True)
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
