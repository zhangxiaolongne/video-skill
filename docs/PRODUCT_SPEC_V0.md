# Product Spec V0

Authoritative source: `artist_portrait_editor_revision5_optimized.md`.

V0 has two future modes:

- `core_mode`: deterministic processing, canonical data, risk rules, and
  material reports without text-generation or vision models.
- `creative_mode`: evidence-grounded proposals and timeline drafts after valid
  `core_mode` data exists.

Current repository implementation must not enter either media or creative
capability yet. The only allowed work is Stage A:

```text
project.yaml
-> configuration validation
-> workspace initialization
-> capability detection
-> status ledger
-> run report
-> fixed exit codes
```

Before Stage A passes, do not implement scanning, transcription, visual
analysis, proposal generation, timeline generation, or preview rendering.
