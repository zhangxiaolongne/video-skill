---
name: artist-portrait-editor
description: Deterministic local workflow for preparing and auditing artist portrait video-editing projects. Use when Codex needs to validate an artist portrait project config, initialize local workspace state, scan local media into a source ledger and scan report, segment sources into a fixed-window clip ledger and clip report, generate a material map, run project risk review, diagnose workspace issues, or preserve the boundary before any scene detection, transcription, visual analysis, BGM selection, proposal generation, timeline generation, preview rendering, model calls, image generation/editing, or network search.
---

# Artist Portrait Editor

Use this skill to operate the local `artist-portrait` CLI for deterministic
artist portrait project preparation and audit work.

## Operating Order

1. Read `project.yaml` and run validation:

   ```bash
   artist-portrait validate --project ./project.yaml
   ```

2. Initialize local state before any other workspace command:

   ```bash
   artist-portrait init --project ./project.yaml
   ```

3. Inspect current state and diagnostics:

   ```bash
   artist-portrait status --project ./project.yaml --json
   artist-portrait doctor --project ./project.yaml --json
   ```

4. Scan local media only when `ffmpeg` and `ffprobe` are available:

   ```bash
   artist-portrait scan --project ./project.yaml
   ```

   This writes `.artist-portrait/data/sources.jsonl` and
   `output/scan_report.md`.

5. Generate deterministic local reports from `.artist-portrait/data/sources.jsonl`:

   ```bash
   artist-portrait segment --project ./project.yaml
   artist-portrait map --project ./project.yaml
   artist-portrait review --project ./project.yaml --scope project
   ```

   `segment` writes `.artist-portrait/data/clips.jsonl` and
   `output/clip_report.md` using fixed-window segmentation only.

6. Use `review --scope all` only as a shallow aggregate. It runs project review
   and marks proposal/timeline review as skipped; it does not implement those
   review surfaces.

## Diagnostics

- Use `doctor --json` before deciding the next command.
- Treat `recommended_commands` as guidance, not automatic repair.
- Treat `missing_output_ref` as a rebuild signal for the step that produced the
  missing artifact.
- Treat `source_ledger_invalid` as a stop condition until
  `.artist-portrait/data/sources.jsonl` is fixed or regenerated.
- Treat `map_invalidated` and `review_project_invalidated` as rebuild signals
  after a newer scan changes the source ledger.
- Treat `segment_invalidated` as a rebuild signal after a newer scan changes
  the source ledger.
- Treat `clips_invalid` as a stop condition until `.artist-portrait/data/clips.jsonl`
  is fixed or regenerated.

## Hard Boundaries

Do not perform these actions through this skill in the current local foundation
gate. A later validated gate may use mature third-party tools, installed Codex
skills, plugins, search, image generation/editing tools, models, or media
libraries instead of rebuilding those capabilities from scratch:

- PySceneDetect or scene-detection segmentation
- transcription or Whisper
- OpenCV or vision analysis
- embeddings
- BGM selection, beat analysis, music recommendation, or music/timeline fitting
- creative proposals
- timeline generation
- preview rendering
- model calls
- network search
- image generation or image editing

Keep all current foundation outputs local and deterministic.
