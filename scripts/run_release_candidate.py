from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "bin" / "python"
if not PYTHON.exists():
    PYTHON = Path(sys.executable)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a non-publishing release readiness audit.")
    parser.add_argument("--json", action="store_true", help="Print manifest JSON.")
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow a dirty working tree for pre-publication local validation.",
    )
    parser.add_argument("--target-version", help="Audit this release version instead of the published ledger version.")
    parser.add_argument("--allow-missing-tag", action="store_true", help="Allow the target tag to be absent during the pre-commit audit.")
    parser.add_argument("--benchmark-pack", type=Path, help="Require and validate a local V2 real-video benchmark pack.")
    parser.add_argument(
        "--write-artifacts",
        action="store_true",
        help="Write .artist-portrait/data and output release-candidate reports.",
    )
    args = parser.parse_args(argv)

    manifest = build_manifest(
        allow_dirty=args.allow_dirty,
        target_version_override=args.target_version,
        allow_missing_tag=args.allow_missing_tag,
        benchmark_pack_path=args.benchmark_pack,
    )
    if args.write_artifacts:
        write_manifest(manifest)
    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        target = "output/release_candidate_report.md" if args.write_artifacts else "no artifacts written"
        print(f"release candidate {manifest['status']}: {target}")
    return 0 if manifest["status"] in {"passed", "warning"} else 1


