from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "golden_artist_portrait"
ARTIST_PORTRAIT = Path(
    shutil.which("artist-portrait") or ROOT / ".venv" / "bin" / "artist-portrait"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the golden artist portrait baseline.")
    parser.add_argument("--workspace", required=True, help="Directory to create or reuse.")
    parser.add_argument("--keep", action="store_true", help="Keep existing workspace files.")
    parser.add_argument("--json", action="store_true", help="Print manifest JSON.")
    args = parser.parse_args(argv)

    workspace = Path(args.workspace).resolve()
    if not args.keep and workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    prepare_workspace(workspace)
    generate_media(workspace)
    manifest = run_pipeline(workspace)
    write_manifest(workspace, manifest)
    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"golden baseline passed: {workspace / 'output' / 'golden_baseline_manifest.json'}")
    return 0


def prepare_workspace(workspace: Path) -> None:
    for item in FIXTURE.iterdir():
        target = workspace / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
    (workspace / "media").mkdir(exist_ok=True)
    (workspace / "output").mkdir(exist_ok=True)


def generate_media(workspace: Path) -> None:
    media = workspace / "media"
    require_binary("ffmpeg")
    require_binary("ffprobe")
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=128x72:rate=24:duration=2.4",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=220:duration=2.4",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(media / "interview_rehearsal.mp4"),
        ]
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "smptebars=size=128x72:rate=24:duration=2.2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=330:duration=2.2",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(media / "stage_fragment.mp4"),
        ]
    )
    # Uploaded BGM is generated later so source scanning sees only video materials.


