from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class NleSourceBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str
    source_ref: str
    nle_uri: str | None = None
    expected_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    actual_hash: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    exists: bool
    hash_matches: bool
    relink_status: str = Field(pattern=r"^(direct_uri|missing|hash_mismatch)$")
    timeline_item_ids: list[str] = Field(default_factory=list)


class NleDeliverable(BaseModel):
    model_config = ConfigDict(extra="forbid")
    deliverable_id: str
    format: str = Field(pattern=r"^(fcpxml|edl|resolve_markers_csv|premiere_markers_csv|cue_sheet_csv|relink_manifest_csv)$")
    ref: str
    status: str = Field(pattern=r"^(written|blocked)$")
    import_verified: bool = False
    purpose: str
    limitations: list[str] = Field(default_factory=list)


class NleAcceptanceCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    check_id: str
    stage: str = Field(pattern=r"^(pre_import|import|relink|timeline|markers|audio|playback|roundtrip_export)$")
    instruction: str
    required: bool = True
    status: str = Field(default="pending", pattern=r"^(pending|passed|failed|unavailable)$")
    evidence_required: list[str] = Field(default_factory=list)


class NleRoundTripPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = SCHEMA_VERSION
    package_id: str
    project_id: str
    status: str = Field(pattern=r"^(ready|warning|blocked)$")
    timeline_id: str
    timeline_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    editor_package_id: str
    editor_package_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    version_review_id: str | None = None
    version_review_fingerprint: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    exported_version_id: str = "canonical_timeline"
    frame_rate: float = Field(gt=0)
    source_count: int = Field(ge=1)
    directly_linked_source_count: int = Field(ge=0)
    unresolved_source_count: int = Field(ge=0)
    timeline_item_count: int = Field(ge=1)
    marker_count: int = Field(ge=0)
    cue_count: int = Field(ge=1)
    source_bindings: list[NleSourceBinding] = Field(min_length=1)
    deliverables: list[NleDeliverable] = Field(min_length=6)
    acceptance_checks: list[NleAcceptanceCheck] = Field(min_length=8)
    warnings: list[str] = Field(default_factory=list)
    import_performed: bool = False
    relink_performed: bool = False
    playback_checked: bool = False
    roundtrip_verified: bool = False
    canonical_timeline_mutated: bool = False
    media_rendered: bool = False
    automatic_music_selection: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False
