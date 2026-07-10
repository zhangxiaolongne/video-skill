from __future__ import annotations

import hashlib
import json

from artist_portrait_editor.models.clip import ClipRecord
from artist_portrait_editor.models.clip_score import ClipScoreRecord
from artist_portrait_editor.models.config import ProjectConfig
from artist_portrait_editor.models.edit_brief import EditBrief
from artist_portrait_editor.models.proposal import ProposalId, ProposalSet
from artist_portrait_editor.models.source import EvidenceRef, RightsStatus, SourceRecord
from artist_portrait_editor.models.timeline import (
    AudioTransition,
    MediaRole,
    MusicSlotStatus,
    TimelineContinuityCheck,
    TimelineDraft,
    TimelineDroppedClip,
    TimelineDurationVariant,
    TimelineMusicPlan,
    TimelineSegment,
    TimelineStructuralRole,
    TimelineValidationIssue,
    TimelineValidationReport,
    VideoTransition,
)


FUTURE_BGM_INPUT_MODES = [
    "direct_audio",
    "video_audio_extract",
    "source_embedded_audio",
    "multiple_candidates",
    "none_yet",
]


class TimelineBuildError(ValueError):
    pass


def build_timeline_draft(
    *,
    config: ProjectConfig,
    proposal_set: ProposalSet,
    clips: list[ClipRecord],
    sources: list[SourceRecord],
    edit_brief: EditBrief,
    edit_brief_ref: str,
    edit_brief_fingerprint: str,
    clip_scores: list[ClipScoreRecord],
    clip_scores_ref: str,
    clip_scores_fingerprint: str,
    proposal_id: ProposalId,
    input_fingerprint: str,
) -> TimelineDraft:
    proposal = next(
        (item for item in proposal_set.proposals if item.proposal_id == proposal_id),
        None,
    )
    if proposal is None:
        raise TimelineBuildError(f"selected proposal does not exist: {proposal_id.value}")

    clip_by_id = {clip.clip_id: clip for clip in clips}
    source_by_id = {source.source_id: source for source in sources}
    score_by_clip = {score.clip_id: score for score in clip_scores}
    if not score_by_clip:
        raise TimelineBuildError("timeline requires non-empty clip_scores.jsonl")

    usable_clips: list[tuple[ClipRecord, SourceRecord, ClipScoreRecord | None]] = []
    for clip_id in proposal.required_clip_ids:
        clip = clip_by_id.get(clip_id)
        if clip is None:
            raise TimelineBuildError(f"selected proposal references unknown clip: {clip_id}")
        source = source_by_id.get(clip.source_id)
        if source is None:
            raise TimelineBuildError(
                f"selected proposal clip references unknown source: {clip.source_id}"
            )
        if source.forbidden_by_user:
            raise TimelineBuildError(f"selected proposal uses forbidden source: {source.source_id}")
        if source.rights_status.value == RightsStatus.restricted:
            raise TimelineBuildError(
                f"selected proposal uses restricted-rights source: {source.source_id}"
            )
    for clip in clips:
        source = source_by_id.get(clip.source_id)
        if source is None or source.forbidden_by_user:
            continue
        if source.rights_status.value == RightsStatus.restricted:
            continue
        usable_clips.append((clip, source, score_by_clip.get(clip.clip_id)))
    if not proposal.required_clip_ids:
        raise TimelineBuildError("selected proposal has no required clips")
    if not usable_clips:
        raise TimelineBuildError("timeline has no usable clips after source policy checks")

    target = float(edit_brief.selected_duration_seconds)
    selected_clips = _select_aesthetic_clips(
        usable_clips=usable_clips,
        required_clip_ids=proposal.required_clip_ids,
        target_duration=target,
    )
    cursor = 0.0
    segments: list[TimelineSegment] = []
    risks: list[str] = []
    used_ranges_by_clip: dict[str, float] = {}
    segment_specs = _role_segment_specs(selected_clips, target)
    for index, (role, clip, source, score, desired_duration) in enumerate(segment_specs):
        remaining_target = target - cursor
        remaining_clip = clip.boundary.end_seconds - used_ranges_by_clip.get(
            clip.clip_id,
            clip.boundary.start_seconds,
        )
        duration = min(desired_duration, remaining_target, remaining_clip)
        if duration <= 0.001:
            continue
        source_in = used_ranges_by_clip.get(clip.clip_id, clip.boundary.start_seconds)
        source_out = source_in + duration
        used_ranges_by_clip[clip.clip_id] = source_out
        media_role = (
            MediaRole.audio
            if clip.media_kind.value == "audio"
            else MediaRole.both
            if source.media_probe.audio_present
            else MediaRole.video
        )
        creative_intent = _creative_intent_for_role(
            role=role,
            proposal_structure=proposal.story_structure,
            brief_intent=edit_brief.edit_intent,
        )
        score_reason = _score_keep_reason(score)
        segments.append(
            TimelineSegment(
                segment_id=f"segment_{index + 1:03d}",
                structural_role=role,
                timeline_start=round(cursor, 3),
                timeline_end=round(cursor + duration, 3),
                clip_id=clip.clip_id,
                source_id=source.source_id,
                source_in=round(source_in, 3),
                source_out=round(source_out, 3),
                track_id="A1" if media_role == MediaRole.audio else "V1",
                media_role=media_role,
                video_transition=(
                    VideoTransition.none
                    if media_role == MediaRole.audio
                    else VideoTransition.fade_in
                    if index == 0
                    else VideoTransition.hard_cut
                ),
                audio_transition=(
                    AudioTransition.fade_in if index == 0 else AudioTransition.cut
                )
                if media_role in {MediaRole.audio, MediaRole.both}
                else AudioTransition.none,
                reason=(
                    f"{role.value} selected for {proposal_id.value}; "
                    f"{score_reason}"
                ),
                evidence=[
                    EvidenceRef(type="proposal", ref=proposal_id.value),
                    EvidenceRef(type="clip", ref=clip.clip_id),
                    EvidenceRef(type="source", ref=source.source_id),
                    *(
                        [EvidenceRef(type="clip_score", ref=score.clip_score_id)]
                        if score is not None
                        else []
                    ),
                ],
                creative_intent=creative_intent,
                confidence=_segment_confidence(clip, score),
                clip_score_id=score.clip_score_id if score is not None else None,
                clip_overall_score=score.overall_score if score is not None else None,
                selection_tier=score.selection_tier if score is not None else None,
                keep_reason=score_reason,
                continuity_note="first segment" if index == 0 else "checked in continuity_checks",
            )
        )
        cursor += duration
        if source.rights_status.value == RightsStatus.permission_unknown:
            risks.append(f"rights_unknown:{source.source_id}")

    actual = round(cursor, 3)
    warnings = []
    if actual < target - 0.001:
        warnings.append(
            f"available selected clips fill {actual:.3f}s of {target:.3f}s target"
        )
    roles_present = {segment.structural_role.value for segment in segments}
    for role in ("hook", "build", "payoff"):
        if role not in roles_present:
            warnings.append(f"timeline lacks {role} segment because usable scored media is insufficient")
    allow_music = config.content_policy.allow_music
    music_plan = TimelineMusicPlan(
        status=(
            MusicSlotStatus.unresolved
            if allow_music
            else MusicSlotStatus.disabled_by_policy
        ),
        input_mode="none_yet" if allow_music else "disabled_by_policy",
        proposal_sound_structure=proposal.sound_structure,
        future_input_modes=FUTURE_BGM_INPUT_MODES,
    )
    timeline_key = json.dumps(
        {
            "project_id": config.project.id,
            "proposal_set_id": proposal_set.proposal_set_id,
            "proposal_id": proposal_id.value,
            "input_fingerprint": input_fingerprint,
            "edit_brief_fingerprint": edit_brief_fingerprint,
            "clip_scores_fingerprint": clip_scores_fingerprint,
        },
        sort_keys=True,
    ).encode("utf-8")
    timeline_id = "timeline_" + hashlib.sha256(timeline_key).hexdigest()[:16]
    dropped_clips = _dropped_clips(
        usable_clips=usable_clips,
        used_clip_ids={segment.clip_id for segment in segments},
        required_clip_ids=set(proposal.required_clip_ids),
    )
    continuity_checks = _continuity_checks(segments)
    return TimelineDraft(
        timeline_id=timeline_id,
        project_id=config.project.id,
        proposal_set_id=proposal_set.proposal_set_id,
        proposal_id=proposal_id,
        proposal_map_fingerprint=proposal_set.map_fingerprint,
        edit_brief_ref=edit_brief_ref,
        edit_brief_fingerprint=edit_brief_fingerprint,
        clip_scores_ref=clip_scores_ref,
        clip_scores_fingerprint=clip_scores_fingerprint,
        input_fingerprint=input_fingerprint,
        target_duration=target,
        actual_duration=actual,
        selected_duration_option_id=edit_brief.selected_option_id,
        structure_strategy=[
            "score-aware hook/build/payoff slotting",
            "required proposal clips remain eligible and protected from dropping",
            "support clips may be added only from local clip-score evidence",
            "visual semantics are not inferred beyond local ledger evidence",
        ],
        duration_variants=_duration_variants(edit_brief, available_duration=sum(
            clip.boundary.duration_seconds for clip, _, _ in usable_clips
        )),
        segments=segments,
        dropped_clips=dropped_clips,
        continuity_checks=continuity_checks,
        music_plan=music_plan,
        evidence=[
            EvidenceRef(type="proposal_set", ref=proposal_set.proposal_set_id),
            EvidenceRef(type="proposal", ref=proposal_id.value),
            EvidenceRef(type="edit_brief", ref=edit_brief_ref),
            EvidenceRef(type="clip_scores", ref=clip_scores_ref),
        ],
        risks=sorted(set(risks)),
        warnings=warnings,
    )


