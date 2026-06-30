import json
import shutil
import subprocess
from pathlib import Path

import pytest

import artist_portrait_editor.cli as cli
import artist_portrait_editor.workspace as workspace
from artist_portrait_editor.cli import main
from artist_portrait_editor.media.transcription import TranscribedSegment, TranscribedWord
from artist_portrait_editor.media.scanner import ScanResult, read_sources_jsonl
from artist_portrait_editor.models.source import (
    Assertion,
    MediaKind,
    MediaProbe,
    RightsStatus,
    SourceRecord,
)
from artist_portrait_editor.models.state import Capabilities


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "stage_a"


def write_clean_source_ledger(root: Path) -> None:
    source = SourceRecord(
        source_id="clean-source-1",
        locations=["media/clean.mp4"],
        primary_location="media/clean.mp4",
        content_hash="sha256:" + "1" * 64,
        media_kind=MediaKind.video,
        media_probe=MediaProbe(
            duration=2.0,
            width=16,
            height=16,
            frame_rate=24.0,
            video_codec="h264",
            audio_present=False,
            audio_codec=None,
        ),
        source_type=Assertion(
            value="interview",
            method="test",
            level=4,
            confidence=1.0,
        ),
        rights_status=Assertion(
            value=RightsStatus.owned,
            method="test",
            level=4,
            confidence=1.0,
        ),
        provenance_confidence=1.0,
        provenance_method="test",
    )
    data_dir = root / ".artist-portrait" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "sources.jsonl").write_text(
        source.model_dump_json() + "\n",
        encoding="utf-8",
    )


def write_audio_source_ledger(root: Path) -> None:
    source = SourceRecord(
        source_id="audio-source-1",
        locations=["media/audio.wav"],
        primary_location="media/audio.wav",
        content_hash="sha256:" + "2" * 64,
        media_kind=MediaKind.audio,
        media_probe=MediaProbe(
            duration=2.0,
            width=None,
            height=None,
            frame_rate=None,
            video_codec=None,
            audio_present=True,
            audio_codec="pcm_s16le",
        ),
        source_type=Assertion(
            value="interview",
            method="test",
            level=4,
            confidence=1.0,
        ),
        rights_status=Assertion(
            value=RightsStatus.owned,
            method="test",
            level=4,
            confidence=1.0,
        ),
        provenance_confidence=1.0,
        provenance_method="test",
    )
    data_dir = root / ".artist-portrait" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "sources.jsonl").write_text(
        source.model_dump_json() + "\n",
        encoding="utf-8",
    )


def project_fixture_with_scene_detection(value: str) -> str:
    return (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8").replace(
        "scene_detection: auto",
        f"scene_detection: {value}",
    )


def project_fixture_with_transcription(value: str) -> str:
    return (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8").replace(
        "transcription: auto",
        f"transcription: {value}",
    )


def project_fixture_with_remote_text_model_allowed() -> str:
    return (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8").replace(
        "allow_remote_text_model: false",
        "allow_remote_text_model: true",
    )


def test_release_check_writes_hardening_report_without_publication(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(project_fixture_with_scene_detection("off"), encoding="utf-8")
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    capsys.readouterr()

    assert main(["release-check", "--project", str(project_path), "--json"]) in (0, 1)
    payload = json.loads(capsys.readouterr().out)
    report = payload["release_hardening_report"]

    assert payload["output"] == ".artist-portrait/data/release_hardening_report.json"
    assert payload["report"] == "output/release_hardening_report.md"
    assert report["capability_gate"] == "V0-041"
    assert report["status"] in {"warning", "ready_for_local_release"}
    assert report["failed_count"] == 0
    assert report["commit_allowed"] is False
    assert report["push_allowed"] is False
    assert report["tag_allowed"] is False
    assert report["network_performed"] is False
    assert report["model_call_performed_by_cli"] is False
    checks = {check["check_id"]: check for check in report["checks"]}
    assert checks["gate_doc_consistency"]["status"] == "passed"
    assert checks["schema_coverage"]["status"] == "passed"
    assert checks["forbidden_source_surface"]["status"] == "passed"


def write_proposals_from_context(root: Path, *, unknown_clip: bool = False, bgm: bool = True) -> None:
    context = json.loads(
        (root / ".artist-portrait" / "data" / "proposal_context.json").read_text(
            encoding="utf-8"
        )
    )
    clip_id = context["clips"][0]["clip_id"]
    analysis_id = context["analyses"][0]["analysis_id"]
    required_clip = "clip_missing" if unknown_clip else clip_id
    story_structures = {
        "proposal_safe": ["chronological evidence-led opening", "measured conclusion"],
        "proposal_advanced": ["contrast-driven cold open", "parallel development"],
        "proposal_risky": ["disruptive question opening", "nonlinear reveal"],
    }
    sound_structures = {
        "proposal_safe": [
            "BGM strategy: low-interference music under speech with voice ducking"
        ],
        "proposal_advanced": [
            "Music supports pacing and transitions with beat-aligned cuts"
        ],
        "proposal_risky": [
            "Score drives emotional energy through a drop followed by silence"
        ],
    }
    visual_motifs = {
        "proposal_safe": ["chronological portrait details"],
        "proposal_advanced": ["cross-media match cuts"],
        "proposal_risky": ["delayed reveal and negative space"],
    }
    counter_proposals = {
        "proposal_safe": "What if the opening avoids a direct face shot?",
        "proposal_advanced": "What if chronology is replaced by thematic contrast?",
        "proposal_risky": "What if the music climax cuts to intentional silence?",
    }
    proposals = []
    for proposal_id in ("proposal_safe", "proposal_advanced", "proposal_risky"):
        proposals.append(
            {
                "proposal_id": proposal_id,
                "title": proposal_id.replace("_", " ").title(),
                "theme": context["creative_brief"]["theme"],
                "audience": context["creative_brief"]["audience"],
                "required_clip_ids": [required_clip],
                "fact_refs": [
                    {"type": "clip", "ref": clip_id},
                    {"type": "analysis", "ref": analysis_id},
                    {"type": "material_map", "ref": context["material_map_ref"]},
                ],
                "story_structure": story_structures[proposal_id],
                "sound_structure": (
                    sound_structures[proposal_id]
                    if bgm
                    else ["voice-first sound plan"]
                ),
                "visual_motifs": visual_motifs[proposal_id],
                "risks": ["visual semantics not inferred"],
                "minimum_viable_timeline": ["timeline generation not open"],
                "missing_material": [],
                "counter_proposal": counter_proposals[proposal_id],
            }
        )
    payload = {
        "proposal_set_id": "proposal_set_test",
        "project_id": context["project_id"],
        "map_fingerprint": context["material_map_fingerprint"],
        "method": "codex_host_agent_test_fixture",
        "method_version": "test",
        "proposals": proposals,
        "evidence": [{"type": "proposal_context", "ref": context["context_id"]}],
        "warnings": [],
    }
    (root / ".artist-portrait" / "data" / "proposals.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_blocked_proposal_chain(root: Path, capsys) -> Path:
    project_path = root / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(root)
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0
    assert main(["analyze", "--project", str(project_path), "--quiet"]) == 0
    assert main(["map", "--project", str(project_path), "--quiet"]) == 0
    assert main(["propose", "--project", str(project_path), "--json"]) == 1
    capsys.readouterr()
    return project_path


def build_valid_proposal_project(root: Path, capsys, *, allow_music: bool = True) -> Path:
    project_path = build_blocked_proposal_chain(root, capsys)
    if not allow_music:
        project_path.write_text(
            project_path.read_text(encoding="utf-8").replace(
                "allow_music: true",
                "allow_music: false",
            ),
            encoding="utf-8",
        )
    write_proposals_from_context(root, bgm=allow_music)
    canonical = root / ".artist-portrait" / "data" / "proposals.json"
    if not allow_music:
        payload = json.loads(canonical.read_text(encoding="utf-8"))
        for proposal in payload["proposals"]:
            proposal["sound_structure"] = [
                "no added music; preserve original voice and intentional silence "
                f"for {proposal['proposal_id']}"
            ]
        canonical.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    candidate = root / "proposal_candidate.json"
    candidate.write_bytes(canonical.read_bytes())
    canonical.unlink()
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
        == 0
    )
    capsys.readouterr()
    return project_path


def test_validate_valid_project(capsys):
    code = main(["validate", "--project", str(FIXTURES / "valid_project.yaml")])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out.strip() == "valid"


def test_validate_invalid_project(capsys):
    code = main(["validate", "--project", str(FIXTURES / "invalid_enum.yaml")])
    captured = capsys.readouterr()
    assert code == 3
    assert "features.transcription" in captured.err


def test_init_creates_only_stage_a_artifacts(tmp_path):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )

    code = main(["init", "--project", str(project_path)])

    assert code in (0, 1)
    assert (tmp_path / ".artist-portrait" / "state.json").exists()
    assert (tmp_path / ".artist-portrait" / "cache").is_dir()
    assert (tmp_path / ".artist-portrait" / "data").is_dir()
    assert (tmp_path / ".artist-portrait" / "runs").is_dir()
    assert (tmp_path / "output" / "run_report.md").exists()

    forbidden = [
        ".artist-portrait/data/sources.jsonl",
        ".artist-portrait/data/clips.jsonl",
        ".artist-portrait/data/transcripts.jsonl",
        ".artist-portrait/data/relations.jsonl",
        ".artist-portrait/data/proposal_context.json",
        ".artist-portrait/data/text_model_gate.json",
        ".artist-portrait/data/proposals.json",
        "output/scan_report.md",
        "output/clip_report.md",
        "output/material_map.md",
        "output/proposals.md",
        "output/timeline_draft.json",
        "output/risk_report.md",
    ]
    for relative in forbidden:
        assert not (tmp_path / relative).exists()


def test_init_dry_run_does_not_write_project_files(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )

    code = main(["init", "--project", str(project_path), "--dry-run", "--json"])
    captured = capsys.readouterr()

    assert code in (0, 1)
    payload = json.loads(captured.out)
    assert payload["project_id"] == "chen_haoyu_portrait_001"
    assert not (tmp_path / ".artist-portrait").exists()
    assert not (tmp_path / "output").exists()


