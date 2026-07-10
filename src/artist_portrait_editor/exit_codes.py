from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    success = 0
    success_with_warnings = 1
    invalid_arguments = 2
    invalid_project_config = 3
    missing_required_dependency_for_command = 4
    media_operation_failed = 5
    generated_artifact_schema_invalid = 6
    prerequisite_step_missing = 7
    model_call_failed = 8
    output_or_reference_validation_failed = 9
    user_confirmation_required = 10
    forbidden_content_reference = 11
    unrecoverable_internal_error = 12
