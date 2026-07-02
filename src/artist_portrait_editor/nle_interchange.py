from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from artist_portrait_editor.constants import DATA_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.editor_package import EditorPackage
from artist_portrait_editor.models.nle_interchange import (
    NleInterchangeAudioMapping,
    NleInterchangeMarkerMapping,
    NleInterchangePlan,
    NleInterchangeTargetSummary,
    NleInterchangeTimelineMapping,
)
from artist_portrait_editor.run_records import write_json


class NleInterchangeError(RuntimeError):
    pass


NLE_TARGETS = ("fcpxml", "edl", "resolve_csv")


def build_nle_interchange_plan(
    *,
    root: Path,
    project_id: str,
    target: str,
    frame_rate: float,
) -> tuple[Path, Path, Path, Path, NleInterchangePlan]:
    if target not in (*NLE_TARGETS, "all"):
        raise NleInterchangeError("target must be one of fcpxml, edl, resolve_csv, or all")
    if frame_rate <= 0:
        raise NleInterchangeError("frame rate must be greater than zero")
    package_path = root / WORKSPACE_DIR / DATA_DIR / "editor_package.json"
    if not package_path.exists():
        raise NleInterchangeError("nle plan requires .artist-portrait/data/editor_package.json")
    package = EditorPackage.model_validate_json(package_path.read_text(encoding="utf-8"))
    if package.project_id != project_id:
        raise NleInterchangeError("editor package project_id does not match project")

    targets = list(NLE_TARGETS if target == "all" else (target,))
    timeline_mappings: list[NleInterchangeTimelineMapping] = []
    audio_mappings: list[NleInterchangeAudioMapping] = []
    marker_mappings: list[NleInterchangeMarkerMapping] = []
    summaries: list[NleInterchangeTargetSummary] = []
    warnings: list[str] = []
    blocked_reasons: list[str] = []

    for target_name in targets:
        target_timeline = _timeline_mappings(package, target_name, frame_rate)
        target_audio = _audio_mappings(package, target_name)
        target_markers = _marker_mappings(package, target_name)
        timeline_mappings.extend(target_timeline)
        audio_mappings.extend(target_audio)
        marker_mappings.extend(target_markers)
        summaries.append(_summary(target_name, target_timeline, target_audio, target_markers))

    for summary in summaries:
        warnings.extend(summary.format_limitations)
        if summary.status == "blocked":
            blocked_reasons.append(f"{summary.target} has no exportable timeline mappings")

    status = "blocked" if blocked_reasons else "warning" if warnings else "ready"
    key = (
        f"{project_id}:{package.editor_package_id}:{target}:{frame_rate}:"
        f"{len(timeline_mappings)}:{len(audio_mappings)}:{len(marker_mappings)}"
    )
    plan = NleInterchangePlan(
        nle_plan_id="nle_plan_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=project_id,
        editor_package_id=package.editor_package_id,
        target=target,
        status=status,
        frame_rate=frame_rate,
        timeline_mapping_count=len(timeline_mappings),
        audio_mapping_count=len(audio_mappings),
        marker_mapping_count=len(marker_mappings),
        target_summaries=summaries,
        timeline_mappings=timeline_mappings,
        audio_mappings=audio_mappings,
        marker_mappings=marker_mappings,
        warnings=sorted(set(warnings)),
        blocked_reasons=blocked_reasons,
        forbidden_capabilities=[
            "write NLE project files",
            "render media",
            "mutate timeline",
            "move edit points",
            "execute editor instructions",
            "select music automatically",
            "fit music automatically",
            "fabricate BPM or beat grids",
            "call models from the CLI",
            "access the network",
            "use image generation or editing",
        ],
    )

    json_path = root / WORKSPACE_DIR / DATA_DIR / "nle_interchange_plan.json"
    md_path = root / "output" / "nle_interchange_plan.md"
    csv_path = root / "output" / "nle_interchange_map.csv"
    handoff_path = root / "output" / "nle_interchange_handoff.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, plan.model_dump(mode="json"))
    md_path.write_text(render_nle_interchange_plan(plan) + "\n", encoding="utf-8")
    _write_mapping_csv(csv_path, plan)
    write_json(handoff_path, _handoff(plan))
    return json_path, md_path, csv_path, handoff_path, plan