def validate_timeline_draft(
    *,
    timeline: TimelineDraft,
    proposal_set: ProposalSet,
    clips: list[ClipRecord],
    sources: list[SourceRecord],
    edit_brief: EditBrief | None = None,
    clip_scores: list[ClipScoreRecord] | None = None,
    timeline_ref: str,
    input_fingerprint: str,
) -> TimelineValidationReport:
    issues: list[TimelineValidationIssue] = []
    clip_by_id = {clip.clip_id: clip for clip in clips}
    source_by_id = {source.source_id: source for source in sources}
    score_by_clip = {score.clip_id: score for score in (clip_scores or [])}
    proposal = next(
        (item for item in proposal_set.proposals if item.proposal_id == timeline.proposal_id),
        None,
    )
    if proposal is None:
        issues.append(_issue("timeline_unknown_proposal", "error", "proposal does not exist"))
    elif timeline.proposal_set_id != proposal_set.proposal_set_id:
        issues.append(
            _issue("timeline_proposal_set_mismatch", "error", "proposal set binding changed")
        )
    elif timeline.proposal_map_fingerprint != proposal_set.map_fingerprint:
        issues.append(
            _issue("timeline_map_fingerprint_mismatch", "error", "material map binding changed")
        )

    seen_required: set[str] = set()
    by_track: dict[str, list] = {}
    for segment in timeline.segments:
        by_track.setdefault(segment.track_id, []).append(segment)
        clip = clip_by_id.get(segment.clip_id)
        source = source_by_id.get(segment.source_id)
        if clip is None:
            issues.append(
                _issue(
                    "timeline_unknown_clip",
                    "error",
                    f"unknown clip {segment.clip_id}",
                    segment.segment_id,
                )
            )
            continue
        seen_required.add(segment.clip_id)
        if source is None or clip.source_id != segment.source_id:
            issues.append(
                _issue(
                    "timeline_source_mismatch",
                    "error",
                    f"source mismatch for {segment.clip_id}",
                    segment.segment_id,
                )
            )
            continue
        if source.forbidden_by_user:
            issues.append(
                _issue(
                    "timeline_forbidden_source",
                    "error",
                    f"forbidden source {source.source_id}",
                    segment.segment_id,
                )
            )
        if source.rights_status.value == RightsStatus.restricted:
            issues.append(
                _issue(
                    "timeline_restricted_rights",
                    "error",
                    f"restricted source {source.source_id}",
                    segment.segment_id,
                )
            )
        elif source.rights_status.value == RightsStatus.permission_unknown:
            issues.append(
                _issue(
                    "timeline_rights_unknown",
                    "warning",
                    f"rights unknown for {source.source_id}",
                    segment.segment_id,
                )
            )
        if (
            segment.source_in < clip.boundary.start_seconds - 0.001
            or segment.source_out > clip.boundary.end_seconds + 0.001
        ):
            issues.append(
                _issue(
                    "timeline_source_range_out_of_bounds",
                    "error",
                    f"source range exceeds clip {segment.clip_id}",
                    segment.segment_id,
                )
            )
        if clip_scores is not None:
            score = score_by_clip.get(segment.clip_id)
            if score is None:
                issues.append(
                    _issue(
                        "timeline_segment_missing_score",
                        "warning",
                        f"segment has no current clip score for {segment.clip_id}",
                        segment.segment_id,
                    )
                )
            elif segment.clip_score_id and segment.clip_score_id != score.clip_score_id:
                issues.append(
                    _issue(
                        "timeline_score_binding_mismatch",
                        "error",
                        f"score binding changed for {segment.clip_id}",
                        segment.segment_id,
                    )
                )
    if proposal is not None:
        missing = set(proposal.required_clip_ids) - seen_required
        if missing:
            issues.append(
                _issue(
                    "timeline_missing_required_clip",
                    "error",
                    "missing required clips: " + ", ".join(sorted(missing)),
                )
            )
    for track_id, segments in by_track.items():
        ordered = sorted(segments, key=lambda item: item.timeline_start)
        for previous, current in zip(ordered, ordered[1:]):
            if current.timeline_start < previous.timeline_end - 0.001:
                issues.append(
                    _issue(
                        "timeline_unexplained_overlap",
                        "error",
                        f"overlap on track {track_id}",
                        current.segment_id,
                    )
                )
    if edit_brief is not None:
        if timeline.selected_duration_option_id != edit_brief.selected_option_id:
            issues.append(
                _issue("timeline_edit_brief_option_mismatch", "error", "selected duration option changed")
            )
        if abs(timeline.target_duration - edit_brief.selected_duration_seconds) > 0.001:
            issues.append(
                _issue("timeline_edit_brief_duration_mismatch", "error", "target duration changed")
            )
    roles_present = {segment.structural_role.value for segment in timeline.segments}
    missing_roles = {"hook", "build", "payoff"} - roles_present
    if missing_roles:
        issues.append(
            _issue(
                "timeline_incomplete_story_arc",
                "warning",
                "missing structural roles: " + ", ".join(sorted(missing_roles)),
            )
        )
    if not timeline.duration_variants:
        issues.append(_issue("timeline_duration_variants_missing", "warning", "no duration variants recorded"))
    if len(timeline.segments) > 1 and not timeline.continuity_checks:
        issues.append(_issue("timeline_continuity_checks_missing", "warning", "multi-segment timeline lacks continuity checks"))
    if not timeline.no_fabricated_content_claims:
        issues.append(_issue("timeline_fabrication_flag", "error", "timeline claims fabricated content understanding"))
    if timeline.music_plan.status.value == "fitted":
        if not timeline.music_plan.selection_performed:
            issues.append(_issue("timeline_bgm_selection_missing", "error", "fitted music has no explicit selection"))
        if not timeline.music_plan.fitting_performed:
            issues.append(_issue("timeline_bgm_fit_state_missing", "error", "fitted music has no fit state"))
        if not timeline.music_plan.candidate_id or not timeline.music_plan.fit_ref:
            issues.append(_issue("timeline_bgm_fit_binding_missing", "error", "fitted music lacks candidate or fit reference"))
    elif timeline.music_plan.selection_performed or timeline.music_plan.fitting_performed:
        issues.append(_issue("timeline_bgm_state_inconsistent", "error", "unfitted music slot claims selection or fitting"))

    errors = sum(issue.severity == "error" for issue in issues)
    warnings = sum(issue.severity == "warning" for issue in issues)
    return TimelineValidationReport(
        timeline_ref=timeline_ref,
        input_fingerprint=input_fingerprint,
        proposal_id=timeline.proposal_id,
        edit_brief_ref=timeline.edit_brief_ref,
        clip_scores_ref=timeline.clip_scores_ref,
        segment_count=len(timeline.segments),
        actual_duration=timeline.actual_duration,
        structural_roles_present=sorted(roles_present),
        dropped_clip_count=len(timeline.dropped_clips),
        continuity_check_count=len(timeline.continuity_checks),
        issues=issues,
        issue_count=len(issues),
        error_count=errors,
        warning_count=warnings,
        valid=errors == 0,
    )


