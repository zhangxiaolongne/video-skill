from __future__ import annotations

import hashlib
import json
from pathlib import Path

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.creative_memory import (
    CreativeMemory,
    CreativeMemoryEntry,
    MemoryConflict,
    MemoryEvidenceBinding,
    MemoryIdentity,
    MemoryProvenance,
)
from artist_portrait_editor.models.revision import RevisionPlan
from artist_portrait_editor.models.revision_application import RevisionApplication
from artist_portrait_editor.models.state import ActiveMode, OverallStatus, StepLedgerEntry, StepStatus
from artist_portrait_editor.models.style_template import StyleTemplatePackage
from artist_portrait_editor.run_records import environment_snapshot, new_run_id, utc_now, write_json
from artist_portrait_editor.workspace_errors import WorkspacePrerequisiteError
from artist_portrait_editor.workspace_state import (
    atomic_write_text,
    fingerprint_file,
    fingerprint_inputs,
    load_state,
    project_root,
    save_state,
    write_run_report,
)


class CreativeMemoryError(RuntimeError):
    pass


CATEGORIES = {
    "style", "shot", "bgm", "text", "cover", "rhythm", "transition",
    "composition", "duration", "audio", "ending", "constraint", "theme",
    "audience", "platform", "custom",
}

DOMAIN_CATEGORY = {
    "style": "style",
    "rhythm": "rhythm",
    "text": "text",
    "source_audio": "audio",
    "bgm": "bgm",
    "transition": "transition",
    "ending": "ending",
    "duration": "duration",
    "constraint": "constraint",
    "emotion": "style",
    "structure": "rhythm",
}

OPERATION_POLARITY = {
    "protect_voice": "require",
    "reduce_density": "prefer",
    "reduce_bgm": "prefer",
    "remove": "forbid",
}


