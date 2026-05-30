"""Exceptions raised by the Kling API wrapper."""


class KlingError(Exception):
    """Base exception for Kling wrapper errors."""


class KlingAPIError(KlingError):
    """Raised when the Kling HTTP API returns an error response."""

    def __init__(
        self,
        message: str,
        *,
        code: int | None = None,
        status: int | None = None,
        request_id: str | None = None,
        response: object | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.request_id = request_id
        self.response = response


class KlingTaskFailedError(KlingError):
    """Raised when a Kling generation task finishes with failed status."""

    def __init__(self, task_id: str, message: str = "", *, response: object | None = None) -> None:
        detail = message or "Kling task failed"
        super().__init__(f"{detail} (task_id={task_id})")
        self.task_id = task_id
        self.response = response


class KlingTimeoutError(KlingError):
    """Raised when polling a Kling task exceeds the configured timeout."""

    def __init__(self, task_id: str, timeout: float) -> None:
        super().__init__(f"Kling task timed out after {timeout:g}s (task_id={task_id})")
        self.task_id = task_id
        self.timeout = timeout
