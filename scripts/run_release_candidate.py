from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET_VERSION = "0.28.0"
TARGET_TAG = f"v{TARGET_VERSION}"
PREVIOUS_TAG = "v0.27.0"
PYTHON = ROOT / ".venv" / "bin" / "python"
if not PYTHON.exists():
    PYTHON = Path(sys.executable)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Stage 6 release-candidate readiness audit.")
    parser.add_argument("--json", action="store_true", help="Print manifest JSON.")
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow a dirty working tree for pre-publication local validation.",
    )
    parser.add_argument(
        "--write-artifacts",
        action="store_true",
        help="Write .artist-portrait/data and output release-candidate reports.",
    )
    args = parser.parse_args(argv)

    manifest = build_manifest(allow_dirty=args.allow_dirty)
    if args.write_artifacts:
        write_manifest(manifest)
    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        target = "output/release_candidate_report.md" if args.write_artifacts else "no artifacts written"
        print(f"release candidate {manifest['status']}: {target}")
    return 0 if manifest["status"] in {"passed", "warning"} else 1


def build_manifest(*, allow_dirty: bool) -> dict:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    version_match = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)
    version = version_match.group(1) if version_match else None
    progress = json.loads((ROOT / "docs" / "current_progress.json").read_text(encoding="utf-8"))
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
    previous_tag_exists = PREVIOUS_TAG in tags
    target_tag_exists = TARGET_TAG in tags
    target_tag_commit = (
        run_text(["git", "rev-parse", f"{TARGET_TAG}^{{}}"]).strip()
        if target_tag_exists
        else None
    )
    release_commit_subject = f"Release artist portrait editor {TARGET_TAG}"

    checks = {
        "version_matches_target": version == TARGET_VERSION,
        "active_stage_is_stage_06": progress.get("active_batch", {}).get("id") == "ACCEPTANCE-STAGE-06",
        "final_acceptance_complete": all(
            stage.get("status") == "completed"
            for stage in progress.get("final_acceptance", {}).get("stages", [])
        ),
        "current_batch_completed": "Batch ID: `ACCEPTANCE-STAGE-06`" in current_batch
        and "Status: `completed`" in current_batch,
        "release_ledger_targets_current_version": TARGET_TAG in releases,
        "preflight_ok": preflight.get("error_count") == 0,
        "install_simulation_ok": install.get("ok") is True,
        "quick_validate_ok": quick_validate_ok,
        "previous_tag_exists": previous_tag_exists,
        "target_tag_state_valid": (not target_tag_exists) or bool(target_tag_commit),
        "origin_is_video_skill": remote.endswith("zhangxiaolongne/video-skill.git"),
        "working_tree_clean_or_allowed": (not dirty) or allow_dirty,
    }
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
        "release_candidate_id": "release_candidate_stage_06",
        "status": status,
        "target_version": TARGET_VERSION,
        "target_tag": TARGET_TAG,
        "target_tag_exists": target_tag_exists,
        "target_tag_commit": target_tag_commit,
        "previous_tag": PREVIOUS_TAG,
        "head": head,
        "release_commit_subject": release_commit_subject,
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
        f"- Previous tag: `{manifest['previous_tag']}`",
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
