import json
from pathlib import Path

import artist_portrait_editor.cli as cli
import artist_portrait_editor.workspace as workspace
from artist_portrait_editor.cli import main
from artist_portrait_editor.media.scanner import ScanResult, read_sources_jsonl
from artist_portrait_editor.models.source import (
    Assertion,
    MediaKind,
    MediaProbe,
    RightsStatus,
    SourceRecord,
)
from artist_portrait_editor.models.state import Capabilities


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "stage_a"


def test_validate_valid_project(capsys):
    code = main(["validate", "--project", str(FIXTURES / "valid_project.yaml")])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == "valid"


def test_validate_invalid_project(capsys):
    code = main(["validate", "--project", str(FIXTURES / "invalid_enum.yaml")])
    captured = capsys.readouterr()
    assert code == 3
    assert "features.transcription" in captured.err


def test_init_creates_only_stage_a_artifacts(tmp_path):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    code = main(["init", "--project", str(project_path)])

    assert code in (0, 1)
    assert (tmp_path / ".artist-portrait" / "state.json").exists()
    assert (tmp_path / ".artist-portrait" / "cache").is_dir()
    assert (tmp_path / ".artist-portrait" / "data").is_dir()
    assert (tmp_path / ".artist-portrait" / "runs").is_dir()
    assert (tmp_path / "output" / "run_report.md").exists()

    forbidden = [
        ".artist-portrait/data/sources.jsonl",
        ".artist-portrait/data/clips.jsonl",
        ".artist-portrait/data/transcripts.jsonl",
        ".artist-portrait/data/relations.jsonl",
        ".artist-portrait/data/proposals.json",
        "output/material_map.md",
        "output/proposals.md",
        "output/timeline_draft.json",
        "output/risk_report.md",
    ]
    for relative in forbidden:
        assert not (tmp_path / relative).exists()


