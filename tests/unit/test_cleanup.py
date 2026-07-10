from pathlib import Path

from artist_portrait_editor.cleanup import cleanup_workspace, project_storage_summary
from artist_portrait_editor.cli import main


def test_cleanup_removes_only_rebuildable_cache_and_temp_files(tmp_path: Path):
    cache_file = tmp_path / ".artist-portrait" / "cache" / "preview" / "segment.mp4"
    cache_file.parent.mkdir(parents=True)
    cache_file.write_bytes(b"cache")
    temp_file = tmp_path / ".artist-portrait" / "data" / "state.json.tmp"
    temp_file.parent.mkdir(parents=True)
    temp_file.write_text("partial", encoding="utf-8")
    source = tmp_path / "media" / "source.mp4"
    source.parent.mkdir()
    source.write_bytes(b"source")
    output = tmp_path / "output" / "final_export.mp4"
    output.parent.mkdir()
    output.write_bytes(b"output")

    result = cleanup_workspace(tmp_path)

    assert result.removed_cache_files == 1
    assert result.removed_cache_bytes == len(b"cache")
    assert result.removed_temp_files == 1
    assert not cache_file.exists()
    assert not temp_file.exists()
    assert source.read_bytes() == b"source"
    assert output.read_bytes() == b"output"


def test_cleanup_cli_requires_a_valid_project_and_reports_json(tmp_path: Path, capsys):
    project = tmp_path / "project.yaml"
    project.write_text(
        """
schema_version: \"0.3\"
project:
  id: cleanup-test
  title: Cleanup Test
  artist_name: Test
  language: en
creative_brief:
  theme: test
  audience: test
  platform: test
  target_duration_seconds: 30
  aspect_ratio: \"9:16\"
  tone: [test]
content_policy:
  allow_role_dialogue: false
  allow_real_person_role_mix: false
  allow_unconfirmed_visual_material: false
  allow_interview_audio: false
  allow_music: false
  allow_restricted_rights: false
features:
  transcription: off
  scene_detection: off
  visual_analysis: off
  experimental_relations: false
data_policy:
  allow_remote_text_model: false
  allow_remote_vision_model: false
  include_absolute_paths_in_remote_requests: false
paths:
  media_dir: ./media
  annotations_dir: ./annotations
  output_dir: ./output
""".strip()
        + "\n",
        encoding="utf-8",
    )
    cache_file = tmp_path / ".artist-portrait" / "cache" / "cached.wav"
    cache_file.parent.mkdir(parents=True)
    cache_file.write_bytes(b"cached")

    assert main(["cleanup", "--project", str(project), "--json"]) == 0

    assert '"removed_cache_files": 1' in capsys.readouterr().out
    assert not cache_file.exists()


def test_project_storage_summary_keeps_rebuildable_cache_visible(tmp_path: Path):
    media = tmp_path / "media" / "source.mp4"
    output = tmp_path / "output" / "final.mp4"
    cache = tmp_path / ".artist-portrait" / "cache" / "preview.mp4"
    for path, contents in ((media, b"media"), (output, b"output"), (cache, b"cache")):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)

    summary = project_storage_summary(
        tmp_path,
        media_dir="media",
        annotations_dir="annotations",
        output_dir="output",
    )

    assert summary["bytes"] == len(b"mediaoutputcache")
    assert summary["categories"]["source_media"]["bytes"] == len(b"media")
    assert summary["categories"]["outputs"]["bytes"] == len(b"output")
    assert summary["categories"]["rebuildable_cache"]["bytes"] == len(b"cache")
