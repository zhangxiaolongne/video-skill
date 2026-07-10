#!/usr/bin/env python3
"""Run the compact validation surface for the artist portrait editor skill."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent
PYTHON = ROOT / ".venv" / "bin" / "python"
if not PYTHON.exists():
    PYTHON = Path(sys.executable)

SKILL_VALIDATE = (
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
RELEASE_READINESS = ROOT / "scripts" / "run_release_candidate.py"


def run(command: list[str], *, allowed: tuple[int, ...] = (0,)) -> str:
    print("$ " + " ".join(command))
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.returncode not in allowed:
        raise SystemExit(
            f"command exited {completed.returncode}, expected {allowed}: {' '.join(command)}\n"
            f"{completed.stderr}"
        )
    return completed.stdout


def run_json(command: list[str], *, allowed: tuple[int, ...] = (0,)) -> dict:
    output = run(command, allowed=allowed)
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"expected JSON output from {' '.join(command)}: {exc}") from exc


def validate_data_files() -> None:
    json_paths = [ROOT / "docs" / "current_progress.json"]
    json_paths.extend(sorted((ROOT / "schemas").glob("*.json")))
    json_paths.extend(sorted((ROOT / "fixtures").rglob("*.json")))
    yaml_paths = sorted((ROOT / "fixtures").rglob("*.yaml"))
    yaml_paths.extend(sorted((ROOT / "fixtures").rglob("*.yml")))

    for path in json_paths:
        json.loads(path.read_text(encoding="utf-8"))
    for path in yaml_paths:
        yaml.safe_load(path.read_text(encoding="utf-8"))


def validate_package() -> None:
    run([str(PYTHON), str(SKILL_VALIDATE), str(ROOT)])
    preflight = run_json([str(PYTHON), str(PACKAGE_PREFLIGHT), str(ROOT), "--json"])
    if preflight.get("error_count") != 0:
        raise SystemExit("skill package preflight reported errors")
    install = run_json([str(PYTHON), str(SIMULATE_INSTALL), str(ROOT), "--json"])
    if install.get("ok") is not True:
        raise SystemExit("canonical skill install simulation failed")


def validate_release_readiness() -> None:
    payload = run_json([str(PYTHON), str(RELEASE_READINESS), "--allow-dirty", "--json"])
    if payload.get("status") not in {"passed", "warning"}:
        raise SystemExit("release readiness audit failed")
    if any(value is not False for value in (payload.get("guardrails") or {}).values()):
        raise SystemExit("release readiness audit reported a forbidden side effect")


def clean_test_caches() -> None:
    shutil.rmtree(ROOT / ".pytest_cache", ignore_errors=True)
    for path in ROOT.rglob("__pycache__"):
        if ".venv" not in path.parts:
            shutil.rmtree(path, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-pytest",
        action="store_true",
        help="Skip the pytest behavior suite; keep package, syntax, data, and readiness checks.",
    )
    args = parser.parse_args(argv)

    try:
        with tempfile.TemporaryDirectory(prefix="artist-portrait-schemas-") as temp_dir:
            run(
                [
                    str(PYTHON),
                    "-m",
                    "artist_portrait_editor.cli",
                    "validate",
                    "--project",
                    "fixtures/stage_a/valid_project.yaml",
                ]
            )
            run(
                [
                    str(PYTHON),
                    "-m",
                    "artist_portrait_editor.cli",
                    "generate-schema",
                    "--output-dir",
                    temp_dir,
                ]
            )
        run([str(PYTHON), "-m", "compileall", "-q", "src", "scripts", "tests"])
        validate_data_files()
        validate_package()
        if not args.skip_pytest:
            run([str(PYTHON), "-m", "pytest"])
        validate_release_readiness()
        run(["git", "diff", "--check"])
    finally:
        clean_test_caches()

    print("checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
