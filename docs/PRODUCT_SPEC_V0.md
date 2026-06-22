# Product Spec V0

Authoritative source: `artist_portrait_editor_revision5_optimized.md`.

V0 has two future modes:

- `core_mode`: deterministic processing, canonical data, risk rules, and
  material reports without text-generation or vision models.
- `creative_mode`: evidence-grounded proposals and timeline drafts after valid
  `core_mode` data exists.

Current repository implementation has entered deterministic core-mode
foundation work only. The active gate is V0-007 keyframe cache gate:

```text
project.yaml
-> configuration validation
-> workspace initialization
-> capability detection
-> status ledger
-> source scan ledger
-> scan report
-> fixed-window or PySceneDetect clip ledger
-> clip report
-> transcript ledger
-> keyframe ledger and rebuildable cache
-> minimal material map
-> minimal project risk report
-> run report
-> fixed exit codes
```

Do not implement visual analysis, proposal generation, timeline generation,
preview rendering, BGM selection, remote model calls, model downloads, image
generation/editing, or network search until a later gate explicitly opens them.
