from artist_portrait_editor.models.version_review import ReviewedVersion, VersionDomainAssessment
from artist_portrait_editor.version_review import DOMAINS, build_version_review


def _version(version_id: str, scores: dict[str, tuple[float | None, float]], level: str) -> ReviewedVersion:
    assessments = [
        VersionDomainAssessment(
            domain=domain,
            status="unavailable" if scores[domain][0] is None else "known",
            score=scores[domain][0],
            confidence=scores[domain][1],
            finding=f"{domain} finding",
            evidence_refs=[f"{version_id}:{domain}"],
        )
        for domain in DOMAINS
    ]
    return ReviewedVersion(
        version_id=version_id,
        version_kind="rendered_second_cut" if level == "rendered_media" else "revision_candidate",
        artifact_ref=f"output/{version_id}.json",
        artifact_fingerprint="sha256:" + ("a" if version_id == "a" else "b") * 64,
        evidence_level=level,
        duration_seconds=60,
        segment_count=8,
        media_valid=True if level == "rendered_media" else None,
        current=False,
        assessments=assessments,
        unresolved_domains=[item.domain for item in assessments if item.status == "unavailable"],
    )


def test_version_review_compares_seven_domains_without_selecting_overall_winner() -> None:
    a = _version("a", {domain: (.8, .8) for domain in DOMAINS}, "rendered_media")
    b = _version("b", {domain: (.5, .7) for domain in DOMAINS}, "rendered_media")
    review = build_version_review("project", [a, b])
    assert review.version_count == 2
    assert review.overall_winner_id is None
    assert review.selection_required is True
    assert review.automatic_version_selection is False
    assert len(review.goal_advantages) == 7
    assert all(item.leading_version_ids == ["a"] for item in review.goal_advantages)
    assert set(review.pairwise_comparisons[0].left_advantages) == set(DOMAINS)


def test_low_confidence_or_single_version_evidence_cannot_claim_goal_leadership() -> None:
    strong = {domain: (.8, .8) for domain in DOMAINS}
    weak = {domain: (.9, .3) for domain in DOMAINS}
    a = _version("a", strong, "rendered_media")
    b = _version("b", weak, "timeline_candidate")
    review = build_version_review("project", [a, b])
    assert all(item.status == "unavailable" for item in review.goal_advantages)
    assert all(not item.leading_version_ids for item in review.goal_advantages)
    assert review.pairwise_comparisons[0].comparable_domains == []
    assert set(review.pairwise_comparisons[0].unresolved_domains) == set(DOMAINS)
    assert review.status == "warning"


def test_missing_domain_evidence_remains_unresolved_instead_of_zero_scored() -> None:
    complete = {domain: (.7, .7) for domain in DOMAINS}
    partial = {domain: (.6, .7) for domain in DOMAINS}
    partial["bgm_conflict"] = (None, 0)
    partial["text_burden"] = (None, 0)
    review = build_version_review(
        "project",
        [_version("a", complete, "rendered_media"), _version("b", partial, "timeline_candidate")],
    )
    pair = review.pairwise_comparisons[0]
    assert {"bgm_conflict", "text_burden"} <= set(pair.unresolved_domains)
    assert next(item for item in review.goal_advantages if item.goal == "voice_first").status == "unavailable"
    assert next(item for item in review.goal_advantages if item.goal == "text_light").status == "unavailable"
