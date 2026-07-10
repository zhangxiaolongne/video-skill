from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from artist_portrait_editor.models.proposal import ProposalSet
from artist_portrait_editor.models.proposal_context import ProposalContext
from artist_portrait_editor.models.proposal_validation import ProposalValidationReport
from artist_portrait_editor.proposal_io import read_proposal_artifact
from artist_portrait_editor.workspace_errors import WorkspacePrerequisiteError


ProposalModel = TypeVar("ProposalModel", bound=BaseModel)


def _read_proposal_model(
    artifact_name: str,
    model: type[ProposalModel],
    path: Path,
) -> ProposalModel:
    try:
        return model.model_validate(read_proposal_artifact(artifact_name, path))
    except ValueError as exc:
        raise WorkspacePrerequisiteError(str(exc)) from exc


def read_proposals_json(path: Path) -> ProposalSet:
    return _read_proposal_model("proposals", ProposalSet, path)


def read_proposal_context_json(path: Path) -> ProposalContext:
    return _read_proposal_model("proposal_context", ProposalContext, path)


def read_proposal_validation_json(path: Path) -> ProposalValidationReport:
    return _read_proposal_model(
        "proposal_validation",
        ProposalValidationReport,
        path,
    )
