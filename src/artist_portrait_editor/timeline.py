from __future__ import annotations

import hashlib
import json

from artist_portrait_editor.models.clip import ClipRecord
from artist_portrait_editor.models.config import ProjectConfig
from artist_portrait_editor.models.proposal import ProposalId, ProposalSet
from artist_portrait_editor.models.source import EvidenceRef, RightsStatus, SourceRecord
from artist_portrait_editor.models.timeline import (
    AudioTransition,
    MediaRole,
    MusicSlotStatus,
    TimelineDraft,
    TimelineMusicPlan,
    TimelineSegment,
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
    selected_clips: list[tuple[ClipRecord, SourceRecord]] = []
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
        selected_clips.append((clip, source))
    if not selected_clips:
        raise TimelineBuildError("selected proposal has no required clips")

    target = float(config.creative_brief.target_duration_seconds)
    cursor = 0.0
    segments: list[TimelineSegment] = []
    risks: list[str] = []
    for index, (clip, source) in enumerate(selected_clips):
        remaining = target - cursor
        if remaining <= 0.001:
            break
        duration = min(clip.boundary.duration_seconds, remaining)
        source_in = clip.boundary.start_seconds
        source_out = source_in + duration
        media_role = (
            MediaRole.audio
            if clip.media_kind.value == "audio"
            else MediaRole.both
            if source.media_probe.audio_present
            else MediaRole.video
        )
        creative_intent = (
            proposal.minimum_viable_timeline[index % len(proposal.minimum_viable_timeline)]
            if proposal.minimum_viable_timeline
            else proposal.story_structure[index % len(proposal.story_structure)]
        )
        segments.append(
            TimelineSegment(
                segment_id=f"segment_{index + 1:03d}",
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
                reason=f"required by selected proposal {proposal_id.value}",
                evidence=[
                    EvidenceRef(type="proposal", ref=proposal_id.value),
                    EvidenceRef(type="clip", ref=clip.clip_id),
                    EvidenceRef(type="source", ref=source.source_id),
                ],
                creative_intent=creative_intent,
                confidence=clip.boundary_confidence,
            )
        )
        cursor += duration
        if source.rights_status.value == RightsStatus.permission_unknown:
            risks.append(f"rights_unknown:{source.source_id}")

    actual = round(cursor, 3)
    warnings = []
    if actual < target - 0.001:
        warnings.append(
            f"available required clips fill {actual:.3f}s of {target:.3f}s target"
        )
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
        },
        sort_keys=True,
    ).encode("utf-8")
    timeline_id = "timeline_" + hashlib.sha256(timeline_key).hexdigest()[:16]
    return TimelineDraft(
        timeline_id=timeline_id,
        project_id=config.project.id,
        proposal_set_id=proposal_set.proposal_set_id,
        proposal_id=proposal_id,
        proposal_map_fingerprint=proposal_set.map_fingerprint,
        input_fingerprint=input_fingerprint,
        target_duration=target,
        actual_duration=actual,
        segments=segments,
        music_plan=music_plan,
        evidence=[
            EvidenceRef(type="proposal_set", ref=proposal_set.proposal_set_id),
            EvidenceRef(type="proposal", ref=proposal_id.value),
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
    timeline_ref: str,
    input_fingerprint: str,
) -> TimelineValidationReport:
    issues: list[TimelineValidationIssue] = []
    clip_by_id = {clip.clip_id: clip for clip in clips}
    source_by_id = {source.source_id: source for source in sources}
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
        segment_count=len(timeline.segments),
        actual_duration=timeline.actual_duration,
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
        f"- Segments: `{report.segment_count}`",
        f"- Actual duration: `{report.actual_duration:.3f}`",
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
