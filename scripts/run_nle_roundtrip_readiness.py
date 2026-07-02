from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from run_golden_baseline import (
    ARTIST_PORTRAIT,
    generate_bgm,
    generate_media,
    prepare_workspace,
    write_valid_proposals_from_context,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Stage 5 NLE round-trip readiness pass.")
    parser.add_argument("--workspace", required=True, help="Directory to create or reuse.")
    parser.add_argument("--keep", action="store_true", help="Keep existing workspace files.")
    parser.add_argument("--json", action="store_true", help="Print manifest JSON.")
    args = parser.parse_args(argv)

    workspace = Path(args.workspace).resolve()
    if not args.keep and workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    prepare_workspace(workspace)
    generate_media(workspace)
    manifest = run_roundtrip(workspace)
    write_manifest(workspace, manifest)
    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"NLE round-trip readiness passed: {workspace / 'output' / 'nle_roundtrip_manifest.json'}")
    return 0


def run_roundtrip(workspace: Path) -> dict:
    project = workspace / "project.yaml"
    steps: list[dict] = []

    def cli(*parts: str, expect: tuple[int, ...] = (0,)) -> dict | None:
        command = [str(ARTIST_PORTRAIT), *parts]
        completed = subprocess.run(command, cwd=workspace, capture_output=True, text=True)
        steps.append({"command": " ".join(["artist-portrait", *parts]), "exit_code": completed.returncode})
        if completed.returncode not in expect:
            raise SystemExit(
                f"command failed in NLE round-trip readiness: {' '.join(command)}\n"
                f"exit={completed.returncode}\nstdout={completed.stdout}\nstderr={completed.stderr}"
            )
        if "--json" in parts:
            return json.loads(completed.stdout)
        return None

    cli("init", "--project", str(project), "--quiet")
    cli("scan", "--project", str(project), "--quiet")
    cli("segment", "--project", str(project), "--quiet")
    cli("keyframes", "--project", str(project), "--quiet", expect=(0, 1))
    cli("analyze", "--project", str(project), "--quiet")
    cli("map", "--project", str(project), "--quiet")
    cli("propose", "--project", str(project), "--json", expect=(1,))
    write_valid_proposals_from_context(workspace)
    candidate = workspace / "proposal_candidate.json"
    canonical = workspace / ".artist-portrait" / "data" / "proposals.json"
    candidate.write_bytes(canonical.read_bytes())
    canonical.unlink()
    cli("propose", "--project", str(project), "--agent-output", str(candidate), "--quiet", expect=(0, 1))
    cli("timeline", "--project", str(project), "--proposal", "proposal_safe", "--quiet", expect=(0, 1))

    generate_bgm(workspace)
    bgm_import = cli(
        "bgm",
        "import",
        "--project",
        str(project),
        "--file",
        "media/uploaded_bgm.wav",
        "--rights-status",
        "owned",
        "--json",
        expect=(0, 1),
    )
    candidate_id = bgm_import["candidate"]["music_candidate_id"]
    cli("bgm", "analyze", "--project", str(project), "--json", expect=(0, 1))
    cli("bgm", "rhythm", "--project", str(project), "--json", expect=(0, 1))
    cli(
        "bgm",
        "fit",
        "--project",
        str(project),
        "--candidate",
        candidate_id,
        "--fit-mode",
        "loop",
        "--ducking-gain-db",
        "-10",
        "--quiet",
        expect=(0, 1),
    )
    cli("bgm", "review", "--project", str(project), "--json", expect=(0, 1))
    cli(
        "rhythm",
        "--project",
        str(project),
        "--intent",
        str(workspace / "annotations" / "rhythm_intent.json"),
        "--json",
        expect=(0, 1),
    )
    cli("rhythm", "--project", str(project), "--edit-guidance", "--json", expect=(0, 1))
    cli("preview", "--project", str(project), "--width", "320", "--fps", "10", "--quiet", expect=(0, 1))
    cli("rhythm", "--project", str(project), "--qc", "--json", expect=(0, 1))
    cli("acceptance", "--project", str(project), "--profile", "preview", "--json", expect=(0, 9))
    cli("export", "--project", str(project), "--profile", "review_720p", "--quiet", expect=(0, 1))
    cli("rhythm", "--project", str(project), "--qc", "--json", expect=(0, 1))
    delivery_acceptance = cli("acceptance", "--project", str(project), "--profile", "delivery", "--json", expect=(0, 9))
    if delivery_acceptance["final_export_ready"] is not True:
        raise SystemExit("delivery media was not ready before NLE round-trip")

    operator_before = cli("operator", "--project", str(project), "--target", "delivery", "--json", expect=(0, 1))
    editor = cli("editor-package", "--project", str(project), "--json", expect=(0, 1))
    nle = cli("nle-plan", "--project", str(project), "--target", "all", "--json", expect=(0, 1))
    fcpxml = cli("fcpxml", "--project", str(project), "--draft", "--json", expect=(0, 1))

    draft = fcpxml["fcpxml_draft"]
    validation = fcpxml["fcpxml_validation"]
    nle_plan = nle["nle_interchange_plan"]
    assert_true(validation["xml_parse_passed"], "FCPXML XML parse")
    assert_true(draft["relink_required"], "FCPXML relink required")
    assert_false(draft["import_verified"], "FCPXML import verified by CLI")
    assert_false(nle_plan["nle_project_written"], "NLE project written by CLI")

    import_candidate = write_import_review_candidate(
        workspace=workspace,
        project_id=draft["project_id"],
        fcpxml_draft_id=draft["fcpxml_draft_id"],
        nle_plan_id=draft["nle_plan_id"],
    )
    import_review = cli(
        "fcpxml",
        "--project",
        str(project),
        "--import-review",
        str(import_candidate),
        "--json",
        expect=(0, 1),
    )
    review = import_review["fcpxml_import_review"]
    assert_equal(review["status"], "warning", "import review status")
    assert_equal(review["binding_status"], "matched", "import review binding")
    assert_true(review["import_attempted"], "import attempted")
    assert_true(review["import_success_claimed"], "import success claim")
    assert_false(review["relink_success_claimed"], "relink success claim")
    assert_false(review["import_success_accepted_as_project_success"], "import success promoted")

    repair_plan = cli("fcpxml", "--project", str(project), "--repair-plan", "--json", expect=(0, 1))
    plan = repair_plan["fcpxml_repair_plan"]
    if plan["required_action_count"] < 1 or plan["relink_action_count"] < 1:
        raise SystemExit("FCPXML repair plan did not require relink actions")

    approval_request = cli("fcpxml", "--project", str(project), "--approval-request", "--json", expect=(0, 1))
    approved_ids = approval_request["fcpxml_repair_approval_request"]["required_action_ids"]
    if not approved_ids:
        raise SystemExit("FCPXML repair approval request had no required actions")
    approval_candidate = write_fcpxml_approval_candidate(workspace, plan, approved_ids)
    approval_record = cli(
        "fcpxml",
        "--project",
        str(project),
        "--approval-record",
        str(approval_candidate),
        "--json",
        expect=(0, 1),
    )
    assert_equal(approval_record["fcpxml_repair_approval_record"]["status"], "passed", "approval status")
    dry_run = cli("fcpxml", "--project", str(project), "--repair-dry-run", "--json", expect=(0, 1))
    dry = dry_run["fcpxml_repair_dry_run"]
    if dry["approved_action_count"] < 1:
        raise SystemExit("FCPXML repair dry-run did not approve any manual action")
    execution_candidate = write_fcpxml_execution_candidate(workspace, dry)
    execution_review = cli(
        "fcpxml",
        "--project",
        str(project),
        "--repair-execution-record",
        str(execution_candidate),
        "--json",
        expect=(0, 1),
    )
    repair_execution = execution_review["fcpxml_repair_execution_review"]
    assert_equal(repair_execution["status"], "passed", "FCPXML repair execution review")
    assert_equal(repair_execution["accepted_action_count"], dry["approved_action_count"], "accepted FCPXML repair actions")
    assert_false(repair_execution["repair_success_promoted_by_cli"], "repair success promoted")
    assert_false(repair_execution["acceptance_success_promoted_by_cli"], "acceptance success promoted")

    final_workflow = cli("workflow", "--project", str(project), "--target", "delivery", "--json", expect=(0,))
    workflow_plan = final_workflow["workflow_plan"]
    assert_equal(workflow_plan["status"], "ready", "post-FCPXML workflow status")
    workflow_candidate = write_workflow_execution_candidate(workspace, workflow_plan)
    workflow_review = cli(
        "workflow",
        "--project",
        str(project),
        "--target",
        "delivery",
        "--execution-record",
        str(workflow_candidate),
        "--json",
        expect=(0,),
    )
    assert_equal(workflow_review["workflow_execution_review"]["status"], "passed", "workflow execution review")
    operator_after = cli("operator", "--project", str(project), "--target", "delivery", "--json", expect=(0, 1))
    runbook = operator_after["operator_runbook"]
    artifact_ids = {item["artifact_id"] for item in runbook["artifact_map"]}
    if not {"workflow_execution_review", "fcpxml_repair_execution_review", "fcpxml_import_review"}.issubset(artifact_ids):
        raise SystemExit("operator handback does not expose NLE round-trip evidence artifacts")

    required_artifacts = [
        ".artist-portrait/data/editor_package.json",
        "output/editor_package.md",
        "output/cue_sheet.csv",
        ".artist-portrait/data/nle_interchange_plan.json",
        "output/nle_interchange_map.csv",
        "output/draft.fcpxml",
        ".artist-portrait/data/fcpxml_import_review.json",
        ".artist-portrait/data/fcpxml_repair_plan.json",
        ".artist-portrait/data/fcpxml_repair_dry_run.json",
        ".artist-portrait/data/fcpxml_repair_execution_review.json",
        ".artist-portrait/data/workflow_execution_review.json",
        "output/operator_runbook.md",
    ]
    missing = [ref for ref in required_artifacts if not (workspace / ref).exists()]
    if missing:
        raise SystemExit(f"NLE round-trip missing artifacts: {missing}")

    guardrails = {
        "nle_project_written": nle_plan["nle_project_written"],
        "fcpxml_import_performed_by_cli": any(
            value is not False
            for value in [
                draft["nle_import_performed"],
                validation["nle_import_performed"],
                review["commands_executed"],
                plan["nle_import_performed"],
                dry["nle_import_performed"],
                repair_execution["nle_import_performed_by_cli"],
            ]
        ),
        "source_relink_performed_by_cli": any(
            value is not False
            for value in [
                plan["source_relink_performed"],
                dry["source_relink_performed"],
                repair_execution["source_relink_performed_by_cli"],
            ]
        ),
        "timeline_mutated": any(
            value is not False
            for value in [
                draft["timeline_mutated"],
                validation["timeline_mutated"],
                review["timeline_mutated"],
                plan["timeline_mutated"],
                dry["timeline_mutated"],
                repair_execution["timeline_mutated_by_cli"],
            ]
        ),
        "edit_points_moved": any(
            value is not False
            for value in [
                draft["edit_points_moved"],
                validation["edit_points_moved"],
                review["edit_points_moved"],
                plan["edit_points_moved"],
                dry["edit_points_moved"],
                repair_execution["edit_points_moved_by_cli"],
            ]
        ),
        "automatic_music_selection": any(
            value is not False
            for value in [
                draft["automatic_music_selection"],
                review["automatic_music_selection"],
                plan["automatic_music_selection"],
                dry["automatic_music_selection"],
                repair_execution["automatic_music_selection_by_cli"],
            ]
        ),
        "model_call_performed_by_cli": any(
            value is not False
            for value in [
                draft["model_call_performed_by_cli"],
                review["model_call_performed_by_cli"],
                plan["model_call_performed_by_cli"],
                dry["model_call_performed_by_cli"],
                repair_execution["model_call_performed_by_cli"],
            ]
        ),
        "network_performed": any(
            value is not False
            for value in [
                draft["network_performed"],
                review["network_performed"],
                plan["network_performed"],
                dry["network_performed"],
                repair_execution["network_performed_by_cli"],
            ]
        ),
        "image_generation_or_editing_used": any(
            value is not False
            for value in [
                draft["image_generation_or_editing_used"],
                review["image_generation_or_editing_used"],
                plan["image_generation_or_editing_used"],
                dry["image_generation_or_editing_used"],
                repair_execution["image_generation_or_editing_used_by_cli"],
            ]
        ),
        "repair_success_promoted": repair_execution["repair_success_promoted_by_cli"],
        "acceptance_success_promoted": repair_execution["acceptance_success_promoted_by_cli"],
    }
    if any(guardrails.values()):
        raise SystemExit(f"NLE round-trip guardrail failed: {guardrails}")

    return {
        "schema_version": "1.0",
        "roundtrip_id": "nle_roundtrip_stage_05",
        "project_id": "golden_artist_portrait_001",
        "status": "passed",
        "workspace": str(workspace),
        "package": {
            "operator_status_before": operator_before["operator_runbook"]["status"],
            "operator_status_after": runbook["status"],
            "editor_manual_action_count": editor["editor_package"]["manual_action_count"],
            "nle_timeline_mapping_count": nle_plan["timeline_mapping_count"],
            "nle_marker_mapping_count": nle_plan["marker_mapping_count"],
            "fcpxml_clip_count": draft["clip_count"],
            "fcpxml_marker_count": draft["marker_count"],
            "artifact_map_contains_workflow_execution": "workflow_execution_review" in artifact_ids,
            "artifact_map_contains_fcpxml_repair_execution": "fcpxml_repair_execution_review" in artifact_ids,
        },
        "import_review": {
            "status": review["status"],
            "binding_status": review["binding_status"],
            "import_attempted": review["import_attempted"],
            "import_success_claimed": review["import_success_claimed"],
            "relink_success_claimed": review["relink_success_claimed"],
            "timeline_opened": review["timeline_opened"],
            "playback_checked": review["playback_checked"],
            "success_promoted": review["import_success_accepted_as_project_success"],
        },
        "repair": {
            "plan_status": plan["status"],
            "required_action_count": plan["required_action_count"],
            "relink_action_count": plan["relink_action_count"],
            "dry_run_approved_action_count": dry["approved_action_count"],
            "execution_review_status": repair_execution["status"],
            "accepted_action_count": repair_execution["accepted_action_count"],
        },
        "workflow_handback": {
            "workflow_status": workflow_plan["status"],
            "workflow_execution_review_status": workflow_review["workflow_execution_review"]["status"],
            "operator_next_command": runbook["next_command"],
            "operator_artifact_count": runbook["artifact_count"],
            "operator_present_artifact_count": runbook["present_artifact_count"],
        },
        "guardrails": guardrails,
        "steps": steps,
    }


