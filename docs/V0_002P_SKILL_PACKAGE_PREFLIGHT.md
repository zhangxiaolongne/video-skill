# V0-002p Skill Package Preflight

Status: completed.

This slice adds a deterministic package preflight for the Codex skill wrapper.
It distinguishes hard metadata errors from known install-name risks.

## Accepted Behavior

- `scripts/skill_package_preflight.py` checks the repository root as a skill
  package.
- The preflight validates:
  - `SKILL.md` frontmatter presence and basic shape
  - required hard-boundary terms
  - `agents/openai.yaml`
  - default prompt reference to the skill token
  - current folder name versus skill name
  - origin repository name versus skill name
- Hard errors return exit code `1`.
- Warnings do not fail the command.
- `run_checks.py` runs the package preflight and allows only the current known
  name warnings:
  - `folder_name_mismatch`
  - `repo_name_mismatch`

## Current Known Risk

The skill name is `artist-portrait-editor`, while the current local folder is
`video skill` and the GitHub repository is `video-skill`. The official quick
validator accepts the skill, but `skill-creator` guidance recommends the folder
name match the skill name. Treat this as a packaging/install warning to resolve
before a final release tag.

## Boundaries

This does not rename the GitHub repository, install the skill into
`~/.codex/skills`, create tags, push to GitHub, or change runtime behavior.

## Validation

Covered by:

- `test_skill_package_preflight_allows_only_known_name_warnings`
- `run_checks.py`
