from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from artist_portrait_editor.models.source import RightsStatus, SourceType


TRUE_VALUES = {"1", "true", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "no", "n", "off", ""}


@dataclass(frozen=True)
class SourceAnnotation:
    location: str
    source_type: SourceType | None = None
    work: str | None = None
    role: str | None = None
    rights_status: RightsStatus | None = None
    forbidden_by_user: bool | None = None
    notes: str | None = None
    line_number: int = 0


@dataclass(frozen=True)
class SourceCsvLoadResult:
    annotations: dict[str, SourceAnnotation]
    warnings: list[str]


def load_sources_csv(root: Path) -> SourceCsvLoadResult:
    path = root / "sources.csv"
    if not path.exists():
        return SourceCsvLoadResult(annotations={}, warnings=[])

    warnings: list[str] = []
    annotations: dict[str, SourceAnnotation] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return SourceCsvLoadResult(annotations={}, warnings=["sources.csv is empty"])
        for line_number, row in enumerate(reader, start=2):
            location = clean(row.get("location") or row.get("path") or row.get("file"))
            if not location:
                warnings.append(f"sources.csv:{line_number}: missing location")
                continue
            location = normalize_location(location)
            if location.startswith("/") or ".." in Path(location).parts:
                warnings.append(f"sources.csv:{line_number}: location must be project-relative")
                continue
            source_type = parse_enum(
                SourceType,
                clean(row.get("source_type") or row.get("media_type")),
                "source_type",
                line_number,
                warnings,
            )
            rights_status = parse_enum(
                RightsStatus,
                clean(row.get("rights_status")),
                "rights_status",
                line_number,
                warnings,
            )
            forbidden_by_user = parse_bool(
                clean(row.get("forbidden_by_user")),
                "forbidden_by_user",
                line_number,
                warnings,
            )
            annotations[normalize_location(location)] = SourceAnnotation(
                location=location,
                source_type=source_type,
                work=clean(row.get("work")),
                role=clean(row.get("role")),
                rights_status=rights_status,
                forbidden_by_user=forbidden_by_user,
                notes=clean(row.get("notes")),
                line_number=line_number,
            )
    return SourceCsvLoadResult(annotations=annotations, warnings=warnings)


def clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def normalize_location(value: str) -> str:
    return value.removeprefix("./").replace("\\", "/")


def parse_enum(enum_type, value: str | None, field: str, line_number: int, warnings: list[str]):
    if value is None:
        return None
    try:
        return enum_type(value)
    except ValueError:
        warnings.append(f"sources.csv:{line_number}: invalid {field}: {value}")
        return None


def parse_bool(value: str | None, field: str, line_number: int, warnings: list[str]) -> bool | None:
    if value is None:
        return None
    lowered = value.lower()
    if lowered in TRUE_VALUES:
        return True
    if lowered in FALSE_VALUES:
        return False
    warnings.append(f"sources.csv:{line_number}: invalid {field}: {value}")
    return None
