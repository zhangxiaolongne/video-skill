from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from artist_portrait_editor.constants import SCHEMA_VERSION


class BenchmarkCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: Literal[
        "input_integrity", "goal_binding", "selection", "structure", "pacing",
        "source_audio_bgm", "text", "composition", "semantic_continuity",
        "technical_delivery",
    ]
    status: Literal["passed", "warning", "failed", "unavailable"]
    finding: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)


class BenchmarkCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    benchmark_id: str
    benchmark_class: Literal["stage_person", "interview_talking_head", "event_promo_mix"]
    project_id: str
    project_ref: str
    title: str
    target_platform: str
    target_duration_seconds: float | None = Field(default=None, gt=0)
    source_count: int = Field(ge=1)
    source_duration_seconds: float = Field(gt=0)
    source_hashes: list[str] = Field(min_length=1)
    rights_statuses: list[str] = Field(min_length=1)
    source_scan_current: bool
    first_cut_present: bool
    second_cut_present: bool
    second_cut_media_valid: bool | None = None
    second_cut_duration_seconds: float | None = Field(default=None, gt=0)
    second_cut_dimensions: str | None = None
    second_cut_publishability: str | None = None
    checklist: list[BenchmarkCheck] = Field(min_length=10, max_length=10)
    failure_examples: list[str] = Field(min_length=1)
    acceptance_status: Literal["closed_loop", "input_baseline", "blocked"]
    acceptance_summary: str = Field(min_length=1)
    model_call_performed_by_cli: bool = False
    network_performed_by_cli: bool = False


class RealVideoBenchmarkPack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    pack_id: str
    generated_at: str
    required_classes: list[str] = Field(min_length=3, max_length=3)
    covered_classes: list[str] = Field(min_length=3, max_length=3)
    benchmarks: list[BenchmarkCase] = Field(min_length=3)
    class_coverage_complete: bool
    closed_loop_count: int = Field(ge=0)
    input_baseline_count: int = Field(ge=0)
    blocked_count: int = Field(ge=0)
    cross_case_findings: list[str] = Field(min_length=3)
    known_blind_spots: list[str] = Field(min_length=1)
    status: Literal["ready", "degraded", "blocked"]
    distributable_media_included: bool = False
    synthetic_fixture_counted_as_real: bool = False
    model_call_performed_by_cli: bool = False
    network_performed_by_cli: bool = False

    @model_validator(mode="after")
    def require_distinct_complete_classes(self) -> "RealVideoBenchmarkPack":
        required = set(self.required_classes)
        covered = set(self.covered_classes)
        actual = {item.benchmark_class for item in self.benchmarks}
        if required != {"stage_person", "interview_talking_head", "event_promo_mix"}:
            raise ValueError("benchmark pack requires the three V2 real-video classes")
        if covered != required or actual != required:
            raise ValueError("benchmark pack must cover each required class exactly")
        if self.closed_loop_count < 1:
            raise ValueError("at least one real benchmark must have a closed first/second-cut loop")
        return self
