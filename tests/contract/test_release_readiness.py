from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_release_readiness_records_unpushed_candidate_scope():
    content = (ROOT / "docs" / "V0_002S_RELEASE_READINESS.md").read_text(
        encoding="utf-8"
    )

    assert "Status: completed locally, not pushed, not tagged." in content
    assert "origin/main..HEAD" in content
    assert "0fa9f73 Render minimal project risk report" in content
    assert "91adf47 Simulate canonical skill installation" in content
    assert "functional/package release candidate range" in content
    assert "V0-002s documentation and tests" in content


def test_release_readiness_records_required_checks_and_release_boundary():
    content = (ROOT / "docs" / "V0_002S_RELEASE_READINESS.md").read_text(
        encoding="utf-8"
    )

    assert ".venv/bin/python -m pytest" in content
    assert ".venv/bin/python run_checks.py" in content
    assert ".venv/bin/python scripts/skill_package_preflight.py . --json" in content
    assert ".venv/bin/python scripts/simulate_skill_install.py . --json" in content
    assert "git diff --check" in content
    assert "folder_name_mismatch warning is allowed" in content
    assert "Do not push or tag automatically" in content
    assert "user confirmation" in content


def test_release_readiness_carries_future_constraints():
    content = (ROOT / "docs" / "V0_002S_RELEASE_READINESS.md").read_text(
        encoding="utf-8"
    )

    assert "BGM as a non-negotiable future editing constraint" in content
    assert "third-party tool reuse policy for later gates" in content
    assert "does not call models" in content
    assert "network search" in content
    assert "image generation/editing" in content
