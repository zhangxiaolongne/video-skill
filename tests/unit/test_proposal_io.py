import ast
from pathlib import Path

import pytest

import artist_portrait_editor.workspace as workspace
from artist_portrait_editor.proposal_artifacts import PROPOSAL_ARTIFACTS
from artist_portrait_editor.proposal_io import (
    PROPOSAL_JSON_MODELS,
    ProposalJsonError,
    read_proposal_artifact,
    validate_proposal_json_model_registry,
)


ROOT = Path(__file__).resolve().parents[2]


def test_proposal_json_model_registry_is_valid_and_complete():
    assert validate_proposal_json_model_registry() == []
    assert set(PROPOSAL_JSON_MODELS) == set(PROPOSAL_ARTIFACTS)


@pytest.mark.parametrize(
    ("artifact_name", "label"),
    sorted(
        (artifact_name, metadata[1])
        for artifact_name, metadata in PROPOSAL_JSON_MODELS.items()
    ),
)
def test_proposal_json_reader_preserves_error_contract(
    tmp_path,
    artifact_name,
    label,
):
    path = tmp_path / f"{artifact_name}.json"
    path.write_text('{"missing": "required fields"}\n', encoding="utf-8")

    with pytest.raises(ProposalJsonError, match=rf"^invalid {label} JSON:"):
        read_proposal_artifact(artifact_name, path)


def test_proposal_json_reader_rejects_unknown_artifact(tmp_path):
    with pytest.raises(KeyError, match="unknown proposal artifact model"):
        read_proposal_artifact("unknown", tmp_path / "unknown.json")


def test_summary_registry_covers_every_proposal_artifact(tmp_path):
    paths = {
        name: tmp_path / spec.filename
        for name, spec in PROPOSAL_ARTIFACTS.items()
    }

    summaries = workspace.proposal_status_summaries(paths)

    assert set(workspace.PROPOSAL_SUMMARY_READERS) == set(PROPOSAL_ARTIFACTS)
    assert set(summaries) == set(PROPOSAL_ARTIFACTS)
    assert all(summary == {"exists": False} for summary in summaries.values())


def test_workspace_proposal_readers_are_compatibility_wrappers():
    path = ROOT / "src" / "artist_portrait_editor" / "workspace.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    proposal_readers = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and (
            node.name.startswith("read_proposal")
            or node.name == "read_text_model_gate_json"
        )
    ]

    assert len(proposal_readers) == 21
    for reader in proposal_readers:
        source = ast.get_source_segment(path.read_text(encoding="utf-8"), reader) or ""
        called_attributes = {
            node.func.attr
            for node in ast.walk(reader)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        assert "model_validate_json" not in called_attributes
        assert "read_text" not in called_attributes
        assert "read_proposal_artifact" in source


def test_workspace_module_stays_below_architecture_budget():
    path = ROOT / "src" / "artist_portrait_editor" / "workspace.py"

    assert len(path.read_text(encoding="utf-8").splitlines()) < 8400
