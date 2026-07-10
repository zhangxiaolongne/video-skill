from pathlib import Path

import pytest

from artist_portrait_editor.proposal_artifacts import PROPOSAL_ARTIFACTS
from artist_portrait_editor.proposal_io import (
    PROPOSAL_JSON_MODELS,
    ProposalJsonError,
    read_proposal_artifact,
    validate_proposal_json_model_registry,
)


def test_proposal_json_model_registry_matches_canonical_artifacts():
    assert validate_proposal_json_model_registry() == []
    assert set(PROPOSAL_JSON_MODELS) == set(PROPOSAL_ARTIFACTS)


@pytest.mark.parametrize(
    ("artifact_name", "label"),
    sorted((name, metadata[1]) for name, metadata in PROPOSAL_JSON_MODELS.items()),
)
def test_proposal_json_reader_preserves_error_contract(tmp_path, artifact_name, label):
    path = tmp_path / f"{artifact_name}.json"
    path.write_text('{"missing": "required fields"}\n', encoding="utf-8")

    with pytest.raises(ProposalJsonError, match=rf"^invalid {label} JSON:"):
        read_proposal_artifact(artifact_name, path)


def test_proposal_json_reader_rejects_unknown_artifact(tmp_path):
    with pytest.raises(KeyError, match="unknown proposal artifact model"):
        read_proposal_artifact("unknown", tmp_path / "unknown.json")


def test_workspace_module_stays_below_architecture_budget():
    path = Path(__file__).resolve().parents[2] / "src" / "artist_portrait_editor" / "workspace.py"

    assert len(path.read_text(encoding="utf-8").splitlines()) < 7500
