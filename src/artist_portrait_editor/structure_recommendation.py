from __future__ import annotations

import hashlib
from pathlib import Path

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.edit_brief import EditBrief
from artist_portrait_editor.models.editorial_score import EditorialCandidateScore, EditorialScoreSet
from artist_portrait_editor.models.state import ActiveMode, OverallStatus, StepLedgerEntry, StepStatus
from artist_portrait_editor.models.structure_recommendation import RecommendedRange, StructureOption, StructureRecommendation
from artist_portrait_editor.run_records import environment_snapshot, new_run_id, utc_now, write_json
from artist_portrait_editor.workspace_state import atomic_write_text, fingerprint_file, fingerprint_inputs, load_state, project_root, save_state, write_run_report


class StructureRecommendationError(RuntimeError): pass


def build_structure_recommendation(project_path: Path) -> tuple[Path, Path, StructureRecommendation, list[str]]:
    config = load_project_config(project_path); root = project_root(project_path); state = load_state(root)
    if state is None: raise StructureRecommendationError("structure-recommend requires init first")
    data = root / WORKSPACE_DIR / DATA_DIR; score_path = data / "editorial_scores.json"; brief_path = data / "edit_brief.json"
    if not score_path.exists() or not brief_path.exists(): raise StructureRecommendationError("structure-recommend requires current editorial scores and edit brief")
    scores = EditorialScoreSet.model_validate_json(score_path.read_text(encoding="utf-8")); brief = EditBrief.model_validate_json(brief_path.read_text(encoding="utf-8"))
    if scores.project_id != config.project.id or brief.project_id != config.project.id: raise StructureRecommendationError("recommendation input project binding mismatch")
    standard = brief.selected_duration_seconds; targets = {"short": round(max(.5, standard * .65), 3), "standard": standard, "extended": round(min(sum(x.end_seconds-x.start_seconds for x in scores.candidates), standard * 1.5), 3)}
    if targets["extended"] <= standard: targets["extended"] = round(standard * 1.25, 3)
    options = [_option(kind, targets[kind], scores.candidates, standard) for kind in ("short", "standard", "extended")]
    avg_conf = sum(c.ranking_confidence for c in scores.candidates) / len(scores.candidates); warnings = list(scores.warnings)
    if avg_conf < .5: warnings.append(f"average editorial ranking confidence is low ({avg_conf:.4f}); duration structures require host/editor review")
    rec = StructureRecommendation(recommendation_id="structure_"+hashlib.sha256((fingerprint_file(score_path)+fingerprint_file(brief_path)).encode()).hexdigest()[:20], project_id=config.project.id, score_set_id=scores.score_set_id, score_set_ref=score_path.relative_to(root).as_posix(), score_set_fingerprint=fingerprint_file(score_path), edit_brief_id=brief.edit_brief_id, edit_brief_ref=brief_path.relative_to(root).as_posix(), edit_brief_fingerprint=fingerprint_file(brief_path), target_platform=brief.target_platform, explicit_standard_duration_seconds=standard, options=options, recommended_option_id="standard", status="degraded" if warnings else "ready", warnings=warnings)
    canonical=data/"structure_recommendation.json"; report=root/"output"/"structure_recommendation.md"; atomic_write_text(canonical,rec.model_dump_json(indent=2)+"\n"); atomic_write_text(report,_report(rec))
    run_id=new_run_id(); refs=[canonical.relative_to(root).as_posix(),report.relative_to(root).as_posix()]; state.steps["structure_recommendation"]=StepLedgerEntry(status=StepStatus.completed_with_warnings if warnings else StepStatus.completed,input_fingerprint=fingerprint_inputs([("scores",score_path),("brief",brief_path)]),output_refs=refs,last_run_id=run_id,warnings=warnings); state.active_mode=ActiveMode.creative; state.overall_status=OverallStatus.degraded if warnings else OverallStatus.ready; state.latest_run_id=run_id; state.updated_at=utc_now(); runs=root/WORKSPACE_DIR/RUNS_DIR/run_id; runs.mkdir(parents=True,exist_ok=True); write_json(runs/"command.json",{"command":"structure-recommend","project":str(project_path)}); write_json(runs/"environment.json",environment_snapshot()); write_json(runs/"step_result.json",{"step":"structure_recommendation","status":rec.status,"output_refs":refs,"timeline_mutated":False}); save_state(root,state); write_run_report(root/config.paths.output_dir,state,warnings)
    return canonical,report,rec,warnings


