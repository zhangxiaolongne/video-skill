from __future__ import annotations

from artist_portrait_editor.models.source import RightsStatus, SourceRecord


def risk_issue(
    *,
    source: SourceRecord,
    code: str,
    severity: str,
    detail: str,
) -> dict[str, str]:
    return {
        "scope": "source",
        "source_id": source.source_id,
        "location": source.primary_location,
        "code": code,
        "severity": severity,
        "detail": detail,
    }


def artifact_issue(
    *,
    step: str,
    ref: str,
    code: str,
    severity: str,
    detail: str,
) -> dict[str, str]:
    return {
        "scope": "artifact",
        "step": step,
        "ref": ref,
        "location": ref,
        "code": code,
        "severity": severity,
        "detail": detail,
        "next_action": rebuild_command_for_step(step),
    }


def review_scope_issue(*, scope: str, detail: str) -> dict[str, str]:
    return {
        "scope": "review_scope",
        "review_scope": scope,
        "code": "review_scope_skipped",
        "severity": "warning",
        "detail": detail,
    }


def workspace_issue(
    *,
    code: str,
    severity: str,
    detail: str,
    next_action: str,
) -> dict[str, str]:
    return {
        "scope": "workspace",
        "code": code,
        "severity": severity,
        "detail": detail,
        "next_action": next_action,
    }


def rebuild_command_for_step(step: str) -> str:
    commands = {
        "init": "artist-portrait init --project <project.yaml>",
        "scan": "artist-portrait scan --project <project.yaml>",
        "transcribe": "artist-portrait transcribe --project <project.yaml>",
        "segment": "artist-portrait segment --project <project.yaml>",
        "keyframes": "artist-portrait keyframes --project <project.yaml>",
        "analyze": "artist-portrait analyze --project <project.yaml>",
        "map": "artist-portrait map --project <project.yaml>",
        "propose": "artist-portrait propose --project <project.yaml>",
        "timeline": (
            "artist-portrait timeline --project <project.yaml> "
            "--proposal <proposal_safe|proposal_advanced|proposal_risky>"
        ),
        "review_project": "artist-portrait review --project <project.yaml> --scope project",
        "review_timeline": "artist-portrait review --project <project.yaml> --scope timeline",
        "bgm_import": (
            "artist-portrait bgm import --project <project.yaml> "
            "--file <project-relative-media>"
        ),
        "bgm_fit": (
            "artist-portrait bgm fit --project <project.yaml> "
            "--candidate <candidate-id>"
        ),
        "bgm_analyze": "artist-portrait bgm analyze --project <project.yaml>",
        "preview": "artist-portrait preview --project <project.yaml>",
        "review_preview": "artist-portrait review --project <project.yaml> --scope preview",
        "final_export": (
            "artist-portrait export --project <project.yaml> --profile review_720p"
        ),
        "review_final_export": (
            "artist-portrait review --project <project.yaml> --scope final_export"
        ),
        "review_bgm": "artist-portrait bgm review --project <project.yaml>",
    }
    return commands.get(step, "rerun the command that produced this output")


def render_risk_report(
    *,
    records: list[SourceRecord],
    issues: list[dict[str, str]],
    sources_ref: str,
) -> str:
    severity_counts = _count_by_value(issue["severity"] for issue in issues)
    code_counts = _count_by_value(issue["code"] for issue in issues)
    return (
        "# Risk Report\n\n"
        "This deterministic project review is rendered from local scan data only. "
        "No transcription, visual analysis, embeddings, creative proposals, timeline "
        "generation, preview rendering, network calls, or model calls were performed.\n\n"
        "## Summary\n\n"
        f"- Source ledger: `{sources_ref}`\n"
        f"- Source count: `{len(records)}`\n"
        f"- Issue count: `{len(issues)}`\n\n"
        "## Severity Counts\n\n"
        f"{_render_count_lines(severity_counts)}"
        "## Issue Counts\n\n"
        f"{_render_count_lines(code_counts)}"
        "## Issues\n\n"
        f"{render_issue_sections(issues)}"
    )


def render_issue_sections(issues: list[dict[str, str]]) -> str:
    if not issues:
        return "No project review issues were found in the current scan ledger.\n"
    sections = []
    for index, issue in enumerate(issues, start=1):
        optional_lines = ""
        if issue.get("source_id"):
            optional_lines += f"- Source ID: `{issue['source_id']}`\n"
        if issue.get("step"):
            optional_lines += f"- Step: `{issue['step']}`\n"
        if issue.get("location"):
            optional_lines += f"- Location: `{issue['location']}`\n"
        if issue.get("review_scope"):
            optional_lines += f"- Review scope: `{issue['review_scope']}`\n"
        if issue.get("ref"):
            optional_lines += f"- Output ref: `{issue['ref']}`\n"
        if issue.get("next_action"):
            optional_lines += f"- Next action: `{issue['next_action']}`\n"
        sections.append(
            f"### {index}. `{issue['code']}`\n\n"
            f"- Scope: `{issue['scope']}`\n"
            f"- Severity: `{issue['severity']}`\n"
            f"{optional_lines}"
            f"- Detail: {issue['detail']}\n"
        )
    return "\n".join(sections)


def source_rights_issue(source: SourceRecord, *, allow_restricted_rights: bool) -> dict[str, str] | None:
    if source.rights_status.value == RightsStatus.permission_unknown:
        return risk_issue(
            source=source,
            code="rights_unknown",
            severity="warning",
            detail="rights_status is permission_unknown",
        )
    if source.rights_status.value == RightsStatus.restricted and not allow_restricted_rights:
        return risk_issue(
            source=source,
            code="rights_restricted",
            severity="error",
            detail="rights_status is restricted and project policy does not allow restricted rights",
        )
    return None


def _count_by_value(values) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def _render_count_lines(counts: dict[str, int]) -> str:
    if not counts:
        return "- none: `0`\n\n"
    return "".join(f"- {key}: `{counts[key]}`\n" for key in sorted(counts)) + "\n"
