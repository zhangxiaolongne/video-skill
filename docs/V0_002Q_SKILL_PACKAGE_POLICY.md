# V0-002q Skill Package Policy

Status: completed.

This slice resolves the repository-name warning without weakening the skill
name. The canonical skill identity remains `artist-portrait-editor`; the GitHub
repository `video-skill` is treated as a distribution repository.

## Accepted Behavior

- `skill-package.json` declares:
  - `skill_name`: `artist-portrait-editor`
  - `canonical_install_dir`: `artist-portrait-editor`
  - `distribution_repositories`: `["video-skill"]`
  - `local_development_dirs`: `["video skill"]`
- `scripts/skill_package_preflight.py` validates the package policy.
- A policy skill name mismatch is a hard error.
- A canonical install dir mismatch is a hard error.
- The current origin repository `video-skill` no longer emits
  `repo_name_mismatch`.
- The current local folder `video skill` still emits `folder_name_mismatch`,
  because the final installed skill folder should be `artist-portrait-editor`.

## Release Implication

For a final installable release, install or copy this repository into a folder
named `artist-portrait-editor`. Do not rename the skill to `video-skill`; that
name is too broad for the actual workflow and would reduce trigger precision.

## Boundaries

This does not rename the local folder, rename the GitHub repository, install the
skill, create a tag, push to GitHub, or change runtime behavior.

## Validation

Covered by:

- `test_skill_package_preflight_allows_only_known_name_warnings`
- `run_checks.py`
