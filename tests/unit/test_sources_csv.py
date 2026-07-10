from pathlib import Path

from artist_portrait_editor.media.sources_csv import load_sources_csv
from artist_portrait_editor.models.source import RightsStatus, SourceType


def test_load_sources_csv_annotations(tmp_path):
    (tmp_path / "sources.csv").write_text(
        "location,source_type,work,role,rights_status,forbidden_by_user,notes\n"
        "media/a.mp4,interview,Work A,Role A,licensed,true,Important\n",
        encoding="utf-8",
    )

    result = load_sources_csv(tmp_path)

    assert result.warnings == []
    annotation = result.annotations["media/a.mp4"]
    assert annotation.source_type == SourceType.interview
    assert annotation.work == "Work A"
    assert annotation.role == "Role A"
    assert annotation.rights_status == RightsStatus.licensed
    assert annotation.forbidden_by_user is True
    assert annotation.notes == "Important"


def test_load_sources_csv_accepts_path_alias_and_relative_prefix(tmp_path):
    (tmp_path / "sources.csv").write_text(
        "path,source_type,rights_status,forbidden_by_user\n"
        "./media/a.mp4,stage_performance,owned,false\n",
        encoding="utf-8",
    )

    result = load_sources_csv(tmp_path)

    assert result.warnings == []
    assert "media/a.mp4" in result.annotations
    assert result.annotations["media/a.mp4"].source_type == SourceType.stage_performance


def test_load_sources_csv_invalid_values_become_warnings(tmp_path):
    (tmp_path / "sources.csv").write_text(
        "location,source_type,rights_status,forbidden_by_user\n"
        "media/a.mp4,bad_type,bad_rights,maybe\n",
        encoding="utf-8",
    )

    result = load_sources_csv(tmp_path)

    assert len(result.warnings) == 3
    annotation = result.annotations["media/a.mp4"]
    assert annotation.source_type is None
    assert annotation.rights_status is None
    assert annotation.forbidden_by_user is None


def test_load_sources_csv_rejects_unsafe_locations(tmp_path):
    (tmp_path / "sources.csv").write_text(
        "location,source_type\n"
        "../outside.mp4,interview\n"
        "/absolute.mp4,interview\n",
        encoding="utf-8",
    )

    result = load_sources_csv(tmp_path)

    assert result.annotations == {}
    assert len(result.warnings) == 2


def test_load_sources_csv_rejects_backslash_traversal(tmp_path):
    (tmp_path / "sources.csv").write_text(
        "location,source_type\n"
        "..\\outside.mp4,interview\n",
        encoding="utf-8",
    )

    result = load_sources_csv(tmp_path)

    assert result.annotations == {}
    assert result.warnings == ["sources.csv:2: location must be project-relative"]
