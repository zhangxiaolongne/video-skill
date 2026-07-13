from __future__ import annotations

import csv
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.editor_package import EditorPackage
from artist_portrait_editor.models.nle_roundtrip import NleAcceptanceCheck, NleDeliverable, NleRoundTripPackage, NleSourceBinding
from artist_portrait_editor.models.source import SourceRecord
from artist_portrait_editor.models.state import ActiveMode, OverallStatus, StepLedgerEntry, StepStatus
from artist_portrait_editor.models.timeline import TimelineDraft
from artist_portrait_editor.models.version_review import VersionReview
from artist_portrait_editor.run_records import environment_snapshot, new_run_id, utc_now, write_json
from artist_portrait_editor.workspace_errors import WorkspacePrerequisiteError
from artist_portrait_editor.workspace_state import atomic_write_text, load_state, project_root, save_state, write_run_report


class NleRoundTripError(RuntimeError): pass


def build_nle_roundtrip_workspace(project_path: Path, *, frame_rate: float) -> tuple[Path, Path, NleRoundTripPackage, list[str]]:
    if frame_rate <= 0: raise NleRoundTripError("frame rate must be greater than zero")
    config=load_project_config(project_path); root=project_root(project_path); state=load_state(root)
    if state is None: raise WorkspacePrerequisiteError("nle-roundtrip requires init to complete first")
    data=root/WORKSPACE_DIR/DATA_DIR; timeline_path=root/"output"/"timeline_draft.json"; package_path=data/"editor_package.json"; sources_path=data/"sources.jsonl"; version_path=data/"version_review.json"
    for path,label in ((timeline_path,"timeline"),(package_path,"editor-package"),(sources_path,"scan")):
        if not path.exists(): raise WorkspacePrerequisiteError(f"nle-roundtrip requires {label} to complete first")
    timeline=TimelineDraft.model_validate_json(timeline_path.read_text()); editor=EditorPackage.model_validate_json(package_path.read_text())
    sources=[SourceRecord.model_validate_json(line) for line in sources_path.read_text().splitlines() if line.strip()]
    version=VersionReview.model_validate_json(version_path.read_text()) if version_path.exists() else None
    timeline_fp=_fingerprint(timeline_path); editor_fp=_fingerprint(package_path)
    if timeline.project_id != config.project.id or editor.project_id != config.project.id: raise NleRoundTripError("project binding mismatch")
    if editor.timeline_id != timeline.timeline_id or editor.timeline_fingerprint != timeline_fp: raise NleRoundTripError("editor package is stale; rerun editor-package")
    bindings=_source_bindings(root, editor, sources); out=root/"output"/"nle_roundtrip"; out.mkdir(parents=True,exist_ok=True)
    markers=_marker_rows(editor, version); cues=_cue_rows(editor); deliverables=[]
    files={
        "fcpxml": out/"timeline.fcpxml", "edl": out/"timeline.edl",
        "resolve_markers_csv": out/"resolve_markers.csv", "premiere_markers_csv": out/"premiere_markers.csv",
        "cue_sheet_csv": out/"cue_sheet.csv", "relink_manifest_csv": out/"relink_manifest.csv",
    }
    _write_fcpxml(files["fcpxml"], editor, bindings, markers, frame_rate)
    _write_edl(files["edl"], editor, frame_rate); _write_marker_csv(files["resolve_markers_csv"], markers, "resolve")
    _write_marker_csv(files["premiere_markers_csv"], markers, "premiere"); _write_rows(files["cue_sheet_csv"], cues)
    _write_rows(files["relink_manifest_csv"], [_binding_row(x) for x in bindings])
    limits={
        "fcpxml":["Import compatibility is structurally generated but must be verified in Final Cut Pro."],
        "edl":["EDL is picture-track focused; rich markers and audio automation remain sidecars."],
        "resolve_markers_csv":["Marker CSV is not a full Resolve project."],
        "premiere_markers_csv":["Marker CSV is not a Premiere project file."],
        "cue_sheet_csv":["Cue sheet is editor guidance, not applied automation."],
        "relink_manifest_csv":["Direct file URIs are machine-local and require verification on another workstation."],
    }
    unresolved=sum(1 for x in bindings if x.relink_status != "direct_uri")
    for key,path in files.items(): deliverables.append(NleDeliverable(deliverable_id=key,format=key,ref=path.relative_to(root).as_posix(),status="blocked" if key=="fcpxml" and unresolved else "written",purpose=_purpose(key),limitations=limits[key]))
    checks=_checks(); warnings=[]
    if unresolved: warnings.append(f"{unresolved} source bindings require manual relink or hash review")
    if version is None: warnings.append("version review is absent; package identifies only the canonical timeline")
    warnings.append("NLE import, relink, marker placement, playback, and round-trip export remain externally unverified")
    key=config.project.id+timeline_fp+editor_fp+str(frame_rate)+"".join(x.actual_hash or "missing" for x in bindings)
    model=NleRoundTripPackage(package_id="nle_roundtrip_"+hashlib.sha256(key.encode()).hexdigest()[:20],project_id=config.project.id,status="blocked" if unresolved else "warning",timeline_id=timeline.timeline_id,timeline_fingerprint=timeline_fp,editor_package_id=editor.editor_package_id,editor_package_fingerprint=editor_fp,version_review_id=version.review_id if version else None,version_review_fingerprint=_fingerprint(version_path) if version else None,frame_rate=frame_rate,source_count=len(bindings),directly_linked_source_count=len(bindings)-unresolved,unresolved_source_count=unresolved,timeline_item_count=len(editor.timeline_items),marker_count=len(markers),cue_count=len(cues),source_bindings=bindings,deliverables=deliverables,acceptance_checks=checks,warnings=warnings)
    json_path=data/"nle_roundtrip.json"; md_path=root/"output"/"nle_roundtrip.md"; atomic_write_text(json_path,json.dumps(model.model_dump(mode="json"),ensure_ascii=False,indent=2,sort_keys=True)+"\n"); atomic_write_text(md_path,render_nle_roundtrip(model))
    run_id=new_run_id(); step_status=StepStatus.failed if model.status=="blocked" else StepStatus.completed_with_warnings
    state.steps["nle_roundtrip"]=StepLedgerEntry(status=step_status,input_fingerprint=_fingerprint_many([timeline_path,package_path,sources_path,version_path]),output_refs=[json_path.relative_to(root).as_posix(),md_path.relative_to(root).as_posix(),*[x.ref for x in deliverables]],last_run_id=run_id,warnings=warnings)
    state.active_mode=ActiveMode.core; state.latest_run_id=run_id; state.updated_at=utc_now(); state.overall_status=OverallStatus.blocked if model.status=="blocked" else OverallStatus.degraded
    runs=root/WORKSPACE_DIR/RUNS_DIR/run_id; runs.mkdir(parents=True,exist_ok=True); write_json(runs/"command.json",{"command":"nle-roundtrip","project":str(project_path),"frame_rate":frame_rate}); write_json(runs/"environment.json",environment_snapshot()); write_json(runs/"step_result.json",{"step":"nle_roundtrip","status":step_status.value,"output_refs":state.steps["nle_roundtrip"].output_refs,"warnings":warnings})
    save_state(root,state); write_run_report(root/config.paths.output_dir,state,warnings); return json_path,md_path,model,warnings


