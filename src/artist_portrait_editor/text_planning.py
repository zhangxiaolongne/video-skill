from __future__ import annotations

import hashlib
from pathlib import Path

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.bgm_match import BgmMatchReport
from artist_portrait_editor.models.edit_brief import EditBrief
from artist_portrait_editor.models.editorial_score import EditorialScoreSet
from artist_portrait_editor.models.evidence_map import EvidenceMap
from artist_portrait_editor.models.state import ActiveMode, OverallStatus, StepLedgerEntry, StepStatus
from artist_portrait_editor.models.structure_recommendation import StructureRecommendation
from artist_portrait_editor.models.text_plan import TextOptionPlan, TextPlanElement, TextTimingPlan
from artist_portrait_editor.run_records import environment_snapshot, new_run_id, utc_now, write_json
from artist_portrait_editor.workspace_state import atomic_write_text, fingerprint_file, fingerprint_inputs, load_state, project_root, save_state, write_run_report


class TextPlanningError(RuntimeError):
    pass


def build_text_plan(project_path: Path) -> tuple[Path, Path, TextTimingPlan, list[str]]:
    config = load_project_config(project_path)
    root = project_root(project_path)
    state = load_state(root)
    if state is None:
        raise TextPlanningError("text-plan requires init first")
    data = root / WORKSPACE_DIR / DATA_DIR
    paths = {
        "structure": data / "structure_recommendation.json",
        "scores": data / "editorial_scores.json",
        "evidence": data / "evidence_map.json",
        "bgm": data / "bgm_match.json",
        "brief": data / "edit_brief.json",
    }
    missing = [name for name, path in paths.items() if not path.exists()]
    if missing:
        raise TextPlanningError("text-plan missing current inputs: " + ", ".join(missing))
    structure = StructureRecommendation.model_validate_json(paths["structure"].read_text(encoding="utf-8"))
    scores = EditorialScoreSet.model_validate_json(paths["scores"].read_text(encoding="utf-8"))
    evidence = EvidenceMap.model_validate_json(paths["evidence"].read_text(encoding="utf-8"))
    bgm = BgmMatchReport.model_validate_json(paths["bgm"].read_text(encoding="utf-8"))
    brief = EditBrief.model_validate_json(paths["brief"].read_text(encoding="utf-8"))
    project_ids = {structure.project_id, scores.project_id, evidence.project_id, bgm.project_id, brief.project_id}
    if project_ids != {config.project.id}:
        raise TextPlanningError("text-plan input project binding mismatch")
    unit_by_id = {item.unit_id: item for item in evidence.units}
    candidate_units = {item.candidate_id: unit_by_id[item.unit_id] for item in scores.candidates}
    pressure = _audio_pressure(bgm)
    option_plans = [
        _build_option(option, brief.title, candidate_units, pressure)
        for option in structure.options
    ]
    warnings = list(dict.fromkeys(
        [warning for option in option_plans for warning in option.warnings]
        + (["transcript coverage is zero; subtitle and emphasis content remain unavailable"] if evidence.transcript_coverage_ratio == 0 else [])
        + (["composition evidence is sampled only; every text safe region requires moving-playback review"])
    ))
    overall = "degraded" if warnings else "ready"
    fingerprint_source = ":".join(fingerprint_file(path) for path in paths.values())
    plan = TextTimingPlan(
        text_plan_id="text_plan_" + hashlib.sha256(fingerprint_source.encode()).hexdigest()[:20],
        project_id=config.project.id,
        structure_recommendation_id=structure.recommendation_id,
        structure_ref=paths["structure"].relative_to(root).as_posix(),
        structure_fingerprint=fingerprint_file(paths["structure"]),
        evidence_map_id=evidence.evidence_map_id,
        evidence_map_ref=paths["evidence"].relative_to(root).as_posix(),
        evidence_map_fingerprint=fingerprint_file(paths["evidence"]),
        bgm_match_id=bgm.bgm_match_id,
        bgm_match_ref=paths["bgm"].relative_to(root).as_posix(),
        bgm_match_fingerprint=fingerprint_file(paths["bgm"]),
        edit_brief_id=brief.edit_brief_id,
        title_text=brief.title,
        options=option_plans,
        transcript_coverage_ratio=evidence.transcript_coverage_ratio,
        status=overall,
        warnings=warnings,
    )
    canonical = data / "text_timing_plan.json"
    report = root / "output" / "text_timing_plan.md"
    atomic_write_text(canonical, plan.model_dump_json(indent=2) + "\n")
    atomic_write_text(report, _render_report(plan))
    run_id = new_run_id()
    refs = [canonical.relative_to(root).as_posix(), report.relative_to(root).as_posix()]
    state.steps["text_plan"] = StepLedgerEntry(
        status=StepStatus.completed_with_warnings if warnings else StepStatus.completed,
        input_fingerprint=fingerprint_inputs(list(paths.items())), output_refs=refs,
        last_run_id=run_id, warnings=warnings,
    )
    state.active_mode = ActiveMode.creative
    state.overall_status = OverallStatus.degraded if warnings else OverallStatus.ready
    state.latest_run_id = run_id
    state.updated_at = utc_now()
    runs = root / WORKSPACE_DIR / RUNS_DIR / run_id
    runs.mkdir(parents=True, exist_ok=True)
    write_json(runs / "command.json", {"command": "text-plan", "project": str(project_path)})
    write_json(runs / "environment.json", environment_snapshot())
    write_json(runs / "step_result.json", {"step": "text_plan", "status": overall, "output_refs": refs, "invented_transcript": False, "media_rendered": False})
    save_state(root, state)
    write_run_report(root / config.paths.output_dir, state, warnings)
    return canonical, report, plan, warnings