def run_pipeline(workspace: Path) -> dict:
    project = workspace / "project.yaml"
    steps: list[dict] = []

    def cli(*parts: str, expect: tuple[int, ...] = (0,)) -> dict | None:
        command = [str(ARTIST_PORTRAIT), *parts]
        completed = subprocess.run(
            command,
            cwd=workspace,
            capture_output=True,
            text=True,
        )
        steps.append(
            {
                "command": " ".join(["artist-portrait", *parts]),
                "exit_code": completed.returncode,
            }
        )
        if completed.returncode not in expect:
            raise SystemExit(
                f"command failed in golden baseline: {' '.join(command)}\n"
                f"exit={completed.returncode}\nstdout={completed.stdout}\nstderr={completed.stderr}"
            )
        if "--json" in parts:
            return json.loads(completed.stdout)
        return None

    cli("validate", "--project", str(project))
    cli("init", "--project", str(project), "--quiet")
    initial_workflow = cli("workflow", "--project", str(project), "--target", "delivery", "--json", expect=(1,))
    assert_equal(initial_workflow["workflow_plan"]["current_stage_id"], "setup", "initial workflow stage")
    cli("scan", "--project", str(project), "--quiet")
    cli("segment", "--project", str(project), "--quiet")
    cli("keyframes", "--project", str(project), "--quiet", expect=(0, 1))
    cli("analyze", "--project", str(project), "--quiet")
    cli("map", "--project", str(project), "--quiet")
    brief = cli("brief", "--project", str(project), "--json", expect=(0, 1))
    assert_equal(brief["edit_brief"]["duration_source"], "system_recommended", "edit brief duration source")
    assert_false(brief["edit_brief"]["media_rendered"], "edit brief rendered media")
    assert_false(brief["edit_brief"]["network_performed"], "edit brief accessed network")
    scores = cli("score", "--project", str(project), "--json", expect=(0, 1))
    assert_equal(scores["output"], ".artist-portrait/data/clip_scores.jsonl", "clip score output")
    assert_false(scores["clip_scores"][0]["media_rendered"], "clip score rendered media")
    assert_false(scores["clip_scores"][0]["network_performed"], "clip score accessed network")
    blocked = cli("propose", "--project", str(project), "--json", expect=(1,))
    assert_equal(blocked["status"], "blocked", "proposal handoff status")
    write_valid_proposals_from_context(workspace)
    candidate = workspace / "proposal_candidate.json"
    canonical = workspace / ".artist-portrait" / "data" / "proposals.json"
    candidate.write_bytes(canonical.read_bytes())
    canonical.unlink()
    cli("propose", "--project", str(project), "--agent-output", str(candidate), "--quiet", expect=(0, 1))
    cli("timeline", "--project", str(project), "--proposal", "proposal_safe", "--quiet", expect=(0, 1))

    generate_bgm(workspace)
    bgm_import = cli(
        "bgm",
        "import",
        "--project",
        str(project),
        "--file",
        "media/uploaded_bgm.wav",
        "--rights-status",
        "owned",
        "--json",
        expect=(0, 1),
    )
    candidate_id = bgm_import["candidate"]["music_candidate_id"]
    bgm_analysis = cli("bgm", "analyze", "--project", str(project), "--json", expect=(0, 1))
    assert_false(bgm_analysis["analysis"]["automatic_music_selection"], "BGM analysis selected music")
    bgm_rhythm = cli("bgm", "rhythm", "--project", str(project), "--json", expect=(0, 1))
    assert_false(
        bgm_rhythm["bgm_rhythm_intelligence"]["fabricated_bpm_or_beats"],
        "BGM rhythm fabricated BPM",
    )
    cli(
        "bgm",
        "fit",
        "--project",
        str(project),
        "--candidate",
        candidate_id,
        "--fit-mode",
        "loop",
        "--fade-in-seconds",
        "0.15",
        "--fade-out-seconds",
        "0.2",
        "--ducking-gain-db",
        "-10",
        "--quiet",
        expect=(0, 1),
    )
    bgm_review = cli("bgm", "review", "--project", str(project), "--json", expect=(0, 1))
    if bgm_review["status"] not in {"passed", "warning"}:
        raise SystemExit("golden BGM review did not complete")
    sound = cli("sound", "--project", str(project), "--json", expect=(0, 1))
    if sound["sound_decision"]["automatic_music_selection"] is not False:
        raise SystemExit("golden sound decision selected music automatically")

    cli(
        "rhythm",
        "--project",
        str(project),
        "--intent",
        str(workspace / "annotations" / "rhythm_intent.json"),
        "--json",
        expect=(0, 1),
    )
    edit_guidance = cli("rhythm", "--project", str(project), "--edit-guidance", "--json", expect=(0, 1))
    if edit_guidance["edit_guidance"]["action_count"] < 10:
        raise SystemExit("golden edit guidance lacks manual actions")
    cli("preview", "--project", str(project), "--width", "320", "--fps", "10", "--quiet", expect=(0, 1))
    cli("rhythm", "--project", str(project), "--qc", "--json", expect=(0, 1))
    cut_review = cli("cut-review", "--project", str(project), "--json", expect=(0, 1))
    if cut_review["cut_review"]["timeline_mutated"] is not False:
        raise SystemExit("golden cut review mutated timeline")
    revision = cli(
        "revise",
        "--project",
        str(project),
        "--intent",
        "make the preview more emotional but preserve the current timing",
        "--request-type",
        "more_emotional",
        "--json",
        expect=(0, 1),
    )
    if revision["revision_plan"]["timeline_mutated"] is not False:
        raise SystemExit("golden preview revision mutated timeline")
    if revision["revision_plan"]["media_rendered"] is not False:
        raise SystemExit("golden preview revision rendered media")
    revision_application = cli(
        "apply-revision",
        "--project",
        str(project),
        "--version-id",
        "revision_candidate_1",
        "--json",
        expect=(0, 1),
    )
    if revision_application["revision_application"]["canonical_timeline_mutated"] is not False:
        raise SystemExit("golden preview revision application mutated canonical timeline")
    if revision_application["revision_application"]["media_rendered"] is not False:
        raise SystemExit("golden preview revision application rendered media")
    revision_promotion = cli(
        "promote-revision",
        "--project",
        str(project),
        "--revision-application-id",
        revision_application["revision_application"]["revision_application_id"],
        "--json",
        expect=(0, 1),
    )
    if revision_promotion["revision_promotion"]["canonical_timeline_mutated"] is not True:
        raise SystemExit("golden preview revision promotion did not mutate canonical timeline")
    if revision_promotion["revision_promotion"]["media_rendered"] is not False:
        raise SystemExit("golden preview revision promotion rendered media")
    cli(
        "bgm",
        "fit",
        "--project",
        str(project),
        "--candidate",
        candidate_id,
        "--fit-mode",
        "loop",
        "--fade-in-seconds",
        "0.15",
        "--fade-out-seconds",
        "0.2",
        "--ducking-gain-db",
        "-10",
        "--quiet",
        expect=(0, 1),
    )
    cli("sound", "--project", str(project), "--quiet", expect=(0, 1))
    cli(
        "rhythm",
        "--project",
        str(project),
        "--intent",
        str(workspace / "annotations" / "rhythm_intent.json"),
        "--quiet",
        expect=(0, 1),
    )
    cli("preview", "--project", str(project), "--width", "320", "--fps", "10", "--quiet", expect=(0, 1))
    cli("rhythm", "--project", str(project), "--qc", "--quiet", expect=(0, 1))
    cli("cut-review", "--project", str(project), "--quiet", expect=(0, 1))
    preview_acceptance = cli("acceptance", "--project", str(project), "--profile", "preview", "--json")
    assert_true(preview_acceptance["preview_ready"], "preview acceptance")
    cli("export", "--project", str(project), "--profile", "review_720p", "--quiet", expect=(0, 1))
    cli("rhythm", "--project", str(project), "--qc", "--json", expect=(0, 1))
    cut_review = cli("cut-review", "--project", str(project), "--json", expect=(0, 1))
    if cut_review["cut_review"]["media_rendered"] is not False:
        raise SystemExit("golden cut review rendered media")
    revision = cli(
        "revise",
        "--project",
        str(project),
        "--intent",
        "make the final version more emotional and compare tradeoffs",
        "--request-type",
        "more_emotional",
        "--json",
        expect=(0, 1),
    )
    if revision["revision_plan"]["edit_points_moved"] is not False:
        raise SystemExit("golden final revision moved edit points")
    if revision["revision_plan"]["automatic_music_selection"] is not False:
        raise SystemExit("golden final revision selected music")
    revision_application = cli(
        "apply-revision",
        "--project",
        str(project),
        "--version-id",
        "revision_candidate_1",
        "--json",
        expect=(0, 1),
    )
    if revision_application["revision_application"]["canonical_edit_points_moved"] is not False:
        raise SystemExit("golden final revision application moved canonical edit points")
    if revision_application["revision_application"]["automatic_bgm_fit"] is not False:
        raise SystemExit("golden final revision application fitted BGM")
    revision_promotion = cli(
        "promote-revision",
        "--project",
        str(project),
        "--revision-application-id",
        revision_application["revision_application"]["revision_application_id"],
        "--json",
        expect=(0, 1),
    )
    if revision_promotion["revision_promotion"]["canonical_timeline_mutated"] is not True:
        raise SystemExit("golden final revision promotion did not mutate canonical timeline")
    if revision_promotion["revision_promotion"]["automatic_bgm_fit"] is not False:
        raise SystemExit("golden final revision promotion fitted BGM")
    cli(
        "bgm",
        "fit",
        "--project",
        str(project),
        "--candidate",
        candidate_id,
        "--fit-mode",
        "loop",
        "--fade-in-seconds",
        "0.15",
        "--fade-out-seconds",
        "0.2",
        "--ducking-gain-db",
        "-10",
        "--quiet",
        expect=(0, 1),
    )
    cli("sound", "--project", str(project), "--quiet", expect=(0, 1))
    cli(
        "rhythm",
        "--project",
        str(project),
        "--intent",
        str(workspace / "annotations" / "rhythm_intent.json"),
        "--quiet",
        expect=(0, 1),
    )
    cli("preview", "--project", str(project), "--width", "320", "--fps", "10", "--quiet", expect=(0, 1))
    cli("export", "--project", str(project), "--profile", "review_720p", "--quiet", expect=(0, 1))
    cli("rhythm", "--project", str(project), "--qc", "--quiet", expect=(0, 1))
    cli("cut-review", "--project", str(project), "--quiet", expect=(0, 1))
    delivery_acceptance = cli("acceptance", "--project", str(project), "--profile", "delivery", "--json")
    assert_true(delivery_acceptance["final_export_ready"], "delivery acceptance")
    operator = cli("operator", "--project", str(project), "--target", "delivery", "--json", expect=(0, 1))
    if operator["operator_runbook"]["next_command"] not in {
        "artist-portrait editor-package --project <project.yaml>",
        "artist-portrait nle-plan --project <project.yaml> --target all",
        "artist-portrait fcpxml --project <project.yaml> --draft",
    }:
        raise SystemExit(
            "golden operator did not point to handoff chain: "
            f"{operator['operator_runbook']['next_command']!r}"
        )
    editor = cli("editor-package", "--project", str(project), "--json", expect=(0, 1))
    if editor["editor_package"]["manual_action_count"] < 10:
        raise SystemExit("golden editor package lacks manual actions")
    nle = cli("nle-plan", "--project", str(project), "--target", "all", "--json", expect=(0, 1))
    assert_false(nle["nle_interchange_plan"]["nle_project_written"], "NLE project was written")
    fcpxml = cli("fcpxml", "--project", str(project), "--draft", "--json", expect=(0, 1))
    assert_true(fcpxml["fcpxml_validation"]["xml_parse_passed"], "FCPXML XML parse")
    assert_false(fcpxml["fcpxml_validation"]["import_verified"], "FCPXML import verification")
    final_workflow = cli("workflow", "--project", str(project), "--target", "delivery", "--json")
    assert_equal(final_workflow["workflow_plan"]["status"], "ready", "final workflow status")

    artifact_contract = json.loads(
        (workspace / "expected" / "artifact_contract.json").read_text(encoding="utf-8")
    )
    artifacts = artifact_status(workspace, artifact_contract["required_artifacts"])
    missing = [item["path"] for item in artifacts if not item["exists"]]
    if missing:
        raise SystemExit(f"golden baseline missing artifacts: {missing}")

    guardrails = {
        "commands_executed_by_workflow": final_workflow["workflow_plan"]["commands_executed"],
        "automatic_music_selection": any(
            value is not False
            for value in [
                bgm_analysis["analysis"]["automatic_music_selection"],
                bgm_rhythm["bgm_rhythm_intelligence"]["automatic_music_selection"],
                editor["editor_package"]["automatic_music_selection"],
                nle["nle_interchange_plan"]["automatic_music_selection"],
                fcpxml["fcpxml_draft"]["automatic_music_selection"],
            ]
        ),
        "automatic_bgm_fit_without_explicit_candidate": False,
        "timeline_mutated_by_guidance": edit_guidance["edit_guidance"]["timeline_mutated"],
        "nle_import_performed": fcpxml["fcpxml_draft"]["nle_import_performed"],
        "network_performed": any(
            value is not False
            for value in [
                bgm_rhythm["bgm_rhythm_intelligence"]["network_performed"],
                editor["editor_package"]["network_performed"],
                nle["nle_interchange_plan"]["network_performed"],
                fcpxml["fcpxml_draft"]["network_performed"],
            ]
        ),
        "model_call_performed_by_cli": any(
            value is not False
            for value in [
                editor["editor_package"]["model_call_performed_by_cli"],
                nle["nle_interchange_plan"]["model_call_performed_by_cli"],
                fcpxml["fcpxml_draft"]["model_call_performed_by_cli"],
            ]
        ),
        "image_generation_or_editing_used": any(
            value is not False
            for value in [
                editor["editor_package"]["image_generation_or_editing_used"],
                nle["nle_interchange_plan"]["image_generation_or_editing_used"],
                fcpxml["fcpxml_draft"]["image_generation_or_editing_used"],
            ]
        ),
    }
    for key, expected in artifact_contract["required_guardrails"].items():
        if guardrails.get(key) is not expected:
            raise SystemExit(f"golden guardrail failed: {key}={guardrails.get(key)}")

    return {
        "schema_version": "1.0",
        "baseline_id": "golden_artist_portrait_stage_03",
        "project_id": "golden_artist_portrait_001",
        "status": "passed",
        "workspace": str(workspace),
        "source_count": 2,
        "media_hashes": media_hashes(workspace),
        "artifact_count": len(artifacts),
        "artifacts": artifacts,
        "guardrails": guardrails,
        "acceptance": {
            "preview_ready": preview_acceptance["preview_ready"],
            "delivery_ready": delivery_acceptance["final_export_ready"],
            "workflow_ready": final_workflow["workflow_plan"]["status"] == "ready",
        },
        "counts": {
            "edit_guidance_actions": edit_guidance["edit_guidance"]["action_count"],
            "editor_package_actions": editor["editor_package"]["manual_action_count"],
            "nle_timeline_mappings": nle["nle_interchange_plan"]["timeline_mapping_count"],
            "fcpxml_clips": fcpxml["fcpxml_draft"]["clip_count"],
            "fcpxml_markers": fcpxml["fcpxml_draft"]["marker_count"],
        },
        "steps": steps,
    }