def _source_bindings(root, editor, sources):
    by_id={x.source_id:x for x in sources}; used={x.source_id for x in editor.timeline_items}; result=[]
    for sid in sorted(used):
        source=by_id.get(sid)
        if source is None: raise NleRoundTripError(f"source ledger missing {sid}")
        path=Path(source.primary_location); path=path if path.is_absolute() else root/path; exists=path.is_file(); actual=_fingerprint(path) if exists else None; matches=actual==source.content_hash
        status="direct_uri" if exists and matches else "hash_mismatch" if exists else "missing"
        result.append(NleSourceBinding(source_id=sid,source_ref=source.primary_location,nle_uri=path.resolve().as_uri() if exists else None,expected_hash=source.content_hash,actual_hash=actual,exists=exists,hash_matches=matches,relink_status=status,timeline_item_ids=[x.item_id for x in editor.timeline_items if x.source_id==sid]))
    return result


def _marker_rows(editor, version):
    rows=[]
    for action in editor.manual_actions:
        rows.append({"name":f"{action.priority}:{action.category}","description":action.instruction,"in":action.timeline_start or 0,"out":action.timeline_end or action.timeline_start or 0,"color":"Red" if action.priority=="high" else "Yellow"})
    if version:
        for goal in version.goal_advantages:
            rows.append({"name":f"AB:{goal.goal}","description":f"{goal.status}; leaders={','.join(goal.leading_version_ids) or 'none'}; {goal.rationale}","in":0,"out":0,"color":"Blue"})
    return rows


