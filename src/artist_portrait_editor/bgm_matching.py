from __future__ import annotations
import hashlib,json
from pathlib import Path
from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import DATA_DIR,RUNS_DIR,WORKSPACE_DIR
from artist_portrait_editor.models.bgm import BgmCandidateLedger
from artist_portrait_editor.models.bgm_match import BgmMatchCandidate,BgmMatchReport
from artist_portrait_editor.models.state import ActiveMode,OverallStatus,StepLedgerEntry,StepStatus
from artist_portrait_editor.models.structure_recommendation import StructureRecommendation
from artist_portrait_editor.run_records import environment_snapshot,new_run_id,utc_now,write_json
from artist_portrait_editor.workspace_state import atomic_write_text,fingerprint_file,fingerprint_inputs,load_state,project_root,save_state,write_run_report

class BgmMatchingError(RuntimeError): pass
def build_bgm_match(project_path:Path):
 config=load_project_config(project_path); root=project_root(project_path); state=load_state(root)
 if state is None: raise BgmMatchingError("bgm-match requires init first")
 data=root/WORKSPACE_DIR/DATA_DIR; structure_path=data/"structure_recommendation.json"; ledger_path=data/"bgm_candidates.json"
 if not structure_path.exists(): raise BgmMatchingError("bgm-match requires current structure recommendation")
 structure=StructureRecommendation.model_validate_json(structure_path.read_text()); ledger=BgmCandidateLedger.model_validate_json(ledger_path.read_text()) if ledger_path.exists() else BgmCandidateLedger(project_id=config.project.id)
 modes={x.input_mode.value for x in ledger.candidates}; input_state="no_file_yet" if not modes else next(iter(modes)) if len(ledger.candidates)==1 else "multiple_candidates"
 items=[]; warnings=[]
 for c in ledger.candidates:
  risks=[]
  if c.mixed_audio: risks.append("mixed video/source audio is not clean BGM and may contain speech, vocals, environment, or effects")
  if c.contains_speech.value=="unknown": risks.append("speech presence unknown; ducking conflict cannot be cleared")
  if c.beat_analysis_status!="completed": risks.append("BPM/beat grid unavailable; rhythm and phrase fit remain unknown")
  pressure="high" if c.mixed_audio or c.contains_speech.value!="absent" else "medium"
  items.append(BgmMatchCandidate(music_candidate_id=c.music_candidate_id,input_mode=c.input_mode.value,mixed_audio=c.mixed_audio,mood_confidence=0,rhythm_confidence=0 if c.beat_analysis_status!="completed" else .7,bpm=c.bpm,beat_status=c.beat_analysis_status,ducking_pressure=pressure,text_timing_pressure="high" if pressure=="high" else "medium",transition_pressure="high" if c.beat_analysis_status!="completed" else "medium",source_risks=risks,compatible_option_ids=[x.option_id for x in structure.options]))
 if not items: warnings.append("no BGM file exists; retain original audio/silence planning and request explicit candidate before matching")
 else: warnings.extend(sorted({r for x in items for r in x.source_risks}))
 report=BgmMatchReport(bgm_match_id="bgm_match_"+hashlib.sha256((fingerprint_file(structure_path)+(fingerprint_file(ledger_path) if ledger_path.exists() else "none")).encode()).hexdigest()[:20],project_id=config.project.id,structure_ref=structure_path.relative_to(root).as_posix(),structure_fingerprint=fingerprint_file(structure_path),input_state=input_state,candidate_count=len(items),candidates=items,status="planning_only" if not items else "degraded" if warnings else "ready",summary="No BGM candidate yet; plan remains unresolved." if not items else "Candidate compatibility is technical-only; mood/rhythm semantics remain unresolved.",warnings=warnings)
 canonical=data/"bgm_match.json"; md=root/"output"/"bgm_match.md"; atomic_write_text(canonical,report.model_dump_json(indent=2)+"\n"); atomic_write_text(md,"# BGM Mood And Rhythm Match\n\n"+f"- Status: `{report.status}`\n- Input: `{report.input_state}`\n- Candidates: `{report.candidate_count}`\n- Automatic selection: `false`\n\n## Warnings\n\n"+"\n".join(f"- {x}" for x in warnings)+"\n")
 run_id=new_run_id(); refs=[canonical.relative_to(root).as_posix(),md.relative_to(root).as_posix()]; inputs=[("structure",structure_path)]+([("ledger",ledger_path)] if ledger_path.exists() else []); state.steps["bgm_match"]=StepLedgerEntry(status=StepStatus.completed_with_warnings if warnings else StepStatus.completed,input_fingerprint=fingerprint_inputs(inputs),output_refs=refs,last_run_id=run_id,warnings=warnings); state.active_mode=ActiveMode.creative; state.overall_status=OverallStatus.degraded if warnings else OverallStatus.ready; state.latest_run_id=run_id; state.updated_at=utc_now(); runs=root/WORKSPACE_DIR/RUNS_DIR/run_id; runs.mkdir(parents=True,exist_ok=True); write_json(runs/"command.json",{"command":"bgm-match","project":str(project_path)}); write_json(runs/"environment.json",environment_snapshot()); save_state(root,state); write_run_report(root/config.paths.output_dir,state,warnings); return canonical,md,report,warnings