def write_import_review_candidate(
    *,
    workspace: Path,
    project_id: str,
    fcpxml_draft_id: str,
    nle_plan_id: str,
) -> Path:
    path = workspace / "fcpxml_import_review_candidate.json"
    payload = {
        "schema_version": "0.3",
        "import_review_id": "external_import_review_stage_05",
        "project_id": project_id,
        "fcpxml_draft_id": fcpxml_draft_id,
        "nle_plan_id": nle_plan_id,
        "reviewed_by": "stage-05-fixture-editor",
        "application_name": "Final Cut Pro",
        "application_version": "fixture",
        "import_attempted": True,
        "import_succeeded": True,
        "relink_attempted": True,
        "relink_succeeded": False,
        "relink_missing_count": 2,
        "timeline_opened": True,
        "playback_checked": False,
        "issue_count": 2,
        "issues": [
            {
                "issue_id": "external_relink_missing_001",
                "severity": "warning",
                "category": "relink",
                "detail": "Placeholder assets imported but require manual relink to project-local media.",
            },
            {
                "issue_id": "external_playback_unchecked_001",
                "severity": "info",
                "category": "playback",
                "detail": "Timeline opened; playback spot-check is still required after relink.",
            },
        ],
        "evidence_refs": ["output/draft.fcpxml", "output/fcpxml_review.md"],
    }
    write_json(path, payload)
    return path