def render_timeline_review(report: TimelineValidationReport) -> str:
    lines = [
        "# Timeline Review",
        "",
        f"- Timeline: `{report.timeline_ref}`",
        f"- Proposal: `{report.proposal_id.value}`",
        f"- Edit brief: `{report.edit_brief_ref or 'not bound'}`",
        f"- Clip scores: `{report.clip_scores_ref or 'not bound'}`",
        f"- Segments: `{report.segment_count}`",
        f"- Actual duration: `{report.actual_duration:.3f}`",
        f"- Structural roles: `{', '.join(report.structural_roles_present) or 'none'}`",
        f"- Dropped clips: `{report.dropped_clip_count}`",
        f"- Continuity checks: `{report.continuity_check_count}`",
        f"- Valid: `{str(report.valid).lower()}`",
        f"- Errors: `{report.error_count}`",
        f"- Warnings: `{report.warning_count}`",
        "",
        "## Issues",
        "",
    ]
    if not report.issues:
        lines.append("- None")
    else:
        for issue in report.issues:
            segment = f" segment `{issue.segment_id}`" if issue.segment_id else ""
            lines.append(
                f"- `{issue.severity}` `{issue.code}`{segment}: {issue.detail}"
            )
    return "\n".join(lines) + "\n"


def _issue(
    code: str,
    severity: str,
    detail: str,
    segment_id: str | None = None,
) -> TimelineValidationIssue:
    return TimelineValidationIssue(
        code=code,
        severity=severity,
        detail=detail,
        segment_id=segment_id,
    )


