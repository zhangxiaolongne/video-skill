# CLI Spec

Authoritative source: `artist_portrait_editor_revision5_optimized.md`.

Implemented Stage A commands:

```bash
artist-portrait validate --project ./project.yaml
artist-portrait init --project ./project.yaml
artist-portrait status --project ./project.yaml
artist-portrait generate-schema --output-dir schemas
```

Common Stage A flags:

```text
--project PATH
--json
--verbose
--quiet
--dry-run   # init only
```

Commands outside Stage A currently return `7 prerequisite_step_missing`.