def write_fcpxml_approval_candidate(workspace: Path, plan: dict, approved_ids: list[str]) -> Path:
    path = workspace / "fcpxml_repair_approval_record_candidate.json"
    all_action_ids = [action["action_id"] for action in plan["actions"]]
    payload = {
        "schema_version": "0.3",
        "approval_record_id": "fcpxml_repair_approval_stage_05",
        "project_id": plan["project_id"],
        "fcpxml_repair_plan_id": plan["repair_plan_id"],
        "fcpxml_draft_id": plan["fcpxml_draft_id"],
        "fcpxml_import_review_id": plan["fcpxml_import_review_id"],
        "approved_by": "stage-05-fixture-operator",
        "approved_action_ids": approved_ids,
        "rejected_action_ids": [action_id for action_id in all_action_ids if action_id not in set(approved_ids)],
        "status": "passed",
    }
    write_json(path, payload)
    return path


def write_fcpxml_execution_candidate(workspace: Path, dry_run: dict) -> Path:
    path = workspace / "fcpxml_repair_execution_record_candidate.json"
    actions = [
        {
            "action_id": step["action_id"],
            "command": step["command"],
            "status": "succeeded",
            "exit_code": 0,
            "output_refs": ["external/final-cut-import-review-notes.md"],
            "evidence_refs": [
                ".artist-portrait/data/fcpxml_import_review.json",
                "output/fcpxml_repair_dry_run.md",
            ],
            "notes": "External operator reports the manual repair action was completed outside the CLI.",
        }
        for step in dry_run["steps"]
        if step["status"] == "approved"
    ]
    payload = {
        "schema_version": "0.3",
        "execution_record_id": "fcpxml_repair_execution_stage_05",
        "project_id": dry_run["project_id"],
        "fcpxml_repair_plan_id": dry_run["fcpxml_repair_plan_id"],
        "approval_record_id": dry_run["approval_record_id"],
        "dry_run_id": dry_run["dry_run_id"],
        "fcpxml_draft_id": dry_run["fcpxml_draft_id"],
        "fcpxml_import_review_id": dry_run["fcpxml_import_review_id"],
        "executed_by": "stage-05-fixture-editor",
        "actions": actions,
    }
    write_json(path, payload)
    return path


