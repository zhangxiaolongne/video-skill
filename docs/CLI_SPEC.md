# CLI Spec

Authoritative source: `artist_portrait_editor_revision5_optimized.md`.

Implemented local foundation commands:

```bash
artist-portrait validate --project ./project.yaml
artist-portrait init --project ./project.yaml
artist-portrait status --project ./project.yaml
artist-portrait generate-schema --output-dir schemas
artist-portrait scan --project ./project.yaml
artist-portrait map --project ./project.yaml
artist-portrait review --project ./project.yaml --scope project
```

Common Stage A flags:

```text
--project PATH
--json
--verbose
--quiet
--dry-run   # init only
```

Commands outside the current gate currently return `7 prerequisite_step_missing`.

`status --json` includes the state ledger plus local artifact and source
summaries. It does not run media operations or mutate project files.
