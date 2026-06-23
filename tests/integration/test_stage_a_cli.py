import json
from pathlib import Path

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


def write_proposals_from_context(root: Path, *, unknown_clip: bool = False, bgm: bool = True) -> None:
    context = json.loads(
        (root / ".artist-portrait" / "data" / "proposal_context.json").read_text(
            encoding="utf-8"
        )
    )
    clip_id = context["clips"][0]["clip_id"]
    analysis_id = context["analyses"][0]["analysis_id"]
    required_clip = "clip_missing" if unknown_clip else clip_id
    sound_structure = ["BGM strategy: low-interference music under speech"] if bgm else [
        "voice-first sound plan"
    ]
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
                "story_structure": ["open with established evidence", "develop contrast"],
                "sound_structure": sound_structure,
                "visual_motifs": ["manual confirmation required"],
                "risks": ["visual semantics not inferred"],
                "minimum_viable_timeline": ["timeline generation not open"],
                "missing_material": [],
                "counter_proposal": None,
            }
        )
    payload = {
        "proposal_set_id": "proposal_set_test",
        "project_id": context["project_id"],
        "map_fingerprint": context["material_map_fingerprint"],
        "method": "test_fixture",
        "method_version": "test",
        "proposals": proposals,
        "evidence": [{"type": "proposal_context", "ref": context["context_id"]}],
        "warnings": [],
    }
    (root / ".artist-portrait" / "data" / "proposals.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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

    assert code == 4
    payload = json.loads(captured.out)
    assert payload["status"] == "blocked"
    assert payload["output_refs"] == [
        ".artist-portrait/data/proposal_context.json",
        ".artist-portrait/data/text_model_gate.json",
        ".artist-portrait/data/proposal_request.json",
        ".artist-portrait/data/proposal_adapter_check.json",
        ".artist-portrait/data/proposal_provider_registry.json",
        ".artist-portrait/data/proposal_mock_adapter_handshake.json",
    ]
    assert "text_model_gate_blocked" in payload["warnings"][0]
    assert "remote_text_model_not_allowed" in payload["warnings"][0]
    assert "text_model_capability_missing" in payload["warnings"][0]
    assert "no fake proposals" in payload["error"]
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
    assert "full_creative_proposal_generation" in context_payload["blocked_capabilities"]
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
        ".artist-portrait/data/proposal_adapter_check.json",
        ".artist-portrait/data/proposal_provider_registry.json",
        ".artist-portrait/data/proposal_mock_adapter_handshake.json",
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

    assert code == 4
    payload = json.loads(captured.out)
    assert payload["status"] == "blocked"
    assert "proposal_generation_not_implemented" in payload["warnings"][0]
    assert "generation is not implemented" in payload["error"]
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

    assert code == 4
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


def test_review_timeline_scope_remains_blocked(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    code = main(["review", "--project", str(project_path), "--scope", "timeline"])
    captured = capsys.readouterr()

    assert code == 7
    assert "review --scope timeline" in captured.err


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
    assert main(["propose", "--project", str(project_path), "--quiet"]) == 4
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
    assert main(["propose", "--project", str(project_path), "--quiet"]) == 4
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
    assert validation["error_count"] == 3
    assert validation["warning_count"] == 3


def test_review_all_runs_project_review_and_marks_unimplemented_scopes(
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

    assert code == 1
    payload = json.loads(captured.out)
    assert payload["output"] == "output/risk_report.md"
    assert [issue["code"] for issue in payload["issues"]] == [
        "review_scope_skipped",
    ]
    assert {issue["review_scope"] for issue in payload["issues"]} == {"timeline"}
    risk_report = (tmp_path / "output" / "risk_report.md").read_text(encoding="utf-8")
    assert "Review scope: `timeline`" in risk_report

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
