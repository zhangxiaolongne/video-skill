from pathlib import Path

import pytest

from artist_portrait_editor.config_loader import ConfigLoadError, load_project_config


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "stage_a"


def test_valid_project_config_loads():
    config = load_project_config(FIXTURES / "valid_project.yaml")
    assert config.schema_version == "0.3"
    assert config.project.id == "chen_haoyu_portrait_001"
    assert config.features.transcription == "auto"


@pytest.mark.parametrize(
    "filename",
    [
        "invalid_missing_field.yaml",
        "invalid_enum.yaml",
        "invalid_path_policy.yaml",
    ],
)
def test_invalid_project_configs_fail(filename):
    with pytest.raises(ConfigLoadError):
        load_project_config(FIXTURES / filename)
