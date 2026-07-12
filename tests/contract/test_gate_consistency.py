from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_current_gate_is_consistent_across_primary_docs():
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    master = (ROOT / "artist_portrait_editor_revision5_optimized.md").read_text(
        encoding="utf-8"
    )
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    progress = (ROOT / "docs" / "DEVELOPMENT_PROGRESS.md").read_text(encoding="utf-8")

    gate = "V2-11 V2 Release"
    assert f"Current gate: {gate}." in agents
    assert "V2：真实视频审美剪辑基线" in master
    assert "V4：导演型创作系统" in master
    assert f"Current {gate} is complete locally" in readme
    assert f"Current active gate: {gate}" in progress
    assert "`V2-10` Real Video Benchmark Pack" in progress
    assert "Current published capability work: `V1-08 Revision promotion, revised render" in readme
    assert "release baseline is `v0.40.0`." in readme
    assert "Current acceptance stage: `ACCEPTANCE-STAGE-07`" in progress


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
    assert "automatic beat-synced editing" in docs
    assert "automatic top-ranked selection" in docs
    assert "render media" in docs or "media rendering" in docs
    assert "fit controls" in docs
    assert "acceptance" in docs
    assert "acceptance profiles" in docs or "acceptance profile" in docs
    assert "real-media acceptance" in docs
    assert "repair-plan" in docs
    assert "manual repair plan" in docs
    assert "next commands directly" in docs
    assert "fcpxml --approval-request" not in docs
    assert "acceptance --approval-request" not in docs
    assert "execution record" in docs
    assert "rhythm" in docs
    assert "edit points" in docs
    assert "media QC" in docs or "media-QC" in docs
    assert "rhythm-aware acceptance" in docs or "rhythm acceptance" in docs
    assert "repair planning" in docs
    assert "workflow planning" in docs
    assert "workflow execution evidence" in docs
    assert "workflow evidence repair" in docs
    assert "workflow repair approval" in docs
    assert "workflow repair execution" in docs
    assert "workflow repair refresh" in docs
    assert "BGM rhythm intelligence" in docs
    assert "bgm_rhythm_intelligence" in docs
    assert "phrase-level manual edit guidance" in docs
    assert "edit_guidance" in docs
    assert "operator runbook" in docs
    assert "operator_runbook" in docs
    assert "editor package" in docs
    assert "editor_package" in docs
    assert "NLE interchange" in docs
    assert "nle_interchange" in docs
    assert "FCPXML draft" in docs
    assert "fcpxml" in docs
    assert "import-review" in docs
    assert "release hardening" in docs
    assert "auto-run pipeline" in docs or "auto-run" in docs
