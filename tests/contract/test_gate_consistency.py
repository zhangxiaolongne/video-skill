from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_current_gate_is_fixed_window_segmentation_foundation_across_primary_docs():
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    master = (ROOT / "artist_portrait_editor_revision5_optimized.md").read_text(
        encoding="utf-8"
    )
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    vision = (ROOT / "docs" / "VISION.md").read_text(encoding="utf-8")
    progress = (ROOT / "docs" / "DEVELOPMENT_PROGRESS.md").read_text(encoding="utf-8")
    v004 = (ROOT / "docs" / "V0_004_SEGMENTATION_FOUNDATION.md").read_text(
        encoding="utf-8"
    )

    assert "Current gate: V0-004 fixed-window segmentation foundation only." in agents
    assert "V0-004 固定窗口切分基础" in master
    assert "Current V0-004 fixed-window segmentation foundation work" in readme
    assert "Current implementation gate: V0-004 fixed-window segmentation foundation only." in vision
    assert "Current local gate: V0-004 fixed-window segmentation foundation only" in progress
    assert "V0-004 opens deterministic fixed-window segmentation only" in v004


def test_current_gate_forbids_future_media_and_creative_surfaces():
    docs = "\n".join(
        [
            (ROOT / "AGENTS.md").read_text(encoding="utf-8"),
            (ROOT / "SKILL.md").read_text(encoding="utf-8"),
            (ROOT / "docs" / "V0_004_SEGMENTATION_FOUNDATION.md").read_text(
                encoding="utf-8"
            ),
        ]
    )

    assert "PySceneDetect" in docs
    assert "Whisper" in docs
    assert "OpenCV" in docs
    assert "BGM selection" in docs
    assert "timeline generation" in docs
    assert "preview rendering" in docs
    assert "model calls" in docs
    assert "network search" in docs
    assert "image generation or image editing" in docs


def test_stage_a_acceptance_is_historical_not_active_gate():
    content = (ROOT / "docs" / "STAGE_A_ACCEPTANCE.md").read_text(encoding="utf-8")

    assert "accepted historical engineering foundation" in content
    assert "Stage A is no longer the active implementation gate" in content
    assert "V0-003 media scan foundation" in content


def test_v003_release_readiness_records_local_validation_scope():
    content = (ROOT / "docs" / "V0_003_RELEASE_READINESS.md").read_text(
        encoding="utf-8"
    )

    assert "Status: completed locally, not pushed, not tagged." in content
    assert "b003a91 Record release readiness checkpoint" in content
    assert "gate reconciliation from Stage A-only" in content
    assert "deterministic `output/scan_report.md`" in content
    assert "downstream map/review invalidation" in content
    assert "pytest: 74 passed, 1 skipped" in content
    assert "run_checks.py: checks passed" in content


def test_v004_release_readiness_records_scope():
    content = (ROOT / "docs" / "V0_004_RELEASE_READINESS.md").read_text(
        encoding="utf-8"
    )

    assert "Status: completed locally, ready to push, not tagged." in content
    assert "6760831 Close V0-003 media scan foundation" in content
    assert "`ClipRecord` schema" in content
    assert "deterministic fixed-window segmentation" in content
    assert "canonical `.artist-portrait/data/clips.jsonl`" in content
    assert "pytest: 79 passed, 1 skipped" in content
    assert "run_checks.py: checks passed" in content
