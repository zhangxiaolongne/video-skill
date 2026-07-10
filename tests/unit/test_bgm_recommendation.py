import json

import pytest

from artist_portrait_editor.bgm import analyze_candidates, import_candidate
from artist_portrait_editor.bgm_recommendation import (
    BgmRecommendationError,
    import_bgm_recommendation_candidate,
    prepare_bgm_recommendation_handoff,
    review_bgm_recommendation_fit,
    select_bgm_recommendation_for_fit,
)
from artist_portrait_editor.bgm import build_fit_plan
from artist_portrait_editor.models.source import RightsStatus
from tests.unit.test_bgm import make_audio, write_timeline


def make_recommendation(path, *, project_id, context_id, candidate_id, method="host_agent"):
    payload = {
        "schema_version": "1.0",
        "recommendation_set_id": "bgmrec_test",
        "project_id": project_id,
        "context_id": context_id,
        "method": method,
        "method_version": "test",
        "recommendations": [
            {
                "recommendation_id": "rec_001",
                "music_candidate_id": candidate_id,
                "rank": 1,
                "fit_rationale": "matches the requested mood and duration",
                "timing_rationale": "has stable energy for the timeline",
                "risk_notes": [],
                "evidence_refs": [".artist-portrait/data/bgm_analysis.json"],
                "confidence": 0.8,
            }
        ],
        "selection_performed": False,
        "automatic_selection_performed": False,
        "network_performed": False,
        "model_call_performed_by_cli": False,
        "warnings": [],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def prepare_project(root):
    make_audio(root / "media" / "one.wav", duration=1.0)
    _ledger, candidate = import_candidate(
        root=root,
        project_id="project-test",
        file_ref="media/one.wav",
        source_id=None,
        extract_in=0,
        extract_out=None,
        stream_index=0,
        rights_status=RightsStatus.owned,
        user_intent="recommend",
    )
    analyze_candidates(root=root, project_id="project-test")
    write_timeline(root, duration=1.0)
    return candidate


def test_prepare_bgm_recommendation_handoff(tmp_path):
    candidate = prepare_project(tmp_path)

    context_path, handoff_path = prepare_bgm_recommendation_handoff(
        root=tmp_path,
        project_id="project-test",
    )
    context = json.loads(context_path.read_text(encoding="utf-8"))
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))

    assert not (tmp_path / ".artist-portrait" / "data" / "bgm_recommendation_request.json").exists()
    assert handoff["mode"] == "host_agent_local_model_or_third_party_tool"
    assert context["candidates"][0]["music_candidate_id"] == candidate.music_candidate_id
    assert "bgm_recommendation_set_json_schema" in handoff


def test_import_valid_bgm_recommendation_candidate(tmp_path):
    candidate = prepare_project(tmp_path)
    context_path, _handoff_path = prepare_bgm_recommendation_handoff(
        root=tmp_path,
        project_id="project-test",
    )
    context = json.loads(context_path.read_text(encoding="utf-8"))
    candidate_path = tmp_path / "recommendation.json"
    make_recommendation(
        candidate_path,
        project_id="project-test",
        context_id=context["context_id"],
        candidate_id=candidate.music_candidate_id,
    )

    recommendation_path, review_path, validation = import_bgm_recommendation_candidate(
        root=tmp_path,
        project_id="project-test",
        candidate_path=candidate_path,
    )

    assert recommendation_path.exists()
    assert review_path.exists()
    assert validation.valid is True
    assert (tmp_path / ".artist-portrait" / "quarantine" / "bgm_recommendations").exists()


def test_select_bgm_recommendation_binds_explicit_selection_and_fit(tmp_path):
    candidate = prepare_project(tmp_path)
    context_path, _handoff_path = prepare_bgm_recommendation_handoff(
        root=tmp_path,
        project_id="project-test",
    )
    context = json.loads(context_path.read_text(encoding="utf-8"))
    candidate_path = tmp_path / "recommendation.json"
    make_recommendation(
        candidate_path,
        project_id="project-test",
        context_id=context["context_id"],
        candidate_id=candidate.music_candidate_id,
    )
    import_bgm_recommendation_candidate(
        root=tmp_path,
        project_id="project-test",
        candidate_path=candidate_path,
    )

    selection, item = select_bgm_recommendation_for_fit(
        root=tmp_path,
        project_id="project-test",
        recommendation_id="rec_001",
    )

    assert item.music_candidate_id == candidate.music_candidate_id
    assert selection.music_candidate_id == candidate.music_candidate_id
    assert selection.explicit_user_selection is True
    assert selection.automatic_selection_performed is False
    assert selection.selection_source == "recommendation_id"
    assert selection.bgm_fit_ref == ".artist-portrait/data/bgm_fit.json"
    assert (tmp_path / ".artist-portrait" / "data" / "bgm_recommendation_selection.json").exists()
    assert (tmp_path / "output" / "bgm_recommendation_selection_review.md").exists()


def test_select_bgm_recommendation_by_rank(tmp_path):
    candidate = prepare_project(tmp_path)
    context_path, _handoff_path = prepare_bgm_recommendation_handoff(
        root=tmp_path,
        project_id="project-test",
    )
    context = json.loads(context_path.read_text(encoding="utf-8"))
    candidate_path = tmp_path / "recommendation.json"
    make_recommendation(
        candidate_path,
        project_id="project-test",
        context_id=context["context_id"],
        candidate_id=candidate.music_candidate_id,
    )
    import_bgm_recommendation_candidate(
        root=tmp_path,
        project_id="project-test",
        candidate_path=candidate_path,
    )

    selection, _item = select_bgm_recommendation_for_fit(
        root=tmp_path,
        project_id="project-test",
        rank=1,
    )

    assert selection.selection_source == "rank"
    assert selection.selected_rank == 1


