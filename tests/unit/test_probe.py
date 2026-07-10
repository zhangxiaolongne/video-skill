import pytest

from artist_portrait_editor.media.probe import ProbeError, media_probe_from_ffprobe, parse_frame_rate
from artist_portrait_editor.models.source import MediaKind


def test_parse_frame_rate_fraction():
    assert parse_frame_rate("30000/1001") == pytest.approx(29.97002997)


def test_parse_frame_rate_handles_invalid_values():
    assert parse_frame_rate(None) is None
    assert parse_frame_rate("0/0") is None
    assert parse_frame_rate("not-a-rate") is None


def test_media_probe_from_video_stream_with_audio():
    media_kind, probe = media_probe_from_ffprobe(
        {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "duration": "2.5",
                    "width": 1920,
                    "height": 1080,
                    "avg_frame_rate": "25/1",
                },
                {"codec_type": "audio", "codec_name": "aac", "duration": "2.5"},
            ],
            "format": {"duration": "2.5"},
        }
    )

    assert media_kind == MediaKind.video
    assert probe.duration == 2.5
    assert probe.width == 1920
    assert probe.height == 1080
    assert probe.frame_rate == 25.0
    assert probe.video_codec == "h264"
    assert probe.audio_present is True
    assert probe.audio_codec == "aac"


def test_media_probe_from_audio_only_stream():
    media_kind, probe = media_probe_from_ffprobe(
        {
            "streams": [{"codec_type": "audio", "codec_name": "pcm_s16le"}],
            "format": {"duration": "1.25"},
        }
    )

    assert media_kind == MediaKind.audio
    assert probe.duration == 1.25
    assert probe.width is None
    assert probe.height is None
    assert probe.frame_rate is None
    assert probe.video_codec is None
    assert probe.audio_present is True
    assert probe.audio_codec == "pcm_s16le"


def test_media_probe_rejects_missing_media_streams():
    with pytest.raises(ProbeError, match="no audio or video"):
        media_probe_from_ffprobe({"streams": [], "format": {"duration": "1"}})


def test_media_probe_rejects_invalid_duration():
    with pytest.raises(ProbeError, match="duration"):
        media_probe_from_ffprobe(
            {
                "streams": [{"codec_type": "audio", "codec_name": "aac"}],
                "format": {"duration": "not-a-number"},
            }
        )
