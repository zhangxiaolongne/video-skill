# State And Invalidation

Authoritative source: `artist_portrait_editor_revision5_optimized.md`.

Stage A uses `.artist-portrait/state.json` as a step ledger, not a single
linear project state.

Current step statuses:

```text
pending
running
completed
completed_with_warnings
skipped
blocked
failed
invalidated
```

Current overall statuses:

```text
new
ready
running
degraded
blocked
```

Stage A initializes ledger entries for future V0 steps but leaves media and
creative steps pending.

`status --json` is read-only. It reports the current ledger, local artifact
presence, source ledger summaries, and latest run metadata without triggering
scan, map, review, model calls, or network access.

`output/run_report.md` is a rebuildable status artifact. Foundation commands
that update the ledger refresh it after writing state.
