from __future__ import annotations

import argparse
import json
import math
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
            "analysis_record.schema.json",
            "clip_record.schema.json",
            "project_config.schema.json",
            "project_state.schema.json",
            "proposal_adapter_check.schema.json",
            "proposal_execution_approval_request.schema.json",
            "proposal_execution_authorization.schema.json",
            "proposal_mock_adapter_handshake.schema.json",
            "proposal_context.schema.json",
            "proposal_provider_registry.schema.json",
            "proposal_provider_output_quarantine.schema.json",
            "proposal_provider_result_envelope.schema.json",
            "proposal_request_packet.schema.json",
            "proposal_validation_report.schema.json",
            "proposal_set.schema.json",
            "source_record.schema.json",
            "keyframe_record.schema.json",
            "transcript_record.schema.json",
            "text_model_gate.schema.json",
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
        "V0_010K_PROPOSAL_EXECUTION_APPROVAL_REQUEST_GATE.md": ROOT
        / "docs"
        / "V0_010K_PROPOSAL_EXECUTION_APPROVAL_REQUEST_GATE.md",
    }
    content = {name: path.read_text(encoding="utf-8") for name, path in docs.items()}
    if (
        "Current gate: V0-010k proposal execution approval request gate only."
        not in content["AGENTS.md"]
    ):
        raise SystemExit("AGENTS.md current gate is not V0-010k approval request")
    if "V0-010k 提案 execution approval request 闸门" not in content["master"]:
        raise SystemExit("master document current gate is not V0-010k approval request")
    if "Current V0-010k proposal execution approval request gate work" not in content["README.md"]:
        raise SystemExit("README current gate is not V0-010k approval request")
    if (
        "Current local gate: V0-010k proposal execution approval request gate only"
        not in content["DEVELOPMENT_PROGRESS.md"]
    ):
        raise SystemExit("development progress current gate is stale")
    if (
        "V0-010k opens deterministic provider execution approval request packets"
        not in content["V0_010K_PROPOSAL_EXECUTION_APPROVAL_REQUEST_GATE.md"]
    ):
        raise SystemExit("V0-010k approval request gate doc is missing active gate")


def write_sine_wav(path: Path, *, seconds: float = 0.25, sample_rate: int = 8000) -> None:
    frames = int(seconds * sample_rate)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        for index in range(frames):
            sample = int(12000 * math.sin(2 * math.pi * 440 * index / sample_rate))
            handle.writeframesraw(sample.to_bytes(2, byteorder="little", signed=True))


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
            expect=1,
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
            expect=4,
        )
        context = tmp_path / ".artist-portrait" / "data" / "proposal_context.json"
        gate = tmp_path / ".artist-portrait" / "data" / "text_model_gate.json"
        if not context.exists():
            raise SystemExit("blocked propose did not write proposal_context.json")
        if not gate.exists():
            raise SystemExit("blocked propose did not write text_model_gate.json")
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
                "story_structure": ["open with verified evidence"],
                "sound_structure": ["BGM strategy: low-interference music under speech"],
                "visual_motifs": ["manual confirmation required"],
                "risks": ["visual semantics not inferred"],
                "minimum_viable_timeline": ["timeline generation is not open"],
                "missing_material": [],
                "counter_proposal": None,
            }
        )
    payload = {
        "proposal_set_id": "proposal_set_run_checks",
        "project_id": context["project_id"],
        "map_fingerprint": context["material_map_fingerprint"],
        "method": "run_checks_fixture",
        "method_version": "v0-010d",
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
        if propose.returncode != 4:
            raise SystemExit(f"propose did not block without text model: {propose.stdout}")
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
        if ".artist-portrait/data/proposal_adapter_check.json" not in output_refs:
            raise SystemExit("propose did not report proposal_adapter_check output ref")
        if ".artist-portrait/data/proposal_provider_registry.json" not in output_refs:
            raise SystemExit("propose did not report proposal_provider_registry output ref")
        if ".artist-portrait/data/proposal_mock_adapter_handshake.json" not in output_refs:
            raise SystemExit("propose did not report proposal_mock_adapter_handshake output ref")
        if ".artist-portrait/data/proposal_execution_approval_request.json" not in output_refs:
            raise SystemExit("propose did not report proposal_execution_approval_request output ref")
        if ".artist-portrait/data/proposal_execution_authorization.json" not in output_refs:
            raise SystemExit("propose did not report proposal_execution_authorization output ref")
        if ".artist-portrait/data/proposal_provider_output_quarantine.json" not in output_refs:
            raise SystemExit("propose did not report proposal_provider_output_quarantine output ref")
        if ".artist-portrait/data/proposal_provider_result.json" not in output_refs:
            raise SystemExit("propose did not report proposal_provider_result output ref")
        if "no fake proposals" not in propose_payload.get("error", ""):
            raise SystemExit("propose did not explain fake proposals were not generated")
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
        authorization = (
            tmp_path / ".artist-portrait" / "data" / "proposal_execution_authorization.json"
        )
        quarantine = (
            tmp_path
            / ".artist-portrait"
            / "data"
            / "proposal_provider_output_quarantine.json"
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
        if not authorization.exists():
            raise SystemExit("blocked propose did not write proposal_execution_authorization.json")
        if not quarantine.exists():
            raise SystemExit("blocked propose did not write proposal_provider_output_quarantine.json")
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
        authorization_payload = json.loads(authorization.read_text(encoding="utf-8"))
        if authorization_payload.get("approved_execution_gate") is not False:
            raise SystemExit("proposal_execution_authorization opened execution gate")
        if authorization_payload.get("user_approval_present") is not False:
            raise SystemExit("proposal_execution_authorization recorded user approval unexpectedly")
        if authorization_payload.get("model_call_allowed") is not False:
            raise SystemExit("proposal_execution_authorization allowed model calls unexpectedly")
        if authorization_payload.get("execution_performed") is not False:
            raise SystemExit("proposal_execution_authorization performed execution unexpectedly")
        quarantine_payload = json.loads(quarantine.read_text(encoding="utf-8"))
        if quarantine_payload.get("raw_output_captured") is not False:
            raise SystemExit("proposal_provider_output_quarantine captured raw output unexpectedly")
        if quarantine_payload.get("parsed_payload_generated") is not False:
            raise SystemExit("proposal_provider_output_quarantine generated parsed payload")
        if quarantine_payload.get("promoted_to_proposals") is not False:
            raise SystemExit("proposal_provider_output_quarantine promoted output to proposals")
        if quarantine_payload.get("validation_performed") is not False:
            raise SystemExit("proposal_provider_output_quarantine performed validation unexpectedly")
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
    print("checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