def write_workflow_execution_candidate(workspace: Path, workflow_plan: dict) -> Path:
    path = workspace / "workflow_execution_record_candidate.json"
    nle_steps = {"operator", "editor_package", "nle_plan", "fcpxml_draft"}
    steps = []
    for step in workflow_plan["steps"]:
        refs = [ref for ref in step["expected_artifacts"] if (workspace / ref).exists()]
        if not refs:
            refs = step["expected_artifacts"][:1]
        evidence_refs = list(refs)
        if step["step_id"] in nle_steps:
            evidence_refs.extend(
                [
                    ".artist-portrait/data/fcpxml_import_review.json",
                    ".artist-portrait/data/fcpxml_repair_execution_review.json",
                ]
            )
        steps.append(
            {
                "step_id": step["step_id"],
                "command": step["command"],
                "status": "succeeded",
                "exit_code": 0,
                "output_refs": refs,
                "evidence_refs": evidence_refs,
                "notes": "NLE handoff evidence was reviewed outside the CLI and rebound to workflow.",
            }
        )
    payload = {
        "schema_version": "0.3",
        "execution_record_id": "workflow_execution_stage_05_nle_handback",
        "project_id": workflow_plan["project_id"],
        "workflow_plan_id": workflow_plan["workflow_plan_id"],
        "target": workflow_plan["target"],
        "executed_by": "stage-05-fixture-operator",
        "steps": steps,
    }
    write_json(path, payload)
    return path


