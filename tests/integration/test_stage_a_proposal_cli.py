import json
from pathlib import Path

from artist_portrait_editor.cli import main

from tests.integration.helpers import (
    build_blocked_proposal_chain,
    build_valid_proposal_project,
    project_fixture_with_scene_detection,
    write_clean_source_ledger,
)


def test_propose_requires_material_map(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(project_fixture_with_scene_detection("off"), encoding="utf-8")
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)

    assert main(["propose", "--project", str(project_path)]) == 7
    assert "propose requires map" in capsys.readouterr().err


def test_propose_writes_only_context_and_host_agent_handoff(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(project_fixture_with_scene_detection("off"), encoding="utf-8")
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    for command in ("segment", "analyze", "map", "brief", "score"):
        assert main([command, "--project", str(project_path), "--quiet"]) in (0, 1)

    assert main(["propose", "--project", str(project_path), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)

    assert payload["status"] == "blocked"
    assert payload["output_refs"] == [
        ".artist-portrait/data/proposal_context.json",
        "output/proposal_agent_handoff.json",
    ]
    handoff = json.loads(
        (tmp_path / "output" / "proposal_agent_handoff.json").read_text(encoding="utf-8")
    )
    assert handoff["mode"] == "codex_chatgpt_host_agent"
    assert "proposal_request" not in handoff
    assert not (tmp_path / ".artist-portrait" / "data" / "proposal_provider_registry.json").exists()


def test_valid_host_agent_candidate_is_quarantined_validated_and_promoted(tmp_path, capsys):
    project_path = build_valid_proposal_project(tmp_path, capsys)

    proposals = json.loads(
        (tmp_path / ".artist-portrait" / "data" / "proposals.json").read_text(encoding="utf-8")
    )
    validation = json.loads(
        (tmp_path / ".artist-portrait" / "data" / "proposal_validation.json").read_text(encoding="utf-8")
    )
    assert proposals["method"] == "codex_host_agent_test_fixture"
    assert validation["error_count"] == 0
    assert not (tmp_path / ".artist-portrait" / "data" / "proposal_provider_result.json").exists()
    assert main(["review", "--project", str(project_path), "--scope", "proposal", "--quiet"]) == 0


def test_invalid_host_agent_candidate_stays_quarantined_without_canonical_overwrite(tmp_path, capsys):
    project_path = build_blocked_proposal_chain(tmp_path, capsys)
    candidate = tmp_path / "invalid_candidate.json"
    candidate.write_text('{"not": "a ProposalSet"}\n', encoding="utf-8")

    assert main(["propose", "--project", str(project_path), "--agent-output", str(candidate), "--json"]) == 9
    payload = json.loads(capsys.readouterr().out)

    assert payload["status"] == "failed"
    assert payload["quarantine"].startswith(".artist-portrait/quarantine/proposals/")
    assert not (tmp_path / ".artist-portrait" / "data" / "proposals.json").exists()
