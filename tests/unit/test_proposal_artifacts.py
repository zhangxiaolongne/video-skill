import json
from pathlib import Path

import pytest

from artist_portrait_editor.proposal_artifacts import (
    PROPOSAL_ARTIFACTS,
    proposal_artifact_paths,
    proposal_chain_ref_targets,
    proposal_invalid_artifacts,
    validate_proposal_artifact_registry,
)


def test_proposal_artifact_registry_is_small_and_complete():
    assert validate_proposal_artifact_registry() == []
    assert set(PROPOSAL_ARTIFACTS) == {
        "proposal_context",
        "proposals",
        "proposal_validation",
    }


def test_proposal_artifact_paths_are_canonical(tmp_path):
    paths = proposal_artifact_paths(tmp_path)

    assert all(path.parent == tmp_path / ".artist-portrait" / "data" for path in paths.values())
    assert proposal_chain_ref_targets(tmp_path)["proposals_ref"].endswith("proposals.json")


@pytest.mark.parametrize("name", ("proposal_context", "proposals"))
def test_canonical_artifacts_have_invalid_diagnostics(name):
    code, label = proposal_invalid_artifacts()[name]

    assert code == f"{name}_invalid"
    assert label


def test_progress_snapshot_keeps_current_v2_boundaries_machine_readable():
    root = Path(__file__).resolve().parents[2]
    payload = json.loads(
        (root / "docs" / "current_progress.json").read_text(encoding="utf-8")
    )

    assert payload["schema_version"] == "1.5"
    assert payload["capability_gate"] == "V3-04"
    assert payload["active_batch"]["capability_gate"] == payload["capability_gate"]
