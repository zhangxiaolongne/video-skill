from pathlib import Path

import pytest

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.media.probe import ProbeError
from artist_portrait_editor.media.scanner import read_sources_jsonl, scan_project_sources, write_sources_jsonl
from artist_portrait_editor.models.source import MediaKind, MediaProbe


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "stage_a"


def write_project(tmp_path: Path) -> Path:
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return project_path


def fake_video_probe(path: Path):
    return (
        MediaKind.video,
        MediaProbe(
            duration=1.0,
            width=16,
            height=16,
            frame_rate=24.0,
            video_codec="h264",
            audio_present=False,
            audio_codec=None,
        ),
    )


def test_scan_empty_media_dir_returns_warning(tmp_path):
    project_path = write_project(tmp_path)
    (tmp_path / "media").mkdir()
    config = load_project_config(project_path)

    result = scan_project_sources(root=tmp_path, config=config, probe_fn=fake_video_probe)

    assert result.records == []
    assert result.errors == []
    assert result.warnings == ["no supported media files found"]


def test_scan_deduplicates_identical_media_content(tmp_path):
    project_path = write_project(tmp_path)
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / "a.mp4").write_bytes(b"same-content")
    (media_dir / "b.mp4").write_bytes(b"same-content")
    config = load_project_config(project_path)

    result = scan_project_sources(root=tmp_path, config=config, probe_fn=fake_video_probe)

    assert result.errors == []
    assert len(result.records) == 1
    record = result.records[0]
    assert record.locations == ["media/a.mp4", "media/b.mp4"]
    assert record.primary_location == "media/a.mp4"
    assert record.media_kind == MediaKind.video


def test_scan_all_probe_failures_are_errors(tmp_path):
    project_path = write_project(tmp_path)
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / "bad.mp4").write_bytes(b"not media")
    config = load_project_config(project_path)

    def fail_probe(path: Path):
        raise ProbeError("decode failed")

    result = scan_project_sources(root=tmp_path, config=config, probe_fn=fail_probe)

    assert result.records == []
    assert result.warnings == []
    assert result.errors == ["media/bad.mp4: decode failed"]


def test_scan_missing_media_dir_fails(tmp_path):
    project_path = write_project(tmp_path)
    config = load_project_config(project_path)

    with pytest.raises(Exception, match="media directory does not exist"):
        scan_project_sources(root=tmp_path, config=config, probe_fn=fake_video_probe)


def test_sources_jsonl_round_trips_through_pydantic(tmp_path):
    project_path = write_project(tmp_path)
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / "a.mp4").write_bytes(b"content")
    config = load_project_config(project_path)
    result = scan_project_sources(root=tmp_path, config=config, probe_fn=fake_video_probe)

    output = write_sources_jsonl(tmp_path, result.records)
    records = read_sources_jsonl(output)

    assert len(records) == 1
    assert records[0].source_id == result.records[0].source_id


def test_invalid_sources_jsonl_fails_validation(tmp_path):
    path = tmp_path / "sources.jsonl"
    path.write_text('{"source_id": "missing-required-fields"}\n', encoding="utf-8")

    with pytest.raises(Exception, match="invalid SourceRecord JSONL"):
        read_sources_jsonl(path)
