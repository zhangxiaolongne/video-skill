# CLI Spec

Authoritative source: `artist_portrait_editor_revision5_optimized.md`.

Implemented local foundation commands:

```bash
artist-portrait validate --project ./project.yaml
artist-portrait init --project ./project.yaml
artist-portrait status --project ./project.yaml
artist-portrait doctor --project ./project.yaml
artist-portrait generate-schema --output-dir schemas
artist-portrait scan --project ./project.yaml
artist-portrait map --project ./project.yaml
artist-portrait review --project ./project.yaml --scope project
artist-portrait review --project ./project.yaml --scope all
```

Common Stage A flags:

```text
--project PATH
--json
--verbose
--quiet
--dry-run   # init only
```

`review --scope all` runs the implemented project review, then records proposal
and timeline review as skipped warnings. `review --scope proposal` and
`review --scope timeline` still return `7 prerequisite_step_missing`.

Commands outside the current gate currently return `7 prerequisite_step_missing`.

`status --json` includes the state ledger plus local artifact and source
summaries. It also reports `artifact_issues` when completed ledger steps refer
to outputs that no longer exist. It does not run media operations or mutate
project files.

`doctor --json` is a read-only diagnostic command. It reports local workspace,
source ledger, and artifact consistency issues with `next_action` guidance and
`recommended_commands`. It returns `1 success_with_warnings` when diagnostics
find issues and `0 success` when no issues are found.
