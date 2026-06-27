from __future__ import annotations

import re

from artist_portrait_editor.models.proposal import ProposalRecord, ProposalSet
from artist_portrait_editor.models.proposal_context import ProposalContext
from artist_portrait_editor.models.proposal_validation import ProposalValidationIssue


def proposal_validation_issue(
    *,
    code: str,
    severity: str,
    detail: str,
    proposal_id: str | None = None,
    ref: str | None = None,
) -> ProposalValidationIssue:
    return ProposalValidationIssue(
        code=code,
        severity=severity,
        detail=detail,
        proposal_id=proposal_id,
        ref=ref,
    )


def valid_proposal_ref_index(context: ProposalContext) -> set[tuple[str, str]]:
    refs: set[tuple[str, str]] = {
        ("proposal_context", context.context_id),
        ("material_map", context.material_map_ref),
        ("source_ledger", context.sources_ref),
        ("clip_ledger", context.clips_ref),
        ("analysis_ledger", context.analysis_ref),
    }
    refs.update(("source", source.source_id) for source in context.sources)
    refs.update(("clip", clip.clip_id) for clip in context.clips)
    refs.update(("analysis", analysis.analysis_id) for analysis in context.analyses)
    return refs


def proposal_mentions_bgm(sound_structure: list[str]) -> bool:
    text = " ".join(sound_structure).lower()
    return any(token in text for token in ("bgm", "music", "score", "配乐", "音乐"))


def proposal_has_actionable_bgm_strategy(sound_structure: list[str]) -> bool:
    text = " ".join(sound_structure).lower()
    purpose_tokens = (
        "speech", "voice", "dialogue", "emotion", "energy", "pacing",
        "transition", "narrative", "人声", "对白", "情绪", "节奏", "转场", "叙事",
    )
    execution_tokens = (
        "duck", "mix", "fade", "beat", "bpm", "drop", "bar", "phrase",
        "low-interference", "silence", "loop", "压低", "混音", "淡入", "淡出",
        "节拍", "鼓点", "留白", "循环",
    )
    return (
        proposal_mentions_bgm(sound_structure)
        and any(token in text for token in purpose_tokens)
        and any(token in text for token in execution_tokens)
    )


def proposal_declares_no_added_music(sound_structure: list[str]) -> bool:
    text = " ".join(sound_structure).lower()
    return any(
        token in text
        for token in (
            "no bgm",
            "no music",
            "without music",
            "no added music",
            "original audio only",
            "voice only",
            "silence only",
            "不加配乐",
            "无配乐",
            "仅原声",
            "只用原声",
            "仅人声",
        )
    )


def proposal_uses_forbidden_generation_method(method: str) -> bool:
    normalized = re.sub(r"[\s_-]+", "", method.lower())
    return any(
        token in normalized
        for token in ("fake", "template", "mock", "modelfree", "dummy")
    )


def normalized_structure(items: list[str]) -> tuple[str, ...]:
    return tuple(" ".join(item.lower().split()) for item in items)


def contains_absolute_path(value: str) -> bool:
    return bool(
        re.search(
            r"(^|\s)(/Users/|/home/|/private/|~/|[A-Za-z]:[\\/])",
            value,
        )
    )


def proposal_text_values(proposal: ProposalRecord) -> list[str]:
    values = [
        proposal.title,
        proposal.theme,
        proposal.audience,
        *proposal.story_structure,
        *proposal.sound_structure,
        *proposal.visual_motifs,
        *proposal.risks,
        *proposal.minimum_viable_timeline,
        *proposal.missing_material,
    ]
    if proposal.counter_proposal:
        values.append(proposal.counter_proposal)
    return values


