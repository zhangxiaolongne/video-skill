from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PYTHON = Path(sys.executable)
ARTIST_PORTRAIT = Path(
    shutil.which("artist-portrait") or ROOT / ".venv" / "bin" / "artist-portrait"
)
QUICK_VALIDATE = (
    Path.home()
    / ".codex"
    / "skills"
    / ".system"
    / "skill-creator"
    / "scripts"
    / "quick_validate.py"
)
PACKAGE_PREFLIGHT = ROOT / "scripts" / "skill_package_preflight.py"
SIMULATE_INSTALL = ROOT / "scripts" / "simulate_skill_install.py"


def run(command: list[str], *, expect: int | tuple[int, ...] = 0) -> None:
    print("$", " ".join(command), flush=True)
    completed = subprocess.run(command, cwd=ROOT)
    expected = (expect,) if isinstance(expect, int) else expect
    if completed.returncode not in expected:
        raise SystemExit(
            f"command exited {completed.returncode}, expected {expected}: {' '.join(command)}"
        )


def run_json(command: list[str], *, expect: int | tuple[int, ...] = 0) -> dict:
    print("$", " ".join(command), flush=True)
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    expected = (expect,) if isinstance(expect, int) else expect
    if completed.returncode not in expected:
        raise SystemExit(
            f"command exited {completed.returncode}, expected {expected}: "
            f"{' '.join(command)}\nstdout: {completed.stdout}\nstderr: {completed.stderr}"
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"command did not emit JSON: {' '.join(command)}\n{completed.stdout}"
        ) from exc


def require_local_env() -> None:
    missing = [path for path in (PYTHON, ARTIST_PORTRAIT) if not path.exists()]
    if missing:
        paths = ", ".join(str(path.relative_to(ROOT)) for path in missing)
        raise SystemExit(
            f"missing local environment files: {paths}\n"
            "Create it with: python3 -m venv .venv && "
            ".venv/bin/python -m pip install -e '.[dev]'"
        )


def check_schema_drift() -> None:
    with tempfile.TemporaryDirectory(prefix="artist-portrait-schemas-") as tmp:
        tmp_path = Path(tmp)
        run([str(ARTIST_PORTRAIT), "generate-schema", "--output-dir", str(tmp_path)])
        for name in (
            "acceptance_repair_approval_record.schema.json",
            "acceptance_repair_approval_request.schema.json",
            "acceptance_repair_execution_bundle.schema.json",
            "acceptance_repair_execution_dry_run.schema.json",
            "acceptance_repair_execution_record.schema.json",
            "acceptance_repair_plan.schema.json",
            "analysis_record.schema.json",
            "project_acceptance_report.schema.json",
            "bgm_analysis_report.schema.json",
            "bgm_beat_grid.schema.json",
            "bgm_candidate_ledger.schema.json",
            "bgm_fit_plan.schema.json",
            "bgm_rhythm_intelligence_report.schema.json",
            "bgm_recommendation_context.schema.json",
            "bgm_recommendation_fit_review.schema.json",
            "bgm_recommendation_request.schema.json",
            "bgm_recommendation_selection.schema.json",
            "bgm_recommendation_set.schema.json",
            "bgm_recommendation_validation_report.schema.json",
            "clip_record.schema.json",
            "edit_guidance_report.schema.json",
            "final_export_manifest.schema.json",
            "final_export_validation_report.schema.json",
            "preview_render_manifest.schema.json",
            "preview_validation_report.schema.json",
            "project_config.schema.json",
            "project_state.schema.json",
            "rhythm_agent_candidate.schema.json",
            "rhythm_intent.schema.json",
            "rhythm_media_qc_report.schema.json",
            "rhythm_plan.schema.json",
            "rhythm_repair_plan.schema.json",
            "proposal_adapter_check.schema.json",
            "proposal_canonical_write_transaction_plan.schema.json",
            "proposal_execution_approval_record.schema.json",
            "proposal_execution_approval_request.schema.json",
            "proposal_execution_authorization.schema.json",
            "proposal_execution_input_bundle.schema.json",
            "proposal_execution_readiness_plan.schema.json",
            "proposal_mock_adapter_handshake.schema.json",
            "proposal_context.schema.json",
            "proposal_promotion_authorization_plan.schema.json",
            "proposal_promotion_validation_report.schema.json",
            "proposal_provider_call_dry_run.schema.json",
            "proposal_provider_response_intake_plan.schema.json",
            "proposal_provider_response_validation_plan.schema.json",
            "proposal_provider_registry.schema.json",
            "proposal_provider_output_quarantine.schema.json",
            "proposal_provider_result_envelope.schema.json",
            "proposal_request_packet.schema.json",
            "proposal_validation_report.schema.json",
            "proposal_set.schema.json",
            "release_hardening_report.schema.json",
            "source_record.schema.json",
            "keyframe_record.schema.json",
            "transcript_record.schema.json",
            "text_model_gate.schema.json",
            "timeline_draft.schema.json",
            "timeline_validation_report.schema.json",
            "workflow_execution_record.schema.json",
            "workflow_execution_review.schema.json",
            "workflow_plan.schema.json",
            "workflow_repair_approval_record.schema.json",
            "workflow_repair_approval_request.schema.json",
            "workflow_repair_dry_run.schema.json",
            "workflow_repair_execution_record.schema.json",
            "workflow_repair_execution_review.schema.json",
            "workflow_repair_refresh_plan.schema.json",
            "workflow_repair_plan.schema.json",
        ):
            committed = ROOT / "schemas" / name
            generated = tmp_path / name
            if committed.read_text(encoding="utf-8") != generated.read_text(encoding="utf-8"):
                raise SystemExit(f"schema drift detected: {name}")


