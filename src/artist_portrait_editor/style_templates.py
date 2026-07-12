from __future__ import annotations

import hashlib
from pathlib import Path

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import DATA_DIR, RUNS_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.source import SourceRecord
from artist_portrait_editor.models.state import ActiveMode, OverallStatus, StepLedgerEntry, StepStatus
from artist_portrait_editor.models.style_template import StyleTemplate, StyleTemplatePackage, TemplateCompatibility
from artist_portrait_editor.run_records import environment_snapshot, new_run_id, utc_now, write_json
from artist_portrait_editor.workspace_state import atomic_write_text, fingerprint_file, fingerprint_inputs, load_state, project_root, save_state, write_run_report


class StyleTemplatesError(RuntimeError):
    pass


def _beat(beat: str, low: float, high: float, purpose: str) -> dict:
    return {"beat": beat, "minimum_ratio": low, "maximum_ratio": high, "purpose": purpose}


TEMPLATE_DATA = [
    dict(template_id="stage_portrait", name="Stage Portrait", intended_source_types=["stage_performance", "live_performance", "musical_scene"], intended_platforms=["douyin", "bilibili", "xiaohongshu"], intended_aspects=["9:16", "16:9"], structure=[_beat("hook", .08, .18, "performer-forward visual or vocal hook"), _beat("build", .55, .72, "escalate performance and shot intimacy"), _beat("payoff", .15, .28, "complete gesture, phrase, or applause-safe landing")], shot_duration_range_seconds=(1.5, 7.0), rhythm_policy="follow verified performance phrases and gestures; do not infer beats from loudness", source_audio_policy="performance source audio is primary unless an explicit clean replacement is selected", bgm_policy="do not layer unrelated BGM over an existing performance mix without explicit audition", subtitle_density="minimal", maximum_characters_per_second=5.0, transition_restraint="strict", transition_policy="cuts and restrained fades only; preserve movement continuity", composition_policy="keep performer face/body and stage intent inside approved frame throughout motion", required_evidence=["performer composition", "source audio semantics", "phrase or gesture boundaries"], acceptance_checks=["hook foregrounds performer", "no broadcast bands dominate", "cuts respect movement", "source audio remains coherent", "text does not cover performer", "ending completes a phrase"], hard_incompatibilities=["audio-only source", "performer cannot be kept in frame"]),
    dict(template_id="interview_portrait", name="Interview Portrait", intended_source_types=["interview"], intended_platforms=["douyin", "bilibili", "xiaohongshu"], intended_aspects=["16:9", "9:16"], structure=[_beat("hook", .08, .15, "strong complete statement"), _beat("context", .12, .25, "identify subject and premise"), _beat("build", .45, .65, "develop connected ideas"), _beat("payoff", .12, .22, "land the clearest concluding thought")], shot_duration_range_seconds=(3.0, 12.0), rhythm_policy="sentence and thought boundaries dominate; avoid equal-duration mechanical cuts", source_audio_policy="speech is primary and must remain intelligible across every edit", bgm_policy="optional low-pressure instrumental only after speech and vocal conflict review", subtitle_density="moderate", maximum_characters_per_second=7.0, transition_restraint="strict", transition_policy="hard cuts, J/L cuts, or motivated reaction cuts; no decorative transitions", composition_policy="protect face, eye line, gestures, and lower-third/text safe regions", required_evidence=["transcript", "speaker boundaries", "sentence completeness"], acceptance_checks=["hook is a complete thought", "chronology remains intelligible", "no sentence is clipped", "speech dominates BGM", "subtitles remain readable", "ending resolves the idea"], hard_incompatibilities=["no intelligible speech", "speaker identity is unresolved for multi-speaker material"]),
    dict(template_id="event_montage", name="Event Montage", intended_source_types=["public_event", "variety_show", "behind_the_scenes"], intended_platforms=["douyin", "xiaohongshu", "bilibili"], intended_aspects=["16:9", "9:16"], structure=[_beat("hook", .06, .14, "immediate event identity or spectacle"), _beat("context", .08, .18, "establish place, people, and occasion"), _beat("build", .52, .70, "vary actions, scales, and participants"), _beat("payoff", .12, .22, "peak moment or clear event close")], shot_duration_range_seconds=(.8, 4.0), rhythm_policy="use visual action and verified musical phrases; vary shot scale and avoid source clumping", source_audio_policy="retain useful ambience and sync moments; avoid chaotic discontinuities", bgm_policy="one explicitly selected track may organize montage after source-vocal and rhythm review", subtitle_density="restrained", maximum_characters_per_second=6.0, transition_restraint="restrained", transition_policy="cuts dominate; limited motivated speed ramps or dissolves require playback review", composition_policy="normalize mixed source quality while preserving action and event identity", required_evidence=["multi-source provenance", "action boundaries", "source quality matrix"], acceptance_checks=["event is identifiable quickly", "sources are visibly varied", "quality jumps are controlled", "ambience/BGM do not fight", "text stays concise", "ending carries event identity"], hard_incompatibilities=["single static talking-head source", "event identity cannot be established"]),
    dict(template_id="short_talking_head", name="Short Talking Head", intended_source_types=["interview", "public_event", "other"], intended_platforms=["douyin", "xiaohongshu"], intended_aspects=["9:16", "16:9"], structure=[_beat("hook", .05, .12, "direct claim or question"), _beat("context", .08, .18, "minimal necessary setup"), _beat("build", .55, .72, "compact argument or instruction"), _beat("outro", .08, .16, "clear close without filler")], shot_duration_range_seconds=(1.5, 8.0), rhythm_policy="tight sentence-level pacing with deliberate pauses; remove filler only with transcript proof", source_audio_policy="voice is primary; silence removal must preserve natural cadence", bgm_policy="optional and aggressively ducked under speech; vocals usually incompatible", subtitle_density="dense", maximum_characters_per_second=8.0, transition_restraint="strict", transition_policy="jump cuts require continuity and face-position review", composition_policy="face and captions must coexist in the target vertical safe region", required_evidence=["transcript", "speech timing", "face-safe composition"], acceptance_checks=["hook lands in first seconds", "no clipped words", "pace is tight but human", "voice remains dominant", "captions fit", "outro is concise"], hard_incompatibilities=["speech is not the main content", "no transcript or manual dialogue boundaries for final application"]),
    dict(template_id="promotional_film", name="Promotional Film", intended_source_types=["public_event", "fan_edit", "behind_the_scenes", "other"], intended_platforms=["douyin", "bilibili", "xiaohongshu"], intended_aspects=["16:9", "9:16"], structure=[_beat("hook", .06, .14, "brand, subject, or offer signal"), _beat("context", .10, .22, "establish value and setting"), _beat("build", .45, .62, "accumulate proof, variety, and aspiration"), _beat("payoff", .12, .22, "strong identity or call-to-action landing")], shot_duration_range_seconds=(1.0, 5.0), rhythm_policy="controlled escalation with intentional information peaks and breathing intervals", source_audio_policy="dialogue, ambience, and designed sound must have explicit hierarchy", bgm_policy="explicit track selection and phrase-aware fitting required before release", subtitle_density="restrained", maximum_characters_per_second=6.0, transition_restraint="moderate", transition_policy="motivated transitions allowed only when they support identity or information hierarchy", composition_policy="preserve subject/product identity, typography safe regions, and platform crop", required_evidence=["promotion goal", "identity/subject proof", "BGM phrase evidence"], acceptance_checks=["identity appears early", "value progression is clear", "shots are varied", "sound hierarchy is controlled", "text hierarchy is readable", "ending has a deliberate identity signal"], hard_incompatibilities=["no identifiable subject or event", "rights policy blocks promotional use"]),
    dict(template_id="documentary_portrait", name="Documentary Portrait", intended_source_types=["interview", "public_event", "behind_the_scenes", "rehearsal"], intended_platforms=["bilibili", "douyin", "xiaohongshu"], intended_aspects=["16:9", "9:16"], structure=[_beat("hook", .06, .14, "human detail or unresolved question"), _beat("context", .15, .28, "ground person, place, and stakes"), _beat("build", .45, .62, "interleave statement, behavior, and environment"), _beat("payoff", .12, .22, "earned reflective or visual ending")], shot_duration_range_seconds=(2.5, 12.0), rhythm_policy="meaning and observation dominate; allow pauses and environmental texture", source_audio_policy="speech and location sound are primary evidence, not noise to erase", bgm_policy="sparse instrumental or no BGM; never manufacture emotion over unsupported meaning", subtitle_density="restrained", maximum_characters_per_second=6.5, transition_restraint="strict", transition_policy="motivated cuts and sound bridges; avoid promotional transition language", composition_policy="preserve environmental context and human detail, not only close-up faces", required_evidence=["transcript or manual semantic notes", "environmental context", "subject continuity"], acceptance_checks=["subject and context are clear", "observational moments remain", "meaning survives edits", "location sound has purpose", "text is restrained", "ending feels earned"], hard_incompatibilities=["only disconnected spectacle shots", "no subject continuity evidence"]),
]


