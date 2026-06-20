from __future__ import annotations

SCHEMA_VERSION = "0.3"
WORKSPACE_DIR = ".artist-portrait"
DATA_DIR = "data"
CACHE_DIR = "cache"
RUNS_DIR = "runs"
OUTPUT_DIR_DEFAULT = "output"

BUSINESS_ARTIFACTS = {
    ".artist-portrait/data/sources.jsonl",
    ".artist-portrait/data/clips.jsonl",
    ".artist-portrait/data/transcripts.jsonl",
    ".artist-portrait/data/relations.jsonl",
    ".artist-portrait/data/proposals.json",
    "output/material_map.md",
    "output/proposals.md",
    "output/timeline_draft.json",
    "output/risk_report.md",
}
