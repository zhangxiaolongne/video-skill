# V0-002s Release Readiness

Status: completed locally, not pushed, not tagged.

This slice records the current unpushed local batch as a release candidate and
defines the checks required before any push or tag.

This document records the functional/package release candidate range before the
V0-002s bookkeeping commit itself is added. The V0-002s documentation and tests
must be included in the final push or tag after validation.

## Commit Range

Remote base:

```text
0fa9f73 Render minimal project risk report
```

Local release candidate range:

```text
origin/main..HEAD
```

Included local commits:

```text
7fecdab Enhance status dashboard and run reports
cd1881d Expand foundation verification checks
8447514 Handle invalid source ledgers consistently
dea103f Write rebuildable reports atomically
d498c6e Check ledger artifact consistency
bd1b4f2 Add read-only doctor diagnostics
44c14dc Add minimal Codex skill metadata
4d2cfb3 Add skill package preflight
19bbb3f Declare canonical skill package policy
a8ef662 Record development progress and BGM constraint
62e9967 Synchronize master and development docs
2eccfba Record third-party tool reuse policy
91adf47 Simulate canonical skill installation
```

## Release Candidate Scope

This local batch includes:

- enhanced `status --json` and human status panel
- deterministic `run_report.md` refresh
- expanded `run_checks.py`
- invalid `sources.jsonl` handling
- atomic rebuildable report writes
- ledger output reference consistency
- read-only `doctor` diagnostics
- root `SKILL.md`
- `agents/openai.yaml`
- skill package preflight
- canonical package policy
- development progress tracking
- BGM as a non-negotiable future editing constraint
- third-party tool reuse policy for later gates
- canonical install simulation with zero package warnings

## Required Checks Before Push Or Tag

Run all of these from the repository root:

```bash
.venv/bin/python -m pytest
.venv/bin/python run_checks.py
.venv/bin/python scripts/skill_package_preflight.py . --json
.venv/bin/python scripts/simulate_skill_install.py . --json
git diff --check
```

Expected result:

```text
pytest: pass
run_checks.py: checks passed
skill_package_preflight.py: error_count 0; local folder_name_mismatch warning is allowed
simulate_skill_install.py: ok true, package_preflight.warning_count 0
git diff --check: no output
```

## Current Non-Release Actions

Do not push or tag automatically from this slice. Push/tag requires explicit
user confirmation after the release candidate is reviewed.

## Known Limits

- Current local folder is `video skill`; final installed skill folder should be
  `artist-portrait-editor`.
- Stage A/local foundation remains deterministic and does not call models,
  network search, image generation/editing, transcription, visual analysis,
  creative proposal generation, timeline generation, or preview rendering.
- Real scan validation is skipped when `ffmpeg`/`ffprobe` are unavailable.

## Recommended Next Step

After user confirmation, either:

- push `main` to `origin/main`, or
- create a release tag and push both commits and tag.
