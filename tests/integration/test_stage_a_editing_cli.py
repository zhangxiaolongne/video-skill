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
    assert timeline["edit_brief_ref"] == ".artist-portrait/data/edit_brief.json"
    assert timeline["clip_scores_ref"] == ".artist-portrait/data/clip_scores.jsonl"
    assert timeline["selected_duration_option_id"] == "standard_cut"
    assert timeline["target_duration"] == 2.0
    assert timeline["duration_variants"]
    assert timeline["no_fabricated_content_claims"] is True
    assert timeline["segments"][0]["clip_id"]
    assert timeline["segments"][0]["timeline_start"] == 0.0
    assert {segment["structural_role"] for segment in timeline["segments"]} == {
        "hook",
        "build",
        "payoff",
    }
    assert all(segment["clip_score_id"] for segment in timeline["segments"])
    assert all(segment["keep_reason"] for segment in timeline["segments"])
    assert len(timeline["continuity_checks"]) == len(timeline["segments"]) - 1
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
    review = (tmp_path / "output" / "timeline_review.md").read_text(encoding="utf-8")
    assert "Structural roles: `build, hook, payoff`" in review


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


def test_sound_decision_documents_audio_bgm_and_silence_strategy(tmp_path, capsys):
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

    code = main(["sound", "--project", str(project_path), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 1
    assert payload["output"] == ".artist-portrait/data/sound_decision.json"
    assert payload["report"] == "output/sound_decision.md"
    decision = payload["sound_decision"]
    assert decision["selected_strategy"] == "needs_user_bgm_input"
    assert decision["timeline_ref"] == "output/timeline_draft.json"
    assert decision["edit_brief_ref"] == ".artist-portrait/data/edit_brief.json"
    modes = {item["mode"]: item for item in decision["input_modes"]}
    assert modes["original_audio"]["status"] == "missing"
    assert modes["direct_bgm"]["status"] == "missing"
    assert modes["video_extracted_mixed_audio"]["status"] == "missing"
    assert modes["source_embedded_audio"]["status"] == "missing"
    assert modes["silence"]["status"] == "available"
    assert decision["beat_status"] == "unavailable"
    assert decision["automatic_music_selection"] is False
    assert decision["automatic_bgm_fit"] is False
    assert decision["media_rendered"] is False
    assert decision["network_performed"] is False
    assert any("no BGM candidate" in warning for warning in decision["warnings"])
    report = (tmp_path / "output" / "sound_decision.md").read_text(encoding="utf-8")
    assert "Beat fallback" in report


def test_sound_decision_warns_for_video_extracted_mixed_audio(tmp_path, capsys):
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
    media = tmp_path / "media" / "mixed_bgm.mp4"
    media.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc=size=64x64:rate=24:duration=1",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(media),
        ],
        check=True,
    )
    assert (
        main(
            [
                "bgm",
                "import",
                "--project",
                str(project_path),
                "--file",
                "media/mixed_bgm.mp4",
                "--rights-status",
                "owned",
                "--quiet",
            ]
        )
        == 1
    )

    code = main(["sound", "--project", str(project_path), "--json"])
    decision = json.loads(capsys.readouterr().out)["sound_decision"]

    assert code == 1
    modes = {item["mode"]: item for item in decision["input_modes"]}
    assert modes["video_extracted_mixed_audio"]["status"] == "warning"
    assert decision["video_extracted_mixed_audio_candidate_count"] == 1
    assert decision["mixed_audio_warning_count"] == 1
    assert any("mixed audio" in warning for warning in decision["warnings"])


def test_sound_decision_warns_for_source_embedded_mixed_audio(tmp_path, capsys):
    project_path = build_valid_proposal_project(tmp_path, capsys)
    assert main(["timeline", "--project", str(project_path), "--proposal", "proposal_safe", "--quiet"]) in (0, 1)
    source_id = read_sources_jsonl(tmp_path / ".artist-portrait" / "data" / "sources.jsonl")[0].source_id
    source_media = tmp_path / "media" / "clean.mp4"
    source_media.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "testsrc=size=64x64:rate=24:duration=1",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
        "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(source_media),
    ], check=True)
    assert main([
        "bgm", "import", "--project", str(project_path), "--source-id", source_id,
        "--rights-status", "owned", "--quiet",
    ]) == 1

    code = main(["sound", "--project", str(project_path), "--json"])
    decision = json.loads(capsys.readouterr().out)["sound_decision"]
    modes = {item["mode"]: item for item in decision["input_modes"]}

    assert code == 1
    assert modes["source_embedded_audio"]["status"] == "warning"
    assert decision["source_embedded_audio_candidate_count"] == 1
    assert decision["mixed_audio_warning_count"] == 1


