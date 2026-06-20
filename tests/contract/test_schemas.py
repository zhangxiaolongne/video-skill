import json
from pathlib import Path

from artist_portrait_editor.models.config import ProjectConfig
from artist_portrait_editor.models.state import ProjectState


def test_schema_generation_from_pydantic_models():
    config_schema = ProjectConfig.model_json_schema()
    state_schema = ProjectState.model_json_schema()

    assert config_schema["title"] == "ProjectConfig"
    assert state_schema["title"] == "ProjectState"
    assert "project" in config_schema["properties"]
    assert "steps" in state_schema["properties"]


def test_committed_schemas_match_pydantic_generation():
    schema_dir = Path(__file__).resolve().parents[2] / "schemas"
    committed_config = json.loads(
        (schema_dir / "project_config.schema.json").read_text(encoding="utf-8")
    )
    committed_state = json.loads(
        (schema_dir / "project_state.schema.json").read_text(encoding="utf-8")
    )

    assert committed_config == json.loads(
        json.dumps(ProjectConfig.model_json_schema(), sort_keys=True)
    )
    assert committed_state == json.loads(
        json.dumps(ProjectState.model_json_schema(), sort_keys=True)
    )
