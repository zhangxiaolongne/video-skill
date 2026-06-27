from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_current_gate_is_consistent_across_primary_docs():
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    master = (ROOT / "artist_portrait_editor_revision5_optimized.md").read_text(
        encoding="utf-8"
    )
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    progress = (ROOT / "docs" / "DEVELOPMENT_PROGRESS.md").read_text(encoding="utf-8")

    gate = "V0-018 BGM recommendation review gate"
    assert f"Current gate: {gate}." in agents
    assert gate in master
    assert f"Current {gate} work" in readme
    assert f"Current local gate: {gate}" in progress


def test_historical_fragment_documents_are_removed():
    historical = list((ROOT / "docs").glob("V0_*.md"))
    assert historical == []
    assert not (ROOT / "docs" / "STAGE_A_ACCEPTANCE.md").exists()


def test_current_gate_preserves_remaining_boundaries():
    docs = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "AGENTS.md",
            "SKILL.md",
            "docs/ENGINEERING_SPEC_V0.md",
        )
    )
    assert "network" in docs
    assert "paid API" in docs
    assert "automatic music recommendation" in docs
    assert "fabricate BPM" in docs or "fabricated BPM" in docs
