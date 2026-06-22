# V0-008 Basic Analysis Gate

V0-008 opens deterministic, evidence-only clip analysis. It creates a canonical
analysis ledger and a rebuildable report without performing OpenCV analysis,
vision-model analysis, embeddings, creative selection, BGM selection, timeline
generation, preview rendering, image generation/editing, network search, or
model calls.

## Scope

- `artist-portrait analyze --project <project.yaml>` reads
  `.artist-portrait/data/clips.jsonl`.
- Existing `.artist-portrait/data/transcripts.jsonl` and
  `.artist-portrait/data/keyframes.jsonl` may be referenced as evidence.
- `.artist-portrait/data/analysis.jsonl` is the canonical manifest.
- `output/analysis_report.md` is rebuildable from the analysis manifest.
- Changed source, clip, transcript, or keyframe ledgers invalidate completed
  analysis.
- Changed analysis invalidates completed map and project review outputs.

## Boundary

Analysis records may copy source material type, record audio usability from
ffprobe/transcript presence, and attach deterministic risk flags. Shot size,
camera motion, emotion, action, and visual quality are not classified in this
gate. They remain `null` or empty candidates with `method:
not_run_current_gate`.

Still forbidden:

- OpenCV or visual classification
- embeddings
- vision models
- BGM selection, beat analysis, or music/timeline fitting
- creative proposals
- timeline generation
- preview rendering
- model calls
- network search
- image generation or image editing

## Contract

Every non-deterministic or not-yet-run field keeps the common assertion shape:

- `value`
- `method`
- `level`
- `confidence`
- `evidence`
- `user_confirmed`

`AnalysisRecord` includes:

- stable analysis identity
- clip/source identity
- clip and analysis fingerprints
- material type
- original audio usability
- transcript refs
- keyframe refs
- risk flags
- evidence refs

