# V0-002l Atomic Report Writes

Status: completed.

This slice hardens rebuildable text outputs so partial writes do not leave
truncated reports when a write is interrupted.

## Accepted Behavior

- `output/run_report.md` is written through a temporary file and replace.
- `output/material_map.md` is written through a temporary file and replace.
- `output/risk_report.md` is written through a temporary file and replace.
- Successful writes do not leave `*.tmp` files in `output/`.
- `run_checks.py` verifies report content and temporary-file cleanup.

## Boundaries

This slice does not change canonical JSONL writes, media scanning, source
identity, model behavior, network behavior, or report content semantics.

## Validation

Covered by:

- `test_atomic_write_text_replaces_content_without_leaving_tmp_file`
- `run_checks.py`
