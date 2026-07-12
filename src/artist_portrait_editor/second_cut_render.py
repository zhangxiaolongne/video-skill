from __future__ import annotations

import hashlib
import json
from pathlib import Path

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.media.probe import probe_media
from artist_portrait_editor.media.rendering import RenderCanvas, concat_files, fingerprint_file, mux_tracks, render_audio_segment, render_silence, render_video_segment
from artist_portrait_editor.models.bgm_match import BgmMatchReport
from artist_portrait_editor.models.final_export import FinalExportManifest
from artist_portrait_editor.models.first_cut_review import FirstCutSelfReview
from artist_portrait_editor.models.second_cut_render import SecondCutComparison, SecondCutRender, SecondCutSegment
from artist_portrait_editor.models.source import SourceRecord
from artist_portrait_editor.models.structure_recommendation import StructureRecommendation
from artist_portrait_editor.models.text_plan import TextTimingPlan
from artist_portrait_editor.models.state import ActiveMode, OverallStatus, StepLedgerEntry, StepStatus
from artist_portrait_editor.run_records import environment_snapshot, new_run_id, utc_now, write_json
from artist_portrait_editor.workspace_state import atomic_write_text, fingerprint_inputs, load_state, project_root, save_state, write_run_report


class SecondCutRenderError(RuntimeError):
    pass


