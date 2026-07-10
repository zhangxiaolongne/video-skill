from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from artist_portrait_editor.constants import DATA_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.analysis import AnalysisRecord
from artist_portrait_editor.models.clip import ClipRecord
from artist_portrait_editor.models.keyframe import KeyframeRecord
from artist_portrait_editor.models.transcript import TranscriptRecord
from artist_portrait_editor.workspace_errors import WorkspacePrerequisiteError


Record = TypeVar("Record", bound=BaseModel)


def _write_jsonl(root: Path, filename: str, records: list[Record]) -> Path:
    output = root / WORKSPACE_DIR / DATA_DIR / filename
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(".jsonl.tmp")
    tmp.write_text(
        "".join(
            json.dumps(record.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
            + "\n"
            for record in records
        ),
        encoding="utf-8",
    )
    tmp.replace(output)
    return output


def _read_jsonl(path: Path, model: type[Record]) -> list[Record]:
    records: list[Record] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(model.model_validate_json(line))
        except ValueError as exc:
            raise WorkspacePrerequisiteError(
                f"invalid {model.__name__} JSONL at line {line_number}: {exc}"
            ) from exc
    return records


def write_clips_jsonl(root: Path, clips: list[ClipRecord]) -> Path:
    return _write_jsonl(root, "clips.jsonl", clips)


def read_clips_jsonl(path: Path) -> list[ClipRecord]:
    return _read_jsonl(path, ClipRecord)


def write_transcripts_jsonl(root: Path, transcripts: list[TranscriptRecord]) -> Path:
    return _write_jsonl(root, "transcripts.jsonl", transcripts)


def read_transcripts_jsonl(path: Path) -> list[TranscriptRecord]:
    return _read_jsonl(path, TranscriptRecord)


def write_keyframes_jsonl(root: Path, keyframes: list[KeyframeRecord]) -> Path:
    return _write_jsonl(root, "keyframes.jsonl", keyframes)


def read_keyframes_jsonl(path: Path) -> list[KeyframeRecord]:
    return _read_jsonl(path, KeyframeRecord)


def write_analysis_jsonl(root: Path, analyses: list[AnalysisRecord]) -> Path:
    return _write_jsonl(root, "analysis.jsonl", analyses)


def read_analysis_jsonl(path: Path) -> list[AnalysisRecord]:
    return _read_jsonl(path, AnalysisRecord)
