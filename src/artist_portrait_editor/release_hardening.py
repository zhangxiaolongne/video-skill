from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from artist_portrait_editor.constants import DATA_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.release import ReleaseHardeningCheck, ReleaseHardeningReport
from artist_portrait_editor.run_records import write_json


REQUIRED_SCHEMA_FILES = [
    "acceptance_repair_approval_record.schema.json",
    "acceptance_repair_approval_request.schema.json",
    "acceptance_repair_execution_bundle.schema.json",
    "acceptance_repair_execution_dry_run.schema.json",
    "acceptance_repair_execution_record.schema.json",
    "acceptance_repair_plan.schema.json",
    "release_hardening_report.schema.json",
    "rhythm_agent_candidate.schema.json",
    "rhythm_intent.schema.json",
    "rhythm_media_qc_report.schema.json",
    "rhythm_plan.schema.json",
    "rhythm_repair_plan.schema.json",
    "workflow_execution_record.schema.json",
    "workflow_execution_review.schema.json",
    "workflow_plan.schema.json",
    "workflow_repair_approval_record.schema.json",
    "workflow_repair_approval_request.schema.json",
    "workflow_repair_dry_run.schema.json",
    "workflow_repair_execution_record.schema.json",
    "workflow_repair_execution_review.schema.json",
    "workflow_repair_refresh_plan.schema.json",
    "workflow_repair_plan.schema.json",
]


REQUIRED_ARTIFACT_TOKENS = [
    "rhythm_plan.json",
    "rhythm_media_qc.json",
    "rhythm_repair_plan.json",
    "workflow_plan.json",
    "workflow_execution_review.json",
    "workflow_repair_plan.json",
    "workflow_repair_approval_request.json",
    "workflow_repair_approval_record.json",
    "workflow_repair_dry_run.json",
    "workflow_repair_execution_review.json",
    "workflow_repair_refresh_plan.json",
]


FORBIDDEN_SOURCE_TOKENS = [
    "import requests",
    "import httpx",
    "from openai",
    "import openai",
]


class ReleaseHardeningError(RuntimeError):
    pass


def build_release_hardening_report(
    *, project_root: Path, project_id: str, repo_root: Path
) -> tuple[Path, Path, ReleaseHardeningReport]:
    progress_path = repo_root / "docs" / "current_progress.json"
    if not progress_path.exists():
        raise ReleaseHardeningError("docs/current_progress.json is required")
    progress = json.loads(progress_path.read_text(encoding="utf-8"))
    gate = str(progress.get("capability_gate") or "")
    milestone = str(progress.get("milestone") or "")
    checks = [
        _check_gate_docs(repo_root, gate, milestone),
        _check_git_publication_state(repo_root),
        _check_schema_coverage(repo_root),
        _check_forbidden_source_tokens(repo_root),
        _check_artifact_chain(repo_root),
        _check_validation_evidence(repo_root, gate),
    ]
    passed = sum(check.status == "passed" for check in checks)
    warnings = sum(check.status == "warning" for check in checks)
    failed = sum(check.status == "failed" for check in checks)
    status = "blocked" if failed else "warning" if warnings else "ready_for_local_release"
    key = f"{project_id}:{gate}:{passed}:{warnings}:{failed}"
    report = ReleaseHardeningReport(
        release_hardening_id="release_hardening_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=project_id,
        capability_gate=gate,
        milestone=milestone,
        status=status,
        check_count=len(checks),
        passed_count=passed,
        warning_count=warnings,
        failed_count=failed,
        checks=checks,
    )
    json_path = project_root / WORKSPACE_DIR / DATA_DIR / "release_hardening_report.json"
    md_path = project_root / "output" / "release_hardening_report.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, report.model_dump(mode="json"))
    md_path.write_text(render_release_hardening_report(report) + "\n", encoding="utf-8")
    return json_path, md_path, report


def render_release_hardening_report(report: ReleaseHardeningReport) -> str:
    lines = [
        "# Release Hardening Report",
        "",
        "This report audits local release readiness. It does not commit, push, tag, render media, call models, or access the network.",
        "",
        f"- Capability gate: `{report.capability_gate}`",
        f"- Milestone: `{report.milestone}`",
        f"- Status: `{report.status}`",
        f"- Checks: `{report.check_count}`",
        f"- Passed: `{report.passed_count}`",
        f"- Warnings: `{report.warning_count}`",
        f"- Failed: `{report.failed_count}`",
        "",
    ]
    for check in report.checks:
        lines.extend(
            [
                f"## `{check.check_id}`",
                "",
                f"- Status: `{check.status}`",
                f"- Summary: {check.summary}",
                f"- Detail: {check.detail}",
                "",
            ]
        )
    return "\n".join(lines)


