from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class StepStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    completed_with_warnings = "completed_with_warnings"
    skipped = "skipped"
    blocked = "blocked"
    failed = "failed"
    invalidated = "invalidated"


class OverallStatus(str, Enum):
    new = "new"
    ready = "ready"
    running = "running"
    degraded = "degraded"
    blocked = "blocked"


class ActiveMode(str, Enum):
    core = "core"
    creative = "creative"


class Capabilities(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ffmpeg: bool = False
    ffprobe: bool = False
    pyscenedetect: bool = False
    faster_whisper: bool = False
    opencv: bool = False
    beat_librosa: bool = False
    beat_aubio: bool = False
    beat_essentia: bool = False
    beat_madmom: bool = False
    text_model: bool = False
    vision_model: bool = False


class StepLedgerEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: StepStatus = StepStatus.pending
    input_fingerprint: str | None = None
    output_refs: list[str] = Field(default_factory=list)
    last_run_id: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ProjectState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    project_id: str
    overall_status: OverallStatus = OverallStatus.ready
    active_mode: ActiveMode = ActiveMode.core
    capabilities: Capabilities = Field(default_factory=Capabilities)
    steps: dict[str, StepLedgerEntry] = Field(default_factory=dict)
    latest_run_id: str | None = None
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def initial_steps() -> dict[str, StepLedgerEntry]:
    return {
        "validate": StepLedgerEntry(),
        "init": StepLedgerEntry(),
        "scan": StepLedgerEntry(),
        "segment": StepLedgerEntry(),
        "transcribe": StepLedgerEntry(),
        "keyframes": StepLedgerEntry(),
        "analyze": StepLedgerEntry(),
        "relate": StepLedgerEntry(),
        "map": StepLedgerEntry(),
        "brief": StepLedgerEntry(),
        "score": StepLedgerEntry(),
        "propose": StepLedgerEntry(),
        "timeline": StepLedgerEntry(),
        "sound": StepLedgerEntry(),
        "cut_review": StepLedgerEntry(),
        "composition": StepLedgerEntry(),
        "composition_review": StepLedgerEntry(),
        "composition_preview": StepLedgerEntry(),
        "reframe": StepLedgerEntry(),
        "evidence_map": StepLedgerEntry(),
        "editorial_score": StepLedgerEntry(),
        "aesthetic_baseline_context": StepLedgerEntry(),
        "aesthetic_baseline": StepLedgerEntry(),
        "second_cut": StepLedgerEntry(),
        "revision": StepLedgerEntry(),
        "revision_application": StepLedgerEntry(),
        "revision_promotion": StepLedgerEntry(),
        "bgm_import": StepLedgerEntry(),
        "bgm_analyze": StepLedgerEntry(),
        "bgm_rhythm": StepLedgerEntry(),
        "bgm_recommend": StepLedgerEntry(),
        "review_bgm_recommendation": StepLedgerEntry(),
        "bgm_fit": StepLedgerEntry(),
        "preview": StepLedgerEntry(),
        "review_preview": StepLedgerEntry(),
        "final_export": StepLedgerEntry(),
        "review_final_export": StepLedgerEntry(),
        "review_bgm": StepLedgerEntry(),
        "review_project": StepLedgerEntry(),
        "review_proposal": StepLedgerEntry(),
        "review_timeline": StepLedgerEntry(),
        "acceptance": StepLedgerEntry(),
        "rhythm": StepLedgerEntry(),
        "workflow": StepLedgerEntry(),
        "workflow_execution_review": StepLedgerEntry(),
        "operator": StepLedgerEntry(),
        "editor_package": StepLedgerEntry(),
        "nle_plan": StepLedgerEntry(),
        "fcpxml_draft": StepLedgerEntry(),
        "fcpxml_import_review": StepLedgerEntry(),
        "fcpxml_repair_plan": StepLedgerEntry(),
    }
