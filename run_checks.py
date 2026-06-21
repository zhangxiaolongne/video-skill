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
        for name in (
            "project_config.schema.json",
            "project_state.schema.json",
            "source_record.schema.json",
        ):
            committed = ROOT / "schemas" / name
            generated = tmp_path / name
            if committed.read_text(encoding="utf-8") != generated.read_text(encoding="utf-8"):
                raise SystemExit(f"schema drift detected: {name}")


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
        run([str(ARTIST_PORTRAIT), "init", "--project", str(project), "--quiet"])
        run([str(ARTIST_PORTRAIT), "scan", "--project", str(project), "--json"])
        sources = tmp_path / ".artist-portrait" / "data" / "sources.jsonl"
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
    check_real_scan_if_available()
    print("checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
