from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from artist_portrait_editor.models.proposal import ProposalSet
from artist_portrait_editor.models.proposal_context import ProposalContext
from artist_portrait_editor.models.proposal_validation import ProposalValidationReport


class ProposalJsonError(ValueError):
    pass


ModelT = TypeVar("ModelT", bound=BaseModel)


PROPOSAL_JSON_MODELS: dict[str, tuple[type[BaseModel], str]] = {
    "proposals": (ProposalSet, "ProposalSet"),
    "proposal_context": (ProposalContext, "ProposalContext"),
    "proposal_validation": (ProposalValidationReport, "ProposalValidationReport"),
}


def validate_proposal_json_model_registry() -> list[str]:
    labels = [label for _, label in PROPOSAL_JSON_MODELS.values()]
    if len(labels) != len(set(labels)):
        return ["proposal JSON model labels must be unique"]
    return []


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
