from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from run_golden_baseline import (
    ARTIST_PORTRAIT,
    generate_bgm,
    generate_media,
    prepare_workspace,
    write_valid_proposals_from_context,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Stage 4 BGM/rhythm quality pass.")
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
    manifest = run_quality_pass(workspace)
    write_outputs(workspace, manifest)
    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"BGM/rhythm quality passed: {workspace / 'output' / 'bgm_rhythm_quality_manifest.json'}")
    return 0


def run_quality_pass(workspace: Path) -> dict:
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
                f"command failed in BGM/rhythm quality pass: {' '.join(command)}\n"
                f"exit={completed.returncode}\nstdout={completed.stdout}\nstderr={completed.stderr}"
            )
        if "--json" in parts:
            return json.loads(completed.stdout)
        return None

    cli("init", "--project", str(project), "--quiet")
    cli("scan", "--project", str(project), "--quiet")
    cli("segment", "--project", str(project), "--quiet")
    cli("keyframes", "--project", str(project), "--quiet", expect=(0, 1))
    cli("analyze", "--project", str(project), "--quiet")
    cli("map", "--project", str(project), "--quiet")
    cli("propose", "--project", str(project), "--json", expect=(1,))
    write_valid_proposals_from_context(workspace)
    candidate = workspace / "proposal_candidate.json"
    canonical = workspace / ".artist-portrait" / "data" / "proposals.json"
    candidate.write_bytes(canonical.read_bytes())
    canonical.unlink()
    cli("propose", "--project", str(project), "--agent-output", str(candidate), "--quiet", expect=(0, 1))
    cli("timeline", "--project", str(project), "--proposal", "proposal_safe", "--quiet", expect=(0, 1))

    no_file_rhythm = cli(
        "rhythm",
        "--project",
        str(project),
        "--intent",
        str(workspace / "annotations" / "rhythm_intent.json"),
        "--json",
        expect=(0, 1),
    )
    no_file_plan = no_file_rhythm["rhythm_plan"]
    if no_file_plan.get("bgm_fit_id") is not None:
        raise SystemExit("no-file-yet rhythm planning unexpectedly bound a BGM fit")
    if no_file_plan.get("media_rendered") is not False:
        raise SystemExit("no-file-yet rhythm planning rendered media")

    source_ids = load_source_ids(workspace)
    generate_bgm(workspace)
    direct = cli(
        "bgm",
        "import",
        "--project",
        str(project),
        "--file",
        "media/uploaded_bgm.wav",
        "--rights-status",
        "owned",
        "--intent",
        "direct uploaded music for restrained portrait pacing",
        "--json",
        expect=(0, 1),
    )["candidate"]
    video_extract = cli(
        "bgm",
        "import",
        "--project",
        str(project),
        "--file",
        "media/stage_fragment.mp4",
        "--extract-in",
        "0.2",
        "--extract-out",
        "1.2",
        "--rights-status",
        "owned",
        "--intent",
        "extracted video audio candidate for contamination review",
        "--json",
        expect=(0, 1),
    )["candidate"]
    embedded = cli(
        "bgm",
        "import",
        "--project",
        str(project),
        "--source-id",
        source_ids["interview"],
        "--extract-in",
        "0.1",
        "--extract-out",
        "1.1",
        "--intent",
        "source embedded audio candidate for provenance comparison",
        "--json",
        expect=(0, 1),
    )["candidate"]

    candidates = [direct, video_extract, embedded]
    modes = {candidate["input_mode"] for candidate in candidates}
    if modes != {"direct_audio", "video_audio_extract", "source_embedded_audio"}:
        raise SystemExit(f"BGM input modes drifted: {sorted(modes)}")
    if direct["mixed_audio"] is not False:
        raise SystemExit("direct audio candidate was marked mixed")
    if video_extract["mixed_audio"] is not True or embedded["mixed_audio"] is not True:
        raise SystemExit("video/source extracted candidates were not marked mixed")

    analysis = cli("bgm", "analyze", "--project", str(project), "--json", expect=(0, 1))["analysis"]
    rhythm = cli("bgm", "rhythm", "--project", str(project), "--json", expect=(0, 1))[
        "bgm_rhythm_intelligence"
    ]
    if analysis["automatic_music_selection"] is not False:
        raise SystemExit("BGM analysis selected music")
    if rhythm["automatic_music_selection"] is not False:
        raise SystemExit("BGM rhythm intelligence selected music")
    if rhythm["mixed_audio_candidate_count"] < 2:
        raise SystemExit("BGM rhythm intelligence missed mixed-audio candidates")
    if set(rhythm["source_modes_present"]) != modes:
        raise SystemExit("BGM rhythm source modes do not match imported candidates")
    high_risk = [
        item
        for item in rhythm["candidates"]
        if item["input_mode"] in {"video_audio_extract", "source_embedded_audio"}
    ]
    if not high_risk or any(item["source_risk_status"] != "high" for item in high_risk):
        raise SystemExit("mixed BGM candidates did not surface high source-risk status")

    cli(
        "bgm",
        "fit",
        "--project",
        str(project),
        "--candidate",
        direct["music_candidate_id"],
        "--fit-mode",
        "loop",
        "--fade-in-seconds",
        "0.25",
        "--fade-out-seconds",
        "0.35",
        "--target-gain-db",
        "-13",
        "--ducking-gain-db",
        "-11",
        "--beat-align",
        "--quiet",
        expect=(0, 1),
    )
    fit = json.loads(
        (workspace / ".artist-portrait" / "data" / "bgm_fit.json").read_text(
            encoding="utf-8"
        )
    )
    if fit["music_candidate_id"] != direct["music_candidate_id"]:
        raise SystemExit("BGM fit did not bind the explicitly selected direct candidate")
    if fit["controls"]["ducking_gain_db"] != -11:
        raise SystemExit("BGM fit did not preserve explicit ducking gain")
    if fit["controls"]["target_gain_db"] != -13:
        raise SystemExit("BGM fit did not preserve explicit target gain")
    if not fit["ducking_intervals"]:
        raise SystemExit("BGM fit did not create ducking intervals for retained source audio")
    bgm_review = cli("bgm", "review", "--project", str(project), "--json", expect=(0, 1))
    if bgm_review["status"] not in {"passed", "warning"}:
        raise SystemExit("BGM review did not complete after explicit fit controls")

    quality_rhythm = cli(
        "rhythm",
        "--project",
        str(project),
        "--intent",
        str(workspace / "annotations" / "rhythm_intent.json"),
        "--json",
        expect=(0, 1),
    )["rhythm_plan"]
    if not quality_rhythm.get("bgm_rhythm_intelligence_fingerprint"):
        raise SystemExit("rhythm plan did not bind BGM rhythm intelligence")
    edit_guidance = cli("rhythm", "--project", str(project), "--edit-guidance", "--json", expect=(0, 1))[
        "edit_guidance"
    ]
    categories = {item["category"] for item in edit_guidance["actions"]}
    for expected_category in {
        "subtitle",
        "transition",
        "pause",
        "ducking",
        "phrase",
        "cut_review",
        "ending",
        "source_risk",
    }:
        if expected_category not in categories:
            raise SystemExit(f"edit guidance lacks {expected_category} action")
    source_actions = [
        item for item in edit_guidance["actions"] if item["category"] == "source_risk"
    ]
    if not source_actions or "clean BGM" not in source_actions[0]["recommendation"]:
        raise SystemExit("edit guidance did not warn against treating mixed video audio as clean BGM")

    cli("preview", "--project", str(project), "--width", "320", "--fps", "10", "--quiet", expect=(0, 1))
    preview_qc = cli("rhythm", "--project", str(project), "--qc", "--json", expect=(0, 1))[
        "rhythm_media_qc"
    ]
    preview_acceptance = cli(
        "acceptance",
        "--project",
        str(project),
        "--profile",
        "preview",
        "--json",
        expect=(0, 9),
    )
    cli("export", "--project", str(project), "--profile", "review_720p", "--quiet", expect=(0, 1))
    final_qc = cli("rhythm", "--project", str(project), "--qc", "--json", expect=(0, 1))[
        "rhythm_media_qc"
    ]
    delivery = cli(
        "acceptance",
        "--project",
        str(project),
        "--profile",
        "delivery",
        "--json",
        expect=(0, 9),
    )
    if preview_acceptance["preview_ready"] is not True:
        raise SystemExit("BGM/rhythm quality preview acceptance failed")
    if delivery["final_export_ready"] is not True:
        raise SystemExit("BGM/rhythm quality delivery acceptance failed")
    if final_qc["status"] not in {"passed", "warning"}:
        raise SystemExit("BGM/rhythm quality final media QC did not complete")

    manifest = {
        "schema_version": "1.0",
        "quality_pass_id": "bgm_rhythm_quality_stage_04",
        "project_id": "golden_artist_portrait_001",
        "status": "passed",
        "workspace": str(workspace),
        "candidate_count": len(candidates),
        "input_modes": sorted(modes),
        "mixed_audio_candidate_count": rhythm["mixed_audio_candidate_count"],
        "source_risk_high_count": sum(
            1 for item in rhythm["candidates"] if item["source_risk_status"] == "high"
        ),
        "no_file_yet": {
            "rhythm_status": no_file_plan["status"],
            "bgm_fit_id": no_file_plan.get("bgm_fit_id"),
        },
        "fit_controls": {
            "fit_mode": fit["fit_mode"],
            "target_gain_db": fit["controls"]["target_gain_db"],
            "ducking_gain_db": fit["controls"]["ducking_gain_db"],
            "ducking_interval_count": len(fit["ducking_intervals"]),
            "beat_alignment_requested": fit["controls"]["beat_alignment_requested"],
            "beat_alignment_status": fit["beat_alignment_status"],
        },
        "guidance": {
            "action_count": edit_guidance["action_count"],
            "categories": sorted(categories),
            "manual_only": edit_guidance["manual_only"],
        },
        "media_qc": {
            "preview_status": preview_qc["status"],
            "final_status": final_qc["status"],
            "preview_ready": preview_acceptance["preview_ready"],
            "delivery_ready": delivery["final_export_ready"],
            "preview_profile_passed": preview_acceptance["profile_passed"],
            "delivery_profile_passed": delivery["profile_passed"],
        },
        "guardrails": {
            "automatic_music_selection": any(
                value is not False
                for value in [
                    analysis["automatic_music_selection"],
                    rhythm["automatic_music_selection"],
                    fit["controls"]["automatic_music_selection"],
                    quality_rhythm["automatic_music_selection"],
                    edit_guidance["automatic_music_selection"],
                ]
            ),
            "edit_points_moved": any(
                value is not False
                for value in [
                    rhythm["edit_points_moved"],
                    quality_rhythm["edit_points_moved"],
                    edit_guidance["edit_points_moved"],
                    final_qc["edit_points_moved"],
                ]
            ),
            "media_rendered_by_quality_review": any(
                value is not False
                for value in [
                    rhythm["media_rendered"],
                    quality_rhythm["media_rendered"],
                    edit_guidance["media_rendered"],
                    final_qc["preview_rendered_by_qc"],
                    final_qc["final_export_rendered_by_qc"],
                ]
            ),
            "model_call_performed_by_cli": any(
                value is not False
                for value in [
                    rhythm["model_call_performed_by_cli"],
                    quality_rhythm["model_call_performed_by_cli"],
                    edit_guidance["model_call_performed_by_cli"],
                ]
            ),
            "network_performed": any(
                value is not False
                for value in [
                    rhythm["network_performed"],
                    quality_rhythm["network_performed"],
                    edit_guidance["network_performed"],
                ]
            ),
            "fabricated_bpm_or_beats": rhythm["fabricated_bpm_or_beats"],
        },
        "steps": steps,
    }
    if any(manifest["guardrails"].values()):
        raise SystemExit(f"BGM/rhythm quality guardrails failed: {manifest['guardrails']}")
    return manifest


