import json
from pathlib import Path

from artist_portrait_editor.schemas import write_schema_files


ROOT = Path(__file__).resolve().parents[2]


def test_checked_in_schemas_match_the_current_model_registry(tmp_path):
    write_schema_files(tmp_path)
    generated = {path.name for path in tmp_path.glob("*.schema.json")}
    checked_in = {path.name for path in (ROOT / "schemas").glob("*.schema.json")}

    assert checked_in == generated
    for name in generated:
        assert json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8")) == json.loads(
            (tmp_path / name).read_text(encoding="utf-8")
        )


def test_removed_mock_provider_schemas_are_not_distributed():
    schema_names = {path.name for path in (ROOT / "schemas").glob("*.schema.json")}

    assert not any(
        name.startswith(("proposal_provider_", "proposal_execution_", "proposal_promotion_"))
        for name in schema_names
    )
    assert "proposal_context.schema.json" in schema_names
    assert "proposal_set.schema.json" in schema_names
    assert "proposal_validation_report.schema.json" in schema_names
