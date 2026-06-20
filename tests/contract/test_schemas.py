from artist_portrait_editor.models.config import ProjectConfig
from artist_portrait_editor.models.state import ProjectState


def test_schema_generation_from_pydantic_models():
    config_schema = ProjectConfig.model_json_schema()
    state_schema = ProjectState.model_json_schema()

    assert config_schema["title"] == "ProjectConfig"
    assert state_schema["title"] == "ProjectState"
    assert "project" in config_schema["properties"]
    assert "steps" in state_schema["properties"]
