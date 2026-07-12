from __future__ import annotations

from enum import Enum
from pathlib import PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from artist_portrait_editor.constants import SCHEMA_VERSION


class FeatureSwitch(str, Enum):
    off = "off"
    auto = "auto"
    required = "required"


class ProjectInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    artist_name: str = Field(min_length=1)
    language: str = Field(min_length=2)


class CreativeBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    platform: str = Field(min_length=1)
    target_duration_seconds: int | None = Field(default=None, gt=0)
    aspect_ratio: str = Field(min_length=3)
    tone: list[str] = Field(default_factory=list)


class ContentPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allow_role_dialogue: bool
    allow_real_person_role_mix: bool
    allow_unconfirmed_visual_material: bool
    allow_interview_audio: bool
    allow_music: bool
    allow_restricted_rights: bool


class Features(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transcription: FeatureSwitch = FeatureSwitch.auto
    scene_detection: FeatureSwitch = FeatureSwitch.auto
    visual_analysis: FeatureSwitch = FeatureSwitch.off
    experimental_relations: bool = False

    @field_validator("transcription", "scene_detection", "visual_analysis", mode="before")
    @classmethod
    def normalize_yaml_boolean_switches(cls, value: object) -> object:
        # PyYAML follows YAML 1.1 and parses unquoted "off" as False.
        # The project spec uses `visual_analysis: off`, so accept that form.
        if value is False:
            return "off"
        return value


class DataPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allow_remote_text_model: bool = False
    allow_remote_vision_model: bool = False
    include_absolute_paths_in_remote_requests: bool = False


class Paths(BaseModel):
    model_config = ConfigDict(extra="forbid")

    media_dir: str = "./media"
    annotations_dir: str = "./annotations"
    output_dir: str = "./output"

    @field_validator("media_dir", "annotations_dir", "output_dir")
    @classmethod
    def require_project_relative_path(cls, value: str) -> str:
        if not value:
            raise ValueError("path must not be empty")
        normalized = value.replace("\\", "/")
        path = PurePosixPath(normalized)
        if path.is_absolute():
            raise ValueError("path must be relative to project.yaml")
        if ".." in path.parts:
            raise ValueError("path must not traverse outside the project")
        return normalized


class ProjectConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    project: ProjectInfo
    creative_brief: CreativeBrief
    content_policy: ContentPolicy
    features: Features = Field(default_factory=Features)
    data_policy: DataPolicy = Field(default_factory=DataPolicy)
    paths: Paths = Field(default_factory=Paths)

    @field_validator("schema_version")
    @classmethod
    def require_supported_schema(cls, value: str) -> str:
        if value != SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {SCHEMA_VERSION!r}")
        return value

    @model_validator(mode="after")
    def enforce_stage_a_boundaries(self) -> "ProjectConfig":
        if (
            self.data_policy.include_absolute_paths_in_remote_requests
            and not (
                self.data_policy.allow_remote_text_model
                or self.data_policy.allow_remote_vision_model
            )
        ):
            raise ValueError(
                "absolute paths in remote requests require a remote model policy"
            )
        return self