def write_valid_proposals_from_context(root: Path) -> None:
    context = json.loads(
        (root / ".artist-portrait" / "data" / "proposal_context.json").read_text(
            encoding="utf-8"
        )
    )
    clip_ids = [clip["clip_id"] for clip in context["clips"]]
    analysis_ids = [item["analysis_id"] for item in context["analyses"]]
    proposals = []
    proposal_specs = {
        "proposal_safe": {
            "title": "Evidence First Portrait",
            "story": ["open with rehearsal context", "move into stage contrast", "close on voice texture"],
            "sound": ["Speech-first bed with low-gain BGM and conservative ducking"],
            "visual": ["rehearsal texture", "direct continuity", "restrained ending"],
            "counter": "What if the safest version starts from interview evidence before stage motion?",
        },
        "proposal_advanced": {
            "title": "Parallel Voices",
            "story": ["intercut interview audio", "contrast body rhythm", "resolve with soft landing"],
            "sound": ["Rhythmic BGM loop supports cross-cut pacing while retained audio remains primary"],
            "visual": ["parallel staging", "motion contrast", "body-to-voice match"],
            "counter": "What if the middle section alternates stage geometry and rehearsal stillness more aggressively?",
        },
        "proposal_risky": {
            "title": "Delayed Reveal",
            "story": ["start with abstract stage motion", "delay identity cue", "end with silence"],
            "sound": ["BGM enters late, then fades into a deliberate quiet ending"],
            "visual": ["abstract opening", "delayed subject cue", "negative-space close"],
            "counter": "What if the ending drops music earlier and leaves only retained source audio?",
        },
    }
    for proposal_id, spec in proposal_specs.items():
        proposals.append(
            {
                "proposal_id": proposal_id,
                "title": spec["title"],
                "theme": context["creative_brief"]["theme"],
                "audience": context["creative_brief"]["audience"],
                "required_clip_ids": clip_ids,
                "fact_refs": [
                    *({"type": "clip", "ref": clip_id} for clip_id in clip_ids),
                    *({"type": "analysis", "ref": analysis_id} for analysis_id in analysis_ids),
                    {"type": "material_map", "ref": context["material_map_ref"]},
                ],
                "story_structure": spec["story"],
                "sound_structure": spec["sound"],
                "visual_motifs": spec["visual"],
                "risks": ["synthetic visual fixture cannot prove real semantic recognition"],
                "minimum_viable_timeline": ["use both source clips and preserve retained audio"],
                "missing_material": [],
                "counter_proposal": spec["counter"],
            }
        )
    payload = {
        "proposal_set_id": "proposal_set_golden_baseline",
        "project_id": context["project_id"],
        "map_fingerprint": context["material_map_fingerprint"],
        "method": "codex_host_agent_golden_baseline",
        "method_version": "stage-03",
        "proposals": proposals,
        "evidence": [{"type": "proposal_context", "ref": context["context_id"]}],
        "warnings": [],
    }
    (root / ".artist-portrait" / "data" / "proposals.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def generate_bgm(workspace: Path) -> None:
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1.2",
            "-ac",
            "1",
            "-ar",
            "44100",
            str(workspace / "media" / "uploaded_bgm.wav"),
        ]
    )


