import json
import math
import shutil
import wave
from pathlib import Path

import pytest

from artist_portrait_editor.cli import main
from artist_portrait_editor.media.scanner import read_sources_jsonl


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "stage_a"


def write_project(tmp_path: Path) -> Path:
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return project_path


def write_sine_wav(path: Path, *, seconds: float = 0.25, sample_rate: int = 8000) -> None:
    frames = int(seconds * sample_rate)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        for index in range(frames):
            sample = int(12000 * math.sin(2 * math.pi * 440 * index / sample_rate))
            handle.writeframesraw(sample.to_bytes(2, byteorder="little", signed=True))


@pytest.mark.skipif(
    shutil.which("ffprobe") is None or shutil.which("ffmpeg") is None,
    reason="real scan requires ffprobe and ffmpeg",
)
def test_real_scan_writes_valid_source_jsonl_for_generated_wav(tmp_path, capsys):
    project_path = write_project(tmp_path)
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    write_sine_wav(media_dir / "tone.wav")

    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    code = main(["scan", "--project", str(project_path), "--json"])
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["sources"] == 1

    sources_path = tmp_path / ".artist-portrait" / "data" / "sources.jsonl"
    records = read_sources_jsonl(sources_path)
    assert len(records) == 1
    record = records[0]
    assert record.locations == ["media/tone.wav"]
    assert record.media_kind == "audio"
    assert record.media_probe.audio_present is True
    assert record.media_probe.width is None
    assert record.media_probe.height is None
    assert record.media_probe.video_codec is None
    assert record.media_probe.duration > 0
