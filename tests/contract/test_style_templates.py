from types import SimpleNamespace

from artist_portrait_editor.style_templates import AESTHETIC_STYLES, CONTENT_TEMPLATES, CREATIVE_TECHNIQUES, EMOTIONAL_ARCS, _compatibility


def _config(transcription="off"):
    return SimpleNamespace(
        creative_brief=SimpleNamespace(platform="douyin", aspect_ratio="16:9"),
        features=SimpleNamespace(transcription=SimpleNamespace(value=transcription)),
    )


def test_style_space_is_open_and_separates_four_creative_axes() -> None:
    assert len(CONTENT_TEMPLATES) >= 12
    assert len(AESTHETIC_STYLES) >= 12
    assert len(CREATIVE_TECHNIQUES) >= 8
    assert len(EMOTIONAL_ARCS) >= 8
    assert {item.form_family for item in CONTENT_TEMPLATES} >= {
        "performance", "spoken", "fiction", "process", "event",
        "promotional", "documentary", "cross_media", "fan_creation",
    }
    assert {item.style_id for item in AESTHETIC_STYLES} >= {
        "idol_gloss", "hot_blooded", "inspirational", "restrained_premium",
        "cinematic", "healing", "romantic", "melancholic", "dreamy",
        "epic", "nostalgic", "experimental_contrast",
    }


def test_content_forms_cover_master_cross_media_scope() -> None:
    source_types = {source_type for item in CONTENT_TEMPLATES for source_type in item.intended_source_types}
    assert source_types >= {
        "stage_performance", "live_performance", "interview", "music_video",
        "film_scene", "tv_scene", "theatre_scene", "musical_scene",
        "variety_show", "rehearsal", "behind_the_scenes", "public_event",
        "fan_edit",
    }
    assert any(item.template_id == "cross_media_portrait" for item in CONTENT_TEMPLATES)


def test_break_techniques_explain_form_feeling_meaning_risk_verification_and_fallback() -> None:
    breaking = [item for item in CREATIVE_TECHNIQUES if item.default_rule_mode == "break"]
    assert {item.technique_id for item in breaking} >= {
        "extreme_reversal", "sound_image_dislocation", "long_take_breathing",
        "intentional_rupture",
    }
    for item in breaking:
        assert item.form and item.expected_feeling and item.meaning_requirement
        assert item.principal_risk and item.playback_verification and item.fallback
    assert any(item.reversal_strength == "extreme" for item in EMOTIONAL_ARCS)


def test_compatibility_is_content_advice_not_aesthetic_selection() -> None:
    config = _config()
    stage = [_compatibility(item, {"other"}, set(), "舞台 stage performance", config) for item in CONTENT_TEMPLATES]
    event = [_compatibility(item, {"public_event"}, {"public_event"}, "festival event", config) for item in CONTENT_TEMPLATES]
    assert max(stage, key=lambda item: item.compatibility_score).template_id == "stage_performance_portrait"
    assert "event_montage" in {item.template_id for item in event if item.compatibility_score == max(x.compatibility_score for x in event)}
