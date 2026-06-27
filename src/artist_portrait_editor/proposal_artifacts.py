from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from artist_portrait_editor.constants import DATA_DIR, WORKSPACE_DIR


@dataclass(frozen=True)
class ProposalArtifactSpec:
    name: str
    filename: str
    invalid_code: str | None
    label: str


PROPOSAL_ARTIFACT_SPECS = (
    ProposalArtifactSpec(
        "proposal_context",
        "proposal_context.json",
        "proposal_context_invalid",
        "proposal context",
    ),
    ProposalArtifactSpec(
        "text_model_gate",
        "text_model_gate.json",
        "text_model_gate_invalid",
        "text model gate",
    ),
    ProposalArtifactSpec(
        "proposal_request",
        "proposal_request.json",
        "proposal_request_invalid",
        "proposal request",
    ),
    ProposalArtifactSpec(
        "proposal_adapter_check",
        "proposal_adapter_check.json",
        "proposal_adapter_check_invalid",
        "proposal adapter check",
    ),
    ProposalArtifactSpec(
        "proposal_provider_registry",
        "proposal_provider_registry.json",
        "proposal_provider_registry_invalid",
        "proposal provider registry",
    ),
    ProposalArtifactSpec(
        "proposal_mock_adapter_handshake",
        "proposal_mock_adapter_handshake.json",
        "proposal_mock_adapter_handshake_invalid",
        "proposal mock adapter handshake",
    ),
    ProposalArtifactSpec(
        "proposal_execution_approval_request",
        "proposal_execution_approval_request.json",
        "proposal_execution_approval_request_invalid",
        "proposal execution approval request",
    ),
    ProposalArtifactSpec(
        "proposal_execution_approval_record",
        "proposal_execution_approval_record.json",
        "proposal_execution_approval_record_invalid",
        "proposal execution approval record",
    ),
    ProposalArtifactSpec(
        "proposal_execution_readiness_plan",
        "proposal_execution_readiness_plan.json",
        "proposal_execution_readiness_plan_invalid",
        "proposal execution readiness plan",
    ),
    ProposalArtifactSpec(
        "proposal_execution_input_bundle",
        "proposal_execution_input_bundle.json",
        "proposal_execution_input_bundle_invalid",
        "proposal execution input bundle",
    ),
    ProposalArtifactSpec(
        "proposal_provider_call_dry_run",
        "proposal_provider_call_dry_run.json",
        "proposal_provider_call_dry_run_invalid",
        "proposal provider call dry run",
    ),
    ProposalArtifactSpec(
        "proposal_execution_authorization",
        "proposal_execution_authorization.json",
        "proposal_execution_authorization_invalid",
        "proposal execution authorization",
    ),
    ProposalArtifactSpec(
        "proposal_provider_response_intake_plan",
        "proposal_provider_response_intake_plan.json",
        "proposal_provider_response_intake_plan_invalid",
        "proposal provider response intake plan",
    ),
    ProposalArtifactSpec(
        "proposal_provider_output_quarantine",
        "proposal_provider_output_quarantine.json",
        "proposal_provider_output_quarantine_invalid",
        "proposal provider output quarantine",
    ),
    ProposalArtifactSpec(
        "proposal_provider_response_validation_plan",
        "proposal_provider_response_validation_plan.json",
        "proposal_provider_response_validation_plan_invalid",
        "proposal provider response validation plan",
    ),
    ProposalArtifactSpec(
        "proposal_promotion_authorization_plan",
        "proposal_promotion_authorization_plan.json",
        "proposal_promotion_authorization_plan_invalid",
        "proposal promotion authorization plan",
    ),
    ProposalArtifactSpec(
        "proposal_promotion_validation_report",
        "proposal_promotion_validation_report.json",
        "proposal_promotion_validation_report_invalid",
        "proposal promotion validation report",
    ),
    ProposalArtifactSpec(
        "proposal_canonical_write_transaction_plan",
        "proposal_canonical_write_transaction_plan.json",
        "proposal_canonical_write_transaction_plan_invalid",
        "proposal canonical write transaction plan",
    ),
    ProposalArtifactSpec(
        "proposal_provider_result",
        "proposal_provider_result.json",
        "proposal_provider_result_invalid",
        "proposal provider result envelope",
    ),
    ProposalArtifactSpec(
        "proposals",
        "proposals.json",
        "proposals_invalid",
        "proposals ledger",
    ),
    ProposalArtifactSpec(
        "proposal_validation",
        "proposal_validation.json",
        None,
        "proposal validation report",
    ),
)

