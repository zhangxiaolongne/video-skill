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


# Canonical proposal truth is intentionally small. External candidates belong in
# quarantine; the Agent handoff is a human-facing output, not another data ledger.
PROPOSAL_ARTIFACT_SPECS = (
    ProposalArtifactSpec(
        "proposal_context",
        "proposal_context.json",
        "proposal_context_invalid",
        "proposal context",
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
    return errors


def proposal_artifact_paths(root: Path) -> dict[str, Path]:
    data_dir = root / WORKSPACE_DIR / DATA_DIR
    return {spec.name: data_dir / spec.filename for spec in PROPOSAL_ARTIFACT_SPECS}


def proposal_invalid_artifacts() -> dict[str, tuple[str, str]]:
    return {
        spec.name: (spec.invalid_code, spec.label)
        for spec in PROPOSAL_ARTIFACT_SPECS
        if spec.invalid_code is not None
    }


def proposal_chain_ref_targets(root: Path) -> dict[str, str]:
    paths = proposal_artifact_paths(root)
    return {
        "proposal_context_ref": paths["proposal_context"].relative_to(root).as_posix(),
        "proposals_ref": paths["proposals"].relative_to(root).as_posix(),
        "proposal_validation_ref": paths["proposal_validation"].relative_to(root).as_posix(),
        "target_schema_ref": "schemas/proposal_set.schema.json",
        "material_map_ref": "output/material_map.md",
        "sources_ref": f"{WORKSPACE_DIR}/{DATA_DIR}/sources.jsonl",
        "clips_ref": f"{WORKSPACE_DIR}/{DATA_DIR}/clips.jsonl",
        "analysis_ref": f"{WORKSPACE_DIR}/{DATA_DIR}/analysis.jsonl",
    }


def _load_json_object(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def proposal_chain_issues(root: Path) -> list[dict[str, str]]:
    paths = proposal_artifact_paths(root)
    payloads = {
        name: payload
        for name, path in paths.items()
        if (payload := _load_json_object(path)) is not None
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
                detail="proposal artifacts disagree on project_id: " + ", ".join(sorted(project_ids)),
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
                        detail="proposal context material_map_fingerprint does not match the current material map",
                    )
                )

    validation = payloads.get("proposal_validation")
    if validation:
        expected_context = context_path.relative_to(root).as_posix()
        expected_proposals = paths["proposals"].relative_to(root).as_posix()
        for field, expected in (
            ("proposal_context_ref", expected_context),
            ("proposals_ref", expected_proposals),
        ):
            if validation.get(field) != expected:
                issues.append(
                    _artifact_issue(
                        ref=paths["proposal_validation"].relative_to(root).as_posix(),
                        code="proposal_ref_mismatch",
                        detail=f"proposal validation field `{field}` must reference `{expected}`",
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
