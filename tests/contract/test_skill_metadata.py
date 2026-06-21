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
    assert "network search" in frontmatter["description"]
    assert "model calls" in frontmatter["description"]
    assert "artist-portrait doctor --project ./project.yaml --json" in content
    assert "image generation or image editing" in content


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
