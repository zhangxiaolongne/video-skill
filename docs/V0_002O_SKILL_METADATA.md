# V0-002o Skill Metadata

Status: completed.

This slice turns the repository root into a minimal Codex skill folder while
keeping the runtime instructions concise.

## Accepted Behavior

- `SKILL.md` exists at the repository root.
- `SKILL.md` frontmatter uses `name: artist-portrait-editor`.
- The frontmatter description includes the working surface and hard boundaries.
- The skill body gives the local command order:
  - `validate`
  - `init`
  - `status`
  - `doctor`
  - `scan`
  - `map`
  - `review --scope project`
- The skill body explicitly forbids current-gate violations such as
  transcription, visual analysis, proposals, timelines, preview rendering,
  model calls, network search, and image generation/editing.
- `agents/openai.yaml` exists with UI-facing metadata and a default prompt that
  references `$artist-portrait-editor`.
- `run_checks.py` runs the system `skill-creator` quick validator.

## Boundaries

This does not install the skill into `~/.codex/skills`, create a release tag,
push to GitHub, or add extra bundled resources. The current skill is intentionally
metadata-first: one `SKILL.md` and one UI metadata file.

## Validation

Covered by:

- `test_skill_metadata_is_valid`
- `test_skill_frontmatter_and_boundaries`
- `test_openai_yaml_matches_skill`
- `run_checks.py`
