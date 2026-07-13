from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.revision_application import RevisionApplication
from artist_portrait_editor.models.second_cut_render import SecondCutRender
from artist_portrait_editor.models.state import ActiveMode, OverallStatus, StepLedgerEntry, StepStatus
from artist_portrait_editor.models.timeline import TimelineDraft
from artist_portrait_editor.models.version_review import (
    GoalAdvantage, ReviewedVersion, VersionDomainAssessment, VersionPairComparison, VersionReview,
)
from artist_portrait_editor.run_records import environment_snapshot, new_run_id, utc_now, write_json
from artist_portrait_editor.workspace_errors import WorkspacePrerequisiteError
from artist_portrait_editor.workspace_state import atomic_write_text, load_state, project_root, save_state, write_run_report


class VersionReviewError(RuntimeError):
    pass


DOMAINS = ("hook", "emotional_arc", "information_density", "bgm_conflict", "text_burden", "ending_strength", "platform_fit")
GOALS = {
    "fast_hook": "hook", "emotional_depth": "emotional_arc", "information_clarity": "information_density",
    "voice_first": "bgm_conflict", "text_light": "text_burden", "strong_ending": "ending_strength",
    "platform_delivery": "platform_fit",
}


def build_version_review_workspace(project_path: Path) -> tuple[Path, Path, VersionReview, list[str]]:
    config = load_project_config(project_path); root = project_root(project_path); state = load_state(root)
    if state is None: raise WorkspacePrerequisiteError("version-review requires init to complete first")
    data = root / WORKSPACE_DIR / DATA_DIR
    timeline_path = root / "output" / "timeline_draft.json"
    if not timeline_path.exists(): raise WorkspacePrerequisiteError("version-review requires output/timeline_draft.json")
    timeline = TimelineDraft.model_validate_json(timeline_path.read_text(encoding="utf-8"))
    if timeline.project_id != config.project.id: raise VersionReviewError("timeline project_id mismatches project config")
    versions = [_from_timeline(timeline, timeline_path, root)]
    second_path = data / "second_cut_render.json"
    if second_path.exists():
        second = SecondCutRender.model_validate_json(second_path.read_text(encoding="utf-8"))
        if second.project_id != config.project.id: raise VersionReviewError("second cut project_id mismatches project config")
        versions.append(_from_second_cut(second, second_path, root))
    revision_path = data / "revision_application.json"
    if revision_path.exists():
        revision = RevisionApplication.model_validate_json(revision_path.read_text(encoding="utf-8"))
        if revision.project_id != config.project.id: raise VersionReviewError("revision application project_id mismatches project config")
        versions.append(_from_revision(revision, revision_path, root, _fingerprint(timeline_path)))
    if len(versions) < 2: raise WorkspacePrerequisiteError("version-review requires at least two existing versions")
    review = build_version_review(config.project.id, versions)
    json_path = data / "version_review.json"; md_path = root / "output" / "version_review.md"
    atomic_write_text(json_path, json.dumps(review.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    atomic_write_text(md_path, render_version_review(review))
    warnings = review.warnings; run_id = new_run_id(); status = StepStatus.completed_with_warnings if warnings else StepStatus.completed
    state.steps["version_review"] = StepLedgerEntry(status=status, input_fingerprint=_fingerprint_many([timeline_path, second_path, revision_path]), output_refs=[json_path.relative_to(root).as_posix(), md_path.relative_to(root).as_posix()], last_run_id=run_id, warnings=warnings)
    state.active_mode = ActiveMode.creative; state.latest_run_id = run_id; state.updated_at = utc_now(); state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready
    runs = root / WORKSPACE_DIR / RUNS_DIR / run_id; runs.mkdir(parents=True, exist_ok=True)
    write_json(runs / "command.json", {"command": "version-review", "project": str(project_path)})
    write_json(runs / "environment.json", environment_snapshot())
    write_json(runs / "step_result.json", {"step": "version_review", "status": status.value, "output_refs": state.steps["version_review"].output_refs, "warnings": warnings})
    save_state(root, state); write_run_report(root / config.paths.output_dir, state, warnings)
    return json_path, md_path, review, warnings


def build_version_review(project_id: str, versions: list[ReviewedVersion]) -> VersionReview:
    pairs = [_compare(left, right) for left, right in itertools.combinations(versions, 2)]
    goals = [_goal_advantage(goal, domain, versions) for goal, domain in GOALS.items()]
    warnings = sorted({warning for version in versions for warning in version.warnings})
    if any(version.evidence_level != "rendered_media" for version in versions):
        warnings.append("plan/timeline candidates are not equivalent to rendered playback evidence")
    key = project_id + "|" + "|".join(item.artifact_fingerprint for item in versions)
    return VersionReview(review_id="version_review_" + hashlib.sha256(key.encode()).hexdigest()[:20], project_id=project_id, status="warning" if warnings else "ready", version_count=len(versions), versions=versions, pairwise_comparisons=pairs, goal_advantages=goals, warnings=warnings)


def _from_timeline(timeline: TimelineDraft, path: Path, root: Path) -> ReviewedVersion:
    segments = timeline.segments; duration = timeline.actual_duration
    scores = [item.clip_overall_score for item in segments if item.clip_overall_score is not None]
    hook = segments[0]; ending = segments[-1]
    assessments = [
        _a("hook", hook.clip_overall_score, .55 if hook.clip_overall_score is not None else 0, "Opening uses the canonical first segment; score is a clip proxy, not playback judgment.", [hook.segment_id]),
        _a("emotional_arc", sum(scores)/len(scores) if scores else None, .3 if scores else 0, "Clip scores provide only a weak proxy for emotional development.", [path.name], ["no host-reviewed emotional arc binding"]),
        _a("information_density", min(1, len(segments)/(duration/60)/12), .55, f"{len(segments)} segments across {duration:.2f}s.", [path.name]),
        _a("bgm_conflict", None, 0, "Candidate-specific BGM/voice conflict is unavailable from timeline structure alone.", [], ["requires rendered audio or current candidate-specific sound review"]),
        _a("text_burden", None, 0, "Candidate-specific burned or timed text burden is unavailable.", [], ["requires candidate-specific text evidence"]),
        _a("ending_strength", .7 if ending.structural_role.value == "payoff" else .4, .45, f"Final segment role is {ending.structural_role.value}; role is not playback strength.", [ending.segment_id]),
        _a("platform_fit", max(0, 1-abs(duration-timeline.target_duration)/max(timeline.target_duration,1)), .8, "Duration is compared with the explicit timeline target.", [path.name]),
    ]
    return _version("canonical_timeline", "canonical_timeline", path, root, "timeline_candidate", duration, len(segments), None, True, assessments)


def _from_second_cut(cut: SecondCutRender, path: Path, root: Path) -> ReviewedVersion:
    output_path = root / cut.output_ref
    output_current = output_path.exists() and _fingerprint(output_path) == cut.output_hash
    segs = cut.candidate_timeline; duration = cut.actual_duration_seconds; scores = [x.ranking_score for x in segs]
    comparison = {x.domain: x for x in cut.comparisons}
    assessments = [
        _a("hook", segs[0].ranking_score if segs[0].role == "hook" else .35, segs[0].ranking_confidence, "Rendered second cut begins with an explicitly ranked hook candidate.", [segs[0].segment_id, cut.output_ref]),
        _a("emotional_arc", sum(scores)/len(scores), min(x.ranking_confidence for x in segs), "Ranking continuity is a proxy; no invented emotion claim is made.", [cut.editorial_scores_ref], ["semantic emotion may remain degraded"]),
        _a("information_density", min(1, len(segs)/(duration/60)/12), .75, f"{len(segs)} ranked segments across {duration:.2f}s.", [cut.output_ref]),
        _a("bgm_conflict", .75 if cut.source_audio_retained and not cut.added_bgm_applied else .45, .75, "Rendered audio state distinguishes retained source audio from added BGM.", [cut.output_ref, cut.bgm_match_ref]),
        _a("text_burden", .85 if not cut.text_applied else .55, .9, "Text application state is recorded on the rendered candidate.", [cut.text_plan_ref, cut.output_ref]),
        _a("ending_strength", _comparison_score(comparison.get("ending")), .7, comparison.get("ending").finding if comparison.get("ending") else "Ending review unavailable.", [cut.output_ref]),
        _a("platform_fit", max(0, 1-abs(cut.duration_delta_seconds)/max(cut.target_duration_seconds,1)) if cut.media_valid else .2, .95, "Rendered duration and media validity are compared with the explicit target.", [cut.output_ref]),
    ]
    warnings = list(cut.warnings)
    if not output_current: warnings.append("second-cut media is missing or its hash is stale")
    return _version(cut.render_id, "rendered_second_cut", path, root, "rendered_media", duration, len(segs), cut.media_valid and output_current, False, assessments, warnings)


def _from_revision(app: RevisionApplication, path: Path, root: Path, timeline_fingerprint: str) -> ReviewedVersion:
    segs = app.revised_segments; duration = app.revised_duration_seconds
    manual_domains = {out.domain for out in app.semantic_outcomes if out.status in {"manual_only", "blocked", "not_selected"}}
    def semantic(domain: str) -> tuple[float | None, float, list[str]]:
        return (None, 0, [f"{domain} revision remains manual or unverified"]) if domain in manual_domains else (.6, .45, ["candidate edit state is not rendered playback"])
    emotion, emotion_c, emotion_l = semantic("emotion"); bgm, bgm_c, bgm_l = semantic("source_audio"); text, text_c, text_l = semantic("text"); ending, ending_c, ending_l = semantic("ending")
    assessments = [
        _a("hook", .55 if any(x.status == "moved" for x in app.segment_changes) else .45, .4, "Hook score reflects candidate movement only; playback remains unavailable.", [path.name]),
        _a("emotional_arc", emotion, emotion_c, "Revision semantic outcome is used without claiming emotional playback success.", [path.name], emotion_l),
        _a("information_density", min(1, len(segs)/(duration/60)/12), .6, f"Candidate has {len(segs)} segments across {duration:.2f}s.", [path.name]),
        _a("bgm_conflict", bgm, bgm_c, "Voice/BGM semantics are tracked but require rendered audio verification.", [path.name], bgm_l),
        _a("text_burden", text, text_c, "Text semantics are tracked but require rendered frame verification.", [path.name], text_l),
        _a("ending_strength", ending, ending_c, "Ending semantics are tracked but require playback verification.", [path.name], ending_l),
        _a("platform_fit", .7, .5, "Candidate duration is known; media and platform playback are not.", [path.name], ["revision candidate is not rendered"]),
    ]
    warnings = list(app.warnings)
    if app.baseline_timeline_fingerprint != timeline_fingerprint:
        warnings.append("revision candidate baseline timeline fingerprint is stale")
        for assessment in assessments:
            assessment.confidence = 0
            assessment.status = "unavailable"
            assessment.score = None
            assessment.limitations.append("stale baseline timeline")
    return _version(app.revision_application_id, "revision_candidate", path, root, "plan_only", duration, len(segs), None, False, assessments, warnings)


def _a(domain, score, confidence, finding, refs, limits=None):
    return VersionDomainAssessment(domain=domain, status="unavailable" if score is None else "partial" if limits else "known", score=score, confidence=confidence, finding=finding, evidence_refs=refs, limitations=limits or [])


def _version(version_id, kind, path, root, level, duration, count, media_valid, current, assessments, warnings=None):
    return ReviewedVersion(version_id=version_id, version_kind=kind, artifact_ref=path.relative_to(root).as_posix(), artifact_fingerprint=_fingerprint(path), evidence_level=level, duration_seconds=duration, segment_count=count, media_valid=media_valid, current=current, assessments=assessments, unresolved_domains=[a.domain for a in assessments if a.status == "unavailable"], warnings=warnings or [])


def _compare(left: ReviewedVersion, right: ReviewedVersion) -> VersionPairComparison:
    lm={a.domain:a for a in left.assessments}; rm={a.domain:a for a in right.assessments}; comparable=[]; la=[]; ra=[]; unresolved=[]
    for domain in DOMAINS:
        l,r=lm[domain],rm[domain]
        if l.score is None or r.score is None or min(l.confidence, r.confidence) < .5:
            unresolved.append(domain); continue
        comparable.append(domain); delta=l.score-r.score
        if delta >= .08: la.append(domain)
        elif delta <= -.08: ra.append(domain)
    return VersionPairComparison(left_version_id=left.version_id,right_version_id=right.version_id,comparable_domains=comparable,left_advantages=la,right_advantages=ra,unresolved_domains=unresolved,tradeoff_summary=f"{left.version_id} leads {len(la)} domains; {right.version_id} leads {len(ra)}; {len(unresolved)} remain unresolved. No overall winner is selected.")


def _goal_advantage(goal, domain, versions):
    known=[(v,next(a for a in v.assessments if a.domain==domain)) for v in versions]
    known=[x for x in known if x[1].score is not None and x[1].confidence >= .5]
    if len(known) < 2:
        return GoalAdvantage(goal=goal,status="unavailable",rationale=f"Fewer than two versions have sufficiently reliable {domain} evidence.",confidence=0)
    best=max(a.score for _,a in known); leaders=[v.version_id for v,a in known if best-a.score < .05]; confidence=min(a.confidence for v,a in known if v.version_id in leaders)
    return GoalAdvantage(goal=goal,leading_version_ids=leaders,status="tie" if len(leaders)>1 else "supported",rationale=f"Leaders have the strongest available {domain} evidence; this is goal-specific, not an overall selection.",confidence=confidence)


def render_version_review(review: VersionReview) -> str:
    lines=["# A/B Version Review","",f"- Status: `{review.status}`",f"- Versions: `{review.version_count}`","- Overall winner: `none`","- Explicit selection required: `true`","","## Versions",""]
    for v in review.versions:
        lines += [f"### {v.version_id}","",f"- Kind: `{v.version_kind}`",f"- Evidence: `{v.evidence_level}`",f"- Duration: `{v.duration_seconds:.2f}s`",f"- Media valid: `{v.media_valid}`",""]
        for a in v.assessments: lines.append(f"- `{a.domain}`: `{a.status}` score `{a.score}` confidence `{a.confidence:.2f}`; {a.finding}")
        lines.append("")
    lines += ["## Pairwise Tradeoffs",""]
    for p in review.pairwise_comparisons: lines.append(f"- `{p.left_version_id}` vs `{p.right_version_id}`: {p.tradeoff_summary}")
    lines += ["","## Goal-Specific Advantages",""]
    for g in review.goal_advantages: lines.append(f"- `{g.goal}`: `{g.status}` -> `{', '.join(g.leading_version_ids) or 'none'}`; confidence `{g.confidence:.2f}`")
    if review.warnings: lines += ["","## Warnings","",*[f"- {x}" for x in review.warnings]]
    lines += ["","## Guardrails","","- Canonical timeline mutated: `false`","- Media rendered: `false`","- Automatic version selection: `false`","- Automatic music selection: `false`","- Model/network access by CLI: `false`",""]
    return "\n".join(lines)


def _comparison_score(item):
    return {"improved": .8, "preserved": .65, "unresolved": None, "regressed": .3}.get(item.status) if item else None


def _fingerprint(path: Path) -> str: return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
def _fingerprint_many(paths: list[Path]) -> str:
    h=hashlib.sha256()
    for p in paths:
        if p.exists(): h.update(p.read_bytes())
    return "sha256:" + h.hexdigest()