def _cue_rows(editor):
    rows=[]
    for item in editor.timeline_items: rows.append({"type":"clip","id":item.item_id,"in":f"{item.timeline_start:.3f}","out":f"{item.timeline_end:.3f}","source_id":item.source_id,"source_in":f"{item.source_in:.3f}","source_out":f"{item.source_out:.3f}","instruction":item.creative_intent})
    for item in editor.audio_items: rows.append({"type":"audio","id":item.item_id,"in":"" if item.timeline_start is None else f"{item.timeline_start:.3f}","out":"" if item.timeline_end is None else f"{item.timeline_end:.3f}","source_id":"","source_in":"","source_out":"","instruction":item.instruction})
    return rows


def _write_fcpxml(path, editor, bindings, markers, fps):
    root=ET.Element("fcpxml",version="1.10"); resources=ET.SubElement(root,"resources"); ET.SubElement(resources,"format",id="r1",name=f"FFVideoFormatRate{fps:g}",frameDuration=_sec(1/fps))
    by_source={x.source_id:x for x in bindings}
    for i,b in enumerate(bindings,2): ET.SubElement(resources,"asset",id=f"r{i}",name=b.source_id,src=b.nle_uri or f"file:///ARTIST_PORTRAIT_RELINK/{b.source_id}",start="0s",hasVideo="1",hasAudio="1")
    library=ET.SubElement(root,"library"); event=ET.SubElement(library,"event",name=editor.project_id); project=ET.SubElement(event,"project",name=f"{editor.project_id}-canonical"); sequence=ET.SubElement(project,"sequence",format="r1",duration=_sec(editor.actual_duration)); spine=ET.SubElement(sequence,"spine")
    source_refs={b.source_id:f"r{i}" for i,b in enumerate(bindings,2)}
    for item in editor.timeline_items:
        clip=ET.SubElement(spine,"asset-clip",name=item.clip_id,ref=source_refs[item.source_id],offset=_sec(item.timeline_start),start=_sec(item.source_in),duration=_sec(item.timeline_end-item.timeline_start))
        for m in markers:
            if item.timeline_start <= float(m["in"]) <= item.timeline_end: ET.SubElement(clip,"marker",start=_sec(max(float(m["in"])-item.timeline_start,0)),value=str(m["name"]),note=str(m["description"]))
    xml=ET.tostring(root,encoding="unicode"); ET.fromstring(xml); path.write_text("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<!DOCTYPE fcpxml>\n"+xml+"\n",encoding="utf-8")


def _write_edl(path, editor, fps):
    lines=[f"TITLE: {editor.project_id}","FCM: NON-DROP FRAME",""]
    for i,item in enumerate(editor.timeline_items,1): lines += [f"{i:03d}  {item.source_id[:8].upper():<8} V     C        {_tc(item.source_in,fps)} {_tc(item.source_out,fps)} {_tc(item.timeline_start,fps)} {_tc(item.timeline_end,fps)}",f"* FROM CLIP NAME: {item.clip_id}",""]
    path.write_text("\n".join(lines),encoding="utf-8")


