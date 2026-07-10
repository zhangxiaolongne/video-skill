#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
QUICK_VALIDATE = (
    Path.home()
    / ".codex"
    / "skills"
    / ".system"
    / "skill-creator"
    / "scripts"
    / "quick_validate.py"
)
EXCLUDED_NAMES = {
    ".artist-portrait",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "output",
    "runs",
    "__pycache__",
}
EXCLUDED_SUFFIXES = {
    ".pyc",
    ".tmp",
}


def should_ignore(_directory: str, names: list[str]) -> set[str]:
    ignored = set()
    for name in names:
        if name in EXCLUDED_NAMES:
            ignored.add(name)
            continue
        if name.endswith(tuple(EXCLUDED_SUFFIXES)):
            ignored.add(name)
    return ignored


def run_json(command: list[str], *, cwd: Path) -> tuple[int, dict[str, Any] | None, str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    payload = None
    if completed.stdout.strip():
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            payload = None
    return completed.returncode, payload, completed.stdout + completed.stderr


def simulate_install(source_root: Path, work_dir: Path | None = None) -> dict[str, Any]:
    source_root = source_root.resolve()
    policy = json.loads((source_root / "skill-package.json").read_text(encoding="utf-8"))
    canonical_dir = policy["canonical_install_dir"]
    declared_exclusions = set(policy.get("excluded_distribution_paths") or [])
    if not declared_exclusions.issubset(EXCLUDED_NAMES):
        unknown = ", ".join(sorted(declared_exclusions - EXCLUDED_NAMES))
        raise ValueError(f"distribution exclusions are not enforced by installer: {unknown}")

    if work_dir is None:
        temp_context = tempfile.TemporaryDirectory(prefix="artist-portrait-install-")
        install_parent = Path(temp_context.name)
    else:
        temp_context = None
        install_parent = work_dir.resolve()
        install_parent.mkdir(parents=True, exist_ok=True)

    try:
        install_dir = install_parent / canonical_dir
        if install_dir.exists():
            shutil.rmtree(install_dir)
        shutil.copytree(source_root, install_dir, ignore=should_ignore)

        quick = subprocess.run(
            [sys.executable, str(QUICK_VALIDATE), str(install_dir)],
            capture_output=True,
            text=True,
        )
        preflight_code, preflight, preflight_output = run_json(
            [
                sys.executable,
                str(install_dir / "scripts" / "skill_package_preflight.py"),
                str(install_dir),
                "--json",
            ],
            cwd=install_dir,
        )
        excluded_paths_verified = {
            name: not (install_dir / name).exists()
            for name in sorted(declared_exclusions)
        }
        payload = {
            "source_root": str(source_root),
            "install_dir": str(install_dir),
            "canonical_dir": canonical_dir,
            "excluded_paths_verified": excluded_paths_verified,
            "quick_validate": {
                "returncode": quick.returncode,
                "output": quick.stdout + quick.stderr,
            },
            "package_preflight": preflight,
            "package_preflight_returncode": preflight_code,
            "ok": (
                quick.returncode == 0
                and preflight_code == 0
                and bool(preflight)
                and preflight.get("error_count") == 0
                and preflight.get("warning_count") == 0
                and all(excluded_paths_verified.values())
            ),
        }
        if preflight is None:
            payload["package_preflight_output"] = preflight_output
        return payload
    finally:
        if temp_context is not None:
            temp_context.cleanup()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_dir", nargs="?", default=str(ROOT))
    parser.add_argument("--work-dir")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    payload = simulate_install(
        Path(args.skill_dir),
        Path(args.work_dir) if args.work_dir else None,
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"install_dir: {payload['install_dir']}")
        print(f"quick_validate: {payload['quick_validate']['returncode']}")
        preflight = payload.get("package_preflight") or {}
        print(f"preflight_errors: {preflight.get('error_count')}")
        print(f"preflight_warnings: {preflight.get('warning_count')}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
