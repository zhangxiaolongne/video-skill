import pytest
from pydantic import ValidationError

from artist_portrait_editor.creative_strategies import SPECS
from artist_portrait_editor.models.creative_strategy import CreativeStrategy, CreativeStrategyPackage, StrategyRange


def _strategy(strategy_id: str, candidate_id: str) -> CreativeStrategy:
    return CreativeStrategy(
        strategy_id=strategy_id, title=strategy_id, creative_intent="distinct intent",
        target_duration_seconds=10, planned_duration_seconds=10,
        ranges=[StrategyRange(candidate_id=candidate_id, source_id="source", source_in=0,
            source_out=10, planned_duration=10, role="hook", strategy_score=.5,
            evidence_confidence=0, selection_reason="evidence-limited selection",
            semantic_status="unavailable")],
        ordering_logic="explicit ordering", retained_qualities=["one quality"],
        sacrifices=["one sacrifice"], source_audio_policy="retain source audio",
        bgm_policy="no automatic BGM", text_density_policy="minimal",
        transition_policy="restrained", composition_policy="manual review",
        acceptance_checks=["opening", "middle", "audio", "composition", "ending"],
        strategy_confidence=0, status="degraded",
    )


def _package(signatures: int) -> dict:
    ids = list(SPECS)
    return {
        "package_id": "strategies_test", "project_id": "project", "target_duration_seconds": 10,
        "editorial_scores_ref": "scores.json", "editorial_scores_fingerprint": "sha256:" + "1" * 64,
        "structure_ref": "structure.json", "structure_fingerprint": "sha256:" + "2" * 64,
        "bgm_match_ref": "bgm.json", "bgm_match_fingerprint": "sha256:" + "3" * 64,
        "text_plan_ref": "text.json", "text_plan_fingerprint": "sha256:" + "4" * 64,
        "first_cut_review_ref": "review.json", "first_cut_review_fingerprint": "sha256:" + "5" * 64,
        "second_cut_ref": "second.json", "second_cut_fingerprint": "sha256:" + "6" * 64,
        "strategies": [_strategy(strategy_id, f"candidate_{index if index < signatures else 0}").model_dump(mode="json") for index, strategy_id in enumerate(ids)],
        "materially_distinct": True, "distinct_range_signatures": signatures,
        "transcript_coverage_ratio": 0, "status": "degraded",
    }


def test_four_strategy_specs_have_distinct_editorial_policies() -> None:
    assert set(SPECS) == {"emotional_arc", "high_energy", "narrative_clarity", "portrait_highlight"}
    assert len({tuple(sorted(spec["weights"].items())) for spec in SPECS.values()}) == 4
    assert len({spec["ordering"] for spec in SPECS.values()}) == 4
    assert {spec["text"] for spec in SPECS.values()} == {"minimal", "restrained", "moderate"}


def test_materially_distinct_package_requires_four_range_signatures() -> None:
    package = CreativeStrategyPackage.model_validate(_package(4))
    assert package.materially_distinct is True
    assert package.selected_strategy_id is None
    assert package.timeline_mutated is False
    assert package.media_rendered is False
    assert package.invented_semantics is False

    with pytest.raises(ValidationError, match="requires four range signatures"):
        CreativeStrategyPackage.model_validate(_package(3))
