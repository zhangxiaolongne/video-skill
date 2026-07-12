import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
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
from artist_portrait_editor.models.keyframe import KeyframeRecord
from artist_portrait_editor.models.state import Capabilities
from artist_portrait_editor.models.transcript import TranscriptRecord, TranscriptTextType


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "stage_a"


from tests.integration.helpers import (
    build_blocked_proposal_chain,
    build_valid_proposal_project,
    project_fixture_with_remote_text_model_allowed,
    project_fixture_with_scene_detection,
    project_fixture_with_transcription,
    run_brief_and_score_for_propose,
    write_audio_source_ledger,
    write_clean_source_ledger,
    write_proposals_from_context,
    write_score_evidence_ledgers,
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
    assert report["capability_gate"] == "V2-08"
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


def test_brief_recommends_duration_from_local_evidence(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0
    assert main(["analyze", "--project", str(project_path), "--quiet"]) == 0

    code = main(["brief", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    brief = payload["edit_brief"]
    assert payload["output"] == ".artist-portrait/data/edit_brief.json"
    assert payload["report"] == "output/edit_brief.md"
    assert brief["duration_source"] == "system_recommended"
    assert brief["selected_option_id"] == "standard_cut"
    assert brief["selected_duration_seconds"] == 2.0
    assert brief["artifact_refs"] == [
        ".artist-portrait/data/edit_brief.json",
        "output/edit_brief.md",
    ]
    assert brief["forbidden_capability_flags"]["network_performed"] is False
    assert brief["evidence_summary"]["evidence_level"] == "analysis_available"
    assert brief["model_call_performed_by_cli"] is False
    assert brief["network_performed"] is False
    assert brief["media_rendered"] is False
    assert brief["automatic_music_selection"] is False
    assert "Never treat extracted mixed video audio as clean BGM" in (
        tmp_path / "output" / "edit_brief.md"
    ).read_text(encoding="utf-8")

    status_code = main(["status", "--project", str(project_path), "--json"])
    status_payload = json.loads(capsys.readouterr().out)
    assert status_code == 0
    assert status_payload["steps"]["brief"]["status"] == "completed"


def test_brief_respects_explicit_user_duration(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)

    code = main(
        [
            "brief",
            "--project",
            str(project_path),
            "--target-duration-seconds",
            "1.5",
            "--platform",
            "douyin",
            "--json",
        ]
    )
    captured = capsys.readouterr()

    assert code == 1
    brief = json.loads(captured.out)["edit_brief"]
    assert brief["duration_source"] == "user_specified"
    assert brief["requested_duration_seconds"] == 1.5
    assert brief["selected_duration_seconds"] == 1.5
    assert brief["selected_option_id"] == "user_specified"
    assert brief["target_platform"] == "douyin"
    assert brief["warnings"] == [
        "clip and analysis ledgers are missing; brief cannot reason about shot density"
    ]


def test_score_writes_clip_value_selection_map_and_feeds_proposal_context(
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
    write_score_evidence_ledgers(tmp_path)
    assert main(["analyze", "--project", str(project_path), "--quiet"]) == 0
    assert main(["map", "--project", str(project_path), "--quiet"]) == 0
    assert main(["brief", "--project", str(project_path), "--quiet"]) in (0, 1)

    code = main(["score", "--project", str(project_path), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["output"] == ".artist-portrait/data/clip_scores.jsonl"
    assert payload["report"] == "output/clip_score_report.md"
    score = payload["clip_scores"][0]
    assert score["evidence_level"] == "multi_modal"
    assert score["speech_score"]["score"] > 0
    assert score["transcript_density_score"]["score"] > 0
    assert score["keyframe_coverage_score"]["score"] == 1.0
    assert score["keyframe_cluster_id"].startswith("keyframe_cluster_")
    assert score["model_call_performed_by_cli"] is False
    assert score["network_performed"] is False
    assert score["media_rendered"] is False
    assert "source file missing" in score["audio_energy"]["detail"]
    assert "Clip Score Report" in (
        tmp_path / "output" / "clip_score_report.md"
    ).read_text(encoding="utf-8")

    monkeypatch.setattr(
        workspace,
        "detect_capabilities",
        lambda: Capabilities(text_model=False),
    )
    assert main(["propose", "--project", str(project_path), "--json"]) == 1
    context = json.loads(
        (tmp_path / ".artist-portrait" / "data" / "proposal_context.json").read_text(
            encoding="utf-8"
        )
    )
    assert context["clip_scores_ref"] == ".artist-portrait/data/clip_scores.jsonl"
    assert context["clip_scores"][0]["clip_id"] == score["clip_id"]
    assert context["clip_scores"][0]["overall_score"] == score["overall_score"]


def test_workflow_places_brief_before_propose(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(tmp_path)
    (tmp_path / "output" / "scan_report.md").write_text("# Scan Report\n", encoding="utf-8")
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0
    assert main(["analyze", "--project", str(project_path), "--quiet"]) == 0
    assert main(["map", "--project", str(project_path), "--quiet"]) == 0

    assert main(["workflow", "--project", str(project_path), "--target", "core", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    steps = {step["step_id"]: step for step in payload["workflow_plan"]["steps"]}
    deliverables = {
        item["deliverable_id"]: item
        for item in payload["workflow_plan"]["deliverables"]
    }
    assert steps["brief"]["status"] == "next"
    assert steps["score"]["status"] == "pending"
    assert steps["propose"]["status"] == "pending"
    assert payload["workflow_plan"]["next_command"] == "artist-portrait brief --project <project.yaml>"
    assert deliverables["edit_brief"]["status"] == "missing"


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