def test_timeline_build_and_review_honor_restricted_rights_override(tmp_path, capsys):
    project_path = build_valid_proposal_project(tmp_path, capsys)
    project_path.write_text(
        project_path.read_text(encoding="utf-8").replace(
            "allow_restricted_rights: false", "allow_restricted_rights: true"
        ),
        encoding="utf-8",
    )
    sources_path = tmp_path / ".artist-portrait" / "data" / "sources.jsonl"
    sources = read_sources_jsonl(sources_path)
    sources[0].rights_status.value = RightsStatus.restricted
    sources_path.write_text("".join(item.model_dump_json() + "\n" for item in sources), encoding="utf-8")

    assert main(["timeline", "--project", str(project_path), "--proposal", "proposal_safe", "--quiet"]) in (0, 1)
    assert main(["review", "--project", str(project_path), "--scope", "timeline", "--quiet"]) in (0, 1)
    validation = json.loads((tmp_path / ".artist-portrait" / "data" / "timeline_validation.json").read_text(encoding="utf-8"))

    assert "timeline_restricted_rights" not in {item["code"] for item in validation["issues"]}


def test_acceptance_rejects_blocked_workspace_state(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text((FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    state_path = tmp_path / ".artist-portrait" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["overall_status"] = "blocked"
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    assert main(["acceptance", "--project", str(project_path), "--profile", "core", "--json"]) != 0
    report = json.loads(capsys.readouterr().out)["acceptance"]
    workspace_stage = next(item for item in report["stages"] if item["stage_id"] == "workspace_state")

    assert workspace_stage["status"] == "failed"
    assert {item["code"] for item in workspace_stage["issues"]} == {"workspace_blocked"}


def test_cut_review_requires_sound_decision(tmp_path, capsys):
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

    code = main(["cut-review", "--project", str(project_path)])
    captured = capsys.readouterr()

    assert code == 7
    assert "requires sound decision" in captured.err


def test_cut_review_writes_second_pass_aesthetic_plan(tmp_path, capsys):
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
    assert main(["sound", "--project", str(project_path), "--quiet"]) in (0, 1)
    capsys.readouterr()

    code = main(["cut-review", "--project", str(project_path), "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 1
    assert payload["output"] == ".artist-portrait/data/cut_review.json"
    assert payload["report"] == "output/cut_review.md"
    review = payload["cut_review"]
    assert review["reviewed_media_scope"] == "timeline_only"
    assert review["timeline_ref"] == "output/timeline_draft.json"
    assert review["sound_decision_id"]
    assert review["issue_count"] >= 1
    assert review["second_pass_action_count"] >= 1
    assert {issue["domain"] for issue in review["issues"]} >= {"rhythm", "media_qc"}
    assert {action["action_type"] for action in review["second_pass_actions"]} >= {
        "adjust_transition",
        "rerender_preview",
    }
    assert review["media_rendered"] is False
    assert review["timeline_mutated"] is False
    assert review["edit_points_moved"] is False
    assert review["automatic_music_selection"] is False
    assert review["network_performed"] is False
    report = (tmp_path / "output" / "cut_review.md").read_text(encoding="utf-8")
    assert "Second-Pass Actions" in report


def test_revision_requires_cut_review(tmp_path, capsys):
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
    assert main(["sound", "--project", str(project_path), "--quiet"]) in (0, 1)
    capsys.readouterr()

    code = main(["revise", "--project", str(project_path), "--intent", "make it shorter"])
    captured = capsys.readouterr()

    assert code == 7
    assert "requires cut-review" in captured.err


def test_revision_plan_classifies_note_and_compares_versions(tmp_path, capsys):
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
    assert main(["sound", "--project", str(project_path), "--quiet"]) in (0, 1)
    assert main(["cut-review", "--project", str(project_path), "--quiet"]) in (0, 1)
    capsys.readouterr()

    timeline_before = (tmp_path / "output" / "timeline_draft.json").read_bytes()
    timeline = json.loads(timeline_before)
    keep_segment_id = timeline["segments"][0]["segment_id"]
    code = main(
        [
            "revise",
            "--project",
            str(project_path),
            "--intent",
            "make it shorter but keep the opening segment",
            "--request-type",
            "shorter",
            "--keep-segment",
            keep_segment_id,
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 1
    assert payload["output"] == ".artist-portrait/data/revision_plan.json"
    assert payload["report"] == "output/revision_plan.md"
    plan = payload["revision_plan"]
    assert plan["status"] == "warning"
    assert plan["intent"]["request_type"] == "shorter"
    assert plan["intent"]["keep_segment_ids"] == [keep_segment_id]
    assert plan["timeline_ref"] == "output/timeline_draft.json"
    assert plan["cut_review_ref"] == ".artist-portrait/data/cut_review.json"
    assert plan["current_duration_seconds"] == timeline["actual_duration"]
    assert {candidate["version_id"] for candidate in plan["version_candidates"]} == {
        "current_version",
        "revision_candidate_1",
    }
    assert plan["comparison"]["baseline_version_id"] == "current_version"
    assert plan["comparison"]["recommended_version_id"] == "revision_candidate_1"
    assert {action["action_type"] for action in plan["actions"]} >= {"trim", "keep"}
    assert plan["media_rendered"] is False
    assert plan["timeline_mutated"] is False
    assert plan["edit_points_moved"] is False
    assert plan["automatic_music_selection"] is False
    assert plan["model_call_performed_by_cli"] is False
    assert plan["network_performed"] is False
    assert (tmp_path / "output" / "timeline_draft.json").read_bytes() == timeline_before
    report = (tmp_path / "output" / "revision_plan.md").read_text(encoding="utf-8")
    assert "Version Comparison" in report
    assert "Manual Revision Actions" in report


def test_revision_plan_expands_compound_semantics_and_tracks_application(tmp_path, capsys):
    project_path = build_valid_proposal_project(tmp_path, capsys)
    assert main(["timeline", "--project", str(project_path), "--proposal", "proposal_safe", "--quiet"]) in (0, 1)
    assert main(["sound", "--project", str(project_path), "--quiet"]) in (0, 1)
    assert main(["cut-review", "--project", str(project_path), "--quiet"]) in (0, 1)
    capsys.readouterr()

    note = "整体更高级一点，节奏快点，少点字，别压人声，结尾更有力量"
    assert main(["revise", "--project", str(project_path), "--intent", note, "--json"]) in (0, 1)
    plan = json.loads(capsys.readouterr().out)["revision_plan"]
    assert set(plan["covered_domains"]) >= {"style", "rhythm", "text", "source_audio", "ending"}
    assert {item["action_type"] for item in plan["actions"]} >= {
        "refine_style", "accelerate_pacing", "reduce_subtitles", "protect_voice", "replace_ending"
    }
    assert all(item["acceptance_observations"] for item in plan["actions"])

    assert main([
        "apply-revision", "--project", str(project_path),
        "--version-id", "revision_candidate_1", "--json",
    ]) in (0, 1)
    application = json.loads(capsys.readouterr().out)["revision_application"]
    outcomes = {item["domain"]: item["status"] for item in application["semantic_outcomes"]}
    assert set(outcomes) >= {"style", "rhythm", "text", "source_audio", "ending"}
    assert set(outcomes.values()) <= {"applied", "partially_applied", "manual_only", "not_selected", "blocked"}
    assert all(item["acceptance_observations"] for item in application["semantic_outcomes"])


def test_apply_revision_requires_revision_plan(tmp_path, capsys):
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
    assert main(["sound", "--project", str(project_path), "--quiet"]) in (0, 1)
    assert main(["cut-review", "--project", str(project_path), "--quiet"]) in (0, 1)
    capsys.readouterr()

    code = main(
        [
            "apply-revision",
            "--project",
            str(project_path),
            "--version-id",
            "revision_candidate_1",
        ]
    )
    captured = capsys.readouterr()

    assert code == 7
    assert "requires revise" in captured.err


def test_apply_revision_rejects_current_version(tmp_path, capsys):
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
    assert main(["sound", "--project", str(project_path), "--quiet"]) in (0, 1)
    assert main(["cut-review", "--project", str(project_path), "--quiet"]) in (0, 1)
    assert (
        main(
            [
                "revise",
                "--project",
                str(project_path),
                "--intent",
                "make it shorter",
                "--request-type",
                "shorter",
                "--quiet",
            ]
        )
        in (0, 1)
    )
    capsys.readouterr()

    code = main(
        [
            "apply-revision",
            "--project",
            str(project_path),
            "--version-id",
            "current_version",
        ]
    )
    captured = capsys.readouterr()

    assert code == 9
    assert "non-current revision candidate" in captured.err


def test_apply_revision_builds_candidate_without_mutating_timeline(tmp_path, capsys):
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
    assert main(["sound", "--project", str(project_path), "--quiet"]) in (0, 1)
    assert main(["cut-review", "--project", str(project_path), "--quiet"]) in (0, 1)
    assert (
        main(
            [
                "revise",
                "--project",
                str(project_path),
                "--intent",
                "make it shorter",
                "--request-type",
                "shorter",
                "--quiet",
            ]
        )
        in (0, 1)
    )
    capsys.readouterr()

    timeline_path = tmp_path / "output" / "timeline_draft.json"
    timeline_before = timeline_path.read_bytes()
    baseline = json.loads(timeline_before)
    code = main(
        [
            "apply-revision",
            "--project",
            str(project_path),
            "--version-id",
            "revision_candidate_1",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code in (0, 1)
    assert payload["output"] == ".artist-portrait/data/revision_application.json"
    assert payload["report"] == "output/revision_application.md"
    application = payload["revision_application"]
    assert application["selected_version_id"] == "revision_candidate_1"
    assert application["baseline_timeline_ref"] == "output/timeline_draft.json"
    assert application["revision_plan_ref"] == ".artist-portrait/data/revision_plan.json"
    assert application["current_duration_seconds"] == baseline["actual_duration"]
    assert application["revised_duration_seconds"] < baseline["actual_duration"]
    assert application["applied_action_count"] >= 1
    assert application["baseline_segment_count"] == len(baseline["segments"])
    assert application["revised_segment_count"] == len(application["revised_segments"])
    assert any(result["status"] == "applied" for result in application["action_results"])
    assert any(change["status"] == "trimmed" for change in application["segment_changes"])
    assert application["media_rendered"] is False
    assert application["canonical_timeline_mutated"] is False
    assert application["canonical_edit_points_moved"] is False
    assert application["revised_candidate_edit_points_changed"] is True
    assert application["automatic_music_selection"] is False
    assert application["automatic_bgm_fit"] is False
    assert application["model_call_performed_by_cli"] is False
    assert application["network_performed"] is False
    assert timeline_path.read_bytes() == timeline_before
    report = (tmp_path / "output" / "revision_application.md").read_text(encoding="utf-8")
    assert "Action Results" in report
    assert "Segment Changes" in report


def test_promote_revision_requires_matching_application_id(tmp_path, capsys):
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
    assert main(["sound", "--project", str(project_path), "--quiet"]) in (0, 1)
    assert main(["cut-review", "--project", str(project_path), "--quiet"]) in (0, 1)
    assert (
        main(
            [
                "revise",
                "--project",
                str(project_path),
                "--intent",
                "make it shorter",
                "--request-type",
                "shorter",
                "--quiet",
            ]
        )
        in (0, 1)
    )
    assert (
        main(
            [
                "apply-revision",
                "--project",
                str(project_path),
                "--version-id",
                "revision_candidate_1",
                "--quiet",
            ]
        )
        in (0, 1)
    )
    capsys.readouterr()

    code = main(
        [
            "promote-revision",
            "--project",
            str(project_path),
            "--revision-application-id",
            "revision_application_missing",
        ]
    )
    captured = capsys.readouterr()

    assert code == 9
    assert "does not match" in captured.err


def test_promote_revision_mutates_canonical_timeline_and_invalidates_downstream(tmp_path, capsys):
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
    assert main(["sound", "--project", str(project_path), "--quiet"]) in (0, 1)
    assert main(["cut-review", "--project", str(project_path), "--quiet"]) in (0, 1)
    assert (
        main(
            [
                "revise",
                "--project",
                str(project_path),
                "--intent",
                "make it shorter",
                "--request-type",
                "shorter",
                "--quiet",
            ]
        )
        in (0, 1)
    )
    capsys.readouterr()

    timeline_path = tmp_path / "output" / "timeline_draft.json"
    before_bytes = timeline_path.read_bytes()
    baseline = json.loads(before_bytes)
    assert (
        main(
            [
                "apply-revision",
                "--project",
                str(project_path),
                "--version-id",
                "revision_candidate_1",
                "--json",
            ]
        )
        in (0, 1)
    )
    application = json.loads(capsys.readouterr().out)["revision_application"]

    code = main(
        [
            "promote-revision",
            "--project",
            str(project_path),
            "--revision-application-id",
            application["revision_application_id"],
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code in (0, 1)
    assert payload["timeline"] == "output/timeline_draft.json"
    assert payload["output"] == ".artist-portrait/data/revision_promotion.json"
    assert payload["report"] == "output/revision_promotion.md"
    promotion = payload["revision_promotion"]
    promoted = json.loads(timeline_path.read_text(encoding="utf-8"))
    assert timeline_path.read_bytes() != before_bytes
    assert promoted["timeline_id"] == promotion["promoted_timeline_id"]
    assert promoted["timeline_id"] != baseline["timeline_id"]
    assert promoted["actual_duration"] == application["revised_duration_seconds"]
    assert len(promoted["segments"]) == application["revised_segment_count"]
    assert promoted["media_rendered"] is False
    assert promoted["automatic_music_selection"] is False
    assert promotion["revision_application_id"] == application["revision_application_id"]
    assert promotion["baseline_timeline_id"] == baseline["timeline_id"]
    assert promotion["canonical_timeline_mutated"] is True
    assert promotion["canonical_edit_points_moved"] is True
    assert promotion["media_rendered"] is False
    assert promotion["automatic_music_selection"] is False
    assert promotion["automatic_bgm_fit"] is False
    assert promotion["model_call_performed_by_cli"] is False
    assert promotion["network_performed"] is False
    assert {item["step"] for item in promotion["invalidated_steps"]} >= {
        "sound",
        "cut_review",
        "revision",
    }
    state = json.loads((tmp_path / ".artist-portrait" / "state.json").read_text(encoding="utf-8"))
    assert state["steps"]["revision_promotion"]["status"] in {
        "completed",
        "completed_with_warnings",
    }
    assert state["steps"]["timeline"]["status"] in {
        "completed",
        "completed_with_warnings",
    }
    assert state["steps"]["sound"]["status"] == "invalidated"
    assert state["steps"]["cut_review"]["status"] == "invalidated"
    report = (tmp_path / "output" / "revision_promotion.md").read_text(encoding="utf-8")
    assert "Revision Promotion" in report
    assert "Invalidated Steps" in report


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
        main(["bgm", "rhythm", "--project", str(project_path), "--json"])
        == 1
    )
    bgm_rhythm_payload = json.loads(capsys.readouterr().out)
    bgm_rhythm = bgm_rhythm_payload["bgm_rhythm_intelligence"]
    assert bgm_rhythm_payload["output"] == ".artist-portrait/data/bgm_rhythm_intelligence.json"
    assert bgm_rhythm_payload["report"] == "output/bgm_rhythm_intelligence.md"
    assert bgm_rhythm_payload["handoff"] == "output/bgm_rhythm_handoff.json"
    assert bgm_rhythm["automatic_music_selection"] is False
    assert bgm_rhythm["edit_points_moved"] is False
    assert bgm_rhythm["media_rendered"] is False
    assert bgm_rhythm["network_performed"] is False
    assert bgm_rhythm["fabricated_bpm_or_beats"] is False
    assert bgm_rhythm["candidate_count"] == 1
    assert bgm_rhythm["usable_beat_candidate_count"] == 0
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
    assert plan["bgm_rhythm_intelligence_fingerprint"]
    assert plan["timeline_profile"]["metrics"]
    assert plan["bgm_profile"]["metrics"]
    bgm_metrics = {
        metric["metric_id"]: metric
        for metric in plan["bgm_profile"]["metrics"]
    }
    assert bgm_metrics["bgm_rhythm_status"]["value"] == "warning"
    assert bgm_metrics["usable_beat_candidate_count"]["value"] == 0
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

    assert (
        main(["rhythm", "--project", str(project_path), "--edit-guidance", "--json"])
        == 1
    )
    guidance_payload = json.loads(capsys.readouterr().out)
    guidance = guidance_payload["edit_guidance"]
    assert guidance_payload["output"] == ".artist-portrait/data/edit_guidance.json"
    assert guidance_payload["report"] == "output/edit_guidance.md"
    assert guidance_payload["handoff"] == "output/edit_guidance_handoff.json"
    assert guidance["action_count"] >= 10
    assert guidance["manual_only"] is True
    assert {action["category"] for action in guidance["actions"]} >= {
        "subtitle",
        "transition",
        "pause",
        "ducking",
        "phrase",
        "cut_review",
        "ending",
        "qc_repair",
        "handoff",
    }
    assert all(action["manual_only"] is True for action in guidance["actions"])
    assert all(action["edits_applied"] is False for action in guidance["actions"])
    assert guidance["automatic_music_selection"] is False
    assert guidance["edit_points_moved"] is False
    assert guidance["timeline_mutated"] is False
    assert guidance["media_rendered"] is False
    assert guidance["model_call_performed_by_cli"] is False
    assert guidance["network_performed"] is False
    assert (tmp_path / ".artist-portrait" / "data" / "edit_guidance.json").exists()
    assert (tmp_path / "output" / "edit_guidance.md").exists()
    assert (tmp_path / "output" / "edit_guidance_handoff.json").exists()

    assert (
        main(["operator", "--project", str(project_path), "--target", "delivery", "--json"])
        in (0, 1)
    )
    operator_payload = json.loads(capsys.readouterr().out)
    assert operator_payload["output"] == ".artist-portrait/data/operator_runbook.json"

    assert main(["editor-package", "--project", str(project_path), "--json"]) in (0, 1)
    editor_payload = json.loads(capsys.readouterr().out)
    editor_package = editor_payload["editor_package"]
    assert editor_payload["output"] == ".artist-portrait/data/editor_package.json"
    assert editor_payload["report"] == "output/editor_package.md"
    assert editor_payload["cue_sheet"] == "output/cue_sheet.csv"
    assert editor_payload["handoff"] == "output/editor_handoff.json"
    assert editor_package["timeline_id"] == plan["timeline_id"]
    assert editor_package["timeline_item_count"] >= 1
    assert editor_package["audio_item_count"] >= 3
    assert editor_package["manual_action_count"] == guidance["action_count"]
    assert editor_package["cue_sheet_row_count"] >= (
        editor_package["timeline_item_count"]
        + editor_package["audio_item_count"]
        + editor_package["manual_action_count"]
    )
    assert {item["category"] for item in editor_package["audio_items"]} >= {
        "bgm_segment",
        "ducking",
        "fade",
        "gain",
        "beat_alignment",
    }
    assert {action["category"] for action in editor_package["manual_actions"]} >= {
        "subtitle",
        "ducking",
        "handoff",
    }
    assert editor_package["commands_executed"] is False
    assert editor_package["media_rendered"] is False
    assert editor_package["timeline_mutated"] is False
    assert editor_package["edit_points_moved"] is False
    assert editor_package["automatic_music_selection"] is False
    assert editor_package["automatic_bgm_fit"] is False
    assert editor_package["model_call_performed_by_cli"] is False
    assert editor_package["network_performed"] is False
    assert editor_package["image_generation_or_editing_used"] is False
    cue_sheet = (tmp_path / "output" / "cue_sheet.csv").read_text(encoding="utf-8")
    assert "row_type,item_id,order,timeline_start,timeline_end,track,source,instruction,evidence_refs" in cue_sheet
    assert "manual_action" in cue_sheet
    assert (tmp_path / ".artist-portrait" / "data" / "editor_package.json").exists()
    assert (tmp_path / "output" / "editor_package.md").exists()
    assert (tmp_path / "output" / "editor_handoff.json").exists()

    assert main(["nle-plan", "--project", str(project_path), "--target", "all", "--json"]) in (0, 1)
    nle_payload = json.loads(capsys.readouterr().out)
    nle_plan = nle_payload["nle_interchange_plan"]
    assert nle_payload["output"] == ".artist-portrait/data/nle_interchange_plan.json"
    assert nle_payload["report"] == "output/nle_interchange_plan.md"
    assert nle_payload["mapping_csv"] == "output/nle_interchange_map.csv"
    assert nle_payload["handoff"] == "output/nle_interchange_handoff.json"
    assert nle_plan["target"] == "all"
    assert nle_plan["editor_package_id"] == editor_package["editor_package_id"]
    assert nle_plan["timeline_mapping_count"] >= editor_package["timeline_item_count"] * 3
    assert nle_plan["audio_mapping_count"] >= editor_package["audio_item_count"] * 3
    assert nle_plan["marker_mapping_count"] >= editor_package["manual_action_count"] * 3
    assert {summary["target"] for summary in nle_plan["target_summaries"]} == {
        "fcpxml",
        "edl",
        "resolve_csv",
    }
    assert {mapping["target"] for mapping in nle_plan["timeline_mappings"]} == {
        "fcpxml",
        "edl",
        "resolve_csv",
    }
    assert any(mapping["compatibility"] == "warning" for mapping in nle_plan["audio_mappings"])
    assert any(mapping["compatibility"] == "warning" for mapping in nle_plan["marker_mappings"])
    assert nle_plan["commands_executed"] is False
    assert nle_plan["media_rendered"] is False
    assert nle_plan["timeline_mutated"] is False
    assert nle_plan["edit_points_moved"] is False
    assert nle_plan["nle_project_written"] is False
    assert nle_plan["automatic_music_selection"] is False
    assert nle_plan["automatic_bgm_fit"] is False
    assert nle_plan["model_call_performed_by_cli"] is False
    assert nle_plan["network_performed"] is False
    assert nle_plan["image_generation_or_editing_used"] is False
    nle_csv = (tmp_path / "output" / "nle_interchange_map.csv").read_text(encoding="utf-8")
    assert "row_type,target,mapping_id,source_id,order,timeline_start,timeline_end,record_in,record_out,compatibility,instruction,warnings,evidence_refs" in nle_csv
    assert "timeline" in nle_csv
    assert "audio" in nle_csv
    assert "marker" in nle_csv
    assert (tmp_path / ".artist-portrait" / "data" / "nle_interchange_plan.json").exists()
    assert (tmp_path / "output" / "nle_interchange_plan.md").exists()
    assert (tmp_path / "output" / "nle_interchange_handoff.json").exists()

    assert main(["fcpxml", "--project", str(project_path), "--draft", "--json"]) in (0, 1)
    fcpxml_payload = json.loads(capsys.readouterr().out)
    fcpxml_draft = fcpxml_payload["fcpxml_draft"]
    fcpxml_validation = fcpxml_payload["fcpxml_validation"]
    assert fcpxml_payload["output"] == ".artist-portrait/data/fcpxml_draft.json"
    assert fcpxml_payload["fcpxml"] == "output/draft.fcpxml"
    assert fcpxml_payload["validation"] == ".artist-portrait/data/fcpxml_validation.json"
    assert fcpxml_payload["report"] == "output/fcpxml_review.md"
    assert fcpxml_payload["handoff"] == "output/fcpxml_handoff.json"
    assert fcpxml_draft["nle_plan_id"] == nle_plan["nle_plan_id"]
    assert fcpxml_draft["clip_count"] >= editor_package["timeline_item_count"]
    assert fcpxml_draft["marker_count"] >= editor_package["manual_action_count"]
    assert fcpxml_draft["audio_note_count"] >= editor_package["audio_item_count"]
    assert fcpxml_draft["relink_required"] is True
    assert fcpxml_draft["import_verified"] is False
    assert fcpxml_draft["commands_executed"] is False
    assert fcpxml_draft["media_rendered"] is False
    assert fcpxml_draft["timeline_mutated"] is False
    assert fcpxml_draft["edit_points_moved"] is False
    assert fcpxml_draft["nle_import_performed"] is False
    assert fcpxml_draft["automatic_music_selection"] is False
    assert fcpxml_draft["automatic_bgm_fit"] is False
    assert fcpxml_draft["model_call_performed_by_cli"] is False
    assert fcpxml_draft["network_performed"] is False
    assert fcpxml_draft["image_generation_or_editing_used"] is False
    assert fcpxml_validation["xml_parse_passed"] is True
    assert fcpxml_validation["import_verified"] is False
    fcpxml_text = (tmp_path / "output" / "draft.fcpxml").read_text(encoding="utf-8")
    assert "ARTIST_PORTRAIT_RELINK_REQUIRED" in fcpxml_text
    ET.fromstring(fcpxml_text.split("\n", 2)[2])
    assert (tmp_path / ".artist-portrait" / "data" / "fcpxml_draft.json").exists()
    assert (tmp_path / ".artist-portrait" / "data" / "fcpxml_validation.json").exists()
    assert (tmp_path / "output" / "fcpxml_review.md").exists()
    assert (tmp_path / "output" / "fcpxml_handoff.json").exists()

    import_review_candidate = tmp_path / "fcpxml_import_review_candidate.json"
    import_review_candidate.write_text(
        json.dumps(
            {
                "import_review_id": "fcpxml_import_review_candidate_safe",
                "project_id": fcpxml_draft["project_id"],
                "fcpxml_draft_id": fcpxml_draft["fcpxml_draft_id"],
                "nle_plan_id": fcpxml_draft["nle_plan_id"],
                "reviewed_by": "integration-test",
                "application_name": "Final Cut Pro",
                "application_version": "external-review",
                "import_attempted": True,
                "import_succeeded": True,
                "relink_attempted": True,
                "relink_succeeded": False,
                "relink_missing_count": 1,
                "timeline_opened": True,
                "playback_checked": False,
                "issue_count": 1,
                "issues": [
                    {
                        "issue_id": "relink_required",
                        "severity": "warning",
                        "category": "asset_relink",
                        "detail": "Draft imported, but placeholder assets require manual relink.",
                    }
                ],
                "evidence_refs": ["manual external import review"],
                "media_rendered": False,
                "timeline_mutated": False,
                "edit_points_moved": False,
                "automatic_music_selection": False,
                "automatic_bgm_fit": False,
                "model_call_performed_by_cli": False,
                "network_performed": False,
                "image_generation_or_editing_used": False,
            }
        ),
        encoding="utf-8",
    )
    assert (
        main(
            [
                "fcpxml",
                "--project",
                str(project_path),
                "--import-review",
                str(import_review_candidate),
                "--json",
            ]
        )
        in (0, 1)
    )
    import_review_payload = json.loads(capsys.readouterr().out)
    import_review = import_review_payload["fcpxml_import_review"]
    assert import_review_payload["output"] == ".artist-portrait/data/fcpxml_import_review.json"
    assert import_review_payload["report"] == "output/fcpxml_import_review.md"
    assert import_review_payload["handoff"] == "output/fcpxml_import_review_handoff.json"
    assert import_review["binding_status"] == "matched"
    assert import_review["status"] == "warning"
    assert import_review["import_attempted"] is True
    assert import_review["import_success_claimed"] is True
    assert import_review["import_success_accepted_as_project_success"] is False
    assert import_review["relink_success_claimed"] is False
    assert import_review["commands_executed"] is False
    assert import_review["media_rendered"] is False
    assert import_review["timeline_mutated"] is False
    assert import_review["edit_points_moved"] is False
    assert import_review["automatic_music_selection"] is False
    assert import_review["automatic_bgm_fit"] is False
    assert import_review["model_call_performed_by_cli"] is False
    assert import_review["network_performed"] is False
    assert import_review["image_generation_or_editing_used"] is False
    assert (tmp_path / ".artist-portrait" / "data" / "fcpxml_import_review.json").exists()
    assert (
        tmp_path / ".artist-portrait" / "data" / "fcpxml_import_review_candidate_quarantine.json"
    ).exists()
    assert (tmp_path / "output" / "fcpxml_import_review.md").exists()
    assert (tmp_path / "output" / "fcpxml_import_review_handoff.json").exists()

    assert main(["fcpxml", "--project", str(project_path), "--repair-plan", "--json"]) in (0, 1)
    repair_payload = json.loads(capsys.readouterr().out)
    repair_plan = repair_payload["fcpxml_repair_plan"]
    assert repair_payload["output"] == ".artist-portrait/data/fcpxml_repair_plan.json"
    assert repair_payload["report"] == "output/fcpxml_repair_plan.md"
    assert repair_payload["handoff"] == "output/fcpxml_repair_handoff.json"
    assert repair_plan["fcpxml_draft_id"] == fcpxml_draft["fcpxml_draft_id"]
    assert repair_plan["fcpxml_import_review_id"] == import_review["review_id"]
    assert repair_plan["status"] == "warning"
    assert repair_plan["action_count"] >= 3
    assert repair_plan["required_action_count"] >= 2
    assert repair_plan["optional_action_count"] >= 1
    assert repair_plan["relink_action_count"] >= 2
    assert repair_plan["playback_review_required"] is True
    assert repair_plan["commands_executed"] is False
    assert repair_plan["media_rendered"] is False
    assert repair_plan["timeline_mutated"] is False
    assert repair_plan["edit_points_moved"] is False
    assert repair_plan["nle_import_performed"] is False
    assert repair_plan["source_relink_performed"] is False
    assert repair_plan["automatic_music_selection"] is False
    assert repair_plan["automatic_bgm_fit"] is False
    assert repair_plan["model_call_performed_by_cli"] is False
    assert repair_plan["network_performed"] is False
    assert repair_plan["image_generation_or_editing_used"] is False
    assert repair_plan["repair_success_claimed"] is False
    assert (tmp_path / ".artist-portrait" / "data" / "fcpxml_repair_plan.json").exists()
    assert (tmp_path / "output" / "fcpxml_repair_plan.md").exists()
    assert (tmp_path / "output" / "fcpxml_repair_handoff.json").exists()


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
    assert accepted["required_stage_ids"][-5:] == [
        "rhythm_plan",
        "preview",
        "final_export",
        "rhythm_media_qc",
        "cut_review",
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