def test_select_bgm_recommendation_requires_explicit_target(tmp_path):
    prepare_project(tmp_path)
    prepare_bgm_recommendation_handoff(root=tmp_path, project_id="project-test")

    with pytest.raises(BgmRecommendationError, match="provide exactly one"):
        select_bgm_recommendation_for_fit(root=tmp_path, project_id="project-test")


def test_review_bgm_recommendation_fit_binds_selection_fit_and_timeline(tmp_path):
    candidate = prepare_project(tmp_path)
    context_path, _handoff_path = prepare_bgm_recommendation_handoff(
        root=tmp_path,
        project_id="project-test",
    )
    context = json.loads(context_path.read_text(encoding="utf-8"))
    candidate_path = tmp_path / "recommendation.json"
    make_recommendation(
        candidate_path,
        project_id="project-test",
        context_id=context["context_id"],
        candidate_id=candidate.music_candidate_id,
    )
    import_bgm_recommendation_candidate(
        root=tmp_path,
        project_id="project-test",
        candidate_path=candidate_path,
    )
    selection, _item = select_bgm_recommendation_for_fit(
        root=tmp_path,
        project_id="project-test",
        recommendation_id="rec_001",
    )
    fit, _timeline = build_fit_plan(
        root=tmp_path,
        project_id="project-test",
        candidate_id=selection.music_candidate_id,
    )

    review_json, review_md, report = review_bgm_recommendation_fit(
        root=tmp_path,
        project_id="project-test",
    )

    assert review_json.exists()
    assert review_md.exists()
    assert report.status == "warning"
    assert report.error_count == 0
    assert report.selection_id == selection.selection_id
    assert report.fit_id == fit.fit_id
    assert report.music_candidate_id == candidate.music_candidate_id
    assert report.preview_state == "missing"
    assert report.final_export_state == "missing"
    assert {issue.code for issue in report.issues} == {
        "preview_missing_after_fit",
        "final_export_missing_after_fit",
    }


def test_review_bgm_recommendation_fit_detects_mismatched_fit(tmp_path):
    first = prepare_project(tmp_path)
    make_audio(tmp_path / "media" / "two.wav", duration=1.5)
    _ledger, second = import_candidate(
        root=tmp_path,
        project_id="project-test",
        file_ref="media/two.wav",
        source_id=None,
        extract_in=0,
        extract_out=None,
        stream_index=0,
        rights_status=RightsStatus.owned,
        user_intent="alternate",
    )
    context_path, _handoff_path = prepare_bgm_recommendation_handoff(
        root=tmp_path,
        project_id="project-test",
    )
    context = json.loads(context_path.read_text(encoding="utf-8"))
    candidate_path = tmp_path / "recommendation.json"
    make_recommendation(
        candidate_path,
        project_id="project-test",
        context_id=context["context_id"],
        candidate_id=first.music_candidate_id,
    )
    import_bgm_recommendation_candidate(
        root=tmp_path,
        project_id="project-test",
        candidate_path=candidate_path,
    )
    select_bgm_recommendation_for_fit(
        root=tmp_path,
        project_id="project-test",
        recommendation_id="rec_001",
    )
    build_fit_plan(
        root=tmp_path,
        project_id="project-test",
        candidate_id=second.music_candidate_id,
    )

    _review_json, _review_md, report = review_bgm_recommendation_fit(
        root=tmp_path,
        project_id="project-test",
    )

    assert report.status == "failed"
    assert "fit_candidate_mismatch" in {issue.code for issue in report.issues}


def test_review_bgm_recommendation_fit_allows_manual_fit_without_selection(tmp_path):
    candidate = prepare_project(tmp_path)
    fit, _timeline = build_fit_plan(
        root=tmp_path,
        project_id="project-test",
        candidate_id=candidate.music_candidate_id,
    )

    _review_json, _review_md, report = review_bgm_recommendation_fit(
        root=tmp_path,
        project_id="project-test",
    )

    assert report.status == "warning"
    assert report.error_count == 0
    assert report.fit_id == fit.fit_id
    assert report.music_candidate_id == candidate.music_candidate_id
    assert "bgm_recommendation_selection_missing" in {
        issue.code for issue in report.issues
    }


def test_import_rejects_unknown_candidate(tmp_path):
    prepare_project(tmp_path)
    context_path, _handoff_path = prepare_bgm_recommendation_handoff(
        root=tmp_path,
        project_id="project-test",
    )
    context = json.loads(context_path.read_text(encoding="utf-8"))
    candidate_path = tmp_path / "recommendation.json"
    make_recommendation(
        candidate_path,
        project_id="project-test",
        context_id=context["context_id"],
        candidate_id="missing",
    )

    with pytest.raises(BgmRecommendationError) as error:
        import_bgm_recommendation_candidate(
            root=tmp_path,
            project_id="project-test",
            candidate_path=candidate_path,
        )

    assert error.value.code == "bgm_recommendation_validation_failed"
    validation = json.loads(
        (tmp_path / ".artist-portrait" / "data" / "bgm_recommendation_validation.json").read_text(
            encoding="utf-8"
        )
    )
    assert validation["valid"] is False
    assert validation["issues"][0]["code"] == "bgm_recommendation_unknown_candidate"