PROPOSAL_ARTIFACTS = {spec.name: spec for spec in PROPOSAL_ARTIFACT_SPECS}


def validate_proposal_artifact_registry() -> list[str]:
    errors: list[str] = []
    names = [spec.name for spec in PROPOSAL_ARTIFACT_SPECS]
    filenames = [spec.filename for spec in PROPOSAL_ARTIFACT_SPECS]
    invalid_codes = [
        spec.invalid_code
        for spec in PROPOSAL_ARTIFACT_SPECS
        if spec.invalid_code is not None
    ]
    if len(names) != len(set(names)):
        errors.append("proposal artifact names must be unique")
    if len(filenames) != len(set(filenames)):
        errors.append("proposal artifact filenames must be unique")
    if len(invalid_codes) != len(set(invalid_codes)):
        errors.append("proposal invalid diagnostic codes must be unique")
    for spec in PROPOSAL_ARTIFACT_SPECS:
        if not spec.name or not spec.label:
            errors.append("proposal artifact names and labels must be non-empty")
        if Path(spec.filename).name != spec.filename or not spec.filename.endswith(".json"):
            errors.append(f"invalid proposal artifact filename: {spec.filename}")
        if spec.invalid_code is not None and not spec.invalid_code.endswith("_invalid"):
            errors.append(f"invalid proposal diagnostic code: {spec.invalid_code}")
    return errors


def proposal_artifact_paths(root: Path) -> dict[str, Path]:
    data_dir = root / WORKSPACE_DIR / DATA_DIR
    return {
        spec.name: data_dir / spec.filename
        for spec in PROPOSAL_ARTIFACT_SPECS
    }


def proposal_invalid_artifacts() -> dict[str, tuple[str, str]]:
    return {
        spec.name: (spec.invalid_code, spec.label)
        for spec in PROPOSAL_ARTIFACT_SPECS
        if spec.invalid_code is not None
    }


def proposal_chain_ref_targets(root: Path) -> dict[str, str]:
    paths = proposal_artifact_paths(root)
    refs = {
        f"{name}_ref": path.relative_to(root).as_posix()
        for name, path in paths.items()
    }
    refs.update(
        {
            "proposal_context_ref": refs["proposal_context_ref"],
            "text_model_gate_ref": refs["text_model_gate_ref"],
            "request_ref": refs["proposal_request_ref"],
            "adapter_check_ref": refs["proposal_adapter_check_ref"],
            "registry_ref": refs["proposal_provider_registry_ref"],
            "handshake_ref": refs["proposal_mock_adapter_handshake_ref"],
            "approval_request_ref": refs["proposal_execution_approval_request_ref"],
            "approval_record_ref": refs["proposal_execution_approval_record_ref"],
            "execution_readiness_ref": refs["proposal_execution_readiness_plan_ref"],
            "readiness_plan_ref": refs["proposal_execution_readiness_plan_ref"],
            "execution_input_bundle_ref": refs["proposal_execution_input_bundle_ref"],
            "input_bundle_ref": refs["proposal_execution_input_bundle_ref"],
            "provider_call_dry_run_ref": refs["proposal_provider_call_dry_run_ref"],
            "response_intake_ref": refs["proposal_provider_response_intake_plan_ref"],
            "output_quarantine_ref": refs["proposal_provider_output_quarantine_ref"],
            "response_validation_ref": refs[
                "proposal_provider_response_validation_plan_ref"
            ],
            "promotion_authorization_ref": refs[
                "proposal_promotion_authorization_plan_ref"
            ],
            "promotion_validation_report_ref": refs[
                "proposal_promotion_validation_report_ref"
            ],
            "canonical_write_transaction_ref": refs[
                "proposal_canonical_write_transaction_plan_ref"
            ],
            "promotion_target_ref": refs["proposals_ref"],
            "canonical_target_ref": refs["proposals_ref"],
            "target_schema_ref": "schemas/proposal_set.schema.json",
            "response_contract_ref": "schemas/proposal_set.schema.json",
            "material_map_ref": "output/material_map.md",
            "sources_ref": f"{WORKSPACE_DIR}/{DATA_DIR}/sources.jsonl",
            "clips_ref": f"{WORKSPACE_DIR}/{DATA_DIR}/clips.jsonl",
            "analysis_ref": f"{WORKSPACE_DIR}/{DATA_DIR}/analysis.jsonl",
        }
    )
    return refs


