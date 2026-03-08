"""Custom exceptions for 1C HTTP service integration."""

from __future__ import annotations


class OneCError(Exception):
    """Base error for 1C integration."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class OneCTimeoutError(OneCError):
    """Request to 1C timed out after all retries."""

    pass


class OneCServerError(OneCError):
    """1C returned a 5xx status code."""

    pass
