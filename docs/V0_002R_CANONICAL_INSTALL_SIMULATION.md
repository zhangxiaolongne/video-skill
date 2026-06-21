# V0-002r Canonical Install Simulation

Status: completed.

This slice validates the final installed skill shape without modifying the
user's real `~/.codex/skills` directory.

## Accepted Behavior

- `scripts/simulate_skill_install.py` copies the repository to a temporary
  `artist-portrait-editor/` directory.
- The copy excludes local development artifacts such as `.git`, `.venv`,
  `.pytest_cache`, `.artist-portrait`, `__pycache__`, `*.pyc`, and `*.tmp`.
- The simulated install runs the system `skill-creator` quick validator.
- The simulated install runs `scripts/skill_package_preflight.py`.
- The target simulated install result is:
  - quick validator return code `0`
  - package preflight `error_count = 0`
  - package preflight `warning_count = 0`
- `run_checks.py` includes this install simulation.

## Boundary

This does not install the skill into `~/.codex/skills`, push to GitHub, create a
tag, or modify the user's existing skills.

## Validation

Covered by:

- `test_canonical_install_simulation_has_no_package_warnings`
- `run_checks.py`