def render_nle_interchange_plan(plan: NleInterchangePlan) -> str:
    lines = [
        "# NLE Interchange Plan",
        "",
        "This plan maps the existing editor package into deterministic NLE interchange candidates. It does not write FCPXML, EDL, Resolve projects, render media, mutate timelines, move edit points, execute instructions, call models, access the network, or use image generation.",
        "",
        f"- Status: `{plan.status}`",
        f"- Target: `{plan.target}`",
        f"- Frame rate: `{plan.frame_rate:.3f}`",
        f"- Editor package: `{plan.editor_package_id}`",
        f"- Timeline mappings: `{plan.timeline_mapping_count}`",
        f"- Audio mappings: `{plan.audio_mapping_count}`",
        f"- Marker mappings: `{plan.marker_mapping_count}`",
        "",
        "## Target Summary",
        "",
    ]
    for summary in plan.target_summaries:
        lines.extend(
            [
                f"### `{summary.target}`",
                "",
                f"- Status: `{summary.status}`",
                f"- Export candidates: `{summary.export_candidate_count}`",
                f"- Warnings: `{summary.warning_count}`",
                f"- Blocked: `{summary.blocked_count}`",
            ]
        )
        if summary.format_limitations:
            lines.append("- Limitations:")
            lines.extend(f"  - {item}" for item in summary.format_limitations)
        lines.append("")
    lines.extend(["## Timeline Mapping", ""])
    for item in plan.timeline_mappings:
        lines.append(
            f"- `{item.target}` `{item.mapping_id}` {item.record_in}-{item.record_out}: "
            f"{item.instruction} status `{item.compatibility}`"
        )
    lines.extend(["", "## Audio Mapping", ""])
    for item in plan.audio_mappings:
        span = (
            f"{item.timeline_start:.3f}-{item.timeline_end:.3f}"
            if item.timeline_start is not None and item.timeline_end is not None
            else "global"
        )
        lines.append(
            f"- `{item.target}` `{item.category}` {span}: {item.instruction} status `{item.compatibility}`"
        )
    lines.extend(["", "## Marker Mapping", ""])
    for item in plan.marker_mappings:
        span = (
            f"{item.timeline_start:.3f}-{item.timeline_end:.3f}"
            if item.timeline_start is not None and item.timeline_end is not None
            else "global"
        )
        lines.append(
            f"- `{item.target}` `{item.marker_name}` {span}: {item.note} status `{item.compatibility}`"
        )
    if plan.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {item}" for item in plan.warnings)
    if plan.blocked_reasons:
        lines.extend(["", "## Blocked Reasons", ""])
        lines.extend(f"- {item}" for item in plan.blocked_reasons)
    lines.extend(["", "## Forbidden Capabilities", ""])
    lines.extend(f"- {item}" for item in plan.forbidden_capabilities)
    return "\n".join(lines)


def _timeline_mappings(
    package: EditorPackage,
    target: str,
    frame_rate: float,
) -> list[NleInterchangeTimelineMapping]:
    mappings: list[NleInterchangeTimelineMapping] = []
    for item in package.timeline_items:
        warnings: list[str] = []
        transition_support = "native"
        compatibility = "export_candidate"
        if target == "edl":
            if item.track_id not in {"v1", "video", "main"}:
                warnings.append("EDL is treated as a single-picture-track candidate; review extra track mapping manually.")
                compatibility = "warning"
            if item.video_transition != "cut" or item.audio_transition != "cut":
                warnings.append("EDL transition expression is limited; transition is preserved as a note.")
                transition_support = "note_only"
                compatibility = "warning"
        if target == "resolve_csv":
            transition_support = "note_only"
            if item.video_transition != "cut" or item.audio_transition != "cut":
                warnings.append("Resolve CSV marker/import flow keeps transition intent as notes, not native transitions.")
                compatibility = "warning"
        mappings.append(
            NleInterchangeTimelineMapping(
                mapping_id=f"{target}_timeline_{item.order:03d}",
                source_item_id=item.item_id,
                target=target,
                order=item.order,
                timeline_start=item.timeline_start,
                timeline_end=item.timeline_end,
                record_in=_timecode(item.timeline_start, frame_rate),
                record_out=_timecode(item.timeline_end, frame_rate),
                source_id=item.source_id,
                clip_id=item.clip_id,
                source_in=item.source_in,
                source_out=item.source_out,
                track_id=item.track_id,
                media_role=item.media_role,
                transition_support=transition_support,
                compatibility=compatibility,
                instruction=(
                    f"Map `{item.clip_id}` into {target} from "
                    f"{_timecode(item.timeline_start, frame_rate)} to "
                    f"{_timecode(item.timeline_end, frame_rate)}."
                ),
                warnings=warnings,
                evidence_refs=item.evidence_refs + [".artist-portrait/data/editor_package.json"],
            )
        )
    return mappings


