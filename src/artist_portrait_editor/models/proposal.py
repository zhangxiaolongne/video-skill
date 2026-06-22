from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from artist_portrait_editor.constants import SCHEMA_VERSION
from artist_portrait_editor.models.source import EvidenceRef


class ProposalId(str, Enum):
    proposal_safe = "proposal_safe"
    proposal_advanced = "proposal_advanced"
    proposal_risky = "proposal_risky"


class ProposalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: ProposalId
    title: str = Field(min_length=1)
    theme: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    required_clip_ids: list[str] = Field(default_factory=list)
    fact_refs: list[EvidenceRef] = Field(default_factory=list)
    story_structure: list[str] = Field(default_factory=list)
    sound_structure: list[str] = Field(default_factory=list)
    visual_motifs: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    minimum_viable_timeline: list[str] = Field(default_factory=list)
    missing_material: list[str] = Field(default_factory=list)
    counter_proposal: str | None = None


class ProposalSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    proposal_set_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    map_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    method: str = Field(min_length=1)
    method_version: str = Field(min_length=1)
    proposals: list[ProposalRecord] = Field(min_length=3, max_length=3)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_required_proposal_ids(self) -> "ProposalSet":
        proposal_ids = {proposal.proposal_id for proposal in self.proposals}
        required = set(ProposalId)
        if proposal_ids != required:
            raise ValueError("proposals must contain safe, advanced, and risky proposal IDs")
        return self
