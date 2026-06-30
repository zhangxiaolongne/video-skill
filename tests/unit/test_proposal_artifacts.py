import json
from pathlib import Path

import pytest

from artist_portrait_editor.proposal_artifacts import (
    PROPOSAL_ARTIFACTS,
    PROPOSAL_ARTIFACT_SPECS,
    proposal_artifact_paths,
    proposal_chain_ref_targets,
    proposal_invalid_artifacts,
    validate_proposal_artifact_registry,
)


def test_proposal_artifact_registry_is_valid_and_complete():
    assert validate_proposal_artifact_registry() == []
    assert len(PROPOSAL_ARTIFACT_SPECS) == 21
    assert len(PROPOSAL_ARTIFACTS) == 21
    assert set(PROPOSAL_ARTIFACTS) == {
        "proposal_context",
        "text_model_gate",
        "proposal_request",
        "proposal_adapter_check",
        "proposal_provider_registry",
        "proposal_mock_adapter_handshake",
        "proposal_execution_approval_request",
        "proposal_execution_approval_record",
        "proposal_execution_readiness_plan",
        "proposal_execution_input_bundle",
        "proposal_provider_call_dry_run",
        "proposal_execution_authorization",
        "proposal_provider_response_intake_plan",
        "proposal_provider_output_quarantine",
        "proposal_provider_response_validation_plan",
        "proposal_promotion_authorization_plan",
        "proposal_promotion_validation_report",
        "proposal_canonical_write_transaction_plan",
        "proposal_provider_result",
        "proposals",
        "proposal_validation",
    }


def test_proposal_artifact_paths_are_canonical(tmp_path):
    paths = proposal_artifact_paths(tmp_path)

    assert all(path.parent == tmp_path / ".artist-portrait" / "data" for path in paths.values())
    assert paths["proposal_context"].name == "proposal_context.json"
    assert paths["proposals"].name == "proposals.json"
    assert paths["proposal_validation"].name == "proposal_validation.json"


def test_proposal_reference_targets_cover_pipeline_aliases(tmp_path):
    refs = proposal_chain_ref_targets(tmp_path)

    assert refs["request_ref"] == ".artist-portrait/data/proposal_request.json"
    assert (
        refs["execution_readiness_ref"]
        == ".artist-portrait/data/proposal_execution_readiness_plan.json"
    )
    assert (
        refs["canonical_write_transaction_ref"]
        == ".artist-portrait/data/proposal_canonical_write_transaction_plan.json"
    )
    assert refs["promotion_target_ref"] == ".artist-portrait/data/proposals.json"
    assert refs["target_schema_ref"] == "schemas/proposal_set.schema.json"


@pytest.mark.parametrize(
    ("artifact_name", "invalid_code"),
    sorted(
        (name, metadata[0])
        for name, metadata in proposal_invalid_artifacts().items()
    ),
)
def test_invalid_diagnostic_matrix_is_registry_driven(artifact_name, invalid_code):
    spec = PROPOSAL_ARTIFACTS[artifact_name]

    assert invalid_code == f"{artifact_name}_invalid"
    assert spec.invalid_code == invalid_code
    assert spec.label


def test_proposal_artifact_module_has_no_execution_or_network_surface():
    module_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "artist_portrait_editor"
        / "proposal_artifacts.py"
    )
    content = module_path.read_text(encoding="utf-8")

    forbidden_imports = (
        "import requests",
        "import urllib",
        "import httpx",
        "import openai",
        "import subprocess",
        "from socket",
    )
    assert not any(token in content for token in forbidden_imports)
    assert "model_call_performed" not in content
    assert "network_performed" not in content


def test_progress_snapshot_is_machine_readable_and_paid_gate_closed():
    root = Path(__file__).resolve().parents[2]
    payload = json.loads(
        (root / "docs" / "current_progress.json").read_text(encoding="utf-8")
    )

    assert payload["capability_gate"] == "V0-041"
    assert payload["milestone"] == "V0-041 workflow repair evidence refresh guidance gate"
    assert payload["active_batch"]["id"] == "V0-041"
    assert payload["active_batch"]["capability_gate"] == payload["capability_gate"]
    assert len(payload["tasks"]) == 10
    assert {task["status"] for task in payload["tasks"]}.issubset(
        {"planned", "in_progress", "completed", "blocked", "dropped"}
    )
    assert payload["forbidden_capabilities"]["host_agent_generation"] is True
    assert payload["forbidden_capabilities"]["timeline_generation"] is True
    assert payload["forbidden_capabilities"]["bgm_analysis"] is True
    assert payload["forbidden_capabilities"]["bgm_technical_analysis"] is True
    assert payload["forbidden_capabilities"]["bgm_recommendation_review"] is True
    assert payload["forbidden_capabilities"]["final_export"] is True
    assert all(
        value is False
        for key, value in payload["forbidden_capabilities"].items()
        if key not in {
            "host_agent_generation",
            "timeline_generation",
            "bgm_analysis",
            "bgm_technical_analysis",
            "bgm_recommendation_review",
            "bgm_beat_engine_evidence",
            "bgm_recommendation_to_fit_selection",
            "bgm_recommendation_fit_review",
            "bgm_fit_controls",
            "project_acceptance",
            "acceptance_profiles",
            "real_media_acceptance_fixtures",
            "acceptance_repair_plans",
            "acceptance_repair_approvals",
            "repair_execution_dry_runs",
            "repair_execution_handoffs",
            "rhythm_planning",
            "rhythm_media_qc",
            "rhythm_acceptance_integration",
            "rhythm_manual_repair_planning",
            "guided_workflow_planning",
            "workflow_execution_evidence_review",
            "workflow_evidence_repair_planning",
            "workflow_repair_approval_dry_run",
            "workflow_repair_execution_review",
            "release_hardening",
            "workflow_repair_refresh_guidance",
            "preview_rendering",
            "final_export",
        }
    )
