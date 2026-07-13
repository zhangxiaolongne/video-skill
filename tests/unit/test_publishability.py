from types import SimpleNamespace

from artist_portrait_editor.models.version_review import (
    ReviewedVersion,
    VersionDomainAssessment,
)
from artist_portrait_editor.publishability import evaluate_version_publishability


FINGERPRINT = "sha256:" + "a" * 64
DOMAINS = (
    "hook",
    "emotional_arc",
    "information_density",
    "bgm_conflict",
    "text_burden",
    "ending_strength",
    "platform_fit",
)


def _version(kind="rendered_second_cut", *, evidence_level="rendered_media", media_valid=True):
    return ReviewedVersion(
        version_id="version_1",
        version_kind=kind,
        artifact_ref=".artist-portrait/data/version.json",
        artifact_fingerprint=FINGERPRINT,
        evidence_level=evidence_level,
        duration_seconds=60,
        segment_count=4,
        media_valid=media_valid,
        current=kind == "canonical_timeline",
        assessments=[
            VersionDomainAssessment(
                domain=domain,
                status="known",
                score=0.8,
                confidence=0.8,
                finding=f"{domain} has usable current evidence",
                evidence_refs=["evidence.json"],
            )
            for domain in DOMAINS
        ],
    )


def _second(publishability="publishable"):
    return SimpleNamespace(
        media_valid=True,
        comparisons=[],
        publishability=publishability,
        output_ref="output/second_cut.mp4",
    )


def test_plan_only_revision_is_unusable_even_when_assessments_are_positive():
    version = _version(
        "revision_candidate", evidence_level="plan_only", media_valid=None
    )

    result = evaluate_version_publishability(version, None, None, None, None)

    assert result.tier == "unusable"
    assert result.media_present is False
    assert result.ready_for_preview is False
    assert any(issue.disposition == "blocks_use" for issue in result.issues)


def test_technical_validity_does_not_promote_conditional_first_cut_to_publishable():
    version = _version(
        "canonical_timeline", evidence_level="timeline_candidate", media_valid=None
    )
    final = SimpleNamespace(
        valid=True,
        timeline_fingerprint=FINGERPRINT,
        export_ref="output/final_export.mp4",
        recovery_command="rerun export",
    )
    first = SimpleNamespace(
        domains=[], publishability="conditional", maturity_score=0.65
    )

    result = evaluate_version_publishability(version, final, first, None, None)

    assert result.technical_valid is True
    assert result.tier == "manual_refinement_required"
    assert result.ready_for_publish is False
    assert any(issue.disposition == "blocks_publish" for issue in result.issues)


def test_fully_supported_second_cut_can_reach_publishable_without_auto_selection():
    result = evaluate_version_publishability(
        _version(), None, None, _second(), None,
        second_media_current=True,
        second_record_current=True,
    )

    assert result.tier == "publishable"
    assert result.ready_for_preview is True
    assert result.ready_for_publish is True


def test_low_confidence_second_cut_is_previewable_not_publishable():
    version = _version()
    version.assessments[1].confidence = 0.3

    result = evaluate_version_publishability(version, None, None, _second(), None)

    assert result.tier == "previewable"
    assert result.ready_for_publish is False
    assert result.evidence_gap_count == 1


def test_nle_delivery_gap_is_not_applied_to_independent_second_cut():
    nle = SimpleNamespace(unresolved_source_count=1, roundtrip_verified=False)

    result = evaluate_version_publishability(_version(), None, None, _second(), nle)

    assert result.tier == "publishable"
    assert not any(issue.domain == "nle" for issue in result.issues)


def test_missing_or_changed_second_cut_media_is_unusable():
    result = evaluate_version_publishability(
        _version(), None, None, _second(), None, second_media_current=False
    )

    assert result.tier == "unusable"
    assert result.media_present is False
    assert any(issue.domain == "media" for issue in result.issues)


def test_stale_canonical_manifest_or_review_binding_is_unusable():
    version = _version(
        "canonical_timeline", evidence_level="timeline_candidate", media_valid=None
    )
    final = SimpleNamespace(
        valid=True,
        timeline_fingerprint=FINGERPRINT,
        export_ref="output/final_export.mp4",
        recovery_command="rerun export",
    )
    first = SimpleNamespace(domains=[], publishability="publishable", maturity_score=1.0)

    result = evaluate_version_publishability(
        version, final, first, None, None, canonical_record_current=False
    )

    assert result.tier == "unusable"
    assert any(
        issue.domain == "evidence" and issue.disposition == "blocks_use"
        for issue in result.issues
    )
