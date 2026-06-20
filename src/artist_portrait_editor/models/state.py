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
        "analyze": StepLedgerEntry(),
        "relate": StepLedgerEntry(),
        "map": StepLedgerEntry(),
        "propose": StepLedgerEntry(),
        "timeline": StepLedgerEntry(),
        "review_project": StepLedgerEntry(),
        "review_proposal": StepLedgerEntry(),
        "review_timeline": StepLedgerEntry(),
    }
