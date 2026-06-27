import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def snapshot() -> dict:
    return json.loads(read("docs/current_progress.json"))


def current_batch_rows() -> list[tuple[str, str]]:
    pattern = re.compile(
        r"^\| `([A-Z][A-Z0-9_-]*-\d{2})` \|.*\| "
        r"`(planned|in_progress|completed|blocked|dropped)` \|",
        re.MULTILINE,
    )
    return pattern.findall(read("docs/CURRENT_BATCH.md"))


def test_six_canonical_document_owners_exist_and_are_linked():
    payload = snapshot()
    owners = payload["documentation_system"]
    expected = {
        "master": "artist_portrait_editor_revision5_optimized.md",
        "current_progress": "docs/DEVELOPMENT_PROGRESS.md",
        "current_batch": "docs/CURRENT_BATCH.md",
        "issues": "docs/ISSUES.md",
        "decisions": "docs/DECISIONS.md",
        "releases": "docs/RELEASES.md",
        "machine_progress": "docs/current_progress.json",
    }
    assert {key: owners[key] for key in expected} == expected
    assert owners["historical_readiness_policy"] == "consolidated_in_release_ledger"
    for path in expected.values():
        assert (ROOT / path).is_file()

    progress = read("docs/DEVELOPMENT_PROGRESS.md")
    agents = read("AGENTS.md")
    master = read("artist_portrait_editor_revision5_optimized.md")
    readme = read("README.md")
    for path in expected.values():
        assert path in progress or path == "docs/current_progress.json"
    for path in expected.values():
        assert path in agents or path == "docs/current_progress.json"
    for path in (
        "docs/CURRENT_BATCH.md",
        "docs/ISSUES.md",
        "docs/DECISIONS.md",
        "docs/RELEASES.md",
    ):
        assert path in master
        assert path.removeprefix("docs/") in readme


def test_current_batch_and_machine_snapshot_match():
    payload = snapshot()
    batch = read("docs/CURRENT_BATCH.md")
    active = payload["active_batch"]
    rows = current_batch_rows()

    assert active["id"] in batch
    assert active["name"] in batch
    assert f"Status: `{active['status']}`" in batch
    assert active["capability_gate"] == payload["capability_gate"]
    assert len(rows) == 10
    assert len({task_id for task_id, _ in rows}) == 10
    assert rows == [(task["id"], task["status"]) for task in payload["tasks"]]


def test_progress_is_dashboard_not_duplicate_history():
    progress = read("docs/DEVELOPMENT_PROGRESS.md")
    releases = read("docs/RELEASES.md")
    issues = read("docs/ISSUES.md")

    assert "This is the current-stage dashboard" in progress
    assert "## Capability Dashboard" in progress
    assert "## Principal Blockers" in progress
    assert "## Next Major Decision" in progress
    assert "## Major Version History" in releases
    assert "## Active Issues" in issues
    assert "Resolved capability and governance history belongs to" in issues
    assert "V0-002a:" not in progress
    assert "final validation: 244 tests passed" not in progress


def test_master_and_tactical_docs_have_distinct_roles():
    master = read("artist_portrait_editor_revision5_optimized.md")
    progress = read("docs/DEVELOPMENT_PROGRESS.md")
    decisions = read("docs/DECISIONS.md")

    assert "本母版文档负责记录长期稳定的战略内容" in master
    assert "任何战术事实只允许有一个" in master
    assert "It is not the task ledger" in progress
    assert "DEC-001: Separate strategy from execution records" in decisions
    assert "BGM 不是最后装饰层，而是视听结构的一部分" in master


def test_third_party_and_bgm_policy_remain_recorded():
    master = read("artist_portrait_editor_revision5_optimized.md")
    progress = read("docs/DEVELOPMENT_PROGRESS.md")
    skill = read("SKILL.md")
    decisions = read("docs/DECISIONS.md")

    assert "第三方能力复用原则" in master
    assert "不重复造轮子" in master
    assert "Prefer Mature Third-Party Tools" in progress
    assert "later validated gate may use mature third-party tools" in skill
    assert "DEC-004: Prefer mature third-party capabilities" in decisions
    assert "BGM must not be treated as a final decorative layer" in progress
    assert "BPM" in progress
    assert "subtitle entrances/exits" in progress
    assert "ducking under speech" in progress
    assert "DEC-005: Treat BGM as editing structure" in decisions
    assert "DEC-009: Support multiple BGM input modes" in decisions


