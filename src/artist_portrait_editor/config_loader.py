from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from artist_portrait_editor.models.config import ProjectConfig


class ConfigLoadError(Exception):
    pass


def load_project_config(project_path: Path) -> ProjectConfig:
    if not project_path.exists():
        raise ConfigLoadError(f"project file does not exist: {project_path}")
    try:
        raw: Any = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigLoadError(f"invalid YAML: {exc}") from exc
    if raw is None:
        raise ConfigLoadError("project.yaml is empty")
    if not isinstance(raw, dict):
        raise ConfigLoadError("project.yaml must contain a mapping")
    try:
        return ProjectConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigLoadError(str(exc)) from exc
