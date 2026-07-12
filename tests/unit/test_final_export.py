import json
import shutil

import pytest

from artist_portrait_editor.bgm import build_fit_plan, import_candidate
from artist_portrait_editor.final_export import (
    FinalExportError,
    render_final_export,
    review_final_export,
)
from artist_portrait_editor.models.source import RightsStatus
from tests.unit.test_preview import make_audio, write_source_and_timeline


pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="final export tests require ffmpeg and ffprobe",
)


def test_render_final_export_without_bgm_uses_original_audio(tmp_path):
    write_source_and_timeline(tmp_path)

    export_path, manifest_path, validation_path, manifest, validation = render_final_export(
        root=tmp_path,
        project_id="project-test",
        profile_name="review_720p",
    )

    assert export_path.exists()
    assert manifest_path.exists()
    assert validation_path.exists()
    assert manifest.final_export is True
    assert manifest.automatic_music_selection is False
    assert manifest.network_performed is False
    assert manifest.model_call_performed is False
    assert manifest.render_profile == "review_720p"
    assert manifest.width == 1280
    assert manifest.height == 720
    assert manifest.bgm_included is False
    assert manifest.original_audio_included is True
    assert manifest.audio_present is True
    assert validation.valid is True
    assert validation.quality_status == "passed"


def test_render_final_export_delivery_profile_records_profile(tmp_path):
    write_source_and_timeline(tmp_path, duration=1.0)

    _, _, _, manifest, validation = render_final_export(
        root=tmp_path,
        project_id="project-test",
        profile_name="delivery_1080p",
        aspect_ratio="9:16",
    )

    assert manifest.render_profile == "delivery_1080p"
    assert manifest.requested_profile.width == 1080
    assert manifest.requested_profile.height == 1920
    assert manifest.requested_profile.aspect_ratio == "9:16"
    assert manifest.requested_profile.fps == 30
    assert (manifest.width, manifest.height) == (1080, 1920)
    assert validation.requested_profile == "delivery_1080p"
    assert validation.requested_width == 1080
    assert validation.requested_height == 1920
    assert validation.valid is True


def test_render_final_export_rejects_unknown_profile(tmp_path):
    write_source_and_timeline(tmp_path)

    with pytest.raises(FinalExportError, match="profile"):
        render_final_export(
            root=tmp_path,
            project_id="project-test",
            profile_name="social_4k",
        )


def test_render_final_export_with_bgm_fit_applies_manifest_binding(tmp_path):
    write_source_and_timeline(tmp_path, duration=1.5)
    make_audio(tmp_path / "media" / "bgm.wav", duration=0.5)
    _, candidate = import_candidate(
        root=tmp_path,
        project_id="project-test",
        file_ref="media/bgm.wav",
        source_id=None,
        extract_in=0,
        extract_out=None,
        stream_index=0,
        rights_status=RightsStatus.owned,
        user_intent="final export test BGM",
    )
    build_fit_plan(root=tmp_path, project_id="project-test", candidate_id=candidate.music_candidate_id)

    _, manifest_path, _, manifest, validation = render_final_export(
        root=tmp_path,
        project_id="project-test",
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest.bgm_included is True
    assert manifest.ducking_applied is True
    assert payload["bgm_fit_ref"] == ".artist-portrait/data/bgm_fit.json"
    assert validation.valid is True


def test_review_final_export_detects_stale_timeline(tmp_path):
    write_source_and_timeline(tmp_path)
    render_final_export(root=tmp_path, project_id="project-test")
    timeline_path = tmp_path / "output" / "timeline_draft.json"
    payload = json.loads(timeline_path.read_text(encoding="utf-8"))
    payload["warnings"] = ["changed after export"]
    timeline_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    report = review_final_export(tmp_path)

    assert report.valid is False
    assert [issue.code for issue in report.issues] == ["final_export_timeline_stale"]


def test_review_final_export_detects_duration_and_profile_drift(tmp_path):
    write_source_and_timeline(tmp_path)
    render_final_export(root=tmp_path, project_id="project-test", profile_name="review_720p")
    manifest_path = tmp_path / ".artist-portrait" / "data" / "final_export_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["expected_duration"] = 99
    payload["requested_profile"]["width"] = 1920
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    report = review_final_export(tmp_path)
    codes = {issue.code for issue in report.issues}

    assert report.quality_status == "failed"
    assert "final_export_duration_mismatch" in codes
    assert "final_export_width_mismatch" in codes
