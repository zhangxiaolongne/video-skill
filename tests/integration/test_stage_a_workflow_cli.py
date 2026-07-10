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
    assert plan["current_stage_id"] == "setup"
    assert plan["current_stage_title"] == "Project setup"
    assert plan["creator_stage_count"] >= 7
    assert plan["commands_executed"] is False
    assert plan["media_rendered"] is False
    assert plan["edit_points_moved"] is False
    assert plan["automatic_music_selection"] is False
    steps = {step["step_id"]: step for step in plan["steps"]}
    assert steps["init"]["status"] == "done"
    assert steps["scan"]["status"] == "next"
    assert steps["final_export"]["status"] == "pending"
    assert steps["operator"]["status"] == "pending"
    assert steps["editor_package"]["status"] == "pending"
    assert steps["nle_plan"]["status"] == "pending"
    assert steps["fcpxml_draft"]["status"] == "pending"
    creator_stages = {stage["stage_id"]: stage for stage in plan["creator_stages"]}
    assert creator_stages["setup"]["status"] == "current"
    assert creator_stages["editor_handoff"]["status"] == "pending"
    deliverables = {item["deliverable_id"]: item for item in plan["deliverables"]}
    assert deliverables["material_map"]["status"] == "missing"
    assert deliverables["nle_package"]["status"] == "missing"
    assert any("Direct audio" in item for item in plan["bgm_input_guidance"])
    assert any("mixed video track" in item for item in plan["bgm_input_guidance"])
    assert (tmp_path / ".artist-portrait" / "data" / "workflow_plan.json").exists()
    assert (tmp_path / "output" / "workflow_plan.md").exists()
    assert (tmp_path / "output" / "workflow_agent_handoff.json").exists()


def test_operator_cli_summarizes_next_action_and_guardrails_without_execution(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    capsys.readouterr()

    assert main(["operator", "--project", str(project_path), "--target", "delivery", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    runbook = payload["operator_runbook"]
    assert payload["output"] == ".artist-portrait/data/operator_runbook.json"
    assert payload["report"] == "output/operator_runbook.md"
    assert payload["handoff"] == "output/operator_handoff.json"
    assert payload["next_command"] == "artist-portrait scan --project <project.yaml>"
    assert runbook["target"] == "delivery"
    assert runbook["status"] == "in_progress"
    assert runbook["workflow_plan_id"]
    assert runbook["stage_count"] >= 14
    assert runbook["done_stage_count"] >= 1
    assert runbook["pending_stage_count"] >= 1
    stages = {stage["stage_id"]: stage for stage in runbook["stages"]}
    assert stages["scan"]["status"] == "current"
    assert stages["final_export"]["status"] == "pending"
    artifacts = {artifact["artifact_id"]: artifact for artifact in runbook["artifact_map"]}
    assert artifacts["workflow_plan"]["status"] == "present"
    assert artifacts["edit_guidance"]["status"] == "missing"
    bgm_modes = {item["mode"]: item for item in runbook["bgm_input_guidance"]}
    assert bgm_modes["direct_audio"]["status"] == "missing"
    assert bgm_modes["video_audio_extract"]["status"] == "missing"
    assert bgm_modes["source_embedded_audio"]["status"] == "missing"
    assert bgm_modes["no_file_yet"]["status"] == "warning"
    assert "treat mixed extracted video audio as clean BGM" in " ".join(
        runbook["forbidden_capabilities"]
    )
    assert runbook["commands_executed"] is False
    assert runbook["media_rendered"] is False
    assert runbook["timeline_mutated"] is False
    assert runbook["edit_points_moved"] is False
    assert runbook["automatic_music_selection"] is False
    assert runbook["model_call_performed_by_cli"] is False
    assert runbook["network_performed"] is False
    assert (tmp_path / ".artist-portrait" / "data" / "operator_runbook.json").exists()
    assert (tmp_path / "output" / "operator_runbook.md").exists()
    assert (tmp_path / "output" / "operator_handoff.json").exists()


def test_workflow_execution_record_review_quarantines_external_evidence(tmp_path, capsys):
    project_path = tmp_path / "project.yaml"
    project_path.write_text(project_fixture_with_scene_detection("off"), encoding="utf-8")
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)

    assert main(["workflow", "--project", str(project_path), "--target", "delivery", "--json"]) == 1
    plan = json.loads(capsys.readouterr().out)["workflow_plan"]
    record_path = tmp_path / "workflow_execution_record.json"
    record_path.write_text(
        json.dumps(
            {
                "schema_version": "0.3",
                "execution_record_id": "workflow_execution_record_test",
                "project_id": plan["project_id"],
                "workflow_plan_id": plan["workflow_plan_id"],
                "target": "delivery",
                "executed_by": "manual_editor",
                "steps": [],
            }
        ) + "\n",
        encoding="utf-8",
    )

    assert main(["workflow", "--project", str(project_path), "--target", "delivery", "--execution-record", str(record_path), "--json"]) == 1
    reviewed = json.loads(capsys.readouterr().out)

    assert reviewed["quarantine"] == ".artist-portrait/data/workflow_execution_record_quarantine.json"
    assert reviewed["workflow_execution_review"]["workflow_plan_id"] == plan["workflow_plan_id"]
    assert (tmp_path / ".artist-portrait" / "data" / "workflow_execution_review.json").exists()
    assert not (tmp_path / ".artist-portrait" / "data" / "workflow_repair_plan.json").exists()


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
    run_brief_and_score_for_propose(tmp_path, project_path)
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
    run_brief_and_score_for_propose(tmp_path, project_path)
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
    run_brief_and_score_for_propose(tmp_path, project_path)
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
    run_brief_and_score_for_propose(tmp_path, project_path)
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
    run_brief_and_score_for_propose(tmp_path, project_path)
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