def test_init_dry_run_does_not_write_project_files(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    code = main(["init", "--project", str(project_path), "--dry-run", "--json"])
    captured = capsys.readouterr()

    assert code in (0, 1)
    payload = json.loads(captured.out)
    assert payload["project_id"] == "chen_haoyu_portrait_001"
    assert not (tmp_path / ".artist-portrait").exists()
    assert not (tmp_path / "output").exists()


def test_status_before_init_reports_new(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["overall_status"] == "new"
    assert payload["state"] is None


def test_status_after_init_json(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["project_id"] == "chen_haoyu_portrait_001"
    assert payload["steps"]["scan"]["status"] == "pending"


def test_repeated_init_keeps_stage_a_boundary(tmp_path):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)

    forbidden = [
        ".artist-portrait/data/sources.jsonl",
        ".artist-portrait/data/clips.jsonl",
        ".artist-portrait/data/transcripts.jsonl",
        ".artist-portrait/data/relations.jsonl",
        ".artist-portrait/data/proposals.json",
        "output/material_map.md",
        "output/proposals.md",
        "output/timeline_draft.json",
        "output/risk_report.md",
    ]
    for relative in forbidden:
        assert not (tmp_path / relative).exists()


def test_scan_requires_init_first(tmp_path, monkeypatch, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        cli,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True),
    )

    code = main(["scan", "--project", str(project_path)])
    captured = capsys.readouterr()

    assert code == 7
    assert "requires init" in captured.err


def test_scan_missing_media_dependencies_returns_4(tmp_path, monkeypatch, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    monkeypatch.setattr(
        cli,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=False, ffprobe=False),
    )

    code = main(["scan", "--project", str(project_path)])
    captured = capsys.readouterr()

    assert code == 4
    assert "missing required media dependencies" in captured.err


def test_scan_writes_sources_and_updates_state(tmp_path, monkeypatch, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    monkeypatch.setattr(
        cli,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True),
    )

    def fake_scan_project_sources(*, root, config, previous_records=None):
        return ScanResult(
            records=[
                SourceRecord(
                    source_id="source-1",
                    locations=["media/a.mp4"],
                    primary_location="media/a.mp4",
                    content_hash="sha256:" + "a" * 64,
                    media_kind=MediaKind.video,
                    media_probe=MediaProbe(
                        duration=1.0,
                        width=16,
                        height=16,
                        frame_rate=24.0,
                        video_codec="h264",
                        audio_present=False,
                        audio_codec=None,
                    ),
                    source_type=Assertion(
                        value="other",
                        method="test",
                        level=1,
                        confidence=0.2,
                    ),
                    rights_status=Assertion(
                        value=RightsStatus.permission_unknown,
                        method="test",
                        level=1,
                        confidence=0.0,
                    ),
                    provenance_confidence=0.0,
                    provenance_method="test",
                )
            ],
            warnings=[],
            errors=[],
        )

    monkeypatch.setattr(workspace, "scan_project_sources", fake_scan_project_sources)

    code = main(["scan", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["sources"] == 1
    sources_path = tmp_path / ".artist-portrait" / "data" / "sources.jsonl"
    assert sources_path.exists()
    assert len(sources_path.read_text(encoding="utf-8").splitlines()) == 1

    state_payload = json.loads(
        (tmp_path / ".artist-portrait" / "state.json").read_text(encoding="utf-8")
    )
    assert state_payload["steps"]["scan"]["status"] == "completed"
    assert state_payload["steps"]["segment"]["status"] == "pending"
    assert state_payload["steps"]["map"]["status"] == "pending"
    assert not (tmp_path / "output" / "material_map.md").exists()


def test_map_requires_scan_first(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)

    code = main(["map", "--project", str(project_path)])
    captured = capsys.readouterr()

    assert code == 7
    assert "map requires scan" in captured.err


def test_map_writes_material_map_from_sources(tmp_path, monkeypatch, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / "a.mp4").write_bytes(b"content")
    (tmp_path / "sources.csv").write_text(
        "location,source_type,work,role,rights_status,forbidden_by_user,notes\n"
        "media/a.mp4,interview,Work A,Role A,owned,false,Primary interview\n",
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    monkeypatch.setattr(
        cli,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True),
    )

    def fake_probe(path):
        return (
            MediaKind.video,
            MediaProbe(
                duration=12.5,
                width=1920,
                height=1080,
                frame_rate=29.97,
                video_codec="h264",
                audio_present=True,
                audio_codec="aac",
            ),
        )

    from artist_portrait_editor.media import scanner

    original_scan_project_sources = scanner.scan_project_sources

    def scan_with_fake_probe(*, root, config, previous_records=None):
        return original_scan_project_sources(
            root=root,
            config=config,
            probe_fn=fake_probe,
            previous_records=previous_records,
        )

    monkeypatch.setattr(workspace, "scan_project_sources", scan_with_fake_probe)

    assert main(["scan", "--project", str(project_path), "--quiet"]) == 0
    code = main(["map", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["output"] == "output/material_map.md"
    material_map = (tmp_path / "output" / "material_map.md").read_text(encoding="utf-8")
    assert "# Material Map" in material_map
    assert "No transcription, visual analysis" in material_map
    assert "- Source count: `1`" in material_map
    assert "- Total duration seconds: `12.500`" in material_map
    assert "### 1. `media/a.mp4`" in material_map
    assert "- Source type: `interview`" in material_map
    assert "- Rights status: `owned`" in material_map
    assert "- Notes: Primary interview" in material_map

    state_payload = json.loads(
        (tmp_path / ".artist-portrait" / "state.json").read_text(encoding="utf-8")
    )
    assert state_payload["steps"]["map"]["status"] == "completed"
    assert state_payload["steps"]["map"]["output_refs"] == ["output/material_map.md"]


def test_repeated_cli_scan_updates_moved_location(tmp_path, monkeypatch, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    original = media_dir / "a.mp4"
    moved = media_dir / "moved.mp4"
    original.write_bytes(b"same-content")
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    monkeypatch.setattr(
        cli,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True),
    )

    def fake_probe(path):
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

    from artist_portrait_editor.media import scanner

    original_scan_project_sources = scanner.scan_project_sources

    def scan_with_fake_probe(*, root, config, previous_records=None):
        return original_scan_project_sources(
            root=root,
            config=config,
            probe_fn=fake_probe,
            previous_records=previous_records,
        )

    monkeypatch.setattr(workspace, "scan_project_sources", scan_with_fake_probe)

    assert main(["scan", "--project", str(project_path), "--quiet"]) == 0
    sources_path = tmp_path / ".artist-portrait" / "data" / "sources.jsonl"
    first_record = read_sources_jsonl(sources_path)[0]
    original.rename(moved)
    assert main(["scan", "--project", str(project_path), "--quiet"]) == 0
    second_record = read_sources_jsonl(sources_path)[0]

    assert second_record.source_id == first_record.source_id
    assert second_record.locations == ["media/moved.mp4"]


def test_repeated_cli_scan_records_superseded_source_for_same_location_change(
    tmp_path,
    monkeypatch,
    capsys,
):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    media = media_dir / "a.mp4"
    media.write_bytes(b"first-content")
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    monkeypatch.setattr(
        cli,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True),
    )

    def fake_probe(path):
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

    from artist_portrait_editor.media import scanner

    original_scan_project_sources = scanner.scan_project_sources

    def scan_with_fake_probe(*, root, config, previous_records=None):
        return original_scan_project_sources(
            root=root,
            config=config,
            probe_fn=fake_probe,
            previous_records=previous_records,
        )

    monkeypatch.setattr(workspace, "scan_project_sources", scan_with_fake_probe)

    assert main(["scan", "--project", str(project_path), "--quiet"]) == 0
    sources_path = tmp_path / ".artist-portrait" / "data" / "sources.jsonl"
    first_record = read_sources_jsonl(sources_path)[0]
    media.write_bytes(b"changed-content")
    assert main(["scan", "--project", str(project_path), "--quiet"]) == 0
    second_record = read_sources_jsonl(sources_path)[0]

    assert second_record.source_id != first_record.source_id
    assert second_record.locations == ["media/a.mp4"]
    assert second_record.supersedes_source_id == first_record.source_id