def validate_proposal_set_against_context(
    *,
    proposal_set: ProposalSet,
    context: ProposalContext,
) -> list[ProposalValidationIssue]:
    issues: list[ProposalValidationIssue] = []
    valid_clip_ids = {clip.clip_id for clip in context.clips}
    clip_by_id = {clip.clip_id: clip for clip in context.clips}
    source_by_id = {source.source_id: source for source in context.sources}
    analysis_by_id = {analysis.analysis_id: analysis for analysis in context.analyses}
    valid_refs = valid_proposal_ref_index(context)
    story_signatures: dict[tuple[str, ...], list[str]] = {}
    sound_signatures: dict[tuple[str, ...], list[str]] = {}
    visual_signatures: dict[tuple[str, ...], list[str]] = {}
    counter_signatures: dict[str, list[str]] = {}

    if proposal_uses_forbidden_generation_method(proposal_set.method):
        issues.append(proposal_validation_issue(
            code="proposal_forbidden_generation_method",
            severity="error",
            detail=(
                f"proposal method `{proposal_set.method}` is forbidden because "
                "fake, template, mock, or model-free proposal generation is closed"
            ),
            ref=proposal_set.method,
        ))
    if proposal_set.project_id != context.project_id:
        issues.append(proposal_validation_issue(
            code="proposal_project_mismatch",
            severity="error",
            detail=(
                f"proposal project_id `{proposal_set.project_id}` does not match "
                f"context project_id `{context.project_id}`"
            ),
            ref=proposal_set.project_id,
        ))
    if proposal_set.map_fingerprint != context.material_map_fingerprint:
        issues.append(proposal_validation_issue(
            code="proposal_map_fingerprint_mismatch",
            severity="error",
            detail="proposal set map_fingerprint does not match proposal context material map",
            ref=proposal_set.map_fingerprint,
        ))
    proposal_set_evidence = [
        (evidence.type, evidence.ref)
        for evidence in proposal_set.evidence
    ]
    if ("proposal_context", context.context_id) not in proposal_set_evidence:
        issues.append(proposal_validation_issue(
            code="proposal_set_missing_context_evidence",
            severity="error",
            detail="proposal set evidence must bind the current proposal context",
            ref=context.context_id,
        ))
    duplicate_set_evidence = sorted({
        ref_key
        for ref_key in proposal_set_evidence
        if proposal_set_evidence.count(ref_key) > 1
    })
    for evidence_type, evidence_ref in duplicate_set_evidence:
        issues.append(proposal_validation_issue(
            code="proposal_set_duplicate_evidence",
            severity="warning",
            detail=f"proposal set evidence `{evidence_type}:{evidence_ref}` is duplicated",
            ref=f"{evidence_type}:{evidence_ref}",
        ))
    for evidence_type, evidence_ref in proposal_set_evidence:
        if (evidence_type, evidence_ref) not in valid_refs:
            issues.append(proposal_validation_issue(
                code="proposal_set_unknown_evidence",
                severity="error",
                detail=(
                    f"proposal set evidence `{evidence_type}:{evidence_ref}` "
                    "is not valid for the current context"
                ),
                ref=f"{evidence_type}:{evidence_ref}",
            ))
        if contains_absolute_path(evidence_ref):
            issues.append(proposal_validation_issue(
                code="proposal_absolute_path_leak",
                severity="error",
                detail="proposal set evidence contains an absolute filesystem path",
                ref=evidence_ref,
            ))

    for proposal in proposal_set.proposals:
        proposal_id = proposal.proposal_id.value
        story_signatures.setdefault(normalized_structure(proposal.story_structure), []).append(
            proposal_id
        )
        sound_signatures.setdefault(normalized_structure(proposal.sound_structure), []).append(
            proposal_id
        )
        visual_signatures.setdefault(normalized_structure(proposal.visual_motifs), []).append(
            proposal_id
        )
        if proposal.counter_proposal:
            counter_signatures.setdefault(
                " ".join(proposal.counter_proposal.lower().split()),
                [],
            ).append(proposal_id)
        if proposal.theme != context.creative_brief.theme:
            issues.append(proposal_validation_issue(
                code="proposal_theme_mismatch",
                severity="error",
                detail=(
                    f"proposal theme `{proposal.theme}` does not match creative brief "
                    f"theme `{context.creative_brief.theme}`"
                ),
                proposal_id=proposal_id,
            ))
        if proposal.audience != context.creative_brief.audience:
            issues.append(proposal_validation_issue(
                code="proposal_audience_mismatch",
                severity="error",
                detail=(
                    f"proposal audience `{proposal.audience}` does not match creative "
                    f"brief audience `{context.creative_brief.audience}`"
                ),
                proposal_id=proposal_id,
            ))
        if not proposal.risks:
            issues.append(proposal_validation_issue(
                code="proposal_missing_risks",
                severity="error",
                detail="proposal must explicitly list at least one risk",
                proposal_id=proposal_id,
            ))
        if not proposal.counter_proposal or not proposal.counter_proposal.strip():
            issues.append(proposal_validation_issue(
                code="proposal_missing_counter_proposal",
                severity="error",
                detail="proposal must answer at least one counter-proposal challenge",
                proposal_id=proposal_id,
            ))
        for text_value in proposal_text_values(proposal):
            if contains_absolute_path(text_value):
                issues.append(proposal_validation_issue(
                    code="proposal_absolute_path_leak",
                    severity="error",
                    detail="proposal text contains an absolute filesystem path",
                    proposal_id=proposal_id,
                    ref=text_value,
                ))
                break
        for missing, code, detail in (
            (
                not proposal.story_structure,
                "proposal_missing_story_structure",
                "proposal must include a non-empty story_structure",
            ),
            (
                not proposal.visual_motifs,
                "proposal_missing_visual_motifs",
                "proposal must include at least one visual motif",
            ),
            (
                not proposal.minimum_viable_timeline,
                "proposal_missing_minimum_timeline",
                "proposal must describe a minimum viable timeline",
            ),
        ):
            if missing:
                issues.append(proposal_validation_issue(
                    code=code,
                    severity="error",
                    detail=detail,
                    proposal_id=proposal_id,
                ))

        if not proposal.required_clip_ids:
            issues.append(proposal_validation_issue(
                code="proposal_missing_required_clips",
                severity="error",
                detail="proposal must cite at least one required clip",
                proposal_id=proposal_id,
            ))
        duplicate_clip_ids = sorted({
            clip_id
            for clip_id in proposal.required_clip_ids
            if proposal.required_clip_ids.count(clip_id) > 1
        })
        for clip_id in duplicate_clip_ids:
            issues.append(proposal_validation_issue(
                code="proposal_duplicate_required_clip",
                severity="error",
                detail=f"required clip `{clip_id}` is listed more than once",
                proposal_id=proposal_id,
                ref=clip_id,
            ))
        for clip_id in proposal.required_clip_ids:
            if clip_id not in valid_clip_ids:
                issues.append(proposal_validation_issue(
                    code="proposal_unknown_clip_id",
                    severity="error",
                    detail=f"required clip `{clip_id}` is not present in proposal context",
                    proposal_id=proposal_id,
                    ref=clip_id,
                ))
                continue
            clip = clip_by_id[clip_id]
            source = source_by_id.get(clip.source_id)
            if source and source.forbidden_by_user:
                issues.append(proposal_validation_issue(
                    code="proposal_uses_forbidden_source",
                    severity="error",
                    detail=(
                        f"required clip `{clip_id}` belongs to forbidden source "
                        f"`{clip.source_id}`"
                    ),
                    proposal_id=proposal_id,
                    ref=clip_id,
                ))

        if not proposal.fact_refs:
            issues.append(proposal_validation_issue(
                code="proposal_missing_fact_refs",
                severity="error",
                detail="proposal must include fact_refs for traceability",
                proposal_id=proposal_id,
            ))
        fact_ref_keys = [(fact_ref.type, fact_ref.ref) for fact_ref in proposal.fact_refs]
        duplicate_fact_refs = sorted({
            ref_key for ref_key in fact_ref_keys if fact_ref_keys.count(ref_key) > 1
        })
        for fact_type, fact_ref in duplicate_fact_refs:
            issues.append(proposal_validation_issue(
                code="proposal_duplicate_fact_ref",
                severity="warning",
                detail=f"fact ref `{fact_type}:{fact_ref}` is listed more than once",
                proposal_id=proposal_id,
                ref=f"{fact_type}:{fact_ref}",
            ))
        for fact_ref in proposal.fact_refs:
            ref_key = (fact_ref.type, fact_ref.ref)
            if ref_key not in valid_refs:
                issues.append(proposal_validation_issue(
                    code="proposal_unknown_fact_ref",
                    severity="error",
                    detail=f"fact ref `{fact_ref.type}:{fact_ref.ref}` is not valid",
                    proposal_id=proposal_id,
                    ref=f"{fact_ref.type}:{fact_ref.ref}",
                ))
                continue
            if fact_ref.type == "source":
                source = source_by_id.get(fact_ref.ref)
                if source and source.forbidden_by_user:
                    issues.append(proposal_validation_issue(
                        code="proposal_fact_ref_uses_forbidden_source",
                        severity="error",
                        detail=f"source fact ref `{fact_ref.ref}` is forbidden by user",
                        proposal_id=proposal_id,
                        ref=fact_ref.ref,
                    ))
            elif fact_ref.type == "clip":
                clip = clip_by_id.get(fact_ref.ref)
                source = source_by_id.get(clip.source_id) if clip else None
                if source and source.forbidden_by_user:
                    issues.append(proposal_validation_issue(
                        code="proposal_fact_ref_uses_forbidden_clip",
                        severity="error",
                        detail=(
                            f"clip fact ref `{fact_ref.ref}` belongs to forbidden "
                            f"source `{source.source_id}`"
                        ),
                        proposal_id=proposal_id,
                        ref=fact_ref.ref,
                    ))

        fact_ref_set = set(fact_ref_keys)
        required_clip_set = {
            clip_id for clip_id in proposal.required_clip_ids if clip_id in valid_clip_ids
        }
        analysis_refs_by_clip: dict[str, set[str]] = {}
        for fact_type, fact_ref in fact_ref_set:
            if fact_type != "analysis":
                continue
            analysis = analysis_by_id.get(fact_ref)
            if analysis is None:
                continue
            analysis_refs_by_clip.setdefault(analysis.clip_id, set()).add(fact_ref)
            if analysis.clip_id not in required_clip_set:
                issues.append(proposal_validation_issue(
                    code="proposal_analysis_not_tied_to_required_clip",
                    severity="error",
                    detail=(
                        f"analysis fact ref `{fact_ref}` belongs to clip "
                        f"`{analysis.clip_id}`, which is not required by the proposal"
                    ),
                    proposal_id=proposal_id,
                    ref=fact_ref,
                ))
        for clip_id in sorted(set(proposal.required_clip_ids)):
            if ("clip", clip_id) not in fact_ref_set:
                issues.append(proposal_validation_issue(
                    code="proposal_required_clip_missing_fact_ref",
                    severity="error",
                    detail=f"required clip `{clip_id}` must also appear as a clip fact_ref",
                    proposal_id=proposal_id,
                    ref=clip_id,
                ))
        for clip_id in sorted(required_clip_set):
            if clip_id not in analysis_refs_by_clip:
                issues.append(proposal_validation_issue(
                    code="proposal_required_clip_missing_analysis_ref",
                    severity="error",
                    detail=(
                        f"required clip `{clip_id}` must have an analysis fact_ref "
                        "for evidence closure"
                    ),
                    proposal_id=proposal_id,
                    ref=clip_id,
                ))
        for evidence_type, issue_code in (
            ("clip", "proposal_missing_clip_evidence"),
            ("analysis", "proposal_missing_analysis_evidence"),
            ("material_map", "proposal_missing_material_map_evidence"),
        ):
            if not any(fact_type == evidence_type for fact_type, _ in fact_ref_set):
                issues.append(proposal_validation_issue(
                    code=issue_code,
                    severity="error",
                    detail=f"proposal must include at least one `{evidence_type}` fact_ref",
                    proposal_id=proposal_id,
                ))

        if not proposal.sound_structure:
            issues.append(proposal_validation_issue(
                code="proposal_missing_sound_structure",
                severity="error",
                detail="proposal must include sound_structure",
                proposal_id=proposal_id,
            ))
        elif not context.content_policy.allow_music:
            if not proposal_declares_no_added_music(proposal.sound_structure):
                issues.append(proposal_validation_issue(
                    code="proposal_music_policy_violation",
                    severity="error",
                    detail=(
                        "content policy forbids music; sound_structure must explicitly "
                        "state no added music and use original audio, voice, or silence"
                    ),
                    proposal_id=proposal_id,
                ))
        elif not proposal_mentions_bgm(proposal.sound_structure):
            issues.append(proposal_validation_issue(
                code="proposal_missing_bgm_strategy",
                severity="warning",
                detail="sound_structure should explicitly describe BGM/music strategy",
                proposal_id=proposal_id,
            ))
        elif not proposal_has_actionable_bgm_strategy(proposal.sound_structure):
            issues.append(proposal_validation_issue(
                code="proposal_incomplete_bgm_strategy",
                severity="warning",
                detail=(
                    "BGM strategy must state both its editorial purpose and "
                    "an execution detail such as ducking, fades, beat, BPM, or silence"
                ),
                proposal_id=proposal_id,
            ))

        existing_material_ids = {
            *valid_clip_ids,
            *source_by_id,
            *analysis_by_id,
        }
        for missing_item in proposal.missing_material:
            if missing_item.strip() in existing_material_ids:
                issues.append(proposal_validation_issue(
                    code="proposal_missing_material_already_exists",
                    severity="error",
                    detail=(
                        f"missing_material `{missing_item}` already exists in the "
                        "current proposal context"
                    ),
                    proposal_id=proposal_id,
                    ref=missing_item,
                ))

    for signature, proposal_ids in sorted(story_signatures.items()):
        if signature and len(proposal_ids) > 1:
            issues.append(proposal_validation_issue(
                code="proposal_story_structures_not_distinct",
                severity="error",
                detail=(
                    "story_structure is identical across proposals: "
                    + ", ".join(sorted(proposal_ids))
                ),
                ref="|".join(sorted(proposal_ids)),
            ))
    for signature, proposal_ids in sorted(sound_signatures.items()):
        if signature and len(proposal_ids) > 1:
            issues.append(proposal_validation_issue(
                code="proposal_sound_structures_not_distinct",
                severity="error",
                detail=(
                    "sound_structure is identical across proposals: "
                    + ", ".join(sorted(proposal_ids))
                ),
                ref="|".join(sorted(proposal_ids)),
            ))
    for signature, proposal_ids in sorted(visual_signatures.items()):
        if signature and len(proposal_ids) > 1:
            issues.append(proposal_validation_issue(
                code="proposal_visual_motifs_not_distinct",
                severity="error",
                detail=(
                    "visual_motifs are identical across proposals: "
                    + ", ".join(sorted(proposal_ids))
                ),
                ref="|".join(sorted(proposal_ids)),
            ))
    for signature, proposal_ids in sorted(counter_signatures.items()):
        if signature and len(proposal_ids) > 1:
            issues.append(proposal_validation_issue(
                code="proposal_counter_proposals_not_distinct",
                severity="error",
                detail=(
                    "counter_proposal challenge is reused across proposals: "
                    + ", ".join(sorted(proposal_ids))
                ),
                ref=signature,
            ))
    normalized_titles: dict[str, list[str]] = {}
    for proposal in proposal_set.proposals:
        normalized_titles.setdefault(
            " ".join(proposal.title.lower().split()),
            [],
        ).append(proposal.proposal_id.value)
    for title, proposal_ids in sorted(normalized_titles.items()):
        if title and len(proposal_ids) > 1:
            issues.append(proposal_validation_issue(
                code="proposal_titles_not_unique",
                severity="error",
                detail=(
                    "proposal title is reused across proposals: "
                    + ", ".join(sorted(proposal_ids))
                ),
                ref=title,
            ))
    return issues
