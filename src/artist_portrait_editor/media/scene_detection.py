from __future__ import annotations

from importlib import metadata
from pathlib import Path


class SceneDetectionError(Exception):
    pass


def pyscenedetect_version() -> str:
    try:
        return metadata.version("scenedetect")
    except metadata.PackageNotFoundError:
        return "unknown"


def detect_scenes_pyscenedetect(path: Path) -> list[tuple[float, float]]:
    try:
        from scenedetect import SceneManager, open_video
        from scenedetect.detectors import ContentDetector
    except Exception as exc:
        raise SceneDetectionError("PySceneDetect is not installed") from exc

    try:
        video = open_video(str(path))
        scene_manager = SceneManager()
        scene_manager.add_detector(ContentDetector())
        scene_manager.detect_scenes(video)
        scenes = scene_manager.get_scene_list()
    except Exception as exc:
        raise SceneDetectionError(f"PySceneDetect failed for {path}: {exc}") from exc

    boundaries: list[tuple[float, float]] = []
    for start_time, end_time in scenes:
        start_seconds = round(float(start_time.get_seconds()), 3)
        end_seconds = round(float(end_time.get_seconds()), 3)
        if end_seconds > start_seconds:
            boundaries.append((start_seconds, end_seconds))
    if not boundaries:
        raise SceneDetectionError(f"PySceneDetect found no usable scenes for {path}")
    return boundaries
