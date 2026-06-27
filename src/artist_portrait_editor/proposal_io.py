from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

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


class ProposalJsonError(ValueError):
    pass


ModelT = TypeVar("ModelT", bound=BaseModel)


PROPOSAL_JSON_MODELS: dict[str, tuple[type[BaseModel], str]] = {
    "proposals": (ProposalSet, "ProposalSet"),
    "proposal_context": (ProposalContext, "ProposalContext"),
    "text_model_gate": (TextModelGate, "TextModelGate"),
    "proposal_request": (ProposalRequestPacket, "ProposalRequestPacket"),
    "proposal_adapter_check": (ProposalAdapterCheck, "ProposalAdapterCheck"),
    "proposal_provider_registry": (
        ProposalProviderRegistry,
        "ProposalProviderRegistry",
    ),
    "proposal_mock_adapter_handshake": (
        ProposalMockAdapterHandshake,
        "ProposalMockAdapterHandshake",
    ),
    "proposal_execution_approval_request": (
        ProposalExecutionApprovalRequest,
        "ProposalExecutionApprovalRequest",
    ),
    "proposal_execution_approval_record": (
        ProposalExecutionApprovalRecord,
        "ProposalExecutionApprovalRecord",
    ),
    "proposal_execution_readiness_plan": (
        ProposalExecutionReadinessPlan,
        "ProposalExecutionReadinessPlan",
    ),
    "proposal_execution_input_bundle": (
        ProposalExecutionInputBundle,
        "ProposalExecutionInputBundle",
    ),
    "proposal_provider_call_dry_run": (
        ProposalProviderCallDryRun,
        "ProposalProviderCallDryRun",
    ),
    "proposal_execution_authorization": (
        ProposalExecutionAuthorization,
        "ProposalExecutionAuthorization",
    ),
    "proposal_provider_response_intake_plan": (
        ProposalProviderResponseIntakePlan,
        "ProposalProviderResponseIntakePlan",
    ),
    "proposal_provider_output_quarantine": (
        ProposalProviderOutputQuarantine,
        "ProposalProviderOutputQuarantine",
    ),
    "proposal_provider_response_validation_plan": (
        ProposalProviderResponseValidationPlan,
        "ProposalProviderResponseValidationPlan",
    ),
    "proposal_promotion_authorization_plan": (
        ProposalPromotionAuthorizationPlan,
        "ProposalPromotionAuthorizationPlan",
    ),
    "proposal_promotion_validation_report": (
        ProposalPromotionValidationReport,
        "ProposalPromotionValidationReport",
    ),
    "proposal_canonical_write_transaction_plan": (
        ProposalCanonicalWriteTransactionPlan,
        "ProposalCanonicalWriteTransactionPlan",
    ),
    "proposal_provider_result": (
        ProposalProviderResultEnvelope,
        "ProposalProviderResultEnvelope",
    ),
    "proposal_validation": (
        ProposalValidationReport,
        "ProposalValidationReport",
    ),
}


def validate_proposal_json_model_registry() -> list[str]:
    errors: list[str] = []
    labels = [label for _, label in PROPOSAL_JSON_MODELS.values()]
    if len(labels) != len(set(labels)):
        errors.append("proposal JSON model labels must be unique")
    for artifact_name, (model, label) in PROPOSAL_JSON_MODELS.items():
        if not artifact_name or not label:
            errors.append("proposal JSON registry keys and labels must be non-empty")
        if not issubclass(model, BaseModel):
            errors.append(f"proposal JSON model is not a BaseModel: {artifact_name}")
    return errors


def read_proposal_json(path: Path, model: type[ModelT], label: str) -> ModelT:
    try:
        return model.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ProposalJsonError(f"invalid {label} JSON: {exc}") from exc


def read_proposal_artifact(name: str, path: Path) -> BaseModel:
    try:
        model, label = PROPOSAL_JSON_MODELS[name]
    except KeyError as exc:
        raise KeyError(f"unknown proposal artifact model: {name}") from exc
    return read_proposal_json(path, model, label)
