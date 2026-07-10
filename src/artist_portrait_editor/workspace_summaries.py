from __future__ import annotations

from pathlib import Path

from artist_portrait_editor.models.bgm import BgmCandidateLedger, BgmFitPlan
from artist_portrait_editor.models.timeline import TimelineDraft, TimelineValidationReport
from artist_portrait_editor.workspace_proposal_io import (
    read_proposal_context_json,
    read_proposal_validation_json,
    read_proposals_json,
)
from artist_portrait_editor.workspace_records import (
    read_analysis_jsonl,
    read_keyframes_jsonl,
    read_transcripts_jsonl,
)


def count_by_value(values) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[str(value)] = counts.get(str(value), 0) + 1
    return dict(sorted(counts.items()))



def transcript_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        transcripts = read_transcripts_jsonl(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    language_counts = count_by_value(
        transcript.language or "unknown" for transcript in transcripts
    )
    return {
        "exists": True,
        "valid": True,
        "count": len(transcripts),
        "language_counts": language_counts,
        "total_duration_seconds": round(
            sum(
                transcript.end_seconds - transcript.start_seconds
                for transcript in transcripts
            ),
            3,
        ),
    }


def keyframe_summary(path: Path, *, root: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        keyframes = read_keyframes_jsonl(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    missing_cache = [
        keyframe.image_path
        for keyframe in keyframes
        if not (root / keyframe.image_path).exists()
    ]
    method_counts = count_by_value(keyframe.method for keyframe in keyframes)
    return {
        "exists": True,
        "valid": True,
        "count": len(keyframes),
        "method_counts": method_counts,
        "missing_cache_count": len(missing_cache),
        "missing_cache_refs": missing_cache[:10],
    }


def analysis_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        analyses = read_analysis_jsonl(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    risk_counts = count_by_value(
        flag.value
        for analysis in analyses
        for flag in analysis.risk_flags
    )
    audio_counts = count_by_value(
        str(analysis.original_audio_usability.value) for analysis in analyses
    )
    return {
        "exists": True,
        "valid": True,
        "count": len(analyses),
        "risk_counts": risk_counts,
        "original_audio_usability_counts": audio_counts,
    }


def proposal_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        proposal_set = read_proposals_json(path)
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": str(exc),
        }
    return {
        "exists": True,
        "valid": True,
        "count": len(proposal_set.proposals),
        "proposal_ids": [proposal.proposal_id.value for proposal in proposal_set.proposals],
        "method": proposal_set.method,
    }


def timeline_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        timeline = TimelineDraft.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"exists": True, "valid": False, "error": f"invalid TimelineDraft JSON: {exc}"}
    return {
        "exists": True,
        "valid": True,
        "timeline_id": timeline.timeline_id,
        "proposal_id": timeline.proposal_id.value,
        "segment_count": len(timeline.segments),
        "actual_duration": timeline.actual_duration,
        "music_status": timeline.music_plan.status.value,
    }


def timeline_validation_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        report = TimelineValidationReport.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": f"invalid TimelineValidationReport JSON: {exc}",
        }
    return {
        "exists": True,
        "valid": True,
        "proposal_id": report.proposal_id.value,
        "issue_count": report.issue_count,
        "error_count": report.error_count,
        "warning_count": report.warning_count,
        "timeline_valid": report.valid,
    }


def bgm_candidates_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        ledger = BgmCandidateLedger.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": f"invalid BgmCandidateLedger JSON: {exc}",
        }
    return {
        "exists": True,
        "valid": True,
        "count": len(ledger.candidates),
        "candidate_ids": [item.music_candidate_id for item in ledger.candidates],
    }


def bgm_fit_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        plan = BgmFitPlan.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "exists": True,
            "valid": False,
            "error": f"invalid BgmFitPlan JSON: {exc}",
        }
    return {
        "exists": True,
        "valid": True,
        "fit_id": plan.fit_id,
        "candidate_id": plan.music_candidate_id,
        "fit_mode": plan.fit_mode,
        "target_duration": plan.target_duration,
    }


def proposal_context_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        context = read_proposal_context_json(path)
    except Exception as exc:
        return {"exists": True, "valid": False, "error": str(exc)}
    return {
        "exists": True,
        "valid": True,
        "context_id": context.context_id,
        "project_id": context.project_id,
        "analysis_count": len(context.analyses),
        "clip_count": len(context.clips),
        "score_count": len(context.clip_scores),
    }


def proposal_validation_summary(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    try:
        report = read_proposal_validation_json(path)
    except Exception as exc:
        return {"exists": True, "valid": False, "error": str(exc)}
    return {
        "exists": True,
        "valid": True,
        "report_id": report.report_id,
        "proposal_set_id": report.proposal_set_id,
        "proposal_count": report.proposal_count,
        "issue_count": report.issue_count,
        "error_count": report.error_count,
        "warning_count": report.warning_count,
    }


PROPOSAL_SUMMARY_READERS = {
    "proposal_context": proposal_context_summary,
    "proposals": proposal_summary,
    "proposal_validation": proposal_validation_summary,
}


def proposal_status_summaries(paths: dict[str, Path]) -> dict[str, dict]:
    return {
        name: PROPOSAL_SUMMARY_READERS[name](paths[name])
        for name in PROPOSAL_SUMMARY_READERS
    }

