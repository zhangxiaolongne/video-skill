import json

import pytest

from artist_portrait_editor.proposal_handoff import (
    MAX_AGENT_CANDIDATE_BYTES,
    AgentProposalCandidateError,
    quarantine_agent_candidate,
)


def test_agent_candidate_is_quarantined_by_content_hash(tmp_path):
    candidate = tmp_path / "candidate.json"
    candidate.write_text('{"proposal": true}\n', encoding="utf-8")

    result = quarantine_agent_candidate(root=tmp_path, candidate_path=candidate)

    assert result.byte_count == candidate.stat().st_size
    assert result.path.read_bytes() == candidate.read_bytes()
    assert result.ref.startswith(
        ".artist-portrait/quarantine/proposals/host_agent_"
    )
    assert result.ref.endswith(".json")


def test_agent_candidate_missing_and_directory_are_rejected(tmp_path):
    with pytest.raises(AgentProposalCandidateError) as missing:
        quarantine_agent_candidate(
            root=tmp_path,
            candidate_path=tmp_path / "missing.json",
        )
    assert missing.value.code == "agent_candidate_missing"

    directory = tmp_path / "candidate-dir"
    directory.mkdir()
    with pytest.raises(AgentProposalCandidateError) as not_file:
        quarantine_agent_candidate(root=tmp_path, candidate_path=directory)
    assert not_file.value.code == "agent_candidate_not_file"


def test_agent_candidate_symlink_is_rejected(tmp_path):
    target = tmp_path / "target.json"
    target.write_text(json.dumps({"ok": True}), encoding="utf-8")
    symlink = tmp_path / "candidate.json"
    symlink.symlink_to(target)

    with pytest.raises(AgentProposalCandidateError) as error:
        quarantine_agent_candidate(root=tmp_path, candidate_path=symlink)

    assert error.value.code == "agent_candidate_symlink_forbidden"


def test_agent_candidate_size_limit_is_enforced_before_read(tmp_path):
    candidate = tmp_path / "large.json"
    candidate.write_bytes(b"x" * (MAX_AGENT_CANDIDATE_BYTES + 1))

    with pytest.raises(AgentProposalCandidateError) as error:
        quarantine_agent_candidate(root=tmp_path, candidate_path=candidate)

    assert error.value.code == "agent_candidate_too_large"
    assert not (tmp_path / ".artist-portrait" / "quarantine").exists()
