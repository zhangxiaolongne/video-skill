from __future__ import annotations

import json
from pathlib import Path

from artist_portrait_editor.models.analysis import AnalysisRecord
from artist_portrait_editor.models.clip import ClipRecord
from artist_portrait_editor.models.config import ProjectConfig
from artist_portrait_editor.models.keyframe import KeyframeRecord
from artist_portrait_editor.models.model_gate import TextModelGate
from artist_portrait_editor.models.proposal import ProposalSet
from artist_portrait_editor.models.proposal_adapter import (
    ProposalAdapterCheck,
    ProposalExecutionApprovalRequest,
    ProposalExecutionAuthorization,
    ProposalMockAdapterHandshake,
    ProposalProviderOutputQuarantine,
    ProposalProviderResultEnvelope,
    ProposalProviderRegistry,
)
from artist_portrait_editor.models.proposal_context import ProposalContext
from artist_portrait_editor.models.proposal_request import ProposalRequestPacket
from artist_portrait_editor.models.proposal_validation import ProposalValidationReport
from artist_portrait_editor.models.source import SourceRecord
from artist_portrait_editor.models.state import ProjectState
from artist_portrait_editor.models.transcript import TranscriptRecord


def write_schema_files(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    schemas = {
        "analysis_record.schema.json": AnalysisRecord.model_json_schema(),
        "project_config.schema.json": ProjectConfig.model_json_schema(),
        "project_state.schema.json": ProjectState.model_json_schema(),
        "proposal_adapter_check.schema.json": ProposalAdapterCheck.model_json_schema(),
        "proposal_execution_approval_request.schema.json": (
            ProposalExecutionApprovalRequest.model_json_schema()
        ),
        "proposal_execution_authorization.schema.json": (
            ProposalExecutionAuthorization.model_json_schema()
        ),
        "proposal_mock_adapter_handshake.schema.json": (
            ProposalMockAdapterHandshake.model_json_schema()
        ),
        "proposal_provider_registry.schema.json": ProposalProviderRegistry.model_json_schema(),
        "proposal_provider_output_quarantine.schema.json": (
            ProposalProviderOutputQuarantine.model_json_schema()
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
    }
    for filename, schema in schemas.items():
        (output_dir / filename).write_text(
            json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
