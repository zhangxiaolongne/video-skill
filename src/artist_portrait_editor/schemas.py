from __future__ import annotations

import json
from pathlib import Path

from artist_portrait_editor.models.config import ProjectConfig
from artist_portrait_editor.models.source import SourceRecord
from artist_portrait_editor.models.state import ProjectState


def write_schema_files(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    schemas = {
        "project_config.schema.json": ProjectConfig.model_json_schema(),
        "project_state.schema.json": ProjectState.model_json_schema(),
        "source_record.schema.json": SourceRecord.model_json_schema(),
    }
    for filename, schema in schemas.items():
        (output_dir / filename).write_text(
            json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
