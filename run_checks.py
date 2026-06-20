from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PYTHON = ROOT / ".venv" / "bin" / "python"
ARTIST_PORTRAIT = ROOT / ".venv" / "bin" / "artist-portrait"


def run(command: list[str], *, expect: int = 0) -> None:
    print("$", " ".join(command), flush=True)
    completed = subprocess.run(command, cwd=ROOT)
    if completed.returncode != expect:
        raise SystemExit(
            f"command exited {completed.returncode}, expected {expect}: {' '.join(command)}"
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
        for name in ("project_config.schema.json", "project_state.schema.json"):
            committed = ROOT / "schemas" / name
            generated = tmp_path / name
            if committed.read_text(encoding="utf-8") != generated.read_text(encoding="utf-8"):
                raise SystemExit(f"schema drift detected: {name}")


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
    run(
        [
            str(ARTIST_PORTRAIT),
            "scan",
            "--project",
            "fixtures/stage_a/valid_project.yaml",
        ],
        expect=7,
    )
    print("checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
