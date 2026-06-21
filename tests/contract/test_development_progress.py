from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_development_progress_records_versions_and_bgm_constraint():
    content = (ROOT / "docs" / "DEVELOPMENT_PROGRESS.md").read_text(encoding="utf-8")

    assert "V0-002a" in content
    assert "V0-002q" in content
    assert "V0-002s" in content
    assert "BGM must not be treated as a final decorative layer" in content
    assert "BPM" in content
    assert "subtitle entrances/exits" in content
    assert "ducking under speech" in content
    assert "proposal, timeline, review, and preview gates" in content


def test_master_and_development_docs_have_distinct_roles():
    master = (ROOT / "artist_portrait_editor_revision5_optimized.md").read_text(
        encoding="utf-8"
    )
    progress = (ROOT / "docs" / "DEVELOPMENT_PROGRESS.md").read_text(encoding="utf-8")

    assert "母版记录战略原则和长期约束" in master
    assert "开发文档记录当前进度、战术状态和后续落地批次" in master
    assert "BGM 不是最后装饰层，而是视听结构的一部分" in master
    assert "The master document" in progress
    assert "This development document owns tactics" in progress


def test_third_party_tool_policy_is_recorded():
    master = (ROOT / "artist_portrait_editor_revision5_optimized.md").read_text(
        encoding="utf-8"
    )
    progress = (ROOT / "docs" / "DEVELOPMENT_PROGRESS.md").read_text(encoding="utf-8")
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")

    assert "第三方能力复用原则" in master
    assert "不重复造轮子" in master
    assert "公开素材场景下，第三方工具调用不是默认禁区" in master
    assert "Prefer Mature Third-Party Tools" in progress
    assert "check available tools, skills, plugins, and libraries" in progress
    assert "later validated gate may use mature third-party tools" in skill
