import json
import shutil
import subprocess

import pytest

from artist_portrait_editor.bgm import build_fit_plan, import_candidate
from artist_portrait_editor.media.scanner import hash_file
from artist_portrait_editor.models.source import (
    Assertion,
    MediaKind,
    MediaProbe,
    RightsStatus,
    SourceRecord,
)
from artist_portrait_editor.models.timeline import (
    AudioTransition,
    MediaRole,
    MusicSlotStatus,
    TimelineDraft,
    TimelineMusicPlan,
    TimelineSegment,
    VideoTransition,
)
from artist_portrait_editor.preview import PreviewError, render_preview, review_preview


pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="preview tests require ffmpeg and ffprobe",
)


def make_video(path, duration=1.5, frequency=440):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"testsrc=size=64x64:rate=24:duration={duration}",
            "-f", "lavfi", "-i", f"sine=frequency={frequency}:duration={duration}",
            "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(path),
        ],
        check=True,
    )


def make_audio(path, duration=0.75, frequency=660):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"sine=frequency={frequency}:duration={duration}",
            str(path),
        ],
        check=True,
    )


def write_source_and_timeline(root, *, duration=1.5):
    media = root / "media" / "source.mp4"
    make_video(media, duration=duration)
    source = SourceRecord(
        source_id="source-1",
        locations=["media/source.mp4"],
        primary_location="media/source.mp4",
        content_hash=hash_file(media),
        media_kind=MediaKind.video,
        media_probe=MediaProbe(
            duration=duration,
            width=64,
            height=64,
            frame_rate=24,
            video_codec="h264",
            audio_present=True,
            audio_codec="aac",
        ),
        source_type=Assertion(value="other", method="test", level=4, confidence=1),
        rights_status=Assertion(
            value=RightsStatus.owned,
            method="test",
            level=4,
            confidence=1,
        ),
        provenance_confidence=1,
        provenance_method="test",
    )
    data = root / ".artist-portrait" / "data"
    data.mkdir(parents=True, exist_ok=True)
    (data / "sources.jsonl").write_text(source.model_dump_json() + "\n", encoding="utf-8")
    timeline = TimelineDraft(
        timeline_id="timeline_preview_test",
        project_id="project-test",
        proposal_set_id="proposal-set",
        proposal_id="proposal_safe",
        proposal_map_fingerprint="sha256:" + "1" * 64,
        input_fingerprint="sha256:" + "2" * 64,
        target_duration=duration,
        actual_duration=duration,
        segments=[
            TimelineSegment(
                segment_id="segment_001",
                timeline_start=0,
                timeline_end=duration,
                clip_id="clip-1",
                source_id="source-1",
                source_in=0,
                source_out=duration,
                track_id="V1",
                media_role=MediaRole.both,
                video_transition=VideoTransition.fade_in,
                audio_transition=AudioTransition.fade_in,
                reason="test",
                evidence=[{"type": "clip", "ref": "clip-1"}],
                creative_intent="test",
                confidence=1,
            )
        ],
        music_plan=TimelineMusicPlan(
            status=MusicSlotStatus.unresolved,
            input_mode="none_yet",
            future_input_modes=[
                "direct_audio",
                "video_audio_extract",
                "source_embedded_audio",
                "multiple_candidates",
                "none_yet",
            ],
        ),
        evidence=[{"type": "proposal", "ref": "proposal_safe"}],
    )
    output = root / "output"
    output.mkdir(exist_ok=True)
    (output / "timeline_draft.json").write_text(
        timeline.model_dump_json(indent=2),
        encoding="utf-8",
    )


def test_render_preview_without_bgm_uses_original_audio(tmp_path):
    write_source_and_timeline(tmp_path)

    preview_path, manifest_path, validation_path, manifest, validation = render_preview(
        root=tmp_path,
        project_id="project-test",
    )

    assert preview_path.exists()
    assert manifest_path.exists()
    assert validation_path.exists()
    assert manifest.bgm_included is False
    assert manifest.original_audio_included is True
    assert manifest.audio_expected is True
    assert manifest.video_present is True
    assert manifest.duration_delta_seconds == pytest.approx(0, abs=0.25)
    assert manifest.final_export is False
    assert manifest.network_performed is False
    assert validation.valid is True
    assert validation.quality_status == "passed"


def test_render_preview_records_bounded_controls(tmp_path):
    write_source_and_timeline(tmp_path)

    _, _, _, manifest, validation = render_preview(
        root=tmp_path,
        project_id="project-test",
        width=320,
        fps=10,
    )

    assert manifest.requested_width == 320
    assert manifest.requested_fps == 10
    assert manifest.width == 320
    assert validation.requested_width == 320
    assert validation.requested_fps == 10
    assert validation.valid is True


def test_render_preview_rejects_unsafe_controls(tmp_path):
    write_source_and_timeline(tmp_path)

    with pytest.raises(PreviewError, match="width"):
        render_preview(root=tmp_path, project_id="project-test", width=161, fps=12)
    with pytest.raises(PreviewError, match="fps"):
        render_preview(root=tmp_path, project_id="project-test", width=320, fps=60)


def test_render_preview_with_bgm_fit_applies_manifest_binding(tmp_path):
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
        user_intent="preview test BGM",
    )
    build_fit_plan(root=tmp_path, project_id="project-test", candidate_id=candidate.music_candidate_id)

    _, manifest_path, _, manifest, validation = render_preview(
        root=tmp_path,
        project_id="project-test",
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest.bgm_included is True
    assert manifest.ducking_applied is True
    assert payload["bgm_fit_ref"] == ".artist-portrait/data/bgm_fit.json"
    assert validation.valid is True


def test_review_preview_detects_stale_timeline(tmp_path):
    write_source_and_timeline(tmp_path)
    render_preview(root=tmp_path, project_id="project-test")
    timeline_path = tmp_path / "output" / "timeline_draft.json"
    payload = json.loads(timeline_path.read_text(encoding="utf-8"))
    payload["warnings"] = ["changed after preview"]
    timeline_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    report = review_preview(tmp_path)

    assert report.valid is False
    assert [issue.code for issue in report.issues] == ["preview_timeline_stale"]


def test_review_preview_detects_duration_and_profile_drift(tmp_path):
    write_source_and_timeline(tmp_path)
    render_preview(root=tmp_path, project_id="project-test", width=320, fps=10)
    manifest_path = tmp_path / ".artist-portrait" / "data" / "preview_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["expected_duration"] = 99
    payload["requested_width"] = 640
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    report = review_preview(tmp_path)
    codes = {issue.code for issue in report.issues}

    assert report.quality_status == "failed"
    assert "preview_duration_mismatch" in codes
    assert "preview_width_mismatch" in codes