def _build_option(option, title: str, candidate_units: dict, pressure: str) -> TextOptionPlan:
    elements: list[TextPlanElement] = []
    title_duration = min(2.5, max(1.2, option.target_duration_seconds * 0.06))
    elements.append(TextPlanElement(
        element_id=f"{option.option_id}_title", element_type="title",
        timeline_in=0.2, timeline_out=round(0.2 + title_duration, 3), content=title,
        evidence_status="available", evidence_refs=["edit_brief:title"],
        character_count=len(title), characters_per_second=round(len(title) / title_duration, 3),
        reading_risk=_reading_risk(len(title) / title_duration), safe_region="top",
        safe_region_status="manual_review_required", audio_pressure=pressure,
        warnings=["title placement requires playback review against performer and persistent branding"],
    ))
    cursor = 0.0
    option_warnings: list[str] = []
    for index, item in enumerate(option.ranges, start=1):
        unit = candidate_units[item.candidate_id]
        start = cursor
        end = round(cursor + item.planned_duration, 3)
        transcript_text = str(unit.transcript.facts.get("text", "")).strip() if unit.transcript.status in {"available", "partial"} else ""
        if transcript_text:
            cps = len(transcript_text) / item.planned_duration
            content = transcript_text
            evidence_status = unit.transcript.status
            risk = _reading_risk(cps)
            refs = unit.transcript.refs
            warnings = ["subtitle text is evidence-backed but requires line breaking and visual playback review"]
        else:
            cps = None
            content = None
            evidence_status = "unavailable"
            risk = "unavailable"
            refs = []
            warnings = ["subtitle slot unavailable: no overlapping transcript; do not invent dialogue or lyrics"]
            option_warnings.append(f"{item.candidate_id}: subtitle unavailable without transcript")
        elements.append(TextPlanElement(
            element_id=f"{option.option_id}_subtitle_{index:03d}", element_type="subtitle",
            candidate_id=item.candidate_id, source_id=item.source_id,
            source_in=item.source_in, source_out=item.source_out,
            timeline_in=start, timeline_out=end, content=content,
            evidence_status=evidence_status, evidence_refs=refs,
            character_count=len(content) if content else 0,
            characters_per_second=round(cps, 3) if cps is not None else None,
            reading_risk=risk, safe_region="lower_third",
            safe_region_status="manual_review_required", audio_pressure=pressure,
            warnings=warnings,
        ))
        if item.role == "payoff":
            pause_end = min(end, start + min(0.5, item.planned_duration / 4))
            elements.append(TextPlanElement(
                element_id=f"{option.option_id}_payoff_space_{index:03d}", element_type="empty_space",
                candidate_id=item.candidate_id, source_id=item.source_id,
                source_in=item.source_in, source_out=min(item.source_out, item.source_in + (pause_end - start)),
                timeline_in=start, timeline_out=pause_end, content=None,
                evidence_status="not_applicable", character_count=0,
                reading_risk="none", safe_region="full_frame_reservation",
                safe_region_status="manual_review_required", audio_pressure=pressure,
                warnings=["reserve text-free landing; this does not add or move edit time"],
            ))
        cursor = end
    subtitle_elements = [item for item in elements if item.element_type == "subtitle"]
    densities = [item.characters_per_second for item in subtitle_elements if item.characters_per_second is not None]
    return TextOptionPlan(
        option_id=option.option_id, duration_seconds=option.target_duration_seconds,
        elements=elements, title_count=1,
        subtitle_count=sum(item.content is not None for item in subtitle_elements),
        unavailable_subtitle_slot_count=sum(item.content is None for item in subtitle_elements),
        emphasis_count=0,
        pause_or_space_count=sum(item.element_type in {"pause", "empty_space"} for item in elements),
        maximum_text_density_cps=max(densities) if densities else None,
        status="degraded" if option_warnings else "ready",
        warnings=list(dict.fromkeys(option_warnings)),
    )


def _audio_pressure(bgm: BgmMatchReport) -> str:
    levels = {"low": 0, "medium": 1, "high": 2}
    if not bgm.candidates:
        return "unknown"
    return max((item.text_timing_pressure for item in bgm.candidates), key=levels.get)


def _reading_risk(cps: float) -> str:
    if cps <= 4: return "low"
    if cps <= 7: return "medium"
    return "high"


def _render_report(plan: TextTimingPlan) -> str:
    lines = ["# Text, Subtitle, And On-Screen Timing Plan", "", f"- Plan: `{plan.text_plan_id}`", f"- Status: `{plan.status}`", f"- Transcript coverage: `{plan.transcript_coverage_ratio:.4f}`", f"- Invented transcript: `false`", f"- Text burned into media: `false`", ""]
    for option in plan.options:
        lines.extend([f"## {option.option_id.title()}", "", f"- Duration: `{option.duration_seconds:.3f}s`", f"- Subtitle slots: `{option.subtitle_count}` available / `{option.unavailable_subtitle_slot_count}` unavailable", f"- Pause/space: `{option.pause_or_space_count}`", f"- Status: `{option.status}`", ""])
    lines.extend(["## Warnings", ""] + [f"- {item}" for item in plan.warnings])
    return "\n".join(lines) + "\n"
