from types import SimpleNamespace

from artist_portrait_editor.style_templates import TEMPLATES, _compatibility


def _config(*, platform: str = "douyin", aspect: str = "16:9", transcription: str = "off", music: bool = True):
    return SimpleNamespace(
        creative_brief=SimpleNamespace(platform=platform, aspect_ratio=aspect),
        features=SimpleNamespace(transcription=SimpleNamespace(value=transcription)),
        content_policy=SimpleNamespace(allow_music=music),
    )


def test_six_style_templates_have_complete_distinct_editing_policies() -> None:
    assert {item.template_id for item in TEMPLATES} == {
        "stage_portrait", "interview_portrait", "event_montage",
        "short_talking_head", "promotional_film", "documentary_portrait",
    }
    assert len(TEMPLATES) == 6
    assert all(len(item.structure) >= 3 for item in TEMPLATES)
    assert all(len(item.acceptance_checks) >= 6 for item in TEMPLATES)
    assert all(item.rhythm_policy and item.bgm_policy and item.transition_policy for item in TEMPLATES)
    assert {item.subtitle_density for item in TEMPLATES} >= {"minimal", "restrained", "moderate", "dense"}


def test_specialized_templates_beat_generic_templates_for_real_class_signals() -> None:
    config = _config()
    stage = [_compatibility(item, {"other"}, set(), "舞台 stage performance", config) for item in TEMPLATES]
    event = [_compatibility(item, {"public_event"}, {"public_event"}, "festival event", config) for item in TEMPLATES]

    assert max(stage, key=lambda item: item.compatibility_score).template_id == "stage_portrait"
    assert max(event, key=lambda item: item.compatibility_score).template_id == "event_montage"
    assert next(item for item in event if item.template_id == "event_montage").status == "compatible"


def test_interview_template_exposes_transcript_requirement() -> None:
    config = _config(transcription="off", music=False)
    template = next(item for item in TEMPLATES if item.template_id == "interview_portrait")
    result = _compatibility(template, {"other"}, set(), "高质量女演员采访 interview", config)

    assert result.template_id == "interview_portrait"
    assert result.status == "conditional"
    assert "transcript" in result.missing_evidence
