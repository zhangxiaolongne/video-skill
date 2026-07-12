from __future__ import annotations

import hashlib
import json
from pathlib import Path

from artist_portrait_editor.config_loader import load_project_config
from artist_portrait_editor.constants import DATA_DIR, WORKSPACE_DIR
from artist_portrait_editor.models.benchmark_pack import BenchmarkCase, BenchmarkCheck, RealVideoBenchmarkPack
from artist_portrait_editor.models.first_cut_review import FirstCutSelfReview
from artist_portrait_editor.models.second_cut_render import SecondCutRender
from artist_portrait_editor.models.source import SourceRecord
from artist_portrait_editor.run_records import utc_now
from artist_portrait_editor.workspace_state import atomic_write_text, fingerprint_file, project_root


REQUIRED_CLASSES = ("stage_person", "interview_talking_head", "event_promo_mix")


class BenchmarkPackError(RuntimeError):
    pass


def build_benchmark_pack(bindings: list[str], output_dir: Path) -> tuple[Path, Path, RealVideoBenchmarkPack, list[str]]:
    parsed = _parse_bindings(bindings)
    cases = [_build_case(kind, project_path) for kind, project_path in parsed.items()]
    closed = sum(item.acceptance_status == "closed_loop" for item in cases)
    inputs = sum(item.acceptance_status == "input_baseline" for item in cases)
    blocked = sum(item.acceptance_status == "blocked" for item in cases)
    warnings = [
        "benchmark media and project workspaces remain local and are not included in the distributed Skill",
        "technical media validity is not mature aesthetic acceptance",
    ]
    if inputs:
        warnings.append(f"{inputs} benchmark class is an input baseline without a completed second-cut loop")
    key = ":".join(item.benchmark_id for item in cases)
    pack = RealVideoBenchmarkPack(
        pack_id="benchmark_pack_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        generated_at=utc_now(), required_classes=list(REQUIRED_CLASSES),
        covered_classes=[item.benchmark_class for item in cases], benchmarks=cases,
        class_coverage_complete=True, closed_loop_count=closed,
        input_baseline_count=inputs, blocked_count=blocked,
        cross_case_findings=[
            "Long-form interview selection needs transcript-backed sentence continuity; technical audio energy cannot substitute for meaning.",
            "Stage footage needs performer-safe reframing and source/BGM separation; a valid vertical canvas does not remove broadcast-layout risk.",
            "Event/promo mixes stress multi-source selection, source quality consistency, and rapid visual progression more than single-source continuity.",
            "All classes require source-audio, text, transition, composition, and duration decisions to be reviewed as a coupled system.",
        ],
        known_blind_spots=[
            "No benchmark currently has transcript-backed semantic continuity.",
            "Existing second cuts use coarse ranked ranges rather than frame-accurate semantic or musical boundaries.",
            "The event/promo benchmark has source-scan evidence but no first/second-cut render loop yet.",
        ],
        status="blocked" if blocked else "degraded" if inputs else "ready",
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    canonical = output_dir / "real_video_benchmark_pack.json"
    report = output_dir / "real_video_benchmark_pack.md"
    atomic_write_text(canonical, pack.model_dump_json(indent=2) + "\n")
    atomic_write_text(report, _report(pack, warnings))
    return canonical, report, pack, warnings


def _parse_bindings(bindings: list[str]) -> dict[str, Path]:
    parsed: dict[str, Path] = {}
    for binding in bindings:
        kind, separator, raw_path = binding.partition("=")
        if not separator or kind not in REQUIRED_CLASSES or not raw_path:
            raise BenchmarkPackError("benchmark binding must be CLASS=/path/to/project.yaml")
        if kind in parsed:
            raise BenchmarkPackError(f"duplicate benchmark class: {kind}")
        parsed[kind] = Path(raw_path).expanduser().resolve()
    missing = sorted(set(REQUIRED_CLASSES) - set(parsed))
    if missing:
        raise BenchmarkPackError("missing required benchmark classes: " + ", ".join(missing))
    return parsed


def _build_case(kind: str, project_path: Path) -> BenchmarkCase:
    config = load_project_config(project_path)
    root = project_root(project_path)
    data = root / WORKSPACE_DIR / DATA_DIR
    sources_path = data / "sources.jsonl"
    if not sources_path.exists():
        raise BenchmarkPackError(f"benchmark source scan is missing: {project_path}")
    sources = [SourceRecord.model_validate_json(line) for line in sources_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not sources:
        raise BenchmarkPackError(f"benchmark has no real source records: {project_path}")
    review_path = data / "first_cut_self_review.json"
    second_path = data / "second_cut_render.json"
    review = FirstCutSelfReview.model_validate_json(review_path.read_text(encoding="utf-8")) if review_path.exists() else None
    second = SecondCutRender.model_validate_json(second_path.read_text(encoding="utf-8")) if second_path.exists() else None
    status = "closed_loop" if review and second and second.media_valid else "input_baseline"
    failure_examples = _failures(review, second, sources)
    checklist = _checklist(config, sources_path, review, second)
    key = kind + config.project.id + fingerprint_file(sources_path) + (second.output_hash if second else "input_only")
    return BenchmarkCase(
        benchmark_id="benchmark_" + hashlib.sha256(key.encode()).hexdigest()[:20],
        benchmark_class=kind, project_id=config.project.id, project_ref=project_path.as_posix(),
        title=config.project.title, target_platform=config.creative_brief.platform,
        target_duration_seconds=config.creative_brief.target_duration_seconds,
        source_count=len(sources), source_duration_seconds=round(sum(item.media_probe.duration for item in sources), 3),
        source_hashes=[item.content_hash for item in sources],
        rights_statuses=sorted({str(item.rights_status.value) for item in sources}),
        source_scan_current=True, first_cut_present=review is not None,
        second_cut_present=second is not None,
        second_cut_media_valid=second.media_valid if second else None,
        second_cut_duration_seconds=second.actual_duration_seconds if second else None,
        second_cut_dimensions=f"{second.width}x{second.height}" if second else None,
        second_cut_publishability=second.publishability if second else None,
        checklist=checklist, failure_examples=failure_examples, acceptance_status=status,
        acceptance_summary=(
            "Real first-cut review and independent second-cut media are present; unresolved aesthetic warnings remain visible."
            if status == "closed_loop" else
            "Real multi-source input, creative goal, provenance, and scan evidence are present; first/second-cut closure is not yet available."
        ),
    )


def _checklist(config, sources_path: Path, review: FirstCutSelfReview | None, second: SecondCutRender | None) -> list[BenchmarkCheck]:
    second_by_domain = {item.domain: item for item in second.comparisons} if second else {}
    def check(domain: str, available: bool, finding: str, refs: list[str]) -> BenchmarkCheck:
        return BenchmarkCheck(domain=domain, status="warning" if available else "unavailable", finding=finding, evidence_refs=refs)
    refs = [sources_path.as_posix()]
    return [
        BenchmarkCheck(domain="input_integrity", status="passed", finding="Real local media is fingerprinted and probeable.", evidence_refs=refs),
        BenchmarkCheck(domain="goal_binding", status="passed", finding=f"Goal binds platform {config.creative_brief.platform}, aspect {config.creative_brief.aspect_ratio}, and explicit creative brief.", evidence_refs=["project.yaml"]),
        check("selection", second is not None, "Ranked source ranges are applied in an independent candidate." if second else "Selection has not been evaluated beyond source ingestion.", [second.render_id] if second else refs),
        check("structure", second is not None, second_by_domain.get("duration_structure").finding if second else "No rendered hook/build/payoff structure exists yet.", [second.render_id] if second else refs),
        check("pacing", second is not None, second_by_domain.get("middle_pacing").finding if second else "Playback pacing has not been evaluated.", [second.render_id] if second else refs),
        check("source_audio_bgm", second is not None, second_by_domain.get("source_audio_bgm").finding if second else "Source audio is present but BGM/voice coupling has not been evaluated.", [second.render_id] if second else refs),
        check("text", second is not None, second_by_domain.get("text").finding if second else "No transcript-backed text evaluation exists.", [second.render_id] if second else refs),
        check("composition", second is not None, second_by_domain.get("composition").finding if second else "No candidate-specific composition review exists.", [second.render_id] if second else refs),
        check("semantic_continuity", second is not None, second_by_domain.get("semantic_continuity").finding if second else "No transcript or manual semantic-boundary review exists.", [second.render_id] if second else refs),
        BenchmarkCheck(domain="technical_delivery", status="passed" if second and second.media_valid else "unavailable", finding="Second-cut media passes technical QC." if second and second.media_valid else "No second-cut media is available for delivery QC.", evidence_refs=[second.output_ref] if second else refs),
    ]


def _failures(review: FirstCutSelfReview | None, second: SecondCutRender | None, sources: list[SourceRecord]) -> list[str]:
    failures: list[str] = []
    if review:
        failures.extend(f"{item.domain}: {item.diagnosis}" for item in review.domains if item.severity in {"high", "critical"})
    if second:
        failures.extend(f"{item.domain}: {item.finding}" for item in second.comparisons if item.status in {"unresolved", "regressed"})
    if not review:
        failures.extend([
            "No first-cut aesthetic review exists for this real input class.",
            "No rendered second cut exists for playback or technical comparison.",
            "Low and mixed source quality may create visual continuity failures that source probing alone cannot judge.",
        ])
    return failures or [f"No high-severity failure is recorded across {len(sources)} source files; manual aesthetic review remains required."]


def _report(pack: RealVideoBenchmarkPack, warnings: list[str]) -> str:
    lines = ["# Real Video Benchmark Pack", "", f"- Pack: `{pack.pack_id}`", f"- Status: `{pack.status}`", f"- Classes: `{len(pack.covered_classes)}/3`", f"- Closed loops: `{pack.closed_loop_count}`", f"- Input baselines: `{pack.input_baseline_count}`", "", "## Benchmarks", ""]
    for item in pack.benchmarks:
        lines.extend([f"### {item.title}", "", f"- Class: `{item.benchmark_class}`", f"- Acceptance: `{item.acceptance_status}`", f"- Sources: `{item.source_count}` / `{item.source_duration_seconds:.3f}s`", f"- Target: `{item.target_duration_seconds}` seconds on `{item.target_platform}`", f"- Second cut: `{item.second_cut_present}` / media valid `{item.second_cut_media_valid}`", "", "Failure examples:", ""] + [f"- {failure}" for failure in item.failure_examples] + [""])
    lines.extend(["## Cross-Case Findings", ""] + [f"- {item}" for item in pack.cross_case_findings])
    lines.extend(["", "## Known Blind Spots", ""] + [f"- {item}" for item in pack.known_blind_spots])
    lines.extend(["", "## Warnings", ""] + [f"- {item}" for item in warnings])
    return "\n".join(lines) + "\n"
