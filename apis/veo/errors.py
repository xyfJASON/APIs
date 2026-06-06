"""Exceptions raised by the Veo API wrappers."""


class VeoError(Exception):
    """Base exception for Veo wrapper errors."""


class VeoTaskFailedError(VeoError):
    """Raised when a Veo generation operation finishes with an error."""

    def __init__(
        self,
        operation_name: str,
        message: str = "",
        *,
        response: object | None = None,
    ) -> None:
        detail = message or "Veo operation failed"
        super().__init__(f"{detail} (operation={operation_name})")
        self.operation_name = operation_name
        self.response = response


class VeoTimeoutError(VeoError):
    """Raised when polling a Veo operation exceeds the configured timeout."""

    def __init__(self, operation_name: str, timeout: float) -> None:
        super().__init__(f"Veo operation timed out after {timeout:g}s (operation={operation_name})")
        self.operation_name = operation_name
        self.timeout = timeout
