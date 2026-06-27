import json

import pytest

from artist_portrait_editor.bgm import analyze_candidates, import_candidate
from artist_portrait_editor.bgm_recommendation import (
    BgmRecommendationError,
    import_bgm_recommendation_candidate,
    prepare_bgm_recommendation_handoff,
)
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

    context_path, request_path, handoff_path = prepare_bgm_recommendation_handoff(
        root=tmp_path,
        project_id="project-test",
    )
    context = json.loads(context_path.read_text(encoding="utf-8"))
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))

    assert request_path.exists()
    assert handoff["mode"] == "host_agent_local_model_or_third_party_tool"
    assert context["candidates"][0]["music_candidate_id"] == candidate.music_candidate_id
    assert "bgm_recommendation_set_json_schema" in handoff


def test_import_valid_bgm_recommendation_candidate(tmp_path):
    candidate = prepare_project(tmp_path)
    context_path, _request_path, _handoff_path = prepare_bgm_recommendation_handoff(
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


def test_import_rejects_unknown_candidate(tmp_path):
    prepare_project(tmp_path)
    context_path, _request_path, _handoff_path = prepare_bgm_recommendation_handoff(
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
