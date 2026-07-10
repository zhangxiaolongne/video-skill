import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import artist_portrait_editor.cli as cli
import artist_portrait_editor.workspace as workspace
from artist_portrait_editor.cli import main
from artist_portrait_editor.media.transcription import TranscribedSegment, TranscribedWord
from artist_portrait_editor.media.scanner import ScanResult, read_sources_jsonl
from artist_portrait_editor.models.source import (
    Assertion,
    MediaKind,
    MediaProbe,
    RightsStatus,
    SourceRecord,
)
from artist_portrait_editor.models.keyframe import KeyframeRecord
from artist_portrait_editor.models.state import Capabilities
from artist_portrait_editor.models.transcript import TranscriptRecord, TranscriptTextType


FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "stage_a"


def write_clean_source_ledger(root: Path) -> None:
    source = SourceRecord(
        source_id="clean-source-1",
        locations=["media/clean.mp4"],
        primary_location="media/clean.mp4",
        content_hash="sha256:" + "1" * 64,
        media_kind=MediaKind.video,
        media_probe=MediaProbe(
            duration=2.0,
            width=16,
            height=16,
            frame_rate=24.0,
            video_codec="h264",
            audio_present=False,
            audio_codec=None,
        ),
        source_type=Assertion(
            value="interview",
            method="test",
            level=4,
            confidence=1.0,
        ),
        rights_status=Assertion(
            value=RightsStatus.owned,
            method="test",
            level=4,
            confidence=1.0,
        ),
        provenance_confidence=1.0,
        provenance_method="test",
    )
    data_dir = root / ".artist-portrait" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "sources.jsonl").write_text(
        source.model_dump_json() + "\n",
        encoding="utf-8",
    )


def write_audio_source_ledger(root: Path) -> None:
    source = SourceRecord(
        source_id="audio-source-1",
        locations=["media/audio.wav"],
        primary_location="media/audio.wav",
        content_hash="sha256:" + "2" * 64,
        media_kind=MediaKind.audio,
        media_probe=MediaProbe(
            duration=2.0,
            width=None,
            height=None,
            frame_rate=None,
            video_codec=None,
            audio_present=True,
            audio_codec="pcm_s16le",
        ),
        source_type=Assertion(
            value="interview",
            method="test",
            level=4,
            confidence=1.0,
        ),
        rights_status=Assertion(
            value=RightsStatus.owned,
            method="test",
            level=4,
            confidence=1.0,
        ),
        provenance_confidence=1.0,
        provenance_method="test",
    )
    data_dir = root / ".artist-portrait" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "sources.jsonl").write_text(
        source.model_dump_json() + "\n",
        encoding="utf-8",
    )


def write_score_evidence_ledgers(root: Path) -> None:
    clip = workspace.read_clips_jsonl(root / ".artist-portrait" / "data" / "clips.jsonl")[0]
    transcript = TranscriptRecord(
        transcript_id="transcript-score-1",
        source_id=clip.source_id,
        source_location=clip.source_location,
        source_content_hash=clip.source_content_hash,
        source_fingerprint=clip.source_fingerprint,
        segment_index=0,
        start_seconds=clip.boundary.start_seconds,
        end_seconds=clip.boundary.end_seconds,
        text="This is a dense spoken moment with usable portrait information.",
        language="en",
        speaker="artist",
        text_type=TranscriptTextType.interview,
        method="test",
        method_version="test",
        confidence=0.95,
    )
    keyframe_path = root / ".artist-portrait" / "cache" / "keyframes" / "score-test.png"
    keyframe_path.parent.mkdir(parents=True, exist_ok=True)
    keyframe_path.write_bytes(b"score-keyframe")
    keyframe = KeyframeRecord(
        keyframe_id="keyframe-score-1",
        clip_id=clip.clip_id,
        source_id=clip.source_id,
        source_location=clip.source_location,
        source_content_hash=clip.source_content_hash,
        clip_fingerprint=clip.source_fingerprint,
        frame_index=0,
        timestamp_seconds=(clip.boundary.start_seconds + clip.boundary.end_seconds) / 2,
        image_path=keyframe_path.relative_to(root).as_posix(),
        method="test",
        method_version="test",
    )
    data_dir = root / ".artist-portrait" / "data"
    (data_dir / "transcripts.jsonl").write_text(
        transcript.model_dump_json() + "\n",
        encoding="utf-8",
    )
    (data_dir / "keyframes.jsonl").write_text(
        keyframe.model_dump_json() + "\n",
        encoding="utf-8",
    )


def project_fixture_with_scene_detection(value: str) -> str:
    return (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8").replace(
        "scene_detection: auto",
        f"scene_detection: {value}",
    )


def project_fixture_with_transcription(value: str) -> str:
    return (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8").replace(
        "transcription: auto",
        f"transcription: {value}",
    )


def project_fixture_with_remote_text_model_allowed() -> str:
    return (FIXTURES / "valid_project.yaml").read_text(encoding="utf-8").replace(
        "allow_remote_text_model: false",
        "allow_remote_text_model: true",
    )




