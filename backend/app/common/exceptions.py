from typing import Any


class AppException(Exception):
    """Base domain exception."""
    def __init__(self, code: str, message: str, status_code: int = 400, details: Any = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, resource: str, details: Any = None):
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource} not found",
            status_code=404,
            details=details,
        )


class ConflictError(AppException):
    def __init__(self, message: str, details: Any = None):
        super().__init__(code="CONFLICT", message=message, status_code=409, details=details)


class ValidationError(AppException):
    def __init__(self, message: str, details: Any = None):
        super().__init__(code="VALIDATION_ERROR", message=message, status_code=422, details=details)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Access denied", details: Any = None):
        super().__init__(code="FORBIDDEN", message=message, status_code=403, details=details)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Authentication required", details: Any = None):
        super().__init__(code="UNAUTHORIZED", message=message, status_code=401, details=details)


class PaymentError(AppException):
    def __init__(self, message: str, details: Any = None):
        super().__init__(code="PAYMENT_ERROR", message=message, status_code=402, details=details)


class InsufficientStockError(AppException):
    def __init__(self, ingredient: str, details: Any = None):
        super().__init__(
            code="INSUFFICIENT_STOCK",
            message=f"Insufficient stock for: {ingredient}",
            status_code=422,
            details=details,
        )


def app_exception_handler(request, exc: AppException):
    """Convert domain exceptions to standard HTTP error responses."""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
    )
