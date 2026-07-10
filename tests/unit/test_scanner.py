from pathlib import Path

import pytest

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.media.probe import ProbeError
from artist_portrait_editor.media.scanner import (
    hash_file,
    read_sources_jsonl,
    scan_project_sources,
    stable_source_id,
    write_sources_jsonl,
)
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


def test_stable_source_id_depends_on_project_and_content_hash_only():
    content_hash = "sha256:" + "a" * 64

    first = stable_source_id("project-a", content_hash)
    second = stable_source_id("project-a", content_hash)
    different_project = stable_source_id("project-b", content_hash)
    different_hash = stable_source_id("project-a", "sha256:" + "b" * 64)

    assert first == second
    assert first != different_project
    assert first != different_hash


def test_file_move_keeps_source_id_and_updates_location(tmp_path):
    project_path = write_project(tmp_path)
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    original = media_dir / "a.mp4"
    moved = media_dir / "moved.mp4"
    original.write_bytes(b"same-content")
    config = load_project_config(project_path)

    first = scan_project_sources(root=tmp_path, config=config, probe_fn=fake_video_probe)
    first_record = first.records[0]
    original.rename(moved)
    second = scan_project_sources(root=tmp_path, config=config, probe_fn=fake_video_probe)
    second_record = second.records[0]

    assert second_record.source_id == first_record.source_id
    assert second_record.content_hash == first_record.content_hash
    assert second_record.locations == ["media/moved.mp4"]
    assert second_record.primary_location == "media/moved.mp4"


def test_file_content_change_creates_new_source_id(tmp_path):
    project_path = write_project(tmp_path)
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    media = media_dir / "a.mp4"
    media.write_bytes(b"first-content")
    config = load_project_config(project_path)

    first = scan_project_sources(root=tmp_path, config=config, probe_fn=fake_video_probe)
    media.write_bytes(b"changed-content")
    second = scan_project_sources(root=tmp_path, config=config, probe_fn=fake_video_probe)

    assert second.records[0].content_hash != first.records[0].content_hash
    assert second.records[0].source_id != first.records[0].source_id


def test_file_content_change_at_same_location_sets_supersedes_source_id(tmp_path):
    project_path = write_project(tmp_path)
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    media = media_dir / "a.mp4"
    media.write_bytes(b"first-content")
    config = load_project_config(project_path)

    first = scan_project_sources(root=tmp_path, config=config, probe_fn=fake_video_probe)
    media.write_bytes(b"changed-content")
    second = scan_project_sources(
        root=tmp_path,
        config=config,
        probe_fn=fake_video_probe,
        previous_records=first.records,
    )

    assert second.records[0].source_id != first.records[0].source_id
    assert second.records[0].supersedes_source_id == first.records[0].source_id


def test_file_move_and_content_change_does_not_infer_supersedes_source_id(tmp_path):
    project_path = write_project(tmp_path)
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    original = media_dir / "a.mp4"
    moved = media_dir / "moved.mp4"
    original.write_bytes(b"first-content")
    config = load_project_config(project_path)

    first = scan_project_sources(root=tmp_path, config=config, probe_fn=fake_video_probe)
    original.rename(moved)
    moved.write_bytes(b"changed-content")
    second = scan_project_sources(
        root=tmp_path,
        config=config,
        probe_fn=fake_video_probe,
        previous_records=first.records,
    )

    assert second.records[0].source_id != first.records[0].source_id
    assert second.records[0].locations == ["media/moved.mp4"]
    assert second.records[0].supersedes_source_id is None


def test_repeated_write_replaces_sources_jsonl_locations(tmp_path):
    project_path = write_project(tmp_path)
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    original = media_dir / "a.mp4"
    moved = media_dir / "moved.mp4"
    original.write_bytes(b"same-content")
    config = load_project_config(project_path)

    first = scan_project_sources(root=tmp_path, config=config, probe_fn=fake_video_probe)
    output = write_sources_jsonl(tmp_path, first.records)
    original.rename(moved)
    second = scan_project_sources(root=tmp_path, config=config, probe_fn=fake_video_probe)
    write_sources_jsonl(tmp_path, second.records)
    records = read_sources_jsonl(output)

    assert records[0].source_id == first.records[0].source_id
    assert records[0].locations == ["media/moved.mp4"]
    assert not any(location == "media/a.mp4" for location in records[0].locations)


def test_scan_applies_sources_csv_annotation(tmp_path):
    project_path = write_project(tmp_path)
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / "a.mp4").write_bytes(b"content")
    (tmp_path / "sources.csv").write_text(
        "location,source_type,work,role,rights_status,forbidden_by_user,notes\n"
        "media/a.mp4,interview,Work A,Role A,restricted,true,Do not use\n",
        encoding="utf-8",
    )
    config = load_project_config(project_path)

    result = scan_project_sources(root=tmp_path, config=config, probe_fn=fake_video_probe)

    assert result.warnings == []
    record = result.records[0]
    assert record.source_type.value == "interview"
    assert record.source_type.method == "sources_csv"
    assert record.work.value == "Work A"
    assert record.role.value == "Role A"
    assert record.rights_status.value == "restricted"
    assert record.forbidden_by_user is True
    assert "rights_restricted" in [flag.value for flag in record.risk_flags]
    assert "forbidden_by_user" in [flag.value for flag in record.risk_flags]
    assert record.notes == "Do not use"


def test_scan_sources_csv_annotation_can_match_duplicate_location(tmp_path):
    project_path = write_project(tmp_path)
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / "a.mp4").write_bytes(b"same-content")
    (media_dir / "b.mp4").write_bytes(b"same-content")
    (tmp_path / "sources.csv").write_text(
        "location,source_type,rights_status\n"
        "media/b.mp4,stage_performance,owned\n",
        encoding="utf-8",
    )
    config = load_project_config(project_path)

    result = scan_project_sources(root=tmp_path, config=config, probe_fn=fake_video_probe)

    assert result.warnings == []
    assert len(result.records) == 1
    record = result.records[0]
    assert record.locations == ["media/a.mp4", "media/b.mp4"]
    assert record.source_type.value == "stage_performance"
    assert record.rights_status.value == "owned"


def test_scan_reports_sources_csv_warnings(tmp_path):
    project_path = write_project(tmp_path)
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / "a.mp4").write_bytes(b"content")
    (tmp_path / "sources.csv").write_text(
        "location,source_type\n"
        "media/a.mp4,bad_type\n",
        encoding="utf-8",
    )
    config = load_project_config(project_path)

    result = scan_project_sources(root=tmp_path, config=config, probe_fn=fake_video_probe)

    assert result.warnings == ["sources.csv:2: invalid source_type: bad_type"]
    assert result.records[0].source_type.value == "other"


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


def test_hash_file_uses_sha256_prefix(tmp_path):
    path = tmp_path / "file.bin"
    path.write_bytes(b"abc")

    assert hash_file(path) == (
        "sha256:ba7816bf8f01cfea414140de5dae2223"
        "b00361a396177a9cb410ff61f20015ad"
    )


def test_invalid_sources_jsonl_fails_validation(tmp_path):
    path = tmp_path / "sources.jsonl"
    path.write_text('{"source_id": "missing-required-fields"}\n', encoding="utf-8")

    with pytest.raises(Exception, match="invalid SourceRecord JSONL"):
        read_sources_jsonl(path)