def test_status_before_init_reports_new(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["overall_status"] == "new"
    assert payload["state"] is None


def test_status_after_init_json(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["project_id"] == "chen_haoyu_portrait_001"
    assert payload["steps"]["scan"]["status"] == "pending"
    assert payload["artifacts"]["state"]["exists"] is True
    assert payload["artifacts"]["run_report"]["exists"] is True
    assert payload["artifacts"]["sources"]["exists"] is False
    assert payload["summaries"]["sources"]["exists"] is False


def test_status_after_init_human_panel(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)

    code = main(["status", "--project", str(project_path)])
    captured = capsys.readouterr()

    assert code == 0
    assert "project: chen_haoyu_portrait_001" in captured.out
    assert "overall_status:" in captured.out
    assert "sources: missing" in captured.out
    assert "scan: pending" in captured.out


def test_doctor_before_init_recommends_init(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 1
    payload = json.loads(captured.out)
    assert payload["initialized"] is False
    assert payload["issue_count"] == 1
    assert payload["issues"][0]["code"] == "workspace_not_initialized"
    assert "artist-portrait init --project" in payload["issues"][0]["next_action"]


def test_doctor_after_init_reports_no_issues(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)

    code = main(["doctor", "--project", str(project_path)])
    captured = capsys.readouterr()

    assert code == 0
    assert "issues: 0" in captured.out
    assert "next: none" in captured.out


def test_repeated_init_keeps_stage_a_boundary(tmp_path):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)

    forbidden = [
        ".artist-portrait/data/sources.jsonl",
        ".artist-portrait/data/clips.jsonl",
        ".artist-portrait/data/transcripts.jsonl",
        ".artist-portrait/data/relations.jsonl",
        ".artist-portrait/data/proposals.json",
        "output/scan_report.md",
        "output/clip_report.md",
        "output/material_map.md",
        "output/proposals.md",
        "output/timeline_draft.json",
        "output/risk_report.md",
    ]
    for relative in forbidden:
        assert not (tmp_path / relative).exists()


def test_scan_requires_init_first(tmp_path, monkeypatch, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        cli,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True),
    )

    code = main(["scan", "--project", str(project_path)])
    captured = capsys.readouterr()

    assert code == 7
    assert "requires init" in captured.err


def test_scan_missing_media_dependencies_returns_4(tmp_path, monkeypatch, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    monkeypatch.setattr(
        cli,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=False, ffprobe=False),
    )

    code = main(["scan", "--project", str(project_path)])
    captured = capsys.readouterr()

    assert code == 4
    assert "missing required media dependencies" in captured.err


def test_scan_writes_sources_and_updates_state(tmp_path, monkeypatch, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    monkeypatch.setattr(
        cli,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True),
    )

    def fake_scan_project_sources(*, root, config, previous_records=None):
        return ScanResult(
            records=[
                SourceRecord(
                    source_id="source-1",
                    locations=["media/a.mp4"],
                    primary_location="media/a.mp4",
                    content_hash="sha256:" + "a" * 64,
                    media_kind=MediaKind.video,
                    media_probe=MediaProbe(
                        duration=1.0,
                        width=16,
                        height=16,
                        frame_rate=24.0,
                        video_codec="h264",
                        audio_present=False,
                        audio_codec=None,
                    ),
                    source_type=Assertion(
                        value="other",
                        method="test",
                        level=1,
                        confidence=0.2,
                    ),
                    rights_status=Assertion(
                        value=RightsStatus.permission_unknown,
                        method="test",
                        level=1,
                        confidence=0.0,
                    ),
                    provenance_confidence=0.0,
                    provenance_method="test",
                )
            ],
            warnings=[],
            errors=[],
        )

    monkeypatch.setattr(workspace, "scan_project_sources", fake_scan_project_sources)

    code = main(["scan", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["sources"] == 1
    assert payload["output_refs"] == [
        ".artist-portrait/data/sources.jsonl",
        "output/scan_report.md",
    ]
    assert payload["invalidated_steps"] == []
    sources_path = tmp_path / ".artist-portrait" / "data" / "sources.jsonl"
    assert sources_path.exists()
    assert len(sources_path.read_text(encoding="utf-8").splitlines()) == 1
    scan_report = (tmp_path / "output" / "scan_report.md").read_text(encoding="utf-8")
    assert "# Scan Report" in scan_report
    assert "ffprobe-derived media facts only" in scan_report
    assert "No transcription, visual analysis" in scan_report
    assert "- Source count: `1`" in scan_report
    assert "- Content hash: `sha256:" in scan_report

    state_payload = json.loads(
        (tmp_path / ".artist-portrait" / "state.json").read_text(encoding="utf-8")
    )
    assert state_payload["steps"]["scan"]["status"] == "completed"
    assert state_payload["steps"]["scan"]["output_refs"] == [
        ".artist-portrait/data/sources.jsonl",
        "output/scan_report.md",
    ]
    assert state_payload["steps"]["segment"]["status"] == "pending"
    assert state_payload["steps"]["map"]["status"] == "pending"
    assert not (tmp_path / "output" / "material_map.md").exists()
    run_report = (tmp_path / "output" / "run_report.md").read_text(encoding="utf-8")
    assert "- `scan`: `completed`" in run_report
    assert "- `map`: `pending`" in run_report


def test_map_requires_scan_first(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)

    code = main(["map", "--project", str(project_path)])
    captured = capsys.readouterr()

    assert code == 7
    assert "map requires scan" in captured.err


def test_map_requires_analyze_first(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0

    code = main(["map", "--project", str(project_path)])
    captured = capsys.readouterr()

    assert code == 7
    assert "map requires analyze" in captured.err


def test_segment_requires_scan_first(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)

    code = main(["segment", "--project", str(project_path)])
    captured = capsys.readouterr()

    assert code == 7
    assert "segment requires scan" in captured.err


def test_segment_writes_fixed_window_clips_and_report(tmp_path, monkeypatch, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / "a.mp4").write_bytes(b"content")
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    monkeypatch.setattr(
        cli,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True),
    )

    def fake_probe(path):
        return (
            MediaKind.video,
            MediaProbe(
                duration=25.0,
                width=1920,
                height=1080,
                frame_rate=25.0,
                video_codec="h264",
                audio_present=True,
                audio_codec="aac",
            ),
        )

    from artist_portrait_editor.media import scanner

    original_scan_project_sources = scanner.scan_project_sources

    def scan_with_fake_probe(*, root, config, previous_records=None):
        return original_scan_project_sources(
            root=root,
            config=config,
            probe_fn=fake_probe,
            previous_records=previous_records,
        )

    monkeypatch.setattr(workspace, "scan_project_sources", scan_with_fake_probe)

    assert main(["scan", "--project", str(project_path), "--quiet"]) == 0
    code = main(["segment", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["output"] == "output/clip_report.md"
    assert payload["output_refs"] == [
        ".artist-portrait/data/clips.jsonl",
        "output/clip_report.md",
    ]
    clips_path = tmp_path / ".artist-portrait" / "data" / "clips.jsonl"
    clips = [
        json.loads(line)
        for line in clips_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(clips) == 3
    assert [clip["boundary"]["start_seconds"] for clip in clips] == [0.0, 10.0, 20.0]
    assert [clip["boundary"]["end_seconds"] for clip in clips] == [10.0, 20.0, 25.0]
    assert clips[0]["method"] == "fixed_window"
    assert clips[-1]["risk_flags"] == ["inherited_source_risk", "short_tail"]

    clip_report = (tmp_path / "output" / "clip_report.md").read_text(encoding="utf-8")
    assert "# Clip Report" in clip_report
    assert "configured local segmentation method" in clip_report
    assert "- Clip count: `3`" in clip_report
    assert "fixed_window" in clip_report

    state_payload = json.loads(
        (tmp_path / ".artist-portrait" / "state.json").read_text(encoding="utf-8")
    )
    assert state_payload["steps"]["segment"]["status"] == "completed"
    assert state_payload["steps"]["segment"]["output_refs"] == [
        ".artist-portrait/data/clips.jsonl",
        "output/clip_report.md",
    ]

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)

    assert code == 0
    assert status_payload["summaries"]["clips"]["count"] == 3
    assert status_payload["summaries"]["clips"]["method_counts"] == {"fixed_window": 3}
    assert status_payload["artifacts"]["clip_report"]["exists"] is True


def test_segment_auto_missing_pyscenedetect_falls_back(tmp_path, monkeypatch, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("auto"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    monkeypatch.setattr(
        workspace,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True, pyscenedetect=False),
    )

    code = main(["segment", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 1
    payload = json.loads(captured.out)
    assert payload["warnings"] == [
        "pyscenedetect_missing: using fixed_window for media/clean.mp4"
    ]
    clips = [
        json.loads(line)
        for line in (tmp_path / ".artist-portrait" / "data" / "clips.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert clips[0]["method"] == "fixed_window"
    assert "scene_detection_fallback" in clips[0]["risk_flags"]


def test_segment_required_missing_pyscenedetect_returns_dependency_code(
    tmp_path,
    monkeypatch,
    capsys,
):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("required"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    monkeypatch.setattr(
        workspace,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True, pyscenedetect=False),
    )

    code = main(["segment", "--project", str(project_path)])
    captured = capsys.readouterr()

    assert code == 4
    assert "scene_detection is required but PySceneDetect is not available" in captured.err
    assert not (tmp_path / ".artist-portrait" / "data" / "clips.jsonl").exists()

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)
    assert code == 1
    assert any(
        issue["code"] == "scene_detection_required_missing"
        for issue in doctor_payload["issues"]
    )


def test_segment_uses_pyscenedetect_when_available(tmp_path, monkeypatch, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("auto"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    monkeypatch.setattr(
        workspace,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True, pyscenedetect=True),
    )
    monkeypatch.setattr(
        workspace,
        "detect_scenes_pyscenedetect",
        lambda path: [(0.0, 0.75), (0.75, 2.0)],
    )
    monkeypatch.setattr(workspace, "pyscenedetect_version", lambda: "test")

    code = main(["segment", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["warnings"] == []
    clips = [
        json.loads(line)
        for line in (tmp_path / ".artist-portrait" / "data" / "clips.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert [clip["method"] for clip in clips] == ["pyscenedetect", "pyscenedetect"]
    assert [clip["method_version"] for clip in clips] == [
        "pyscenedetect-test",
        "pyscenedetect-test",
    ]
    assert [clip["boundary"]["end_seconds"] for clip in clips] == [0.75, 2.0]


def test_segment_required_pyscenedetect_failure_returns_dependency_code(
    tmp_path,
    monkeypatch,
    capsys,
):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("required"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    monkeypatch.setattr(
        workspace,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True, pyscenedetect=True),
    )

    def fail_scene_detection(path):
        raise workspace.SceneDetectionError("synthetic failure")

    monkeypatch.setattr(workspace, "detect_scenes_pyscenedetect", fail_scene_detection)

    code = main(["segment", "--project", str(project_path)])
    captured = capsys.readouterr()

    assert code == 4
    assert "scene_detection is required but PySceneDetect failed" in captured.err


def test_transcribe_requires_scan_first(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)

    code = main(["transcribe", "--project", str(project_path)])
    captured = capsys.readouterr()

    assert code == 7
    assert "transcribe requires scan" in captured.err


def test_transcribe_off_skips_without_transcripts_file(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_transcription("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)

    code = main(["transcribe", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["status"] == "skipped"
    assert payload["output"] is None
    assert payload["warnings"] == []
    assert not (tmp_path / ".artist-portrait" / "data" / "transcripts.jsonl").exists()
    state_payload = json.loads(
        (tmp_path / ".artist-portrait" / "state.json").read_text(encoding="utf-8")
    )
    assert state_payload["steps"]["transcribe"]["status"] == "skipped"


def test_transcribe_auto_missing_faster_whisper_skips(tmp_path, monkeypatch, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_transcription("auto"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    monkeypatch.setattr(
        workspace,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True, faster_whisper=False),
    )

    code = main(["transcribe", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 1
    payload = json.loads(captured.out)
    assert payload["status"] == "skipped"
    assert payload["warnings"] == ["faster_whisper_missing: transcription skipped"]
    assert not (tmp_path / ".artist-portrait" / "data" / "transcripts.jsonl").exists()


def test_transcribe_required_missing_faster_whisper_returns_dependency_code(
    tmp_path,
    monkeypatch,
    capsys,
):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_transcription("required"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    monkeypatch.setattr(
        workspace,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True, faster_whisper=False),
    )

    code = main(["transcribe", "--project", str(project_path)])
    captured = capsys.readouterr()

    assert code == 4
    assert "transcription is required but faster-whisper is not available" in captured.err

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)
    assert code == 1
    assert any(
        issue["code"] == "transcription_required_missing"
        for issue in doctor_payload["issues"]
    )


def test_transcribe_writes_transcripts_when_faster_whisper_available(
    tmp_path,
    monkeypatch,
    capsys,
):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_transcription("auto"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    monkeypatch.setattr(
        workspace,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True, faster_whisper=True),
    )
    monkeypatch.setattr(workspace, "faster_whisper_version", lambda: "test")
    monkeypatch.setattr(
        workspace,
        "transcribe_source_faster_whisper",
        lambda path: [
            TranscribedSegment(
                start_seconds=0.0,
                end_seconds=1.25,
                text="hello world",
                language="en",
                confidence=0.8,
                words=[
                    TranscribedWord("hello", 0.0, 0.5, 0.9),
                    TranscribedWord("world", 0.5, 1.25, 0.85),
                ],
            )
        ],
    )

    code = main(["transcribe", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["output"] == ".artist-portrait/data/transcripts.jsonl"
    transcripts_path = tmp_path / ".artist-portrait" / "data" / "transcripts.jsonl"
    records = [
        json.loads(line)
        for line in transcripts_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) == 1
    assert records[0]["text"] == "hello world"
    assert records[0]["language"] == "en"
    assert records[0]["method"] == "faster_whisper"
    assert records[0]["method_version"] == "faster-whisper-test"
    assert records[0]["text_type"] is None
    assert records[0]["risk_flags"] == ["unclassified_text_type"]

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)
    assert code == 0
    assert status_payload["summaries"]["transcripts"]["count"] == 1
    assert status_payload["summaries"]["transcripts"]["language_counts"] == {"en": 1}


def test_invalid_transcripts_jsonl_status_and_doctor(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_transcription("auto"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    transcripts_path = tmp_path / ".artist-portrait" / "data" / "transcripts.jsonl"
    transcripts_path.write_text('{"transcript_id": "missing-required-fields"}\n', encoding="utf-8")

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 0
    assert payload["summaries"]["transcripts"]["valid"] is False
    assert "invalid TranscriptRecord JSONL" in payload["summaries"]["transcripts"]["error"]

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(issue["code"] == "transcripts_invalid" for issue in doctor_payload["issues"])


def test_repeated_cli_scan_invalidates_transcribe_outputs(
    tmp_path,
    monkeypatch,
    capsys,
):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_transcription("auto"),
        encoding="utf-8",
    )
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    media = media_dir / "a.mp4"
    media.write_bytes(b"first-content")
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    monkeypatch.setattr(
        cli,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True),
    )
    monkeypatch.setattr(
        workspace,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True, faster_whisper=True),
    )

    def fake_probe(path):
        return (
            MediaKind.video,
            MediaProbe(
                duration=3.0,
                width=16,
                height=16,
                frame_rate=24.0,
                video_codec="h264",
                audio_present=True,
                audio_codec="aac",
            ),
        )

    from artist_portrait_editor.media import scanner

    original_scan_project_sources = scanner.scan_project_sources

    def scan_with_fake_probe(*, root, config, previous_records=None):
        return original_scan_project_sources(
            root=root,
            config=config,
            probe_fn=fake_probe,
            previous_records=previous_records,
        )

    monkeypatch.setattr(workspace, "scan_project_sources", scan_with_fake_probe)
    monkeypatch.setattr(
        workspace,
        "transcribe_source_faster_whisper",
        lambda path: [
            TranscribedSegment(
                start_seconds=0.0,
                end_seconds=1.0,
                text="first",
                language="en",
                confidence=0.8,
            )
        ],
    )

    assert main(["scan", "--project", str(project_path), "--quiet"]) == 0
    assert main(["transcribe", "--project", str(project_path), "--quiet"]) == 0
    media.write_bytes(b"changed-content")

    code = main(["scan", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["invalidated_steps"] == ["transcribe"]
    state_payload = json.loads(
        (tmp_path / ".artist-portrait" / "state.json").read_text(encoding="utf-8")
    )
    assert state_payload["steps"]["transcribe"]["status"] == "invalidated"

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(issue["code"] == "transcribe_invalidated" for issue in doctor_payload["issues"])


def test_keyframes_requires_segment_first(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)

    code = main(["keyframes", "--project", str(project_path)])
    captured = capsys.readouterr()

    assert code == 7
    assert "keyframes requires segment" in captured.err


def test_keyframes_missing_ffmpeg_returns_dependency_code(tmp_path, monkeypatch, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0
    monkeypatch.setattr(
        workspace,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=False, ffprobe=True),
    )

    code = main(["keyframes", "--project", str(project_path)])
    captured = capsys.readouterr()

    assert code == 4
    assert "keyframes requires ffmpeg" in captured.err


def test_keyframes_writes_manifest_and_cache(tmp_path, monkeypatch, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0
    monkeypatch.setattr(
        workspace,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True),
    )
    monkeypatch.setattr(workspace, "ffmpeg_version", lambda: "ffmpeg-test")

    def fake_extract_keyframe_image(*, source_path, output_path, timestamp_seconds):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake-jpeg")

    monkeypatch.setattr(workspace, "extract_keyframe_image", fake_extract_keyframe_image)

    code = main(["keyframes", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["output"] == ".artist-portrait/data/keyframes.jsonl"
    keyframes_path = tmp_path / ".artist-portrait" / "data" / "keyframes.jsonl"
    records = [
        json.loads(line)
        for line in keyframes_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) == 1
    assert records[0]["method"] == "ffmpeg"
    assert records[0]["method_version"] == "ffmpeg-test"
    assert records[0]["timestamp_seconds"] == 1.0
    assert (tmp_path / records[0]["image_path"]).exists()

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)
    assert code == 0
    assert status_payload["summaries"]["keyframes"]["count"] == 1
    assert status_payload["summaries"]["keyframes"]["missing_cache_count"] == 0


def test_keyframes_audio_only_writes_empty_manifest_with_warning(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_audio_source_ledger(tmp_path)
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0

    code = main(["keyframes", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 1
    payload = json.loads(captured.out)
    assert payload["warnings"] == ["no video clips available for keyframe extraction"]
    keyframes_path = tmp_path / ".artist-portrait" / "data" / "keyframes.jsonl"
    assert keyframes_path.exists()
    assert keyframes_path.read_text(encoding="utf-8") == ""


def test_invalid_keyframes_jsonl_and_missing_cache_are_reported(
    tmp_path,
    monkeypatch,
    capsys,
):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0
    keyframes_path = tmp_path / ".artist-portrait" / "data" / "keyframes.jsonl"
    keyframes_path.write_text('{"keyframe_id": "missing-required-fields"}\n', encoding="utf-8")

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 0
    assert payload["summaries"]["keyframes"]["valid"] is False
    assert "invalid KeyframeRecord JSONL" in payload["summaries"]["keyframes"]["error"]

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(issue["code"] == "keyframes_invalid" for issue in doctor_payload["issues"])

    monkeypatch.setattr(
        workspace,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True),
    )
    monkeypatch.setattr(
        workspace,
        "extract_keyframe_image",
        lambda *, source_path, output_path, timestamp_seconds: (
            output_path.parent.mkdir(parents=True, exist_ok=True),
            output_path.write_bytes(b"fake-jpeg"),
        ),
    )
    assert main(["keyframes", "--project", str(project_path), "--quiet"]) == 0
    record = json.loads(keyframes_path.read_text(encoding="utf-8").splitlines()[0])
    (tmp_path / record["image_path"]).unlink()

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(issue["code"] == "keyframe_cache_missing" for issue in doctor_payload["issues"])


def test_repeated_segment_invalidates_keyframes(tmp_path, monkeypatch, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0
    monkeypatch.setattr(
        workspace,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True),
    )
    monkeypatch.setattr(
        workspace,
        "extract_keyframe_image",
        lambda *, source_path, output_path, timestamp_seconds: (
            output_path.parent.mkdir(parents=True, exist_ok=True),
            output_path.write_bytes(b"fake-jpeg"),
        ),
    )
    assert main(["keyframes", "--project", str(project_path), "--quiet"]) == 0

    write_clean_source_ledger(tmp_path)
    sources_path = tmp_path / ".artist-portrait" / "data" / "sources.jsonl"
    record = json.loads(sources_path.read_text(encoding="utf-8"))
    record["media_probe"]["duration"] = 4.0
    sources_path.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")

    code = main(["segment", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["invalidated_steps"] == ["keyframes"]
    state_payload = json.loads(
        (tmp_path / ".artist-portrait" / "state.json").read_text(encoding="utf-8")
    )
    assert state_payload["steps"]["keyframes"]["status"] == "invalidated"


def test_analyze_requires_segment_first(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)

    code = main(["analyze", "--project", str(project_path)])
    captured = capsys.readouterr()

    assert code == 7
    assert "analyze requires segment" in captured.err


def test_analyze_writes_evidence_ledger_and_report(tmp_path, monkeypatch, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0
    monkeypatch.setattr(
        workspace,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True),
    )
    monkeypatch.setattr(
        workspace,
        "extract_keyframe_image",
        lambda *, source_path, output_path, timestamp_seconds: (
            output_path.parent.mkdir(parents=True, exist_ok=True),
            output_path.write_bytes(b"fake-jpeg"),
        ),
    )
    assert main(["keyframes", "--project", str(project_path), "--quiet"]) == 0

    code = main(["analyze", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["output"] == ".artist-portrait/data/analysis.jsonl"
    assert payload["report"] == "output/analysis_report.md"
    analysis_path = tmp_path / ".artist-portrait" / "data" / "analysis.jsonl"
    records = [
        json.loads(line)
        for line in analysis_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) == 1
    assert records[0]["clip_id"]
    assert records[0]["material_type"]["value"] == "interview"
    assert records[0]["shot_size"]["value"] is None
    assert records[0]["shot_size"]["method"] == "not_run_current_gate"
    assert records[0]["emotion_candidates"]["value"] == []
    assert records[0]["keyframe_refs"]
    assert "visual_analysis_not_run" in records[0]["risk_flags"]
    report = (tmp_path / "output" / "analysis_report.md").read_text(encoding="utf-8")
    assert "Shot size, camera motion, emotion, action, and visual quality remain" in report

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)
    assert code == 0
    assert status_payload["summaries"]["analysis"]["count"] == 1


def test_invalid_analysis_jsonl_status_and_doctor(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0
    analysis_path = tmp_path / ".artist-portrait" / "data" / "analysis.jsonl"
    analysis_path.write_text('{"analysis_id": "missing-required-fields"}\n', encoding="utf-8")

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 0
    assert payload["summaries"]["analysis"]["valid"] is False
    assert "invalid AnalysisRecord JSONL" in payload["summaries"]["analysis"]["error"]

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(issue["code"] == "analysis_invalid" for issue in doctor_payload["issues"])


def test_repeated_segment_invalidates_analysis(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0
    assert main(["analyze", "--project", str(project_path), "--quiet"]) == 0

    write_clean_source_ledger(tmp_path)
    sources_path = tmp_path / ".artist-portrait" / "data" / "sources.jsonl"
    record = json.loads(sources_path.read_text(encoding="utf-8"))
    record["media_probe"]["duration"] = 4.0
    sources_path.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")

    code = main(["segment", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["invalidated_steps"] == ["analyze"]
    state_payload = json.loads(
        (tmp_path / ".artist-portrait" / "state.json").read_text(encoding="utf-8")
    )
    assert state_payload["steps"]["analyze"]["status"] == "invalidated"


def test_map_writes_material_map_from_analysis(tmp_path, monkeypatch, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / "a.mp4").write_bytes(b"content")
    (tmp_path / "sources.csv").write_text(
        "location,source_type,work,role,rights_status,forbidden_by_user,notes\n"
        "media/a.mp4,interview,Work A,Role A,owned,false,Primary interview\n",
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    monkeypatch.setattr(
        cli,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True),
    )

    def fake_probe(path):
        return (
            MediaKind.video,
            MediaProbe(
                duration=12.5,
                width=1920,
                height=1080,
                frame_rate=29.97,
                video_codec="h264",
                audio_present=True,
                audio_codec="aac",
            ),
        )

    from artist_portrait_editor.media import scanner

    original_scan_project_sources = scanner.scan_project_sources

    def scan_with_fake_probe(*, root, config, previous_records=None):
        return original_scan_project_sources(
            root=root,
            config=config,
            probe_fn=fake_probe,
            previous_records=previous_records,
        )

    monkeypatch.setattr(workspace, "scan_project_sources", scan_with_fake_probe)

    assert main(["scan", "--project", str(project_path), "--quiet"]) == 0
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0
    assert main(["analyze", "--project", str(project_path), "--quiet"]) == 0
    code = main(["map", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["output"] == "output/material_map.md"
    material_map = (tmp_path / "output" / "material_map.md").read_text(encoding="utf-8")
    assert "# Material Map" in material_map
    assert "rendered from local source and analysis ledgers" in material_map
    assert "- Source count: `1`" in material_map
    assert "- Analysis record count: `2`" in material_map
    assert "- Total duration seconds: `12.500`" in material_map
    assert "## Priority Review Queue" in material_map
    assert "## Pending Confirmation" in material_map
    assert "## Risk Items" in material_map
    assert "### 1. `media/a.mp4`" in material_map
    assert "- Source type: `interview`" in material_map
    assert "- Rights status: `owned`" in material_map
    assert "- Notes: Primary interview" in material_map

    state_payload = json.loads(
        (tmp_path / ".artist-portrait" / "state.json").read_text(encoding="utf-8")
    )
    assert state_payload["steps"]["map"]["status"] == "completed"
    assert state_payload["steps"]["map"]["output_refs"] == ["output/material_map.md"]


def test_propose_requires_map_first(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)

    code = main(["propose", "--project", str(project_path)])
    captured = capsys.readouterr()

    assert code == 7
    assert "propose requires map" in captured.err


def test_propose_without_text_model_blocks_without_fake_outputs(
    tmp_path,
    monkeypatch,
    capsys,
):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0
    assert main(["analyze", "--project", str(project_path), "--quiet"]) == 0
    assert main(["map", "--project", str(project_path), "--quiet"]) == 0
    monkeypatch.setattr(
        workspace,
        "detect_capabilities",
        lambda: Capabilities(text_model=False),
    )

    code = main(["propose", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 1
    payload = json.loads(captured.out)
    assert payload["status"] == "blocked"
    assert payload["output_refs"] == [
        ".artist-portrait/data/proposal_context.json",
        ".artist-portrait/data/text_model_gate.json",
        ".artist-portrait/data/proposal_request.json",
        "output/proposal_agent_handoff.json",
        ".artist-portrait/data/proposal_adapter_check.json",
        ".artist-portrait/data/proposal_provider_registry.json",
        ".artist-portrait/data/proposal_mock_adapter_handshake.json",
        ".artist-portrait/data/proposal_execution_approval_request.json",
        ".artist-portrait/data/proposal_execution_approval_record.json",
        ".artist-portrait/data/proposal_execution_readiness_plan.json",
        ".artist-portrait/data/proposal_execution_input_bundle.json",
        ".artist-portrait/data/proposal_provider_call_dry_run.json",
        ".artist-portrait/data/proposal_execution_authorization.json",
        ".artist-portrait/data/proposal_provider_response_intake_plan.json",
        ".artist-portrait/data/proposal_provider_output_quarantine.json",
        ".artist-portrait/data/proposal_provider_response_validation_plan.json",
        ".artist-portrait/data/proposal_promotion_authorization_plan.json",
        ".artist-portrait/data/proposal_promotion_validation_report.json",
        ".artist-portrait/data/proposal_canonical_write_transaction_plan.json",
        ".artist-portrait/data/proposal_provider_result.json",
    ]
    assert "host_agent_candidate_required" in payload["warnings"][0]
    assert "paid APIs were not used" in payload["warnings"][0]
    assert payload["output"] is None
    context_path = tmp_path / ".artist-portrait" / "data" / "proposal_context.json"
    assert context_path.exists()
    context_payload = json.loads(context_path.read_text(encoding="utf-8"))
    assert context_payload["project_id"] == "chen_haoyu_portrait_001"
    assert context_payload["proposal_ids_required"] == [
        "proposal_safe",
        "proposal_advanced",
        "proposal_risky",
    ]
    assert context_payload["sources"][0]["source_id"] == "clean-source-1"
    assert context_payload["clips"][0]["clip_id"] == context_payload["analyses"][0]["clip_id"]
    assert context_payload["bgm_requirements"]
    assert "timeline_generation" in context_payload["blocked_capabilities"]
    assert "full_creative_proposal_generation" not in context_payload["blocked_capabilities"]
    handoff_payload = json.loads(
        (tmp_path / "output" / "proposal_agent_handoff.json").read_text(
            encoding="utf-8"
        )
    )
    assert handoff_payload["mode"] == "codex_chatgpt_host_agent"
    assert handoff_payload["proposal_set_json_schema"]["title"] == "ProposalSet"
    gate_path = tmp_path / ".artist-portrait" / "data" / "text_model_gate.json"
    assert gate_path.exists()
    gate_payload = json.loads(gate_path.read_text(encoding="utf-8"))
    assert gate_payload["status"] == "blocked"
    assert gate_payload["remote_text_model_allowed"] is False
    assert gate_payload["text_model_capability"] is False
    assert gate_payload["reasons"] == [
        "remote_text_model_not_allowed",
        "text_model_capability_missing",
    ]
    request_path = tmp_path / ".artist-portrait" / "data" / "proposal_request.json"
    assert request_path.exists()
    request_payload = json.loads(request_path.read_text(encoding="utf-8"))
    assert request_payload["status"] == "blocked"
    assert request_payload["target_schema_name"] == "ProposalSet"
    assert request_payload["required_proposal_ids"] == [
        "proposal_safe",
        "proposal_advanced",
        "proposal_risky",
    ]
    assert request_payload["blocking_reasons"] == [
        "remote_text_model_not_allowed",
        "text_model_capability_missing",
    ]
    assert "BGM" in request_payload["user_prompt"]
    adapter_path = tmp_path / ".artist-portrait" / "data" / "proposal_adapter_check.json"
    assert adapter_path.exists()
    adapter_payload = json.loads(adapter_path.read_text(encoding="utf-8"))
    assert adapter_payload["status"] == "blocked"
    assert adapter_payload["provider"] == "unconfigured"
    assert adapter_payload["provider_mode"] == "dry_run_contract_only"
    assert adapter_payload["model_call_performed"] is False
    assert adapter_payload["network_performed"] is False
    assert "plaintext_secret_material_detected" not in {
        issue["code"] for issue in adapter_payload["issues"]
    }
    registry_path = (
        tmp_path / ".artist-portrait" / "data" / "proposal_provider_registry.json"
    )
    assert registry_path.exists()
    registry_payload = json.loads(registry_path.read_text(encoding="utf-8"))
    assert registry_payload["selected_provider_id"] == "local_mock"
    assert registry_payload["generation_open"] is False
    assert registry_payload["model_call_performed"] is False
    assert registry_payload["network_performed"] is False
    assert registry_payload["providers"][0]["execution_mode"] == "dry_run_mock_no_generation"
    handshake_path = (
        tmp_path / ".artist-portrait" / "data" / "proposal_mock_adapter_handshake.json"
    )
    assert handshake_path.exists()
    handshake_payload = json.loads(handshake_path.read_text(encoding="utf-8"))
    assert handshake_payload["status"] == "blocked"
    assert handshake_payload["provider_id"] == "local_mock"
    assert handshake_payload["model_call_performed"] is False
    assert handshake_payload["network_performed"] is False
    assert handshake_payload["proposal_content_generated"] is False
    approval_path = (
        tmp_path / ".artist-portrait" / "data" / "proposal_execution_approval_request.json"
    )
    assert approval_path.exists()
    approval_payload = json.loads(approval_path.read_text(encoding="utf-8"))
    assert approval_payload["status"] == "blocked"
    assert approval_payload["provider_id"] == "local_mock"
    assert approval_payload["approval_required"] is True
    assert approval_payload["approval_recorded"] is False
    assert approval_payload["approval_record_ref"] is None
    assert approval_payload["secret_source_selection_required"] is True
    assert approval_payload["allowed_secret_sources"] == [
        "environment_variable_name_only",
        "os_keychain_reference",
        "encrypted_secret_reference",
    ]
    assert approval_payload["selected_secret_source"] is None
    assert approval_payload["credential_value_read"] is False
    assert approval_payload["credential_value_ref"] is None
    assert approval_payload["network_allowed"] is False
    assert approval_payload["model_call_allowed"] is False
    assert approval_payload["execution_performed"] is False
    assert approval_payload["model_call_performed"] is False
    assert approval_payload["network_performed"] is False
    assert approval_payload["proposal_content_generated"] is False
    assert approval_payload["quarantine_required"] is True
    approval_record_path = (
        tmp_path / ".artist-portrait" / "data" / "proposal_execution_approval_record.json"
    )
    assert approval_record_path.exists()
    approval_record_payload = json.loads(
        approval_record_path.read_text(encoding="utf-8")
    )
    assert approval_record_payload["status"] == "blocked"
    assert approval_record_payload["provider_id"] == "local_mock"
    assert approval_record_payload["approval_granted"] is False
    assert approval_record_payload["approval_actor"] is None
    assert approval_record_payload["approval_recorded_at"] is None
    assert approval_record_payload["approval_scope"] == "none_current_gate"
    assert approval_record_payload["selected_secret_source"] is None
    assert approval_record_payload["credential_value_read"] is False
    assert approval_record_payload["credential_value_ref"] is None
    assert approval_record_payload["network_allowed"] is False
    assert approval_record_payload["model_call_allowed"] is False
    assert approval_record_payload["execution_allowed"] is False
    assert approval_record_payload["execution_performed"] is False
    assert approval_record_payload["model_call_performed"] is False
    assert approval_record_payload["network_performed"] is False
    assert approval_record_payload["proposal_content_generated"] is False
    assert approval_record_payload["quarantine_required"] is True
    readiness_path = (
        tmp_path / ".artist-portrait" / "data" / "proposal_execution_readiness_plan.json"
    )
    assert readiness_path.exists()
    readiness_payload = json.loads(readiness_path.read_text(encoding="utf-8"))
    assert readiness_payload["status"] == "blocked"
    assert readiness_payload["provider_id"] == "local_mock"
    assert readiness_payload["secret_source_selection"]["status"] == "blocked"
    assert readiness_payload["credential_access"]["status"] == "blocked"
    assert readiness_payload["execution_plan"]["status"] == "blocked"
    assert readiness_payload["provider_call_preflight"]["status"] == "blocked"
    assert readiness_payload["output_capture_plan"]["status"] == "blocked"
    assert readiness_payload["selected_secret_source"] is None
    assert readiness_payload["credential_value_read"] is False
    assert readiness_payload["network_allowed"] is False
    assert readiness_payload["model_call_allowed"] is False
    assert readiness_payload["execution_allowed"] is False
    assert readiness_payload["execution_performed"] is False
    assert readiness_payload["model_call_performed"] is False
    assert readiness_payload["network_performed"] is False
    assert readiness_payload["raw_output_capture_allowed"] is False
    assert readiness_payload["raw_output_captured"] is False
    assert readiness_payload["proposal_content_generated"] is False
    assert readiness_payload["quarantine_required"] is True
    input_bundle_path = (
        tmp_path / ".artist-portrait" / "data" / "proposal_execution_input_bundle.json"
    )
    assert input_bundle_path.exists()
    input_bundle_payload = json.loads(input_bundle_path.read_text(encoding="utf-8"))
    assert input_bundle_payload["status"] == "blocked"
    assert input_bundle_payload["provider_id"] == "local_mock"
    for item_id in [
        "provider_identity",
        "request_packet",
        "prompt_contract",
        "schema_contract",
        "approval_chain",
        "secret_reference",
        "credential_access_policy",
        "network_policy",
        "quarantine_target",
        "output_routing",
    ]:
        assert input_bundle_payload[item_id]["status"] == "blocked"
        assert input_bundle_payload[item_id]["allowed"] is False
        assert input_bundle_payload[item_id]["materialized"] is False
    assert input_bundle_payload["selected_secret_source"] is None
    assert input_bundle_payload["credential_value_read"] is False
    assert input_bundle_payload["network_allowed"] is False
    assert input_bundle_payload["model_call_allowed"] is False
    assert input_bundle_payload["execution_allowed"] is False
    assert input_bundle_payload["execution_performed"] is False
    assert input_bundle_payload["model_call_performed"] is False
    assert input_bundle_payload["network_performed"] is False
    assert input_bundle_payload["raw_output_capture_allowed"] is False
    assert input_bundle_payload["raw_output_captured"] is False
    assert input_bundle_payload["proposal_content_generated"] is False
    assert input_bundle_payload["prompt_embedded"] is False
    assert input_bundle_payload["quarantine_required"] is True
    call_dry_run_path = (
        tmp_path / ".artist-portrait" / "data" / "proposal_provider_call_dry_run.json"
    )
    assert call_dry_run_path.exists()
    call_dry_run_payload = json.loads(call_dry_run_path.read_text(encoding="utf-8"))
    assert call_dry_run_payload["status"] == "blocked"
    assert call_dry_run_payload["provider_id"] == "local_mock"
    for item_id in [
        "endpoint_reference",
        "auth_header_policy",
        "request_body_reference",
        "timeout_policy",
        "retry_policy",
        "rate_limit_policy",
        "idempotency_policy",
        "network_egress_policy",
        "response_capture_policy",
        "failure_handling_policy",
    ]:
        assert call_dry_run_payload[item_id]["status"] == "blocked"
        assert call_dry_run_payload[item_id]["allowed"] is False
        assert call_dry_run_payload[item_id]["materialized"] is False
    assert call_dry_run_payload["endpoint_resolved"] is False
    assert call_dry_run_payload["auth_header_materialized"] is False
    assert call_dry_run_payload["request_body_materialized"] is False
    assert call_dry_run_payload["timeout_seconds"] is None
    assert call_dry_run_payload["retry_count"] == 0
    assert call_dry_run_payload["idempotency_key_materialized"] is False
    assert call_dry_run_payload["selected_secret_source"] is None
    assert call_dry_run_payload["credential_value_read"] is False
    assert call_dry_run_payload["network_allowed"] is False
    assert call_dry_run_payload["model_call_allowed"] is False
    assert call_dry_run_payload["execution_allowed"] is False
    assert call_dry_run_payload["execution_performed"] is False
    assert call_dry_run_payload["model_call_performed"] is False
    assert call_dry_run_payload["network_performed"] is False
    assert call_dry_run_payload["raw_output_capture_allowed"] is False
    assert call_dry_run_payload["raw_output_captured"] is False
    assert call_dry_run_payload["request_payload_sent"] is False
    assert call_dry_run_payload["proposal_content_generated"] is False
    assert call_dry_run_payload["quarantine_required"] is True
    authorization_path = (
        tmp_path / ".artist-portrait" / "data" / "proposal_execution_authorization.json"
    )
    assert authorization_path.exists()
    authorization_payload = json.loads(authorization_path.read_text(encoding="utf-8"))
    assert authorization_payload["status"] == "blocked"
    assert authorization_payload["provider_id"] == "local_mock"
    assert authorization_payload["approved_execution_gate"] is False
    assert authorization_payload["user_approval_required"] is True
    assert authorization_payload["user_approval_present"] is False
    assert authorization_payload["credential_policy"] == "no_credentials_allowed_current_gate"
    assert authorization_payload["allowed_secret_sources"] == []
    assert authorization_payload["selected_secret_source"] is None
    assert authorization_payload["network_allowed"] is False
    assert authorization_payload["model_call_allowed"] is False
    assert authorization_payload["execution_performed"] is False
    assert authorization_payload["model_call_performed"] is False
    assert authorization_payload["network_performed"] is False
    assert authorization_payload["proposal_content_generated"] is False
    assert authorization_payload["quarantine_required"] is True
    response_intake_path = (
        tmp_path
        / ".artist-portrait"
        / "data"
        / "proposal_provider_response_intake_plan.json"
    )
    assert response_intake_path.exists()
    response_intake_payload = json.loads(response_intake_path.read_text(encoding="utf-8"))
    assert response_intake_payload["status"] == "blocked"
    assert response_intake_payload["provider_id"] == "local_mock"
    for item_id in [
        "response_channel",
        "raw_output_location",
        "content_type_policy",
        "size_limit_policy",
        "checksum_policy",
        "redaction_policy",
        "parser_selection",
        "validation_queue",
        "promotion_gate",
        "audit_trail",
    ]:
        assert response_intake_payload[item_id]["status"] == "blocked"
        assert response_intake_payload[item_id]["allowed"] is False
        assert response_intake_payload[item_id]["materialized"] is False
    assert response_intake_payload["response_channel_open"] is False
    assert response_intake_payload["raw_output_location_materialized"] is False
    assert response_intake_payload["content_type_validated"] is False
    assert response_intake_payload["size_limit_bytes"] == 0
    assert response_intake_payload["checksum_computed"] is False
    assert response_intake_payload["redaction_performed"] is False
    assert response_intake_payload["parser_selected"] is False
    assert response_intake_payload["validation_enqueued"] is False
    assert response_intake_payload["promotion_allowed"] is False
    assert response_intake_payload["audit_event_written"] is False
    assert response_intake_payload["raw_output_captured"] is False
    assert response_intake_payload["parsed_payload_generated"] is False
    assert response_intake_payload["validation_performed"] is False
    assert response_intake_payload["promoted_to_proposals"] is False
    assert response_intake_payload["model_call_performed"] is False
    assert response_intake_payload["network_performed"] is False
    assert response_intake_payload["proposal_content_generated"] is False
    assert response_intake_payload["quarantine_required"] is True
    quarantine_path = (
        tmp_path
        / ".artist-portrait"
        / "data"
        / "proposal_provider_output_quarantine.json"
    )
    assert quarantine_path.exists()
    quarantine_payload = json.loads(quarantine_path.read_text(encoding="utf-8"))
    assert quarantine_payload["status"] == "blocked"
    assert quarantine_payload["provider_id"] == "local_mock"
    assert quarantine_payload["raw_output_captured"] is False
    assert quarantine_payload["raw_output_ref"] is None
    assert quarantine_payload["raw_output_sha256"] is None
    assert quarantine_payload["raw_output_bytes"] == 0
    assert quarantine_payload["parsed_payload_generated"] is False
    assert quarantine_payload["parsed_payload_ref"] is None
    assert quarantine_payload["promoted_to_proposals"] is False
    assert quarantine_payload["validation_performed"] is False
    assert quarantine_payload["model_call_performed"] is False
    assert quarantine_payload["network_performed"] is False
    assert quarantine_payload["proposal_content_generated"] is False
    assert quarantine_payload["quarantine_required"] is True
    response_validation_path = (
        tmp_path
        / ".artist-portrait"
        / "data"
        / "proposal_provider_response_validation_plan.json"
    )
    assert response_validation_path.exists()
    response_validation_payload = json.loads(
        response_validation_path.read_text(encoding="utf-8")
    )
    assert response_validation_payload["status"] == "blocked"
    assert response_validation_payload["provider_id"] == "local_mock"
    for item_id in [
        "quarantine_input_binding",
        "content_type_check",
        "size_limit_check",
        "checksum_verification",
        "redaction_verification",
        "parser_contract",
        "json_syntax_validation",
        "schema_validation",
        "semantic_validation",
        "promotion_decision",
    ]:
        assert response_validation_payload[item_id]["status"] == "blocked"
        assert response_validation_payload[item_id]["allowed"] is False
        assert response_validation_payload[item_id]["materialized"] is False
    assert response_validation_payload["quarantine_input_bound"] is False
    assert response_validation_payload["content_type_checked"] is False
    assert response_validation_payload["size_limit_checked"] is False
    assert response_validation_payload["checksum_verified"] is False
    assert response_validation_payload["redaction_verified"] is False
    assert response_validation_payload["parser_contract_selected"] is False
    assert response_validation_payload["json_syntax_validated"] is False
    assert response_validation_payload["schema_validated"] is False
    assert response_validation_payload["semantic_validation_performed"] is False
    assert response_validation_payload["promotion_decided"] is False
    assert response_validation_payload["raw_output_read"] is False
    assert response_validation_payload["parsed_payload_generated"] is False
    assert response_validation_payload["validation_performed"] is False
    assert response_validation_payload["promoted_to_proposals"] is False
    assert response_validation_payload["audit_event_written"] is False
    assert response_validation_payload["model_call_performed"] is False
    assert response_validation_payload["network_performed"] is False
    assert response_validation_payload["proposal_content_generated"] is False
    assert response_validation_payload["quarantine_required"] is True
    promotion_path = (
        tmp_path
        / ".artist-portrait"
        / "data"
        / "proposal_promotion_authorization_plan.json"
    )
    assert promotion_path.exists()
    promotion_payload = json.loads(promotion_path.read_text(encoding="utf-8"))
    assert promotion_payload["status"] == "blocked"
    assert promotion_payload["provider_id"] == "local_mock"
    assert promotion_payload["promotion_target_ref"] == ".artist-portrait/data/proposals.json"
    for item_id in [
        "validation_report_binding",
        "schema_validation_requirement",
        "semantic_validation_requirement",
        "evidence_validation_requirement",
        "risk_acceptance_requirement",
        "proposal_identity_requirement",
        "overwrite_policy",
        "atomic_write_policy",
        "provenance_binding",
        "final_promotion_authorization",
    ]:
        assert promotion_payload[item_id]["status"] == "blocked"
        assert promotion_payload[item_id]["allowed"] is False
        assert promotion_payload[item_id]["materialized"] is False
    for field in [
        "validation_report_bound",
        "schema_validation_passed",
        "semantic_validation_passed",
        "evidence_validation_passed",
        "risk_acceptance_recorded",
        "proposal_ids_unique",
        "overwrite_allowed",
        "atomic_write_ready",
        "provenance_bound",
        "promotion_authorized",
        "promotion_performed",
        "proposals_file_written",
        "audit_event_written",
        "model_call_performed",
        "network_performed",
        "proposal_content_generated",
    ]:
        assert promotion_payload[field] is False
    assert promotion_payload["quarantine_required"] is True
    promotion_report_path = (
        tmp_path
        / ".artist-portrait"
        / "data"
        / "proposal_promotion_validation_report.json"
    )
    assert promotion_report_path.exists()
    promotion_report_payload = json.loads(
        promotion_report_path.read_text(encoding="utf-8")
    )
    assert promotion_report_payload["status"] == "blocked"
    for check_id in [
        "input_binding_check",
        "schema_result_check",
        "semantic_result_check",
        "evidence_traceability_check",
        "risk_result_check",
        "proposal_identity_check",
        "overwrite_conflict_check",
        "atomic_write_readiness_check",
        "provenance_integrity_check",
        "final_authorization_check",
    ]:
        assert promotion_report_payload[check_id]["status"] == "blocked"
        assert promotion_report_payload[check_id]["performed"] is False
        assert promotion_report_payload[check_id]["passed"] is False
        assert promotion_report_payload[check_id]["issue_count"] == 1
    assert promotion_report_payload["checks_performed"] == 0
    assert promotion_report_payload["checks_passed"] == 0
    assert promotion_report_payload["error_count"] == 0
    assert promotion_report_payload["warning_count"] == 0
    assert promotion_report_payload["overall_passed"] is False
    assert promotion_report_payload["promotion_recommended"] is False
    assert promotion_report_payload["promotion_authorized"] is False
    assert promotion_report_payload["promotion_performed"] is False
    assert promotion_report_payload["proposals_file_written"] is False
    assert promotion_report_payload["model_call_performed"] is False
    assert promotion_report_payload["network_performed"] is False
    assert promotion_report_payload["proposal_content_generated"] is False
    assert promotion_report_payload["quarantine_required"] is True
    transaction_path = (
        tmp_path / ".artist-portrait" / "data" / "proposal_canonical_write_transaction_plan.json"
    )
    assert transaction_path.exists()
    transaction_payload = json.loads(transaction_path.read_text(encoding="utf-8"))
    assert transaction_payload["status"] == "blocked"
    for item_id in [
        "target_lock", "prewrite_snapshot", "temporary_file",
        "schema_prewrite_check", "durability_policy", "atomic_replace",
        "conflict_detection", "rollback_plan", "audit_commit",
        "postcommit_verification",
    ]:
        assert transaction_payload[item_id]["status"] == "blocked"
        assert transaction_payload[item_id]["allowed"] is False
        assert transaction_payload[item_id]["materialized"] is False
    for field in [
        "lock_acquired", "snapshot_created", "temporary_file_created",
        "schema_prewrite_passed", "fsync_performed", "atomic_replace_performed",
        "conflict_check_performed", "rollback_prepared", "rollback_performed",
        "audit_commit_written", "postcommit_verified", "transaction_started",
        "transaction_committed", "proposals_file_written", "model_call_performed",
        "network_performed", "proposal_content_generated",
    ]:
        assert transaction_payload[field] is False
    result_path = tmp_path / ".artist-portrait" / "data" / "proposal_provider_result.json"
    assert result_path.exists()
    result_payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert result_payload["status"] == "blocked"
    assert result_payload["provider_id"] == "local_mock"
    assert result_payload["expected_output_kind"] == "ProposalSet"
    assert (
        result_payload["response_validation_ref"]
        == ".artist-portrait/data/proposal_provider_response_validation_plan.json"
    )
    assert (
        result_payload["promotion_authorization_ref"]
        == ".artist-portrait/data/proposal_promotion_authorization_plan.json"
    )
    assert (
        result_payload["promotion_validation_report_ref"]
        == ".artist-portrait/data/proposal_promotion_validation_report.json"
    )
    assert (
        result_payload["canonical_write_transaction_ref"]
        == ".artist-portrait/data/proposal_canonical_write_transaction_plan.json"
    )
    assert result_payload["payload_generated"] is False
    assert result_payload["payload_json_ref"] is None
    assert result_payload["validation_performed"] is False
    assert result_payload["model_call_performed"] is False
    assert result_payload["network_performed"] is False
    assert result_payload["proposal_content_generated"] is False
    assert not (tmp_path / ".artist-portrait" / "data" / "proposals.json").exists()
    assert not (tmp_path / "output" / "proposals.md").exists()
    state_payload = json.loads(
        (tmp_path / ".artist-portrait" / "state.json").read_text(encoding="utf-8")
    )
    assert state_payload["steps"]["propose"]["status"] == "blocked"
    assert state_payload["steps"]["propose"]["output_refs"] == [
        ".artist-portrait/data/proposal_context.json",
        ".artist-portrait/data/text_model_gate.json",
        ".artist-portrait/data/proposal_request.json",
        "output/proposal_agent_handoff.json",
        ".artist-portrait/data/proposal_adapter_check.json",
        ".artist-portrait/data/proposal_provider_registry.json",
        ".artist-portrait/data/proposal_mock_adapter_handshake.json",
        ".artist-portrait/data/proposal_execution_approval_request.json",
        ".artist-portrait/data/proposal_execution_approval_record.json",
        ".artist-portrait/data/proposal_execution_readiness_plan.json",
        ".artist-portrait/data/proposal_execution_input_bundle.json",
        ".artist-portrait/data/proposal_provider_call_dry_run.json",
        ".artist-portrait/data/proposal_execution_authorization.json",
        ".artist-portrait/data/proposal_provider_response_intake_plan.json",
        ".artist-portrait/data/proposal_provider_output_quarantine.json",
        ".artist-portrait/data/proposal_provider_response_validation_plan.json",
        ".artist-portrait/data/proposal_promotion_authorization_plan.json",
        ".artist-portrait/data/proposal_promotion_validation_report.json",
        ".artist-portrait/data/proposal_canonical_write_transaction_plan.json",
        ".artist-portrait/data/proposal_provider_result.json",
    ]


def test_propose_with_ready_text_model_gate_still_does_not_generate(
    tmp_path,
    monkeypatch,
    capsys,
):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_remote_text_model_allowed().replace(
            "scene_detection: auto",
            "scene_detection: off",
        ),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0
    assert main(["analyze", "--project", str(project_path), "--quiet"]) == 0
    assert main(["map", "--project", str(project_path), "--quiet"]) == 0
    monkeypatch.setattr(
        workspace,
        "detect_capabilities",
        lambda: Capabilities(text_model=True),
    )

    code = main(["propose", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 1
    payload = json.loads(captured.out)
    assert payload["status"] == "blocked"
    assert "host_agent_candidate_required" in payload["warnings"][0]
    assert payload["output"] is None
    gate_payload = json.loads(
        (tmp_path / ".artist-portrait" / "data" / "text_model_gate.json").read_text(
            encoding="utf-8"
        )
    )
    assert gate_payload["status"] == "ready"
    assert gate_payload["reasons"] == []
    request_payload = json.loads(
        (tmp_path / ".artist-portrait" / "data" / "proposal_request.json").read_text(
            encoding="utf-8"
        )
    )
    assert request_payload["status"] == "ready"
    assert request_payload["blocking_reasons"] == []
    assert "ProposalSet" in request_payload["developer_prompt"]
    adapter_payload = json.loads(
        (
            tmp_path / ".artist-portrait" / "data" / "proposal_adapter_check.json"
        ).read_text(encoding="utf-8")
    )
    assert adapter_payload["status"] == "ready_for_future_adapter"
    assert adapter_payload["model_call_performed"] is False
    assert adapter_payload["network_performed"] is False
    registry_payload = json.loads(
        (
            tmp_path / ".artist-portrait" / "data" / "proposal_provider_registry.json"
        ).read_text(encoding="utf-8")
    )
    assert registry_payload["selected_provider_id"] == "local_mock"
    assert registry_payload["generation_open"] is False
    handshake_payload = json.loads(
        (
            tmp_path / ".artist-portrait" / "data" / "proposal_mock_adapter_handshake.json"
        ).read_text(encoding="utf-8")
    )
    assert handshake_payload["status"] == "ready_for_future_execution"
    assert handshake_payload["model_call_performed"] is False
    assert handshake_payload["network_performed"] is False
    assert handshake_payload["proposal_content_generated"] is False
    approval_payload = json.loads(
        (
            tmp_path
            / ".artist-portrait"
            / "data"
            / "proposal_execution_approval_request.json"
        ).read_text(encoding="utf-8")
    )
    assert approval_payload["status"] == "blocked"
    assert approval_payload["approval_recorded"] is False
    assert approval_payload["selected_secret_source"] is None
    assert approval_payload["credential_value_read"] is False
    assert approval_payload["network_allowed"] is False
    assert approval_payload["model_call_allowed"] is False
    assert approval_payload["execution_performed"] is False
    approval_record_payload = json.loads(
        (
            tmp_path
            / ".artist-portrait"
            / "data"
            / "proposal_execution_approval_record.json"
        ).read_text(encoding="utf-8")
    )
    assert approval_record_payload["status"] == "blocked"
    assert approval_record_payload["approval_granted"] is False
    assert approval_record_payload["selected_secret_source"] is None
    assert approval_record_payload["credential_value_read"] is False
    assert approval_record_payload["execution_allowed"] is False
    assert approval_record_payload["execution_performed"] is False
    readiness_payload = json.loads(
        (
            tmp_path
            / ".artist-portrait"
            / "data"
            / "proposal_execution_readiness_plan.json"
        ).read_text(encoding="utf-8")
    )
    assert readiness_payload["status"] == "blocked"
    assert readiness_payload["secret_source_selection"]["status"] == "blocked"
    assert readiness_payload["credential_access"]["status"] == "blocked"
    assert readiness_payload["execution_plan"]["status"] == "blocked"
    assert readiness_payload["provider_call_preflight"]["status"] == "blocked"
    assert readiness_payload["output_capture_plan"]["status"] == "blocked"
    assert readiness_payload["credential_value_read"] is False
    assert readiness_payload["execution_allowed"] is False
    assert readiness_payload["raw_output_captured"] is False
    input_bundle_payload = json.loads(
        (
            tmp_path
            / ".artist-portrait"
            / "data"
            / "proposal_execution_input_bundle.json"
        ).read_text(encoding="utf-8")
    )
    assert input_bundle_payload["status"] == "blocked"
    assert input_bundle_payload["provider_identity"]["status"] == "blocked"
    assert input_bundle_payload["request_packet"]["status"] == "blocked"
    assert input_bundle_payload["prompt_contract"]["status"] == "blocked"
    assert input_bundle_payload["schema_contract"]["status"] == "blocked"
    assert input_bundle_payload["approval_chain"]["status"] == "blocked"
    assert input_bundle_payload["secret_reference"]["status"] == "blocked"
    assert input_bundle_payload["credential_access_policy"]["status"] == "blocked"
    assert input_bundle_payload["network_policy"]["status"] == "blocked"
    assert input_bundle_payload["quarantine_target"]["status"] == "blocked"
    assert input_bundle_payload["output_routing"]["status"] == "blocked"
    assert input_bundle_payload["credential_value_read"] is False
    assert input_bundle_payload["execution_allowed"] is False
    assert input_bundle_payload["raw_output_captured"] is False
    assert input_bundle_payload["prompt_embedded"] is False
    call_dry_run_payload = json.loads(
        (
            tmp_path
            / ".artist-portrait"
            / "data"
            / "proposal_provider_call_dry_run.json"
        ).read_text(encoding="utf-8")
    )
    assert call_dry_run_payload["status"] == "blocked"
    assert call_dry_run_payload["endpoint_reference"]["status"] == "blocked"
    assert call_dry_run_payload["auth_header_policy"]["status"] == "blocked"
    assert call_dry_run_payload["request_body_reference"]["status"] == "blocked"
    assert call_dry_run_payload["timeout_policy"]["status"] == "blocked"
    assert call_dry_run_payload["retry_policy"]["status"] == "blocked"
    assert call_dry_run_payload["rate_limit_policy"]["status"] == "blocked"
    assert call_dry_run_payload["idempotency_policy"]["status"] == "blocked"
    assert call_dry_run_payload["network_egress_policy"]["status"] == "blocked"
    assert call_dry_run_payload["response_capture_policy"]["status"] == "blocked"
    assert call_dry_run_payload["failure_handling_policy"]["status"] == "blocked"
    assert call_dry_run_payload["endpoint_resolved"] is False
    assert call_dry_run_payload["auth_header_materialized"] is False
    assert call_dry_run_payload["request_body_materialized"] is False
    assert call_dry_run_payload["credential_value_read"] is False
    assert call_dry_run_payload["execution_allowed"] is False
    assert call_dry_run_payload["network_performed"] is False
    assert call_dry_run_payload["request_payload_sent"] is False
    assert call_dry_run_payload["raw_output_captured"] is False
    authorization_payload = json.loads(
        (
            tmp_path
            / ".artist-portrait"
            / "data"
            / "proposal_execution_authorization.json"
        ).read_text(encoding="utf-8")
    )
    assert authorization_payload["status"] == "blocked"
    assert authorization_payload["approved_execution_gate"] is False
    assert authorization_payload["user_approval_present"] is False
    assert authorization_payload["network_allowed"] is False
    assert authorization_payload["model_call_allowed"] is False
    assert authorization_payload["execution_performed"] is False
    response_intake_payload = json.loads(
        (
            tmp_path
            / ".artist-portrait"
            / "data"
            / "proposal_provider_response_intake_plan.json"
        ).read_text(encoding="utf-8")
    )
    assert response_intake_payload["status"] == "blocked"
    assert response_intake_payload["response_channel"]["status"] == "blocked"
    assert response_intake_payload["raw_output_location"]["status"] == "blocked"
    assert response_intake_payload["content_type_policy"]["status"] == "blocked"
    assert response_intake_payload["size_limit_policy"]["status"] == "blocked"
    assert response_intake_payload["checksum_policy"]["status"] == "blocked"
    assert response_intake_payload["redaction_policy"]["status"] == "blocked"
    assert response_intake_payload["parser_selection"]["status"] == "blocked"
    assert response_intake_payload["validation_queue"]["status"] == "blocked"
    assert response_intake_payload["promotion_gate"]["status"] == "blocked"
    assert response_intake_payload["audit_trail"]["status"] == "blocked"
    assert response_intake_payload["response_channel_open"] is False
    assert response_intake_payload["raw_output_location_materialized"] is False
    assert response_intake_payload["parser_selected"] is False
    assert response_intake_payload["validation_enqueued"] is False
    assert response_intake_payload["promotion_allowed"] is False
    assert response_intake_payload["raw_output_captured"] is False
    assert response_intake_payload["parsed_payload_generated"] is False
    assert response_intake_payload["promoted_to_proposals"] is False
    quarantine_payload = json.loads(
        (
            tmp_path
            / ".artist-portrait"
            / "data"
            / "proposal_provider_output_quarantine.json"
        ).read_text(encoding="utf-8")
    )
    assert quarantine_payload["status"] == "blocked"
    assert quarantine_payload["raw_output_captured"] is False
    assert quarantine_payload["promoted_to_proposals"] is False
    assert quarantine_payload["validation_performed"] is False
    response_validation_payload = json.loads(
        (
            tmp_path
            / ".artist-portrait"
            / "data"
            / "proposal_provider_response_validation_plan.json"
        ).read_text(encoding="utf-8")
    )
    assert response_validation_payload["status"] == "blocked"
    assert response_validation_payload["quarantine_input_binding"]["status"] == "blocked"
    assert response_validation_payload["content_type_check"]["status"] == "blocked"
    assert response_validation_payload["size_limit_check"]["status"] == "blocked"
    assert response_validation_payload["checksum_verification"]["status"] == "blocked"
    assert response_validation_payload["redaction_verification"]["status"] == "blocked"
    assert response_validation_payload["parser_contract"]["status"] == "blocked"
    assert response_validation_payload["json_syntax_validation"]["status"] == "blocked"
    assert response_validation_payload["schema_validation"]["status"] == "blocked"
    assert response_validation_payload["semantic_validation"]["status"] == "blocked"
    assert response_validation_payload["promotion_decision"]["status"] == "blocked"
    assert response_validation_payload["raw_output_read"] is False
    assert response_validation_payload["parsed_payload_generated"] is False
    assert response_validation_payload["validation_performed"] is False
    assert response_validation_payload["promoted_to_proposals"] is False
    promotion_payload = json.loads(
        (
            tmp_path
            / ".artist-portrait"
            / "data"
            / "proposal_promotion_authorization_plan.json"
        ).read_text(encoding="utf-8")
    )
    assert promotion_payload["status"] == "blocked"
    assert promotion_payload["validation_report_binding"]["status"] == "blocked"
    assert promotion_payload["schema_validation_requirement"]["status"] == "blocked"
    assert promotion_payload["semantic_validation_requirement"]["status"] == "blocked"
    assert promotion_payload["evidence_validation_requirement"]["status"] == "blocked"
    assert promotion_payload["risk_acceptance_requirement"]["status"] == "blocked"
    assert promotion_payload["proposal_identity_requirement"]["status"] == "blocked"
    assert promotion_payload["overwrite_policy"]["status"] == "blocked"
    assert promotion_payload["atomic_write_policy"]["status"] == "blocked"
    assert promotion_payload["provenance_binding"]["status"] == "blocked"
    assert promotion_payload["final_promotion_authorization"]["status"] == "blocked"
    assert promotion_payload["promotion_authorized"] is False
    assert promotion_payload["promotion_performed"] is False
    assert promotion_payload["proposals_file_written"] is False
    promotion_report_payload = json.loads(
        (
            tmp_path
            / ".artist-portrait"
            / "data"
            / "proposal_promotion_validation_report.json"
        ).read_text(encoding="utf-8")
    )
    assert promotion_report_payload["status"] == "blocked"
    assert promotion_report_payload["input_binding_check"]["performed"] is False
    assert promotion_report_payload["schema_result_check"]["passed"] is False
    assert promotion_report_payload["semantic_result_check"]["passed"] is False
    assert promotion_report_payload["evidence_traceability_check"]["passed"] is False
    assert promotion_report_payload["risk_result_check"]["passed"] is False
    assert promotion_report_payload["proposal_identity_check"]["passed"] is False
    assert promotion_report_payload["overwrite_conflict_check"]["passed"] is False
    assert promotion_report_payload["atomic_write_readiness_check"]["passed"] is False
    assert promotion_report_payload["provenance_integrity_check"]["passed"] is False
    assert promotion_report_payload["final_authorization_check"]["passed"] is False
    assert promotion_report_payload["overall_passed"] is False
    assert promotion_report_payload["promotion_recommended"] is False
    transaction_payload = json.loads(
        (
            tmp_path / ".artist-portrait" / "data" / "proposal_canonical_write_transaction_plan.json"
        ).read_text(encoding="utf-8")
    )
    assert transaction_payload["status"] == "blocked"
    assert transaction_payload["transaction_started"] is False
    assert transaction_payload["transaction_committed"] is False
    assert transaction_payload["rollback_performed"] is False
    assert transaction_payload["proposals_file_written"] is False
    result_payload = json.loads(
        (
            tmp_path / ".artist-portrait" / "data" / "proposal_provider_result.json"
        ).read_text(encoding="utf-8")
    )
    assert result_payload["status"] == "blocked"
    assert result_payload["payload_generated"] is False
    assert result_payload["validation_performed"] is False
    assert result_payload["model_call_performed"] is False
    assert result_payload["network_performed"] is False
    assert result_payload["proposal_content_generated"] is False
    assert not (tmp_path / ".artist-portrait" / "data" / "proposals.json").exists()
    assert not (tmp_path / "output" / "proposals.md").exists()


def test_invalid_proposals_json_status_and_doctor(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    proposals_path = tmp_path / ".artist-portrait" / "data" / "proposals.json"
    proposals_path.write_text('{"proposal_set_id": "missing-required-fields"}\n', encoding="utf-8")

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)

    assert code == 0
    assert status_payload["summaries"]["proposals"]["valid"] is False
    assert "invalid ProposalSet JSON" in status_payload["summaries"]["proposals"]["error"]

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(issue["code"] == "proposals_invalid" for issue in doctor_payload["issues"])


def test_invalid_proposal_context_status_and_doctor(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    context_path = tmp_path / ".artist-portrait" / "data" / "proposal_context.json"
    context_path.write_text('{"context_id": "missing-required-fields"}\n', encoding="utf-8")

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)

    assert code == 0
    assert status_payload["summaries"]["proposal_context"]["valid"] is False
    assert (
        "invalid ProposalContext JSON"
        in status_payload["summaries"]["proposal_context"]["error"]
    )

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(
        issue["code"] == "proposal_context_invalid"
        for issue in doctor_payload["issues"]
    )


def test_invalid_text_model_gate_status_and_doctor(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    gate_path = tmp_path / ".artist-portrait" / "data" / "text_model_gate.json"
    gate_path.write_text('{"gate_id": "missing-required-fields"}\n', encoding="utf-8")

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)

    assert code == 0
    assert status_payload["summaries"]["text_model_gate"]["valid"] is False
    assert (
        "invalid TextModelGate JSON"
        in status_payload["summaries"]["text_model_gate"]["error"]
    )

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(
        issue["code"] == "text_model_gate_invalid"
        for issue in doctor_payload["issues"]
    )


def test_invalid_proposal_request_status_and_doctor(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    request_path = tmp_path / ".artist-portrait" / "data" / "proposal_request.json"
    request_path.write_text('{"request_id": "missing-required-fields"}\n', encoding="utf-8")

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)

    assert code == 0
    assert status_payload["summaries"]["proposal_request"]["valid"] is False
    assert (
        "invalid ProposalRequestPacket JSON"
        in status_payload["summaries"]["proposal_request"]["error"]
    )

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(
        issue["code"] == "proposal_request_invalid"
        for issue in doctor_payload["issues"]
    )


def test_invalid_proposal_adapter_check_status_and_doctor(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    check_path = tmp_path / ".artist-portrait" / "data" / "proposal_adapter_check.json"
    check_path.write_text('{"check_id": "missing-required-fields"}\n', encoding="utf-8")

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)

    assert code == 0
    assert status_payload["summaries"]["proposal_adapter_check"]["valid"] is False
    assert (
        "invalid ProposalAdapterCheck JSON"
        in status_payload["summaries"]["proposal_adapter_check"]["error"]
    )

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(
        issue["code"] == "proposal_adapter_check_invalid"
        for issue in doctor_payload["issues"]
    )


def test_invalid_proposal_provider_registry_status_and_doctor(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    registry_path = tmp_path / ".artist-portrait" / "data" / "proposal_provider_registry.json"
    registry_path.write_text('{"registry_id": "missing-required-fields"}\n', encoding="utf-8")

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)

    assert code == 0
    assert status_payload["summaries"]["proposal_provider_registry"]["valid"] is False
    assert (
        "invalid ProposalProviderRegistry JSON"
        in status_payload["summaries"]["proposal_provider_registry"]["error"]
    )

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(
        issue["code"] == "proposal_provider_registry_invalid"
        for issue in doctor_payload["issues"]
    )


def test_invalid_proposal_mock_adapter_handshake_status_and_doctor(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    handshake_path = (
        tmp_path / ".artist-portrait" / "data" / "proposal_mock_adapter_handshake.json"
    )
    handshake_path.write_text('{"handshake_id": "missing-required-fields"}\n', encoding="utf-8")

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)

    assert code == 0
    assert status_payload["summaries"]["proposal_mock_adapter_handshake"]["valid"] is False
    assert (
        "invalid ProposalMockAdapterHandshake JSON"
        in status_payload["summaries"]["proposal_mock_adapter_handshake"]["error"]
    )

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(
        issue["code"] == "proposal_mock_adapter_handshake_invalid"
        for issue in doctor_payload["issues"]
    )


def test_invalid_proposal_execution_authorization_status_and_doctor(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    authorization_path = (
        tmp_path / ".artist-portrait" / "data" / "proposal_execution_authorization.json"
    )
    authorization_path.write_text(
        '{"authorization_id": "missing-required-fields"}\n',
        encoding="utf-8",
    )

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)

    assert code == 0
    assert (
        status_payload["summaries"]["proposal_execution_authorization"]["valid"]
        is False
    )
    assert (
        "invalid ProposalExecutionAuthorization JSON"
        in status_payload["summaries"]["proposal_execution_authorization"]["error"]
    )

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(
        issue["code"] == "proposal_execution_authorization_invalid"
        for issue in doctor_payload["issues"]
    )


def test_invalid_proposal_execution_approval_request_status_and_doctor(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    approval_path = (
        tmp_path / ".artist-portrait" / "data" / "proposal_execution_approval_request.json"
    )
    approval_path.write_text(
        '{"approval_request_id": "missing-required-fields"}\n',
        encoding="utf-8",
    )

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)

    assert code == 0
    assert (
        status_payload["summaries"]["proposal_execution_approval_request"]["valid"]
        is False
    )
    assert (
        "invalid ProposalExecutionApprovalRequest JSON"
        in status_payload["summaries"]["proposal_execution_approval_request"]["error"]
    )

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(
        issue["code"] == "proposal_execution_approval_request_invalid"
        for issue in doctor_payload["issues"]
    )


def test_invalid_proposal_execution_approval_record_status_and_doctor(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    approval_record_path = (
        tmp_path / ".artist-portrait" / "data" / "proposal_execution_approval_record.json"
    )
    approval_record_path.write_text(
        '{"approval_record_id": "missing-required-fields"}\n',
        encoding="utf-8",
    )

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)

    assert code == 0
    assert (
        status_payload["summaries"]["proposal_execution_approval_record"]["valid"]
        is False
    )
    assert (
        "invalid ProposalExecutionApprovalRecord JSON"
        in status_payload["summaries"]["proposal_execution_approval_record"]["error"]
    )

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(
        issue["code"] == "proposal_execution_approval_record_invalid"
        for issue in doctor_payload["issues"]
    )


def test_invalid_proposal_execution_readiness_plan_status_and_doctor(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    readiness_path = (
        tmp_path / ".artist-portrait" / "data" / "proposal_execution_readiness_plan.json"
    )
    readiness_path.write_text(
        '{"readiness_plan_id": "missing-required-fields"}\n',
        encoding="utf-8",
    )

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)

    assert code == 0
    assert (
        status_payload["summaries"]["proposal_execution_readiness_plan"]["valid"]
        is False
    )
    assert (
        "invalid ProposalExecutionReadinessPlan JSON"
        in status_payload["summaries"]["proposal_execution_readiness_plan"]["error"]
    )

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(
        issue["code"] == "proposal_execution_readiness_plan_invalid"
        for issue in doctor_payload["issues"]
    )


def test_invalid_proposal_execution_input_bundle_status_and_doctor(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    input_bundle_path = (
        tmp_path / ".artist-portrait" / "data" / "proposal_execution_input_bundle.json"
    )
    input_bundle_path.write_text(
        '{"bundle_id": "missing-required-fields"}\n',
        encoding="utf-8",
    )

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)

    assert code == 0
    assert (
        status_payload["summaries"]["proposal_execution_input_bundle"]["valid"]
        is False
    )
    assert (
        "invalid ProposalExecutionInputBundle JSON"
        in status_payload["summaries"]["proposal_execution_input_bundle"]["error"]
    )

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(
        issue["code"] == "proposal_execution_input_bundle_invalid"
        for issue in doctor_payload["issues"]
    )


def test_invalid_proposal_provider_call_dry_run_status_and_doctor(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    call_dry_run_path = (
        tmp_path / ".artist-portrait" / "data" / "proposal_provider_call_dry_run.json"
    )
    call_dry_run_path.write_text(
        '{"dry_run_id": "missing-required-fields"}\n',
        encoding="utf-8",
    )

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)

    assert code == 0
    assert (
        status_payload["summaries"]["proposal_provider_call_dry_run"]["valid"]
        is False
    )
    assert (
        "invalid ProposalProviderCallDryRun JSON"
        in status_payload["summaries"]["proposal_provider_call_dry_run"]["error"]
    )

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(
        issue["code"] == "proposal_provider_call_dry_run_invalid"
        for issue in doctor_payload["issues"]
    )


def test_invalid_proposal_provider_response_intake_plan_status_and_doctor(
    tmp_path,
    capsys,
):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    response_intake_path = (
        tmp_path
        / ".artist-portrait"
        / "data"
        / "proposal_provider_response_intake_plan.json"
    )
    response_intake_path.write_text(
        '{"intake_id": "missing-required-fields"}\n',
        encoding="utf-8",
    )

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)

    assert code == 0
    assert (
        status_payload["summaries"]["proposal_provider_response_intake_plan"]["valid"]
        is False
    )
    assert (
        "invalid ProposalProviderResponseIntakePlan JSON"
        in status_payload["summaries"]["proposal_provider_response_intake_plan"]["error"]
    )

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(
        issue["code"] == "proposal_provider_response_intake_plan_invalid"
        for issue in doctor_payload["issues"]
    )


def test_invalid_proposal_provider_output_quarantine_status_and_doctor(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    quarantine_path = (
        tmp_path / ".artist-portrait" / "data" / "proposal_provider_output_quarantine.json"
    )
    quarantine_path.write_text(
        '{"quarantine_id": "missing-required-fields"}\n',
        encoding="utf-8",
    )

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)

    assert code == 0
    assert (
        status_payload["summaries"]["proposal_provider_output_quarantine"]["valid"]
        is False
    )
    assert (
        "invalid ProposalProviderOutputQuarantine JSON"
        in status_payload["summaries"]["proposal_provider_output_quarantine"]["error"]
    )

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(
        issue["code"] == "proposal_provider_output_quarantine_invalid"
        for issue in doctor_payload["issues"]
    )


def test_invalid_proposal_provider_response_validation_plan_status_and_doctor(
    tmp_path,
    capsys,
):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    response_validation_path = (
        tmp_path
        / ".artist-portrait"
        / "data"
        / "proposal_provider_response_validation_plan.json"
    )
    response_validation_path.write_text(
        '{"validation_plan_id": "missing-required-fields"}\n',
        encoding="utf-8",
    )

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)

    assert code == 0
    assert (
        status_payload["summaries"]["proposal_provider_response_validation_plan"][
            "valid"
        ]
        is False
    )
    assert (
        "invalid ProposalProviderResponseValidationPlan JSON"
        in status_payload["summaries"][
            "proposal_provider_response_validation_plan"
        ]["error"]
    )

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(
        issue["code"] == "proposal_provider_response_validation_plan_invalid"
        for issue in doctor_payload["issues"]
    )


def test_invalid_proposal_promotion_authorization_plan_status_and_doctor(
    tmp_path,
    capsys,
):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    promotion_path = (
        tmp_path
        / ".artist-portrait"
        / "data"
        / "proposal_promotion_authorization_plan.json"
    )
    promotion_path.write_text(
        '{"promotion_plan_id": "missing-required-fields"}\n',
        encoding="utf-8",
    )

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)

    assert code == 0
    assert (
        status_payload["summaries"]["proposal_promotion_authorization_plan"]["valid"]
        is False
    )
    assert (
        "invalid ProposalPromotionAuthorizationPlan JSON"
        in status_payload["summaries"]["proposal_promotion_authorization_plan"]["error"]
    )

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(
        issue["code"] == "proposal_promotion_authorization_plan_invalid"
        for issue in doctor_payload["issues"]
    )


def test_invalid_proposal_promotion_validation_report_status_and_doctor(
    tmp_path,
    capsys,
):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    report_path = (
        tmp_path
        / ".artist-portrait"
        / "data"
        / "proposal_promotion_validation_report.json"
    )
    report_path.write_text(
        '{"report_id": "missing-required-fields"}\n',
        encoding="utf-8",
    )

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)

    assert code == 0
    assert (
        status_payload["summaries"]["proposal_promotion_validation_report"]["valid"]
        is False
    )
    assert (
        "invalid ProposalPromotionValidationReport JSON"
        in status_payload["summaries"]["proposal_promotion_validation_report"]["error"]
    )

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(
        issue["code"] == "proposal_promotion_validation_report_invalid"
        for issue in doctor_payload["issues"]
    )


def test_invalid_proposal_canonical_write_transaction_plan_status_and_doctor(
    tmp_path,
    capsys,
):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(project_fixture_with_scene_detection("off"), encoding="utf-8")
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    transaction_path = (
        tmp_path / ".artist-portrait" / "data" / "proposal_canonical_write_transaction_plan.json"
    )
    transaction_path.write_text(
        '{"transaction_plan_id": "missing-required-fields"}\n',
        encoding="utf-8",
    )

    assert main(["status", "--project", str(project_path), "--json"]) == 0
    status_payload = json.loads(capsys.readouterr().out)
    summary = status_payload["summaries"]["proposal_canonical_write_transaction_plan"]
    assert summary["valid"] is False
    assert "invalid ProposalCanonicalWriteTransactionPlan JSON" in summary["error"]

    assert main(["doctor", "--project", str(project_path), "--json"]) == 1
    doctor_payload = json.loads(capsys.readouterr().out)
    assert any(
        issue["code"] == "proposal_canonical_write_transaction_plan_invalid"
        for issue in doctor_payload["issues"]
    )


def test_invalid_proposal_provider_result_status_and_doctor(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    result_path = tmp_path / ".artist-portrait" / "data" / "proposal_provider_result.json"
    result_path.write_text('{"result_id": "missing-required-fields"}\n', encoding="utf-8")

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)

    assert code == 0
    assert status_payload["summaries"]["proposal_provider_result"]["valid"] is False
    assert (
        "invalid ProposalProviderResultEnvelope JSON"
        in status_payload["summaries"]["proposal_provider_result"]["error"]
    )

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(
        issue["code"] == "proposal_provider_result_invalid"
        for issue in doctor_payload["issues"]
    )


def test_proposal_adapter_check_rejects_plaintext_secret_material(
    tmp_path,
    monkeypatch,
    capsys,
):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_remote_text_model_allowed()
        .replace("scene_detection: auto", "scene_detection: off")
        + "\n# OPENAI_API_KEY=sk-proj-test-secret\n",
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0
    assert main(["analyze", "--project", str(project_path), "--quiet"]) == 0
    assert main(["map", "--project", str(project_path), "--quiet"]) == 0
    monkeypatch.setattr(
        workspace,
        "detect_capabilities",
        lambda: Capabilities(text_model=True),
    )

    code = main(["propose", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 1
    assert payload["status"] == "blocked"
    adapter_payload = json.loads(
        (
            tmp_path / ".artist-portrait" / "data" / "proposal_adapter_check.json"
        ).read_text(encoding="utf-8")
    )
    issue_codes = {issue["code"] for issue in adapter_payload["issues"]}
    assert adapter_payload["status"] == "blocked"
    assert "plaintext_secret_material_detected" in issue_codes
    assert adapter_payload["model_call_performed"] is False
    assert adapter_payload["network_performed"] is False


def test_review_project_requires_scan_first(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)

    code = main(["review", "--project", str(project_path), "--scope", "project"])
    captured = capsys.readouterr()

    assert code == 7
    assert "review --scope project requires scan" in captured.err


def test_review_proposal_requires_context_and_proposals(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)

    code = main(["review", "--project", str(project_path), "--scope", "proposal"])
    captured = capsys.readouterr()

    assert code == 7
    assert "requires propose to prepare proposal context" in captured.err


def test_review_timeline_requires_generated_timeline(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    code = main(["review", "--project", str(project_path), "--scope", "timeline"])
    captured = capsys.readouterr()

    assert code == 7
    assert "requires timeline generation first" in captured.err


def test_timeline_generates_selected_proposal_canonical_draft(tmp_path, capsys):
    project_path = build_valid_proposal_project(tmp_path, capsys)

    code = main(
        [
            "timeline",
            "--project",
            str(project_path),
            "--proposal",
            "proposal_advanced",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code in (0, 1)
    assert payload["proposal"] == "proposal_advanced"
    assert payload["output"] == "output/timeline_draft.json"
    timeline = json.loads(
        (tmp_path / "output" / "timeline_draft.json").read_text(encoding="utf-8")
    )
    assert timeline["proposal_id"] == "proposal_advanced"
    assert timeline["segments"][0]["clip_id"]
    assert timeline["segments"][0]["timeline_start"] == 0.0
    assert timeline["music_plan"]["status"] == "unresolved"
    assert timeline["music_plan"]["input_mode"] == "none_yet"
    assert timeline["music_plan"]["selection_performed"] is False
    assert timeline["music_plan"]["beat_analysis_performed"] is False
    assert timeline["music_plan"]["fitting_performed"] is False
    assert set(timeline["music_plan"]["future_input_modes"]) == {
        "direct_audio",
        "video_audio_extract",
        "source_embedded_audio",
        "multiple_candidates",
        "none_yet",
    }


def test_timeline_is_deterministic_and_reviewable(tmp_path, capsys):
    project_path = build_valid_proposal_project(tmp_path, capsys)
    command = [
        "timeline",
        "--project",
        str(project_path),
        "--proposal",
        "proposal_safe",
        "--quiet",
    ]
    assert main(command) in (0, 1)
    first = (tmp_path / "output" / "timeline_draft.json").read_bytes()
    assert main(command) in (0, 1)
    second = (tmp_path / "output" / "timeline_draft.json").read_bytes()
    assert first == second

    assert (
        main(
            [
                "review",
                "--project",
                str(project_path),
                "--scope",
                "timeline",
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["issues"] == []
    assert payload["validation"] == ".artist-portrait/data/timeline_validation.json"
    assert (tmp_path / "output" / "timeline_review.md").exists()


def test_timeline_respects_allow_music_false(tmp_path, capsys):
    project_path = build_valid_proposal_project(tmp_path, capsys, allow_music=False)

    assert (
        main(
            [
                "timeline",
                "--project",
                str(project_path),
                "--proposal",
                "proposal_risky",
                "--quiet",
            ]
        )
        in (0, 1)
    )
    timeline = json.loads(
        (tmp_path / "output" / "timeline_draft.json").read_text(encoding="utf-8")
    )
    assert timeline["music_plan"]["status"] == "disabled_by_policy"
    assert timeline["music_plan"]["input_mode"] == "disabled_by_policy"


def test_timeline_requires_validated_canonical_proposal(tmp_path, capsys):
    project_path = build_blocked_proposal_chain(tmp_path, capsys)
    write_proposals_from_context(tmp_path)

    code = main(
        [
            "timeline",
            "--project",
            str(project_path),
            "--proposal",
            "proposal_safe",
        ]
    )

    assert code == 7
    assert "validated canonical proposal import" in capsys.readouterr().err


def test_timeline_status_doctor_and_invalid_json_diagnostics(tmp_path, capsys):
    project_path = build_valid_proposal_project(tmp_path, capsys)
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
    assert main(["status", "--project", str(project_path), "--json"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["summaries"]["timeline"]["valid"] is True
    assert status["steps"]["timeline"]["status"] in {
        "completed",
        "completed_with_warnings",
    }

    (tmp_path / "output" / "timeline_draft.json").write_text("{broken", encoding="utf-8")
    assert main(["doctor", "--project", str(project_path), "--json"]) == 1
    doctor = json.loads(capsys.readouterr().out)
    assert "timeline_invalid" in {issue["code"] for issue in doctor["issues"]}


def test_new_canonical_proposals_invalidate_existing_timeline(tmp_path, capsys):
    project_path = build_valid_proposal_project(tmp_path, capsys)
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
    candidate = tmp_path / "proposal_candidate_v2.json"
    payload = json.loads(
        (tmp_path / ".artist-portrait" / "data" / "proposals.json").read_text(
            encoding="utf-8"
        )
    )
    payload["proposal_set_id"] = "proposal_set_test_v2"
    candidate.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
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
        == 0
    )
    assert main(["status", "--project", str(project_path), "--json"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["steps"]["timeline"]["status"] == "invalidated"
    assert status["steps"]["review_timeline"]["status"] == "invalidated"


def test_bgm_cli_import_list_fit_and_status(tmp_path, capsys):
    project_path = build_valid_proposal_project(tmp_path, capsys)
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
    audio = tmp_path / "media" / "bgm.wav"
    audio.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            str(audio),
        ],
        check=True,
    )
    assert (
        main(
            [
                "bgm", "import", "--project", str(project_path),
                "--file", "media/bgm.wav", "--rights-status", "owned", "--json",
            ]
        )
        == 1
    )
    imported = json.loads(capsys.readouterr().out)
    candidate_id = imported["candidate"]["music_candidate_id"]
    assert imported["candidate"]["beat_analysis_status"] == "unavailable"

    assert (
        main(
            [
                "bgm", "analyze", "--project", str(project_path),
                "--window-seconds", "0.5", "--json",
            ]
        )
        == 1
    )
    analyzed = json.loads(capsys.readouterr().out)
    assert analyzed["analysis"]["analysis_engine"] == "local_pcm_energy_v1"
    assert analyzed["analysis"]["beat_engine_capabilities"]
    assert analyzed["analysis"]["automatic_music_selection"] is False
    assert analyzed["report"] == "output/bgm_analysis_report.md"

    assert (
        main(
            [
                "bgm", "fit", "--project", str(project_path),
                "--candidate", candidate_id,
                "--fit-mode", "loop",
                "--fade-in-seconds", "0.2",
                "--fade-out-seconds", "0.4",
                "--target-gain-db", "-7",
                "--ducking-gain-db", "-11",
                "--beat-align",
                "--json",
            ]
        )
        == 1
    )
    fitted = json.loads(capsys.readouterr().out)
    assert fitted["fit"]["music_candidate_id"] == candidate_id
    assert fitted["fit"]["beat_alignment_status"] == "unavailable"
    assert fitted["fit"]["controls"]["control_policy"] == "explicit_cli_v1"
    assert fitted["fit"]["controls"]["requested_fit_mode"] == "loop"
    assert fitted["fit"]["controls"]["fade_in_seconds"] == 0.2
    assert fitted["fit"]["controls"]["target_gain_db"] == -7
    assert fitted["fit"]["controls"]["ducking_gain_db"] == -11
    assert fitted["fit"]["controls"]["beat_alignment_requested"] is True
    assert fitted["fit"]["analysis_ref"] == ".artist-portrait/data/bgm_analysis.json"
    assert fitted["fit"]["energy_alignment_status"] == "analysis_used"
    timeline = json.loads(
        (tmp_path / "output" / "timeline_draft.json").read_text(encoding="utf-8")
    )
    assert timeline["music_plan"]["status"] == "fitted"
    assert timeline["music_plan"]["candidate_id"] == candidate_id
    assert main(["status", "--project", str(project_path), "--json"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["summaries"]["bgm_candidates"]["count"] == 1
    assert status["summaries"]["bgm_analysis"]["candidate_count"] == 1
    assert status["summaries"]["bgm_analysis"]["beat_completed_count"] == 0


def test_rhythm_cli_plans_bgm_edit_rhythm_without_mutating_outputs(tmp_path, capsys):
    project_path = build_valid_proposal_project(tmp_path, capsys)
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
    capsys.readouterr()
    audio = tmp_path / "media" / "rhythm_bgm.wav"
    audio.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "sine=frequency=330:duration=2",
            str(audio),
        ],
        check=True,
    )
    assert (
        main(
            [
                "bgm", "import", "--project", str(project_path),
                "--file", "media/rhythm_bgm.wav", "--rights-status", "owned", "--json",
            ]
        )
        == 1
    )
    candidate_id = json.loads(capsys.readouterr().out)["candidate"]["music_candidate_id"]
    assert (
        main(["bgm", "analyze", "--project", str(project_path), "--json"])
        == 1
    )
    capsys.readouterr()
    assert (
        main(
            [
                "bgm", "fit", "--project", str(project_path),
                "--candidate", candidate_id,
                "--fit-mode", "loop",
                "--fade-in-seconds", "0.2",
                "--fade-out-seconds", "0.3",
                "--ducking-gain-db", "-10",
                "--beat-align",
                "--json",
            ]
        )
        == 1
    )
    capsys.readouterr()
    intent_path = tmp_path / "rhythm_intent.json"
    intent_path.write_text(
        json.dumps(
            {
                "intent_id": "speech_first_medium_text",
                "mode": "speech_first",
                "pacing": "medium",
                "text_density": "medium",
                "transition_style": "smooth",
                "ending_style": "fade_out",
                "notes": "test explicit rhythm intent",
                "model_call_performed_by_cli": False,
                "network_performed": False,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    assert (
        main(
            [
                "rhythm",
                "--project",
                str(project_path),
                "--intent",
                str(intent_path),
                "--json",
            ]
        )
        == 1
    )
    payload = json.loads(capsys.readouterr().out)
    plan = payload["rhythm_plan"]
    assert payload["output"] == ".artist-portrait/data/rhythm_plan.json"
    assert payload["report"] == "output/rhythm_report.md"
    assert payload["handoff"] == "output/rhythm_agent_handoff.json"
    assert plan["intent"]["mode"] == "speech_first"
    assert plan["timeline_profile"]["metrics"]
    assert plan["bgm_profile"]["metrics"]
    assert plan["compatibility_audit"]["domain_id"] == "compatibility_audit"
    assert plan["cut_cue_audit"]["status"] == "unavailable"
    assert plan["transition_audit"]["domain_id"] == "transition_audit"
    assert plan["text_audit"]["domain_id"] == "text_audit"
    assert plan["ducking_silence_audit"]["domain_id"] == "ducking_silence_audit"
    assert plan["ending_audit"]["domain_id"] == "ending_audit"
    assert plan["edit_points_moved"] is False
    assert plan["automatic_music_selection"] is False
    assert plan["media_rendered"] is False
    assert plan["model_call_performed_by_cli"] is False
    assert plan["network_performed"] is False
    assert (tmp_path / ".artist-portrait" / "data" / "rhythm_plan.json").exists()
    assert (tmp_path / "output" / "rhythm_report.md").exists()
    assert (tmp_path / "output" / "rhythm_agent_handoff.json").exists()

    agent_candidate_path = tmp_path / "rhythm_candidate.json"
    agent_candidate_path.write_text(
        json.dumps(
            {
                "candidate_id": "rhythm_candidate_safe",
                "project_id": plan["project_id"],
                "timeline_id": plan["timeline_id"],
                "rhythm_plan_id": plan["rhythm_plan_id"],
                "recommendations": ["Keep speech-first pacing and avoid moving cuts."],
                "rejected_automatic_actions": ["move edit points", "select music"],
                "model_call_performed_by_cli": False,
                "network_performed": False,
                "edit_points_moved": False,
                "music_selected": False,
                "media_rendered": False,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    assert (
        main(
            [
                "rhythm",
                "--project",
                str(project_path),
                "--intent",
                str(intent_path),
                "--agent-output",
                str(agent_candidate_path),
                "--json",
            ]
        )
        == 1
    )
    imported = json.loads(capsys.readouterr().out)["rhythm_plan"]
    assert imported["agent_candidate_audit"]["status"] == "passed"
    assert imported["agent_candidate_audit"]["metrics"][0]["metric_id"] == "recommendation_count"
    assert (
        main(
            [
                "rhythm",
                "--project",
                str(project_path),
                "--repair-plan",
                "--acceptance-profile",
                "delivery",
                "--json",
            ]
        )
        == 9
    )
    repair_payload = json.loads(capsys.readouterr().out)
    repair = repair_payload["rhythm_repair_plan"]
    assert repair_payload["output"] == ".artist-portrait/data/rhythm_repair_plan.json"
    assert repair_payload["report"] == "output/rhythm_repair_plan.md"
    assert repair_payload["handoff"] == "output/rhythm_repair_handoff.json"
    assert repair["commands_executed"] is False
    assert repair["media_rendered"] is False
    assert repair["edit_points_moved"] is False
    assert repair["automatic_music_selection"] is False
    assert repair["model_call_performed_by_cli"] is False
    assert repair["network_performed"] is False
    assert repair["required_action_count"] >= 3
    assert repair["first_required_command"] == "artist-portrait preview --project <project.yaml>"
    assert {
        action["category"]
        for action in repair["actions"]
        if action["severity"] == "required"
    } >= {"preview", "final_export", "rhythm_qc"}
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc=size=64x64:rate=24:duration=2",
            "-f", "lavfi", "-i", "sine=frequency=220:duration=2",
            "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(tmp_path / "media" / "clean.mp4"),
        ],
        check=True,
    )
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
    capsys.readouterr()
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
    capsys.readouterr()
    assert main(["rhythm", "--project", str(project_path), "--qc", "--json"]) in (0, 1)
    qc = json.loads(capsys.readouterr().out)["rhythm_media_qc"]
    assert qc["preview_binding"]["domain_id"] == "preview_binding"
    assert qc["final_export_binding"]["domain_id"] == "final_export_binding"
    assert qc["timeline_freshness"]["domain_id"] == "timeline_freshness"
    assert qc["bgm_freshness"]["domain_id"] == "bgm_freshness"
    assert qc["preview_duration_qc"]["domain_id"] == "preview_duration_qc"
    assert qc["final_duration_qc"]["domain_id"] == "final_duration_qc"
    assert qc["audio_expectation_qc"]["domain_id"] == "audio_expectation_qc"
    assert qc["ducking_render_qc"]["domain_id"] == "ducking_render_qc"
    assert qc["ending_render_qc"]["domain_id"] == "ending_render_qc"
    assert qc["media_qc_summary"]["domain_id"] == "media_qc_summary"
    assert qc["preview_rendered_by_qc"] is False
    assert qc["final_export_rendered_by_qc"] is False
    assert qc["edit_points_moved"] is False
    assert qc["automatic_music_selection"] is False
    assert qc["model_call_performed_by_cli"] is False
    assert qc["network_performed"] is False
    assert (tmp_path / ".artist-portrait" / "data" / "rhythm_media_qc.json").exists()
    assert (tmp_path / "output" / "rhythm_media_qc.md").exists()
    assert (tmp_path / "output" / "rhythm_media_qc_handoff.json").exists()
    assert (
        main(
            [
                "rhythm",
                "--project",
                str(project_path),
                "--repair-plan",
                "--acceptance-profile",
                "delivery",
                "--json",
            ]
        )
        in (0, 1, 9)
    )
    completed_repair = json.loads(capsys.readouterr().out)["rhythm_repair_plan"]
    assert completed_repair["commands_executed"] is False
    assert completed_repair["media_rendered"] is False
    assert completed_repair["edit_points_moved"] is False
    assert completed_repair["automatic_music_selection"] is False
    assert (tmp_path / ".artist-portrait" / "data" / "rhythm_repair_plan.json").exists()
    assert (tmp_path / "output" / "rhythm_repair_plan.md").exists()
    assert (tmp_path / "output" / "rhythm_repair_handoff.json").exists()
    assert main(["status", "--project", str(project_path), "--json"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["summaries"]["bgm_analysis"]["bpm_candidate_count"] == 0
    assert status["summaries"]["bgm_fit"]["candidate_id"] == candidate_id


def test_bgm_cli_recommend_handoff_and_import(tmp_path, capsys):
    project_path = build_valid_proposal_project(tmp_path, capsys)
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
    audio = tmp_path / "media" / "bgm.wav"
    audio.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            str(audio),
        ],
        check=True,
    )
    assert main(["bgm", "import", "--project", str(project_path), "--file", "media/bgm.wav", "--json"]) == 1
    candidate_id = json.loads(capsys.readouterr().out)["candidate"]["music_candidate_id"]
    assert main(["bgm", "analyze", "--project", str(project_path), "--json"]) == 1
    capsys.readouterr()
    assert main(["bgm", "recommend", "--project", str(project_path), "--json"]) == 1
    prepared = json.loads(capsys.readouterr().out)
    context = json.loads((tmp_path / prepared["context"]).read_text(encoding="utf-8"))
    recommendation = tmp_path / "recommendation.json"
    recommendation.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "recommendation_set_id": "bgmrec_cli",
                "project_id": context["project_id"],
                "context_id": context["context_id"],
                "method": "host_agent",
                "method_version": "test",
                "recommendations": [
                    {
                        "recommendation_id": "rec_001",
                        "music_candidate_id": candidate_id,
                        "rank": 1,
                        "fit_rationale": "fits the brief",
                        "timing_rationale": "fits the timeline",
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
        )
        + "\n",
        encoding="utf-8",
    )

    assert (
        main(
            [
                "bgm", "recommend", "--project", str(project_path),
                "--agent-output", str(recommendation), "--json",
            ]
        )
        == 0
    )
    imported = json.loads(capsys.readouterr().out)
    assert imported["output"] == ".artist-portrait/data/bgm_recommendations.json"
    assert imported["validation"]["valid"] is True
    assert (
        main(
            [
                "bgm", "select", "--project", str(project_path),
                "--recommendation-id", "rec_001", "--json",
            ]
        )
        == 1
    )
    selected = json.loads(capsys.readouterr().out)
    assert selected["selection"]["recommendation_id"] == "rec_001"
    assert selected["selection"]["explicit_user_selection"] is True
    assert selected["selection"]["automatic_selection_performed"] is False
    assert selected["fit"]["music_candidate_id"] == candidate_id
    assert (tmp_path / ".artist-portrait" / "data" / "bgm_recommendation_selection.json").exists()
    assert (tmp_path / ".artist-portrait" / "data" / "bgm_fit.json").exists()
    assert main(["bgm", "review", "--project", str(project_path), "--json"]) == 1
    reviewed = json.loads(capsys.readouterr().out)
    assert reviewed["output"] == ".artist-portrait/data/bgm_fit_review.json"
    assert reviewed["review"] == "output/bgm_fit_review.md"
    assert reviewed["status"] == "warning"
    assert {issue["code"] for issue in reviewed["issues"]} == {
        "preview_missing_after_fit",
        "final_export_missing_after_fit",
    }
    assert main(["status", "--project", str(project_path), "--json"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["summaries"]["bgm_recommendation_selection"]["recommendation_id"] == "rec_001"
    assert status["summaries"]["bgm_fit"]["candidate_id"] == candidate_id
    assert status["steps"]["review_bgm"]["output_refs"] == [
        ".artist-portrait/data/bgm_fit_review.json",
        "output/bgm_fit_review.md",
    ]


@pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="preview CLI test requires ffmpeg and ffprobe",
)
def test_preview_cli_renders_review_media_from_timeline_and_bgm(tmp_path, capsys):
    project_path = build_valid_proposal_project(tmp_path, capsys)
    source_media = tmp_path / "media" / "clean.mp4"
    source_media.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc=size=64x64:rate=24:duration=2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source_media),
        ],
        check=True,
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
    audio = tmp_path / "media" / "preview-bgm.wav"
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "sine=frequency=330:duration=1",
            str(audio),
        ],
        check=True,
    )
    assert (
        main(
            [
                "bgm", "import", "--project", str(project_path),
                "--file", "media/preview-bgm.wav", "--rights-status", "owned", "--json",
            ]
        )
        == 1
    )
    candidate_id = json.loads(capsys.readouterr().out)["candidate"]["music_candidate_id"]
    assert (
        main(
            [
                "bgm", "fit", "--project", str(project_path),
                "--candidate", candidate_id, "--quiet",
            ]
        )
        in (0, 1)
    )

    code = main(["preview", "--project", str(project_path), "--width", "320", "--fps", "10", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert code in (0, 1)
    assert payload["output"] == "output/preview_lowres.mp4"
    assert payload["manifest"] == ".artist-portrait/data/preview_manifest.json"
    assert (tmp_path / "output" / "preview_lowres.mp4").exists()
    manifest = json.loads(
        (tmp_path / ".artist-portrait" / "data" / "preview_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["bgm_included"] is True
    assert manifest["requested_width"] == 320
    assert manifest["requested_fps"] == 10
    assert manifest["duration_delta_seconds"] == pytest.approx(0, abs=0.25)
    assert manifest["final_export"] is False
    assert manifest["network_performed"] is False

    assert main(["review", "--project", str(project_path), "--scope", "preview", "--json"]) == 0
    review_payload = json.loads(capsys.readouterr().out)
    assert review_payload["validation"] == ".artist-portrait/data/preview_validation.json"
    assert review_payload["issues"] == []

    assert main(["status", "--project", str(project_path), "--json"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["summaries"]["preview"]["bgm_included"] is True
    assert status["summaries"]["preview"]["requested_width"] == 320
    assert status["summaries"]["preview_validation"]["quality_status"] == "passed"

    manifest_path = tmp_path / ".artist-portrait" / "data" / "preview_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["expected_duration"] = 99
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    assert main(["doctor", "--project", str(project_path), "--json"]) == 1
    doctor = json.loads(capsys.readouterr().out)
    assert any(issue["code"] == "preview_duration_mismatch" for issue in doctor["issues"])
    assert status["steps"]["preview"]["status"] in ("completed", "completed_with_warnings")


def test_bgm_cli_respects_allow_music_false(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8").replace(
            "allow_music: true",
            "allow_music: false",
        ),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)

    code = main(
        [
            "bgm", "import", "--project", str(project_path),
            "--file", "media/unused.wav",
        ]
    )

    assert code == 9
    assert "allow_music" in capsys.readouterr().err


def test_acceptance_cli_reports_core_ready_with_delivery_gaps(tmp_path, capsys):
    project_path = build_valid_proposal_project(tmp_path, capsys)
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
    capsys.readouterr()

    assert main(["acceptance", "--project", str(project_path), "--json"]) == 1
    accepted = json.loads(capsys.readouterr().out)

    assert accepted["output"] == ".artist-portrait/data/acceptance_report.json"
    assert accepted["report"] == "output/acceptance_report.md"
    assert accepted["status"] == "warning"
    assert accepted["profile"] == "standard"
    assert accepted["profile_passed"] is True
    assert "preview" not in accepted["required_stage_ids"]
    assert accepted["core_ready"] is True
    assert accepted["preview_ready"] is False
    assert accepted["final_export_ready"] is False
    stages = {stage["stage_id"]: stage for stage in accepted["acceptance"]["stages"]}
    assert stages["proposal"]["status"] == "passed"
    assert stages["timeline"]["status"] == "passed"
    assert stages["rhythm_plan"]["status"] == "warning"
    assert stages["preview"]["status"] == "warning"
    assert stages["final_export"]["status"] == "warning"
    assert stages["rhythm_media_qc"]["status"] == "warning"
    assert (tmp_path / ".artist-portrait" / "data" / "acceptance_report.json").exists()
    assert (tmp_path / "output" / "acceptance_report.md").exists()


def test_acceptance_core_profile_passes_when_delivery_artifacts_are_missing(tmp_path, capsys):
    project_path = build_valid_proposal_project(tmp_path, capsys)
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
    capsys.readouterr()

    assert main(["acceptance", "--project", str(project_path), "--profile", "core", "--json"]) == 0
    accepted = json.loads(capsys.readouterr().out)

    assert accepted["status"] == "passed"
    assert accepted["profile"] == "core"
    assert accepted["profile_passed"] is True
    assert "timeline" in accepted["required_stage_ids"]
    assert "preview" not in accepted["required_stage_ids"]
    assert "final_export" not in accepted["required_stage_ids"]
    assert "rhythm_plan" not in accepted["required_stage_ids"]
    assert "rhythm_media_qc" not in accepted["required_stage_ids"]
    stages = {stage["stage_id"]: stage for stage in accepted["acceptance"]["stages"]}
    assert stages["rhythm_plan"]["status"] == "warning"
    assert stages["preview"]["status"] == "warning"
    assert stages["final_export"]["status"] == "warning"
    assert stages["rhythm_media_qc"]["status"] == "warning"


def test_acceptance_preview_profile_fails_when_preview_is_missing(tmp_path, capsys):
    project_path = build_valid_proposal_project(tmp_path, capsys)
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
    capsys.readouterr()

    assert main(["acceptance", "--project", str(project_path), "--profile", "preview", "--json"]) == 9
    accepted = json.loads(capsys.readouterr().out)

    assert accepted["status"] == "failed"
    assert accepted["profile"] == "preview"
    assert accepted["profile_passed"] is False
    assert "rhythm_plan" in accepted["required_stage_ids"]
    assert "preview" in accepted["required_stage_ids"]
    assert "rhythm_media_qc" in accepted["required_stage_ids"]
    assert "final_export" not in accepted["required_stage_ids"]


def test_acceptance_repair_plan_orders_required_profile_actions(tmp_path, capsys):
    project_path = build_valid_proposal_project(tmp_path, capsys)
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
    capsys.readouterr()

    assert (
        main(
            [
                "acceptance",
                "--project",
                str(project_path),
                "--profile",
                "preview",
                "--repair-plan",
                "--json",
            ]
        )
        == 9
    )
    accepted = json.loads(capsys.readouterr().out)

    plan = accepted["repair_plan"]
    assert accepted["repair_plan_output"] == ".artist-portrait/data/acceptance_repair_plan.json"
    assert accepted["repair_plan_report"] == "output/acceptance_repair_plan.md"
    assert plan["automatic_repair_performed"] is False
    assert plan["media_rendered"] is False
    assert plan["model_call_performed_by_cli"] is False
    assert plan["required_action_count"] == 3
    assert plan["blocked_stage_ids"] == ["preview", "rhythm_media_qc", "rhythm_plan"]
    assert plan["first_required_command"] == "artist-portrait rhythm --project <project.yaml>"
    required_actions = [action for action in plan["actions"] if action["required_for_profile"]]
    assert [action["stage_id"] for action in required_actions] == [
        "rhythm_plan",
        "preview",
        "rhythm_media_qc",
    ]
    assert [action["command"] for action in required_actions] == [
        "artist-portrait rhythm --project <project.yaml>",
        "artist-portrait preview --project <project.yaml>",
        "artist-portrait rhythm --project <project.yaml> --qc",
    ]
    assert (tmp_path / ".artist-portrait" / "data" / "acceptance_repair_plan.json").exists()
    assert (tmp_path / "output" / "acceptance_repair_plan.md").exists()


def test_acceptance_repair_plan_keeps_delivery_gaps_optional_for_core_profile(tmp_path, capsys):
    project_path = build_valid_proposal_project(tmp_path, capsys)
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
    capsys.readouterr()

    assert (
        main(
            [
                "acceptance",
                "--project",
                str(project_path),
                "--profile",
                "core",
                "--repair-plan",
                "--json",
            ]
        )
        == 0
    )
    accepted = json.loads(capsys.readouterr().out)

    plan = accepted["repair_plan"]
    assert accepted["status"] == "passed"
    assert plan["profile_passed"] is True
    assert plan["required_action_count"] == 0
    assert plan["optional_action_count"] >= 4
    assert plan["first_required_command"] is None
    assert all(action["required_for_profile"] is False for action in plan["actions"])


def test_acceptance_repair_approval_request_and_record_import(tmp_path, capsys):
    project_path = build_valid_proposal_project(tmp_path, capsys)
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
    capsys.readouterr()

    assert (
        main(
            [
                "acceptance",
                "--project",
                str(project_path),
                "--profile",
                "preview",
                "--approval-request",
                "--json",
            ]
        )
        == 9
    )
    accepted = json.loads(capsys.readouterr().out)
    request = accepted["approval_request"]
    plan = accepted["repair_plan"]
    assert accepted["approval_request_output"] == ".artist-portrait/data/acceptance_repair_approval_request.json"
    assert request["repair_plan_id"] == plan["repair_plan_id"]
    assert request["actions"][0]["decision"] == "pending"

    record_candidate = tmp_path / "approval_record_candidate.json"
    record_candidate.write_text(
        json.dumps(
            {
                "schema_version": "0.3",
                "approval_record_id": "candidate_record",
                "project_id": request["project_id"],
                "repair_plan_id": request["repair_plan_id"],
                "acceptance_profile": request["acceptance_profile"],
                "valid": False,
                "approved_action_ids": [],
                "rejected_action_ids": [],
                "issue_count": 0,
                "issues": [],
                "actions": [
                    {
                        **action,
                        "decision": "approved",
                        "rationale": "approve preview render for test",
                    }
                    for action in request["actions"]
                    if action["required_for_profile"]
                ],
                "network_performed": False,
                "model_call_performed_by_cli": False,
                "media_rendered": False,
                "automatic_repair_performed": False,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    assert (
        main(
            [
                "acceptance",
                "--project",
                str(project_path),
                "--profile",
                "preview",
                "--approval-record",
                str(record_candidate),
                "--json",
            ]
        )
        == 9
    )
    imported = json.loads(capsys.readouterr().out)
    record = imported["approval_record"]
    assert imported["approval_record_output"] == ".artist-portrait/data/acceptance_repair_approval_record.json"
    assert record["valid"] is True
    assert record["issue_count"] == 0
    required_action_ids = [
        action["action_id"]
        for action in request["actions"]
        if action["required_for_profile"]
    ]
    assert record["approved_action_ids"] == required_action_ids
    assert record["automatic_repair_performed"] is False
    assert record["media_rendered"] is False
    assert (tmp_path / ".artist-portrait" / "data" / "acceptance_repair_approval_record.json").exists()
    assert (tmp_path / "output" / "acceptance_repair_approval_record.md").exists()


def test_acceptance_repair_approval_record_rejects_missing_required_action(tmp_path, capsys):
    project_path = build_valid_proposal_project(tmp_path, capsys)
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
    capsys.readouterr()
    assert (
        main(
            [
                "acceptance",
                "--project",
                str(project_path),
                "--profile",
                "preview",
                "--approval-request",
                "--json",
            ]
        )
        == 9
    )
    request = json.loads(capsys.readouterr().out)["approval_request"]
    record_candidate = tmp_path / "approval_record_missing.json"
    record_candidate.write_text(
        json.dumps(
            {
                "schema_version": "0.3",
                "approval_record_id": "candidate_record_missing",
                "project_id": request["project_id"],
                "repair_plan_id": request["repair_plan_id"],
                "acceptance_profile": request["acceptance_profile"],
                "valid": False,
                "approved_action_ids": [],
                "rejected_action_ids": [],
                "issue_count": 0,
                "issues": [],
                "actions": [],
                "network_performed": False,
                "model_call_performed_by_cli": False,
                "media_rendered": False,
                "automatic_repair_performed": False,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    assert (
        main(
            [
                "acceptance",
                "--project",
                str(project_path),
                "--profile",
                "preview",
                "--approval-record",
                str(record_candidate),
                "--json",
            ]
        )
        == 9
    )
    record = json.loads(capsys.readouterr().out)["approval_record"]
    assert record["valid"] is False
    assert record["issue_count"] == 3
    assert all(issue.startswith("missing_required_action:") for issue in record["issues"])


def test_acceptance_repair_execution_dry_run_never_executes_approved_actions(tmp_path, capsys):
    project_path = build_valid_proposal_project(tmp_path, capsys)
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
    capsys.readouterr()
    assert (
        main(
            [
                "acceptance",
                "--project",
                str(project_path),
                "--profile",
                "preview",
                "--approval-request",
                "--json",
            ]
        )
        == 9
    )
    request = json.loads(capsys.readouterr().out)["approval_request"]
    record_candidate = tmp_path / "approval_record_for_dry_run.json"
    record_candidate.write_text(
        json.dumps(
            {
                "schema_version": "0.3",
                "approval_record_id": "candidate_record_for_dry_run",
                "project_id": request["project_id"],
                "repair_plan_id": request["repair_plan_id"],
                "acceptance_profile": request["acceptance_profile"],
                "valid": False,
                "approved_action_ids": [],
                "rejected_action_ids": [],
                "issue_count": 0,
                "issues": [],
                "actions": [
                    {
                        **action,
                        "decision": "approved",
                        "rationale": "dry run only",
                    }
                    for action in request["actions"]
                    if action["required_for_profile"]
                ],
                "network_performed": False,
                "model_call_performed_by_cli": False,
                "media_rendered": False,
                "automatic_repair_performed": False,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    assert (
        main(
            [
                "acceptance",
                "--project",
                str(project_path),
                "--profile",
                "preview",
                "--approval-record",
                str(record_candidate),
                "--execution-dry-run",
                "--json",
            ]
        )
        == 9
    )
    payload = json.loads(capsys.readouterr().out)
    dry_run = payload["execution_dry_run"]
    assert payload["execution_dry_run_output"] == ".artist-portrait/data/acceptance_repair_execution_dry_run.json"
    assert dry_run["approval_record_valid"] is True
    assert dry_run["approved_step_count"] == 3
    assert dry_run["commands_executed"] is False
    assert dry_run["automatic_repair_performed"] is False
    assert all(step["would_execute"] is False for step in dry_run["steps"])
    assert all(
        step["blocked_reason"] == "dry_run_only_no_commands_executed"
        for step in dry_run["steps"]
    )
    assert (tmp_path / ".artist-portrait" / "data" / "acceptance_repair_execution_dry_run.json").exists()
    assert (tmp_path / "output" / "acceptance_repair_execution_dry_run.md").exists()


def test_acceptance_repair_execution_bundle_and_record_validate_external_evidence(tmp_path, capsys):
    project_path = build_valid_proposal_project(tmp_path, capsys)
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
    capsys.readouterr()
    assert (
        main(
            [
                "acceptance",
                "--project",
                str(project_path),
                "--profile",
                "preview",
                "--approval-request",
                "--json",
            ]
        )
        == 9
    )
    request = json.loads(capsys.readouterr().out)["approval_request"]
    record_candidate = tmp_path / "approval_record_for_execution_bundle.json"
    record_candidate.write_text(
        json.dumps(
            {
                "schema_version": "0.3",
                "approval_record_id": "candidate_record_for_execution_bundle",
                "project_id": request["project_id"],
                "repair_plan_id": request["repair_plan_id"],
                "acceptance_profile": request["acceptance_profile"],
                "valid": False,
                "approved_action_ids": [],
                "rejected_action_ids": [],
                "issue_count": 0,
                "issues": [],
                "actions": [
                    {
                        **action,
                        "decision": "approved",
                        "rationale": "manual execution handoff",
                    }
                    for action in request["actions"]
                    if action["required_for_profile"]
                ],
                "network_performed": False,
                "model_call_performed_by_cli": False,
                "media_rendered": False,
                "automatic_repair_performed": False,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    assert (
        main(
            [
                "acceptance",
                "--project",
                str(project_path),
                "--profile",
                "preview",
                "--approval-record",
                str(record_candidate),
                "--execution-dry-run",
                "--execution-bundle",
                "--json",
            ]
        )
        == 9
    )
    payload = json.loads(capsys.readouterr().out)
    dry_run = payload["execution_dry_run"]
    bundle = payload["execution_bundle"]
    assert bundle["command_count"] == 3
    assert bundle["commands_executed_by_cli"] is False
    assert all(command["manual_execution_required"] is True for command in bundle["commands"])
    assert all(command["executable_by_cli"] is False for command in bundle["commands"])

    execution_record_candidate = tmp_path / "execution_record_candidate.json"
    execution_record_candidate.write_text(
        json.dumps(
            {
                "schema_version": "0.3",
                "execution_record_id": "candidate_execution_record",
                "project_id": bundle["project_id"],
                "repair_plan_id": bundle["repair_plan_id"],
                "approval_record_id": bundle["approval_record_id"],
                "dry_run_id": bundle["dry_run_id"],
                "execution_bundle_id": bundle["execution_bundle_id"],
                "acceptance_profile": bundle["acceptance_profile"],
                "valid": False,
                "completed_action_ids": [],
                "failed_action_ids": [],
                "skipped_action_ids": [],
                "issue_count": 0,
                "issues": [],
                "actions": [
                    {
                        "action_id": command["action_id"],
                        "step_id": command["step_id"],
                        "command": command["command"],
                        "status": "succeeded",
                        "exit_code": 0,
                        "artifact_refs": command["expected_artifacts"],
                        "notes": "external manual execution evidence",
                    }
                    for command in bundle["commands"]
                ],
                "network_performed": False,
                "model_call_performed_by_cli": False,
                "media_rendered": False,
                "automatic_repair_performed": False,
                "commands_executed_by_cli": False,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    assert (
        main(
            [
                "acceptance",
                "--project",
                str(project_path),
                "--profile",
                "preview",
                "--execution-record",
                str(execution_record_candidate),
                "--json",
            ]
        )
        == 9
    )
    record_payload = json.loads(capsys.readouterr().out)
    execution_record = record_payload["execution_record"]
    assert execution_record["valid"] is True
    assert execution_record["completed_action_ids"] == [
        command["action_id"] for command in bundle["commands"]
    ]
    assert execution_record["commands_executed_by_cli"] is False
    assert execution_record["automatic_repair_performed"] is False
    assert dry_run["commands_executed"] is False
    assert (tmp_path / ".artist-portrait" / "data" / "acceptance_repair_execution_bundle.json").exists()
    assert (tmp_path / "output" / "acceptance_repair_execution_bundle.md").exists()
    assert (tmp_path / ".artist-portrait" / "data" / "acceptance_repair_execution_record.json").exists()
    assert (tmp_path / "output" / "acceptance_repair_execution_record.md").exists()


def test_acceptance_delivery_profile_requires_preview_and_final_export(tmp_path, capsys):
    project_path = build_valid_proposal_project(tmp_path, capsys)
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
    capsys.readouterr()

    assert main(["acceptance", "--project", str(project_path), "--profile", "delivery", "--json"]) == 9
    accepted = json.loads(capsys.readouterr().out)

    assert accepted["status"] == "failed"
    assert accepted["profile"] == "delivery"
    assert accepted["profile_passed"] is False
    assert accepted["required_stage_ids"][-4:] == [
        "rhythm_plan",
        "preview",
        "final_export",
        "rhythm_media_qc",
    ]


def test_acceptance_cli_fails_when_core_pipeline_is_missing(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    capsys.readouterr()

    assert main(["acceptance", "--project", str(project_path), "--json"]) == 9
    accepted = json.loads(capsys.readouterr().out)

    assert accepted["status"] == "failed"
    assert accepted["core_ready"] is False
    stages = {stage["stage_id"]: stage for stage in accepted["acceptance"]["stages"]}
    assert stages["source_scan"]["status"] == "failed"


def test_workflow_cli_guides_next_delivery_commands_without_execution(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    capsys.readouterr()

    assert main(["workflow", "--project", str(project_path), "--target", "delivery", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    plan = payload["workflow_plan"]
    assert payload["output"] == ".artist-portrait/data/workflow_plan.json"
    assert payload["report"] == "output/workflow_plan.md"
    assert payload["handoff"] == "output/workflow_agent_handoff.json"
    assert plan["target"] == "delivery"
    assert plan["status"] == "in_progress"
    assert plan["next_command"] == "artist-portrait scan --project <project.yaml>"
    assert plan["commands_executed"] is False
    assert plan["media_rendered"] is False
    assert plan["edit_points_moved"] is False
    assert plan["automatic_music_selection"] is False
    steps = {step["step_id"]: step for step in plan["steps"]}
    assert steps["init"]["status"] == "done"
    assert steps["scan"]["status"] == "next"
    assert steps["final_export"]["status"] == "pending"
    assert (tmp_path / ".artist-portrait" / "data" / "workflow_plan.json").exists()
    assert (tmp_path / "output" / "workflow_plan.md").exists()
    assert (tmp_path / "output" / "workflow_agent_handoff.json").exists()


def test_workflow_execution_record_review_quarantines_and_validates_evidence(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    capsys.readouterr()

    assert main(["workflow", "--project", str(project_path), "--target", "core", "--json"]) == 1
    workflow_payload = json.loads(capsys.readouterr().out)
    plan = workflow_payload["workflow_plan"]

    record_path = tmp_path / "workflow_execution_record.json"
    record_path.write_text(
        json.dumps(
            {
                "execution_record_id": "record_init_only",
                "project_id": plan["project_id"],
                "workflow_plan_id": plan["workflow_plan_id"],
                "target": "core",
                "executed_by": "external-human",
                "steps": [
                    {
                        "step_id": "init",
                        "command": "artist-portrait init --project <project.yaml>",
                        "status": "succeeded",
                        "exit_code": 0,
                        "output_refs": [".artist-portrait/state.json"],
                    }
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    code = main(
        [
            "workflow",
            "--project",
            str(project_path),
            "--target",
            "core",
            "--execution-record",
            str(record_path),
            "--json",
        ]
    )
    reviewed = json.loads(capsys.readouterr().out)
    review = reviewed["workflow_execution_review"]

    assert code == 1
    assert reviewed["output"] == ".artist-portrait/data/workflow_execution_review.json"
    assert reviewed["report"] == "output/workflow_execution_review.md"
    assert reviewed["handoff"] == "output/workflow_execution_handoff.json"
    assert reviewed["quarantine"] == ".artist-portrait/data/workflow_execution_record_quarantine.json"
    assert review["status"] == "warning"
    assert review["accepted_step_count"] == 1
    assert review["missing_step_count"] > 0
    assert review["commands_executed_by_cli"] is False
    assert review["media_rendered_by_cli"] is False
    assert review["edit_points_moved_by_cli"] is False
    step_reviews = {step["step_id"]: step for step in review["step_reviews"]}
    assert step_reviews["init"]["review_status"] == "accepted"
    assert step_reviews["scan"]["review_status"] == "missing"
    assert (
        tmp_path / ".artist-portrait" / "data" / "workflow_execution_record_quarantine.json"
    ).read_text(encoding="utf-8") == record_path.read_text(encoding="utf-8")

    bad_record = tmp_path / "workflow_execution_record_bad.json"
    bad_record.write_text(
        json.dumps(
            {
                "execution_record_id": "record_missing_scan_evidence",
                "project_id": plan["project_id"],
                "workflow_plan_id": plan["workflow_plan_id"],
                "target": "core",
                "executed_by": "external-human",
                "steps": [
                    {
                        "step_id": "init",
                        "command": "artist-portrait init --project <project.yaml>",
                        "status": "succeeded",
                        "exit_code": 0,
                        "output_refs": [".artist-portrait/state.json"],
                    },
                    {
                        "step_id": "scan",
                        "command": "artist-portrait scan --project <project.yaml>",
                        "status": "succeeded",
                        "exit_code": 0,
                        "output_refs": [".artist-portrait/data/sources.jsonl"],
                    }
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    assert (
        main(
            [
                "workflow",
                "--project",
                str(project_path),
                "--target",
                "core",
                "--execution-record",
                str(bad_record),
                "--json",
            ]
        )
        == 1
    )
    rejected = json.loads(capsys.readouterr().out)["workflow_execution_review"]
    rejected_steps = {step["step_id"]: step for step in rejected["step_reviews"]}
    assert rejected["status"] == "failed"
    assert rejected_steps["scan"]["review_status"] == "rejected"
    assert rejected_steps["scan"]["missing_refs"] == [".artist-portrait/data/sources.jsonl"]

    assert (
        main(
            [
                "workflow",
                "--project",
                str(project_path),
                "--target",
                "core",
                "--repair-plan",
                "--json",
            ]
        )
        == 1
    )
    repair_payload = json.loads(capsys.readouterr().out)
    repair = repair_payload["workflow_repair_plan"]
    assert repair_payload["output"] == ".artist-portrait/data/workflow_repair_plan.json"
    assert repair_payload["report"] == "output/workflow_repair_plan.md"
    assert repair_payload["handoff"] == "output/workflow_repair_handoff.json"
    assert repair["status"] == "blocked"
    assert repair["required_action_count"] >= 1
    assert repair["first_required_command"] == "artist-portrait scan --project <project.yaml>"
    assert repair["commands_executed"] is False
    assert repair["media_rendered"] is False
    assert repair["acceptance_success_promoted"] is False
    actions = {action["step_id"]: action for action in repair["actions"]}
    assert actions["scan"]["severity"] == "required"
    assert actions["scan"]["reason"] == "rejected"
    assert actions["scan"]["evidence_to_resubmit"] == [".artist-portrait/data/sources.jsonl"]
    assert (tmp_path / "output" / "workflow_repair_plan.md").exists()

    assert (
        main(
            [
                "workflow",
                "--project",
                str(project_path),
                "--target",
                "core",
                "--approval-request",
                "--json",
            ]
        )
        == 1
    )
    approval_request_payload = json.loads(capsys.readouterr().out)
    approval_request = approval_request_payload["workflow_repair_approval_request"]
    assert approval_request_payload["output"] == ".artist-portrait/data/workflow_repair_approval_request.json"
    assert approval_request["workflow_repair_plan_id"] == repair["workflow_repair_plan_id"]
    assert "workflow_repair_001_scan" in approval_request["required_action_ids"]
    assert approval_request["commands_executed"] is False

    approval_record_candidate = tmp_path / "workflow_repair_approval_record.json"
    approval_record_candidate.write_text(
        json.dumps(
            {
                "approval_record_id": "workflow_repair_approval_record_001",
                "project_id": repair["project_id"],
                "workflow_repair_plan_id": repair["workflow_repair_plan_id"],
                "workflow_plan_id": repair["workflow_plan_id"],
                "workflow_execution_review_id": repair["workflow_execution_review_id"],
                "target": "core",
                "approved_by": "external-human",
                "approved_action_ids": ["workflow_repair_001_scan"],
                "rejected_action_ids": [],
                "status": "passed",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    assert (
        main(
            [
                "workflow",
                "--project",
                str(project_path),
                "--target",
                "core",
                "--approval-record",
                str(approval_record_candidate),
                "--json",
            ]
        )
        == 0
    )
    approval_record = json.loads(capsys.readouterr().out)["workflow_repair_approval_record"]
    assert approval_record["status"] == "passed"
    assert approval_record["commands_executed_by_cli"] is False
    assert approval_record["quarantine_ref"] == ".artist-portrait/data/workflow_repair_approval_record_quarantine.json"

    assert (
        main(
            [
                "workflow",
                "--project",
                str(project_path),
                "--target",
                "core",
                "--repair-dry-run",
                "--json",
            ]
        )
        == 1
    )
    dry_run = json.loads(capsys.readouterr().out)["workflow_repair_dry_run"]
    assert dry_run["approved_step_count"] == 1
    assert dry_run["commands_executed"] is False
    assert dry_run["acceptance_success_promoted"] is False
    dry_run_steps = {step["action_id"]: step for step in dry_run["steps"]}
    assert dry_run_steps["workflow_repair_001_scan"]["status"] == "approved"
    assert dry_run_steps["workflow_repair_001_scan"]["command"] == "artist-portrait scan --project <project.yaml>"

    source_ledger = tmp_path / ".artist-portrait" / "data" / "sources.jsonl"
    source_ledger.parent.mkdir(parents=True, exist_ok=True)
    source_ledger.write_text('{"source_id":"manual_scan"}\n', encoding="utf-8")
    scan_report = tmp_path / "output" / "scan_report.md"
    scan_report.parent.mkdir(parents=True, exist_ok=True)
    scan_report.write_text("# Manual Scan Report\n", encoding="utf-8")
    repair_execution_candidate = tmp_path / "workflow_repair_execution_record.json"
    repair_execution_candidate.write_text(
        json.dumps(
            {
                "execution_record_id": "workflow_repair_execution_record_001",
                "project_id": dry_run["project_id"],
                "workflow_repair_plan_id": dry_run["workflow_repair_plan_id"],
                "approval_record_id": dry_run["approval_record_id"],
                "dry_run_id": dry_run["dry_run_id"],
                "target": "core",
                "executed_by": "external-human",
                "actions": [
                    {
                        "action_id": "workflow_repair_001_scan",
                        "step_id": "scan",
                        "command": "artist-portrait scan --project <project.yaml>",
                        "status": "succeeded",
                        "exit_code": 0,
                        "output_refs": [
                            ".artist-portrait/data/sources.jsonl",
                            "output/scan_report.md",
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    assert (
        main(
            [
                "workflow",
                "--project",
                str(project_path),
                "--target",
                "core",
                "--repair-execution-record",
                str(repair_execution_candidate),
                "--json",
            ]
        )
        == 0
    )
    repair_execution = json.loads(capsys.readouterr().out)["workflow_repair_execution_review"]
    assert repair_execution["status"] == "passed"
    assert repair_execution["accepted_action_count"] == 1
    assert repair_execution["commands_executed_by_cli"] is False
    assert repair_execution["acceptance_success_promoted_by_cli"] is False
    assert repair_execution["quarantine_ref"] == ".artist-portrait/data/workflow_repair_execution_record_quarantine.json"

    assert (
        main(
            [
                "workflow",
                "--project",
                str(project_path),
                "--target",
                "core",
                "--repair-refresh-plan",
                "--json",
            ]
        )
        == 0
    )
    refresh_plan = json.loads(capsys.readouterr().out)["workflow_repair_refresh_plan"]
    assert refresh_plan["status"] == "ready"
    assert refresh_plan["ready_step_count"] == 1
    assert refresh_plan["blocked_step_count"] == 0
    assert refresh_plan["commands_executed"] is False
    assert refresh_plan["workflow_plan_mutated"] is False
    assert refresh_plan["acceptance_success_promoted"] is False
    refresh_steps = {step["action_id"]: step for step in refresh_plan["steps"]}
    assert refresh_steps["workflow_repair_001_scan"]["refresh_status"] == "ready_to_resubmit"
    assert ".artist-portrait/data/sources.jsonl" in refresh_steps["workflow_repair_001_scan"]["evidence_refs"]

    rejected_action_id = next(
        step["action_id"] for step in dry_run["steps"] if step["status"] == "rejected"
    )
    rejected_step = dry_run_steps[rejected_action_id]
    bad_repair_execution_candidate = tmp_path / "workflow_repair_execution_record_bad.json"
    bad_repair_execution_candidate.write_text(
        json.dumps(
            {
                "execution_record_id": "workflow_repair_execution_record_bad",
                "project_id": dry_run["project_id"],
                "workflow_repair_plan_id": dry_run["workflow_repair_plan_id"],
                "approval_record_id": dry_run["approval_record_id"],
                "dry_run_id": dry_run["dry_run_id"],
                "target": "core",
                "executed_by": "external-human",
                "actions": [
                    {
                        "action_id": rejected_action_id,
                        "step_id": rejected_step["step_id"],
                        "command": rejected_step["command"],
                        "status": "succeeded",
                        "exit_code": 0,
                        "output_refs": rejected_step["expected_artifacts"],
                    }
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    assert (
        main(
            [
                "workflow",
                "--project",
                str(project_path),
                "--target",
                "core",
                "--repair-execution-record",
                str(bad_repair_execution_candidate),
                "--json",
            ]
        )
        == 9
    )
    bad_repair_execution = json.loads(capsys.readouterr().out)["workflow_repair_execution_review"]
    assert bad_repair_execution["status"] == "failed"
    bad_action_reviews = {
        action["action_id"]: action for action in bad_repair_execution["action_reviews"]
    }
    assert bad_action_reviews[rejected_action_id]["review_status"] == "rejected"
    assert "not approved" in bad_action_reviews[rejected_action_id]["detail"]


def test_review_proposal_validates_existing_proposals(tmp_path, monkeypatch, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0
    assert main(["analyze", "--project", str(project_path), "--quiet"]) == 0
    assert main(["map", "--project", str(project_path), "--quiet"]) == 0
    monkeypatch.setattr(
        workspace,
        "detect_capabilities",
        lambda: Capabilities(text_model=False),
    )
    assert main(["propose", "--project", str(project_path), "--quiet"]) == 1
    write_proposals_from_context(tmp_path)

    code = main(["review", "--project", str(project_path), "--scope", "proposal", "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 0
    assert payload["output"] == "output/proposal_review.md"
    assert payload["validation"] == ".artist-portrait/data/proposal_validation.json"
    assert payload["issues"] == []
    validation = json.loads(
        (tmp_path / ".artist-portrait" / "data" / "proposal_validation.json").read_text(
            encoding="utf-8"
        )
    )
    assert validation["error_count"] == 0
    assert validation["warning_count"] == 0
    report = (tmp_path / "output" / "proposal_review.md").read_text(encoding="utf-8")
    assert "# Proposal Review" in report
    assert "No proposal validation issues" in report


def test_review_proposal_reports_unknown_clip_and_missing_bgm(
    tmp_path,
    monkeypatch,
    capsys,
):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0
    assert main(["analyze", "--project", str(project_path), "--quiet"]) == 0
    assert main(["map", "--project", str(project_path), "--quiet"]) == 0
    monkeypatch.setattr(
        workspace,
        "detect_capabilities",
        lambda: Capabilities(text_model=False),
    )
    assert main(["propose", "--project", str(project_path), "--quiet"]) == 1
    write_proposals_from_context(tmp_path, unknown_clip=True, bgm=False)

    code = main(["review", "--project", str(project_path), "--scope", "proposal", "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 1
    issue_codes = {issue["code"] for issue in payload["issues"]}
    assert "proposal_unknown_clip_id" in issue_codes
    assert "proposal_missing_bgm_strategy" in issue_codes
    validation = json.loads(
        (tmp_path / ".artist-portrait" / "data" / "proposal_validation.json").read_text(
            encoding="utf-8"
        )
    )
    assert validation["error_count"] == 10
    assert validation["warning_count"] == 3


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("missing_story", "proposal_missing_story_structure"),
        ("missing_visual", "proposal_missing_visual_motifs"),
        ("missing_timeline", "proposal_missing_minimum_timeline"),
        ("duplicate_clip", "proposal_duplicate_required_clip"),
        ("missing_required_clip_fact", "proposal_required_clip_missing_fact_ref"),
        ("duplicate_fact", "proposal_duplicate_fact_ref"),
        ("missing_clip_evidence", "proposal_missing_clip_evidence"),
        ("missing_analysis_evidence", "proposal_missing_analysis_evidence"),
        ("missing_material_map_evidence", "proposal_missing_material_map_evidence"),
        ("identical_story", "proposal_story_structures_not_distinct"),
        ("identical_sound", "proposal_sound_structures_not_distinct"),
        ("incomplete_bgm", "proposal_incomplete_bgm_strategy"),
        ("theme_mismatch", "proposal_theme_mismatch"),
        ("audience_mismatch", "proposal_audience_mismatch"),
        ("duplicate_title", "proposal_titles_not_unique"),
        ("missing_risks", "proposal_missing_risks"),
        ("missing_counter", "proposal_missing_counter_proposal"),
        ("missing_set_context", "proposal_set_missing_context_evidence"),
        ("duplicate_set_evidence", "proposal_set_duplicate_evidence"),
        ("unknown_set_evidence", "proposal_set_unknown_evidence"),
        ("identical_visual", "proposal_visual_motifs_not_distinct"),
        ("absolute_path_text", "proposal_absolute_path_leak"),
        ("absolute_path_evidence", "proposal_absolute_path_leak"),
        ("forbidden_method", "proposal_forbidden_generation_method"),
        ("forbidden_source_fact", "proposal_fact_ref_uses_forbidden_source"),
        ("forbidden_clip_fact", "proposal_fact_ref_uses_forbidden_clip"),
        ("analysis_not_required", "proposal_analysis_not_tied_to_required_clip"),
        (
            "required_clip_missing_analysis",
            "proposal_required_clip_missing_analysis_ref",
        ),
        ("existing_missing_material", "proposal_missing_material_already_exists"),
        ("duplicate_counter", "proposal_counter_proposals_not_distinct"),
    ],
)
def test_review_proposal_quality_matrix(
    tmp_path,
    monkeypatch,
    capsys,
    mutation,
    expected_code,
):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0
    assert main(["analyze", "--project", str(project_path), "--quiet"]) == 0
    assert main(["map", "--project", str(project_path), "--quiet"]) == 0
    monkeypatch.setattr(
        workspace,
        "detect_capabilities",
        lambda: Capabilities(text_model=False),
    )
    assert main(["propose", "--project", str(project_path), "--quiet"]) == 1
    write_proposals_from_context(tmp_path)

    proposals_path = tmp_path / ".artist-portrait" / "data" / "proposals.json"
    payload = json.loads(proposals_path.read_text(encoding="utf-8"))
    proposal = payload["proposals"][0]
    if mutation == "missing_story":
        proposal["story_structure"] = []
    elif mutation == "missing_visual":
        proposal["visual_motifs"] = []
    elif mutation == "missing_timeline":
        proposal["minimum_viable_timeline"] = []
    elif mutation == "duplicate_clip":
        proposal["required_clip_ids"].append(proposal["required_clip_ids"][0])
    elif mutation == "missing_required_clip_fact":
        proposal["fact_refs"] = [
            ref for ref in proposal["fact_refs"] if ref["type"] != "clip"
        ]
    elif mutation == "duplicate_fact":
        proposal["fact_refs"].append(dict(proposal["fact_refs"][0]))
    elif mutation == "missing_clip_evidence":
        proposal["fact_refs"] = [
            ref for ref in proposal["fact_refs"] if ref["type"] != "clip"
        ]
        proposal["required_clip_ids"] = []
    elif mutation == "missing_analysis_evidence":
        proposal["fact_refs"] = [
            ref for ref in proposal["fact_refs"] if ref["type"] != "analysis"
        ]
    elif mutation == "missing_material_map_evidence":
        proposal["fact_refs"] = [
            ref for ref in proposal["fact_refs"] if ref["type"] != "material_map"
        ]
    elif mutation == "identical_story":
        shared = ["same opening", "same ending"]
        for item in payload["proposals"]:
            item["story_structure"] = shared
    elif mutation == "identical_sound":
        shared = ["BGM supports speech with ducking"]
        for item in payload["proposals"]:
            item["sound_structure"] = shared
    elif mutation == "incomplete_bgm":
        proposal["sound_structure"] = ["BGM is present"]
    elif mutation == "theme_mismatch":
        proposal["theme"] = "different theme"
    elif mutation == "audience_mismatch":
        proposal["audience"] = "different audience"
    elif mutation == "duplicate_title":
        payload["proposals"][1]["title"] = proposal["title"]
    elif mutation == "missing_risks":
        proposal["risks"] = []
    elif mutation == "missing_counter":
        proposal["counter_proposal"] = None
    elif mutation == "missing_set_context":
        payload["evidence"] = []
    elif mutation == "duplicate_set_evidence":
        payload["evidence"].append(dict(payload["evidence"][0]))
    elif mutation == "unknown_set_evidence":
        payload["evidence"] = [{"type": "proposal_context", "ref": "unknown"}]
    elif mutation == "identical_visual":
        shared = ["same visual motif"]
        for item in payload["proposals"]:
            item["visual_motifs"] = shared
    elif mutation == "absolute_path_text":
        proposal["story_structure"] = ["/Users/example/private/story.txt"]
    elif mutation == "absolute_path_evidence":
        payload["evidence"] = [
            {"type": "proposal_context", "ref": "/Users/example/private/context.json"}
        ]
    elif mutation == "forbidden_method":
        payload["method"] = "template_generator"
    elif mutation in {"forbidden_source_fact", "forbidden_clip_fact"}:
        context_path = (
            tmp_path / ".artist-portrait" / "data" / "proposal_context.json"
        )
        context = json.loads(context_path.read_text(encoding="utf-8"))
        context["sources"][0]["forbidden_by_user"] = True
        context_path.write_text(
            json.dumps(context, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if mutation == "forbidden_source_fact":
            proposal["fact_refs"].append(
                {"type": "source", "ref": context["sources"][0]["source_id"]}
            )
    elif mutation == "analysis_not_required":
        context_path = (
            tmp_path / ".artist-portrait" / "data" / "proposal_context.json"
        )
        context = json.loads(context_path.read_text(encoding="utf-8"))
        extra_analysis = dict(context["analyses"][0])
        extra_analysis["analysis_id"] = "analysis-not-required"
        extra_analysis["clip_id"] = "clip-not-required"
        context["analyses"].append(extra_analysis)
        context_path.write_text(
            json.dumps(context, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        proposal["fact_refs"].append(
            {"type": "analysis", "ref": "analysis-not-required"}
        )
    elif mutation == "required_clip_missing_analysis":
        proposal["fact_refs"] = [
            ref for ref in proposal["fact_refs"] if ref["type"] != "analysis"
        ]
    elif mutation == "existing_missing_material":
        proposal["missing_material"] = [proposal["required_clip_ids"][0]]
    elif mutation == "duplicate_counter":
        shared = "What if all three proposals use the same challenge?"
        for item in payload["proposals"]:
            item["counter_proposal"] = shared
    proposals_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    assert (
        main(["review", "--project", str(project_path), "--scope", "proposal", "--json"])
        == 1
    )
    review_payload = json.loads(capsys.readouterr().out)
    assert expected_code in {issue["code"] for issue in review_payload["issues"]}


@pytest.mark.parametrize(
    ("sound_structures", "expected_code", "expected_exit"),
    [
        (
            [
                ["BGM drives pacing with beat-aligned cuts"],
                ["Music supports emotion through a drop"],
                ["Score supports transitions with voice ducking"],
            ],
            "proposal_music_policy_violation",
            1,
        ),
        (
            [
                ["No added music; original audio only with intentional silence"],
                ["Voice only, without music, using dialogue pauses"],
                ["No BGM; silence only with original stage sound"],
            ],
            None,
            0,
        ),
    ],
)
def test_review_proposal_music_policy(
    tmp_path,
    monkeypatch,
    capsys,
    sound_structures,
    expected_code,
    expected_exit,
):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off").replace(
            "allow_music: true",
            "allow_music: false",
        ),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0
    assert main(["analyze", "--project", str(project_path), "--quiet"]) == 0
    assert main(["map", "--project", str(project_path), "--quiet"]) == 0
    monkeypatch.setattr(
        workspace,
        "detect_capabilities",
        lambda: Capabilities(text_model=False),
    )
    assert main(["propose", "--project", str(project_path), "--quiet"]) == 1
    write_proposals_from_context(tmp_path)
    proposals_path = tmp_path / ".artist-portrait" / "data" / "proposals.json"
    payload = json.loads(proposals_path.read_text(encoding="utf-8"))
    for proposal, sound_structure in zip(payload["proposals"], sound_structures):
        proposal["sound_structure"] = sound_structure
    proposals_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    assert (
        main(["review", "--project", str(project_path), "--scope", "proposal", "--json"])
        == expected_exit
    )
    review_payload = json.loads(capsys.readouterr().out)
    issue_codes = {issue["code"] for issue in review_payload["issues"]}
    if expected_code is None:
        assert "proposal_music_policy_violation" not in issue_codes
    else:
        assert expected_code in issue_codes


def test_review_all_runs_project_review_without_unimplemented_scope_warnings(
    tmp_path,
    capsys,
):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)

    code = main(["review", "--project", str(project_path), "--scope", "all", "--json"])
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["output"] == "output/risk_report.md"
    assert payload["issues"] == []
    risk_report = (tmp_path / "output" / "risk_report.md").read_text(encoding="utf-8")
    assert "review_scope_skipped" not in risk_report

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)

    assert code == 0
    assert status_payload["latest_run"]["scope"] == "all"


def test_review_project_writes_risk_report_from_sources(tmp_path, monkeypatch, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    (media_dir / "restricted.mp4").write_bytes(b"restricted")
    (tmp_path / "sources.csv").write_text(
        "location,source_type,rights_status,forbidden_by_user,notes\n"
        "media/restricted.mp4,interview,restricted,true,Do not use\n",
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    monkeypatch.setattr(
        cli,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True),
    )

    def fake_probe(path):
        return (
            MediaKind.video,
            MediaProbe(
                duration=3.0,
                width=1280,
                height=720,
                frame_rate=24.0,
                video_codec="h264",
                audio_present=False,
                audio_codec=None,
            ),
        )

    from artist_portrait_editor.media import scanner

    original_scan_project_sources = scanner.scan_project_sources

    def scan_with_fake_probe(*, root, config, previous_records=None):
        return original_scan_project_sources(
            root=root,
            config=config,
            probe_fn=fake_probe,
            previous_records=previous_records,
        )

    monkeypatch.setattr(workspace, "scan_project_sources", scan_with_fake_probe)

    assert main(["scan", "--project", str(project_path), "--quiet"]) == 0
    code = main(["review", "--project", str(project_path), "--scope", "project", "--json"])
    captured = capsys.readouterr()

    assert code == 1
    payload = json.loads(captured.out)
    assert payload["output"] == "output/risk_report.md"
    assert len(payload["issues"]) == 2
    assert {issue["code"] for issue in payload["issues"]} == {
        "forbidden_by_user",
        "rights_restricted",
    }
    risk_report = (tmp_path / "output" / "risk_report.md").read_text(encoding="utf-8")
    assert "# Risk Report" in risk_report
    assert "No transcription, visual analysis" in risk_report
    assert "- Issue count: `2`" in risk_report
    assert "rights_status is restricted" in risk_report
    assert "forbidden_by_user" in risk_report

    state_payload = json.loads(
        (tmp_path / ".artist-portrait" / "state.json").read_text(encoding="utf-8")
    )
    assert state_payload["steps"]["review_project"]["status"] == "completed_with_warnings"
    assert state_payload["steps"]["review_project"]["output_refs"] == ["output/risk_report.md"]
    run_report = (tmp_path / "output" / "run_report.md").read_text(encoding="utf-8")
    assert "- `review_project`: `completed_with_warnings`" in run_report
    assert "2 project review issue(s) found" in run_report

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)

    assert code == 0
    assert status_payload["summaries"]["sources"]["count"] == 1
    assert status_payload["summaries"]["sources"]["media_kind_counts"] == {"video": 1}
    assert status_payload["summaries"]["scan_report"]["exists"] is True
    assert status_payload["artifacts"]["scan_report"]["exists"] is True
    assert status_payload["artifacts"]["risk_report"]["exists"] is True
    assert status_payload["latest_run"]["command"] == "review"
    assert status_payload["latest_run"]["scope"] == "project"
    assert status_payload["latest_run"]["step_result"]["issues"] == 2


def test_status_and_review_report_missing_output_ref(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0
    assert main(["analyze", "--project", str(project_path), "--quiet"]) == 0
    assert main(["map", "--project", str(project_path), "--quiet"]) == 0
    (tmp_path / "output" / "material_map.md").unlink()

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    status_payload = json.loads(captured.out)

    assert code == 0
    assert status_payload["artifacts"]["material_map"]["exists"] is False
    assert status_payload["artifact_issues"] == [
        {
            "code": "missing_output_ref",
            "detail": (
                "step `map` is marked `completed` but referenced output "
                "`output/material_map.md` is missing"
            ),
            "location": "output/material_map.md",
            "ref": "output/material_map.md",
            "scope": "artifact",
            "severity": "warning",
            "step": "map",
            "next_action": "artist-portrait map --project <project.yaml>",
        }
    ]

    code = main(["status", "--project", str(project_path)])
    captured = capsys.readouterr()

    assert code == 0
    assert "artifact_issues: 1" in captured.out

    code = main(["review", "--project", str(project_path), "--scope", "project", "--json"])
    captured = capsys.readouterr()
    review_payload = json.loads(captured.out)

    assert code == 1
    assert [issue["code"] for issue in review_payload["issues"]] == ["missing_output_ref"]
    assert review_payload["issues"][0]["step"] == "map"
    risk_report = (tmp_path / "output" / "risk_report.md").read_text(encoding="utf-8")
    assert "missing_output_ref" in risk_report
    assert "Output ref: `output/material_map.md`" in risk_report

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(issue["code"] == "missing_output_ref" for issue in doctor_payload["issues"])
    assert (
        "artist-portrait map --project <project.yaml>"
        in doctor_payload["recommended_commands"]
    )


def test_proposal_chain_health_has_no_integrity_issues(tmp_path, capsys):
    project_path = build_blocked_proposal_chain(tmp_path, capsys)

    assert main(["status", "--project", str(project_path), "--json"]) == 0
    status_payload = json.loads(capsys.readouterr().out)

    assert not [
        issue
        for issue in status_payload["artifact_issues"]
        if issue["code"].startswith("proposal_")
    ]


def test_status_and_doctor_report_proposal_ref_mismatch(tmp_path, capsys):
    project_path = build_blocked_proposal_chain(tmp_path, capsys)
    result_path = (
        tmp_path / ".artist-portrait" / "data" / "proposal_provider_result.json"
    )
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    payload["request_ref"] = ".artist-portrait/data/wrong_request.json"
    result_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    assert main(["status", "--project", str(project_path), "--json"]) == 0
    status_payload = json.loads(capsys.readouterr().out)
    mismatch = [
        issue
        for issue in status_payload["artifact_issues"]
        if issue["code"] == "proposal_ref_mismatch"
    ]
    assert mismatch
    assert "request_ref" in mismatch[0]["detail"]

    assert main(["doctor", "--project", str(project_path), "--json"]) == 1
    doctor_payload = json.loads(capsys.readouterr().out)
    assert any(
        issue["code"] == "proposal_ref_mismatch"
        for issue in doctor_payload["issues"]
    )


def test_status_reports_missing_proposal_dependency(tmp_path, capsys):
    project_path = build_blocked_proposal_chain(tmp_path, capsys)
    (
        tmp_path / ".artist-portrait" / "data" / "proposal_adapter_check.json"
    ).unlink()

    assert main(["status", "--project", str(project_path), "--json"]) == 0
    status_payload = json.loads(capsys.readouterr().out)
    missing = [
        issue
        for issue in status_payload["artifact_issues"]
        if issue["code"] == "proposal_ref_missing"
    ]

    assert missing
    assert any("adapter_check_ref" in issue["detail"] for issue in missing)


def test_status_reports_proposal_project_id_mismatch(tmp_path, capsys):
    project_path = build_blocked_proposal_chain(tmp_path, capsys)
    result_path = (
        tmp_path / ".artist-portrait" / "data" / "proposal_provider_result.json"
    )
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    payload["project_id"] = "different_project"
    result_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    assert main(["status", "--project", str(project_path), "--json"]) == 0
    status_payload = json.loads(capsys.readouterr().out)

    assert any(
        issue["code"] == "proposal_project_id_mismatch"
        for issue in status_payload["artifact_issues"]
    )


def test_status_reports_stale_proposal_context_after_map_change(tmp_path, capsys):
    project_path = build_blocked_proposal_chain(tmp_path, capsys)
    material_map_path = tmp_path / "output" / "material_map.md"
    material_map_path.write_text(
        material_map_path.read_text(encoding="utf-8") + "\nmanual change\n",
        encoding="utf-8",
    )

    assert main(["status", "--project", str(project_path), "--json"]) == 0
    status_payload = json.loads(capsys.readouterr().out)

    assert any(
        issue["code"] == "proposal_artifact_stale"
        and "material_map_fingerprint" in issue["detail"]
        for issue in status_payload["artifact_issues"]
    )


def test_status_reports_duplicate_proposal_output_ref(tmp_path, capsys):
    project_path = build_blocked_proposal_chain(tmp_path, capsys)
    state_path = tmp_path / ".artist-portrait" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    duplicate_ref = state["steps"]["propose"]["output_refs"][0]
    state["steps"]["propose"]["output_refs"].append(duplicate_ref)
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    assert main(["status", "--project", str(project_path), "--json"]) == 0
    status_payload = json.loads(capsys.readouterr().out)

    assert any(
        issue["code"] == "duplicate_output_ref" and issue["ref"] == duplicate_ref
        for issue in status_payload["artifact_issues"]
    )


def test_invalid_sources_jsonl_blocks_scan_map_and_review_but_status_reports_it(
    tmp_path,
    monkeypatch,
    capsys,
):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    monkeypatch.setattr(
        cli,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True),
    )
    sources_path = tmp_path / ".artist-portrait" / "data" / "sources.jsonl"
    sources_path.write_text('{"source_id": "missing-required-fields"}\n', encoding="utf-8")

    code = main(["scan", "--project", str(project_path)])
    captured = capsys.readouterr()

    assert code == 9
    assert "invalid SourceRecord JSONL" in captured.err

    code = main(["map", "--project", str(project_path)])
    captured = capsys.readouterr()

    assert code == 9
    assert "invalid SourceRecord JSONL" in captured.err

    code = main(["review", "--project", str(project_path), "--scope", "project"])
    captured = capsys.readouterr()

    assert code == 9
    assert "invalid SourceRecord JSONL" in captured.err

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 0
    assert payload["summaries"]["sources"]["exists"] is True
    assert payload["summaries"]["sources"]["valid"] is False
    assert "invalid SourceRecord JSONL" in payload["summaries"]["sources"]["error"]

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert doctor_payload["issue_count"] == 1
    assert doctor_payload["issues"][0]["code"] == "source_ledger_invalid"
    assert "invalid SourceRecord JSONL" in doctor_payload["issues"][0]["detail"]


def test_repeated_cli_scan_updates_moved_location(tmp_path, monkeypatch, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    original = media_dir / "a.mp4"
    moved = media_dir / "moved.mp4"
    original.write_bytes(b"same-content")
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    monkeypatch.setattr(
        cli,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True),
    )

    def fake_probe(path):
        return (
            MediaKind.video,
            MediaProbe(
                duration=1.0,
                width=16,
                height=16,
                frame_rate=24.0,
                video_codec="h264",
                audio_present=False,
                audio_codec=None,
            ),
        )

    from artist_portrait_editor.media import scanner

    original_scan_project_sources = scanner.scan_project_sources

    def scan_with_fake_probe(*, root, config, previous_records=None):
        return original_scan_project_sources(
            root=root,
            config=config,
            probe_fn=fake_probe,
            previous_records=previous_records,
        )

    monkeypatch.setattr(workspace, "scan_project_sources", scan_with_fake_probe)

    assert main(["scan", "--project", str(project_path), "--quiet"]) == 0
    sources_path = tmp_path / ".artist-portrait" / "data" / "sources.jsonl"
    first_record = read_sources_jsonl(sources_path)[0]
    original.rename(moved)
    assert main(["scan", "--project", str(project_path), "--quiet"]) == 0
    second_record = read_sources_jsonl(sources_path)[0]

    assert second_record.source_id == first_record.source_id
    assert second_record.locations == ["media/moved.mp4"]


def test_repeated_cli_scan_records_superseded_source_for_same_location_change(
    tmp_path,
    monkeypatch,
    capsys,
):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    media = media_dir / "a.mp4"
    media.write_bytes(b"first-content")
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    monkeypatch.setattr(
        cli,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True),
    )

    def fake_probe(path):
        return (
            MediaKind.video,
            MediaProbe(
                duration=1.0,
                width=16,
                height=16,
                frame_rate=24.0,
                video_codec="h264",
                audio_present=False,
                audio_codec=None,
            ),
        )

    from artist_portrait_editor.media import scanner

    original_scan_project_sources = scanner.scan_project_sources

    def scan_with_fake_probe(*, root, config, previous_records=None):
        return original_scan_project_sources(
            root=root,
            config=config,
            probe_fn=fake_probe,
            previous_records=previous_records,
        )

    monkeypatch.setattr(workspace, "scan_project_sources", scan_with_fake_probe)

    assert main(["scan", "--project", str(project_path), "--quiet"]) == 0
    sources_path = tmp_path / ".artist-portrait" / "data" / "sources.jsonl"
    first_record = read_sources_jsonl(sources_path)[0]
    media.write_bytes(b"changed-content")
    assert main(["scan", "--project", str(project_path), "--quiet"]) == 0
    second_record = read_sources_jsonl(sources_path)[0]

    assert second_record.source_id != first_record.source_id
    assert second_record.locations == ["media/a.mp4"]
    assert second_record.supersedes_source_id == first_record.source_id


def test_repeated_cli_scan_invalidates_map_and_project_review(
    tmp_path,
    monkeypatch,
    capsys,
):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    media = media_dir / "a.mp4"
    media.write_bytes(b"first-content")
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    monkeypatch.setattr(
        cli,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True),
    )

    def fake_probe(path):
        return (
            MediaKind.video,
            MediaProbe(
                duration=1.0,
                width=16,
                height=16,
                frame_rate=24.0,
                video_codec="h264",
                audio_present=False,
                audio_codec=None,
            ),
        )

    from artist_portrait_editor.media import scanner

    original_scan_project_sources = scanner.scan_project_sources

    def scan_with_fake_probe(*, root, config, previous_records=None):
        return original_scan_project_sources(
            root=root,
            config=config,
            probe_fn=fake_probe,
            previous_records=previous_records,
        )

    monkeypatch.setattr(workspace, "scan_project_sources", scan_with_fake_probe)

    assert main(["scan", "--project", str(project_path), "--quiet"]) == 0
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0
    assert main(["analyze", "--project", str(project_path), "--quiet"]) == 0
    assert main(["map", "--project", str(project_path), "--quiet"]) == 0
    assert main(["review", "--project", str(project_path), "--scope", "project", "--quiet"]) == 1

    media.write_bytes(b"changed-content")
    code = main(["scan", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["invalidated_steps"] == ["segment", "analyze", "map", "review_project"]
    state_payload = json.loads(
        (tmp_path / ".artist-portrait" / "state.json").read_text(encoding="utf-8")
    )
    assert state_payload["steps"]["map"]["status"] == "invalidated"
    assert state_payload["steps"]["review_project"]["status"] == "invalidated"
    scan_report = (tmp_path / "output" / "scan_report.md").read_text(encoding="utf-8")
    assert "## Invalidated Downstream Steps" in scan_report
    assert "- `analyze`" in scan_report
    assert "- `map`" in scan_report
    assert "- `review_project`" in scan_report

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    issue_codes = {issue["code"] for issue in doctor_payload["issues"]}
    assert {"analyze_invalidated", "map_invalidated", "review_project_invalidated"}.issubset(
        issue_codes
    )

    code = main(["review", "--project", str(project_path), "--scope", "project", "--json"])
    captured = capsys.readouterr()
    review_payload = json.loads(captured.out)

    assert code == 1
    issue_codes = [issue["code"] for issue in review_payload["issues"]]
    assert "map_invalidated" in issue_codes
    assert "review_project_invalidated" not in issue_codes
    risk_report = (tmp_path / "output" / "risk_report.md").read_text(encoding="utf-8")
    assert "map_invalidated" in risk_report
    assert "review_project_invalidated" not in risk_report


def test_repeated_cli_scan_invalidates_segment_outputs(
    tmp_path,
    monkeypatch,
    capsys,
):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    media = media_dir / "a.mp4"
    media.write_bytes(b"first-content")
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    monkeypatch.setattr(
        cli,
        "detect_capabilities",
        lambda: Capabilities(ffmpeg=True, ffprobe=True),
    )

    def fake_probe(path):
        return (
            MediaKind.video,
            MediaProbe(
                duration=12.0,
                width=16,
                height=16,
                frame_rate=24.0,
                video_codec="h264",
                audio_present=False,
                audio_codec=None,
            ),
        )

    from artist_portrait_editor.media import scanner

    original_scan_project_sources = scanner.scan_project_sources

    def scan_with_fake_probe(*, root, config, previous_records=None):
        return original_scan_project_sources(
            root=root,
            config=config,
            probe_fn=fake_probe,
            previous_records=previous_records,
        )

    monkeypatch.setattr(workspace, "scan_project_sources", scan_with_fake_probe)

    assert main(["scan", "--project", str(project_path), "--quiet"]) == 0
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0
    media.write_bytes(b"changed-content")

    code = main(["scan", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["invalidated_steps"] == ["segment"]
    state_payload = json.loads(
        (tmp_path / ".artist-portrait" / "state.json").read_text(encoding="utf-8")
    )
    assert state_payload["steps"]["segment"]["status"] == "invalidated"

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(issue["code"] == "segment_invalidated" for issue in doctor_payload["issues"])


def test_invalid_clips_jsonl_is_reported_by_status_and_doctor(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    clips_path = tmp_path / ".artist-portrait" / "data" / "clips.jsonl"
    clips_path.write_text('{"clip_id": "missing-required-fields"}\n', encoding="utf-8")

    code = main(["status", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 0
    assert payload["summaries"]["clips"]["exists"] is True
    assert payload["summaries"]["clips"]["valid"] is False
    assert "invalid ClipRecord JSONL" in payload["summaries"]["clips"]["error"]

    code = main(["doctor", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()
    doctor_payload = json.loads(captured.out)

    assert code == 1
    assert any(issue["code"] == "clips_invalid" for issue in doctor_payload["issues"])


def prepare_host_agent_proposal_handoff(tmp_path: Path) -> Path:
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0
    assert main(["analyze", "--project", str(project_path), "--quiet"]) == 0
    assert main(["map", "--project", str(project_path), "--quiet"]) == 0
    assert main(["propose", "--project", str(project_path), "--quiet"]) == 1
    assert (tmp_path / "output" / "proposal_agent_handoff.json").exists()
    return project_path


def test_host_agent_candidate_is_quarantined_validated_and_promoted(
    tmp_path,
    capsys,
):
    project_path = prepare_host_agent_proposal_handoff(tmp_path)
    write_proposals_from_context(tmp_path)
    canonical = tmp_path / ".artist-portrait" / "data" / "proposals.json"
    candidate = tmp_path / "host-agent-candidate.json"
    canonical.replace(candidate)
    capsys.readouterr()

    code = main(
        [
            "propose",
            "--project",
            str(project_path),
            "--agent-output",
            str(candidate),
            "--json",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 0
    assert payload["status"] == "completed"
    assert payload["output"] == ".artist-portrait/data/proposals.json"
    assert payload["handoff"] == "output/proposal_agent_handoff.json"
    assert payload["quarantine"].startswith(
        ".artist-portrait/quarantine/proposals/host_agent_"
    )
    assert canonical.exists()
    assert json.loads(canonical.read_text(encoding="utf-8"))["method"]
    validation = json.loads(
        (
            tmp_path / ".artist-portrait" / "data" / "proposal_validation.json"
        ).read_text(encoding="utf-8")
    )
    assert validation["error_count"] == 0
    state = json.loads(
        (tmp_path / ".artist-portrait" / "state.json").read_text(encoding="utf-8")
    )
    assert state["active_mode"] == "creative"
    assert state["steps"]["propose"]["status"] == "completed"

    assert main(["status", "--project", str(project_path), "--json"]) == 0
    status_payload = json.loads(capsys.readouterr().out)
    assert status_payload["summaries"]["proposal_agent_handoff"]["exists"] is True
    assert (
        status_payload["summaries"]["proposal_agent_quarantine"]["file_count"]
        >= 1
    )
    assert status_payload["summaries"]["proposals"]["count"] == 3

    assert main(["doctor", "--project", str(project_path), "--json"]) in (0, 1)
    doctor_payload = json.loads(capsys.readouterr().out)
    assert "proposal_agent_candidate_pending" not in {
        issue["code"] for issue in doctor_payload["issues"]
    }


def test_invalid_host_agent_json_is_quarantined_without_canonical_overwrite(
    tmp_path,
    capsys,
):
    project_path = prepare_host_agent_proposal_handoff(tmp_path)
    canonical = tmp_path / ".artist-portrait" / "data" / "proposals.json"
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_text('{"existing": true}\n', encoding="utf-8")
    candidate = tmp_path / "invalid-host-agent.json"
    candidate.write_text('{"broken":', encoding="utf-8")
    capsys.readouterr()

    code = main(
        [
            "propose",
            "--project",
            str(project_path),
            "--agent-output",
            str(candidate),
            "--json",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 9
    assert payload["error_code"] == "agent_candidate_invalid_json"
    assert payload["quarantine"].startswith(
        ".artist-portrait/quarantine/proposals/host_agent_"
    )
    assert canonical.read_text(encoding="utf-8") == '{"existing": true}\n'


def test_semantically_invalid_host_agent_candidate_never_reaches_canonical(
    tmp_path,
    capsys,
):
    project_path = prepare_host_agent_proposal_handoff(tmp_path)
    write_proposals_from_context(tmp_path, unknown_clip=True)
    canonical = tmp_path / ".artist-portrait" / "data" / "proposals.json"
    candidate = tmp_path / "semantic-invalid-host-agent.json"
    canonical.replace(candidate)
    capsys.readouterr()

    code = main(
        [
            "propose",
            "--project",
            str(project_path),
            "--agent-output",
            str(candidate),
            "--json",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 9
    assert payload["error_code"] == "agent_candidate_semantic_invalid"
    assert not canonical.exists()
    quarantine = tmp_path / payload["quarantine"]
    assert quarantine.exists()
    assert quarantine.with_suffix(".validation.json").exists()


def test_host_agent_candidate_requires_explicit_model_provenance(
    tmp_path,
    capsys,
):
    project_path = prepare_host_agent_proposal_handoff(tmp_path)
    write_proposals_from_context(tmp_path)
    canonical = tmp_path / ".artist-portrait" / "data" / "proposals.json"
    payload = json.loads(canonical.read_text(encoding="utf-8"))
    payload["method"] = "manual_json"
    candidate = tmp_path / "missing-host-agent-provenance.json"
    candidate.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    canonical.unlink()
    capsys.readouterr()

    code = main(
        [
            "propose",
            "--project",
            str(project_path),
            "--agent-output",
            str(candidate),
            "--json",
        ]
    )
    result = json.loads(capsys.readouterr().out)

    assert code == 9
    assert result["error_code"] == "agent_candidate_method_invalid"
    assert not canonical.exists()