def _write_marker_csv(path, rows, target):
    fields=["Marker Name","Description","In","Out","Duration","Marker Color" if target=="resolve" else "Marker Type"]
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for r in rows: w.writerow({"Marker Name":r["name"],"Description":r["description"],"In":f'{float(r["in"]):.3f}',"Out":f'{float(r["out"]):.3f}',"Duration":f'{max(float(r["out"])-float(r["in"]),0):.3f}',fields[-1]:r["color"] if target=="resolve" else "Comment"})


def _write_rows(path, rows):
    if not rows: path.write_text("\n",encoding="utf-8"); return
    with path.open("w",encoding="utf-8",newline="") as f: w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
def _binding_row(x): return {"source_id":x.source_id,"source_ref":x.source_ref,"nle_uri":x.nle_uri or "","expected_hash":x.expected_hash,"actual_hash":x.actual_hash or "","exists":x.exists,"hash_matches":x.hash_matches,"relink_status":x.relink_status,"timeline_item_ids":";".join(x.timeline_item_ids)}
def _purpose(key): return {"fcpxml":"Editable Final Cut Pro timeline with source URIs and markers.","edl":"Simple picture edit decision list for broad NLE interchange.","resolve_markers_csv":"Resolve marker import sidecar.","premiere_markers_csv":"Premiere marker import sidecar.","cue_sheet_csv":"Clip, source-range, audio, and creative-intent handoff.","relink_manifest_csv":"Source identity, location, hash, and relink audit."}[key]
def _checks():
    specs=[("sources","pre_import","Confirm every source URI and hash on the editing workstation."),("import","import","Import the FCPXML or EDL into the target NLE."),("relink","relink","Confirm no source is offline or substituted."),("timeline","timeline","Verify clip order, source ranges, duration, tracks, and transitions."),("markers","markers","Import and spot-check manual and A/B markers."),("audio","audio","Rebuild or verify source audio, BGM, gain, fades, and ducking from cue notes."),("playback","playback","Play opening, transitions, voice/BGM overlaps, and ending."),("export","roundtrip_export","Export XML/EDL from the NLE and compare against the package before claiming round-trip success." )]
    return [NleAcceptanceCheck(check_id=f"nle_check_{i:02d}",stage=s,instruction=t,evidence_required=["external operator record or exported NLE artifact"]) for i,(k,s,t) in enumerate(specs,1)]
def render_nle_roundtrip(p):
    lines=["# NLE Round-Trip Plus","",f"- Status: `{p.status}`",f"- Exported version: `{p.exported_version_id}`",f"- Sources: `{p.directly_linked_source_count}/{p.source_count}` directly linked",f"- Timeline items: `{p.timeline_item_count}`",f"- Markers: `{p.marker_count}`",f"- Cues: `{p.cue_count}`","","## Deliverables",""]
    lines += [f"- `{x.format}`: `{x.ref}` status `{x.status}`; {x.purpose}" for x in p.deliverables]; lines += ["","## Relink",""]+[f"- `{x.source_id}`: `{x.relink_status}` `{x.source_ref}`" for x in p.source_bindings]; lines += ["","## Acceptance Checklist",""]+[f"- `{x.stage}` `{x.status}`: {x.instruction}" for x in p.acceptance_checks]
    if p.warnings: lines += ["","## Warnings","",*[f"- {x}" for x in p.warnings]]
    lines += ["","## Guardrails","","- Import performed: `false`","- Relink performed: `false`","- Playback checked: `false`","- Round-trip verified: `false`","- Canonical timeline mutated: `false`","- Media rendered: `false`","- Model/network access by CLI: `false`",""]; return "\n".join(lines)
def _sec(x): return f"{round(x*1000000)}/1000000s"
def _tc(sec,fps):
    frames=round(sec*fps); f=frames%round(fps); total=frames//round(fps); return f"{total//3600:02d}:{(total//60)%60:02d}:{total%60:02d}:{f:02d}"
def _fingerprint(path): return "sha256:"+hashlib.sha256(path.read_bytes()).hexdigest()
def _fingerprint_many(paths):
    h=hashlib.sha256()
    for p in paths:
        if p.exists(): h.update(p.read_bytes())
    return "sha256:"+h.hexdigest()