def load_source_ids(workspace: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    path = workspace / ".artist-portrait" / "data" / "sources.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        result[item["source_type"]["value"]] = item["source_id"]
    if "interview" not in result or "stage_performance" not in result:
        raise SystemExit(f"missing expected source ids: {sorted(result)}")
    return result


def write_outputs(workspace: Path, manifest: dict) -> None:
    output = workspace / "output"
    output.mkdir(exist_ok=True)
    (output / "bgm_rhythm_quality_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# BGM Rhythm Quality Report",
        "",
        f"- Status: `{manifest['status']}`",
        f"- Candidate count: `{manifest['candidate_count']}`",
        f"- Input modes: `{', '.join(manifest['input_modes'])}`",
        f"- Mixed-audio candidates: `{manifest['mixed_audio_candidate_count']}`",
        f"- High source-risk candidates: `{manifest['source_risk_high_count']}`",
        f"- Guidance actions: `{manifest['guidance']['action_count']}`",
        f"- Preview ready: `{manifest['media_qc']['preview_ready']}`",
        f"- Delivery ready: `{manifest['media_qc']['delivery_ready']}`",
        "",
        "## Fit Controls",
        "",
    ]
    for key, value in manifest["fit_controls"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Guardrails", ""])
    for key, value in manifest["guardrails"].items():
        lines.append(f"- `{key}`: `{value}`")
    (output / "bgm_rhythm_quality_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
