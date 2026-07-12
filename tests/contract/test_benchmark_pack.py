import pytest

from artist_portrait_editor.benchmark_pack import BenchmarkPackError, REQUIRED_CLASSES, _parse_bindings
from artist_portrait_editor.models.benchmark_pack import RealVideoBenchmarkPack


def test_benchmark_pack_requires_three_distinct_real_classes(tmp_path) -> None:
    bindings = [f"{kind}={tmp_path / kind / 'project.yaml'}" for kind in REQUIRED_CLASSES]
    parsed = _parse_bindings(bindings)

    assert set(parsed) == set(REQUIRED_CLASSES)
    assert all(path.is_absolute() for path in parsed.values())


def test_benchmark_pack_rejects_missing_or_duplicate_classes(tmp_path) -> None:
    with pytest.raises(BenchmarkPackError, match="missing required benchmark classes"):
        _parse_bindings([f"stage_person={tmp_path / 'project.yaml'}"])
    with pytest.raises(BenchmarkPackError, match="duplicate benchmark class"):
        _parse_bindings([
            f"stage_person={tmp_path / 'one.yaml'}",
            f"stage_person={tmp_path / 'two.yaml'}",
            f"interview_talking_head={tmp_path / 'three.yaml'}",
            f"event_promo_mix={tmp_path / 'four.yaml'}",
        ])


def test_benchmark_pack_schema_forbids_synthetic_real_evidence() -> None:
    schema = RealVideoBenchmarkPack.model_json_schema()
    properties = schema["properties"]

    assert properties["synthetic_fixture_counted_as_real"]["default"] is False
    assert properties["distributable_media_included"]["default"] is False
    assert properties["network_performed_by_cli"]["default"] is False
