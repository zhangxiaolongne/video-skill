import json
from pathlib import Path

import artist_portrait_editor.cli as cli
import artist_portrait_editor.workspace as workspace
from artist_portrait_editor.cli import main
from artist_portrait_editor.media.scanner import ScanResult
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

    def fake_scan_project_sources(*, root, config):
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
