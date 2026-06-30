import json
import shutil
import subprocess

import pytest

import artist_portrait_editor.bgm as bgm_module
from artist_portrait_editor.bgm import (
    BgmError,
    analyze_candidates,
    build_bgm_rhythm_intelligence,
    build_fit_plan,
    import_candidate,
    review_bgm,
)
from artist_portrait_editor.rhythm import build_edit_guidance, build_rhythm_plan
from artist_portrait_editor.models.bgm import BgmBeatEvent, BgmBeatGrid, BgmInputMode
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


pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="BGM tests require ffmpeg and ffprobe",
)


def make_audio(path, duration=1.0, frequency=440):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"sine=frequency={frequency}:duration={duration}",
            str(path),
        ],
        check=True,
    )


def make_video(path, duration=1.0):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c=black:s=16x16:d={duration}",
            "-f", "lavfi", "-i", f"sine=frequency=330:duration={duration}",
            "-shortest", "-c:v", "libx264", "-c:a", "aac", str(path),
        ],
        check=True,
    )


def write_timeline(root, duration=2.5):
    timeline = TimelineDraft(
        timeline_id="timeline_test",
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
    path = root / "output" / "timeline_draft.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(timeline.model_dump_json(indent=2), encoding="utf-8")


def test_direct_audio_import_and_multi_candidate_ledger(tmp_path):
    make_audio(tmp_path / "media" / "one.wav", frequency=440)
    make_audio(tmp_path / "media" / "two.wav", frequency=660)

    ledger, first = import_candidate(
        root=tmp_path,
        project_id="project-test",
        file_ref="media/one.wav",
        source_id=None,
        extract_in=0,
        extract_out=None,
        stream_index=0,
        rights_status=RightsStatus.owned,
        user_intent="quiet portrait",
    )
    ledger, second = import_candidate(
        root=tmp_path,
        project_id="project-test",
        file_ref="media/two.wav",
        source_id=None,
        extract_in=0,
        extract_out=None,
        stream_index=0,
        rights_status=RightsStatus.licensed,
        user_intent="alternate ending",
    )

    assert first.input_mode == BgmInputMode.direct_audio
    assert first.mixed_audio is False
    assert first.bpm is None
    assert first.beat_analysis_status == "unavailable"
    assert len(ledger.candidates) == 2
    assert (tmp_path / first.cache_ref).exists()
    assert second.music_candidate_id != first.music_candidate_id


def test_video_audio_extract_preserves_mixed_audio_and_range(tmp_path):
    make_video(tmp_path / "media" / "music-source.mp4", duration=2)

    _, candidate = import_candidate(
        root=tmp_path,
        project_id="project-test",
        file_ref="media/music-source.mp4",
        source_id=None,
        extract_in=0.25,
        extract_out=1.25,
        stream_index=0,
        rights_status=RightsStatus.publicly_available,
        user_intent="use uploaded video audio",
    )

    assert candidate.input_mode == BgmInputMode.video_audio_extract
    assert candidate.mixed_audio is True
    assert candidate.extract_in == 0.25
    assert candidate.extract_out == 1.25
    assert candidate.duration == pytest.approx(1.0, abs=0.03)


def test_source_embedded_audio_import(tmp_path):
    make_video(tmp_path / "media" / "source.mp4")
    source = SourceRecord(
        source_id="source-1",
        locations=["media/source.mp4"],
        primary_location="media/source.mp4",
        content_hash="sha256:" + "3" * 64,
        media_kind=MediaKind.video,
        media_probe=MediaProbe(
            duration=1,
            width=16,
            height=16,
            frame_rate=25,
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
    data = tmp_path / ".artist-portrait" / "data"
    data.mkdir(parents=True)
    (data / "sources.jsonl").write_text(source.model_dump_json() + "\n", encoding="utf-8")

    _, candidate = import_candidate(
        root=tmp_path,
        project_id="project-test",
        file_ref=None,
        source_id="source-1",
        extract_in=0,
        extract_out=None,
        stream_index=0,
        rights_status=RightsStatus.permission_unknown,
        user_intent="reuse source music",
    )

    assert candidate.input_mode == BgmInputMode.source_embedded_audio
    assert candidate.source_ref == "source_id:source-1"
    assert candidate.rights_status == RightsStatus.owned


def test_fit_plan_loops_ducks_and_binds_timeline(tmp_path):
    make_audio(tmp_path / "media" / "short.wav", duration=1)
    _, candidate = import_candidate(
        root=tmp_path,
        project_id="project-test",
        file_ref="media/short.wav",
        source_id=None,
        extract_in=0,
        extract_out=None,
        stream_index=0,
        rights_status=RightsStatus.owned,
        user_intent="fit portrait",
    )
    write_timeline(tmp_path, duration=2.5)

    plan, timeline = build_fit_plan(
        root=tmp_path,
        project_id="project-test",
        candidate_id=candidate.music_candidate_id,
    )

    assert plan.fit_mode == "loop"
    assert len(plan.segments) == 3
    assert plan.segments[-1].timeline_end == 2.5
    assert plan.ducking_intervals[0].gain_db == -9
    assert plan.beat_alignment_status == "unavailable"
    assert timeline.music_plan.status == MusicSlotStatus.fitted
    assert timeline.music_plan.candidate_id == candidate.music_candidate_id
    assert timeline.music_plan.fitting_performed is True
    assert review_bgm(tmp_path, "project-test") == []

    timeline_path = tmp_path / "output" / "timeline_draft.json"
    payload = json.loads(timeline_path.read_text(encoding="utf-8"))
    payload["warnings"].append("changed")
    timeline_path.write_text(json.dumps(payload), encoding="utf-8")
    assert "BGM fit timeline fingerprint is stale" in review_bgm(
        tmp_path,
        "project-test",
    )


def test_bgm_analysis_records_energy_windows_and_candidate_binding(tmp_path):
    make_audio(tmp_path / "media" / "one.wav", duration=1.5)
    _, candidate = import_candidate(
        root=tmp_path,
        project_id="project-test",
        file_ref="media/one.wav",
        source_id=None,
        extract_in=0,
        extract_out=None,
        stream_index=0,
        rights_status=RightsStatus.owned,
        user_intent="analyze energy",
    )

    report = analyze_candidates(root=tmp_path, project_id="project-test", window_seconds=0.5)
    ledger_payload = json.loads(
        (tmp_path / ".artist-portrait" / "data" / "bgm_candidates.json").read_text(
            encoding="utf-8"
        )
    )

    assert report.analysis_engine == "local_pcm_energy_v1"
    assert report.network_performed is False
    assert report.model_call_performed is False
    assert report.automatic_music_selection is False
    assert len(report.candidates) == 1
    analysis = report.candidates[0]
    assert analysis.music_candidate_id == candidate.music_candidate_id
    assert analysis.window_count >= 2
    assert analysis.average_rms_dbfs < 0
    assert analysis.beat_analysis_status == "unavailable"
    assert analysis.bpm is None
    assert analysis.beat_grid_ref is None
    assert analysis.beat_count == 0
    assert report.beat_engine_capabilities
    assert ledger_payload["candidates"][0]["analysis_ref"] == ".artist-portrait/data/bgm_analysis.json"
    assert ledger_payload["candidates"][0]["beat_grid_ref"] is None


def test_bgm_fit_uses_existing_analysis_without_fabricating_beats(tmp_path):
    make_audio(tmp_path / "media" / "short.wav", duration=1)
    _, candidate = import_candidate(
        root=tmp_path,
        project_id="project-test",
        file_ref="media/short.wav",
        source_id=None,
        extract_in=0,
        extract_out=None,
        stream_index=0,
        rights_status=RightsStatus.owned,
        user_intent="fit analyzed portrait",
    )
    analyze_candidates(root=tmp_path, project_id="project-test", window_seconds=0.5)
    write_timeline(tmp_path, duration=2.5)

    plan, _timeline = build_fit_plan(
        root=tmp_path,
        project_id="project-test",
        candidate_id=candidate.music_candidate_id,
    )

    assert plan.analysis_ref == ".artist-portrait/data/bgm_analysis.json"
    assert plan.analysis_fingerprint is not None
    assert plan.energy_alignment_status == "analysis_used"
    assert plan.beat_alignment_status == "unavailable"
    assert plan.beat_evidence_status == "unavailable"


def test_validated_beat_grid_is_bound_to_analysis_candidate_and_fit(tmp_path, monkeypatch):
    make_audio(tmp_path / "media" / "beat.wav", duration=2)
    _, candidate = import_candidate(
        root=tmp_path,
        project_id="project-test",
        file_ref="media/beat.wav",
        source_id=None,
        extract_in=0,
        extract_out=None,
        stream_index=0,
        rights_status=RightsStatus.owned,
        user_intent="beat fit",
    )

    def fake_capabilities():
        from artist_portrait_editor.models.bgm import BgmBeatEngineCapability

        return [
            BgmBeatEngineCapability(
                engine="librosa",
                package_available=True,
                execution_supported=True,
                status="available",
            )
        ]

    def fake_run_beat_engine(**kwargs):
        return BgmBeatGrid(
            project_id="project-test",
            music_candidate_id=candidate.music_candidate_id,
            cache_ref=candidate.cache_ref,
            cache_fingerprint=bgm_module.hash_file(kwargs["cache_path"]),
            beat_engine="librosa",
            bpm=120.0,
            tempo_confidence=0.8,
            beat_count=8,
            beat_times=[
                BgmBeatEvent(index=index, time=round(index * 0.25, 3), confidence=0.8)
                for index in range(8)
            ],
        )

    monkeypatch.setattr(bgm_module, "detect_beat_engine_capabilities", fake_capabilities)
    monkeypatch.setattr(bgm_module, "run_beat_engine_if_available", fake_run_beat_engine)

    report = analyze_candidates(root=tmp_path, project_id="project-test", window_seconds=0.5)
    analysis = report.candidates[0]
    ledger_payload = json.loads(
        (tmp_path / ".artist-portrait" / "data" / "bgm_candidates.json").read_text(
            encoding="utf-8"
        )
    )

    assert analysis.beat_analysis_status == "completed"
    assert analysis.bpm == 120.0
    assert analysis.beat_grid_ref
    assert analysis.beat_grid_fingerprint
    assert analysis.beat_count == 8
    assert (tmp_path / analysis.beat_grid_ref).exists()
    assert ledger_payload["candidates"][0]["bpm"] == 120.0
    assert ledger_payload["candidates"][0]["beat_grid_ref"] == analysis.beat_grid_ref

    write_timeline(tmp_path, duration=2.0)
    plan, _timeline = build_fit_plan(
        root=tmp_path,
        project_id="project-test",
        candidate_id=candidate.music_candidate_id,
    )

    assert plan.beat_alignment_status == "completed"
    assert plan.beat_evidence_status == "bound"
    assert plan.beat_grid_ref == analysis.beat_grid_ref
    assert review_bgm(tmp_path, "project-test") == []

    beat_grid_path = tmp_path / analysis.beat_grid_ref
    payload = json.loads(beat_grid_path.read_text(encoding="utf-8"))
    payload["bpm"] = 90
    beat_grid_path.write_text(json.dumps(payload), encoding="utf-8")
    assert "BGM fit beat grid fingerprint is stale" in review_bgm(tmp_path, "project-test")


def test_bgm_rhythm_intelligence_scores_beat_quality_and_phrase_hints(tmp_path, monkeypatch):
    make_audio(tmp_path / "media" / "beat.wav", duration=2)
    _, candidate = import_candidate(
        root=tmp_path,
        project_id="project-test",
        file_ref="media/beat.wav",
        source_id=None,
        extract_in=0,
        extract_out=None,
        stream_index=0,
        rights_status=RightsStatus.owned,
        user_intent="beat fit",
    )

    def fake_capabilities():
        from artist_portrait_editor.models.bgm import BgmBeatEngineCapability

        return [
            BgmBeatEngineCapability(
                engine="librosa",
                package_available=True,
                execution_supported=True,
                status="available",
            )
        ]

    def fake_run_beat_engine(**kwargs):
        return BgmBeatGrid(
            project_id="project-test",
            music_candidate_id=candidate.music_candidate_id,
            cache_ref=candidate.cache_ref,
            cache_fingerprint=bgm_module.hash_file(kwargs["cache_path"]),
            beat_engine="librosa",
            bpm=120.0,
            tempo_confidence=0.8,
            beat_count=8,
            beat_times=[
                BgmBeatEvent(index=index, time=round(index * 0.25, 3), confidence=0.8)
                for index in range(8)
            ],
        )

    monkeypatch.setattr(bgm_module, "detect_beat_engine_capabilities", fake_capabilities)
    monkeypatch.setattr(bgm_module, "run_beat_engine_if_available", fake_run_beat_engine)
    analyze_candidates(root=tmp_path, project_id="project-test", window_seconds=0.5)

    json_path, md_path, handoff_path, report = build_bgm_rhythm_intelligence(
        root=tmp_path,
        project_id="project-test",
    )

    assert json_path == tmp_path / ".artist-portrait" / "data" / "bgm_rhythm_intelligence.json"
    assert md_path.exists()
    assert handoff_path.exists()
    assert report.status == "passed"
    assert report.usable_beat_candidate_count == 1
    assert report.fabricated_bpm_or_beats is False
    insight = report.candidates[0]
    assert insight.beat_quality_status == "strong"
    assert insight.beat_quality_score == pytest.approx(0.8, abs=0.001)
    assert insight.estimated_bar_seconds == pytest.approx(2.0)
    assert insight.estimated_phrase_seconds == pytest.approx(8.0)
    assert insight.source_risk_status == "low"


def test_rhythm_plan_consumes_bgm_rhythm_intelligence_without_mutation(tmp_path, monkeypatch):
    make_audio(tmp_path / "media" / "beat.wav", duration=2)
    _, candidate = import_candidate(
        root=tmp_path,
        project_id="project-test",
        file_ref="media/beat.wav",
        source_id=None,
        extract_in=0,
        extract_out=None,
        stream_index=0,
        rights_status=RightsStatus.owned,
        user_intent="beat fit",
    )

    def fake_capabilities():
        from artist_portrait_editor.models.bgm import BgmBeatEngineCapability

        return [
            BgmBeatEngineCapability(
                engine="librosa",
                package_available=True,
                execution_supported=True,
                status="available",
            )
        ]

    def fake_run_beat_engine(**kwargs):
        return BgmBeatGrid(
            project_id="project-test",
            music_candidate_id=candidate.music_candidate_id,
            cache_ref=candidate.cache_ref,
            cache_fingerprint=bgm_module.hash_file(kwargs["cache_path"]),
            beat_engine="librosa",
            bpm=120.0,
            tempo_confidence=0.8,
            beat_count=8,
            beat_times=[
                BgmBeatEvent(index=index, time=round(index * 0.25, 3), confidence=0.8)
                for index in range(8)
            ],
        )

    monkeypatch.setattr(bgm_module, "detect_beat_engine_capabilities", fake_capabilities)
    monkeypatch.setattr(bgm_module, "run_beat_engine_if_available", fake_run_beat_engine)
    analyze_candidates(root=tmp_path, project_id="project-test", window_seconds=0.5)
    build_bgm_rhythm_intelligence(root=tmp_path, project_id="project-test")
    write_timeline(tmp_path, duration=2.0)
    build_fit_plan(
        root=tmp_path,
        project_id="project-test",
        candidate_id=candidate.music_candidate_id,
        beat_alignment_requested=True,
    )

    _json_path, _md_path, _handoff_path, plan = build_rhythm_plan(
        root=tmp_path,
        project_id="project-test",
    )

    metrics = {metric.metric_id: metric for metric in plan.bgm_profile.metrics}
    assert plan.bgm_rhythm_intelligence_fingerprint is not None
    assert metrics["bgm_rhythm_status"].value == "passed"
    assert metrics["beat_quality_status"].value == "strong"
    assert metrics["estimated_phrase_seconds"].value == pytest.approx(8.0)
    assert plan.edit_points_moved is False
    assert plan.automatic_music_selection is False
    assert plan.media_rendered is False


def test_edit_guidance_turns_rhythm_evidence_into_manual_actions(tmp_path, monkeypatch):
    make_audio(tmp_path / "media" / "music.wav", duration=2.0)
    _ledger, candidate = import_candidate(
        root=tmp_path,
        project_id="project-test",
        file_ref="media/music.wav",
        source_id=None,
        extract_in=0,
        extract_out=None,
        stream_index=0,
        rights_status=RightsStatus.owned,
        user_intent="manual edit guidance",
    )

    def fake_capabilities():
        return [
            bgm_module.BgmBeatEngineCapability(
                engine="librosa",
                package_available=True,
                execution_supported=True,
                status="available",
                reason="fake engine",
            )
        ]

    def fake_run_beat_engine(**kwargs):
        return BgmBeatGrid(
            project_id="project-test",
            music_candidate_id=candidate.music_candidate_id,
            cache_ref=candidate.cache_ref,
            cache_fingerprint=bgm_module.hash_file(kwargs["cache_path"]),
            beat_engine="librosa",
            bpm=120.0,
            tempo_confidence=0.8,
            beat_count=8,
            beat_times=[
                BgmBeatEvent(index=index, time=round(index * 0.25, 3), confidence=0.8)
                for index in range(8)
            ],
        )

    monkeypatch.setattr(bgm_module, "detect_beat_engine_capabilities", fake_capabilities)
    monkeypatch.setattr(bgm_module, "run_beat_engine_if_available", fake_run_beat_engine)
    analyze_candidates(root=tmp_path, project_id="project-test", window_seconds=0.5)
    build_bgm_rhythm_intelligence(root=tmp_path, project_id="project-test")
    write_timeline(tmp_path, duration=2.0)
    build_fit_plan(root=tmp_path, project_id="project-test", candidate_id=candidate.music_candidate_id)
    build_rhythm_plan(root=tmp_path, project_id="project-test")

    json_path, md_path, handoff_path, guidance = build_edit_guidance(
        root=tmp_path,
        project_id="project-test",
    )

    assert json_path == tmp_path / ".artist-portrait" / "data" / "edit_guidance.json"
    assert md_path == tmp_path / "output" / "edit_guidance.md"
    assert handoff_path == tmp_path / "output" / "edit_guidance_handoff.json"
    assert guidance.action_count >= 10
    categories = {action.category for action in guidance.actions}
    assert {
        "subtitle",
        "transition",
        "pause",
        "ducking",
        "phrase",
        "cut_review",
        "ending",
        "qc_repair",
        "handoff",
    }.issubset(categories)
    assert guidance.bgm_rhythm_intelligence_fingerprint is not None
    assert guidance.manual_only is True
    assert all(action.manual_only is True for action in guidance.actions)
    assert all(action.edits_applied is False for action in guidance.actions)
    assert guidance.automatic_music_selection is False
    assert guidance.edit_points_moved is False
    assert guidance.timeline_mutated is False
    assert guidance.media_rendered is False
    assert guidance.model_call_performed_by_cli is False
    assert guidance.network_performed is False


def test_bgm_rhythm_intelligence_keeps_no_engine_and_mixed_audio_guidance(tmp_path):
    make_video(tmp_path / "media" / "music-source.mp4", duration=1.5)
    _, candidate = import_candidate(
        root=tmp_path,
        project_id="project-test",
        file_ref="media/music-source.mp4",
        source_id=None,
        extract_in=0,
        extract_out=None,
        stream_index=0,
        rights_status=RightsStatus.publicly_available,
        user_intent="analyze video audio",
    )
    analyze_candidates(root=tmp_path, project_id="project-test", window_seconds=0.5)

    _json_path, _md_path, _handoff_path, report = build_bgm_rhythm_intelligence(
        root=tmp_path,
        project_id="project-test",
    )

    assert candidate.mixed_audio is True
    assert report.status == "warning"
    assert report.usable_beat_candidate_count == 0
    insight = report.candidates[0]
    assert insight.beat_quality_status == "unavailable"
    assert insight.phrase_hint_status == "unavailable"
    assert insight.source_risk_status == "high"
    assert any("video or source mix" in warning for warning in insight.warnings)
    assert any("validated local beat engine" in action for action in insight.next_actions)


def test_bgm_fit_accepts_explicit_controls_without_moving_edit_points(tmp_path):
    make_audio(tmp_path / "media" / "long.wav", duration=3.0)
    _, candidate = import_candidate(
        root=tmp_path,
        project_id="project-test",
        file_ref="media/long.wav",
        source_id=None,
        extract_in=0,
        extract_out=None,
        stream_index=0,
        rights_status=RightsStatus.owned,
        user_intent="controlled fit",
    )
    write_timeline(tmp_path, duration=2.0)

    plan, timeline = build_fit_plan(
        root=tmp_path,
        project_id="project-test",
        candidate_id=candidate.music_candidate_id,
        requested_fit_mode="trim",
        fade_in_seconds=0.25,
        fade_out_seconds=0.75,
        target_gain_db=-6.0,
        ducking_gain_db=-12.0,
        ducking_enabled=True,
        beat_alignment_requested=True,
    )

    assert plan.fit_mode == "trim"
    assert plan.controls.control_policy == "explicit_cli_v1"
    assert plan.controls.requested_fit_mode == "trim"
    assert plan.controls.fade_in_seconds == 0.25
    assert plan.controls.fade_out_seconds == 0.75
    assert plan.controls.target_gain_db == -6.0
    assert plan.controls.ducking_gain_db == -12.0
    assert plan.controls.beat_alignment_requested is True
    assert plan.controls.edit_points_moved is False
    assert plan.controls.automatic_music_selection is False
    assert plan.ducking_intervals[0].gain_db == -12.0
    assert "Beat alignment was requested but no validated beat grid is available" in plan.warnings
    assert timeline.segments[0].timeline_start == 0


def test_bgm_fit_rejects_impossible_single_pass_control(tmp_path):
    make_audio(tmp_path / "media" / "short.wav", duration=1.0)
    _, candidate = import_candidate(
        root=tmp_path,
        project_id="project-test",
        file_ref="media/short.wav",
        source_id=None,
        extract_in=0,
        extract_out=None,
        stream_index=0,
        rights_status=RightsStatus.owned,
        user_intent="controlled fit",
    )
    write_timeline(tmp_path, duration=2.0)

    with pytest.raises(BgmError, match="requires candidate duration"):
        build_fit_plan(
            root=tmp_path,
            project_id="project-test",
            candidate_id=candidate.music_candidate_id,
            requested_fit_mode="single_pass",
        )


def test_video_bgm_analysis_keeps_contamination_warning(tmp_path):
    make_video(tmp_path / "media" / "music-source.mp4", duration=1.5)
    _, candidate = import_candidate(
        root=tmp_path,
        project_id="project-test",
        file_ref="media/music-source.mp4",
        source_id=None,
        extract_in=0,
        extract_out=None,
        stream_index=0,
        rights_status=RightsStatus.publicly_available,
        user_intent="analyze video audio",
    )

    report = analyze_candidates(root=tmp_path, project_id="project-test", window_seconds=0.5)

    assert candidate.mixed_audio is True
    assert "extracted from video" in " ".join(report.candidates[0].warnings)


def test_invalid_range_and_outside_project_are_rejected(tmp_path):
    make_audio(tmp_path / "media" / "one.wav")
    with pytest.raises(BgmError, match="invalid BGM extraction range"):
        import_candidate(
            root=tmp_path,
            project_id="project-test",
            file_ref="media/one.wav",
            source_id=None,
            extract_in=1,
            extract_out=0.5,
            stream_index=0,
            rights_status=RightsStatus.owned,
            user_intent="invalid",
        )
