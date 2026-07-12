import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("run_release_candidate", ROOT / "scripts" / "run_release_candidate.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_v2_release_audit_verifies_current_closed_loop_media(tmp_path) -> None:
    project = tmp_path / "stage"
    media = project / "output" / "second.mp4"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"current-second-cut")
    digest = "sha256:" + hashlib.sha256(media.read_bytes()).hexdigest()
    data = project / ".artist-portrait" / "data"
    data.mkdir(parents=True)
    (data / "second_cut_render.json").write_text(json.dumps({
        "output_ref": "output/second.mp4", "output_hash": digest, "media_valid": True,
    }), encoding="utf-8")
    cases = []
    for kind in ("stage_person", "interview_talking_head", "event_promo_mix"):
        cases.append({
            "benchmark_class": kind,
            "acceptance_status": "closed_loop" if kind == "stage_person" else "input_baseline",
            "project_ref": str(project / "project.yaml"),
        })
    pack = tmp_path / "pack.json"
    pack.write_text(json.dumps({
        "pack_id": "pack_test", "status": "degraded", "benchmarks": cases,
        "class_coverage_complete": True, "input_baseline_count": 2,
        "synthetic_fixture_counted_as_real": False,
        "distributable_media_included": False, "network_performed_by_cli": False,
    }), encoding="utf-8")

    result = MODULE.validate_benchmark_pack(pack)

    assert all(result["checks"].values())
    assert result["media_results"] == [{
        "benchmark_class": "stage_person", "valid_current_media": True,
    }]


def test_v2_release_audit_rejects_stale_second_cut_hash(tmp_path) -> None:
    project = tmp_path / "stage"
    media = project / "output" / "second.mp4"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"changed")
    data = project / ".artist-portrait" / "data"
    data.mkdir(parents=True)
    (data / "second_cut_render.json").write_text(json.dumps({
        "output_ref": "output/second.mp4", "output_hash": "sha256:" + "0" * 64,
        "media_valid": True,
    }), encoding="utf-8")
    pack = tmp_path / "pack.json"
    pack.write_text(json.dumps({
        "pack_id": "pack_test", "status": "degraded", "class_coverage_complete": True,
        "input_baseline_count": 2, "synthetic_fixture_counted_as_real": False,
        "distributable_media_included": False, "network_performed_by_cli": False,
        "benchmarks": [
            {"benchmark_class": "stage_person", "acceptance_status": "closed_loop", "project_ref": str(project / "project.yaml")},
            {"benchmark_class": "interview_talking_head", "acceptance_status": "input_baseline", "project_ref": str(project / "project.yaml")},
            {"benchmark_class": "event_promo_mix", "acceptance_status": "input_baseline", "project_ref": str(project / "project.yaml")},
        ],
    }), encoding="utf-8")

    result = MODULE.validate_benchmark_pack(pack)

    assert result["checks"]["v2_benchmark_closed_loop_media_current"] is False
