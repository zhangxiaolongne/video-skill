from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from artist_portrait_editor.constants import SCHEMA_VERSION


class SecondCutAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(pattern=r"^second_cut_action_[0-9]{2}$")
    order: int = Field(ge=1)
    domain: str = Field(
        pattern=r"^(selection|structure|trim|reframe|source_audio|bgm|text|transition|pause|ending|verification)$"
    )
    operation: str = Field(min_length=1)
    target_segment_ids: list[str] = Field(default_factory=list)
    source_range: list[float] | None = Field(default=None, min_length=2, max_length=2)
    requested_duration_seconds: float | None = Field(default=None, gt=0)
    reframe_candidate_ids: list[str] = Field(default_factory=list)
    execution_status: str = Field(pattern=r"^(deterministic|manual_boundary_required|blocked)$")
    prerequisites: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(min_length=1)
    owns_issue_ids: list[str] = Field(default_factory=list)
    rationale: str = Field(min_length=1)
    expected_effect: str = Field(min_length=1)
    downstream_impacts: list[str] = Field(default_factory=list)
    applied: bool = False


class SecondCutCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    candidate_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    aesthetic_baseline_id: str = Field(min_length=1)
    aesthetic_baseline_ref: str = Field(min_length=1)
    aesthetic_baseline_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    baseline_timeline_id: str = Field(min_length=1)
    baseline_timeline_ref: str = Field(min_length=1)
    baseline_timeline_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    selected_concept_id: str = Field(pattern=r"^concept_[a-z0-9_]+$")
    selected_concept_name: str = Field(min_length=1)
    target_duration_seconds: float = Field(gt=0)
    target_duration_source: str = Field(pattern=r"^(project_config|aesthetic_concept)$")
    concept_duration_seconds: float = Field(gt=0)
    concept_duration_overridden: bool = False
    status: str = Field(pattern=r"^(ready|warning|blocked)$")
    action_count: int = Field(ge=1)
    deterministic_action_count: int = Field(ge=0)
    manual_boundary_action_count: int = Field(ge=0)
    blocked_action_count: int = Field(ge=0)
    actions: list[SecondCutAction] = Field(min_length=1)
    ordered_segment_ids: list[str] = Field(min_length=1)
    owned_issue_ids: list[str] = Field(default_factory=list)
    unowned_high_priority_issue_ids: list[str] = Field(default_factory=list)
    acceptance_requirements: list[str] = Field(min_length=1)
    warnings: list[str] = Field(default_factory=list)
    canonical_timeline_mutated: bool = False
    candidate_media_rendered: bool = False
    edit_points_applied: bool = False
    reframes_applied: bool = False
    music_selected: bool = False
    automatic_bgm_fit: bool = False
    model_call_performed_by_cli: bool = False
    network_performed: bool = False

    @model_validator(mode="after")
    def validate_counts_and_truth(self) -> "SecondCutCandidate":
        if self.action_count != len(self.actions):
            raise ValueError("second-cut action_count mismatch")
        statuses = [item.execution_status for item in self.actions]
        expected = {
            "deterministic_action_count": statuses.count("deterministic"),
            "manual_boundary_action_count": statuses.count("manual_boundary_required"),
            "blocked_action_count": statuses.count("blocked"),
        }
        for field, value in expected.items():
            if getattr(self, field) != value:
                raise ValueError(f"second-cut {field} mismatch")
        orders = [item.order for item in self.actions]
        if orders != list(range(1, len(orders) + 1)):
            raise ValueError("second-cut action order must be contiguous")
        if any(item.applied for item in self.actions):
            raise ValueError("second-cut plan must not claim applied actions")
        if any((self.canonical_timeline_mutated, self.candidate_media_rendered,
                self.edit_points_applied, self.reframes_applied, self.music_selected,
                self.automatic_bgm_fit, self.model_call_performed_by_cli,
                self.network_performed)):
            raise ValueError("second-cut candidate violates supervised planning boundary")
        action_owned = sorted({issue_id for item in self.actions for issue_id in item.owns_issue_ids})
        if sorted(self.owned_issue_ids) != action_owned:
            raise ValueError("second-cut owned issue ids do not match action ownership")
        if self.status != "blocked" and self.unowned_high_priority_issue_ids:
            raise ValueError("non-blocked second-cut candidate cannot leave high-priority issues unowned")
        return self