def media_hashes(workspace: Path) -> dict[str, str]:
    refs = [
        workspace / "media" / "interview_rehearsal.mp4",
        workspace / "media" / "stage_fragment.mp4",
        workspace / "media" / "uploaded_bgm.wav",
    ]
    return {path.name: sha256(path) for path in refs if path.exists()}


def write_manifest(workspace: Path, manifest: dict) -> None:
    output = workspace / "output"
    output.mkdir(exist_ok=True)
    (output / "golden_baseline_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Golden Baseline Report",
        "",
        f"- Status: `{manifest['status']}`",
        f"- Project: `{manifest['project_id']}`",
        f"- Sources: `{manifest['source_count']}`",
        f"- Artifacts checked: `{manifest['artifact_count']}`",
        f"- Preview ready: `{manifest['acceptance']['preview_ready']}`",
        f"- Delivery ready: `{manifest['acceptance']['delivery_ready']}`",
        f"- Workflow ready: `{manifest['acceptance']['workflow_ready']}`",
        "",
        "## Guardrails",
        "",
    ]
    for key, value in manifest["guardrails"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Counts", ""])
    for key, value in manifest["counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    (output / "golden_baseline_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def artifact_status(workspace: Path, refs: list[str]) -> list[dict]:
    return [
        {
            "path": ref,
            "exists": (workspace / ref).exists(),
            "bytes": (workspace / ref).stat().st_size if (workspace / ref).exists() else 0,
        }
        for ref in refs
    ]


def require_binary(name: str) -> None:
    if shutil.which(name) is None:
        raise SystemExit(f"{name} is required for golden baseline media generation")


def run(command: list[str]) -> None:
    completed = subprocess.run(command, cwd=ROOT)
    if completed.returncode != 0:
        raise SystemExit(f"command failed: {' '.join(command)}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_equal(value: object, expected: object, label: str) -> None:
    if value != expected:
        raise SystemExit(f"{label}: expected {expected!r}, got {value!r}")


def assert_true(value: object, label: str) -> None:
    if value is not True:
        raise SystemExit(f"{label}: expected True, got {value!r}")


def assert_false(value: object, label: str) -> None:
    if value is not False:
        raise SystemExit(f"{label}: expected False, got {value!r}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
