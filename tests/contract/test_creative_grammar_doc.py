import re
from pathlib import Path

from artist_portrait_editor.style_templates import AESTHETIC_STYLES, CONTENT_TEMPLATES, CREATIVE_TECHNIQUES, EMOTIONAL_ARCS


ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "CREATIVE_GRAMMAR.md"


def _ids_between(text: str, heading: str, next_heading: str) -> set[str]:
    section = text.split(heading, 1)[1].split(next_heading, 1)[0]
    return set(re.findall(r"^- `([a-z][a-z0-9_]*)`", section, re.MULTILINE))


def test_creative_grammar_document_matches_executable_seed_vocabulary() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert _ids_between(text, "## Content Forms", "## Aesthetic Styles") == {
        item.template_id for item in CONTENT_TEMPLATES
    }
    assert _ids_between(text, "## Aesthetic Styles", "## Creative Techniques") == {
        item.style_id for item in AESTHETIC_STYLES
    }
    assert _ids_between(text, "## Creative Techniques", "## Emotional Arcs") == {
        item.technique_id for item in CREATIVE_TECHNIQUES
    }
    assert _ids_between(text, "## Emotional Arcs", "## Rule Modes") == {
        item.arc_id for item in EMOTIONAL_ARCS
    }


def test_creative_grammar_is_a_required_planning_owner() -> None:
    required_path = "docs/CREATIVE_GRAMMAR.md"
    for path in (
        "AGENTS.md", "artist_portrait_editor_revision5_optimized.md",
        "docs/DEVELOPMENT_PROGRESS.md", "docs/current_progress.json",
    ):
        assert required_path in (ROOT / path).read_text(encoding="utf-8")


def test_creative_grammar_preserves_open_break_contract() -> None:
    text = DOC.read_text(encoding="utf-8")
    for token in (
        "not closed product limits", "follow", "bend", "break",
        "Form", "Feeling", "Meaning", "Risk", "Playback verification",
        "Fallback", "extreme reversal", "mixed",
    ):
        assert token in text
