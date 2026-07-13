import hashlib
import json
from pathlib import Path

import pytest

from artist_portrait_editor.cli import main
from artist_portrait_editor.v3_release import build_v3_release_audit_workspace
from artist_portrait_editor.workspace_errors import WorkspacePrerequisiteError
from artist_portrait_editor.workspace_state import init_workspace


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _workspace(tmp_path: Path) -> tuple[Path, Path]:
    project = tmp_path / "project.yaml"
    project.write_text(
        '''schema_version: "0.3"
project:
  id: release_project
  title: V3 Release Test
  artist_name: Test Subject
  language: en
creative_brief:
  theme: Release truth
  audience: Reviewers
  platform: douyin
  target_duration_seconds: 60
  aspect_ratio: "9:16"
  tone: [restrained]
content_policy:
  allow_role_dialogue: true
  allow_real_person_role_mix: true
  allow_unconfirmed_visual_material: false
  allow_interview_audio: true
  allow_music: false
  allow_restricted_rights: true
features:
  transcription: off
  scene_detection: off
  visual_analysis: off
  experimental_relations: false
data_policy:
  allow_remote_text_model: false
  allow_remote_vision_model: false
  include_absolute_paths_in_remote_requests: false
paths:
  media_dir: ./media
  annotations_dir: ./annotations
  output_dir: ./output
''',
        encoding="utf-8",
    )
    init_workspace(project)
    data = tmp_path / ".artist-portrait" / "data"
    output = tmp_path / "output"
    output.mkdir(exist_ok=True)
    media = b"real second cut bytes"
    media_path = output / "second_cut.mp4"
    media_path.write_bytes(media)
    media_hash = "sha256:" + hashlib.sha256(media).hexdigest()
    project_id = "release_project"
    strategies = []
    for index, strategy_id in enumerate(
        ("emotional_arc", "high_energy", "narrative_clarity", "portrait_highlight")
    ):
        strategies.append(
            {
                "strategy_id": strategy_id,
                "ranges": [
                    {
                        "source_id": "source-1",
                        "source_in": float(index * 10),
                        "source_out": float(index * 10 + 10),
                    }
                ],
            }
        )
    _write(data / "creative_strategy_package.json", {
        "project_id": project_id, "selected_strategy_id": None, "strategies": strategies,
    })
    _write(data / "revision_plan.json", {
        "project_id": project_id, "revision_plan_id": "revision-1",
        "intent": {"request_text": "reduce text and protect voice"},
        "semantic_clauses": [{"clause_id": "clause-1"}],
    })
    _write(data / "revision_application.json", {
        "project_id": project_id, "revision_plan_id": "revision-1",
        "canonical_timeline_mutated": False, "media_rendered": False,
        "semantic_outcomes": [{"clause_id": "clause-1", "status": "manual_only"}],
    })
    _write(data / "version_review.json", {
        "project_id": project_id, "selected_version_id": None,
        "versions": [{"version_id": "a"}, {"version_id": "b"}],
        "pairwise_comparisons": [{"left_version_id": "a", "right_version_id": "b"}],
    })
    _write(data / "publishability.json", {
        "project_id": project_id, "selected_version_id": None,
        "highest_available_tier": "manual_refinement_required",
        "versions": [
            {"tier": "manual_refinement_required", "ready_for_publish": False},
            {"tier": "unusable", "ready_for_publish": False},
        ],
    })
    nle_dir = output / "nle_roundtrip"
    nle_dir.mkdir()
    deliverables = []
    for name in (
        "timeline.fcpxml", "timeline.edl", "resolve_markers.csv",
        "premiere_markers.csv", "cue_sheet.csv", "relink_manifest.csv",
    ):
        (nle_dir / name).write_text("evidence", encoding="utf-8")
        deliverables.append({"status": "written", "ref": f"output/nle_roundtrip/{name}"})
    _write(data / "nle_roundtrip.json", {
        "project_id": project_id, "deliverables": deliverables,
        "source_bindings": [{"exists": True, "hash_matches": True}],
        "acceptance_checks": [{"status": "pending"}],
        "roundtrip_verified": False, "import_performed": False,
    })
    _write(data / "creative_memory.json", {
        "project_id": project_id, "entry_count": 2,
        "memory_applied_to_edit": False, "timeline_mutated": False,
        "media_rendered": False, "automatic_style_selection": False,
        "automatic_bgm_selection": False, "model_call_performed_by_cli": False,
        "network_performed": False,
    })
    _write(data / "second_cut_render.json", {
        "project_id": project_id, "media_valid": True,
        "output_ref": "output/second_cut.mp4", "output_hash": media_hash,
        "source_audio_retained": True, "text_applied": False,
    })
    _write(data / "bgm_match.json", {"project_id": project_id})
    _write(data / "text_timing_plan.json", {"project_id": project_id})
    _write(data / "rhythm_plan.json", {
        "project_id": project_id, "model_call_performed_by_cli": False,
        "network_performed": False,
    })
    benchmark = tmp_path / "benchmark.json"
    _write(benchmark, {
        "benchmarks": [
            {"benchmark_class": "stage_person"},
            {"benchmark_class": "interview_talking_head"},
            {"benchmark_class": "event_promo_mix"},
        ],
        "class_coverage_complete": True, "closed_loop_count": 2,
        "input_baseline_count": 1, "synthetic_fixture_counted_as_real": False,
        "distributable_media_included": False, "model_call_performed_by_cli": False,
        "network_performed_by_cli": False,
    })
    return project, benchmark