def load_json_object(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def proposal_chain_issues(root: Path) -> list[dict[str, str]]:
    paths = proposal_artifact_paths(root)
    ref_targets = proposal_chain_ref_targets(root)
    payloads = {
        name: payload
        for name, path in paths.items()
        if (payload := load_json_object(path)) is not None
    }
    if not payloads:
        return []

    issues: list[dict[str, str]] = []
    project_ids = {
        str(payload["project_id"])
        for payload in payloads.values()
        if payload.get("project_id")
    }
    if len(project_ids) > 1:
        issues.append(
            _artifact_issue(
                ref=f"{WORKSPACE_DIR}/{DATA_DIR}",
                code="proposal_project_id_mismatch",
                detail=(
                    "proposal artifacts disagree on project_id: "
                    + ", ".join(sorted(project_ids))
                ),
            )
        )

    missing_allowed = {
        ref_targets["promotion_target_ref"],
        ref_targets["canonical_target_ref"],
        ref_targets["target_schema_ref"],
        ref_targets["response_contract_ref"],
    }
    for artifact_name, payload in sorted(payloads.items()):
        artifact_ref = paths[artifact_name].relative_to(root).as_posix()
        for field, expected_ref in ref_targets.items():
            actual_ref = payload.get(field)
            if actual_ref is None:
                continue
            if not isinstance(actual_ref, str) or actual_ref != expected_ref:
                issues.append(
                    _artifact_issue(
                        ref=artifact_ref,
                        code="proposal_ref_mismatch",
                        detail=(
                            f"`{artifact_ref}` field `{field}` references "
                            f"`{actual_ref}`; expected `{expected_ref}`"
                        ),
                    )
                )
                continue
            if expected_ref not in missing_allowed and not (root / expected_ref).exists():
                issues.append(
                    _artifact_issue(
                        ref=artifact_ref,
                        code="proposal_ref_missing",
                        detail=(
                            f"`{artifact_ref}` field `{field}` references missing "
                            f"artifact `{expected_ref}`"
                        ),
                    )
                )

    context_path = paths["proposal_context"]
    context = payloads.get("proposal_context")
    if context:
        material_map_ref = context.get("material_map_ref")
        material_map_path = root / material_map_ref if isinstance(material_map_ref, str) else None
        if material_map_path and material_map_path.exists():
            actual = _fingerprint_file(material_map_path)
            if context.get("material_map_fingerprint") != actual:
                issues.append(
                    _artifact_issue(
                        ref=context_path.relative_to(root).as_posix(),
                        code="proposal_artifact_stale",
                        detail=(
                            "proposal context material_map_fingerprint does not match "
                            "the current material map"
                        ),
                    )
                )

    if context_path.exists():
        context_fingerprint = _fingerprint_file(context_path)
        for artifact_name in ("text_model_gate", "proposal_request"):
            payload = payloads.get(artifact_name)
            if (
                payload
                and payload.get("proposal_context_fingerprint") != context_fingerprint
            ):
                issues.append(
                    _artifact_issue(
                        ref=paths[artifact_name].relative_to(root).as_posix(),
                        code="proposal_artifact_stale",
                        detail=(
                            f"`{artifact_name}` proposal_context_fingerprint does not "
                            "match the current proposal context"
                        ),
                    )
                )
    return issues


def _fingerprint_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact_issue(*, ref: str, code: str, detail: str) -> dict[str, str]:
    return {
        "scope": "artifact",
        "step": "propose",
        "ref": ref,
        "location": ref,
        "code": code,
        "severity": "error",
        "detail": detail,
        "next_action": "artist-portrait propose --project <project.yaml>",
    }
