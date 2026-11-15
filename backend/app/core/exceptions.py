from datetime import datetime, timezone
from typing import Optional


class AppError(Exception):
    """Base application exception for structured API error responses."""
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str,
    ):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code
        self.timestamp = datetime.now(timezone.utc).isoformat()


class SchemeNotFoundException(AppError):
    def __init__(self, scheme_id: str):
        super().__init__(
            status_code=404,
            detail=f"Scheme with ID '{scheme_id}' was not found in the catalog.",
            error_code="SCHEME_NOT_FOUND",
        )


class InvalidFilterException(AppError):
    def __init__(self, detail: str):
        super().__init__(
            status_code=400,
            detail=detail,
            error_code="INVALID_FILTER",
        )

