from artist_portrait_editor.revision import (
    _find_semantic_conflicts,
    _parse_revision_semantics,
)


def test_compound_chinese_revision_note_preserves_all_requested_domains() -> None:
    clauses = _parse_revision_semantics(
        "整体更高级一点，节奏快点，少点字，别压人声，结尾更有力量",
        "custom",
        False,
    )
    assert {(item.domain, item.operation) for item in clauses} >= {
        ("style", "refine_premium"),
        ("rhythm", "accelerate"),
        ("text", "reduce_density"),
        ("source_audio", "protect_voice"),
        ("ending", "strengthen"),
    }
    assert [item.priority for item in clauses] == list(range(1, len(clauses) + 1))
    assert all(item.acceptance_observations for item in clauses)
    assert all(item.evidence_requirements for item in clauses)
    assert {domain for item in clauses for domain in item.coupled_domains} >= {
        "bgm", "text", "transition", "rhythm", "source_audio"
    }


def test_revision_semantics_detects_opposing_duration_and_rhythm_requests() -> None:
    clauses = _parse_revision_semantics(
        "短一点但也长一点，整体节奏快一点但关键时刻慢一点留白",
        "custom",
        False,
    )
    conflicts = _find_semantic_conflicts(clauses)
    assert len(conflicts) == 2
    assert all(item.status == "warning" for item in conflicts)
    assert all("Scope" in item.resolution for item in conflicts)


def test_unrecognized_revision_note_remains_custom_and_low_confidence() -> None:
    clauses = _parse_revision_semantics("做得更像我脑子里的感觉", "custom", False)
    assert len(clauses) == 1
    assert clauses[0].domain == "custom"
    assert clauses[0].confidence == 0.25
    assert clauses[0].application_status == "planned"
