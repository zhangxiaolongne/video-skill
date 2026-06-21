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
