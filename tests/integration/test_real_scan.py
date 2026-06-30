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
    assert main(["acceptance", "--project", str(project_path), "--profile", "delivery", "--json"]) == 0
    delivery = json.loads(capsys.readouterr().out)
    stages = {stage["stage_id"]: stage for stage in delivery["acceptance"]["stages"]}
    assert delivery["status"] == "passed"
    assert delivery["final_export_ready"] is True
    assert stages["bgm"]["status"] in {"passed", "warning"}
    assert stages["forbidden_capability_audit"]["status"] == "passed"