def write_proposals_from_context(root: Path, *, unknown_clip: bool = False, bgm: bool = True) -> None:
    context = json.loads(
        (root / ".artist-portrait" / "data" / "proposal_context.json").read_text(
            encoding="utf-8"
        )
    )
    clip_id = context["clips"][0]["clip_id"]
    analysis_id = context["analyses"][0]["analysis_id"]
    required_clip = "clip_missing" if unknown_clip else clip_id
    story_structures = {
        "proposal_safe": ["chronological evidence-led opening", "measured conclusion"],
        "proposal_advanced": ["contrast-driven cold open", "parallel development"],
        "proposal_risky": ["disruptive question opening", "nonlinear reveal"],
    }
    sound_structures = {
        "proposal_safe": [
            "BGM strategy: low-interference music under speech with voice ducking"
        ],
        "proposal_advanced": [
            "Music supports pacing and transitions with beat-aligned cuts"
        ],
        "proposal_risky": [
            "Score drives emotional energy through a drop followed by silence"
        ],
    }
    visual_motifs = {
        "proposal_safe": ["chronological portrait details"],
        "proposal_advanced": ["cross-media match cuts"],
        "proposal_risky": ["delayed reveal and negative space"],
    }
    counter_proposals = {
        "proposal_safe": "What if the opening avoids a direct face shot?",
        "proposal_advanced": "What if chronology is replaced by thematic contrast?",
        "proposal_risky": "What if the music climax cuts to intentional silence?",
    }
    proposals = []
    for proposal_id in ("proposal_safe", "proposal_advanced", "proposal_risky"):
        proposals.append(
            {
                "proposal_id": proposal_id,
                "title": proposal_id.replace("_", " ").title(),
                "theme": context["creative_brief"]["theme"],
                "audience": context["creative_brief"]["audience"],
                "required_clip_ids": [required_clip],
                "fact_refs": [
                    {"type": "clip", "ref": clip_id},
                    {"type": "analysis", "ref": analysis_id},
                    {"type": "material_map", "ref": context["material_map_ref"]},
                ],
                "story_structure": story_structures[proposal_id],
                "sound_structure": (
                    sound_structures[proposal_id]
                    if bgm
                    else ["voice-first sound plan"]
                ),
                "visual_motifs": visual_motifs[proposal_id],
                "risks": ["visual semantics not inferred"],
                "minimum_viable_timeline": ["timeline generation not open"],
                "missing_material": [],
                "counter_proposal": counter_proposals[proposal_id],
            }
        )
    payload = {
        "proposal_set_id": "proposal_set_test",
        "project_id": context["project_id"],
        "map_fingerprint": context["material_map_fingerprint"],
        "method": "codex_host_agent_test_fixture",
        "method_version": "test",
        "proposals": proposals,
        "evidence": [{"type": "proposal_context", "ref": context["context_id"]}],
        "warnings": [],
    }
    (root / ".artist-portrait" / "data" / "proposals.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_blocked_proposal_chain(root: Path, capsys) -> Path:
    project_path = root / "project.yaml"
    project_path.write_text(
        project_fixture_with_scene_detection("off"),
        encoding="utf-8",
    )
    assert main(["init", "--project", str(project_path), "--quiet"]) in (0, 1)
    write_clean_source_ledger(root)
    assert main(["segment", "--project", str(project_path), "--quiet"]) == 0
    assert main(["analyze", "--project", str(project_path), "--quiet"]) == 0
    assert main(["map", "--project", str(project_path), "--quiet"]) == 0
    assert main(["brief", "--project", str(project_path), "--quiet"]) == 0
    assert main(["score", "--project", str(project_path), "--quiet"]) == 1
    assert main(["propose", "--project", str(project_path), "--json"]) == 1
    capsys.readouterr()
    return project_path


def build_valid_proposal_project(root: Path, capsys, *, allow_music: bool = True) -> Path:
    project_path = build_blocked_proposal_chain(root, capsys)
    if not allow_music:
        project_path.write_text(
            project_path.read_text(encoding="utf-8").replace(
                "allow_music: true",
                "allow_music: false",
            ),
            encoding="utf-8",
        )
    write_proposals_from_context(root, bgm=allow_music)
    canonical = root / ".artist-portrait" / "data" / "proposals.json"
    if not allow_music:
        payload = json.loads(canonical.read_text(encoding="utf-8"))
        for proposal in payload["proposals"]:
            proposal["sound_structure"] = [
                "no added music; preserve original voice and intentional silence "
                f"for {proposal['proposal_id']}"
            ]
        canonical.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    candidate = root / "proposal_candidate.json"
    candidate.write_bytes(canonical.read_bytes())
    canonical.unlink()
    assert (
        main(
            [
                "propose",
                "--project",
                str(project_path),
                "--agent-output",
                str(candidate),
                "--quiet",
            ]
        )
        == 0
    )
    capsys.readouterr()
    return project_path


def run_brief_and_score_for_propose(root: Path, project_path: Path) -> None:
    assert main(["brief", "--project", str(project_path), "--quiet"]) == 0
    assert main(["score", "--project", str(project_path), "--quiet"]) in (0, 1)
    assert (root / ".artist-portrait" / "data" / "clip_scores.jsonl").exists()