def write_manifest(workspace: Path, manifest: dict) -> None:
    output = workspace / "output"
    output.mkdir(exist_ok=True)
    write_json(output / "nle_roundtrip_manifest.json", manifest)
    lines = [
        "# NLE Round-Trip Readiness Report",
        "",
        f"- Status: `{manifest['status']}`",
        f"- Project: `{manifest['project_id']}`",
        f"- FCPXML clips: `{manifest['package']['fcpxml_clip_count']}`",
        f"- Required repair actions: `{manifest['repair']['required_action_count']}`",
        f"- Accepted repair actions: `{manifest['repair']['accepted_action_count']}`",
        f"- Workflow handback: `{manifest['workflow_handback']['workflow_execution_review_status']}`",
        "",
        "## Guardrails",
        "",
    ]
    for key, value in manifest["guardrails"].items():
        lines.append(f"- `{key}`: `{value}`")
    (output / "nle_roundtrip_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def assert_equal(value: object, expected: object, label: str) -> None:
    if value != expected:
        raise SystemExit(f"{label}: expected {expected!r}, got {value!r}")


def assert_true(value: object, label: str) -> None:
    if value is not True:
        raise SystemExit(f"{label}: expected True, got {value!r}")


def assert_false(value: object, label: str) -> None:
    if value is not False:
        raise SystemExit(f"{label}: expected False, got {value!r}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
