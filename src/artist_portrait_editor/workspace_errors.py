from __future__ import annotations


class WorkspacePrerequisiteError(Exception):
    pass


class WorkspaceDependencyError(Exception):
    pass


class WorkspaceProposalCandidateError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str,
        quarantine_ref: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.quarantine_ref = quarantine_ref


class WorkspaceTimelineError(Exception):
    pass


class WorkspacePreviewError(Exception):
    pass