def check_skill_metadata() -> None:
    run([str(PYTHON), str(QUICK_VALIDATE), str(ROOT)])
    openai_yaml = ROOT / "agents" / "openai.yaml"
    if "$artist-portrait-editor" not in openai_yaml.read_text(encoding="utf-8"):
        raise SystemExit("agents/openai.yaml default_prompt must mention $artist-portrait-editor")
    preflight = subprocess.run(
        [str(PYTHON), str(PACKAGE_PREFLIGHT), str(ROOT), "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if preflight.returncode != 0:
        raise SystemExit(f"skill package preflight failed: {preflight.stdout}")
    payload = json.loads(preflight.stdout)
    if payload.get("error_count") != 0:
        raise SystemExit("skill package preflight reported hard errors")
    allowed_warnings = {"folder_name_mismatch"}
    warning_codes = {
        issue.get("code")
        for issue in payload.get("issues", [])
        if issue.get("severity") == "warning"
    }
    if warning_codes - allowed_warnings:
        raise SystemExit(f"unexpected skill package warnings: {sorted(warning_codes)}")
    package_policy = payload.get("package_policy") or {}
    if package_policy.get("canonical_install_dir") != "artist-portrait-editor":
        raise SystemExit("skill package canonical install dir is wrong")
    install = subprocess.run(
        [str(PYTHON), str(SIMULATE_INSTALL), str(ROOT), "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if install.returncode != 0:
        raise SystemExit(f"canonical install simulation failed: {install.stdout}")
    install_payload = json.loads(install.stdout)
    install_preflight = install_payload.get("package_preflight") or {}
    if install_preflight.get("warning_count") != 0:
        raise SystemExit("canonical install simulation has package warnings")


def check_gate_consistency() -> None:
    docs = {
        "AGENTS.md": ROOT / "AGENTS.md",
        "master": ROOT / "artist_portrait_editor_revision5_optimized.md",
        "README.md": ROOT / "README.md",
        "DEVELOPMENT_PROGRESS.md": ROOT / "docs" / "DEVELOPMENT_PROGRESS.md",
    }
    content = {name: path.read_text(encoding="utf-8") for name, path in docs.items()}
    if "Current gate: V0-043 phrase-level manual edit guidance gate." not in content["AGENTS.md"]:
        raise SystemExit("AGENTS.md current gate is not V0-043 edit guidance")
    if "V0-043 phrase-level manual edit guidance gate" not in content["master"]:
        raise SystemExit("master document current gate is not V0-043 edit guidance")
    if "Current V0-043 phrase-level manual edit guidance gate work" not in content["README.md"]:
        raise SystemExit("README current gate is not V0-043 edit guidance")
    if (
        "Current local gate: V0-043 phrase-level manual edit guidance gate"
        not in content["DEVELOPMENT_PROGRESS.md"]
    ):
        raise SystemExit("development progress current gate is stale")
    if list((ROOT / "docs").glob("V0_*.md")):
        raise SystemExit("historical V0 document fragments must remain consolidated")
    if (ROOT / "docs" / "STAGE_A_ACCEPTANCE.md").exists():
        raise SystemExit("Stage A fragment must remain consolidated")


def check_progress_contract() -> None:
    path = ROOT / "docs" / "current_progress.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1.4":
        raise SystemExit("progress snapshot schema_version is not 1.4")
    if payload.get("capability_gate") != "V0-043":
        raise SystemExit("progress snapshot capability gate is stale")
    documentation_system = payload.get("documentation_system") or {}
    expected_documents = {
        "master": "artist_portrait_editor_revision5_optimized.md",
        "current_progress": "docs/DEVELOPMENT_PROGRESS.md",
        "current_batch": "docs/CURRENT_BATCH.md",
        "issues": "docs/ISSUES.md",
        "decisions": "docs/DECISIONS.md",
        "releases": "docs/RELEASES.md",
        "machine_progress": "docs/current_progress.json",
    }
    if any(documentation_system.get(key) != value for key, value in expected_documents.items()):
        raise SystemExit("progress snapshot documentation ownership is stale")
    if (
        documentation_system.get("historical_readiness_policy")
        != "consolidated_in_release_ledger"
    ):
        raise SystemExit("historical outcomes are not consolidated")
    for relative_path in expected_documents.values():
        if not (ROOT / relative_path).is_file():
            raise SystemExit(f"canonical documentation file is missing: {relative_path}")
    active_batch = payload.get("active_batch") or {}
    if active_batch.get("capability_gate") != payload.get("capability_gate"):
        raise SystemExit("active batch capability gate does not match progress gate")
    if not re.fullmatch(r"V\d+-\d{3}", str(active_batch.get("id") or "")):
        raise SystemExit("progress snapshot active batch id is invalid")
    allowed_batch_statuses = {"planned", "in_progress", "completed", "blocked", "dropped"}
    if active_batch.get("status") not in allowed_batch_statuses:
        raise SystemExit("active batch has an invalid status")
    tasks = payload.get("tasks") or []
    if len(tasks) != 10:
        raise SystemExit("progress snapshot must record exactly ten version tasks")
    task_ids = [task.get("id") for task in tasks]
    if len(task_ids) != len(set(task_ids)):
        raise SystemExit("progress snapshot task ids must be unique")
    if any(task.get("status") not in allowed_batch_statuses for task in tasks):
        raise SystemExit("progress snapshot contains an invalid task status")
    current_batch = (ROOT / expected_documents["current_batch"]).read_text(encoding="utf-8")
    batch_rows = re.findall(
        r"^\| `([A-Z][A-Z0-9_-]*-\d{2})` \|.*\| "
        r"`(planned|in_progress|completed|blocked|dropped)` \|",
        current_batch,
        flags=re.MULTILINE,
    )
    if batch_rows != [(task.get("id"), task.get("status")) for task in tasks]:
        raise SystemExit("current batch Markdown and machine task states disagree")
    if active_batch.get("id") not in current_batch:
        raise SystemExit("current batch Markdown does not name the active batch")
    if f"Status: `{active_batch.get('status')}`" not in current_batch:
        raise SystemExit("current batch Markdown status is stale")
    terminal_statuses = {"completed", "blocked", "dropped"}
    if active_batch.get("status") == "completed" and any(
        task.get("status") not in terminal_statuses for task in tasks
    ):
        raise SystemExit("completed batch contains non-terminal tasks")
    if active_batch.get("status") == "in_progress" and not any(
        task.get("status") == "in_progress" for task in tasks
    ):
        raise SystemExit("in-progress batch has no in-progress task")
    progress = (ROOT / expected_documents["current_progress"]).read_text(encoding="utf-8")
    issues = (ROOT / expected_documents["issues"]).read_text(encoding="utf-8")
    decisions = (ROOT / expected_documents["decisions"]).read_text(encoding="utf-8")
    releases = (ROOT / expected_documents["releases"]).read_text(encoding="utf-8")
    if payload.get("milestone") not in progress:
        raise SystemExit("development dashboard milestone is stale")
    if "## Active Issues" not in issues:
        raise SystemExit("issue ledger lacks active issues")
    if "## Active Decisions" not in decisions:
        raise SystemExit("decision ledger lacks active decisions")
    if "## Current Release State" not in releases or "## Current Validation" not in releases:
        raise SystemExit("release ledger lacks current state or validation")
    if "Do not recreate per-version readiness" not in releases:
        raise SystemExit("release ledger does not prevent historical fragment drift")
    forbidden = payload.get("forbidden_capabilities") or {}
    if forbidden.get("host_agent_generation") is not True:
        raise SystemExit("progress snapshot did not open host-Agent generation")
    if forbidden.get("timeline_generation") is not True:
        raise SystemExit("progress snapshot did not open timeline generation")
    if forbidden.get("bgm_analysis") is not True:
        raise SystemExit("progress snapshot did not open BGM ingestion/fitting")
    if forbidden.get("bgm_technical_analysis") is not True:
        raise SystemExit("progress snapshot did not open BGM technical analysis")
    if forbidden.get("bgm_recommendation_review") is not True:
        raise SystemExit("progress snapshot did not open BGM recommendation review")
    if forbidden.get("bgm_beat_engine_evidence") is not True:
        raise SystemExit("progress snapshot did not open beat-engine evidence")
    if forbidden.get("bgm_recommendation_to_fit_selection") is not True:
        raise SystemExit("progress snapshot did not open recommendation-to-fit selection")
    if forbidden.get("bgm_recommendation_fit_review") is not True:
        raise SystemExit("progress snapshot did not open recommendation-fit review")
    if forbidden.get("bgm_fit_controls") is not True:
        raise SystemExit("progress snapshot did not open BGM fit controls")
    if forbidden.get("project_acceptance") is not True:
        raise SystemExit("progress snapshot did not open project acceptance")
    if forbidden.get("automatic_beat_synced_editing") is not False:
        raise SystemExit("progress snapshot opened automatic beat-synced editing")
    if forbidden.get("preview_rendering") is not True:
        raise SystemExit("progress snapshot did not open preview rendering")
    if forbidden.get("final_export") is not True:
        raise SystemExit("progress snapshot did not open final export")
    if any(
        value is not False
        for key, value in forbidden.items()
        if key not in {
            "host_agent_generation",
            "timeline_generation",
            "bgm_analysis",
            "bgm_technical_analysis",
            "bgm_recommendation_review",
            "bgm_beat_engine_evidence",
            "bgm_recommendation_to_fit_selection",
            "bgm_recommendation_fit_review",
            "bgm_fit_controls",
            "project_acceptance",
            "acceptance_profiles",
            "real_media_acceptance_fixtures",
            "acceptance_repair_plans",
            "acceptance_repair_approvals",
            "repair_execution_dry_runs",
            "repair_execution_handoffs",
            "rhythm_planning",
            "rhythm_media_qc",
            "rhythm_acceptance_integration",
            "rhythm_manual_repair_planning",
            "guided_workflow_planning",
            "workflow_execution_evidence_review",
            "workflow_evidence_repair_planning",
            "workflow_repair_approval_dry_run",
            "workflow_repair_execution_review",
            "release_hardening",
            "workflow_repair_refresh_guidance",
            "bgm_rhythm_intelligence",
            "phrase_level_edit_guidance",
            "preview_rendering",
            "final_export",
        }
    ):
        raise SystemExit("progress snapshot opened a forbidden paid/future capability")
    capability_progress = payload.get("capability_progress") or {}
    if capability_progress.get("proposal_generation") != "completed":
        raise SystemExit("progress snapshot proposal generation state is stale")
    if capability_progress.get("timeline_generation") != "completed":
        raise SystemExit("progress snapshot timeline state is stale")
    if capability_progress.get("bgm_ingestion_and_fitting") != "completed":
        raise SystemExit("progress snapshot BGM state is stale")
    if capability_progress.get("bgm_technical_analysis") != "completed":
        raise SystemExit("progress snapshot BGM technical analysis state is stale")
    if capability_progress.get("bgm_recommendation_review") != "completed":
        raise SystemExit("progress snapshot BGM recommendation state is stale")
    if capability_progress.get("bgm_beat_engine_evidence") not in {
        "in_progress",
        "completed",
    }:
        raise SystemExit("progress snapshot beat-engine evidence state is stale")
    if capability_progress.get("bgm_recommendation_to_fit_selection") not in {
        "in_progress",
        "completed",
    }:
        raise SystemExit("progress snapshot recommendation-to-fit state is stale")
    if capability_progress.get("bgm_recommendation_fit_review") != "completed":
        raise SystemExit("progress snapshot recommendation-fit review state is stale")
    if capability_progress.get("bgm_fit_controls") != "completed":
        raise SystemExit("progress snapshot BGM fit controls state is stale")
    if capability_progress.get("project_acceptance") != "completed":
        raise SystemExit("progress snapshot project acceptance state is stale")
    if capability_progress.get("acceptance_profiles") not in {"in_progress", "completed"}:
        raise SystemExit("progress snapshot acceptance profiles state is stale")
    if capability_progress.get("real_media_acceptance_fixtures") != "completed":
        raise SystemExit("progress snapshot real-media acceptance fixture state is stale")
    if capability_progress.get("acceptance_repair_plans") != "completed":
        raise SystemExit("progress snapshot acceptance repair-plan state is stale")
    if capability_progress.get("acceptance_repair_approvals") != "completed":
        raise SystemExit("progress snapshot acceptance repair approval state is stale")
    if capability_progress.get("repair_execution_dry_runs") != "completed":
        raise SystemExit("progress snapshot repair execution dry-run state is stale")
    if capability_progress.get("repair_execution_handoffs") != "completed":
        raise SystemExit("progress snapshot repair execution handoff state is stale")
    if capability_progress.get("rhythm_planning") != "completed":
        raise SystemExit("progress snapshot rhythm planning state is stale")
    if capability_progress.get("rhythm_media_qc") != "completed":
        raise SystemExit("progress snapshot rhythm media QC state is stale")
    if capability_progress.get("rhythm_acceptance_integration") != "completed":
        raise SystemExit("progress snapshot rhythm acceptance integration state is stale")
    if capability_progress.get("rhythm_manual_repair_planning") != "completed":
        raise SystemExit("progress snapshot rhythm repair planning state is stale")
    if capability_progress.get("guided_workflow_planning") != "completed":
        raise SystemExit("progress snapshot guided workflow planning state is stale")
    if capability_progress.get("workflow_execution_evidence_review") != "completed":
        raise SystemExit("progress snapshot workflow execution evidence review state is stale")
    if capability_progress.get("workflow_evidence_repair_planning") != "completed":
        raise SystemExit("progress snapshot workflow evidence repair planning state is stale")
    if capability_progress.get("workflow_repair_approval_dry_run") != "completed":
        raise SystemExit("progress snapshot workflow repair approval dry-run state is stale")
    if capability_progress.get("workflow_repair_execution_review") != "completed":
        raise SystemExit("progress snapshot workflow repair execution review state is stale")
    if capability_progress.get("release_hardening") != "completed":
        raise SystemExit("progress snapshot release hardening state is stale")
    if capability_progress.get("workflow_repair_refresh_guidance") != "completed":
        raise SystemExit("progress snapshot workflow repair refresh guidance state is stale")
    if capability_progress.get("bgm_rhythm_intelligence") != "completed":
        raise SystemExit("progress snapshot BGM rhythm intelligence state is stale")
    if capability_progress.get("phrase_level_edit_guidance") != "completed":
        raise SystemExit("progress snapshot edit guidance state is stale")
    if capability_progress.get("preview_rendering") != "completed":
        raise SystemExit("progress snapshot preview state is stale")
    if capability_progress.get("preview_quality_review") != "completed":
        raise SystemExit("progress snapshot preview QC state is stale")
    if capability_progress.get("final_export") != "completed":
        raise SystemExit("progress snapshot final export state is stale")
    bgm_contract = payload.get("future_bgm_input_contract") or {}
    expected_bgm_modes = [
        "direct_audio",
        "video_audio_extract",
        "source_embedded_audio",
        "multiple_candidates",
        "none_yet",
    ]
    if bgm_contract.get("status") != "required_for_future_gate":
        raise SystemExit("future BGM input contract status is stale")
    if bgm_contract.get("input_modes") != expected_bgm_modes:
        raise SystemExit("future BGM input modes are incomplete or reordered")
    required_bgm_provenance = {
        "music_candidate_id",
        "input_mode",
        "source_ref",
        "source_media_kind",
        "extract_in",
        "extract_out",
        "audio_stream_index",
        "content_hash",
        "duration",
        "rights_status",
        "contains_speech",
        "contains_vocals",
        "contains_environment",
        "contains_sound_effects",
        "user_intent",
        "analysis_status",
    }
    if not required_bgm_provenance.issubset(
        set(bgm_contract.get("required_provenance") or [])
    ):
        raise SystemExit("future BGM input provenance contract is incomplete")
    if bgm_contract.get("allows_unresolved_music_slot") is not True:
        raise SystemExit("future BGM contract requires music too early")
    if bgm_contract.get("video_extract_is_mixed_audio") is not True:
        raise SystemExit("future BGM contract lost mixed-audio classification")
    if bgm_contract.get("video_extract_implies_clean_bgm") is not False:
        raise SystemExit("future BGM contract incorrectly treats extraction as clean BGM")
    if bgm_contract.get("derived_audio_is_rebuildable_cache") is not True:
        raise SystemExit("future BGM derived audio is not marked rebuildable")
    master = (ROOT / expected_documents["master"]).read_text(encoding="utf-8")
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    for mode in expected_bgm_modes:
        if mode not in master or mode not in skill:
            raise SystemExit(f"future BGM mode is missing from docs: {mode}")
    if "DEC-009: Support multiple BGM input modes" not in decisions:
        raise SystemExit("future BGM input decision is missing")
    if "mixed audio track, not automatically a clean BGM" not in progress:
        raise SystemExit("development dashboard lost the mixed-audio warning")
    if "Never label extraction alone as clean BGM" not in skill:
        raise SystemExit("Skill lost the video extraction safety boundary")
    contract = payload.get("development_batch_contract") or {}
    if contract.get("minimum_version_tasks") != 10:
        raise SystemExit("development batch contract must require ten version tasks")
    if contract.get("requires_named_capability_milestone") is not True:
        raise SystemExit("development batch contract lacks milestone requirement")
    if contract.get("requires_final_goal_delta") is not True:
        raise SystemExit("development batch contract lacks final-goal delta")
    if contract.get("gate_blocked_action") != "stop_and_request_gate_promotion":
        raise SystemExit("development batch contract permits gate-blocked padding")
    if contract.get("v0_010_ordinary_expansion_closed") is not True:
        raise SystemExit("development batch contract reopened V0-010 expansion")
    non_counting = set(contract.get("small_task_non_counting_work") or [])
    required_non_counting = {
        "isolated_fields",
        "isolated_schemas_or_models",
        "individual_tests_or_fixtures",
        "documentation_only",
        "local_refactors_or_file_moves",
        "incidental_bug_fixes",
        "isolated_diagnostics",
        "isolated_review_rules",
    }
    if not required_non_counting.issubset(non_counting):
        raise SystemExit("development batch contract allows small supporting work to count")
    eligible = set(contract.get("major_version_eligible_work") or [])
    required_eligible = {
        "versioned_data_contract_migration",
        "comprehensive_acceptance_or_evaluation_program",
        "capability_enabling_architectural_refactor",
        "major_defect_closure_or_release_hardening_program",
    }
    if not required_eligible.issubset(eligible):
        raise SystemExit("development batch contract blocks legitimate major-version work")
    requirements = set(contract.get("major_version_task_requirements") or [])
    required_requirements = {
        "named_major_version_milestone",
        "independent_release_level_acceptance_criteria",
        "substantial_cross_cutting_or_release_critical_scope",
        "changes_capability_readiness_release_safety_or_final_goal_completion",
        "not_fragmented_into_trivial_items",
    }
    if not required_requirements.issubset(requirements):
        raise SystemExit("development batch contract lacks major-version task safeguards")


def check_proposal_module_architecture() -> None:
    from artist_portrait_editor.proposal_artifacts import PROPOSAL_ARTIFACTS
    from artist_portrait_editor.proposal_io import (
        PROPOSAL_JSON_MODELS,
        validate_proposal_json_model_registry,
    )
    from artist_portrait_editor.workspace import PROPOSAL_SUMMARY_READERS

    if validate_proposal_json_model_registry():
        raise SystemExit("proposal JSON model registry validation failed")
    expected = set(PROPOSAL_ARTIFACTS)
    if set(PROPOSAL_JSON_MODELS) != expected:
        raise SystemExit("proposal JSON model registry does not cover all artifacts")
    if set(PROPOSAL_SUMMARY_READERS) != expected:
        raise SystemExit("proposal summary registry does not cover all artifacts")
    workspace_lines = (
        ROOT / "src" / "artist_portrait_editor" / "workspace.py"
    ).read_text(encoding="utf-8").splitlines()
    if len(workspace_lines) >= 8400:
        raise SystemExit("workspace.py exceeded the V0-012 orchestration budget")


def write_sine_wav(path: Path, *, seconds: float = 0.25, sample_rate: int = 8000) -> None:
    frames = int(seconds * sample_rate)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        for index in range(frames):
            sample = int(12000 * math.sin(2 * math.pi * 440 * index / sample_rate))
            handle.writeframesraw(sample.to_bytes(2, byteorder="little", signed=True))


def write_test_video_mp4(path: Path, *, seconds: float = 2.0) -> None:
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"testsrc=size=64x64:rate=24:duration={seconds}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=220:duration={seconds}",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(path),
        ]
    )


def check_real_scan_if_available() -> None:
    if shutil.which("ffprobe") is None or shutil.which("ffmpeg") is None:
        print("skipping real scan check; ffmpeg/ffprobe not found")
        return
    with tempfile.TemporaryDirectory(prefix="artist-portrait-real-scan-") as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "media").mkdir()
        project = tmp_path / "project.yaml"
        project_text = (ROOT / "fixtures" / "stage_a" / "valid_project.yaml").read_text(
            encoding="utf-8"
        )
        project.write_text(
            project_text.replace("scene_detection: auto", "scene_detection: off")
            .replace("transcription: auto", "transcription: off"),
            encoding="utf-8",
        )
        write_sine_wav(tmp_path / "media" / "tone.wav")
        (tmp_path / "sources.csv").write_text(
            "location,source_type,work,role,rights_status,forbidden_by_user,notes\n"
            "media/tone.wav,interview,Generated Tone,Test Role,owned,false,check fixture\n",
            encoding="utf-8",
        )
        run(
            [str(ARTIST_PORTRAIT), "init", "--project", str(project), "--quiet"],
            expect=(0, 1),
        )
        run([str(ARTIST_PORTRAIT), "scan", "--project", str(project), "--json"])
        sources = tmp_path / ".artist-portrait" / "data" / "sources.jsonl"
        scan_report = tmp_path / "output" / "scan_report.md"
        records = [
            json.loads(line)
            for line in sources.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if len(records) != 1 or records[0]["media_kind"] != "audio":
            raise SystemExit("real scan check did not produce one audio source")
        if records[0]["source_type"]["value"] != "interview":
            raise SystemExit("real scan check did not apply sources.csv")
        if records[0]["work"]["value"] != "Generated Tone":
            raise SystemExit("real scan check did not preserve sources.csv work")
        report = scan_report.read_text(encoding="utf-8")
        if "# Scan Report" not in report or "ffprobe-derived media facts" not in report:
            raise SystemExit("real scan check did not write scan_report")

        run([str(ARTIST_PORTRAIT), "segment", "--project", str(project), "--quiet"])
        clip_report = (tmp_path / "output" / "clip_report.md").read_text(
            encoding="utf-8"
        )
        if "# Clip Report" not in clip_report or "fixed-window segmentation" not in clip_report:
            raise SystemExit("clip_report content check failed")
        clips = tmp_path / ".artist-portrait" / "data" / "clips.jsonl"
        if not clips.exists():
            raise SystemExit("segment did not write clips.jsonl")

        run([str(ARTIST_PORTRAIT), "transcribe", "--project", str(project), "--quiet"])
        transcripts = tmp_path / ".artist-portrait" / "data" / "transcripts.jsonl"
        if transcripts.exists():
            raise SystemExit("transcription: off wrote transcripts.jsonl")

        run(
            [str(ARTIST_PORTRAIT), "keyframes", "--project", str(project), "--quiet"],
            expect=(0, 1),
        )
        keyframes = tmp_path / ".artist-portrait" / "data" / "keyframes.jsonl"
        if not keyframes.exists() or keyframes.read_text(encoding="utf-8") != "":
            raise SystemExit("audio-only keyframes check did not write an empty manifest")

        run([str(ARTIST_PORTRAIT), "analyze", "--project", str(project), "--quiet"])
        analysis = tmp_path / ".artist-portrait" / "data" / "analysis.jsonl"
        analysis_report = tmp_path / "output" / "analysis_report.md"
        if not analysis.exists() or "original_audio_usability" not in analysis.read_text(
            encoding="utf-8"
        ):
            raise SystemExit("analyze did not write analysis.jsonl")
        if "# Analysis Report" not in analysis_report.read_text(encoding="utf-8"):
            raise SystemExit("analyze did not write analysis_report.md")

        run([str(ARTIST_PORTRAIT), "map", "--project", str(project), "--quiet"])
        material_map = (tmp_path / "output" / "material_map.md").read_text(
            encoding="utf-8"
        )
        if "Analysis ledger" not in material_map or "Priority Review Queue" not in material_map:
            raise SystemExit("real scan material_map did not use analysis ledger")
        run(
            [str(ARTIST_PORTRAIT), "propose", "--project", str(project), "--json"],
            expect=(0, 1),
        )
        context = tmp_path / ".artist-portrait" / "data" / "proposal_context.json"
        gate = tmp_path / ".artist-portrait" / "data" / "text_model_gate.json"
        if not context.exists():
            raise SystemExit("blocked propose did not write proposal_context.json")
        if not gate.exists():
            raise SystemExit("blocked propose did not write text_model_gate.json")
        if not (tmp_path / "output" / "proposal_agent_handoff.json").exists():
            raise SystemExit("propose did not write proposal_agent_handoff.json")
        context_payload = json.loads(context.read_text(encoding="utf-8"))
        if context_payload.get("proposal_ids_required") != [
            "proposal_safe",
            "proposal_advanced",
            "proposal_risky",
        ]:
            raise SystemExit("proposal_context missing required proposal ids")
        if (tmp_path / ".artist-portrait" / "data" / "proposals.json").exists():
            raise SystemExit("blocked propose wrote fake proposals.json")
        if (tmp_path / "output" / "proposals.md").exists():
            raise SystemExit("blocked propose wrote fake proposals.md")
        run(
            [
                str(ARTIST_PORTRAIT),
                "review",
                "--project",
                str(project),
                "--scope",
                "project",
                "--quiet",
            ],
            expect=(0, 1),
        )
        write_sine_wav(tmp_path / "media" / "tone.wav", seconds=0.5)
        rescan = subprocess.run(
            [str(ARTIST_PORTRAIT), "scan", "--project", str(project), "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if rescan.returncode not in (0, 1):
            raise SystemExit(f"real rescan failed: {rescan.stderr}")
        rescan_payload = json.loads(rescan.stdout)
        if sorted(rescan_payload.get("invalidated_steps", [])) != [
            "analyze",
            "keyframes",
            "map",
            "propose",
            "review_project",
            "segment",
        ]:
            raise SystemExit("real rescan did not invalidate downstream outputs")
        doctor = subprocess.run(
            [str(ARTIST_PORTRAIT), "doctor", "--project", str(project), "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if doctor.returncode != 1:
            raise SystemExit("doctor did not report invalidated downstream outputs")
        doctor_payload = json.loads(doctor.stdout)
        issue_codes = {issue.get("code") for issue in doctor_payload.get("issues", [])}
        if {
            "analyze_invalidated",
            "segment_invalidated",
            "keyframes_invalidated",
            "map_invalidated",
            "propose_invalidated",
            "review_project_invalidated",
        } - issue_codes:
            raise SystemExit("doctor did not classify invalidated downstream outputs")


def minimal_source_record() -> dict:
    return {
        "schema_version": "0.3",
        "source_id": "check-source-1",
        "locations": ["media/check.mp4"],
        "primary_location": "media/check.mp4",
        "content_hash": "sha256:" + "1" * 64,
        "supersedes_source_id": None,
        "media_kind": "video",
        "media_probe": {
            "duration": 2.5,
            "width": 16,
            "height": 16,
            "frame_rate": 24.0,
            "video_codec": "h264",
            "audio_present": False,
            "audio_codec": None,
        },
        "source_type": {
            "value": "other",
            "method": "check_fixture",
            "level": 1,
            "confidence": 0.2,
            "evidence": [],
            "user_confirmed": False,
        },
        "work": None,
        "role": None,
        "recorded_date": None,
        "published_date": None,
        "rights_status": {
            "value": "permission_unknown",
            "method": "check_fixture",
            "level": 1,
            "confidence": 0.0,
            "evidence": [],
            "user_confirmed": False,
        },
        "provenance_confidence": 0.0,
        "provenance_method": "check_fixture",
        "provenance_evidence": [],
        "candidate_values": [],
        "conflicts": [],
        "user_confirmed": False,
        "confirmation_history": [],
        "forbidden_by_user": False,
        "risk_flags": [
            "unknown_provenance",
            "low_provenance_confidence",
            "rights_unknown",
        ],
        "notes": "run_checks fixture",
    }


def write_valid_proposals_from_context(root: Path) -> None:
    context = json.loads(
        (root / ".artist-portrait" / "data" / "proposal_context.json").read_text(
            encoding="utf-8"
        )
    )
    clip_id = context["clips"][0]["clip_id"]
    analysis_id = context["analyses"][0]["analysis_id"]
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
                "minimum_viable_timeline": ["timeline generation is not open"],
                "missing_material": [],
                "counter_proposal": counter_proposals[proposal_id],
            }
        )
    payload = {
        "proposal_set_id": "proposal_set_run_checks",
        "project_id": context["project_id"],
        "map_fingerprint": context["material_map_fingerprint"],
        "method": "codex_host_agent_run_checks",
        "method_version": "v0-011",
        "proposals": proposals,
        "evidence": [{"type": "proposal_context", "ref": context["context_id"]}],
        "warnings": [],
    }
    (root / ".artist-portrait" / "data" / "proposals.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def check_local_foundation_outputs() -> None:
    with tempfile.TemporaryDirectory(prefix="artist-portrait-foundation-") as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "media").mkdir()
        project = tmp_path / "project.yaml"
        project_text = (ROOT / "fixtures" / "stage_a" / "valid_project.yaml").read_text(
            encoding="utf-8"
        )
        project.write_text(
            project_text.replace("scene_detection: auto", "scene_detection: off")
            .replace("transcription: auto", "transcription: off"),
            encoding="utf-8",
        )
        run(
            [str(ARTIST_PORTRAIT), "init", "--project", str(project), "--quiet"],
            expect=(0, 1),
        )
        initial_doctor = subprocess.run(
            [str(ARTIST_PORTRAIT), "doctor", "--project", str(project), "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if initial_doctor.returncode != 0:
            raise SystemExit(f"doctor after init reported issues: {initial_doctor.stdout}")

        data_dir = tmp_path / ".artist-portrait" / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        (data_dir / "sources.jsonl").write_text(
            json.dumps(minimal_source_record(), sort_keys=True) + "\n",
            encoding="utf-8",
        )

        run([str(ARTIST_PORTRAIT), "segment", "--project", str(project), "--quiet"])
        clip_report = (tmp_path / "output" / "clip_report.md").read_text(
            encoding="utf-8"
        )
        if "# Clip Report" not in clip_report or "fixed-window segmentation" not in clip_report:
            raise SystemExit("clip_report content check failed")
        clips = tmp_path / ".artist-portrait" / "data" / "clips.jsonl"
        if not clips.exists():
            raise SystemExit("segment did not write clips.jsonl")

        run([str(ARTIST_PORTRAIT), "transcribe", "--project", str(project), "--quiet"])
        transcripts = tmp_path / ".artist-portrait" / "data" / "transcripts.jsonl"
        if transcripts.exists():
            raise SystemExit("transcription: off wrote transcripts.jsonl")

        run([str(ARTIST_PORTRAIT), "analyze", "--project", str(project), "--quiet"])
        analysis = tmp_path / ".artist-portrait" / "data" / "analysis.jsonl"
        if not analysis.exists():
            raise SystemExit("analyze did not write analysis.jsonl")

        run([str(ARTIST_PORTRAIT), "map", "--project", str(project), "--quiet"])
        material_map = (tmp_path / "output" / "material_map.md").read_text(
            encoding="utf-8"
        )
        if (
            "# Material Map" not in material_map
            or "Priority Review Queue" not in material_map
        ):
            raise SystemExit("material_map content check failed")
        propose = subprocess.run(
            [str(ARTIST_PORTRAIT), "propose", "--project", str(project), "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if propose.returncode != 1:
            raise SystemExit(f"propose did not prepare host-Agent handoff: {propose.stdout}")
        propose_payload = json.loads(propose.stdout)
        if propose_payload.get("status") != "blocked":
            raise SystemExit("propose did not report blocked status")
        output_refs = propose_payload.get("output_refs", [])
        if ".artist-portrait/data/proposal_context.json" not in output_refs:
            raise SystemExit("propose did not report proposal_context output ref")
        if ".artist-portrait/data/text_model_gate.json" not in output_refs:
            raise SystemExit("propose did not report text_model_gate output ref")
        if ".artist-portrait/data/proposal_request.json" not in output_refs:
            raise SystemExit("propose did not report proposal_request output ref")
        if "output/proposal_agent_handoff.json" not in output_refs:
            raise SystemExit("propose did not report proposal_agent_handoff output ref")
        if ".artist-portrait/data/proposal_adapter_check.json" not in output_refs:
            raise SystemExit("propose did not report proposal_adapter_check output ref")
        if ".artist-portrait/data/proposal_provider_registry.json" not in output_refs:
            raise SystemExit("propose did not report proposal_provider_registry output ref")
        if ".artist-portrait/data/proposal_mock_adapter_handshake.json" not in output_refs:
            raise SystemExit("propose did not report proposal_mock_adapter_handshake output ref")
        if ".artist-portrait/data/proposal_execution_approval_request.json" not in output_refs:
            raise SystemExit("propose did not report proposal_execution_approval_request output ref")
        if ".artist-portrait/data/proposal_execution_approval_record.json" not in output_refs:
            raise SystemExit("propose did not report proposal_execution_approval_record output ref")
        if ".artist-portrait/data/proposal_execution_readiness_plan.json" not in output_refs:
            raise SystemExit("propose did not report proposal_execution_readiness_plan output ref")
        if ".artist-portrait/data/proposal_execution_input_bundle.json" not in output_refs:
            raise SystemExit("propose did not report proposal_execution_input_bundle output ref")
        if ".artist-portrait/data/proposal_provider_call_dry_run.json" not in output_refs:
            raise SystemExit("propose did not report proposal_provider_call_dry_run output ref")
        if ".artist-portrait/data/proposal_execution_authorization.json" not in output_refs:
            raise SystemExit("propose did not report proposal_execution_authorization output ref")
        if ".artist-portrait/data/proposal_provider_response_intake_plan.json" not in output_refs:
            raise SystemExit("propose did not report proposal_provider_response_intake_plan output ref")
        if ".artist-portrait/data/proposal_provider_output_quarantine.json" not in output_refs:
            raise SystemExit("propose did not report proposal_provider_output_quarantine output ref")
        if ".artist-portrait/data/proposal_provider_response_validation_plan.json" not in output_refs:
            raise SystemExit(
                "propose did not report proposal_provider_response_validation_plan output ref"
            )
        if ".artist-portrait/data/proposal_promotion_authorization_plan.json" not in output_refs:
            raise SystemExit(
                "propose did not report proposal_promotion_authorization_plan output ref"
            )
        if ".artist-portrait/data/proposal_promotion_validation_report.json" not in output_refs:
            raise SystemExit(
                "propose did not report proposal_promotion_validation_report output ref"
            )
        if ".artist-portrait/data/proposal_canonical_write_transaction_plan.json" not in output_refs:
            raise SystemExit(
                "propose did not report proposal_canonical_write_transaction_plan output ref"
            )
        if ".artist-portrait/data/proposal_provider_result.json" not in output_refs:
            raise SystemExit("propose did not report proposal_provider_result output ref")
        if not any(
            "host_agent_candidate_required" in warning
            for warning in propose_payload.get("warnings", [])
        ):
            raise SystemExit("propose did not request a host-Agent candidate")
        status = subprocess.run(
            [str(ARTIST_PORTRAIT), "status", "--project", str(project), "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if status.returncode != 0:
            raise SystemExit(f"status failed after blocked propose: {status.stdout}")
        status_payload = json.loads(status.stdout)
        proposal_integrity_issues = [
            issue
            for issue in status_payload.get("artifact_issues", [])
            if issue.get("code", "").startswith("proposal_")
            or issue.get("step") == "propose"
        ]
        if proposal_integrity_issues:
            raise SystemExit(
                "blocked propose produced an inconsistent artifact chain: "
                + json.dumps(proposal_integrity_issues, sort_keys=True)
            )
        context = tmp_path / ".artist-portrait" / "data" / "proposal_context.json"
        gate = tmp_path / ".artist-portrait" / "data" / "text_model_gate.json"
        request = tmp_path / ".artist-portrait" / "data" / "proposal_request.json"
        adapter_check = (
            tmp_path / ".artist-portrait" / "data" / "proposal_adapter_check.json"
        )
        registry = (
            tmp_path / ".artist-portrait" / "data" / "proposal_provider_registry.json"
        )
        handshake = (
            tmp_path / ".artist-portrait" / "data" / "proposal_mock_adapter_handshake.json"
        )
        approval = (
            tmp_path
            / ".artist-portrait"
            / "data"
            / "proposal_execution_approval_request.json"
        )
        approval_record = (
            tmp_path
            / ".artist-portrait"
            / "data"
            / "proposal_execution_approval_record.json"
        )
        readiness_plan = (
            tmp_path
            / ".artist-portrait"
            / "data"
            / "proposal_execution_readiness_plan.json"
        )
        input_bundle = (
            tmp_path
            / ".artist-portrait"
            / "data"
            / "proposal_execution_input_bundle.json"
        )
        call_dry_run = (
            tmp_path
            / ".artist-portrait"
            / "data"
            / "proposal_provider_call_dry_run.json"
        )
        authorization = (
            tmp_path / ".artist-portrait" / "data" / "proposal_execution_authorization.json"
        )
        response_intake = (
            tmp_path
            / ".artist-portrait"
            / "data"
            / "proposal_provider_response_intake_plan.json"
        )
        quarantine = (
            tmp_path
            / ".artist-portrait"
            / "data"
            / "proposal_provider_output_quarantine.json"
        )
        response_validation = (
            tmp_path
            / ".artist-portrait"
            / "data"
            / "proposal_provider_response_validation_plan.json"
        )
        promotion_authorization = (
            tmp_path
            / ".artist-portrait"
            / "data"
            / "proposal_promotion_authorization_plan.json"
        )
        promotion_validation_report = (
            tmp_path
            / ".artist-portrait"
            / "data"
            / "proposal_promotion_validation_report.json"
        )
        write_transaction = (
            tmp_path
            / ".artist-portrait"
            / "data"
            / "proposal_canonical_write_transaction_plan.json"
        )
        result = (
            tmp_path / ".artist-portrait" / "data" / "proposal_provider_result.json"
        )
        if not context.exists():
            raise SystemExit("blocked propose did not write proposal_context.json")
        if not gate.exists():
            raise SystemExit("blocked propose did not write text_model_gate.json")
        if not request.exists():
            raise SystemExit("blocked propose did not write proposal_request.json")
        if not adapter_check.exists():
            raise SystemExit("blocked propose did not write proposal_adapter_check.json")
        if not registry.exists():
            raise SystemExit("blocked propose did not write proposal_provider_registry.json")
        if not handshake.exists():
            raise SystemExit("blocked propose did not write proposal_mock_adapter_handshake.json")
        if not approval.exists():
            raise SystemExit("blocked propose did not write proposal_execution_approval_request.json")
        if not approval_record.exists():
            raise SystemExit("blocked propose did not write proposal_execution_approval_record.json")
        if not readiness_plan.exists():
            raise SystemExit("blocked propose did not write proposal_execution_readiness_plan.json")
        if not input_bundle.exists():
            raise SystemExit("blocked propose did not write proposal_execution_input_bundle.json")
        if not call_dry_run.exists():
            raise SystemExit("blocked propose did not write proposal_provider_call_dry_run.json")
        if not authorization.exists():
            raise SystemExit("blocked propose did not write proposal_execution_authorization.json")
        if not response_intake.exists():
            raise SystemExit("blocked propose did not write proposal_provider_response_intake_plan.json")
        if not quarantine.exists():
            raise SystemExit("blocked propose did not write proposal_provider_output_quarantine.json")
        if not response_validation.exists():
            raise SystemExit(
                "blocked propose did not write proposal_provider_response_validation_plan.json"
            )
        if not promotion_authorization.exists():
            raise SystemExit(
                "blocked propose did not write proposal_promotion_authorization_plan.json"
            )
        if not promotion_validation_report.exists():
            raise SystemExit(
                "blocked propose did not write proposal_promotion_validation_report.json"
            )
        if not write_transaction.exists():
            raise SystemExit(
                "blocked propose did not write proposal_canonical_write_transaction_plan.json"
            )
        if not result.exists():
            raise SystemExit("blocked propose did not write proposal_provider_result.json")
        context_payload = json.loads(context.read_text(encoding="utf-8"))
        if not context_payload.get("bgm_requirements"):
            raise SystemExit("proposal_context did not carry BGM requirements")
        gate_payload = json.loads(gate.read_text(encoding="utf-8"))
        if gate_payload.get("status") != "blocked":
            raise SystemExit("text_model_gate did not record blocked status")
        request_payload = json.loads(request.read_text(encoding="utf-8"))
        if request_payload.get("status") != "blocked":
            raise SystemExit("proposal_request did not record blocked status")
        if request_payload.get("target_schema_name") != "ProposalSet":
            raise SystemExit("proposal_request did not target ProposalSet")
        adapter_payload = json.loads(adapter_check.read_text(encoding="utf-8"))
        if adapter_payload.get("model_call_performed") is not False:
            raise SystemExit("proposal_adapter_check reported a model call")
        if adapter_payload.get("network_performed") is not False:
            raise SystemExit("proposal_adapter_check reported network access")
        registry_payload = json.loads(registry.read_text(encoding="utf-8"))
        if registry_payload.get("generation_open") is not False:
            raise SystemExit("proposal_provider_registry opened generation unexpectedly")
        handshake_payload = json.loads(handshake.read_text(encoding="utf-8"))
        if handshake_payload.get("proposal_content_generated") is not False:
            raise SystemExit("proposal_mock_adapter_handshake generated proposal content")
        approval_payload = json.loads(approval.read_text(encoding="utf-8"))
        if approval_payload.get("approval_recorded") is not False:
            raise SystemExit("proposal_execution_approval_request recorded approval unexpectedly")
        if approval_payload.get("selected_secret_source") is not None:
            raise SystemExit("proposal_execution_approval_request selected a secret source")
        if approval_payload.get("credential_value_read") is not False:
            raise SystemExit("proposal_execution_approval_request read credential material")
        if approval_payload.get("execution_performed") is not False:
            raise SystemExit("proposal_execution_approval_request performed execution unexpectedly")
        approval_record_payload = json.loads(approval_record.read_text(encoding="utf-8"))
        if approval_record_payload.get("approval_granted") is not False:
            raise SystemExit("proposal_execution_approval_record granted approval unexpectedly")
        if approval_record_payload.get("selected_secret_source") is not None:
            raise SystemExit("proposal_execution_approval_record selected a secret source")
        if approval_record_payload.get("credential_value_read") is not False:
            raise SystemExit("proposal_execution_approval_record read credential material")
        if approval_record_payload.get("execution_allowed") is not False:
            raise SystemExit("proposal_execution_approval_record allowed execution unexpectedly")
        readiness_payload = json.loads(readiness_plan.read_text(encoding="utf-8"))
        if readiness_payload.get("selected_secret_source") is not None:
            raise SystemExit("proposal_execution_readiness_plan selected a secret source")
        if readiness_payload.get("credential_value_read") is not False:
            raise SystemExit("proposal_execution_readiness_plan read credential material")
        if readiness_payload.get("execution_allowed") is not False:
            raise SystemExit("proposal_execution_readiness_plan allowed execution unexpectedly")
        if readiness_payload.get("raw_output_captured") is not False:
            raise SystemExit("proposal_execution_readiness_plan captured raw output unexpectedly")
        input_bundle_payload = json.loads(input_bundle.read_text(encoding="utf-8"))
        for item_id in (
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
        ):
            item = input_bundle_payload.get(item_id) or {}
            if item.get("status") != "blocked":
                raise SystemExit(f"proposal_execution_input_bundle {item_id} is not blocked")
        if input_bundle_payload.get("selected_secret_source") is not None:
            raise SystemExit("proposal_execution_input_bundle selected a secret source")
        if input_bundle_payload.get("credential_value_read") is not False:
            raise SystemExit("proposal_execution_input_bundle read credential material")
        if input_bundle_payload.get("execution_allowed") is not False:
            raise SystemExit("proposal_execution_input_bundle allowed execution unexpectedly")
        if input_bundle_payload.get("raw_output_captured") is not False:
            raise SystemExit("proposal_execution_input_bundle captured raw output unexpectedly")
        if input_bundle_payload.get("prompt_embedded") is not False:
            raise SystemExit("proposal_execution_input_bundle embedded a prompt unexpectedly")
        call_dry_run_payload = json.loads(call_dry_run.read_text(encoding="utf-8"))
        for item_id in (
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
        ):
            item = call_dry_run_payload.get(item_id) or {}
            if item.get("status") != "blocked":
                raise SystemExit(f"proposal_provider_call_dry_run {item_id} is not blocked")
        if call_dry_run_payload.get("endpoint_resolved") is not False:
            raise SystemExit("proposal_provider_call_dry_run resolved an endpoint")
        if call_dry_run_payload.get("auth_header_materialized") is not False:
            raise SystemExit("proposal_provider_call_dry_run materialized an auth header")
        if call_dry_run_payload.get("request_body_materialized") is not False:
            raise SystemExit("proposal_provider_call_dry_run materialized a request body")
        if call_dry_run_payload.get("credential_value_read") is not False:
            raise SystemExit("proposal_provider_call_dry_run read credential material")
        if call_dry_run_payload.get("execution_allowed") is not False:
            raise SystemExit("proposal_provider_call_dry_run allowed execution unexpectedly")
        if call_dry_run_payload.get("network_performed") is not False:
            raise SystemExit("proposal_provider_call_dry_run performed network unexpectedly")
        if call_dry_run_payload.get("request_payload_sent") is not False:
            raise SystemExit("proposal_provider_call_dry_run sent a request payload")
        if call_dry_run_payload.get("raw_output_captured") is not False:
            raise SystemExit("proposal_provider_call_dry_run captured raw output")
        authorization_payload = json.loads(authorization.read_text(encoding="utf-8"))
        if authorization_payload.get("approved_execution_gate") is not False:
            raise SystemExit("proposal_execution_authorization opened execution gate")
        if authorization_payload.get("user_approval_present") is not False:
            raise SystemExit("proposal_execution_authorization recorded user approval unexpectedly")
        if authorization_payload.get("model_call_allowed") is not False:
            raise SystemExit("proposal_execution_authorization allowed model calls unexpectedly")
        if authorization_payload.get("execution_performed") is not False:
            raise SystemExit("proposal_execution_authorization performed execution unexpectedly")
        response_intake_payload = json.loads(response_intake.read_text(encoding="utf-8"))
        for item_id in (
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
        ):
            item = response_intake_payload.get(item_id) or {}
            if item.get("status") != "blocked":
                raise SystemExit(f"proposal_provider_response_intake_plan {item_id} is not blocked")
            if item.get("allowed") is not False:
                raise SystemExit(f"proposal_provider_response_intake_plan {item_id} is allowed")
            if item.get("materialized") is not False:
                raise SystemExit(f"proposal_provider_response_intake_plan {item_id} is materialized")
        if response_intake_payload.get("response_channel_open") is not False:
            raise SystemExit("proposal_provider_response_intake_plan opened response channel")
        if response_intake_payload.get("raw_output_location_materialized") is not False:
            raise SystemExit("proposal_provider_response_intake_plan materialized raw output location")
        if response_intake_payload.get("content_type_validated") is not False:
            raise SystemExit("proposal_provider_response_intake_plan validated content type")
        if response_intake_payload.get("size_limit_bytes") != 0:
            raise SystemExit("proposal_provider_response_intake_plan set a size limit")
        if response_intake_payload.get("checksum_computed") is not False:
            raise SystemExit("proposal_provider_response_intake_plan computed checksum")
        if response_intake_payload.get("redaction_performed") is not False:
            raise SystemExit("proposal_provider_response_intake_plan performed redaction")
        if response_intake_payload.get("parser_selected") is not False:
            raise SystemExit("proposal_provider_response_intake_plan selected parser")
        if response_intake_payload.get("validation_enqueued") is not False:
            raise SystemExit("proposal_provider_response_intake_plan enqueued validation")
        if response_intake_payload.get("promotion_allowed") is not False:
            raise SystemExit("proposal_provider_response_intake_plan allowed promotion")
        if response_intake_payload.get("audit_event_written") is not False:
            raise SystemExit("proposal_provider_response_intake_plan wrote audit event")
        if response_intake_payload.get("raw_output_captured") is not False:
            raise SystemExit("proposal_provider_response_intake_plan captured raw output")
        if response_intake_payload.get("parsed_payload_generated") is not False:
            raise SystemExit("proposal_provider_response_intake_plan generated parsed payload")
        if response_intake_payload.get("validation_performed") is not False:
            raise SystemExit("proposal_provider_response_intake_plan performed validation")
        if response_intake_payload.get("promoted_to_proposals") is not False:
            raise SystemExit("proposal_provider_response_intake_plan promoted proposals")
        if response_intake_payload.get("model_call_performed") is not False:
            raise SystemExit("proposal_provider_response_intake_plan performed model call")
        if response_intake_payload.get("network_performed") is not False:
            raise SystemExit("proposal_provider_response_intake_plan performed network access")
        if response_intake_payload.get("proposal_content_generated") is not False:
            raise SystemExit("proposal_provider_response_intake_plan generated proposal content")
        quarantine_payload = json.loads(quarantine.read_text(encoding="utf-8"))
        if quarantine_payload.get("raw_output_captured") is not False:
            raise SystemExit("proposal_provider_output_quarantine captured raw output unexpectedly")
        if quarantine_payload.get("parsed_payload_generated") is not False:
            raise SystemExit("proposal_provider_output_quarantine generated parsed payload")
        if quarantine_payload.get("promoted_to_proposals") is not False:
            raise SystemExit("proposal_provider_output_quarantine promoted output to proposals")
        if quarantine_payload.get("validation_performed") is not False:
            raise SystemExit("proposal_provider_output_quarantine performed validation unexpectedly")
        response_validation_payload = json.loads(
            response_validation.read_text(encoding="utf-8")
        )
        for item_id in (
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
        ):
            item = response_validation_payload.get(item_id) or {}
            if item.get("status") != "blocked":
                raise SystemExit(
                    f"proposal_provider_response_validation_plan {item_id} is not blocked"
                )
            if item.get("allowed") is not False:
                raise SystemExit(
                    f"proposal_provider_response_validation_plan {item_id} is allowed"
                )
            if item.get("materialized") is not False:
                raise SystemExit(
                    f"proposal_provider_response_validation_plan {item_id} is materialized"
                )
        for field in (
            "quarantine_input_bound",
            "content_type_checked",
            "size_limit_checked",
            "checksum_verified",
            "redaction_verified",
            "parser_contract_selected",
            "json_syntax_validated",
            "schema_validated",
            "semantic_validation_performed",
            "promotion_decided",
            "raw_output_read",
            "parsed_payload_generated",
            "validation_performed",
            "promoted_to_proposals",
            "audit_event_written",
            "model_call_performed",
            "network_performed",
            "proposal_content_generated",
        ):
            if response_validation_payload.get(field) is not False:
                raise SystemExit(
                    f"proposal_provider_response_validation_plan unexpectedly set {field}"
                )
        promotion_payload = json.loads(
            promotion_authorization.read_text(encoding="utf-8")
        )
        for item_id in (
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
        ):
            item = promotion_payload.get(item_id) or {}
            if item.get("status") != "blocked":
                raise SystemExit(
                    f"proposal_promotion_authorization_plan {item_id} is not blocked"
                )
            if item.get("allowed") is not False:
                raise SystemExit(
                    f"proposal_promotion_authorization_plan {item_id} is allowed"
                )
            if item.get("materialized") is not False:
                raise SystemExit(
                    f"proposal_promotion_authorization_plan {item_id} is materialized"
                )
        for field in (
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
        ):
            if promotion_payload.get(field) is not False:
                raise SystemExit(
                    f"proposal_promotion_authorization_plan unexpectedly set {field}"
                )
        promotion_report_payload = json.loads(
            promotion_validation_report.read_text(encoding="utf-8")
        )
        for check_id in (
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
        ):
            check = promotion_report_payload.get(check_id) or {}
            if check.get("status") != "blocked":
                raise SystemExit(
                    f"proposal_promotion_validation_report {check_id} is not blocked"
                )
            if check.get("performed") is not False or check.get("passed") is not False:
                raise SystemExit(
                    f"proposal_promotion_validation_report fabricated {check_id}"
                )
        for field in (
            "overall_passed",
            "promotion_recommended",
            "promotion_authorized",
            "promotion_performed",
            "proposals_file_written",
            "model_call_performed",
            "network_performed",
            "proposal_content_generated",
        ):
            if promotion_report_payload.get(field) is not False:
                raise SystemExit(
                    f"proposal_promotion_validation_report unexpectedly set {field}"
                )
        if promotion_report_payload.get("checks_performed") != 0:
            raise SystemExit("proposal_promotion_validation_report performed checks")
        if promotion_report_payload.get("checks_passed") != 0:
            raise SystemExit("proposal_promotion_validation_report passed checks")
        transaction_payload = json.loads(write_transaction.read_text(encoding="utf-8"))
        for item_id in (
            "target_lock", "prewrite_snapshot", "temporary_file",
            "schema_prewrite_check", "durability_policy", "atomic_replace",
            "conflict_detection", "rollback_plan", "audit_commit",
            "postcommit_verification",
        ):
            item = transaction_payload.get(item_id) or {}
            if (
                item.get("status") != "blocked"
                or item.get("allowed") is not False
                or item.get("materialized") is not False
            ):
                raise SystemExit(
                    f"proposal_canonical_write_transaction_plan opened {item_id}"
                )
        for field in (
            "lock_acquired", "snapshot_created", "temporary_file_created",
            "schema_prewrite_passed", "fsync_performed",
            "atomic_replace_performed", "conflict_check_performed",
            "rollback_prepared", "rollback_performed", "audit_commit_written",
            "postcommit_verified", "transaction_started",
            "transaction_committed", "proposals_file_written",
            "model_call_performed", "network_performed",
            "proposal_content_generated",
        ):
            if transaction_payload.get(field) is not False:
                raise SystemExit(
                    f"proposal_canonical_write_transaction_plan unexpectedly set {field}"
                )
        result_payload = json.loads(result.read_text(encoding="utf-8"))
        if result_payload.get("payload_generated") is not False:
            raise SystemExit("proposal_provider_result generated a payload")
        if result_payload.get("validation_performed") is not False:
            raise SystemExit("proposal_provider_result performed validation unexpectedly")
        if result_payload.get("proposal_content_generated") is not False:
            raise SystemExit("proposal_provider_result generated proposal content")
        if (tmp_path / ".artist-portrait" / "data" / "proposals.json").exists():
            raise SystemExit("blocked propose wrote proposals.json")
        if (tmp_path / "output" / "proposals.md").exists():
            raise SystemExit("blocked propose wrote proposals.md")

        write_valid_proposals_from_context(tmp_path)
        proposals = tmp_path / ".artist-portrait" / "data" / "proposals.json"
        candidate = tmp_path / "host_agent_candidate.json"
        proposals.replace(candidate)
        import_proposal = subprocess.run(
            [
                str(ARTIST_PORTRAIT),
                "propose",
                "--project",
                str(project),
                "--agent-output",
                str(candidate),
                "--json",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if import_proposal.returncode != 0:
            raise SystemExit(
                f"host-Agent proposal import failed: {import_proposal.stdout}"
            )
        import_payload = json.loads(import_proposal.stdout)
        if not import_payload.get("quarantine"):
            raise SystemExit("host-Agent proposal import did not report quarantine")
        if import_payload.get("output") != ".artist-portrait/data/proposals.json":
            raise SystemExit("host-Agent proposal import did not promote proposals")
        review_proposal = subprocess.run(
            [
                str(ARTIST_PORTRAIT),
                "review",
                "--project",
                str(project),
                "--scope",
                "proposal",
                "--json",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if review_proposal.returncode != 0:
            raise SystemExit(
                f"proposal review validation failed: {review_proposal.stdout}"
            )
        review_proposal_payload = json.loads(review_proposal.stdout)
        if review_proposal_payload.get("issues") != []:
            raise SystemExit("proposal review reported issues for valid proposals")
        proposal_validation = (
            tmp_path / ".artist-portrait" / "data" / "proposal_validation.json"
        )
        proposal_review = tmp_path / "output" / "proposal_review.md"
        if not proposal_validation.exists():
            raise SystemExit("review --scope proposal did not write validation JSON")
        if not proposal_review.exists():
            raise SystemExit("review --scope proposal did not write Markdown report")
        validation_payload = json.loads(proposal_validation.read_text(encoding="utf-8"))
        if validation_payload.get("error_count") != 0:
            raise SystemExit("valid proposal fixture produced validation errors")
        if "No proposal validation issues" not in proposal_review.read_text(
            encoding="utf-8"
        ):
            raise SystemExit("proposal review report did not record clean validation")

        (tmp_path / "output" / "material_map.md").unlink()
        run(
            [str(ARTIST_PORTRAIT), "review", "--project", str(project), "--quiet"],
            expect=1,
        )
        status = subprocess.run(
            [str(ARTIST_PORTRAIT), "status", "--project", str(project), "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if status.returncode != 0:
            raise SystemExit(f"status dashboard check failed: {status.stderr}")
        payload = json.loads(status.stdout)
        if payload["summaries"]["sources"]["count"] != 1:
            raise SystemExit("status dashboard did not summarize sources")
        if payload["summaries"]["clips"]["count"] != 1:
            raise SystemExit("status dashboard did not summarize clips")
        if not payload["artifacts"]["clip_report"]["exists"]:
            raise SystemExit("status dashboard did not report clip_report")
        if payload["artifacts"]["material_map"]["exists"]:
            raise SystemExit("status dashboard did not report missing material_map")
        if not payload["artifacts"]["risk_report"]["exists"]:
            raise SystemExit("status dashboard did not report risk_report")
        if payload["latest_run"].get("command") != "review":
            raise SystemExit("status dashboard did not report latest review run")
        artifact_issues = payload.get("artifact_issues") or []
        if not any(issue.get("code") == "missing_output_ref" for issue in artifact_issues):
            raise SystemExit("status dashboard did not report missing output ref")
        doctor = subprocess.run(
            [str(ARTIST_PORTRAIT), "doctor", "--project", str(project), "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if doctor.returncode != 1:
            raise SystemExit(f"doctor did not report artifact issue: {doctor.stdout}")
        doctor_payload = json.loads(doctor.stdout)
        if not any(
            issue.get("code") == "missing_output_ref"
            for issue in doctor_payload.get("issues", [])
        ):
            raise SystemExit("doctor did not include missing output ref")
        risk_report = (tmp_path / "output" / "risk_report.md").read_text(
            encoding="utf-8"
        )
        if "# Risk Report" not in risk_report or "rights_unknown" not in risk_report:
            raise SystemExit("risk_report content check failed")
        if "missing_output_ref" not in risk_report:
            raise SystemExit("risk_report did not include missing output ref")
        run_report = tmp_path / "output" / "run_report.md"
        report = run_report.read_text(encoding="utf-8")
        if "- `review_project`: `completed_with_warnings`" not in report:
            raise SystemExit("run_report was not refreshed after review")
        for name in (
            "clip_report.md.tmp",
            "material_map.md.tmp",
            "risk_report.md.tmp",
            "run_report.md.tmp",
        ):
            if (tmp_path / "output" / name).exists():
                raise SystemExit(f"temporary output file was left behind: {name}")

        (data_dir / "sources.jsonl").write_text(
            '{"source_id": "missing-required-fields"}\n',
            encoding="utf-8",
        )
        for command in ("map", "review"):
            failed = subprocess.run(
                [str(ARTIST_PORTRAIT), command, "--project", str(project), "--quiet"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            if failed.returncode != 9:
                raise SystemExit(
                    f"{command} accepted invalid sources unexpectedly: {failed.stderr}"
                )
            if "invalid SourceRecord JSONL" not in failed.stderr:
                raise SystemExit(f"{command} did not report invalid sources")
        invalid_status = subprocess.run(
            [str(ARTIST_PORTRAIT), "status", "--project", str(project), "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if invalid_status.returncode != 0:
            raise SystemExit(f"invalid source status check failed: {invalid_status.stderr}")
        invalid_payload = json.loads(invalid_status.stdout)
        if invalid_payload["summaries"]["sources"].get("valid") is not False:
            raise SystemExit("status dashboard did not report invalid sources")
        invalid_doctor = subprocess.run(
            [str(ARTIST_PORTRAIT), "doctor", "--project", str(project), "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if invalid_doctor.returncode != 1:
            raise SystemExit("doctor did not report invalid sources")
        invalid_doctor_payload = json.loads(invalid_doctor.stdout)
        if not any(
            issue.get("code") == "source_ledger_invalid"
            for issue in invalid_doctor_payload.get("issues", [])
        ):
            raise SystemExit("doctor did not classify invalid sources")


def check_real_media_acceptance_profiles_if_available() -> None:
    if shutil.which("ffprobe") is None or shutil.which("ffmpeg") is None:
        print("skipping real media acceptance profile check; ffmpeg/ffprobe not found")
        return
    with tempfile.TemporaryDirectory(prefix="artist-portrait-real-acceptance-") as tmp:
        tmp_path = Path(tmp)
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        project = tmp_path / "project.yaml"
        project_text = (ROOT / "fixtures" / "stage_a" / "valid_project.yaml").read_text(
            encoding="utf-8"
        )
        project.write_text(
            project_text.replace("scene_detection: auto", "scene_detection: off")
            .replace("transcription: auto", "transcription: off")
            .replace("target_duration_seconds: 180", "target_duration_seconds: 2"),
            encoding="utf-8",
        )
        write_test_video_mp4(media_dir / "source.mp4", seconds=2.0)
        (tmp_path / "sources.csv").write_text(
            "location,source_type,work,role,rights_status,forbidden_by_user,notes\n"
            "media/source.mp4,interview,Generated Video,Test Role,owned,false,"
            "real acceptance profile fixture\n",
            encoding="utf-8",
        )

        run([str(ARTIST_PORTRAIT), "init", "--project", str(project), "--quiet"], expect=(0, 1))
        initial_workflow = run_json(
            [
                str(ARTIST_PORTRAIT),
                "workflow",
                "--project",
                str(project),
                "--target",
                "delivery",
                "--json",
            ],
            expect=1,
        )
        initial_workflow_plan = initial_workflow.get("workflow_plan") or {}
        if initial_workflow_plan.get("next_command") != "artist-portrait scan --project <project.yaml>":
            raise SystemExit("real acceptance fixture workflow did not start at scan")
        if initial_workflow_plan.get("commands_executed") is not False:
            raise SystemExit("real acceptance fixture workflow executed commands")
        run([str(ARTIST_PORTRAIT), "scan", "--project", str(project), "--quiet"])
        run([str(ARTIST_PORTRAIT), "segment", "--project", str(project), "--quiet"])
        run([str(ARTIST_PORTRAIT), "keyframes", "--project", str(project), "--quiet"], expect=(0, 1))
        run([str(ARTIST_PORTRAIT), "analyze", "--project", str(project), "--quiet"])
        run([str(ARTIST_PORTRAIT), "map", "--project", str(project), "--quiet"])
        blocked = run_json(
            [str(ARTIST_PORTRAIT), "propose", "--project", str(project), "--json"],
            expect=1,
        )
        if blocked.get("status") != "blocked":
            raise SystemExit("real acceptance fixture did not prepare host-Agent handoff")

        write_valid_proposals_from_context(tmp_path)
        canonical = tmp_path / ".artist-portrait" / "data" / "proposals.json"
        candidate = tmp_path / "proposal_candidate.json"
        candidate.write_bytes(canonical.read_bytes())
        canonical.unlink()
        run(
            [
                str(ARTIST_PORTRAIT),
                "propose",
                "--project",
                str(project),
                "--agent-output",
                str(candidate),
                "--quiet",
            ]
        )
        run(
            [
                str(ARTIST_PORTRAIT),
                "timeline",
                "--project",
                str(project),
                "--proposal",
                "proposal_safe",
                "--quiet",
            ],
            expect=(0, 1),
        )

        write_sine_wav(media_dir / "bgm.wav", seconds=1.0)
        bgm_import = run_json(
            [
                str(ARTIST_PORTRAIT),
                "bgm",
                "import",
                "--project",
                str(project),
                "--file",
                "media/bgm.wav",
                "--rights-status",
                "owned",
                "--json",
            ],
            expect=(0, 1),
        )
        candidate_id = bgm_import["candidate"]["music_candidate_id"]
        bgm_analysis = run_json(
            [
                str(ARTIST_PORTRAIT),
                "bgm",
                "analyze",
                "--project",
                str(project),
                "--json",
            ],
            expect=(0, 1),
        )
        if (bgm_analysis.get("analysis") or {}).get("automatic_music_selection") is not False:
            raise SystemExit("real acceptance fixture BGM analysis selected music")
        bgm_rhythm = run_json(
            [
                str(ARTIST_PORTRAIT),
                "bgm",
                "rhythm",
                "--project",
                str(project),
                "--json",
            ],
            expect=(0, 1),
        )
        bgm_rhythm_report = bgm_rhythm.get("bgm_rhythm_intelligence") or {}
        if bgm_rhythm_report.get("automatic_music_selection") is not False:
            raise SystemExit("real acceptance fixture BGM rhythm selected music")
        if bgm_rhythm_report.get("edit_points_moved") is not False:
            raise SystemExit("real acceptance fixture BGM rhythm moved edit points")
        if bgm_rhythm_report.get("media_rendered") is not False:
            raise SystemExit("real acceptance fixture BGM rhythm rendered media")
        if bgm_rhythm_report.get("fabricated_bpm_or_beats") is not False:
            raise SystemExit("real acceptance fixture BGM rhythm fabricated BPM or beats")
        run(
            [
                str(ARTIST_PORTRAIT),
                "bgm",
                "fit",
                "--project",
                str(project),
                "--candidate",
                candidate_id,
                "--fit-mode",
                "loop",
                "--fade-in-seconds",
                "0.1",
                "--fade-out-seconds",
                "0.1",
                "--ducking-gain-db",
                "-9",
                "--quiet",
            ],
            expect=(0, 1),
        )
        bgm_review = run_json(
            [str(ARTIST_PORTRAIT), "bgm", "review", "--project", str(project), "--json"],
            expect=(0, 1),
        )
        if bgm_review.get("status") not in {"passed", "warning"}:
            raise SystemExit("real acceptance fixture BGM review did not complete")
        rhythm_intent = tmp_path / "rhythm_intent.json"
        rhythm_intent.write_text(
            json.dumps(
                {
                    "intent_id": "run_checks_rhythm_intent",
                    "mode": "speech_first",
                    "pacing": "medium",
                    "text_density": "low",
                    "transition_style": "smooth",
                    "ending_style": "fade_out",
                    "notes": "run_checks rhythm planning fixture",
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
        rhythm_payload = run_json(
            [
                str(ARTIST_PORTRAIT),
                "rhythm",
                "--project",
                str(project),
                "--intent",
                str(rhythm_intent),
                "--json",
            ],
            expect=(0, 1),
        )
        rhythm_plan = rhythm_payload.get("rhythm_plan") or {}
        if rhythm_plan.get("edit_points_moved") is not False:
            raise SystemExit("real acceptance fixture rhythm moved edit points")
        if rhythm_plan.get("automatic_music_selection") is not False:
            raise SystemExit("real acceptance fixture rhythm selected music")
        if rhythm_plan.get("media_rendered") is not False:
            raise SystemExit("real acceptance fixture rhythm rendered media")
        if not rhythm_plan.get("bgm_rhythm_intelligence_fingerprint"):
            raise SystemExit("real acceptance fixture rhythm did not bind BGM rhythm intelligence")
        if rhythm_plan.get("timeline_profile", {}).get("domain_id") != "timeline_profile":
            raise SystemExit("real acceptance fixture rhythm timeline profile missing")
        if rhythm_plan.get("bgm_profile", {}).get("domain_id") != "bgm_profile":
            raise SystemExit("real acceptance fixture rhythm BGM profile missing")
        edit_guidance_payload = run_json(
            [
                str(ARTIST_PORTRAIT),
                "rhythm",
                "--project",
                str(project),
                "--edit-guidance",
                "--json",
            ],
            expect=(0, 1),
        )
        edit_guidance = edit_guidance_payload.get("edit_guidance") or {}
        if edit_guidance.get("action_count", 0) < 10:
            raise SystemExit("real acceptance fixture edit guidance lacks actions")
        if edit_guidance.get("manual_only") is not True:
            raise SystemExit("real acceptance fixture edit guidance is not manual-only")
        if edit_guidance.get("edit_points_moved") is not False:
            raise SystemExit("real acceptance fixture edit guidance moved edit points")
        if edit_guidance.get("timeline_mutated") is not False:
            raise SystemExit("real acceptance fixture edit guidance mutated timeline")
        if edit_guidance.get("media_rendered") is not False:
            raise SystemExit("real acceptance fixture edit guidance rendered media")
        if edit_guidance.get("automatic_music_selection") is not False:
            raise SystemExit("real acceptance fixture edit guidance selected music")
        rhythm_repair_before_media = run_json(
            [
                str(ARTIST_PORTRAIT),
                "rhythm",
                "--project",
                str(project),
                "--repair-plan",
                "--acceptance-profile",
                "delivery",
                "--json",
            ],
            expect=9,
        )
        rhythm_repair_plan = rhythm_repair_before_media.get("rhythm_repair_plan") or {}
        if rhythm_repair_plan.get("required_action_count", 0) < 3:
            raise SystemExit("real acceptance fixture rhythm repair plan lacks required actions")
        if rhythm_repair_plan.get("commands_executed") is not False:
            raise SystemExit("real acceptance fixture rhythm repair plan executed commands")
        if rhythm_repair_plan.get("media_rendered") is not False:
            raise SystemExit("real acceptance fixture rhythm repair plan rendered media")

        core = run_json(
            [
                str(ARTIST_PORTRAIT),
                "acceptance",
                "--project",
                str(project),
                "--profile",
                "core",
                "--json",
            ]
        )
        if core.get("status") != "passed" or core.get("profile_passed") is not True:
            raise SystemExit("real acceptance fixture core profile did not pass")
        delivery_plan = run_json(
            [
                str(ARTIST_PORTRAIT),
                "acceptance",
                "--project",
                str(project),
                "--profile",
                "delivery",
                "--repair-plan",
                "--json",
            ],
            expect=9,
        )
        repair_plan = delivery_plan.get("repair_plan") or {}
        if repair_plan.get("required_action_count", 0) < 2:
            raise SystemExit("real acceptance fixture repair plan lacks required actions")
        if repair_plan.get("first_required_command") != "artist-portrait preview --project <project.yaml>":
            raise SystemExit("real acceptance fixture repair plan first command is wrong")
        if repair_plan.get("automatic_repair_performed") is not False:
            raise SystemExit("real acceptance fixture repair plan performed repair")
        approval_request_payload = run_json(
            [
                str(ARTIST_PORTRAIT),
                "acceptance",
                "--project",
                str(project),
                "--profile",
                "delivery",
                "--approval-request",
                "--json",
            ],
            expect=9,
        )
        approval_request = approval_request_payload.get("approval_request") or {}
        if approval_request.get("repair_plan_id") != repair_plan.get("repair_plan_id"):
            raise SystemExit("real acceptance fixture approval request is not bound to repair plan")
        if not approval_request.get("actions"):
            raise SystemExit("real acceptance fixture approval request has no actions")
        if any(action.get("decision") != "pending" for action in approval_request.get("actions", [])):
            raise SystemExit("real acceptance fixture approval request is not pending")
        approval_candidate = tmp_path / "approval_record_candidate.json"
        approval_candidate.write_text(
            json.dumps(
                {
                    "schema_version": "0.3",
                    "approval_record_id": "run_checks_approval_candidate",
                    "project_id": approval_request["project_id"],
                    "repair_plan_id": approval_request["repair_plan_id"],
                    "acceptance_profile": approval_request["acceptance_profile"],
                    "valid": False,
                    "approved_action_ids": [],
                    "rejected_action_ids": [],
                    "issue_count": 0,
                    "issues": [],
                    "actions": [
                        {
                            **action,
                            "decision": "approved",
                            "rationale": "run_checks dry run approval",
                        }
                        for action in approval_request.get("actions", [])
                        if action.get("required_for_profile")
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
        dry_run_payload = run_json(
            [
                str(ARTIST_PORTRAIT),
                "acceptance",
                "--project",
                str(project),
                "--profile",
                "delivery",
                "--approval-record",
                str(approval_candidate),
                "--execution-dry-run",
                "--execution-bundle",
                "--json",
            ],
            expect=9,
        )
        dry_run = dry_run_payload.get("execution_dry_run") or {}
        bundle = dry_run_payload.get("execution_bundle") or {}
        if dry_run.get("commands_executed") is not False:
            raise SystemExit("real acceptance fixture dry-run executed commands")
        if any(step.get("would_execute") is not False for step in dry_run.get("steps", [])):
            raise SystemExit("real acceptance fixture dry-run step would execute")
        if bundle.get("commands_executed_by_cli") is not False:
            raise SystemExit("real acceptance fixture execution bundle executed commands")
        if any(command.get("executable_by_cli") is not False for command in bundle.get("commands", [])):
            raise SystemExit("real acceptance fixture execution bundle exposed CLI execution")
        execution_candidate = tmp_path / "execution_record_candidate.json"
        execution_candidate.write_text(
            json.dumps(
                {
                    "schema_version": "0.3",
                    "execution_record_id": "run_checks_execution_record_candidate",
                    "project_id": bundle.get("project_id"),
                    "repair_plan_id": bundle.get("repair_plan_id"),
                    "approval_record_id": bundle.get("approval_record_id"),
                    "dry_run_id": bundle.get("dry_run_id"),
                    "execution_bundle_id": bundle.get("execution_bundle_id"),
                    "acceptance_profile": bundle.get("acceptance_profile"),
                    "valid": False,
                    "completed_action_ids": [],
                    "failed_action_ids": [],
                    "skipped_action_ids": [],
                    "issue_count": 0,
                    "issues": [],
                    "actions": [
                        {
                            "action_id": command.get("action_id"),
                            "step_id": command.get("step_id"),
                            "command": command.get("command"),
                            "status": "skipped",
                            "exit_code": None,
                            "artifact_refs": [],
                            "notes": "run_checks validates evidence intake without claiming execution",
                        }
                        for command in bundle.get("commands", [])
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
        execution_payload = run_json(
            [
                str(ARTIST_PORTRAIT),
                "acceptance",
                "--project",
                str(project),
                "--profile",
                "delivery",
                "--execution-record",
                str(execution_candidate),
                "--json",
            ],
            expect=9,
        )
        execution_record = execution_payload.get("execution_record") or {}
        if execution_record.get("valid") is not True:
            raise SystemExit("real acceptance fixture execution record did not validate")
        if execution_record.get("commands_executed_by_cli") is not False:
            raise SystemExit("real acceptance fixture execution record executed commands")

        run(
            [
                str(ARTIST_PORTRAIT),
                "preview",
                "--project",
                str(project),
                "--width",
                "320",
                "--fps",
                "10",
                "--quiet",
            ],
            expect=(0, 1),
        )
        preview_rhythm_qc = run_json(
            [
                str(ARTIST_PORTRAIT),
                "rhythm",
                "--project",
                str(project),
                "--qc",
                "--json",
            ],
            expect=(0, 1),
        )
        preview_rhythm_qc_report = preview_rhythm_qc.get("rhythm_media_qc") or {}
        if preview_rhythm_qc_report.get("preview_rendered_by_qc") is not False:
            raise SystemExit("real acceptance fixture preview rhythm QC rendered preview")
        if preview_rhythm_qc_report.get("edit_points_moved") is not False:
            raise SystemExit("real acceptance fixture preview rhythm QC moved edit points")
        preview = run_json(
            [
                str(ARTIST_PORTRAIT),
                "acceptance",
                "--project",
                str(project),
                "--profile",
                "preview",
                "--json",
            ]
        )
        if preview.get("status") != "passed" or preview.get("preview_ready") is not True:
            raise SystemExit("real acceptance fixture preview profile did not pass")
        preview_stages = {stage["stage_id"]: stage for stage in preview["acceptance"]["stages"]}
        if preview_stages["rhythm_plan"]["status"] != "passed":
            raise SystemExit("real acceptance fixture preview profile did not require rhythm plan")
        if preview_stages["rhythm_media_qc"]["status"] != "passed":
            raise SystemExit("real acceptance fixture preview profile did not require rhythm media QC")

        run(
            [
                str(ARTIST_PORTRAIT),
                "export",
                "--project",
                str(project),
                "--profile",
                "review_720p",
                "--quiet",
            ],
            expect=(0, 1),
        )
        rhythm_qc = run_json(
            [
                str(ARTIST_PORTRAIT),
                "rhythm",
                "--project",
                str(project),
                "--qc",
                "--json",
            ],
            expect=(0, 1),
        )
        rhythm_qc_report = rhythm_qc.get("rhythm_media_qc") or {}
        if rhythm_qc_report.get("preview_rendered_by_qc") is not False:
            raise SystemExit("real acceptance fixture rhythm QC rendered preview")
        if rhythm_qc_report.get("final_export_rendered_by_qc") is not False:
            raise SystemExit("real acceptance fixture rhythm QC rendered final export")
        if rhythm_qc_report.get("edit_points_moved") is not False:
            raise SystemExit("real acceptance fixture rhythm QC moved edit points")
        if rhythm_qc_report.get("media_qc_summary", {}).get("domain_id") != "media_qc_summary":
            raise SystemExit("real acceptance fixture rhythm QC summary missing")
        rhythm_repair_after_media = run_json(
            [
                str(ARTIST_PORTRAIT),
                "rhythm",
                "--project",
                str(project),
                "--repair-plan",
                "--acceptance-profile",
                "delivery",
                "--json",
            ],
            expect=(0, 1, 9),
        )
        rhythm_repair_after = rhythm_repair_after_media.get("rhythm_repair_plan") or {}
        if rhythm_repair_after.get("commands_executed") is not False:
            raise SystemExit("real acceptance fixture final rhythm repair plan executed commands")
        if rhythm_repair_after.get("edit_points_moved") is not False:
            raise SystemExit("real acceptance fixture final rhythm repair plan moved edit points")
        delivery = run_json(
            [
                str(ARTIST_PORTRAIT),
                "acceptance",
                "--project",
                str(project),
                "--profile",
                "delivery",
                "--json",
            ]
        )
        if delivery.get("status") != "passed" or delivery.get("final_export_ready") is not True:
            raise SystemExit("real acceptance fixture delivery profile did not pass")
        final_workflow = run_json(
            [
                str(ARTIST_PORTRAIT),
                "workflow",
                "--project",
                str(project),
                "--target",
                "delivery",
                "--json",
            ]
        )
        final_workflow_plan = final_workflow.get("workflow_plan") or {}
        if final_workflow_plan.get("status") != "ready":
            raise SystemExit("real acceptance fixture final workflow was not ready")
        if final_workflow_plan.get("commands_executed") is not False:
            raise SystemExit("real acceptance fixture final workflow executed commands")
        workflow_steps = [
            step
            for step in final_workflow_plan.get("steps", [])
            if step.get("source") == "workflow"
        ]
        workflow_record_candidate = tmp_path / "workflow_execution_record_candidate.json"
        broken_workflow_record_candidate = tmp_path / "workflow_execution_record_broken.json"
        broken_workflow_record_candidate.write_text(
            json.dumps(
                {
                    "execution_record_id": "real_fixture_workflow_execution_broken",
                    "project_id": final_workflow_plan.get("project_id"),
                    "workflow_plan_id": final_workflow_plan.get("workflow_plan_id"),
                    "target": "delivery",
                    "executed_by": "run_checks",
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
                            "output_refs": [".artist-portrait/data/missing_sources.jsonl"],
                        },
                    ],
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        broken_workflow_execution = run_json(
            [
                str(ARTIST_PORTRAIT),
                "workflow",
                "--project",
                str(project),
                "--target",
                "delivery",
                "--execution-record",
                str(broken_workflow_record_candidate),
                "--json",
            ],
            expect=1,
        )
        if (broken_workflow_execution.get("workflow_execution_review") or {}).get("status") != "failed":
            raise SystemExit("broken workflow execution evidence did not fail review")
        workflow_repair = run_json(
            [
                str(ARTIST_PORTRAIT),
                "workflow",
                "--project",
                str(project),
                "--target",
                "delivery",
                "--repair-plan",
                "--json",
            ],
            expect=1,
        )
        workflow_repair_plan = workflow_repair.get("workflow_repair_plan") or {}
        if workflow_repair_plan.get("first_required_command") != "artist-portrait scan --project <project.yaml>":
            raise SystemExit("workflow repair plan did not point to scan repair")
        if workflow_repair_plan.get("commands_executed") is not False:
            raise SystemExit("workflow repair plan executed commands")
        if workflow_repair_plan.get("acceptance_success_promoted") is not False:
            raise SystemExit("workflow repair plan promoted acceptance success")
        workflow_approval_request = run_json(
            [
                str(ARTIST_PORTRAIT),
                "workflow",
                "--project",
                str(project),
                "--target",
                "delivery",
                "--approval-request",
                "--json",
            ],
            expect=1,
        )
        approval_request = workflow_approval_request.get("workflow_repair_approval_request") or {}
        if approval_request.get("workflow_repair_plan_id") != workflow_repair_plan.get("workflow_repair_plan_id"):
            raise SystemExit("workflow repair approval request did not bind to repair plan")
        if approval_request.get("commands_executed") is not False:
            raise SystemExit("workflow repair approval request executed commands")
        first_action_id = (workflow_repair_plan.get("actions") or [{}])[0].get("action_id")
        workflow_approval_candidate = tmp_path / "workflow_repair_approval_record_candidate.json"
        workflow_approval_candidate.write_text(
            json.dumps(
                {
                    "approval_record_id": "real_fixture_workflow_repair_approval",
                    "project_id": workflow_repair_plan.get("project_id"),
                    "workflow_repair_plan_id": workflow_repair_plan.get("workflow_repair_plan_id"),
                    "workflow_plan_id": workflow_repair_plan.get("workflow_plan_id"),
                    "workflow_execution_review_id": workflow_repair_plan.get("workflow_execution_review_id"),
                    "target": "delivery",
                    "approved_by": "run_checks",
                    "approved_action_ids": [first_action_id],
                    "rejected_action_ids": [],
                    "status": "passed",
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        workflow_approval = run_json(
            [
                str(ARTIST_PORTRAIT),
                "workflow",
                "--project",
                str(project),
                "--target",
                "delivery",
                "--approval-record",
                str(workflow_approval_candidate),
                "--json",
            ]
        )
        approval_record = workflow_approval.get("workflow_repair_approval_record") or {}
        if approval_record.get("status") != "passed":
            raise SystemExit("workflow repair approval record did not pass")
        if approval_record.get("commands_executed_by_cli") is not False:
            raise SystemExit("workflow repair approval record executed commands")
        workflow_dry_run = run_json(
            [
                str(ARTIST_PORTRAIT),
                "workflow",
                "--project",
                str(project),
                "--target",
                "delivery",
                "--repair-dry-run",
                "--json",
            ],
            expect=1,
        )
        dry_run = workflow_dry_run.get("workflow_repair_dry_run") or {}
        if dry_run.get("approved_step_count") != 1:
            raise SystemExit("workflow repair dry-run approved count is wrong")
        if dry_run.get("commands_executed") is not False:
            raise SystemExit("workflow repair dry-run executed commands")
        if dry_run.get("acceptance_success_promoted") is not False:
            raise SystemExit("workflow repair dry-run promoted acceptance success")
        approved_step = next(
            (step for step in dry_run.get("steps") or [] if step.get("status") == "approved"),
            None,
        )
        if not approved_step:
            raise SystemExit("workflow repair dry-run did not expose an approved step")
        workflow_repair_execution_candidate = tmp_path / "workflow_repair_execution_record_candidate.json"
        workflow_repair_execution_candidate.write_text(
            json.dumps(
                {
                    "execution_record_id": "real_fixture_workflow_repair_execution",
                    "project_id": dry_run.get("project_id"),
                    "workflow_repair_plan_id": dry_run.get("workflow_repair_plan_id"),
                    "approval_record_id": dry_run.get("approval_record_id"),
                    "dry_run_id": dry_run.get("dry_run_id"),
                    "target": "delivery",
                    "executed_by": "run_checks",
                    "actions": [
                        {
                            "action_id": approved_step.get("action_id"),
                            "step_id": approved_step.get("step_id"),
                            "command": approved_step.get("command"),
                            "status": "succeeded",
                            "exit_code": 0,
                            "output_refs": approved_step.get("expected_artifacts") or [],
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        workflow_repair_execution = run_json(
            [
                str(ARTIST_PORTRAIT),
                "workflow",
                "--project",
                str(project),
                "--target",
                "delivery",
                "--repair-execution-record",
                str(workflow_repair_execution_candidate),
                "--json",
            ]
        )
        repair_execution_review = (
            workflow_repair_execution.get("workflow_repair_execution_review") or {}
        )
        if repair_execution_review.get("status") != "passed":
            raise SystemExit("workflow repair execution review did not pass")
        if repair_execution_review.get("accepted_action_count") != 1:
            raise SystemExit("workflow repair execution review accepted count is wrong")
        if repair_execution_review.get("commands_executed_by_cli") is not False:
            raise SystemExit("workflow repair execution review executed commands")
        if repair_execution_review.get("acceptance_success_promoted_by_cli") is not False:
            raise SystemExit("workflow repair execution review promoted acceptance success")
        workflow_repair_refresh = run_json(
            [
                str(ARTIST_PORTRAIT),
                "workflow",
                "--project",
                str(project),
                "--target",
                "delivery",
                "--repair-refresh-plan",
                "--json",
            ]
        )
        refresh_plan = workflow_repair_refresh.get("workflow_repair_refresh_plan") or {}
        if refresh_plan.get("status") != "ready":
            raise SystemExit("workflow repair refresh plan did not become ready")
        if refresh_plan.get("ready_step_count") != 1:
            raise SystemExit("workflow repair refresh plan ready count is wrong")
        if refresh_plan.get("commands_executed") is not False:
            raise SystemExit("workflow repair refresh plan executed commands")
        if refresh_plan.get("workflow_plan_mutated") is not False:
            raise SystemExit("workflow repair refresh plan mutated workflow plan")
        workflow_record_candidate.write_text(
            json.dumps(
                {
                    "execution_record_id": "real_fixture_workflow_execution",
                    "project_id": final_workflow_plan.get("project_id"),
                    "workflow_plan_id": final_workflow_plan.get("workflow_plan_id"),
                    "target": "delivery",
                    "executed_by": "run_checks",
                    "steps": [
                        {
                            "step_id": step.get("step_id"),
                            "command": step.get("command"),
                            "status": "succeeded",
                            "exit_code": 0,
                            "output_refs": step.get("expected_artifacts") or [],
                        }
                        for step in workflow_steps
                    ],
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        workflow_execution = run_json(
            [
                str(ARTIST_PORTRAIT),
                "workflow",
                "--project",
                str(project),
                "--target",
                "delivery",
                "--execution-record",
                str(workflow_record_candidate),
                "--json",
            ]
        )
        execution_review = workflow_execution.get("workflow_execution_review") or {}
        if execution_review.get("status") != "passed":
            raise SystemExit("real acceptance fixture workflow execution review did not pass")
        if execution_review.get("commands_executed_by_cli") is not False:
            raise SystemExit("workflow execution review executed commands")
        if execution_review.get("accepted_step_count") != len(workflow_steps):
            raise SystemExit("workflow execution review did not accept every workflow step")
        stages = {stage["stage_id"]: stage for stage in delivery["acceptance"]["stages"]}
        if stages["bgm"]["status"] not in {"passed", "warning"}:
            raise SystemExit("real acceptance fixture did not preserve BGM readiness")
        if stages["forbidden_capability_audit"]["status"] != "passed":
            raise SystemExit("real acceptance fixture triggered forbidden capabilities")
        release_check = run_json(
            [
                str(ARTIST_PORTRAIT),
                "release-check",
                "--project",
                str(project),
                "--json",
            ],
            expect=(0, 1),
        )
        release_report = release_check.get("release_hardening_report") or {}
        if release_report.get("status") not in {"warning", "ready_for_local_release"}:
            raise SystemExit("release hardening report blocked unexpectedly")
        if release_report.get("failed_count") != 0:
            raise SystemExit("release hardening report has failed checks")
        if release_report.get("commit_allowed") is not False:
            raise SystemExit("release hardening report allowed commits")
        if release_report.get("network_performed") is not False:
            raise SystemExit("release hardening report performed network access")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-pytest", action="store_true")
    args = parser.parse_args(argv)

    require_local_env()
    if not args.skip_pytest:
        run([str(PYTHON), "-m", "pytest"])
    run(
        [
            str(ARTIST_PORTRAIT),
            "validate",
            "--project",
            "fixtures/stage_a/valid_project.yaml",
        ]
    )
    check_schema_drift()
    check_skill_metadata()
    check_gate_consistency()
    check_progress_contract()
    check_proposal_module_architecture()
    run(
        [
            str(ARTIST_PORTRAIT),
            "scan",
            "--project",
            "fixtures/stage_a/valid_project.yaml",
        ],
        expect=7,
    )
    check_local_foundation_outputs()
    check_real_scan_if_available()
    check_real_media_acceptance_profiles_if_available()
    print("checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
