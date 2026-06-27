from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from artist_portrait_editor.constants import WORKSPACE_DIR
from artist_portrait_editor.models.proposal import ProposalSet
from artist_portrait_editor.models.proposal_context import ProposalContext
from artist_portrait_editor.models.proposal_request import ProposalRequestPacket


MAX_AGENT_CANDIDATE_BYTES = 1024 * 1024


class AgentProposalCandidateError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: str,
        quarantine_ref: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.quarantine_ref = quarantine_ref


@dataclass(frozen=True)
class QuarantinedAgentCandidate:
    path: Path
    ref: str
    sha256: str
    byte_count: int
    raw_bytes: bytes


def build_agent_handoff_bundle(
    *,
    context: ProposalContext,
    request: ProposalRequestPacket,
) -> dict:
    return {
        "handoff_version": "1.0",
        "mode": "codex_chatgpt_host_agent",
        "project_id": context.project_id,
        "context_id": context.context_id,
        "request_id": request.request_id,
        "instructions": {
            "output_format": "Return one JSON object and no surrounding prose.",
            "required_root_model": "ProposalSet",
            "required_method_provenance": (
                "Set ProposalSet.method to a value containing host_agent, codex, "
                "or chatgpt."
            ),
            "generation_method": (
                "Use the active Codex/ChatGPT host Agent. Do not call paid APIs, "
                "request API keys, use network search, or generate template proposals."
            ),
            "next_command": (
                "artist-portrait propose --project <project.yaml> "
                "--agent-output <candidate.json>"
            ),
        },
        "proposal_context": context.model_dump(mode="json"),
        "proposal_request": request.model_dump(mode="json"),
        "proposal_set_json_schema": ProposalSet.model_json_schema(),
    }


def write_agent_handoff_bundle(
    *,
    root: Path,
    output_dir: str,
    context: ProposalContext,
    request: ProposalRequestPacket,
) -> Path:
    output = root / output_dir / "proposal_agent_handoff.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(
            build_agent_handoff_bundle(context=context, request=request),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def quarantine_agent_candidate(
    *,
    root: Path,
    candidate_path: Path,
) -> QuarantinedAgentCandidate:
    if candidate_path.is_symlink():
        raise AgentProposalCandidateError(
            "agent proposal candidate must not be a symlink",
            code="agent_candidate_symlink_forbidden",
        )
    if not candidate_path.exists():
        raise AgentProposalCandidateError(
            "agent proposal candidate does not exist",
            code="agent_candidate_missing",
        )
    if not candidate_path.is_file():
        raise AgentProposalCandidateError(
            "agent proposal candidate must be a regular file",
            code="agent_candidate_not_file",
        )
    byte_count = candidate_path.stat().st_size
    if byte_count > MAX_AGENT_CANDIDATE_BYTES:
        raise AgentProposalCandidateError(
            f"agent proposal candidate exceeds {MAX_AGENT_CANDIDATE_BYTES} bytes",
            code="agent_candidate_too_large",
        )
    raw_bytes = candidate_path.read_bytes()
    digest = hashlib.sha256(raw_bytes).hexdigest()
    quarantine_path = (
        root
        / WORKSPACE_DIR
        / "quarantine"
        / "proposals"
        / f"host_agent_{digest}.json"
    )
    quarantine_path.parent.mkdir(parents=True, exist_ok=True)
    if not quarantine_path.exists():
        tmp = quarantine_path.with_suffix(".json.tmp")
        tmp.write_bytes(raw_bytes)
        tmp.replace(quarantine_path)
    quarantine_ref = quarantine_path.relative_to(root).as_posix()
    return QuarantinedAgentCandidate(
        path=quarantine_path,
        ref=quarantine_ref,
        sha256=digest,
        byte_count=byte_count,
        raw_bytes=raw_bytes,
    )


def parse_quarantined_proposal_set(
    candidate: QuarantinedAgentCandidate,
) -> ProposalSet:
    try:
        text = candidate.raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AgentProposalCandidateError(
            "agent proposal candidate must be UTF-8 JSON",
            code="agent_candidate_invalid_utf8",
            quarantine_ref=candidate.ref,
        ) from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AgentProposalCandidateError(
            f"agent proposal candidate is invalid JSON: {exc.msg}",
            code="agent_candidate_invalid_json",
            quarantine_ref=candidate.ref,
        ) from exc
    try:
        return ProposalSet.model_validate(payload)
    except ValidationError as exc:
        raise AgentProposalCandidateError(
            f"agent proposal candidate is not a valid ProposalSet: {exc}",
            code="agent_candidate_schema_invalid",
            quarantine_ref=candidate.ref,
        ) from exc


def require_host_agent_method(
    *,
    proposal_set: ProposalSet,
    candidate: QuarantinedAgentCandidate,
) -> None:
    normalized = proposal_set.method.lower().replace("-", "_").replace(" ", "_")
    if not any(token in normalized for token in ("host_agent", "codex", "chatgpt")):
        raise AgentProposalCandidateError(
            (
                "agent proposal candidate method must identify the Codex/ChatGPT "
                "host Agent"
            ),
            code="agent_candidate_method_invalid",
            quarantine_ref=candidate.ref,
        )
