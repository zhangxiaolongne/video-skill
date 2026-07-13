from pathlib import Path
from types import SimpleNamespace

import pytest

from artist_portrait_editor.creative_memory import (
    CreativeMemoryError,
    _conflicts,
    _deduplicate,
    _explicit_entries,
    _revision_entries,
    _selected_style_entries,
    build_creative_memory_workspace,
)
from artist_portrait_editor.workspace_state import init_workspace


def _project(tmp_path: Path, project_id: str) -> Path:
    root = tmp_path / project_id
    root.mkdir()
    project_path = root / "project.yaml"
    project_path.write_text(
        f'''schema_version: "0.3"
project:
  id: {project_id}
  title: Memory Test
  artist_name: Explicit Test Subject
  language: en
creative_brief:
  theme: Evidence-bound portrait
  audience: Reviewers
  platform: douyin
  target_duration_seconds: 60
  aspect_ratio: "9:16"
  tone: [restrained, human]
content_policy:
  allow_role_dialogue: true
  allow_real_person_role_mix: true
  allow_unconfirmed_visual_material: false
  allow_interview_audio: true
  allow_music: false
  allow_restricted_rights: true
features:
  transcription: off
  scene_detection: off
  visual_analysis: off
  experimental_relations: false
data_policy:
  allow_remote_text_model: false
  allow_remote_vision_model: false
  include_absolute_paths_in_remote_requests: false
paths:
  media_dir: ./media
  annotations_dir: ./annotations
  output_dir: ./output
''',
        encoding="utf-8",
    )
    init_workspace(project_path)
    return project_path


def test_project_memory_combines_config_preferences_constraints_and_forbids(tmp_path):
    project_path = _project(tmp_path, "memory_project")

    json_path, md_path, memory, warnings = build_creative_memory_workspace(
        project_path,
        scope="project",
        preferences=["cover=clean portrait close-up"],
        constraints=["audio=protect intelligible speech"],
        forbids=["shot=unflattering frozen frame"],
    )

    assert json_path.exists() and md_path.exists()
    assert memory.identity.identity_id == "memory_project"
    assert any(entry.category == "duration" and entry.strength == "hard" for entry in memory.entries)
    assert any(entry.category == "bgm" and entry.polarity == "forbid" for entry in memory.entries)
    assert any(entry.category == "cover" and entry.status == "confirmed" for entry in memory.entries)
    assert any(entry.category == "shot" and entry.polarity == "forbid" for entry in memory.entries)
    assert memory.memory_applied_to_edit is False
    assert memory.timeline_mutated is False
    assert memory.media_rendered is False
    assert warnings == []


def test_subject_memory_requires_explicit_identity_and_never_uses_artist_name(tmp_path):
    project_path = _project(tmp_path, "subject_project")

    with pytest.raises(CreativeMemoryError, match="explicit --subject-id"):
        build_creative_memory_workspace(
            project_path, scope="subject", preferences=["style=restrained"]
        )

    _, _, memory, _ = build_creative_memory_workspace(
        project_path,
        scope="subject",
        subject_id="subject-001",
        subject_name="Explicit Name",
        aliases=["Alias B", "Alias A", "Alias A"],
        preferences=["style=restrained"],
    )
    assert memory.identity.display_name == "Explicit Name"
    assert memory.identity.aliases == ["Alias A", "Alias B"]
    assert all(entry.applicability == "subject_reusable" for entry in memory.entries)


def test_same_identity_preserves_prior_explicit_entries_and_identity_switch_is_blocked(tmp_path):
    project_path = _project(tmp_path, "persistent_project")
    build_creative_memory_workspace(
        project_path,
        scope="subject",
        subject_id="subject-001",
        subject_name="Explicit Name",
        preferences=["cover=clean close-up"],
    )

    _, _, updated, _ = build_creative_memory_workspace(
        project_path,
        scope="subject",
        subject_id="subject-001",
        subject_name="Updated Explicit Name",
        aliases=["Current Alias"],
        constraints=["audio=protect speech"],
    )
    assert any(entry.statement == "clean close-up" for entry in updated.entries)
    assert any(entry.statement == "protect speech" for entry in updated.entries)
    assert updated.identity.display_name == "Updated Explicit Name"
    assert updated.identity.aliases == ["Current Alias", "Explicit Name"]

    with pytest.raises(CreativeMemoryError, match="existing canonical memory identity differs"):
        build_creative_memory_workspace(
            project_path,
            scope="subject",
            subject_id="subject-002",
            subject_name="Different Subject",
            preferences=["style=neutral"],
        )

    _, _, replaced, _ = build_creative_memory_workspace(
        project_path,
        scope="subject",
        subject_id="subject-002",
        subject_name="Different Subject",
        preferences=["style=neutral"],
        replace_existing=True,
    )
    assert replaced.identity.identity_id == "subject-002"
    assert not any(entry.statement == "clean close-up" for entry in replaced.entries)


