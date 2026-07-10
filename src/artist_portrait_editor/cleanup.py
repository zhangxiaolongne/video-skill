from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from artist_portrait_editor.constants import CACHE_DIR, WORKSPACE_DIR


@dataclass(frozen=True)
class CleanupResult:
    removed_cache_bytes: int
    removed_cache_files: int
    removed_temp_files: int


def _directory_usage(path: Path) -> dict[str, int | bool]:
    if not path.exists():
        return {"bytes": 0, "files": 0, "exists": False}
    if path.is_file():
        return {"bytes": path.stat().st_size, "files": 1, "exists": True}

    files = [item for item in path.rglob("*") if item.is_file()]
    return {
        "bytes": sum(item.stat().st_size for item in files),
        "files": len(files),
        "exists": True,
    }


def project_storage_summary(
    root: Path,
    *,
    media_dir: str,
    annotations_dir: str,
    output_dir: str,
) -> dict[str, object]:
    """Expose all local project storage, including rebuildable cache."""
    workspace = root / WORKSPACE_DIR
    locations = {
        "source_media": root / media_dir,
        "annotations": root / annotations_dir,
        "outputs": root / output_dir,
        "workspace_data": workspace / "data",
        "workspace_quarantine": workspace / "quarantine",
        "rebuildable_cache": workspace / CACHE_DIR,
    }
    categories = {
        name: {"path": str(path.relative_to(root)), **_directory_usage(path)}
        for name, path in locations.items()
    }
    return {
        "bytes": sum(item["bytes"] for item in categories.values()),
        "files": sum(item["files"] for item in categories.values()),
        "categories": categories,
        "cleanup_command": "artist-portrait cleanup --project <project.yaml>",
    }


def cleanup_workspace(root: Path) -> CleanupResult:
    """Remove only rebuildable workspace cache and interrupted-write leftovers."""
    cache_dir = root / WORKSPACE_DIR / CACHE_DIR
    cache_files = (
        [path for path in cache_dir.rglob("*") if path.is_file()]
        if cache_dir.exists()
        else []
    )
    removed_cache_bytes = sum(path.stat().st_size for path in cache_files)
    removed_cache_files = len(cache_files)
    if cache_dir.exists():
        shutil.rmtree(cache_dir)

    temp_files = [
        path
        for path in (root / WORKSPACE_DIR).rglob("*.tmp")
        if path.is_file()
    ] if (root / WORKSPACE_DIR).exists() else []
    for path in temp_files:
        path.unlink()

    return CleanupResult(
        removed_cache_bytes=removed_cache_bytes,
        removed_cache_files=removed_cache_files,
        removed_temp_files=len(temp_files),
    )