def render_second_cut(project_path: Path, option_id: str) -> tuple[Path, Path, Path, SecondCutRender, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise SecondCutRenderError("second-cut-render requires init first")
    data = root / WORKSPACE_DIR / DATA_DIR
    paths = {
        "structure": data / "structure_recommendation.json",
        "review": data / "first_cut_self_review.json",
        "scores": data / "editorial_scores.json",
        "bgm": data / "bgm_match.json",
        "text": data / "text_timing_plan.json",
        "sources": data / "sources.jsonl",
        "manifest": data / "final_export_manifest.json",
    }
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        raise SecondCutRenderError("second-cut-render missing current evidence: " + ", ".join(missing))
    structure = StructureRecommendation.model_validate_json(paths["structure"].read_text(encoding="utf-8"))
    review = FirstCutSelfReview.model_validate_json(paths["review"].read_text(encoding="utf-8"))
    bgm = BgmMatchReport.model_validate_json(paths["bgm"].read_text(encoding="utf-8"))
    text = TextTimingPlan.model_validate_json(paths["text"].read_text(encoding="utf-8"))
    manifest = FinalExportManifest.model_validate_json(paths["manifest"].read_text(encoding="utf-8"))
    if {structure.project_id, review.project_id, bgm.project_id, text.project_id, manifest.project_id} != {config.project.id}:
        raise SecondCutRenderError("second-cut-render project binding mismatch")
    option = next((item for item in structure.options if item.option_id == option_id), None)
    if option is None:
        raise SecondCutRenderError(f"unknown structure option: {option_id}")
    sources = _read_sources(paths["sources"])
    profile = manifest.requested_profile
    canvas = RenderCanvas(profile.width, profile.height, profile.fps, profile.aspect_ratio)
    output = root / config.paths.output_dir / f"second_cut_{option.option_id}.mp4"
    work = root / WORKSPACE_DIR / "cache" / "second_cut" / option.option_id
    work.mkdir(parents=True, exist_ok=True)
    video_parts: list[Path] = []
    audio_parts: list[Path] = []
    segments: list[SecondCutSegment] = []
    cursor = 0.0
    for index, item in enumerate(option.ranges, start=1):
        source = sources.get(item.source_id)
        if source is None:
            raise SecondCutRenderError(f"structure range references unknown source: {item.source_id}")
        source_path = root / source.primary_location
        if not source_path.exists():
            raise SecondCutRenderError(f"source media is missing: {source.primary_location}")
        duration = item.source_out - item.source_in
        if abs(duration - item.planned_duration) > 0.02:
            raise SecondCutRenderError(f"range duration mismatch: {item.candidate_id}")
        video_part = work / f"video_{index:03d}.mp4"
        audio_part = work / f"audio_{index:03d}.wav"
        transition = "fade_in" if index == 1 else "hard_cut"
        render_video_segment(source_path=source_path, output_path=video_part, source_in=item.source_in, duration=duration, canvas=canvas, video_transition=transition, preset="medium", crf=profile.video_crf, timeout=300)
        if source.media_probe.audio_present:
            render_audio_segment(source_path=source_path, output_path=audio_part, source_in=item.source_in, duration=duration, audio_transition="fade_in" if index == 1 else "cut", timeout=300)
        else:
            render_silence(output_path=audio_part, duration=duration, timeout=300)
        video_parts.append(video_part)
        audio_parts.append(audio_part)
        segments.append(SecondCutSegment(segment_id=f"second_cut_{index:03d}", candidate_id=item.candidate_id, role=item.role, source_id=item.source_id, source_ref=source.primary_location, source_in=item.source_in, source_out=item.source_out, timeline_start=round(cursor, 3), timeline_end=round(cursor + duration, 3), ranking_score=item.score, ranking_confidence=item.ranking_confidence, original_audio_rendered=source.media_probe.audio_present))
        cursor += duration
    video_track = work / "video_concat.mp4"
    audio_track = work / "audio_concat.wav"
    concat_files(video_parts, video_track, media_type="video", timeout=600)
    concat_files(audio_parts, audio_track, media_type="audio", timeout=600)
    mux_tracks(video_track=video_track, audio_track=audio_track, output_path=output, audio_bitrate=profile.audio_bitrate, timeout=600)
    _, media = probe_media(output)
    delta = round(media.duration - option.target_duration_seconds, 3)
    valid = bool(media.width == profile.width and media.height == profile.height and media.audio_present and abs(delta) <= 0.35 and media.frame_rate and abs(media.frame_rate - profile.fps) <= 0.1)
    warnings = [
        "second cut is an independent candidate; canonical timeline and first-cut final are unchanged",
        "missing transcript prevents semantic continuity and sentence-boundary validation",
        "new source ranges have no approved per-shot reframes; contain framing is used",
        "text plan is not burned in because subtitle evidence and safe-region approval are unavailable",
    ]
    if bgm.selected_candidate_id is None:
        warnings.append("no BGM candidate was selected; source audio is retained without added music")
    comparisons = _comparisons(option.option_id, segments, manifest, media_valid=valid, no_bgm=bgm.selected_candidate_id is None)
    render_id = "second_cut_" + hashlib.sha256((fingerprint_file(paths["structure"]) + fingerprint_file(paths["review"]) + option.option_id + fingerprint_file(output)).encode()).hexdigest()[:20]
    artifact = SecondCutRender(
        render_id=render_id, project_id=config.project.id, selected_option_id=option.option_id,
        structure_ref=paths["structure"].relative_to(root).as_posix(), structure_fingerprint=fingerprint_file(paths["structure"]),
        first_cut_review_ref=paths["review"].relative_to(root).as_posix(), first_cut_review_fingerprint=fingerprint_file(paths["review"]),
        editorial_scores_ref=paths["scores"].relative_to(root).as_posix(), editorial_scores_fingerprint=fingerprint_file(paths["scores"]),
        bgm_match_ref=paths["bgm"].relative_to(root).as_posix(), bgm_match_fingerprint=fingerprint_file(paths["bgm"]),
        text_plan_ref=paths["text"].relative_to(root).as_posix(), text_plan_fingerprint=fingerprint_file(paths["text"]),
        sources_ref=paths["sources"].relative_to(root).as_posix(), sources_fingerprint=fingerprint_file(paths["sources"]),
        first_cut_ref=manifest.output_ref, first_cut_hash=manifest.output_content_hash,
        output_ref=output.relative_to(root).as_posix(), output_hash=fingerprint_file(output),
        target_duration_seconds=option.target_duration_seconds, actual_duration_seconds=media.duration, duration_delta_seconds=delta,
        width=media.width or 0, height=media.height or 0, frame_rate=media.frame_rate or 0,
        video_present=media.width is not None, audio_present=media.audio_present, media_valid=valid,
        candidate_timeline=segments, source_audio_retained=all(item.original_audio_rendered for item in segments),
        comparisons=comparisons, publishability="not_publishable", warnings=warnings,
    )
    canonical = data / "second_cut_render.json"
    report = root / config.paths.output_dir / "second_cut_review.md"
    atomic_write_text(canonical, artifact.model_dump_json(indent=2) + "\n")
    atomic_write_text(report, _report(artifact))
    run_id = new_run_id()
    refs = [canonical.relative_to(root).as_posix(), report.relative_to(root).as_posix(), output.relative_to(root).as_posix()]
    state.steps["second_cut_render"] = StepLedgerEntry(status=StepStatus.completed_with_warnings if valid else StepStatus.failed, input_fingerprint=fingerprint_inputs(list(paths.items())), output_refs=refs, last_run_id=run_id, warnings=warnings)
    state.active_mode = ActiveMode.creative
    state.overall_status = OverallStatus.degraded
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    runs = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs.mkdir(parents=True, exist_ok=True)
    write_json(runs / "command.json", {"command": "second-cut-render", "project": str(project_path), "option_id": option.option_id})
    write_json(runs / "environment.json", environment_snapshot())
    write_json(runs / "step_result.json", {"step": "second_cut_render", "media_valid": valid, "publishability": artifact.publishability, "canonical_timeline_mutated": False, "canonical_final_overwritten": False, "output_refs": refs})
    save_state(root, state)
    write_run_report(root / config.paths.output_dir, state, warnings)
    return canonical, report, output, artifact, warnings


def _read_sources(path: Path) -> dict[str, SourceRecord]:
    records = [SourceRecord.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {item.source_id: item for item in records}


def _comparisons(option_id: str, segments: list[SecondCutSegment], first: FinalExportManifest, *, media_valid: bool, no_bgm: bool) -> list[SecondCutComparison]:
    first_segments = first.rendered_segments
    opening_changed = bool(first_segments and (first_segments[0].source_id != segments[0].source_id or abs(first_segments[0].source_in - segments[0].source_in) > 0.01))
    ending_changed = bool(first_segments and (first_segments[-1].source_id != segments[-1].source_id or abs(first_segments[-1].source_in - segments[-1].source_in) > 0.01))
    refs = [item.candidate_id for item in segments]
    middle_refs = refs[1:-1] or refs
    return [
        SecondCutComparison(domain="duration_structure", status="improved", finding=f"Explicit {option_id} structure was applied as an independent candidate with exact hook/build/payoff roles.", evidence_refs=refs, next_action="Review role progression in full playback."),
        SecondCutComparison(domain="opening", status="improved" if opening_changed else "preserved", finding="Opening source range changed to the selected hook-ranked candidate." if opening_changed else "Opening source range is unchanged.", evidence_refs=[segments[0].candidate_id], next_action="Confirm the first ten seconds work semantically and visually."),
        SecondCutComparison(domain="middle_pacing", status="unresolved", finding="Ranked build ranges were reordered, but mostly fixed ten-second blocks do not prove mature pacing.", evidence_refs=middle_refs, next_action="Trim against sentence, gesture, music, and shot boundaries after semantic review."),
        SecondCutComparison(domain="ending", status="improved" if ending_changed else "preserved", finding="Ending changed to the selected ending-ranked payoff range." if ending_changed else "Ending range is unchanged.", evidence_refs=[segments[-1].candidate_id], next_action="Review completion and cadence with source audio."),
        SecondCutComparison(domain="source_audio_bgm", status="preserved", finding="Original source audio is retained; no unselected BGM was added." if no_bgm else "Original source audio is retained without automatically applying the current BGM candidate.", evidence_refs=[first.export_id], next_action="Review discontinuities at every reordered cut and audition BGM only after explicit selection."),
        SecondCutComparison(domain="text", status="unresolved", finding="No title or subtitles were rendered because transcript and safe-region evidence are unavailable.", evidence_refs=refs, next_action="Obtain transcript or user text before supervised text rendering."),
        SecondCutComparison(domain="composition", status="unresolved", finding="New ranges use contain framing; prior sampled reframe evidence does not cover this candidate timeline.", evidence_refs=refs, next_action="Run composition sampling and approve per-shot reframes for this exact candidate."),
        SecondCutComparison(domain="semantic_continuity", status="unresolved", finding="Ranking evidence does not establish sentence, performance, or narrative continuity.", evidence_refs=refs, next_action="Transcribe or manually review semantic boundaries before publishability approval."),
        SecondCutComparison(domain="technical_delivery", status="preserved" if media_valid else "regressed", finding="Independent MP4 passes duration, canvas, frame-rate, video, and audio checks." if media_valid else "Independent MP4 failed one or more media checks.", evidence_refs=[first.output_ref], next_action="Preserve technical validity after aesthetic revisions." if media_valid else "Repair media validation before aesthetic review."),
    ]


def _report(item: SecondCutRender) -> str:
    lines = ["# Second-Cut Render Review", "", f"- Render: `{item.render_id}`", f"- Explicit option: `{item.selected_option_id}`", f"- Output: `{item.output_ref}`", f"- Duration: `{item.actual_duration_seconds:.3f}` / target `{item.target_duration_seconds:.3f}`", f"- Media valid: `{str(item.media_valid).lower()}`", f"- Publishability: `{item.publishability}`", f"- Canonical first cut overwritten: `{str(item.canonical_final_overwritten).lower()}`", "", "## Candidate Timeline", ""]
    for segment in item.candidate_timeline:
        lines.append(f"- `{segment.segment_id}` `{segment.role}`: source `{segment.source_in:.3f}-{segment.source_out:.3f}` -> timeline `{segment.timeline_start:.3f}-{segment.timeline_end:.3f}`")
    lines.extend(["", "## First Cut vs Second Cut", ""])
    for comparison in item.comparisons:
        lines.append(f"- `{comparison.domain}`: `{comparison.status}` - {comparison.finding}")
    lines.extend(["", "## Warnings", ""] + [f"- {warning}" for warning in item.warnings])
    return "\n".join(lines) + "\n"
