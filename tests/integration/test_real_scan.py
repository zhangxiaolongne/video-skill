import hashlib
import json
import math
import shutil
import subprocess
import wave
from pathlib import Path

import pytest

from artist_portrait_editor.cli import main
from artist_portrait_editor.media.scanner import read_sources_jsonl


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "stage_a"


def write_project(tmp_path: Path) -> Path:
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return project_path


def write_sine_wav(path: Path, *, seconds: float = 0.25, sample_rate: int = 8000) -> None:
    frames = int(seconds * sample_rate)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        for index in range(frames):
            sample = int(12000 * math.sin(2 * math.pi * 440 * index / sample_rate))
            handle.writeframesraw(sample.to_bytes(2, byteorder="little", signed=True))


def write_test_video(path: Path, *, seconds: float = 2.0) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", f"testsrc=size=64x64:rate=24:duration={seconds}",
            "-f", "lavfi", "-i", f"sine=frequency=220:duration={seconds}",
            "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", str(path),
        ],
        check=True,
    )


def write_proposal_candidate(root: Path) -> Path:
    context = json.loads(
        (root / ".artist-portrait" / "data" / "proposal_context.json").read_text(
            encoding="utf-8"
        )
    )
    clip_id = context["clips"][0]["clip_id"]
    analysis_id = context["analyses"][0]["analysis_id"]
    story_structures = {
        "proposal_safe": ["chronological evidence-led opening"],
        "proposal_advanced": ["contrast-driven cold open"],
        "proposal_risky": ["nonlinear reveal with delayed context"],
    }
    sound_structures = {
        "proposal_safe": ["BGM strategy: low-interference music under speech"],
        "proposal_advanced": ["Music supports pacing and transition emphasis"],
        "proposal_risky": ["Score builds to a drop followed by intentional silence"],
    }
    visual_motifs = {
        "proposal_safe": ["generated fixture visual rhythm"],
        "proposal_advanced": ["fast source-to-keyframe match cuts"],
        "proposal_risky": ["delayed face reveal and negative space"],
    }
    proposals = []
    for proposal_id in ("proposal_safe", "proposal_advanced", "proposal_risky"):
        proposals.append(
            {
                "proposal_id": proposal_id,
                "title": proposal_id.replace("_", " ").title(),
                "theme": context["creative_brief"]["theme"],
                "audience": context["creative_brief"]["audience"],
                "required_clip_ids": [clip_id],
                "fact_refs": [
                    {"type": "clip", "ref": clip_id},
                    {"type": "analysis", "ref": analysis_id},
                    {"type": "material_map", "ref": context["material_map_ref"]},
                ],
                "story_structure": story_structures[proposal_id],
                "sound_structure": sound_structures[proposal_id],
                "visual_motifs": visual_motifs[proposal_id],
                "risks": ["visual semantics not inferred"],
                "minimum_viable_timeline": ["fixture timeline"],
                "missing_material": [],
                "counter_proposal": f"What if {proposal_id} changes the opening?",
            }
        )
    candidate = root / "proposal_candidate.json"
    candidate.write_text(
        json.dumps(
            {
                "proposal_set_id": "proposal_set_real_acceptance",
                "project_id": context["project_id"],
                "map_fingerprint": context["material_map_fingerprint"],
                "method": "codex_host_agent_test_fixture",
                "method_version": "test",
                "proposals": proposals,
                "evidence": [{"type": "proposal_context", "ref": context["context_id"]}],
                "warnings": [],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return candidate


@pytest.mark.skipif(
    shutil.which("ffprobe") is None or shutil.which("ffmpeg") is None,
    reason="real scan requires ffprobe and ffmpeg",
)
def test_real_scan_writes_valid_source_jsonl_for_generated_wav(tmp_path, capsys):
    project_path = write_project(tmp_path)
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    write_sine_wav(media_dir / "tone.wav")

    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    code = main(["scan", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["sources"] == 1

    sources_path = tmp_path / ".artist-portrait" / "data" / "sources.jsonl"
    records = read_sources_jsonl(sources_path)
    assert len(records) == 1
    record = records[0]
    assert record.locations == ["media/tone.wav"]
    assert record.media_kind == "audio"
    assert record.media_probe.audio_present is True
    assert record.media_probe.width is None
    assert record.media_probe.height is None
    assert record.media_probe.video_codec is None
    assert record.media_probe.duration > 0


@pytest.mark.skipif(
    shutil.which("ffprobe") is None or shutil.which("ffmpeg") is None,
    reason="real acceptance profile test requires ffprobe and ffmpeg",
)
def test_real_media_acceptance_profiles_reach_delivery(tmp_path, capsys):
    project_path = write_project(tmp_path)
    project_path.write_text(
        project_path.read_text(encoding="utf-8")
        .replace("scene_detection: auto", "scene_detection: off")
        .replace("transcription: auto", "transcription: off")
        .replace("target_duration_seconds: 180", "target_duration_seconds: 2"),
        encoding="utf-8",
    )
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    write_test_video(media_dir / "source.mp4")
    (tmp_path / "sources.csv").write_text(
        "location,source_type,work,role,rights_status,forbidden_by_user,notes\n"
        "media/source.mp4,interview,Generated Video,Test Role,owned,false,"
        "real acceptance fixture\n",
        encoding="utf-8",
    )

    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    assert main(["scan", "--project", str(project_path), "--quiet"]) == 0
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0
    assert main(["keyframes", "--project", str(project_path), "--quiet"]) in (0, 1)
    assert main(["analyze", "--project", str(project_path), "--quiet"]) == 0
    assert main(["map", "--project", str(project_path), "--quiet"]) == 0
    assert main(["brief", "--project", str(project_path), "--quiet"]) == 0
    assert main(["evidence-map", "--project", str(project_path), "--json"]) == 1
    evidence = json.loads(capsys.readouterr().out)["evidence_map"]
    assert evidence["unit_count"] == 1
    assert evidence["audio_feature_coverage_ratio"] == 1.0
    assert evidence["keyframe_coverage_ratio"] == 1.0
    assert evidence["transcript_coverage_ratio"] == 0.0
    assert evidence["scene_detection_ratio"] == 0.0
    assert evidence["overall_status"] == "degraded"
    assert evidence["fabricated_semantics"] is False
    assert evidence["model_call_performed_by_cli"] is False
    assert evidence["network_performed"] is False
    assert "spoken_words" in evidence["global_unknowns"]
    assert "music_presence" in evidence["global_unknowns"]
    assert evidence["units"][0]["transcript"]["missing_reason"]
    assert evidence["units"][0]["audio"]["facts"]["method"] == (
        "ffmpeg_volumedetect_silencedetect_v1"
    )
    assert evidence["units"][0]["media_kind"] == "video"
    assert main(["editorial-score", "--project", str(project_path), "--json"]) == 1
    scores = json.loads(capsys.readouterr().out)["editorial_scores"]
    assert scores["candidate_count"] == 1
    assert scores["status"] == "degraded"
    assert scores["first_clip_position_bonus"] is False
    assert scores["last_clip_position_bonus"] is False
    assert scores["loudness_treated_as_emotion"] is False
    assert scores["missing_evidence_treated_as_zero_quality"] is False
    candidate_score = scores["candidates"][0]
    assert candidate_score["emotion"]["score"] == 0.5
    assert candidate_score["emotion"]["confidence"] == 0.0
    assert candidate_score["hook_rank"] == 1
    assert candidate_score["ending_rank"] == 1
    assert main(["structure-recommend", "--project", str(project_path), "--json"]) == 1
    structure = json.loads(capsys.readouterr().out)["structure_recommendation"]
    assert structure["recommended_option_id"] == "standard"
    assert structure["explicit_standard_duration_seconds"] == 2.0
    assert [item["option_id"] for item in structure["options"]] == [
        "short", "standard", "extended"
    ]
    assert all(
        item["estimated_duration_seconds"] <= item["target_duration_seconds"]
        for item in structure["options"]
    )
    assert structure["timeline_mutated"] is False
    assert structure["edit_points_applied"] is False
    assert structure["media_rendered"] is False
    assert main(["bgm-match", "--project", str(project_path), "--json"]) == 1
    bgm_match = json.loads(capsys.readouterr().out)["bgm_match"]
    assert bgm_match["input_state"] == "no_file_yet"
    assert bgm_match["candidate_count"] == 0
    assert bgm_match["status"] == "planning_only"
    assert bgm_match["automatic_music_selection"] is False
    assert bgm_match["selected_candidate_id"] is None
    assert bgm_match["fabricated_mood"] is False
    assert bgm_match["fabricated_bpm_or_beats"] is False
    assert main(["score", "--project", str(project_path), "--quiet"]) in (0, 1)
    assert main(["propose", "--project", str(project_path), "--json"]) == 1
    capsys.readouterr()

    candidate = write_proposal_candidate(tmp_path)
    assert (
        main(
            [
                "propose",
                "--project",
                str(project_path),
                "--agent-output",
                str(candidate),
                "--quiet",
            ]
        )
        in (0, 1)
    )
    assert (
        main(
            [
                "timeline",
                "--project",
                str(project_path),
                "--proposal",
                "proposal_safe",
                "--quiet",
            ]
        )
        in (0, 1)
    )
    assert main(["rhythm", "--project", str(project_path), "--quiet"]) in (0, 1)

    write_sine_wav(media_dir / "bgm.wav", seconds=1.0)
    assert (
        main(
            [
                "bgm", "import", "--project", str(project_path),
                "--file", "media/bgm.wav", "--rights-status", "owned", "--json",
            ]
        )
        in (0, 1)
    )
    candidate_id = json.loads(capsys.readouterr().out)["candidate"]["music_candidate_id"]
    assert main(["bgm", "analyze", "--project", str(project_path), "--json"]) in (0, 1)
    bgm_analysis = json.loads(capsys.readouterr().out)["analysis"]
    assert bgm_analysis["automatic_music_selection"] is False
    assert main(["bgm", "rhythm", "--project", str(project_path), "--json"]) in (0, 1)
    bgm_rhythm = json.loads(capsys.readouterr().out)["bgm_rhythm_intelligence"]
    assert bgm_rhythm["candidate_count"] == 1
    assert bgm_rhythm["automatic_music_selection"] is False
    assert bgm_rhythm["edit_points_moved"] is False
    assert bgm_rhythm["media_rendered"] is False
    assert (
        main(
            [
                "bgm", "fit", "--project", str(project_path),
                "--candidate", candidate_id, "--fit-mode", "loop", "--quiet",
            ]
        )
        in (0, 1)
    )
    assert main(["rhythm", "--project", str(project_path), "--quiet"]) in (0, 1)
    assert main(["bgm", "review", "--project", str(project_path), "--quiet"]) in (0, 1)
    assert main(["sound", "--project", str(project_path), "--quiet"]) in (0, 1)

    assert main(["acceptance", "--project", str(project_path), "--profile", "core", "--json"]) == 0
    core = json.loads(capsys.readouterr().out)
    assert core["status"] == "passed"

    assert (
        main(
            [
                "preview",
                "--project",
                str(project_path),
                "--width",
                "320",
                "--fps",
                "10",
                "--quiet",
            ]
        )
        in (0, 1)
    )
    assert main(["rhythm", "--project", str(project_path), "--qc", "--quiet"]) in (0, 1)
    assert main(["cut-review", "--project", str(project_path), "--quiet"]) in (0, 1)
    assert main(["acceptance", "--project", str(project_path), "--profile", "preview", "--json"]) == 0
    preview = json.loads(capsys.readouterr().out)
    assert preview["preview_ready"] is True
    preview_stages = {stage["stage_id"]: stage for stage in preview["acceptance"]["stages"]}
    assert preview_stages["rhythm_plan"]["status"] == "passed"
    assert preview_stages["rhythm_media_qc"]["status"] == "passed"

    assert (
        main(
            [
                "export",
                "--project",
                str(project_path),
                "--profile",
                "review_720p",
                "--quiet",
            ]
        )
        in (0, 1)
    )
    assert main(["rhythm", "--project", str(project_path), "--qc", "--quiet"]) in (0, 1)
    assert main(["cut-review", "--project", str(project_path), "--quiet"]) in (0, 1)
    assert main(["composition", "--project", str(project_path), "--samples", "4", "--json"]) == 0
    composition = json.loads(capsys.readouterr().out)["composition_evidence"]
    assert composition["sample_count"] == 4
    assert len(composition["samples"]) == 4
    assert composition["canvas"] == {
        "width": 1280,
        "height": 720,
        "aspect_ratio": "16:9",
        "fit_mode": "contain",
    }
    assert composition["model_call_performed_by_cli"] is False
    assert composition["network_performed"] is False
    assert (tmp_path / composition["contact_sheet_ref"]).is_file()
    review_candidate = {
        "review_id": "composition_review_test",
        "project_id": composition["project_id"],
        "composition_evidence_id": composition["composition_evidence_id"],
        "timeline_id": composition["timeline_id"],
        "timeline_fingerprint": composition["timeline_fingerprint"],
        "final_export_ref": composition["final_export_ref"],
        "final_export_hash": composition["final_export_hash"],
        "contact_sheet_ref": composition["contact_sheet_ref"],
        "contact_sheet_hash": composition["contact_sheet_hash"],
        "method": "codex_host_agent_fixture_review",
        "method_version": "test-v1",
        "aesthetic_status": "needs_reframe",
        "frame_reviews": [
            {
                "sample_id": item["sample_id"],
                "timestamp_seconds": item["timestamp_seconds"],
                "performer_prominence": 0.4,
                "branding_intrusion": 0.5,
                "dead_space": 0.3,
                "crop_safety": "conditional",
                "usability": "reframe_required",
                "observations": ["synthetic fixture composition review"],
                "confidence": 0.8,
            }
            for item in composition["samples"]
        ],
        "reframe_candidates": [
            {
                "candidate_id": "reframe_full_frame",
                "name": "Full-frame geometry fixture",
                "status": "candidate",
                "source_width": 1280,
                "source_height": 720,
                "crop_box": {"x": 0, "y": 0, "width": 1280, "height": 720},
                "target_aspect_ratio": "16:9",
                "applicable_sample_ids": [item["sample_id"] for item in composition["samples"]],
                "protected_region_policy": "Keep the generated test subject inside frame.",
                "benefits": ["Proves validated geometry and binding."],
                "risks": ["Does not improve synthetic composition."],
                "confidence": 0.8,
            },
            {
                "candidate_id": "reframe_single_sample",
                "name": "Single-sample preview fixture",
                "status": "conditional",
                "source_width": 1280,
                "source_height": 720,
                "crop_box": {"x": 320, "y": 180, "width": 640, "height": 360},
                "target_aspect_ratio": "16:9",
                "applicable_sample_ids": [composition["samples"][0]["sample_id"]],
                "protected_region_policy": "Keep the generated subject centered.",
                "benefits": ["Exercises a single-frame candidate preview."],
                "risks": ["Synthetic evidence only."],
                "confidence": 0.7,
            }
        ],
        "recommended_candidate_id": "reframe_full_frame",
        "conclusions": ["Synthetic media remains regression evidence only."],
        "warnings": ["fixture review is not real aesthetic acceptance"],
    }
    candidate_path = tmp_path / "composition_candidate.json"
    candidate_path.write_text(json.dumps(review_candidate, indent=2) + "\n", encoding="utf-8")
    assert main([
        "composition", "--project", str(project_path),
        "--agent-output", str(candidate_path), "--json",
    ]) == 1
    imported = json.loads(capsys.readouterr().out)
    assert imported["composition_review"]["crop_applied"] is False
    assert imported["composition_review"]["media_rendered"] is False
    assert imported["output"] == ".artist-portrait/data/composition_review.json"
    assert (tmp_path / imported["report"]).is_file()
    assert main([
        "composition", "--project", str(project_path),
        "--preview-candidate", "reframe_single_sample", "--json",
    ]) == 0
    reframe_preview = json.loads(capsys.readouterr().out)["reframe_preview"]
    assert reframe_preview["candidate_preview_rendered"] is True
    assert reframe_preview["crop_applied_to_final"] is False
    assert (tmp_path / reframe_preview["preview_ref"]).is_file()
    timeline_path = tmp_path / "output" / "timeline_draft.json"
    review_path = tmp_path / ".artist-portrait" / "data" / "composition_review.json"
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    selection = {
        "selection_id": "explicit_fixture_reframe",
        "project_id": composition["project_id"],
        "timeline_id": composition["timeline_id"],
        "timeline_fingerprint": "sha256:" + hashlib.sha256(timeline_path.read_bytes()).hexdigest(),
        "final_export_hash": composition["final_export_hash"],
        "composition_review_id": review_candidate["review_id"],
        "composition_review_fingerprint": "sha256:" + hashlib.sha256(review_path.read_bytes()).hexdigest(),
        "choices": [
            {
                "segment_id": item["segment_id"],
                "mode": "candidate",
                "candidate_id": "reframe_full_frame",
                "reason": "Explicit synthetic full-frame playback validation.",
            }
            for item in timeline["segments"]
        ],
        "approved_by": "host_agent",
        "approval_note": "Synthetic integration fixture only.",
    }
    selection_path = tmp_path / "reframe_selection.json"
    selection_path.write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")
    assert main([
        "reframe", "--project", str(project_path),
        "--selection", str(selection_path), "--json",
    ]) == 0
    reframe = json.loads(capsys.readouterr().out)["reframe_application"]
    assert reframe["explicit_selection_used"] is True
    assert reframe["automatic_candidate_selection"] is False
    assert reframe["canonical_timeline_mutated"] is False
    assert reframe["canonical_final_overwritten"] is False
    assert reframe["video_present"] is True
    assert reframe["audio_present"] is True
    assert (tmp_path / reframe["output_ref"]).is_file()
    assert main(["acceptance", "--project", str(project_path), "--profile", "delivery", "--json"]) == 0
    delivery = json.loads(capsys.readouterr().out)
    stages = {stage["stage_id"]: stage for stage in delivery["acceptance"]["stages"]}
    assert delivery["status"] == "passed"
    assert delivery["final_export_ready"] is True
    assert stages["bgm"]["status"] in {"passed", "warning"}
    assert stages["forbidden_capability_audit"]["status"] == "passed"