TEMPLATES = [StyleTemplate.model_validate(item) for item in TEMPLATE_DATA]


def build_style_template_package(project_path: Path) -> tuple[Path, Path, StyleTemplatePackage, list[str]]:
    project_path = project_path.resolve()
    config = load_project_config(project_path); root = project_root(project_path); state = load_state(root)
    if state is None: raise StyleTemplatesError("style-templates requires init first")
    data = root / WORKSPACE_DIR / DATA_DIR; sources_path = data / "sources.jsonl"
    if not sources_path.exists(): raise StyleTemplatesError("style-templates requires current source scan")
    sources = [SourceRecord.model_validate_json(line) for line in sources_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not sources: raise StyleTemplatesError("style-templates requires at least one source")
    strategy_path = data / "creative_strategy_package.json"
    source_types = {str(item.source_type.value) for item in sources if item.source_type.value}
    confirmed = {str(item.source_type.value) for item in sources if item.source_type.user_confirmed or item.source_type.method == "sources_csv"}
    brief = " ".join([config.project.title, config.creative_brief.theme, *config.creative_brief.tone]).lower()
    compatibility = [_compatibility(template, source_types, confirmed, brief, config) for template in TEMPLATES]
    best_score = max(item.compatibility_score for item in compatibility)
    best = [item.template_id for item in compatibility if abs(item.compatibility_score - best_score) < .0001]
    evidence_status = "confirmed" if confirmed else "partial" if source_types else "unavailable"
    warnings = ["template compatibility is advisory; no template was selected or applied"]
    if not confirmed: warnings.append("source types are not user/CSV-confirmed; creative-brief signals lower compatibility confidence")
    if not strategy_path.exists(): warnings.append("creative strategy package is unavailable; template-to-strategy fit remains unevaluated")
    key = fingerprint_file(project_path) + fingerprint_file(sources_path) + (fingerprint_file(strategy_path) if strategy_path.exists() else "no_strategy")
    package = StyleTemplatePackage(package_id="style_templates_" + hashlib.sha256(key.encode()).hexdigest()[:20], project_id=config.project.id, project_ref=project_path.relative_to(root).as_posix(), project_fingerprint=fingerprint_file(project_path), sources_ref=sources_path.relative_to(root).as_posix(), sources_fingerprint=fingerprint_file(sources_path), creative_strategy_ref=strategy_path.relative_to(root).as_posix() if strategy_path.exists() else None, creative_strategy_fingerprint=fingerprint_file(strategy_path) if strategy_path.exists() else None, templates=TEMPLATES, compatibility=compatibility, best_match_template_ids=best, source_type_evidence_status=evidence_status, status="degraded" if warnings else "ready", warnings=warnings)
    canonical = data / "style_template_package.json"; report = root / config.paths.output_dir / "style_template_package.md"
    atomic_write_text(canonical, package.model_dump_json(indent=2) + "\n"); atomic_write_text(report, _report(package))
    run_id=new_run_id(); refs=[canonical.relative_to(root).as_posix(),report.relative_to(root).as_posix()]
    inputs=[("project",project_path),("sources",sources_path)]+([("strategies",strategy_path)] if strategy_path.exists() else [])
    state.steps["style_templates"]=StepLedgerEntry(status=StepStatus.completed_with_warnings,input_fingerprint=fingerprint_inputs(inputs),output_refs=refs,last_run_id=run_id,warnings=warnings); state.active_mode=ActiveMode.creative; state.overall_status=OverallStatus.degraded; state.latest_run_id=run_id; state.updated_at=utc_now()
    runs=root/WORKSPACE_DIR/RUNS_DIR/run_id; runs.mkdir(parents=True,exist_ok=True); write_json(runs/"command.json",{"command":"style-templates","project":str(project_path)}); write_json(runs/"environment.json",environment_snapshot()); write_json(runs/"step_result.json",{"step":"style_templates","template_count":6,"best_match_template_ids":best,"template_applied":False,"timeline_mutated":False,"media_rendered":False,"output_refs":refs}); save_state(root,state); write_run_report(root/config.paths.output_dir,state,warnings)
    return canonical,report,package,warnings


def _compatibility(template: StyleTemplate, source_types: set[str], confirmed: set[str], brief: str, config) -> TemplateCompatibility:
    matched=[]; conflicts=[]; missing=[]; score=.15; confidence=.25
    direct = sorted((source_types - {"other"}).intersection(template.intended_source_types)); confirmed_direct=sorted((confirmed - {"other"}).intersection(template.intended_source_types))
    specialized = {"stage_portrait": {"stage_performance", "live_performance", "musical_scene"}, "interview_portrait": {"interview"}, "event_montage": {"public_event", "variety_show"}}
    exact_specialized = bool(set(confirmed_direct).intersection(specialized.get(template.template_id, set())))
    if confirmed_direct: score+=.45 + (.10 if exact_specialized else .02); confidence+=.45; matched.append("confirmed source type: "+", ".join(confirmed_direct))
    elif direct: score+=.28; confidence+=.18; matched.append("unconfirmed source type: "+", ".join(direct))
    keywords={"stage_portrait":["stage","performance","舞台"],"interview_portrait":["interview","访谈","采访"],"event_montage":["event","festival","活动"],"short_talking_head":["interview","talk","访谈","口播"],"promotional_film":["promo","festival","宣传","event"],"documentary_portrait":["human","portrait","人物","访谈","event"]}[template.template_id]
    hits=[word for word in keywords if word in brief]
    brief_bonus={"stage_portrait":.30,"interview_portrait":.30,"event_montage":.30,"short_talking_head":.18,"promotional_film":.18,"documentary_portrait":.18}[template.template_id]
    if hits: score+=brief_bonus; confidence+=.12; matched.append("creative brief signals: "+", ".join(hits))
    if config.creative_brief.platform in template.intended_platforms: score+=.10; matched.append("platform compatible")
    else: conflicts.append("target platform is outside template defaults")
    if config.creative_brief.aspect_ratio in template.intended_aspects: score+=.08; matched.append("aspect compatible")
    else: conflicts.append("target aspect is outside template defaults")
    if "transcript" in template.required_evidence and config.features.transcription.value == "off": missing.append("transcript")
    if not config.content_policy.allow_music and "BGM" in template.bgm_policy: conflicts.append("project music policy disables BGM")
    score=round(min(1,score),4); confidence=round(min(1,confidence),4)
    status="compatible" if score>=.65 and not missing else "conditional" if score>=.35 else "incompatible"
    return TemplateCompatibility(template_id=template.template_id,compatibility_score=score,confidence=confidence,status=status,matched_signals=matched,conflicts=conflicts,missing_evidence=missing,application_constraints=["explicit template selection required","validate exact strategy ranges against template checks","render and review an independent candidate before promotion"])


def _report(package: StyleTemplatePackage) -> str:
    by_id={item.template_id:item for item in package.templates}; lines=["# Style Template Package","",f"- Package: `{package.package_id}`",f"- Status: `{package.status}`",f"- Source type evidence: `{package.source_type_evidence_status}`",f"- Selected template: `{package.selected_template_id}`",f"- Best matches: `{', '.join(package.best_match_template_ids)}`","","## Compatibility",""]
    for item in sorted(package.compatibility,key=lambda value:(-value.compatibility_score,value.template_id)):
        template=by_id[item.template_id]; lines.extend([f"### {template.name}","",f"- Status: `{item.status}`",f"- Score/confidence: `{item.compatibility_score:.3f}` / `{item.confidence:.3f}`",f"- Subtitle density: `{template.subtitle_density}`",f"- Transition restraint: `{template.transition_restraint}`",f"- BGM: {template.bgm_policy}",""])
    lines.extend(["## Warnings",""]+[f"- {item}" for item in package.warnings]); return "\n".join(lines)+"\n"
