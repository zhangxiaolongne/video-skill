from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from pydantic import BaseModel

from artist_portrait_editor.constants import DATA_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.bgm import BgmFitPlan
from artist_portrait_editor.models.editor_package import (
    EditorPackage,
    EditorPackageArtifactBinding,
    EditorPackageAudioItem,
    EditorPackageManualAction,
    EditorPackageTimelineItem,
)
from artist_portrait_editor.models.operator import OperatorRunbook
from artist_portrait_editor.models.rhythm import EditGuidanceReport, RhythmPlan
from artist_portrait_editor.models.state import ProjectState
from artist_portrait_editor.models.timeline import TimelineDraft
from artist_portrait_editor.run_records import write_json


class EditorPackageError(RuntimeError):
    pass


def build_editor_package(
    *,
    root: Path,
    project_id: str,
    state: ProjectState | None,
) -> tuple[Path, Path, Path, Path, EditorPackage]:
    timeline_path = root / "output" / "timeline_draft.json"
    if not timeline_path.exists():
        raise EditorPackageError("editor package requires output/timeline_draft.json")
    timeline = TimelineDraft.model_validate_json(timeline_path.read_text(encoding="utf-8"))
    if timeline.project_id != project_id:
        raise EditorPackageError("timeline project_id does not match project")
    timeline_fingerprint = _fingerprint(timeline_path)
    bgm_fit = _read_optional(root / WORKSPACE_DIR / DATA_DIR / "bgm_fit.json", BgmFitPlan)
    rhythm_plan = _read_optional(root / WORKSPACE_DIR / DATA_DIR / "rhythm_plan.json", RhythmPlan)
    edit_guidance = _read_optional(
        root / WORKSPACE_DIR / DATA_DIR / "edit_guidance.json",
        EditGuidanceReport,
    )
    operator = _read_optional(
        root / WORKSPACE_DIR / DATA_DIR / "operator_runbook.json",
        OperatorRunbook,
    )

    timeline_items = _timeline_items(timeline)
    audio_items = _audio_items(bgm_fit)
    manual_actions = _manual_actions(edit_guidance)
    bindings = _artifact_bindings(root, bgm_fit, rhythm_plan, edit_guidance, operator)
    warnings = _warnings(bgm_fit, rhythm_plan, edit_guidance, operator)
    cue_rows = _cue_rows(timeline_items, audio_items, manual_actions)
    status = "warning" if warnings else "ready"
    key = (
        f"{project_id}:{timeline.timeline_id}:{timeline_fingerprint}:"
        f"{bgm_fit.fit_id if bgm_fit else 'none'}:"
        f"{edit_guidance.edit_guidance_id if edit_guidance else 'none'}:"
        f"{operator.operator_runbook_id if operator else 'none'}:"
        f"{len(cue_rows)}"
    )
    package = EditorPackage(
        editor_package_id="editor_pkg_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        project_id=project_id,
        timeline_id=timeline.timeline_id,
        timeline_fingerprint=timeline_fingerprint,
        status=status,
        target_duration=timeline.target_duration,
        actual_duration=timeline.actual_duration,
        timeline_item_count=len(timeline_items),
        audio_item_count=len(audio_items),
        manual_action_count=len(manual_actions),
        cue_sheet_row_count=len(cue_rows),
        timeline_items=timeline_items,
        audio_items=audio_items,
        manual_actions=manual_actions,
        artifact_bindings=bindings,
        warnings=warnings,
        forbidden_capabilities=[
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

    json_path = root / WORKSPACE_DIR / DATA_DIR / "editor_package.json"
    md_path = root / "output" / "editor_package.md"
    csv_path = root / "output" / "cue_sheet.csv"
    handoff_path = root / "output" / "editor_handoff.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, package.model_dump(mode="json"))
    md_path.write_text(render_editor_package(package) + "\n", encoding="utf-8")
    _write_cue_sheet(csv_path, cue_rows)
    write_json(handoff_path, _editor_handoff(package))
    return json_path, md_path, csv_path, handoff_path, package


def render_editor_package(package: EditorPackage) -> str:
    lines = [
        "# Editor Package",
        "",
        "This package translates existing canonical timeline, BGM, rhythm, manual guidance, and operator evidence into editor-facing instructions. It does not render media, mutate the timeline, move edit points, select music, fit music, call models, access the network, or use image generation.",
        "",
        f"- Status: `{package.status}`",
        f"- Timeline: `{package.timeline_id}`",
        f"- Duration: `{package.actual_duration:.3f}` / target `{package.target_duration:.3f}` seconds",
        f"- Timeline items: `{package.timeline_item_count}`",
        f"- Audio items: `{package.audio_item_count}`",
        f"- Manual actions: `{package.manual_action_count}`",
        f"- Cue sheet rows: `{package.cue_sheet_row_count}`",
        "",
        "## Timeline Items",
        "",
    ]
    for item in package.timeline_items:
        lines.extend(
            [
                f"### `{item.item_id}`",
                "",
                f"- Time: `{item.timeline_start:.3f}` to `{item.timeline_end:.3f}`",
                f"- Source: `{item.source_id}` clip `{item.clip_id}` from `{item.source_in:.3f}` to `{item.source_out:.3f}`",
                f"- Track: `{item.track_id}` / role `{item.media_role}`",
                f"- Transitions: video `{item.video_transition}`, audio `{item.audio_transition}`",
                f"- Intent: {item.creative_intent}",
                "",
            ]
        )
    lines.extend(["## Audio Instructions", ""])
    if package.audio_items:
        for item in package.audio_items:
            span = (
                f"`{item.timeline_start:.3f}` to `{item.timeline_end:.3f}`"
                if item.timeline_start is not None and item.timeline_end is not None
                else "`global`"
            )
            lines.append(f"- `{item.category}` {span}: {item.instruction}")
    else:
        lines.append("- `none`")
    lines.extend(["", "## Manual Edit Actions", ""])
    if package.manual_actions:
        for action in package.manual_actions:
            span = (
                f"`{action.timeline_start:.3f}` to `{action.timeline_end:.3f}`"
                if action.timeline_start is not None and action.timeline_end is not None
                else "`global`"
            )
            lines.append(
                f"- `{action.priority}` `{action.category}` {span}: {action.instruction}"
            )
    else:
        lines.append("- `none`")
    lines.extend(["", "## Artifact Bindings", ""])
    lines.extend(
        f"- `{binding.ref}`: `{binding.status}`; {binding.summary}"
        for binding in package.artifact_bindings
    )
    if package.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in package.warnings)
    lines.extend(["", "## Forbidden Capabilities", ""])
    lines.extend(f"- {item}" for item in package.forbidden_capabilities)
    return "\n".join(lines)


def _timeline_items(timeline: TimelineDraft) -> list[EditorPackageTimelineItem]:
    items: list[EditorPackageTimelineItem] = []
    for index, segment in enumerate(
        sorted(timeline.segments, key=lambda item: (item.timeline_start, item.track_id, item.segment_id)),
        start=1,
    ):
        items.append(
            EditorPackageTimelineItem(
                item_id=f"timeline_{index:03d}_{segment.segment_id}",
                order=index,
                track_id=segment.track_id,
                timeline_start=segment.timeline_start,
                timeline_end=segment.timeline_end,
                source_id=segment.source_id,
                clip_id=segment.clip_id,
                source_in=segment.source_in,
                source_out=segment.source_out,
                media_role=segment.media_role.value,
                video_transition=segment.video_transition.value,
                audio_transition=segment.audio_transition.value,
                creative_intent=segment.creative_intent,
                evidence_refs=[evidence.ref for evidence in segment.evidence],
            )
        )
    return items


def _audio_items(plan: BgmFitPlan | None) -> list[EditorPackageAudioItem]:
    if plan is None:
        return []
    items: list[EditorPackageAudioItem] = []
    order = 1
    for index, segment in enumerate(plan.segments, start=1):
        items.append(
            EditorPackageAudioItem(
                item_id=f"bgm_segment_{index:03d}",
                order=order,
                category="bgm_segment",
                timeline_start=segment.timeline_start,
                timeline_end=segment.timeline_end,
                instruction=(
                    f"Place BGM candidate `{plan.music_candidate_id}` source "
                    f"{segment.source_in:.3f}-{segment.source_out:.3f}s at "
                    f"{segment.timeline_start:.3f}-{segment.timeline_end:.3f}s "
                    f"using fit mode `{plan.fit_mode}`."
                ),
                evidence_refs=[".artist-portrait/data/bgm_fit.json"],
            )
        )
        order += 1
    items.append(
        EditorPackageAudioItem(
            item_id="bgm_gain",
            order=order,
            category="gain",
            instruction=f"Set fitted BGM target gain to `{plan.target_gain_db:.2f}` dB.",
            evidence_refs=[".artist-portrait/data/bgm_fit.json"],
        )
    )
    order += 1
    if plan.fade_in_seconds > 0:
        items.append(
            EditorPackageAudioItem(
                item_id="bgm_fade_in",
                order=order,
                category="fade",
                timeline_start=0.0,
                timeline_end=plan.fade_in_seconds,
                instruction=f"Apply BGM fade-in over `{plan.fade_in_seconds:.3f}` seconds.",
                evidence_refs=[".artist-portrait/data/bgm_fit.json"],
            )
        )
        order += 1
    if plan.fade_out_seconds > 0:
        start = max(plan.target_duration - plan.fade_out_seconds, 0.0)
        items.append(
            EditorPackageAudioItem(
                item_id="bgm_fade_out",
                order=order,
                category="fade",
                timeline_start=start,
                timeline_end=plan.target_duration,
                instruction=f"Apply BGM fade-out over `{plan.fade_out_seconds:.3f}` seconds.",
                evidence_refs=[".artist-portrait/data/bgm_fit.json"],
            )
        )
        order += 1
    if plan.controls.ducking_enabled and not plan.ducking_intervals:
        items.append(
            EditorPackageAudioItem(
                item_id="bgm_ducking_policy",
                order=order,
                category="ducking",
                instruction=(
                    f"Ducking is enabled at `{plan.controls.ducking_gain_db:.2f}` dB, "
                    "but no concrete ducking interval was generated; review speech/original-audio moments manually."
                ),
                evidence_refs=[".artist-portrait/data/bgm_fit.json"],
            )
        )
        order += 1
    for index, duck in enumerate(plan.ducking_intervals, start=1):
        items.append(
            EditorPackageAudioItem(
                item_id=f"bgm_ducking_{index:03d}",
                order=order,
                category="ducking",
                timeline_start=duck.start,
                timeline_end=duck.end,
                instruction=f"Duck BGM by `{duck.gain_db:.2f}` dB because {duck.reason}.",
                evidence_refs=[".artist-portrait/data/bgm_fit.json"],
            )
        )
        order += 1
    items.append(
        EditorPackageAudioItem(
            item_id="bgm_beat_alignment",
            order=order,
            category="beat_alignment",
            instruction=(
                f"Beat alignment status is `{plan.beat_alignment_status}`; do not move edit points automatically."
            ),
            evidence_refs=[ref for ref in (".artist-portrait/data/bgm_fit.json", plan.beat_grid_ref) if ref],
        )
    )
    return items


def _manual_actions(guidance: EditGuidanceReport | None) -> list[EditorPackageManualAction]:
    if guidance is None:
        return []
    return [
        EditorPackageManualAction(
            action_id=action.action_id,
            order=action.order,
            category=action.category,
            priority=action.priority,
            timeline_start=action.timeline_start,
            timeline_end=action.timeline_end,
            instruction=action.recommendation,
            rationale=action.rationale,
            evidence_refs=action.evidence_refs,
            manual_only=action.manual_only,
            edits_applied=action.edits_applied,
        )
        for action in sorted(guidance.actions, key=lambda item: (item.order, item.action_id))
    ]


def _artifact_bindings(
    root: Path,
    bgm_fit: BgmFitPlan | None,
    rhythm_plan: RhythmPlan | None,
    edit_guidance: EditGuidanceReport | None,
    operator: OperatorRunbook | None,
) -> list[EditorPackageArtifactBinding]:
    specs = [
        ("timeline", "output/timeline_draft.json", True, "canonical timeline draft"),
        ("bgm_fit", ".artist-portrait/data/bgm_fit.json", bgm_fit is not None, "explicit BGM fit plan"),
        ("rhythm_plan", ".artist-portrait/data/rhythm_plan.json", rhythm_plan is not None, "rhythm planning evidence"),
        ("edit_guidance", ".artist-portrait/data/edit_guidance.json", edit_guidance is not None, "manual phrase-level guidance"),
        ("operator_runbook", ".artist-portrait/data/operator_runbook.json", operator is not None, "operator state summary"),
    ]
    bindings: list[EditorPackageArtifactBinding] = []
    for artifact_id, ref, loaded, summary in specs:
        exists = (root / ref).exists()
        if exists and loaded:
            status = "present"
        elif exists:
            status = "missing"
        elif artifact_id in {"bgm_fit", "rhythm_plan", "edit_guidance", "operator_runbook"}:
            status = "optional_missing"
        else:
            status = "missing"
        bindings.append(
            EditorPackageArtifactBinding(
                artifact_id=artifact_id,
                ref=ref,
                status=status,
                summary=summary,
            )
        )
    return bindings


def _warnings(
    bgm_fit: BgmFitPlan | None,
    rhythm_plan: RhythmPlan | None,
    edit_guidance: EditGuidanceReport | None,
    operator: OperatorRunbook | None,
) -> list[str]:
    warnings: list[str] = []
    if bgm_fit is None:
        warnings.append("BGM fit plan is missing; package contains no fitted music placement.")
    if rhythm_plan is None:
        warnings.append("Rhythm plan is missing; package contains no rhythm audit binding.")
    if edit_guidance is None:
        warnings.append("Edit guidance is missing; package contains no manual phrase-level actions.")
    if operator is None:
        warnings.append("Operator runbook is missing; package contains no operator state binding.")
    return warnings


def _cue_rows(
    timeline_items: list[EditorPackageTimelineItem],
    audio_items: list[EditorPackageAudioItem],
    manual_actions: list[EditorPackageManualAction],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in timeline_items:
        rows.append(
            {
                "row_type": "timeline",
                "item_id": item.item_id,
                "order": str(item.order),
                "timeline_start": f"{item.timeline_start:.3f}",
                "timeline_end": f"{item.timeline_end:.3f}",
                "track": item.track_id,
                "source": item.source_id,
                "instruction": (
                    f"Use clip `{item.clip_id}` source {item.source_in:.3f}-{item.source_out:.3f}s; "
                    f"video transition `{item.video_transition}`, audio transition `{item.audio_transition}`."
                ),
                "evidence_refs": ";".join(item.evidence_refs),
            }
        )
    for item in audio_items:
        rows.append(
            {
                "row_type": "audio",
                "item_id": item.item_id,
                "order": str(item.order),
                "timeline_start": "" if item.timeline_start is None else f"{item.timeline_start:.3f}",
                "timeline_end": "" if item.timeline_end is None else f"{item.timeline_end:.3f}",
                "track": "audio",
                "source": item.category,
                "instruction": item.instruction,
                "evidence_refs": ";".join(item.evidence_refs),
            }
        )
    for action in manual_actions:
        rows.append(
            {
                "row_type": "manual_action",
                "item_id": action.action_id,
                "order": str(action.order),
                "timeline_start": "" if action.timeline_start is None else f"{action.timeline_start:.3f}",
                "timeline_end": "" if action.timeline_end is None else f"{action.timeline_end:.3f}",
                "track": action.category,
                "source": action.priority,
                "instruction": action.instruction,
                "evidence_refs": ";".join(action.evidence_refs),
            }
        )
    return rows


def _write_cue_sheet(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "row_type",
        "item_id",
        "order",
        "timeline_start",
        "timeline_end",
        "track",
        "source",
        "instruction",
        "evidence_refs",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _editor_handoff(package: EditorPackage) -> dict:
    return {
        "handoff_type": "editor_package",
        "project_id": package.project_id,
        "status": package.status,
        "editor_package_ref": ".artist-portrait/data/editor_package.json",
        "editor_report_ref": "output/editor_package.md",
        "cue_sheet_ref": "output/cue_sheet.csv",
        "timeline_id": package.timeline_id,
        "timeline_item_count": package.timeline_item_count,
        "audio_item_count": package.audio_item_count,
        "manual_action_count": package.manual_action_count,
        "warnings": package.warnings,
        "forbidden_capabilities": package.forbidden_capabilities,
        "commands_executed": False,
        "media_rendered": False,
        "timeline_mutated": False,
        "edit_points_moved": False,
        "automatic_music_selection": False,
        "automatic_bgm_fit": False,
        "model_call_performed_by_cli": False,
        "network_performed": False,
        "image_generation_or_editing_used": False,
    }


def _fingerprint(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _read_optional(path: Path, model: type[BaseModel]):
    if not path.exists():
        return None
    return model.model_validate_json(path.read_text(encoding="utf-8"))