def test_future_bgm_input_contract_is_hard_enforced():
    master = read("artist_portrait_editor_revision5_optimized.md")
    progress = read("docs/DEVELOPMENT_PROGRESS.md")
    engineering = read("docs/ENGINEERING_SPEC_V0.md")
    agents = read("AGENTS.md")
    skill = read("SKILL.md")
    contract = snapshot()["future_bgm_input_contract"]

    expected_modes = [
        "direct_audio",
        "video_audio_extract",
        "source_embedded_audio",
        "multiple_candidates",
        "none_yet",
    ]
    required_provenance = {
        "music_candidate_id",
        "input_mode",
        "source_ref",
        "source_media_kind",
        "extract_in",
        "extract_out",
        "audio_stream_index",
        "content_hash",
        "duration",
        "rights_status",
        "contains_speech",
        "contains_vocals",
        "contains_environment",
        "contains_sound_effects",
        "user_intent",
        "analysis_status",
    }

    assert contract["status"] == "required_for_future_gate"
    assert contract["input_modes"] == expected_modes
    assert required_provenance.issubset(contract["required_provenance"])
    assert contract["allows_unresolved_music_slot"] is True
    assert contract["video_extract_is_mixed_audio"] is True
    assert contract["video_extract_implies_clean_bgm"] is False
    assert contract["derived_audio_is_rebuildable_cache"] is True

    for mode in expected_modes:
        assert mode in master
        assert mode in skill
    assert "BGM 输入来源契约" in master
    assert "mixed audio track, not automatically a clean BGM" in progress
    assert "invalid audio" in engineering
    assert "Never treat an extracted video mix as clean BGM" in agents
    assert "Never label extraction alone as clean BGM" in skill


def test_issue_decision_and_release_ledgers_have_required_contracts():
    issues = read("docs/ISSUES.md")
    decisions = read("docs/DECISIONS.md")
    releases = read("docs/RELEASES.md")

    assert "ISSUE-002" in issues
    assert "ISSUE-008" in issues
    assert "Resolution condition" in issues
    assert "DEC-001" in decisions
    assert "DEC-007" in decisions
    assert "Rationale" in decisions
    assert "Revisit when" in decisions
    assert "Current Release State" in releases
    assert "Current Validation" in releases
    assert "Do not recreate per-version readiness" in releases
    assert "19fc5abe33c22c52073f16d83a60ec05ad87ab56" in releases


def test_machine_readable_progress_matches_current_dashboard():
    progress = read("docs/DEVELOPMENT_PROGRESS.md")
    payload = snapshot()

    assert payload["schema_version"] == "1.4"
    assert payload["capability_gate"] == "V0-018"
    assert payload["milestone"] in progress
    assert payload["active_batch"]["id"] in progress
    assert payload["capability_progress"]["proposal_generation"] == "completed"
    assert payload["capability_progress"]["timeline_generation"] == "completed"
    assert payload["capability_progress"]["bgm_ingestion_and_fitting"] == "completed"
    assert payload["capability_progress"]["bgm_technical_analysis"] == "completed"
    assert payload["capability_progress"]["bgm_recommendation_review"] == "completed"
    assert payload["capability_progress"]["preview_rendering"] == "completed"
    assert payload["capability_progress"]["preview_quality_review"] == "completed"
    assert payload["capability_progress"]["final_export"] == "completed"


def test_version_progress_batch_contract_is_hard_enforced():
    agents = read("AGENTS.md")
    master = read("artist_portrait_editor_revision5_optimized.md")
    progress = read("docs/DEVELOPMENT_PROGRESS.md")
    contract = snapshot()["development_batch_contract"]

    assert "Mandatory Development Batch Contract" in agents
    assert "at least ten independent version tasks" in agents
    assert "may count as major-version tasks only when all conditions hold" in agents
    assert "A single field, test, file move, or incidental bug" in agents
    assert "开发批次硬约束" in master
    assert "只有在同时满足以下条件时，才可作为大版本任务" in master
    assert "Mandatory Batch Contract" in progress
    assert "Do not pad the batch" in progress

    assert contract["minimum_version_tasks"] == 10
    assert contract["requires_named_capability_milestone"] is True
    assert contract["requires_final_goal_delta"] is True
    assert contract["gate_blocked_action"] == "stop_and_request_gate_promotion"
    assert contract["v0_010_ordinary_expansion_closed"] is True
    assert {
        "isolated_fields",
        "isolated_schemas_or_models",
        "individual_tests_or_fixtures",
        "documentation_only",
        "local_refactors_or_file_moves",
        "incidental_bug_fixes",
        "isolated_diagnostics",
        "isolated_review_rules",
    }.issubset(contract["small_task_non_counting_work"])
    assert {
        "versioned_data_contract_migration",
        "comprehensive_acceptance_or_evaluation_program",
        "capability_enabling_architectural_refactor",
        "major_defect_closure_or_release_hardening_program",
    }.issubset(contract["major_version_eligible_work"])
