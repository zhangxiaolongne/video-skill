#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


REQUIRED_BOUNDARY_TERMS = (
    "transcription",
    "visual analysis",
    "model calls",
    "network search",
    "image generation",
)


def load_package_policy(path: Path) -> tuple[dict[str, Any], str | None]:
    if not path.exists():
        return {}, None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, f"skill-package.json is invalid JSON: {exc}"
    if not isinstance(payload, dict):
        return {}, "skill-package.json must contain a JSON object"
    return payload, None


def load_skill_frontmatter(skill_md: Path) -> tuple[dict[str, Any] | None, str, str | None]:
    if not skill_md.exists():
        return None, "", "SKILL.md not found"
    content = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not match:
        return None, content, "SKILL.md frontmatter is missing or invalid"
    try:
        frontmatter = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        return None, content, f"SKILL.md frontmatter YAML is invalid: {exc}"
    if not isinstance(frontmatter, dict):
        return None, content, "SKILL.md frontmatter must be a mapping"
    return frontmatter, content, None


def git_remote_repo_name(root: Path) -> str | None:
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    remote = result.stdout.strip().removesuffix(".git")
    if not remote:
        return None
    return remote.rsplit("/", 1)[-1].split(":", 1)[-1]


def issue(*, severity: str, code: str, detail: str) -> dict[str, str]:
    return {
        "severity": severity,
        "code": code,
        "detail": detail,
    }


def preflight(root: Path) -> dict[str, Any]:
    root = root.resolve()
    issues: list[dict[str, str]] = []
    policy, policy_error = load_package_policy(root / "skill-package.json")
    if policy_error:
        issues.append(
            issue(
                severity="error",
                code="package_policy_invalid",
                detail=policy_error,
            )
        )
    frontmatter, skill_content, frontmatter_error = load_skill_frontmatter(root / "SKILL.md")
    skill_name = ""
    if frontmatter_error:
        issues.append(
            issue(
                severity="error",
                code="skill_frontmatter_invalid",
                detail=frontmatter_error,
            )
        )
    elif frontmatter:
        skill_name = str(frontmatter.get("name") or "").strip()
        description = str(frontmatter.get("description") or "").strip()
        if not skill_name:
            issues.append(
                issue(
                    severity="error",
                    code="skill_name_missing",
                    detail="frontmatter name is missing",
                )
            )
        if len(description) > 1024:
            issues.append(
                issue(
                    severity="error",
                    code="skill_description_too_long",
                    detail="frontmatter description exceeds quick validator limit",
                )
            )
        for term in REQUIRED_BOUNDARY_TERMS:
            if term not in description and term not in skill_content:
                issues.append(
                    issue(
                        severity="error",
                        code="skill_boundary_missing",
                        detail=f"required boundary term is missing: {term}",
                    )
                )

    if policy and skill_name:
        policy_skill_name = str(policy.get("skill_name") or "").strip()
        canonical_install_dir = str(policy.get("canonical_install_dir") or "").strip()
        if policy_skill_name != skill_name:
            issues.append(
                issue(
                    severity="error",
                    code="package_policy_skill_name_mismatch",
                    detail=(
                        f"skill-package.json skill_name `{policy_skill_name}` "
                        f"does not match SKILL.md name `{skill_name}`"
                    ),
                )
            )
        if canonical_install_dir != skill_name:
            issues.append(
                issue(
                    severity="error",
                    code="canonical_install_dir_mismatch",
                    detail=(
                        f"canonical install dir `{canonical_install_dir}` "
                        f"must match skill name `{skill_name}`"
                    ),
                )
            )

    openai_yaml = root / "agents" / "openai.yaml"
    if not openai_yaml.exists():
        issues.append(
            issue(
                severity="error",
                code="openai_yaml_missing",
                detail="agents/openai.yaml not found",
            )
        )
    else:
        try:
            payload = yaml.safe_load(openai_yaml.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            issues.append(
                issue(
                    severity="error",
                    code="openai_yaml_invalid",
                    detail=str(exc),
                )
            )
        else:
            interface = payload.get("interface") if isinstance(payload, dict) else None
            if not isinstance(interface, dict):
                issues.append(
                    issue(
                        severity="error",
                        code="openai_yaml_interface_missing",
                        detail="agents/openai.yaml must contain interface mapping",
                    )
                )
            elif skill_name and f"${skill_name}" not in str(interface.get("default_prompt") or ""):
                issues.append(
                    issue(
                        severity="error",
                        code="default_prompt_skill_missing",
                        detail=f"default_prompt must mention ${skill_name}",
                    )
                )

    if skill_name:
        folder_name = root.name
        if folder_name != skill_name:
            issues.append(
                issue(
                    severity="warning",
                    code="folder_name_mismatch",
                    detail=f"current folder `{folder_name}` does not match skill name `{skill_name}`",
                )
            )
        repo_name = git_remote_repo_name(root)
        distribution_repositories = set(policy.get("distribution_repositories") or [])
        if repo_name and repo_name != skill_name and repo_name not in distribution_repositories:
            issues.append(
                issue(
                    severity="warning",
                    code="repo_name_mismatch",
                    detail=f"origin repo `{repo_name}` does not match skill name `{skill_name}`",
                )
            )

    errors = [item for item in issues if item["severity"] == "error"]
    warnings = [item for item in issues if item["severity"] == "warning"]
    return {
        "root": str(root),
        "skill_name": skill_name,
        "issue_count": len(issues),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "issues": issues,
        "ok": not errors,
        "package_policy": {
            "present": bool(policy),
            "canonical_install_dir": policy.get("canonical_install_dir") if policy else None,
            "distribution_repositories": policy.get("distribution_repositories", []) if policy else [],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("skill_dir", nargs="?", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    payload = preflight(Path(args.skill_dir))
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"skill: {payload['skill_name'] or 'unknown'}")
        print(f"errors: {payload['error_count']}")
        print(f"warnings: {payload['warning_count']}")
        for item in payload["issues"]:
            print(f"- {item['severity']}: {item['code']} - {item['detail']}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
