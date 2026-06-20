# Acceptance Tests V0

Authoritative source: `artist_portrait_editor_revision5_optimized.md`.

Current Stage A tests cover:

- valid and invalid `project.yaml`
- fixed exit code mapping
- Pydantic schema generation
- committed schema drift
- `validate`
- `init`
- `init --dry-run`
- `status` before and after initialization
- repeated `init`
- prevention of business artifact creation during Stage A

Future V0 media and creative fixtures are intentionally not implemented yet.
