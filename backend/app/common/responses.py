from typing import Any

from fastapi.responses import JSONResponse


def success_response(data: Any, status_code: int = 200, message: str = "Success") -> JSONResponse:
    """Standard success envelope for single-item responses."""
    return JSONResponse(
        status_code=status_code,
        content={"data": data, "message": message},
    )


def error_response(code: str, message: str, details: Any = None, status_code: int = 400) -> JSONResponse:
    """Standard error envelope."""
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
    )
