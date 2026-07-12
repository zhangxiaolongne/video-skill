from artist_portrait_editor.models.final_export import FinalExportManifest
from artist_portrait_editor.models.preview import PreviewRenderedSegment
from artist_portrait_editor.models.second_cut_render import SecondCutRender
from artist_portrait_editor.second_cut_render import _comparisons


def test_second_cut_comparison_keeps_unproven_aesthetic_domains_unresolved() -> None:
    segment = {
        "segment_id": "second_cut_001", "candidate_id": "candidate_001",
        "role": "hook", "source_id": "source_001", "source_ref": "media/source.mp4",
        "source_in": 10.0, "source_out": 12.0, "timeline_start": 0.0,
        "timeline_end": 2.0, "ranking_score": 0.7, "ranking_confidence": 0.4,
        "original_audio_rendered": True,
    }
    first_segment = PreviewRenderedSegment(
        segment_id="segment_001", source_id="source_001", source_ref="media/source.mp4",
        source_in=0.0, source_out=2.0, timeline_start=0.0, timeline_end=2.0,
        media_role="both", video_transition="hard_cut", audio_transition="cut",
        video_rendered=True, original_audio_rendered=True,
        video_transition_rendered=True, audio_transition_rendered=True,
    )
    manifest = FinalExportManifest.model_validate({
        "export_id": "export_001", "project_id": "project_001", "timeline_id": "timeline_001",
        "timeline_ref": "output/timeline_draft.json", "timeline_fingerprint": "sha256:" + "1" * 64,
        "output_ref": "output/final_export.mp4", "output_content_hash": "sha256:" + "2" * 64,
        "expected_duration": 2.0, "duration": 2.0, "duration_delta_seconds": 0.0,
        "duration_tolerance_seconds": 0.35,
        "requested_profile": {"name": "review_720p", "width": 1280, "height": 720,
            "aspect_ratio": "16:9", "fit_mode": "contain", "fps": 24,
            "video_crf": 23, "audio_bitrate": "160k", "intent": "review"},
        "width": 1280, "height": 720, "actual_frame_rate": 24.0, "video_codec": "h264",
        "video_present": True, "audio_codec": "aac", "audio_present": True,
        "audio_expected": True, "render_profile": "review_720p",
        "rendered_segments": [first_segment.model_dump(mode="json")],
        "original_audio_included": True, "bgm_included": False, "ducking_applied": False,
    })
    parsed = SecondCutRender.model_fields["candidate_timeline"].annotation.__args__[0].model_validate(segment)
    comparisons = _comparisons("standard", [parsed], manifest, media_valid=True, no_bgm=True)
    by_domain = {item.domain: item for item in comparisons}
    assert len(comparisons) == 9
    assert by_domain["opening"].status == "improved"
    assert by_domain["technical_delivery"].status == "preserved"
    assert by_domain["text"].status == "unresolved"
    assert by_domain["composition"].status == "unresolved"
    assert by_domain["semantic_continuity"].status == "unresolved"