def _select_aesthetic_clips(
    *,
    usable_clips: list[tuple[ClipRecord, SourceRecord, ClipScoreRecord | None]],
    required_clip_ids: list[str],
    target_duration: float,
) -> list[tuple[ClipRecord, SourceRecord, ClipScoreRecord | None]]:
    required = set(required_clip_ids)
    ordered = sorted(
        usable_clips,
        key=lambda item: (
            0 if item[0].clip_id in required else 1,
            -_score_value(item[2]),
            item[0].boundary.start_seconds,
            item[0].clip_id,
        ),
    )
    selected: list[tuple[ClipRecord, SourceRecord, ClipScoreRecord | None]] = []
    duration = 0.0
    for item in ordered:
        clip, _, score = item
        if clip.clip_id in required or _score_value(score) >= 0.45 or duration < target_duration:
            selected.append(item)
            duration += clip.boundary.duration_seconds
        if duration >= target_duration and all(
            clip_id in {selected_clip.clip_id for selected_clip, _, _ in selected}
            for clip_id in required
        ):
            break
    return selected or ordered[:1]


def _role_segment_specs(
    selected_clips: list[tuple[ClipRecord, SourceRecord, ClipScoreRecord | None]],
    target_duration: float,
) -> list[tuple[TimelineStructuralRole, ClipRecord, SourceRecord, ClipScoreRecord | None, float]]:
    roles = [
        (TimelineStructuralRole.hook, 0.25),
        (TimelineStructuralRole.build, 0.50),
        (TimelineStructuralRole.payoff, 0.25),
    ]
    if target_duration < 1.2:
        roles = [
            (TimelineStructuralRole.hook, 0.35),
            (TimelineStructuralRole.payoff, 0.65),
        ]
    specs: list[tuple[TimelineStructuralRole, ClipRecord, SourceRecord, ClipScoreRecord | None, float]] = []
    durations = _quantized_role_durations(target_duration, [ratio for _, ratio in roles])
    for index, (role, _ratio) in enumerate(roles):
        clip, source, score = selected_clips[min(index, len(selected_clips) - 1)]
        specs.append((role, clip, source, score, durations[index]))
    return specs


