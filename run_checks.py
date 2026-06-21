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
            "clip_record.schema.json",
            "project_config.schema.json",
            "project_state.schema.json",
            "source_record.schema.json",
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
        "V0_004_SEGMENTATION_FOUNDATION.md": ROOT
        / "docs"
        / "V0_004_SEGMENTATION_FOUNDATION.md",
    }
    content = {name: path.read_text(encoding="utf-8") for name, path in docs.items()}
    if (
        "Current gate: V0-004 fixed-window segmentation foundation only."
        not in content["AGENTS.md"]
    ):
        raise SystemExit("AGENTS.md current gate is not V0-004 segmentation foundation")
    if "V0-004 固定窗口切分基础" not in content["master"]:
        raise SystemExit("master document current gate is not V0-004 segmentation foundation")
    if "Current V0-004 fixed-window segmentation foundation work" not in content["README.md"]:
        raise SystemExit("README current gate is not V0-004 segmentation foundation")
    if (
        "Current local gate: V0-004 fixed-window segmentation foundation only"
        not in content["DEVELOPMENT_PROGRESS.md"]
    ):
        raise SystemExit("development progress current gate is stale")
    if (
        "V0-004 opens deterministic fixed-window segmentation only"
        not in content["V0_004_SEGMENTATION_FOUNDATION.md"]
    ):
        raise SystemExit("V0-004 segmentation foundation doc is missing active gate")


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
        project.write_text(
            (ROOT / "fixtures" / "stage_a" / "valid_project.yaml").read_text(
                encoding="utf-8"
            ),
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

        run([str(ARTIST_PORTRAIT), "map", "--project", str(project), "--quiet"])
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
            "map",
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
        if {"segment_invalidated", "map_invalidated", "review_project_invalidated"} - issue_codes:
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


def check_local_foundation_outputs() -> None:
    with tempfile.TemporaryDirectory(prefix="artist-portrait-foundation-") as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "media").mkdir()
        project = tmp_path / "project.yaml"
        project.write_text(
            (ROOT / "fixtures" / "stage_a" / "valid_project.yaml").read_text(
                encoding="utf-8"
            ),
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

        run([str(ARTIST_PORTRAIT), "map", "--project", str(project), "--quiet"])
        material_map = (tmp_path / "output" / "material_map.md").read_text(
            encoding="utf-8"
        )
        if "# Material Map" not in material_map or "No transcription" not in material_map:
            raise SystemExit("material_map content check failed")

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