def build_manifest(
    *, allow_dirty: bool, target_version_override: str | None = None,
    allow_missing_tag: bool = False, benchmark_pack_path: Path | None = None,
) -> dict:
    progress = json.loads((ROOT / "docs" / "current_progress.json").read_text(encoding="utf-8"))
    latest_release = progress.get("latest_release") or {}
    target_tag = "v" + target_version_override if target_version_override else str(latest_release.get("tag") or "")
    target_version = target_tag.removeprefix("v")
    expected_release_commit = str(latest_release.get("release_commit") or "") if not target_version_override else ""
    milestone = str(progress.get("milestone") or "")
    gate = str(progress.get("capability_gate") or "")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    version_match = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)
    version = version_match.group(1) if version_match else None
    current_batch = (ROOT / "docs" / "CURRENT_BATCH.md").read_text(encoding="utf-8")
    releases = (ROOT / "docs" / "RELEASES.md").read_text(encoding="utf-8")

    preflight = run_json([str(PYTHON), "scripts/skill_package_preflight.py", str(ROOT), "--json"])
    install = run_json([str(PYTHON), "scripts/simulate_skill_install.py", str(ROOT), "--json"])
    quick_validate_ok = bool(install.get("quick_validate", {}).get("returncode") == 0)
    status_lines = run_text(["git", "status", "--porcelain"]).splitlines()
    dirty = bool(status_lines)
    remote = run_text(["git", "remote", "get-url", "origin"]).strip()
    tags = set(run_text(["git", "tag", "--list"]).splitlines())
    head = run_text(["git", "rev-parse", "HEAD"]).strip()
    target_tag_exists = target_tag in tags
    target_tag_commit = (
        run_text(["git", "rev-parse", f"{target_tag}^{{}}"]).strip()
        if target_tag_exists
        else None
    )

    benchmark = validate_benchmark_pack(benchmark_pack_path) if benchmark_pack_path else None
    checks = {
        "version_matches_target_release": bool(target_version) and version == target_version,
        "target_release_tag_exists_or_is_precommit": target_tag_exists or allow_missing_tag,
        "published_release_commit_matches_ledger": (
            target_tag_commit == expected_release_commit if expected_release_commit else True
        ),
        "current_batch_records_active_gate": bool(gate) and f"Capability gate: `{gate}`" in current_batch,
        "release_ledger_records_published_and_active_state": target_tag in releases and f"Active local work: `{milestone}`" in releases,
        "preflight_ok": preflight.get("error_count") == 0,
        "install_simulation_ok": install.get("ok") is True,
        "quick_validate_ok": quick_validate_ok,
        "origin_is_video_skill": remote.endswith("zhangxiaolongne/video-skill.git"),
        "working_tree_clean_or_allowed": (not dirty) or allow_dirty,
    }
    if benchmark is not None:
        checks.update(benchmark["checks"])
    guardrails = {
        "paid_api_required": False,
        "network_required_for_local_validation": False,
        "model_call_performed_by_cli": False,
        "image_generation_or_editing_used": False,
        "media_rendered_by_release_check": False,
        "git_commit_created_by_release_check": False,
        "git_tag_created_by_release_check": False,
        "git_push_performed_by_release_check": False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    status = "failed" if failed else "warning" if dirty and allow_dirty else "passed"
    return {
        "schema_version": "1.0",
        "release_candidate_id": f"release_readiness_{target_version or 'unknown'}",
        "status": status,
        "target_version": target_version,
        "target_tag": target_tag,
        "target_tag_exists": target_tag_exists,
        "target_tag_commit": target_tag_commit,
        "expected_release_commit": expected_release_commit,
        "head": head,
        "remote": remote,
        "dirty": dirty,
        "dirty_entry_count": len(status_lines),
        "dirty_entries": status_lines[:200],
        "checks": checks,
        "failed_checks": failed,
        "preflight": {
            "error_count": preflight.get("error_count"),
            "warning_count": preflight.get("warning_count"),
            "issues": preflight.get("issues", []),
        },
        "install_simulation": {
            "ok": install.get("ok"),
            "canonical_dir": install.get("canonical_dir"),
            "quick_validate_returncode": install.get("quick_validate", {}).get("returncode"),
            "preflight_errors": (install.get("package_preflight") or {}).get("error_count"),
            "preflight_warnings": (install.get("package_preflight") or {}).get("warning_count"),
        },
        "guardrails": guardrails,
        "benchmark_pack": benchmark,
    }


def validate_benchmark_pack(path: Path) -> dict:
    resolved = path.expanduser().resolve()
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    required = {"stage_person", "interview_talking_head", "event_promo_mix"}
    benchmarks = payload.get("benchmarks") or []
    classes = {item.get("benchmark_class") for item in benchmarks}
    closed = [item for item in benchmarks if item.get("acceptance_status") == "closed_loop"]
    media_results = []
    for item in closed:
        project_path = Path(str(item.get("project_ref") or ""))
        root = project_path.parent
        artifact_path = root / ".artist-portrait" / "data" / "second_cut_render.json"
        valid = False
        if artifact_path.exists():
            artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
            media_path = root / str(artifact.get("output_ref") or "")
            expected_hash = artifact.get("output_hash")
            actual_hash = "sha256:" + hashlib.sha256(media_path.read_bytes()).hexdigest() if media_path.is_file() else None
            valid = bool(artifact.get("media_valid") and expected_hash == actual_hash)
        media_results.append({"benchmark_class": item.get("benchmark_class"), "valid_current_media": valid})
    checks = {
        "v2_benchmark_three_class_coverage": classes == required and payload.get("class_coverage_complete") is True,
        "v2_benchmark_has_closed_loop": len(closed) >= 1,
        "v2_benchmark_closed_loop_media_current": bool(media_results) and all(item["valid_current_media"] for item in media_results),
        "v2_benchmark_synthetic_not_counted": payload.get("synthetic_fixture_counted_as_real") is False,
        "v2_benchmark_media_not_distributable": payload.get("distributable_media_included") is False,
        "v2_benchmark_cli_offline": payload.get("network_performed_by_cli") is False,
        "v2_benchmark_incomplete_state_visible": payload.get("status") in {"degraded", "ready"} and int(payload.get("input_baseline_count") or 0) >= 1,
    }
    return {
        "path": str(resolved), "pack_id": payload.get("pack_id"),
        "status": payload.get("status"), "closed_loop_count": len(closed),
        "input_baseline_count": payload.get("input_baseline_count"),
        "media_results": media_results, "checks": checks,
    }


def run_json(command: list[str]) -> dict:
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if completed.returncode != 0:
        raise SystemExit(
            f"command failed: {' '.join(command)}\nstdout={completed.stdout}\nstderr={completed.stderr}"
        )
    return json.loads(completed.stdout)


def run_text(command: list[str]) -> str:
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if completed.returncode != 0:
        raise SystemExit(
            f"command failed: {' '.join(command)}\nstdout={completed.stdout}\nstderr={completed.stderr}"
        )
    return completed.stdout


def write_manifest(manifest: dict) -> None:
    output = ROOT / "output"
    data = ROOT / ".artist-portrait" / "data"
    output.mkdir(exist_ok=True)
    data.mkdir(parents=True, exist_ok=True)
    (data / "release_candidate.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Release Candidate Report",
        "",
        f"- Status: `{manifest['status']}`",
        f"- Target version: `{manifest['target_version']}`",
        f"- Target tag: `{manifest['target_tag']}`",
        f"- Expected release commit: `{manifest['expected_release_commit']}`",
        f"- Dirty entries: `{manifest['dirty_entry_count']}`",
        "",
        "## Checks",
        "",
    ]
    for key, value in manifest["checks"].items():
        lines.append(f"- `{key}`: `{value}`")
    if manifest["failed_checks"]:
        lines.extend(["", "## Failed Checks", ""])
        lines.extend(f"- `{item}`" for item in manifest["failed_checks"])
    lines.extend(["", "## Guardrails", ""])
    for key, value in manifest["guardrails"].items():
        lines.append(f"- `{key}`: `{value}`")
    (output / "release_candidate_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
