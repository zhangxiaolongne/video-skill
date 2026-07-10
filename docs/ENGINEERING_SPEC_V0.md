# Engineering Spec V0

> Status: current implementation reference. The governing product strategy and
> capability boundaries remain in `artist_portrait_editor_revision5_optimized.md`.
> Historical release detail belongs in `docs/archive/RELEASES_HISTORY.md`, not here.

## Scope

`artist-portrait` prepares and audits local artist-portrait edits. It grounds
plans in project-local media evidence, makes all generated evidence visible in
the workspace, and leaves creative judgment to the host Agent or editor.

The CLI may scan and analyze local media, build deterministic ledgers, validate
an explicit host-Agent proposal candidate, generate a timeline draft, ingest and
analyze locally supplied BGM, make BGM fit and rhythm guidance artifacts, render
local previews/final exports, and prepare editor/NLE/FCPXML handoff artifacts.
It never makes hidden network or provider calls. invalid audio inputs are
rejected with visible validation errors rather than inferred as usable BGM.

## Current Artifact Policy

- One capability normally owns one canonical machine JSON and one human Markdown
  report.
- Extra JSON is allowed only for candidate quarantine/import, typed schema
  boundaries, media validation, run audit, or release-critical evidence.
- `proposal_context.json`, `proposals.json`, and `proposal_validation.json` are
  the proposal machine artifacts; the Agent handoff is a human-facing output.
- BGM recommendation keeps context, quarantined candidate input, validated
  recommendations, explicit selection, and fit review. Its request instructions
  live inside the Agent handoff rather than a duplicate canonical JSON file.
- `workflow_plan.json` and `workflow_execution_review.json` are the workflow
  machine artifacts.
- `acceptance_report.json` is the acceptance machine artifact. Its Markdown
  report lists current next commands directly; there is no separate acceptance
  repair, approval, dry-run, bundle, or external-execution chain.
- FCPXML retains draft, validation, explicit import review, and a manual repair
  plan. It has no simulated repair approval, dry-run, or execution-record chain.
- Local `runs/`, `output/`, and `.artist-portrait/` evidence remains visible on
  disk and appears in status storage reports. It is excluded from source
  distribution and Git commits. Cache deletion is explicit only.

## Workflow

1. Validate/init, scan, segment, and build local analysis evidence.
2. Build an edit brief and clip scores.
3. Export proposal context and host-Agent handoff; import an explicit proposal
   candidate through quarantine and deterministic validation.
4. Select the canonical proposal and generate the timeline draft.
5. Optionally ingest user-provided BGM/audio, analyze it locally, and fit only
   an explicitly selected candidate.
6. Build rhythm and cut-review guidance. Guidance is not an applied edit.
7. Render preview/final media only when the corresponding command runs.
8. Use rhythm-aware acceptance profiles and workflow planning to assess readiness.
9. Generate editor/NLE handoff, FCPXML draft, import review, and manual repair
   guidance as needed.

## Boundaries

- No paid APIs, API keys, remote providers, hidden network access, or CLI-side
  model calls.
- No fabricated visual semantics or BPM/beat grid claims.
- Video-extracted mixed audio is not clean BGM.
- No automatic music selection, beat-synced edit movement, timeline mutation,
  automatic top-ranked selection, NLE import, source relinking, or claims that
  a manual edit was applied.
- Host-Agent, local-model, search, and image-tool work is explicit and must keep
  provenance visible; it is never silently invoked by the CLI.

## Verification

Run `run_checks.py` before a release candidate. It compiles source, validates
schemas, runs the focused test suite, packages and simulates installation,
checks release readiness, and rejects whitespace errors. The real-media fixture
uses generated local temporary media only.