def _check_gate_docs(repo_root: Path, gate: str, milestone: str) -> ReleaseHardeningCheck:
    expected = {
        "AGENTS.md": f"Current gate: {milestone}.",
        "README.md": f"Current {milestone} work",
        "docs/DEVELOPMENT_PROGRESS.md": f"Current local gate: {milestone}",
        "docs/CURRENT_BATCH.md": f"Capability gate: `{gate}`",
        "docs/RELEASES.md": f"Capability gate: `{gate}`",
        "artist_portrait_editor_revision5_optimized.md": milestone,
    }
    missing = [
        f"{path}:{token}"
        for path, token in expected.items()
        if token not in (repo_root / path).read_text(encoding="utf-8")
    ]
    return ReleaseHardeningCheck(
        check_id="gate_doc_consistency",
        status="failed" if missing else "passed",
        summary="current gate is consistently recorded across canonical docs",
        detail="missing " + "; ".join(missing) if missing else f"all docs bind to {milestone}",
    )


def _check_git_publication_state(repo_root: Path) -> ReleaseHardeningCheck:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return ReleaseHardeningCheck(
            check_id="git_publication_state",
            status="failed",
            summary="git status could not be inspected",
            detail=str(exc),
        )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    return ReleaseHardeningCheck(
        check_id="git_publication_state",
        status="warning" if lines else "passed",
        summary="working tree publication state is known",
        detail=(
            f"{len(lines)} changed or untracked paths remain local; commit/push/tag are not allowed by current policy"
            if lines
            else "working tree is clean"
        ),
    )


def _check_schema_coverage(repo_root: Path) -> ReleaseHardeningCheck:
    missing = [name for name in REQUIRED_SCHEMA_FILES if not (repo_root / "schemas" / name).exists()]
    return ReleaseHardeningCheck(
        check_id="schema_coverage",
        status="failed" if missing else "passed",
        summary="release-critical rhythm/workflow/acceptance schemas are present",
        detail="missing " + ", ".join(missing) if missing else f"{len(REQUIRED_SCHEMA_FILES)} schema files present",
    )


def _check_forbidden_source_tokens(repo_root: Path) -> ReleaseHardeningCheck:
    offenders: list[str] = []
    for path in sorted((repo_root / "src" / "artist_portrait_editor").rglob("*.py")):
        if path.name == "release_hardening.py":
            continue
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_SOURCE_TOKENS:
            if token in text:
                offenders.append(f"{path.relative_to(repo_root)}:{token}")
    return ReleaseHardeningCheck(
        check_id="forbidden_source_surface",
        status="failed" if offenders else "passed",
        summary="source code does not expose forbidden paid/network provider surfaces",
        detail="; ".join(offenders) if offenders else "no forbidden source tokens found",
    )


def _check_artifact_chain(repo_root: Path) -> ReleaseHardeningCheck:
    docs = "\n".join(
        (repo_root / path).read_text(encoding="utf-8")
        for path in (
            "AGENTS.md",
            "README.md",
            "SKILL.md",
            "docs/DEVELOPMENT_PROGRESS.md",
            "docs/ENGINEERING_SPEC_V0.md",
        )
    )
    missing = [token for token in REQUIRED_ARTIFACT_TOKENS if token not in docs]
    return ReleaseHardeningCheck(
        check_id="workflow_rhythm_artifact_chain",
        status="failed" if missing else "passed",
        summary="workflow/rhythm release-critical artifacts are documented",
        detail="missing " + ", ".join(missing) if missing else f"{len(REQUIRED_ARTIFACT_TOKENS)} artifact tokens present",
    )


def _check_validation_evidence(repo_root: Path, gate: str) -> ReleaseHardeningCheck:
    combined = "\n".join(
        (repo_root / path).read_text(encoding="utf-8")
        for path in ("docs/CURRENT_BATCH.md", "docs/RELEASES.md")
    )
    required = [
        gate,
        "16 passed",
        "Full pytest: `",
        "Project checks: `run_checks.py --skip-pytest` passed",
        "git diff --check",
    ]
    missing = [token for token in required if token not in combined]
    return ReleaseHardeningCheck(
        check_id="validation_evidence",
        status="warning" if missing else "passed",
        summary="current release validation evidence is recorded",
        detail="missing " + ", ".join(missing) if missing else "targeted, full, project, and diff checks are recorded",
    )
