import json
import re
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
QUICK_VALIDATE = (
    Path.home()
    / ".codex"
    / "skills"
    / ".system"
    / "skill-creator"
    / "scripts"
    / "quick_validate.py"
)
PACKAGE_PREFLIGHT = ROOT / "scripts" / "skill_package_preflight.py"
SIMULATE_INSTALL = ROOT / "scripts" / "simulate_skill_install.py"


def test_skill_metadata_is_valid():
    result = subprocess.run(
        [sys.executable, str(QUICK_VALIDATE), str(ROOT)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Skill is valid" in result.stdout


def test_skill_frontmatter_and_boundaries():
    content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    assert match
    frontmatter = yaml.safe_load(match.group(1))

    assert frontmatter["name"] == "artist-portrait-editor"
    assert "Codex/ChatGPT host Agent" in frontmatter["description"]
    assert "without paid APIs, API keys, or network calls" in frontmatter["description"]
    assert "deterministic media ledgers" in frontmatter["description"]
    assert "evidence analysis" in frontmatter["description"]
    assert "analysis-led material map" in frontmatter["description"]
    assert "quarantined, validated, reviewed, and atomically promoted" in frontmatter["description"]
    assert "BGM fitting" in frontmatter["description"]
    assert "artist-portrait doctor --project ./project.yaml --json" in content
    assert "image generation or image editing" in content
    assert "output/scan_report.md" in content
    assert "output/clip_report.md" in content
    assert ".artist-portrait/data/proposal_context.json" in content
    assert "output/proposal_agent_handoff.json" in content
    assert "--agent-output" in content
    assert ".artist-portrait/data/proposal_validation.json" in content
    assert "output/proposal_review.md" in content
    assert "fake" in content
    assert ".artist-portrait/data/proposals.json" in content
    assert "proposal_provider_registry.json" not in content


def test_openai_yaml_matches_skill():
    payload = yaml.safe_load((ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8"))
    interface = payload["interface"]

    assert interface["display_name"] == "Artist Portrait Editor"
    assert interface["short_description"] == "Local artist portrait project prep"
    assert "$artist-portrait-editor" in interface["default_prompt"]


def test_skill_package_preflight_allows_only_known_name_warnings():
    result = subprocess.run(
        [sys.executable, str(PACKAGE_PREFLIGHT), str(ROOT), "--json"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = yaml.safe_load(result.stdout)
    assert payload["ok"] is True
    assert payload["error_count"] == 0
    assert {issue["code"] for issue in payload["issues"]} == {"folder_name_mismatch"}
    assert payload["package_policy"]["present"] is True
    assert payload["package_policy"]["canonical_install_dir"] == "artist-portrait-editor"
    assert payload["package_policy"]["distribution_repositories"] == ["video-skill"]
    package_policy = json.loads((ROOT / "skill-package.json").read_text(encoding="utf-8"))
    assert package_policy["excluded_distribution_paths"] == [
        "runs",
        "output",
        ".artist-portrait",
    ]


def test_canonical_install_simulation_has_no_package_warnings():
    result = subprocess.run(
        [sys.executable, str(SIMULATE_INSTALL), str(ROOT), "--json"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = yaml.safe_load(result.stdout)
    assert payload["ok"] is True
    assert payload["canonical_dir"] == "artist-portrait-editor"
    assert payload["quick_validate"]["returncode"] == 0
    assert payload["package_preflight"]["error_count"] == 0
    assert payload["package_preflight"]["warning_count"] == 0
    assert all(payload["excluded_paths_verified"].values())
