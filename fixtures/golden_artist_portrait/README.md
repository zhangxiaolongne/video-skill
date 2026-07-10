# Golden Artist Portrait Fixture

This fixture is the deterministic Stage 3 baseline project. It is intentionally
small, but it behaves like a creator-facing project:

- multiple source clips;
- explicit source ledger metadata;
- direct uploaded BGM;
- fixed rhythm intent;
- full preview, final export, editor package, NLE plan, FCPXML draft, and
  acceptance checks.

Media files are not committed. Generate them locally with:

```bash
python3 scripts/run_golden_baseline.py --workspace /tmp/artist-portrait-golden
```

The runner copies this fixture, generates local synthetic media with FFmpeg,
runs the Skill pipeline, and writes:

- `output/golden_baseline_manifest.json`
- `output/golden_baseline_report.md`

The fixture must not call paid APIs, access the network, call models from the
CLI, auto-select music, mutate edit points automatically, import into an NLE, or
claim relink/import success.