def _audio_mappings(package: EditorPackage, target: str) -> list[NleInterchangeAudioMapping]:
    mappings: list[NleInterchangeAudioMapping] = []
    for item in package.audio_items:
        compatibility = "export_candidate"
        warnings: list[str] = []
        if target == "edl":
            compatibility = "warning"
            warnings.append("EDL audio support is limited; preserve this as editor notes unless a later EDL writer supports it.")
        elif target == "resolve_csv" and item.category in {"ducking", "beat_alignment"}:
            compatibility = "warning"
            warnings.append("Resolve CSV can preserve this as a marker/note candidate, not as an applied mix operation.")
        mappings.append(
            NleInterchangeAudioMapping(
                mapping_id=f"{target}_audio_{item.order:03d}_{item.category}",
                source_item_id=item.item_id,
                target=target,
                order=item.order,
                category=item.category,
                timeline_start=item.timeline_start,
                timeline_end=item.timeline_end,
                compatibility=compatibility,
                instruction=item.instruction,
                warnings=warnings,
                evidence_refs=item.evidence_refs + [".artist-portrait/data/editor_package.json"],
            )
        )
    return mappings


def _marker_mappings(package: EditorPackage, target: str) -> list[NleInterchangeMarkerMapping]:
    mappings: list[NleInterchangeMarkerMapping] = []
    for item in package.manual_actions:
        warnings: list[str] = []
        compatibility = "export_candidate"
        if target == "edl":
            compatibility = "warning"
            warnings.append("EDL marker/note support is constrained; keep this as comments or sidecar notes.")
        mappings.append(
            NleInterchangeMarkerMapping(
                mapping_id=f"{target}_marker_{item.order:03d}_{item.category}",
                source_action_id=item.action_id,
                target=target,
                order=item.order,
                category=item.category,
                priority=item.priority,
                timeline_start=item.timeline_start,
                timeline_end=item.timeline_end,
                compatibility=compatibility,
                marker_name=f"{item.priority}:{item.category}:{item.action_id}",
                note=item.instruction,
                warnings=warnings,
                evidence_refs=item.evidence_refs + [".artist-portrait/data/editor_package.json"],
            )
        )
    return mappings


def _summary(
    target: str,
    timeline: list[NleInterchangeTimelineMapping],
    audio: list[NleInterchangeAudioMapping],
    markers: list[NleInterchangeMarkerMapping],
) -> NleInterchangeTargetSummary:
    items = [*timeline, *audio, *markers]
    export_count = sum(1 for item in items if item.compatibility == "export_candidate")
    warning_count = sum(1 for item in items if item.compatibility == "warning")
    blocked_count = sum(1 for item in items if item.compatibility == "blocked")
    limitations = _format_limitations(target)
    status = "blocked" if not timeline else "warning" if warning_count or limitations else "ready"
    return NleInterchangeTargetSummary(
        target=target,
        status=status,
        timeline_mapping_count=len(timeline),
        audio_mapping_count=len(audio),
        marker_mapping_count=len(markers),
        export_candidate_count=export_count,
        warning_count=warning_count,
        blocked_count=blocked_count,
        format_limitations=limitations,
    )


def _format_limitations(target: str) -> list[str]:
    if target == "fcpxml":
        return [
            "FCPXML is a future writer target here; V0-046 only emits a mapping plan.",
            "Source asset relinking and exact XML structure are not written in this gate.",
        ]
    if target == "edl":
        return [
            "EDL is single-track and transition-limited compared with the editor package.",
            "Audio ducking, gain automation, beat notes, and rich markers require sidecar notes.",
        ]
    return [
        "Resolve CSV is treated as marker/timeline import guidance, not a full Resolve project.",
        "Audio mix automation and native transitions remain notes until a later writer gate.",
    ]


