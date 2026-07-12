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
from artist_portrait_editor.media.sources_csv import SourceAnnotation, load_sources_csv

SUPPORTED_MEDIA_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".m4v",
    ".ogv",
    ".webm",
    ".mp3",
    ".wav",
}

ProbeFn = Callable[[Path], tuple[MediaKind, MediaProbe]]


class ScanError(Exception):
    pass


class SourceLedgerError(ScanError):
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
    previous_records: list[SourceRecord] | None = None,
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
    source_csv = load_sources_csv(root)
    warnings.extend(source_csv.warnings)
    previous_by_location = previous_record_by_location(previous_records or [])
    for content_hash in sorted(grouped_locations):
        locations = sorted(grouped_locations[content_hash])
        primary_path = sorted(grouped_paths[content_hash], key=lambda p: p.as_posix())[0]
        try:
            media_kind, media_probe = probe_fn(primary_path)
        except ProbeError as exc:
            errors.append(f"{locations[0]}: {exc}")
            continue
        source_id = stable_source_id(config.project.id, content_hash)
        annotation = first_annotation_for_locations(locations, source_csv.annotations)
        supersedes_source_id = supersedes_for_locations(
            locations=locations,
            content_hash=content_hash,
            source_id=source_id,
            previous_by_location=previous_by_location,
        )
        records.append(
            build_source_record(
                annotation=annotation,
                source_id=source_id,
                locations=locations,
                primary_location=locations[0],
                content_hash=content_hash,
                media_kind=media_kind,
                media_probe=media_probe,
                supersedes_source_id=supersedes_source_id,
            )
        )

    if errors and not records:
        return ScanResult(records=[], warnings=warnings, errors=errors)
    warnings.extend(errors)
    return ScanResult(records=records, warnings=warnings, errors=[])


def stable_source_id(project_id: str, content_hash: str) -> str:
    namespace = uuid.uuid5(uuid.NAMESPACE_URL, f"artist-portrait-editor:{project_id}")
    return str(uuid.uuid5(namespace, content_hash))


def first_annotation_for_locations(
    locations: list[str],
    annotations: dict[str, SourceAnnotation],
) -> SourceAnnotation | None:
    for location in locations:
        if location in annotations:
            return annotations[location]
    return None


def previous_record_by_location(records: list[SourceRecord]) -> dict[str, SourceRecord]:
    previous: dict[str, SourceRecord] = {}
    for record in records:
        for location in record.locations:
            previous[location] = record
    return previous


def supersedes_for_locations(
    *,
    locations: list[str],
    content_hash: str,
    source_id: str,
    previous_by_location: dict[str, SourceRecord],
) -> str | None:
    for location in locations:
        previous = previous_by_location.get(location)
        if (
            previous is not None
            and previous.content_hash != content_hash
            and previous.source_id != source_id
        ):
            return previous.source_id
    return None


def build_source_record(
    *,
    annotation: SourceAnnotation | None,
    source_id: str,
    locations: list[str],
    primary_location: str,
    content_hash: str,
    media_kind: MediaKind,
    media_probe: MediaProbe,
    supersedes_source_id: str | None = None,
) -> SourceRecord:
    csv_evidence = [
        EvidenceRef(type="sources_csv", ref=f"sources.csv:{annotation.line_number}")
    ] if annotation else []
    source_type = Assertion(
        value=annotation.source_type if annotation and annotation.source_type else SourceType.other,
        method="sources_csv" if annotation and annotation.source_type else "extension_scan",
        level=1,
        confidence=0.7 if annotation and annotation.source_type else 0.2,
        evidence=csv_evidence or [EvidenceRef(type="path", ref=primary_location)],
    )
    rights_value = (
        annotation.rights_status
        if annotation and annotation.rights_status
        else RightsStatus.permission_unknown
    )
    rights_status = Assertion(
        value=rights_value,
        method="sources_csv" if annotation and annotation.rights_status else "default_policy",
        level=1,
        confidence=0.7 if annotation and annotation.rights_status else 0.0,
        evidence=csv_evidence,
    )
    risk_flags = [
        SourceRiskFlag.unknown_provenance,
        SourceRiskFlag.low_provenance_confidence,
    ]
    if rights_value == RightsStatus.permission_unknown:
        risk_flags.append(SourceRiskFlag.rights_unknown)
    if rights_value == RightsStatus.restricted:
        risk_flags.append(SourceRiskFlag.rights_restricted)
    if annotation and annotation.forbidden_by_user:
        risk_flags.append(SourceRiskFlag.forbidden_by_user)

    return SourceRecord(
        source_id=source_id,
        locations=locations,
        primary_location=primary_location,
        content_hash=content_hash,
        supersedes_source_id=supersedes_source_id,
        media_kind=media_kind,
        media_probe=media_probe,
        source_type=source_type,
        work=text_assertion(annotation.work, csv_evidence) if annotation and annotation.work else None,
        role=text_assertion(annotation.role, csv_evidence) if annotation and annotation.role else None,
        rights_status=rights_status,
        provenance_confidence=0.7 if annotation else 0.0,
        provenance_method="sources_csv" if annotation else "filesystem_scan",
        provenance_evidence=csv_evidence
        or [EvidenceRef(type="path", ref=location) for location in locations],
        forbidden_by_user=bool(annotation and annotation.forbidden_by_user),
        risk_flags=risk_flags,
        notes=annotation.notes if annotation else None,
    )


def text_assertion(value: str, evidence: list[EvidenceRef]) -> Assertion:
    return Assertion(
        value=value,
        method="sources_csv",
        level=1,
        confidence=0.7,
        evidence=evidence,
    )


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
            raise SourceLedgerError(
                f"invalid SourceRecord JSONL at line {line_number}: {exc}"
            ) from exc
    return records


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()
