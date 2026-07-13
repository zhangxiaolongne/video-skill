from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from artist_portrait_editor.constants import SCHEMA_VERSION


MemoryCategory = Literal[
    "style",
    "shot",
    "bgm",
    "text",
    "cover",
    "rhythm",
    "transition",
    "composition",
    "duration",
    "audio",
    "ending",
    "constraint",
    "theme",
    "audience",
    "platform",
    "custom",
]


class MemoryIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: Literal["project", "subject"]
    identity_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    identity_source: Literal["project_config", "explicit_cli"]


class MemoryProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provenance_id: str = Field(min_length=1)
    source_type: Literal[
        "project_config",
        "user_explicit",
        "revision_request",
        "revision_application",
        "selected_style",
        "imported_memory",
    ]
    project_id: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    source_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evidence_ids: list[str] = Field(default_factory=list)


class CreativeMemoryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_entry_id: str = Field(min_length=1)
    category: MemoryCategory
    polarity: Literal["prefer", "avoid", "require", "forbid", "context"]
    statement: str = Field(min_length=1)
    strength: Literal["soft", "hard"]
    status: Literal["confirmed", "requested", "observed", "rejected", "unresolved"]
    fulfillment: Literal[
        "applied",
        "partially_applied",
        "manual_only",
        "not_selected",
        "blocked",
        "not_applicable",
        "unverified",
    ]
    applicability: Literal["project_only", "subject_reusable"]
    confidence: float = Field(ge=0, le=1)
    provenance: list[MemoryProvenance] = Field(min_length=1)
    acceptance_required: list[str] = Field(default_factory=list)


class MemoryConflict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conflict_id: str = Field(min_length=1)
    category: MemoryCategory
    entry_ids: list[str] = Field(min_length=2)
    detail: str = Field(min_length=1)
    resolution: str = Field(min_length=1)
    status: Literal["unresolved"] = "unresolved"


class MemoryEvidenceBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    ref: str
    fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    used_for_memory: bool
    limitation: str


class CreativeMemory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    memory_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    identity: MemoryIdentity
    status: Literal["ready", "warning", "blocked"]
    entry_count: int = Field(ge=1)
    confirmed_count: int = Field(ge=0)
    requested_count: int = Field(ge=0)
    hard_constraint_count: int = Field(ge=0)
    unresolved_conflict_count: int = Field(ge=0)
    source_project_ids: list[str] = Field(min_length=1)
    entries: list[CreativeMemoryEntry] = Field(min_length=1)
    conflicts: list[MemoryConflict] = Field(default_factory=list)
    evidence_bindings: list[MemoryEvidenceBinding] = Field(min_length=1)
    retrieval_context: list[str] = Field(min_length=1)
    excluded_candidate_claims: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    explicit_identity_required: bool = True
    memory_applied_to_edit: bool = False
    timeline_mutated: bool = False
    media_rendered: bool = False
    automatic_style_selection: bool = False
    automatic_bgm_selection: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False

    @model_validator(mode="after")
    def validate_counts_and_identity(self) -> "CreativeMemory":
        if self.entry_count != len(self.entries):
            raise ValueError("entry_count must match entries")
        if self.confirmed_count != sum(entry.status == "confirmed" for entry in self.entries):
            raise ValueError("confirmed_count must match entries")
        if self.requested_count != sum(entry.status == "requested" for entry in self.entries):
            raise ValueError("requested_count must match entries")
        if self.hard_constraint_count != sum(entry.strength == "hard" for entry in self.entries):
            raise ValueError("hard_constraint_count must match entries")
        if self.unresolved_conflict_count != len(self.conflicts):
            raise ValueError("unresolved_conflict_count must match conflicts")
        if self.identity.scope == "project" and any(
            entry.applicability == "subject_reusable" for entry in self.entries
        ):
            raise ValueError("project memory cannot claim subject-reusable entries")
        return self