def _creative_intent_for_role(
    *,
    role: TimelineStructuralRole,
    proposal_structure: list[str],
    brief_intent: list[str],
) -> str:
    source = proposal_structure or brief_intent
    fallback = {
        TimelineStructuralRole.hook: "open with the highest-evidence portrait moment",
        TimelineStructuralRole.build: "develop the portrait through scored supporting evidence",
        TimelineStructuralRole.payoff: "close on the clearest emotional or informational beat",
    }
    if not source:
        return fallback.get(role, "support the selected portrait structure")
    if role == TimelineStructuralRole.hook:
        return source[0]
    if role == TimelineStructuralRole.payoff:
        return source[-1]
    return source[min(1, len(source) - 1)]


def _score_keep_reason(score: ClipScoreRecord | None) -> str:
    if score is None:
        return "no score binding available; kept only because proposal required local clip evidence"
    reasons = "; ".join(score.reasons[:2]) if score.reasons else "local score evidence available"
    return (
        f"score {score.overall_score:.3f}, tier {score.selection_tier}, "
        f"recommendation {score.keep_recommendation}: {reasons}"
    )


def _segment_confidence(clip: ClipRecord, score: ClipScoreRecord | None) -> float:
    if score is None:
        return clip.boundary_confidence
    return round((clip.boundary_confidence * 0.45) + (score.overall_score * 0.55), 3)


