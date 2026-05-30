"""Exceptions raised by the Seedance API wrappers."""


class SeedanceError(Exception):
    """Base exception for Seedance wrapper errors."""


class SeedanceTaskFailedError(SeedanceError):
    """Raised when a Seedance generation task finishes in a terminal failure state."""

    def __init__(
        self,
        task_id: str,
        status: str,
        message: str = "",
        *,
        response: object | None = None,
    ) -> None:
        detail = message or f"Seedance task ended with status {status}"
        super().__init__(f"{detail} (task_id={task_id})")
        self.task_id = task_id
        self.status = status
        self.response = response


class SeedanceTimeoutError(SeedanceError):
    """Raised when polling a Seedance task exceeds the configured timeout."""

    def __init__(self, task_id: str, timeout: float) -> None:
        super().__init__(f"Seedance task timed out after {timeout:g}s (task_id={task_id})")
        self.task_id = task_id
        self.timeout = timeout
