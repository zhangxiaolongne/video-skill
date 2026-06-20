import json
from pathlib import Path

from artist_portrait_editor.cli import main


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