def build_creative_memory_workspace(
    project_path: Path,
    *,
    scope: str,
    subject_id: str | None = None,
    subject_name: str | None = None,
    aliases: list[str] | None = None,
    preferences: list[str] | None = None,
    constraints: list[str] | None = None,
    forbids: list[str] | None = None,
    source_memory_path: Path | None = None,
    include_project_revisions: bool = False,
    replace_existing: bool = False,
) -> tuple[Path, Path, CreativeMemory, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise WorkspacePrerequisiteError("memory requires init to complete first")
    identity = _identity(config, scope, subject_id, subject_name, aliases or [])
    data = root / WORKSPACE_DIR / DATA_DIR
    canonical_path = data / "creative_memory.json"
    evidence_paths = {
        "project": project_path.resolve(),
        "revision_plan": data / "revision_plan.json",
        "revision_application": data / "revision_application.json",
        "style_templates": data / "style_template_package.json",
        "publishability": data / "publishability.json",
    }
    entries: list[CreativeMemoryEntry] = []
    source_projects = {config.project.id}
    excluded = []
    existing = None

    if canonical_path.exists() and not replace_existing:
        existing = CreativeMemory.model_validate_json(
            canonical_path.read_text(encoding="utf-8")
        )
        if (
            existing.identity.scope != identity.scope
            or existing.identity.identity_id != identity.identity_id
        ):
            raise CreativeMemoryError(
                "existing canonical memory identity differs; use --replace-existing explicitly"
            )
        aliases = set(existing.identity.aliases) | set(identity.aliases)
        if existing.identity.display_name != identity.display_name:
            aliases.add(existing.identity.display_name)
        aliases.discard(identity.display_name)
        identity = identity.model_copy(update={"aliases": sorted(aliases)})
        entries.extend(
            entry
            for entry in existing.entries
            if any(item.source_type != "project_config" for item in entry.provenance)
        )
        source_projects.update(existing.source_project_ids)

    if identity.scope == "project":
        entries.extend(_project_config_entries(config, project_path.resolve()))
    entries.extend(
        _explicit_entries(
            config.project.id,
            identity.scope,
            preferences or [],
            constraints or [],
            forbids or [],
        )
    )

    include_revisions = identity.scope == "project" or include_project_revisions
    if include_revisions and evidence_paths["revision_plan"].exists():
        plan = RevisionPlan.model_validate_json(
            evidence_paths["revision_plan"].read_text(encoding="utf-8")
        )
        if plan.project_id != config.project.id:
            raise CreativeMemoryError("revision plan project_id mismatches project")
        application = _read_optional(
            evidence_paths["revision_application"], RevisionApplication
        )
        if application and application.project_id != config.project.id:
            raise CreativeMemoryError("revision application project_id mismatches project")
        entries.extend(
            _revision_entries(
                plan,
                application,
                evidence_paths["revision_plan"],
                evidence_paths["revision_application"],
                identity.scope,
            )
        )

    if evidence_paths["style_templates"].exists():
        style_package = StyleTemplatePackage.model_validate_json(
            evidence_paths["style_templates"].read_text(encoding="utf-8")
        )
        if style_package.project_id != config.project.id:
            raise CreativeMemoryError("style template package project_id mismatches project")
        selected_entries = _selected_style_entries(
            style_package, evidence_paths["style_templates"], identity.scope
        )
        entries.extend(selected_entries)
        if not selected_entries:
            excluded.append(
                "unselected content forms, aesthetic styles, techniques, arcs, and examples are vocabulary, not memory"
            )

    if source_memory_path:
        imported = CreativeMemory.model_validate_json(
            source_memory_path.read_text(encoding="utf-8")
        )
        if imported.identity.scope != identity.scope or imported.identity.identity_id != identity.identity_id:
            raise CreativeMemoryError(
                "source memory identity must exactly match scope and identity_id"
            )
        imported_entries = [
            entry
            for entry in imported.entries
            if identity.scope == "project" or entry.applicability == "subject_reusable"
        ]
        entries.extend(
            _mark_imported(imported_entries, imported, source_memory_path, config.project.id)
        )
        source_projects.update(imported.source_project_ids)

    entries = _deduplicate(entries)
    if not entries:
        raise CreativeMemoryError(
            "memory has no auditable entries; provide explicit preferences/constraints or current project evidence"
        )
    conflicts = _conflicts(entries)
    bindings = _evidence_bindings(evidence_paths, include_revisions, root)
    if source_memory_path:
        bindings.append(
            MemoryEvidenceBinding(
                label="source_memory",
                ref=source_memory_path.name,
                fingerprint=fingerprint_file(source_memory_path),
                used_for_memory=True,
                limitation="identity-matched imported instructions remain advisory and retain original provenance",
            )
        )
    warnings = []
    if conflicts:
        warnings.append("memory contains unresolved contradictory instructions")
    if any(entry.status == "requested" and entry.fulfillment != "applied" for entry in entries):
        warnings.append("requested revisions are retained separately from proven successful preferences")
    if identity.scope == "subject" and include_project_revisions:
        warnings.append("project revision requests were explicitly included in subject memory and remain unverified for reuse")
    if excluded:
        warnings.extend(excluded)

    retrieval_context = _retrieval_context(identity, entries, conflicts)
    key = json.dumps(
        {
            "identity": identity.model_dump(mode="json"),
            "entries": [entry.model_dump(mode="json") for entry in entries],
            "conflicts": [conflict.model_dump(mode="json") for conflict in conflicts],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    memory = CreativeMemory(
        memory_id="creative_memory_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=config.project.id,
        identity=identity,
        status="warning" if warnings else "ready",
        entry_count=len(entries),
        confirmed_count=sum(entry.status == "confirmed" for entry in entries),
        requested_count=sum(entry.status == "requested" for entry in entries),
        hard_constraint_count=sum(entry.strength == "hard" for entry in entries),
        unresolved_conflict_count=len(conflicts),
        source_project_ids=sorted(source_projects),
        entries=entries,
        conflicts=conflicts,
        evidence_bindings=bindings,
        retrieval_context=retrieval_context,
        excluded_candidate_claims=excluded,
        warnings=warnings,
    )
    json_path = canonical_path
    md_path = root / config.paths.output_dir / "creative_memory.md"
    atomic_write_text(json_path, memory.model_dump_json(indent=2) + "\n")
    atomic_write_text(md_path, render_creative_memory(memory))

    run_id = new_run_id()
    step_status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    refs = [json_path.relative_to(root).as_posix(), md_path.relative_to(root).as_posix()]
    input_items = [(label, path) for label, path in evidence_paths.items() if path.exists()]
    if source_memory_path:
        input_items.append(("source_memory", source_memory_path))
    state.steps["creative_memory"] = StepLedgerEntry(
        status=step_status,
        input_fingerprint=fingerprint_inputs(input_items),
        output_refs=refs,
        last_run_id=run_id,
        warnings=warnings,
    )
    state.active_mode = ActiveMode.creative
    state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    run_dir = root / WORKSPACE_DIR / RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        run_dir / "command.json",
        {
            "command": "memory",
            "project": project_path.resolve().relative_to(root).as_posix(),
            "scope": scope,
            "identity_id": identity.identity_id,
            "source_memory": source_memory_path.name if source_memory_path else None,
        },
    )
    write_json(run_dir / "environment.json", environment_snapshot())
    write_json(
        run_dir / "step_result.json",
        {
            "step": "creative_memory",
            "status": step_status.value,
            "entry_count": len(entries),
            "conflict_count": len(conflicts),
            "memory_applied_to_edit": False,
            "output_refs": refs,
        },
    )
    save_state(root, state)
    write_run_report(root / config.paths.output_dir, state, warnings)
    return json_path, md_path, memory, warnings


def _identity(config, scope, subject_id, subject_name, aliases):
    clean_aliases = sorted({alias.strip() for alias in aliases if alias.strip()})
    if scope == "project":
        if subject_id or subject_name:
            raise CreativeMemoryError("project memory does not accept subject identity fields")
        return MemoryIdentity(
            scope="project",
            identity_id=config.project.id,
            display_name=config.project.title,
            aliases=clean_aliases,
            identity_source="project_config",
        )
    if scope != "subject":
        raise CreativeMemoryError("memory scope must be project or subject")
    if not subject_id or not subject_name:
        raise CreativeMemoryError("subject memory requires explicit --subject-id and --subject-name")
    return MemoryIdentity(
        scope="subject",
        identity_id=subject_id.strip(),
        display_name=subject_name.strip(),
        aliases=clean_aliases,
        identity_source="explicit_cli",
    )


def _project_config_entries(config, project_path):
    provenance = _provenance(
        "project_config", config.project.id, project_path.name,
        fingerprint_file(project_path), ["project.yaml"],
    )
    specs = [
        ("theme", "context", config.creative_brief.theme, "soft"),
        ("audience", "context", config.creative_brief.audience, "soft"),
        ("platform", "context", config.creative_brief.platform, "soft"),
    ]
    specs.extend(("style", "prefer", tone, "soft") for tone in config.creative_brief.tone)
    if config.creative_brief.target_duration_seconds:
        specs.append(
            ("duration", "require", f"target {config.creative_brief.target_duration_seconds} seconds", "hard")
        )
    if not config.content_policy.allow_music:
        specs.append(("bgm", "forbid", "added music is disabled by project content policy", "hard"))
    return [
        _entry(
            category, polarity, statement, strength, "confirmed", "not_applicable",
            "project_only", 1.0, [provenance], [],
        )
        for category, polarity, statement, strength in specs
    ]


def _explicit_entries(project_id, scope, preferences, constraints, forbids):
    applicability = "subject_reusable" if scope == "subject" else "project_only"
    entries = []
    for raw in preferences:
        category, statement = _parse_instruction(raw)
        provenance = _explicit_provenance(project_id, "prefer", raw)
        entries.append(_entry(category, "prefer", statement, "soft", "confirmed", "unverified", applicability, 1.0, [provenance], ["verify preference against future playback"]))
    for raw in constraints:
        category, statement = _parse_instruction(raw)
        provenance = _explicit_provenance(project_id, "require", raw)
        entries.append(_entry(category, "require", statement, "hard", "confirmed", "unverified", applicability, 1.0, [provenance], ["verify constraint in every candidate review"]))
    for raw in forbids:
        category, statement = _parse_instruction(raw)
        provenance = _explicit_provenance(project_id, "forbid", raw)
        entries.append(_entry(category, "forbid", statement, "hard", "confirmed", "unverified", applicability, 1.0, [provenance], ["block candidates that violate this instruction"]))
    return entries


def _explicit_provenance(project_id, polarity, raw):
    return _provenance(
        "user_explicit",
        project_id,
        "cli:memory",
        _text_fingerprint(f"{polarity}|{raw}"),
        ["explicit CLI input", polarity],
    )


def _revision_entries(plan, application, plan_path, application_path, scope):
    applicability = "project_only" if scope == "project" else "subject_reusable"
    plan_provenance = _provenance(
        "revision_request", plan.project_id, plan_path.name, fingerprint_file(plan_path),
        [plan.revision_plan_id, plan.intent.intent_id],
    )
    outcome_by_clause = {
        outcome.clause_id: outcome for outcome in application.semantic_outcomes
    } if application and application.revision_plan_id == plan.revision_plan_id else {}
    entries = [
        _entry(
            "custom", "context", plan.intent.request_text, "soft", "requested",
            "unverified", applicability, 1.0, [plan_provenance],
            ["preserve the complete user request because deterministic clauses may be incomplete"],
        )
    ]
    for clause in plan.semantic_clauses:
        outcome = outcome_by_clause.get(clause.clause_id)
        provenance = [plan_provenance]
        fulfillment = "unverified"
        if outcome:
            fulfillment = outcome.status
            provenance.append(
                _provenance(
                    "revision_application", plan.project_id, application_path.name,
                    fingerprint_file(application_path),
                    [application.revision_application_id, clause.clause_id, *outcome.action_ids],
                )
            )
        statement = " / ".join(clause.matched_text) or f"{clause.domain}:{clause.operation}"
        entries.append(
            _entry(
                DOMAIN_CATEGORY.get(clause.domain, "custom"),
                OPERATION_POLARITY.get(clause.operation, "prefer"),
                statement,
                "hard" if clause.domain == "constraint" else "soft",
                "requested",
                fulfillment,
                applicability,
                clause.confidence,
                provenance,
                clause.acceptance_observations,
            )
        )
    return entries


def _selected_style_entries(package, path, scope):
    selected = [
        ("style", package.selected_content_template_id, "selected content form"),
        ("style", package.selected_aesthetic_style_id, "selected aesthetic style"),
        ("style", package.selected_combination_id, "selected creative combination"),
    ]
    provenance = _provenance(
        "selected_style", package.project_id, path.name, fingerprint_file(path),
        [package.package_id],
    )
    applicability = "subject_reusable" if scope == "subject" else "project_only"
    return [
        _entry("style", "prefer", f"{label}: {value}", "soft", "observed", "unverified", applicability, 0.8, [provenance], ["confirm selection remains preferred after playback"])
        for _, value, label in selected if value
    ]


def _mark_imported(entries, memory, path, project_id):
    provenance = _provenance(
        "imported_memory", project_id, path.name, fingerprint_file(path), [memory.memory_id],
    )
    return [entry.model_copy(update={"provenance": [*entry.provenance, provenance]}) for entry in entries]


def _deduplicate(entries):
    merged = {}
    for entry in entries:
        key = (entry.category, entry.polarity, _normalize(entry.statement), entry.applicability)
        if key not in merged:
            merged[key] = entry
            continue
        current = merged[key]
        provenance = {item.provenance_id: item for item in [*current.provenance, *entry.provenance]}
        status = "confirmed" if "confirmed" in {current.status, entry.status} else current.status
        merged[key] = current.model_copy(
            update={
                "status": status,
                "confidence": max(current.confidence, entry.confidence),
                "provenance": list(provenance.values()),
                "acceptance_required": sorted(set(current.acceptance_required + entry.acceptance_required)),
            }
        )
    return sorted(merged.values(), key=lambda item: (item.category, item.polarity, item.statement))


def _conflicts(entries):
    opposing = {
        "prefer": {"avoid", "forbid"},
        "avoid": {"prefer", "require"},
        "require": {"avoid", "forbid"},
        "forbid": {"prefer", "require"},
        "context": set(),
    }
    conflicts = []
    for index, left in enumerate(entries):
        for right in entries[index + 1:]:
            if left.category != right.category or _normalize(left.statement) != _normalize(right.statement):
                continue
            if right.polarity not in opposing[left.polarity]:
                continue
            key = f"{left.memory_entry_id}|{right.memory_entry_id}"
            conflicts.append(
                MemoryConflict(
                    conflict_id="memory_conflict_" + hashlib.sha256(key.encode()).hexdigest()[:16],
                    category=left.category,
                    entry_ids=[left.memory_entry_id, right.memory_entry_id],
                    detail=f"The same instruction is both {left.polarity} and {right.polarity}: {left.statement}",
                    resolution="Keep both visible and require explicit user resolution before application.",
                )
            )
    return conflicts


def _evidence_bindings(paths, include_revisions, root):
    bindings = []
    for label, path in paths.items():
        if not path.exists():
            continue
        used = label == "project" or label == "style_templates" or (
            include_revisions and label in {"revision_plan", "revision_application"}
        )
        limitation = {
            "project": "explicit project facts only",
            "revision_plan": "a request is not proof of successful application",
            "revision_application": "application status is not proof of user satisfaction",
            "style_templates": "only explicit selected ids may become memory",
            "publishability": "quality verdict is bound for audit but does not become a preference",
        }[label]
        bindings.append(
            MemoryEvidenceBinding(
                label=label,
                ref=path.relative_to(root).as_posix(),
                fingerprint=fingerprint_file(path),
                used_for_memory=used,
                limitation=limitation,
            )
        )
    return bindings


def _retrieval_context(identity, entries, conflicts):
    lines = [f"identity={identity.scope}:{identity.identity_id}:{identity.display_name}"]
    for entry in entries:
        lines.append(
            f"{entry.category}:{entry.polarity}:{entry.status}:{entry.fulfillment}:{entry.statement}"
        )
    if conflicts:
        lines.append("unresolved_conflicts=require_explicit_resolution")
    lines.append("application=advisory_only; explicit selection and playback verification required")
    return lines


def render_creative_memory(memory):
    lines = [
        "# Auditable Creative Memory", "", f"- Memory: `{memory.memory_id}`",
        f"- Identity: `{memory.identity.scope}:{memory.identity.identity_id}`",
        f"- Display name: {memory.identity.display_name}",
        f"- Status: `{memory.status}`", f"- Entries: `{memory.entry_count}`",
        f"- Confirmed: `{memory.confirmed_count}`", f"- Requested: `{memory.requested_count}`",
        f"- Hard constraints: `{memory.hard_constraint_count}`",
        f"- Unresolved conflicts: `{memory.unresolved_conflict_count}`", "", "## Entries", "",
    ]
    for entry in memory.entries:
        lines.append(
            f"- `{entry.category}` `{entry.polarity}` `{entry.status}` "
            f"`{entry.fulfillment}`: {entry.statement}"
        )
    lines.extend(["", "## Retrieval Context", ""] + [f"- {item}" for item in memory.retrieval_context])
    if memory.conflicts:
        lines.extend(["", "## Conflicts", ""] + [f"- {item.detail}" for item in memory.conflicts])
    if memory.warnings:
        lines.extend(["", "## Warnings", ""] + [f"- {item}" for item in memory.warnings])
    lines.extend(
        [
            "", "## Guardrails", "", "- Memory applied to edit: `false`",
            "- Timeline mutated or media rendered: `false`",
            "- Automatic style/BGM selection: `false`",
            "- Model/network access by CLI: `false`", "",
        ]
    )
    return "\n".join(lines)


def _parse_instruction(raw):
    if "=" not in raw:
        raise CreativeMemoryError("memory instructions must use category=statement")
    category, statement = (part.strip() for part in raw.split("=", 1))
    if category not in CATEGORIES:
        raise CreativeMemoryError(f"unsupported memory category: {category}")
    if not statement:
        raise CreativeMemoryError("memory instruction statement must not be empty")
    return category, statement


def _entry(category, polarity, statement, strength, status, fulfillment, applicability, confidence, provenance, acceptance):
    key = f"{category}|{polarity}|{_normalize(statement)}|{applicability}"
    return CreativeMemoryEntry(
        memory_entry_id="memory_entry_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        category=category,
        polarity=polarity,
        statement=statement.strip(),
        strength=strength,
        status=status,
        fulfillment=fulfillment,
        applicability=applicability,
        confidence=confidence,
        provenance=provenance,
        acceptance_required=acceptance,
    )


def _provenance(source_type, project_id, source_ref, fingerprint, evidence_ids):
    key = f"{source_type}|{project_id}|{source_ref}|{fingerprint}|{'|'.join(evidence_ids)}"
    return MemoryProvenance(
        provenance_id="memory_provenance_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        source_type=source_type,
        project_id=project_id,
        source_ref=source_ref,
        source_fingerprint=fingerprint,
        evidence_ids=evidence_ids,
    )


def _normalize(value):
    return " ".join(value.casefold().split())


def _text_fingerprint(value):
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _read_optional(path, model):
    return model.model_validate_json(path.read_text(encoding="utf-8")) if path.exists() else None
