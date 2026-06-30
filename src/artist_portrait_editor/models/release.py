from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from artist_portrait_editor.constants import SCHEMA_VERSION


class ReleaseHardeningCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_id: str = Field(min_length=1)
    status: str = Field(pattern=r"^(passed|warning|failed)$")
    summary: str = Field(min_length=1)
    detail: str = Field(min_length=1)


class ReleaseHardeningReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    release_hardening_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    capability_gate: str = Field(min_length=1)
    milestone: str = Field(min_length=1)
    status: str = Field(pattern=r"^(ready_for_local_release|warning|blocked)$")
    check_count: int = Field(ge=0)
    passed_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    checks: list[ReleaseHardeningCheck] = Field(default_factory=list)
    commit_allowed: bool = False
    push_allowed: bool = False
    tag_allowed: bool = False
    network_performed: bool = False
    model_call_performed_by_cli: bool = False
    media_rendered: bool = False
    commands_executed: bool = False