def _option(kind: str, target: float, candidates: list[EditorialCandidateScore], standard: float) -> StructureOption:
    hook=sorted(candidates,key=lambda x:(x.hook_rank,x.candidate_id))[0]; ending=next((x for x in sorted(candidates,key=lambda x:(x.ending_rank,x.candidate_id)) if x.candidate_id!=hook.candidate_id),hook); middle=[x for x in sorted(candidates,key=lambda x:(x.highlight_rank,x.candidate_id)) if x.candidate_id not in {hook.candidate_id,ending.candidate_id}]
    ending_budget=min(ending.end_seconds-ending.start_seconds,max(1,min(6,target*.12))) if ending.candidate_id!=hook.candidate_id else 0.0
    content_budget=target-ending_budget; ordered=[(hook,"hook")]+[(x,"build") for x in middle]
    selected=[]; used=0.0
    for candidate,role in ordered:
        available=candidate.end_seconds-candidate.start_seconds; take=min(available,max(0,content_budget-used))
        if take<.25: continue
        selected.append(RecommendedRange(candidate_id=candidate.candidate_id,role=role,source_id=candidate.source_id,source_in=candidate.start_seconds,source_out=round(candidate.start_seconds+take,3),planned_duration=round(take,3),score=candidate.hook_score if role=="hook" else candidate.ending_score if role=="payoff" else candidate.highlight_score,ranking_confidence=candidate.ranking_confidence,rationale=f"{role} candidate rank selected from current editorial score set")); used+=take
        if used>=content_budget-.001: break
    if ending_budget:
        selected.append(RecommendedRange(candidate_id=ending.candidate_id,role="payoff",source_id=ending.source_id,source_in=ending.start_seconds,source_out=ending.start_seconds+ending_budget,planned_duration=ending_budget,score=ending.ending_score,ranking_confidence=ending.ranking_confidence,rationale="ending-ranked candidate reserved inside the target-duration budget")); used+=ending_budget
    allocation={role:round(sum(x.planned_duration for x in selected if x.role==role),3) for role in ("hook","build","payoff")}; confidence=sum(x.ranking_confidence*x.planned_duration for x in selected)/max(.001,sum(x.planned_duration for x in selected))
    sacrifices=["fewer context ranges and less breathing room"] if kind=="short" else ["balanced option still omits lower-ranked ranges"] if kind=="standard" else ["greater pacing drag, repetition, text load, and audio-continuity risk"]
    retained=["highest available hook candidate","ranked build ranges","distinct ending candidate where evidence permits"]
    risks=["source-audio continuity must be auditioned after reordering","BGM fit, ducking, subtitles, transitions, and reading time must be replanned","rankings are recommendations; no edit points have been applied"]
    return StructureOption(option_id=kind,target_duration_seconds=target,estimated_duration_seconds=round(used,3),duration_source="user_or_config_target" if kind=="standard" else "derived",ranges=selected,role_allocation_seconds=allocation,retained_qualities=retained,sacrifices=sacrifices,coupled_risks=risks,recommendation_confidence=round(confidence,4))


def _report(value: StructureRecommendation)->str:
    lines=["# Duration And Structure Recommendation","",f"- ID: `{value.recommendation_id}`",f"- Status: `{value.status}`",f"- Recommended: `{value.recommended_option_id}`",""]
    for option in value.options:
        lines.extend([f"## {option.option_id.title()}","",f"- Target: `{option.target_duration_seconds:.3f}s`",f"- Estimated: `{option.estimated_duration_seconds:.3f}s`",f"- Confidence: `{option.recommendation_confidence:.4f}`",f"- Ranges: `{len(option.ranges)}`",""])
    lines.extend(["## Warnings",""]+[f"- {x}" for x in value.warnings]); return "\n".join(lines)+"\n"
