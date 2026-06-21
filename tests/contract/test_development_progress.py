from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_development_progress_records_versions_and_bgm_constraint():
    content = (ROOT / "docs" / "DEVELOPMENT_PROGRESS.md").read_text(encoding="utf-8")

    assert "V0-002a" in content
    assert "V0-002q" in content
    assert "BGM must not be treated as a final decorative layer" in content
    assert "BPM" in content
    assert "subtitle entrances/exits" in content
    assert "ducking under speech" in content
    assert "proposal, timeline, review, and preview gates" in content
