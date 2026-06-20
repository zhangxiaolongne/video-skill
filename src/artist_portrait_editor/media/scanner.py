from __future__ import annotations

import hashlib
import json
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Callable

from artist_portrait_editor.constants import DATA_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.config import ProjectConfig
from artist_portrait_editor.models.source import (
    Assertion,
    EvidenceRef,
    MediaKind,
    MediaProbe,
    RightsStatus,
    SourceRecord,
    SourceRiskFlag,
    SourceType,
)
from artist_portrait_editor.media.probe import ProbeError, probe_media

SUPPORTED_MEDIA_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".m4v",
    ".mp3",
    ".wav",
}

ProbeFn = Callable[[Path], tuple[MediaKind, MediaProbe]]


class ScanError(Exception):
    pass


class ScanResult:
    def __init__(self, records: list[SourceRecord], warnings: list[str], errors: list[str]):
        self.records = records
        self.warnings = warnings
        self.errors = errors


def scan_project_sources(
    *,
    root: Path,
    config: ProjectConfig,
    probe_fn: ProbeFn = probe_media,
) -> ScanResult:
    media_dir = root / config.paths.media_dir
    if not media_dir.exists():
        raise ScanError(f"media directory does not exist: {config.paths.media_dir}")
    if not media_dir.is_dir():
        raise ScanError(f"media path is not a directory: {config.paths.media_dir}")

    candidates = [
        path
        for path in sorted(media_dir.rglob("*"))
        if path.is_file() and path.suffix.lower() in SUPPORTED_MEDIA_EXTENSIONS
    ]
    if not candidates:
        return ScanResult(records=[], warnings=["no supported media files found"], errors=[])

    grouped_locations: dict[str, list[str]] = defaultdict(list)
    grouped_paths: dict[str, list[Path]] = defaultdict(list)
    errors: list[str] = []

    for path in candidates:
        content_hash = hash_file(path)
        relative = path.relative_to(root).as_posix()
        grouped_locations[content_hash].append(relative)
        grouped_paths[content_hash].append(path)

    records: list[SourceRecord] = []
    warnings: list[str] = []
    namespace = uuid.uuid5(uuid.NAMESPACE_URL, f"artist-portrait-editor:{config.project.id}")

    for content_hash in sorted(grouped_locations):
        locations = sorted(grouped_locations[content_hash])
        primary_path = sorted(grouped_paths[content_hash], key=lambda p: p.as_posix())[0]
        try:
            media_kind, media_probe = probe_fn(primary_path)
        except ProbeError as exc:
            errors.append(f"{locations[0]}: {exc}")
            continue
        source_id = str(uuid.uuid5(namespace, content_hash))
        records.append(
            SourceRecord(
                source_id=source_id,
                locations=locations,
                primary_location=locations[0],
                content_hash=content_hash,
                media_kind=media_kind,
                media_probe=media_probe,
                source_type=Assertion(
                    value=SourceType.other,
                    method="extension_scan",
                    level=1,
                    confidence=0.2,
                    evidence=[EvidenceRef(type="path", ref=locations[0])],
                ),
                rights_status=Assertion(
                    value=RightsStatus.permission_unknown,
                    method="default_policy",
                    level=1,
                    confidence=0.0,
                    evidence=[],
                ),
                provenance_confidence=0.0,
                provenance_method="filesystem_scan",
                provenance_evidence=[EvidenceRef(type="path", ref=location) for location in locations],
                risk_flags=[
                    SourceRiskFlag.unknown_provenance,
                    SourceRiskFlag.low_provenance_confidence,
                    SourceRiskFlag.rights_unknown,
                ],
            )
        )

    if errors and not records:
        return ScanResult(records=[], warnings=warnings, errors=errors)
    warnings.extend(errors)
    return ScanResult(records=records, warnings=warnings, errors=[])


def write_sources_jsonl(root: Path, records: list[SourceRecord]) -> Path:
    output = root / WORKSPACE_DIR / DATA_DIR / "sources.jsonl"
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


def read_sources_jsonl(path: Path) -> list[SourceRecord]:
    records: list[SourceRecord] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(SourceRecord.model_validate_json(line))
        except ValueError as exc:
            raise ScanError(f"invalid SourceRecord JSONL at line {line_number}: {exc}") from exc
    return records


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()
