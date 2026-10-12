"""Einheitliches Fehlerformat: {code, message, field_errors}."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, field_errors: dict[str, str] | None = None, extra: dict | None = None):
        self.status = status
        self.code = code
        self.message = message
        self.field_errors = field_errors or {}
        self.extra = extra or {}


def not_found(message: str = "Nicht gefunden.") -> ApiError:
    return ApiError(404, "not_found", message)


def forbidden(message: str = "Diese Aktion ist für Ihre Rolle nicht zulässig.") -> ApiError:
    return ApiError(403, "forbidden", message)


def invalid(message: str, field_errors: dict[str, str] | None = None) -> ApiError:
    return ApiError(422, "validation_error", message, field_errors)


def conflict(message: str = "Der Datensatz wurde inzwischen geändert. Bitte neu laden.", current_version: int | None = None) -> ApiError:
    extra = {"current_version": current_version} if current_version is not None else None
    return ApiError(409, "version_conflict", message, extra=extra)


def check_version(entity, version: int | None) -> None:
    if version is None:
        raise invalid("Feld 'version' fehlt.", {"version": "Pflichtfeld für Änderungen."})
    if entity.version != version:
        raise conflict(current_version=entity.version)


def _body(code: str, message: str, field_errors: dict | None = None, extra: dict | None = None) -> dict:
    body = {"code": code, "message": message, "field_errors": field_errors or {}}
    if extra:
        body.update(extra)
    return body


_STATUS_CODES = {
    400: "bad_request",
    401: "not_authenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "file_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
    429: "too_many_requests",
    503: "maintenance",
}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_request: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status, content=_body(exc.code, exc.message, exc.field_errors, exc.extra))

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_request: Request, exc: StarletteHTTPException):
        message = exc.detail if isinstance(exc.detail, str) else "Fehler."
        return JSONResponse(status_code=exc.status_code, content=_body(_STATUS_CODES.get(exc.status_code, "error"), message))

    @app.exception_handler(RequestValidationError)
    async def _validation(_request: Request, exc: RequestValidationError):
        fields: dict[str, str] = {}
        for err in exc.errors():
            loc = [str(p) for p in err.get("loc", []) if p not in ("body", "query", "path")]
            fields[".".join(loc) or "_"] = err.get("msg", "Ungültiger Wert")
        return JSONResponse(status_code=422, content=_body("validation_error", "Ungültige Eingabe.", fields))
