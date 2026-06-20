import json
from pathlib import Path

from artist_portrait_editor.exit_codes import ExitCode


def test_exit_codes_match_spec_fixture():
    expected_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "stage_a"
        / "expected"
        / "exit_codes.json"
    )
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    assert {code.name: int(code) for code in ExitCode} == expected