def _write_mapping_csv(path: Path, plan: NleInterchangePlan) -> None:
    fields = [
        "row_type",
        "target",
        "mapping_id",
        "source_id",
        "order",
        "timeline_start",
        "timeline_end",
        "record_in",
        "record_out",
        "compatibility",
        "instruction",
        "warnings",
        "evidence_refs",
    ]
    rows: list[dict[str, str]] = []
    for item in plan.timeline_mappings:
        rows.append(
            {
                "row_type": "timeline",
                "target": item.target,
                "mapping_id": item.mapping_id,
                "source_id": item.source_item_id,
                "order": str(item.order),
                "timeline_start": f"{item.timeline_start:.3f}",
                "timeline_end": f"{item.timeline_end:.3f}",
                "record_in": item.record_in,
                "record_out": item.record_out,
                "compatibility": item.compatibility,
                "instruction": item.instruction,
                "warnings": ";".join(item.warnings),
                "evidence_refs": ";".join(item.evidence_refs),
            }
        )
    for item in plan.audio_mappings:
        rows.append(
            {
                "row_type": "audio",
                "target": item.target,
                "mapping_id": item.mapping_id,
                "source_id": item.source_item_id,
                "order": str(item.order),
                "timeline_start": "" if item.timeline_start is None else f"{item.timeline_start:.3f}",
                "timeline_end": "" if item.timeline_end is None else f"{item.timeline_end:.3f}",
                "record_in": "",
                "record_out": "",
                "compatibility": item.compatibility,
                "instruction": item.instruction,
                "warnings": ";".join(item.warnings),
                "evidence_refs": ";".join(item.evidence_refs),
            }
        )
    for item in plan.marker_mappings:
        rows.append(
            {
                "row_type": "marker",
                "target": item.target,
                "mapping_id": item.mapping_id,
                "source_id": item.source_action_id,
                "order": str(item.order),
                "timeline_start": "" if item.timeline_start is None else f"{item.timeline_start:.3f}",
                "timeline_end": "" if item.timeline_end is None else f"{item.timeline_end:.3f}",
                "record_in": "",
                "record_out": "",
                "compatibility": item.compatibility,
                "instruction": item.note,
                "warnings": ";".join(item.warnings),
                "evidence_refs": ";".join(item.evidence_refs),
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _handoff(plan: NleInterchangePlan) -> dict:
    return {
        "handoff_type": "nle_interchange_plan",
        "project_id": plan.project_id,
        "status": plan.status,
        "target": plan.target,
        "nle_plan_ref": ".artist-portrait/data/nle_interchange_plan.json",
        "nle_report_ref": "output/nle_interchange_plan.md",
        "nle_map_ref": "output/nle_interchange_map.csv",
        "editor_package_id": plan.editor_package_id,
        "timeline_mapping_count": plan.timeline_mapping_count,
        "audio_mapping_count": plan.audio_mapping_count,
        "marker_mapping_count": plan.marker_mapping_count,
        "warnings": plan.warnings,
        "blocked_reasons": plan.blocked_reasons,
        "forbidden_capabilities": plan.forbidden_capabilities,
        "commands_executed": False,
        "media_rendered": False,
        "timeline_mutated": False,
        "edit_points_moved": False,
        "nle_project_written": False,
        "automatic_music_selection": False,
        "automatic_bgm_fit": False,
        "model_call_performed_by_cli": False,
        "network_performed": False,
        "image_generation_or_editing_used": False,
    }


def _timecode(seconds: float, frame_rate: float) -> str:
    total_frames = int(round(seconds * frame_rate))
    fps = int(round(frame_rate))
    frames = total_frames % fps
    total_seconds = total_frames // fps
    secs = total_seconds % 60
    total_minutes = total_seconds // 60
    mins = total_minutes % 60
    hours = total_minutes // 60
    return f"{hours:02d}:{mins:02d}:{secs:02d}:{frames:02d}"
