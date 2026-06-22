import json
from pathlib import Path

from artist_portrait_editor.models.analysis import AnalysisRecord
from artist_portrait_editor.models.clip import ClipRecord
from artist_portrait_editor.models.config import ProjectConfig
from artist_portrait_editor.models.keyframe import KeyframeRecord
from artist_portrait_editor.models.source import SourceRecord
from artist_portrait_editor.models.state import ProjectState
from artist_portrait_editor.models.transcript import TranscriptRecord


def test_schema_generation_from_pydantic_models():
    analysis_schema = AnalysisRecord.model_json_schema()
    config_schema = ProjectConfig.model_json_schema()
    clip_schema = ClipRecord.model_json_schema()
    keyframe_schema = KeyframeRecord.model_json_schema()
    state_schema = ProjectState.model_json_schema()
    source_schema = SourceRecord.model_json_schema()
    transcript_schema = TranscriptRecord.model_json_schema()

    assert analysis_schema["title"] == "AnalysisRecord"
    assert config_schema["title"] == "ProjectConfig"
    assert clip_schema["title"] == "ClipRecord"
    assert keyframe_schema["title"] == "KeyframeRecord"
    assert state_schema["title"] == "ProjectState"
    assert source_schema["title"] == "SourceRecord"
    assert transcript_schema["title"] == "TranscriptRecord"
    assert "analysis_id" in analysis_schema["properties"]
    assert "project" in config_schema["properties"]
    assert "clip_id" in clip_schema["properties"]
    assert "keyframe_id" in keyframe_schema["properties"]
    assert "steps" in state_schema["properties"]
    assert "source_id" in source_schema["properties"]
    assert "transcript_id" in transcript_schema["properties"]


def test_committed_schemas_match_pydantic_generation():
    schema_dir = Path(__file__).resolve().parents[2] / "schemas"
    committed_analysis = json.loads(
        (schema_dir / "analysis_record.schema.json").read_text(encoding="utf-8")
    )
    committed_config = json.loads(
        (schema_dir / "project_config.schema.json").read_text(encoding="utf-8")
    )
    committed_clip = json.loads(
        (schema_dir / "clip_record.schema.json").read_text(encoding="utf-8")
    )
    committed_keyframe = json.loads(
        (schema_dir / "keyframe_record.schema.json").read_text(encoding="utf-8")
    )
    committed_state = json.loads(
        (schema_dir / "project_state.schema.json").read_text(encoding="utf-8")
    )
    committed_source = json.loads(
        (schema_dir / "source_record.schema.json").read_text(encoding="utf-8")
    )
    committed_transcript = json.loads(
        (schema_dir / "transcript_record.schema.json").read_text(encoding="utf-8")
    )

    assert committed_analysis == json.loads(
        json.dumps(AnalysisRecord.model_json_schema(), sort_keys=True)
    )
    assert committed_config == json.loads(
        json.dumps(ProjectConfig.model_json_schema(), sort_keys=True)
    )
    assert committed_clip == json.loads(
        json.dumps(ClipRecord.model_json_schema(), sort_keys=True)
    )
    assert committed_keyframe == json.loads(
        json.dumps(KeyframeRecord.model_json_schema(), sort_keys=True)
    )
    assert committed_state == json.loads(
        json.dumps(ProjectState.model_json_schema(), sort_keys=True)
    )
    assert committed_source == json.loads(
        json.dumps(SourceRecord.model_json_schema(), sort_keys=True)
    )
    assert committed_transcript == json.loads(
        json.dumps(TranscriptRecord.model_json_schema(), sort_keys=True)
    )
