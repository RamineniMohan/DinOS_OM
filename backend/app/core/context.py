import contextvars
from typing import Any

request_info: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "request_info", default={}
)