def _score_value(score: ClipScoreRecord | None) -> float:
    return score.overall_score if score is not None else 0.0


def _dropped_clips(
    *,
    usable_clips: list[tuple[ClipRecord, SourceRecord, ClipScoreRecord | None]],
    used_clip_ids: set[str],
    required_clip_ids: set[str],
) -> list[TimelineDroppedClip]:
    dropped: list[TimelineDroppedClip] = []
    for clip, source, score in sorted(
        usable_clips,
        key=lambda item: (item[0].source_location, item[0].boundary.start_seconds, item[0].clip_id),
    ):
        if clip.clip_id in used_clip_ids:
            continue
        if clip.clip_id in required_clip_ids:
            reason = "required clip could not fit after higher-priority structural slots"
        elif score is None:
            reason = "not selected because no clip-score evidence was available"
        elif score.keep_recommendation == "drop":
            reason = "not selected because clip score recommends drop"
        else:
            reason = "not selected because target duration was filled by higher-scoring structural material"
        dropped.append(
            TimelineDroppedClip(
                clip_id=clip.clip_id,
                source_id=source.source_id,
                selection_tier=score.selection_tier if score is not None else None,
                overall_score=score.overall_score if score is not None else None,
                reason=reason,
            )
        )
    return dropped


def _continuity_checks(segments: list[TimelineSegment]) -> list[TimelineContinuityCheck]:
    checks: list[TimelineContinuityCheck] = []
    ordered = sorted(segments, key=lambda item: item.timeline_start)
    for previous, current in zip(ordered, ordered[1:]):
        if previous.media_role == MediaRole.audio or current.media_role == MediaRole.audio:
            status = "audio_only_transition"
            detail = "audio-only transition; visual continuity not applicable"
            risk = "low"
        elif previous.source_id != current.source_id:
            status = "cross_source_cut"
            detail = f"cut crosses from {previous.source_id} to {current.source_id}"
            risk = "medium"
        elif abs(previous.source_out - current.source_in) <= 0.05:
            status = "same_source_continuous"
            detail = "same source range continues without a visible source jump"
            risk = "low"
        else:
            status = "same_source_jump"
            detail = "same source resumes from a non-contiguous range"
            risk = "medium"
        checks.append(
            TimelineContinuityCheck(
                from_segment_id=previous.segment_id,
                to_segment_id=current.segment_id,
                status=status,
                detail=detail,
                risk_level=risk,
            )
        )
    return checks


def _duration_variants(edit_brief: EditBrief, *, available_duration: float) -> list[TimelineDurationVariant]:
    variants: list[TimelineDurationVariant] = []
    for option in edit_brief.duration_options:
        target = option.duration_seconds
        estimated = min(target, available_duration)
        variants.append(
            TimelineDurationVariant(
                option_id=option.option_id,
                label=option.label,
                target_duration=target,
                estimated_duration=round(estimated, 3),
                role_allocation={
                    "hook": round(target * 0.25, 3),
                    "build": round(target * 0.50, 3),
                    "payoff": round(target * 0.25, 3),
                },
                rationale=[
                    *option.rationale,
                    "variant kept inside canonical timeline_draft.json under V1 JSON governance",
                ],
                risks=option.risks,
            )
        )
    return variants


def _quantized_role_durations(target_duration: float, ratios: list[float]) -> list[float]:
    raw = [target_duration * ratio for ratio in ratios]
    durations = [max(0.1, round(value, 1)) for value in raw]
    delta = round(target_duration - sum(durations), 3)
    durations[-1] = max(0.1, round(durations[-1] + delta, 3))
    return durations