def test_v3_release_audit_closes_ten_outcomes_without_mature_editor_claim(tmp_path):
    project, benchmark = _workspace(tmp_path)
    json_path, md_path, audit, warnings = build_v3_release_audit_workspace(
        project, benchmark_pack_path=benchmark
    )

    assert json_path.exists() and md_path.exists()
    assert audit.release_version == "0.50.0"
    assert audit.status == "release_ready_with_known_gaps"
    assert audit.outcome_count == 10
    assert len({item.outcome_id for item in audit.outcomes}) == 10
    assert audit.mature_editor_claimed is False
    assert audit.selected_version_id is None
    assert audit.media_rendered is False
    assert audit.model_call_performed_by_cli is False
    assert audit.network_performed is False
    human = next(item for item in audit.outcomes if item.outcome_id == "human_revision_truth")
    assert human.status == "warning"
    assert any("manual-only" in item for item in audit.known_gaps)
    assert len(warnings) == 2


def test_v3_release_audit_blocks_stale_media_and_duplicate_strategy_signatures(tmp_path):
    project, benchmark = _workspace(tmp_path)
    data = tmp_path / ".artist-portrait" / "data"
    second = json.loads((data / "second_cut_render.json").read_text())
    second["output_hash"] = "sha256:" + "0" * 64
    _write(data / "second_cut_render.json", second)
    strategies = json.loads((data / "creative_strategy_package.json").read_text())
    strategies["strategies"][1]["ranges"] = strategies["strategies"][0]["ranges"]
    _write(data / "creative_strategy_package.json", strategies)

    _, _, audit, _ = build_v3_release_audit_workspace(
        project, benchmark_pack_path=benchmark
    )
    failed = {item.outcome_id for item in audit.outcomes if item.status == "failed"}
    assert audit.status == "blocked"
    assert failed == {"real_media_binding", "multi_version_strategies"}


def test_v3_release_audit_rejects_missing_chain_and_cli_exposes_truth(tmp_path, capsys):
    project, benchmark = _workspace(tmp_path)
    (tmp_path / ".artist-portrait" / "data" / "creative_memory.json").unlink()
    with pytest.raises(WorkspacePrerequisiteError, match="creative_memory"):
        build_v3_release_audit_workspace(project, benchmark_pack_path=benchmark)

    _write(tmp_path / ".artist-portrait" / "data" / "creative_memory.json", {
        "project_id": "release_project", "entry_count": 1,
        "memory_applied_to_edit": False, "timeline_mutated": False,
        "media_rendered": False, "automatic_style_selection": False,
        "automatic_bgm_selection": False, "model_call_performed_by_cli": False,
        "network_performed": False,
    })
    assert main([
        "v3-release-audit", "--project", str(project),
        "--benchmark-pack", str(benchmark), "--json",
    ]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["product_claim"] == "mature_assistant_workflow"
    assert payload["mature_editor_claimed"] is False