def test_project_config_snapshot_refreshes_without_losing_explicit_memory(tmp_path):
    project_path = _project(tmp_path, "refresh_project")
    build_creative_memory_workspace(
        project_path,
        scope="project",
        preferences=["cover=clean close-up"],
    )
    project_path.write_text(
        project_path.read_text(encoding="utf-8").replace(
            "tone: [restrained, human]", "tone: [energetic]"
        ),
        encoding="utf-8",
    )

    _, _, refreshed, _ = build_creative_memory_workspace(
        project_path, scope="project"
    )

    style_statements = {
        entry.statement for entry in refreshed.entries if entry.category == "style"
    }
    assert style_statements == {"energetic"}
    explicit = next(entry for entry in refreshed.entries if entry.statement == "clean close-up")
    assert explicit.provenance[0].source_type == "user_explicit"
    assert explicit.provenance[0].source_fingerprint != next(
        entry for entry in refreshed.entries if entry.category == "theme"
    ).provenance[0].source_fingerprint


def test_subject_memory_reuses_only_exact_matching_identity(tmp_path):
    source_project = _project(tmp_path, "source_project")
    target_project = _project(tmp_path, "target_project")
    source_path, _, source_memory, _ = build_creative_memory_workspace(
        source_project,
        scope="subject",
        subject_id="subject-001",
        subject_name="Explicit Name",
        preferences=["bgm=sparse instrumental"],
        forbids=["shot=eyes closed accidental frame"],
    )

    _, _, imported, _ = build_creative_memory_workspace(
        target_project,
        scope="subject",
        subject_id="subject-001",
        subject_name="Explicit Name",
        source_memory_path=source_path,
    )
    assert imported.source_project_ids == ["source_project", "target_project"]
    assert imported.entry_count == source_memory.entry_count
    assert all(
        any(item.source_type == "imported_memory" for item in entry.provenance)
        for entry in imported.entries
    )
    source_binding = next(
        binding for binding in imported.evidence_bindings
        if binding.label == "source_memory"
    )
    assert source_binding.ref == "creative_memory.json"
    assert source_binding.used_for_memory is True
    assert not source_binding.ref.startswith("/")

    with pytest.raises(CreativeMemoryError, match="exactly match"):
        build_creative_memory_workspace(
            target_project,
            scope="subject",
            subject_id="different-subject",
            subject_name="Different Name",
            preferences=["style=neutral"],
            source_memory_path=source_path,
            replace_existing=True,
        )


def test_duplicate_entries_merge_and_opposing_instruction_remains_conflict(tmp_path):
    project_path = _project(tmp_path, "conflict_project")
    entries = _explicit_entries(
        "conflict_project",
        "project",
        ["shot=hold the close-up", "shot=hold the close-up"],
        [],
        ["shot=hold the close-up"],
    )

    deduplicated = _deduplicate(entries)
    conflicts = _conflicts(deduplicated)

    assert len(deduplicated) == 2
    assert len(conflicts) == 1
    assert set(conflicts[0].entry_ids) == {
        entry.memory_entry_id for entry in deduplicated
    }


def test_revision_memory_preserves_full_request_and_manual_fulfillment(tmp_path):
    plan_path = tmp_path / "revision_plan.json"
    application_path = tmp_path / "revision_application.json"
    plan_path.write_text("{}", encoding="utf-8")
    application_path.write_text("{}", encoding="utf-8")
    clause = SimpleNamespace(
        clause_id="semantic_001",
        domain="text",
        operation="reduce_density",
        matched_text=["减少字幕"],
        confidence=0.85,
        acceptance_observations=["Text pressure decreases."],
    )
    plan = SimpleNamespace(
        project_id="revision_project",
        revision_plan_id="revision_001",
        intent=SimpleNamespace(intent_id="intent_001", request_text="减少字幕，但保留必要信息"),
        semantic_clauses=[clause],
    )
    application = SimpleNamespace(
        revision_plan_id="revision_001",
        revision_application_id="application_001",
        semantic_outcomes=[
            SimpleNamespace(
                clause_id="semantic_001", status="manual_only", action_ids=["action_001"]
            )
        ],
    )

    entries = _revision_entries(
        plan, application, plan_path, application_path, "project"
    )

    assert any(entry.statement == "减少字幕，但保留必要信息" for entry in entries)
    parsed = next(entry for entry in entries if entry.category == "text")
    assert parsed.status == "requested"
    assert parsed.fulfillment == "manual_only"
    assert parsed.status != "confirmed"


def test_unselected_style_vocabulary_never_becomes_memory(tmp_path):
    path = tmp_path / "style_template_package.json"
    path.write_text("{}", encoding="utf-8")
    package = SimpleNamespace(
        project_id="style_project",
        package_id="style_package_001",
        selected_content_template_id=None,
        selected_aesthetic_style_id=None,
        selected_combination_id=None,
    )

    assert _selected_style_entries(package, path, "project") == []

    package.selected_aesthetic_style_id = "restrained_premium"
    selected = _selected_style_entries(package, path, "project")
    assert len(selected) == 1
    assert selected[0].statement.endswith("restrained_premium")
    assert selected[0].status == "observed"
