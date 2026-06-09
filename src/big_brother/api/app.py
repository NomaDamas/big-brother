import hmac
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, ClassVar, override
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Header, Request, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from big_brother.audit.log import AuditLog
from big_brother.decision.review import HumanReviewWorkflow, MissingOverrideReasonError
from big_brother.domain.hashes import HashBankEntry
from big_brother.domain.policy import Policy
from big_brother.hashbank.ingest import HashBankImportError
from big_brother.matching.engine import KnownContentMatcher
from big_brother.matching.loader import load_hash_entries

DEFAULT_MAX_UPLOAD_BYTES = 10 * 1024 * 1024
DEFAULT_AUDIT_LOG_PATH = Path(".omo/evidence/api-audit.jsonl")


class ApiSettings(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    hash_entries: tuple[HashBankEntry, ...] = ()
    dev_mode: bool = True
    admin_token: str | None = None
    max_upload_bytes: int = Field(default=DEFAULT_MAX_UPLOAD_BYTES, gt=0)
    audit_log_path: Path | None = None
    hashbank_path: Path | None = None


class ErrorResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    error_code: str = Field(min_length=1)
    message: str = Field(min_length=1)


class StructuredApiError(Exception):
    def __init__(self, *, status_code: int, error_code: str, message: str) -> None:
        self.status_code: int = status_code
        self.error_code: str = error_code
        self.message: str = message
        super().__init__(message)


class HealthResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    status: str


class ScanResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    decision: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    audit_event_ids: tuple[str, ...]


class ImportStatusResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    active_entries: int
    hashbank_path: str | None


class ReviewOverrideRequest(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    decision: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class ReviewOverrideResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    review_id: str = Field(min_length=1)
    status: str = Field(min_length=1)


class PolicyValidationResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    valid: bool


@dataclass(frozen=True, slots=True)
class ApiRoutes:
    settings: ApiSettings
    matcher: KnownContentMatcher
    audit_log: AuditLog | None

    def require_admin(
        self,
        authorization: Annotated[str | None, Header(alias="Authorization")] = None,
        x_admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None,
    ) -> None:
        if self.settings.dev_mode:
            return
        if _admin_token_matches(
            settings=self.settings,
            authorization=authorization,
            token=x_admin_token,
        ):
            return
        raise StructuredApiError(
            status_code=401,
            error_code="admin_token_required",
            message="admin token required for review actions",
        )

    def healthz(self) -> HealthResponse:
        return HealthResponse(status="ok")

    async def scan_upload(self, image: Annotated[UploadFile, File()]) -> ScanResponse:
        content_type = image.content_type or ""
        if not content_type.startswith("image/"):
            raise StructuredApiError(
                status_code=415,
                error_code="unsupported_media_type",
                message="image upload must use an image/* media type",
            )
        image_bytes = await image.read()
        if len(image_bytes) > self.settings.max_upload_bytes:
            raise StructuredApiError(
                status_code=413,
                error_code="upload_too_large",
                message="image upload exceeds configured maximum size",
            )

        request_id = f"scan_{uuid4().hex}"
        decision = self.matcher.scan(image_bytes)
        match_found = decision.decision == "blocked"
        if self.audit_log is not None:
            self.audit_log.record_scan_flow(
                request_id=request_id,
                user_identifier="anonymous",
                match_found=match_found,
            )
        return ScanResponse(
            decision=decision.decision,
            reason=decision.reason,
            request_id=request_id,
            audit_event_ids=_audit_event_ids(match_found=match_found),
        )

    def hashbank_import_status(self) -> ImportStatusResponse:
        path = self.settings.hashbank_path
        return ImportStatusResponse(
            active_entries=len(self.settings.hash_entries),
            hashbank_path=str(path) if path is not None else None,
        )

    def review_override(
        self,
        review_id: str,
        request: ReviewOverrideRequest,
    ) -> ReviewOverrideResponse:
        if self.audit_log is not None:
            try:
                HumanReviewWorkflow(audit_log=self.audit_log).override(
                    review_id=review_id,
                    decision=request.decision,
                    reason=request.reason,
                )
            except MissingOverrideReasonError as error:
                raise StructuredApiError(
                    status_code=400,
                    error_code="override_reason_required",
                    message=str(error),
                ) from error
        return ReviewOverrideResponse(review_id=review_id, status="recorded")

    def audit_export(self) -> PlainTextResponse:
        if self.audit_log is None:
            return PlainTextResponse("")
        return PlainTextResponse(
            self.audit_log.export_jsonl(),
            media_type="application/x-ndjson",
        )

    def policy_validate(self, policy: Policy) -> PolicyValidationResponse:
        _ = policy
        return PolicyValidationResponse(valid=True)


def structured_error_handler(_: Request, exc: Exception) -> JSONResponse:
    match exc:
        case StructuredApiError() as structured_error:
            return _structured_response(error=structured_error)
        case _:
            raise exc


def create_app(*, settings: ApiSettings) -> FastAPI:
    app = FastAPI(title="big-brother", version="0.1.0")
    app.add_middleware(SecurityHeadersMiddleware)
    routes = ApiRoutes(
        settings=settings,
        matcher=KnownContentMatcher(entries=settings.hash_entries),
        audit_log=_audit_log(settings),
    )

    app.add_exception_handler(StructuredApiError, structured_error_handler)

    _ = app.get("/healthz")(routes.healthz)
    _ = app.post("/v1/scan")(routes.scan_upload)
    _ = app.get("/v1/hashbank/import-status")(routes.hashbank_import_status)
    _ = app.post(
        "/v1/reviews/{review_id}/override",
        dependencies=[Depends(routes.require_admin)],
    )(routes.review_override)
    _ = app.get("/v1/audit/export", dependencies=[Depends(routes.require_admin)])(
        routes.audit_export,
    )
    _ = app.post("/v1/policy/validate")(routes.policy_validate)
    return app


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    @override
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response


def create_default_app() -> FastAPI:
    settings = ApiSettings(
        hash_entries=_load_default_entries(),
        dev_mode=_env_bool("BIG_BROTHER_DEV_MODE", default=True),
        admin_token=os.environ.get("BIG_BROTHER_ADMIN_TOKEN"),
        audit_log_path=DEFAULT_AUDIT_LOG_PATH,
        hashbank_path=Path("tests/fixtures/hashbanks/known-match.jsonl"),
    )
    return create_app(settings=settings)


def _load_default_entries() -> tuple[HashBankEntry, ...]:
    path = Path("tests/fixtures/hashbanks/known-match.jsonl")
    if not path.exists():
        return ()
    try:
        return load_hash_entries(path)
    except HashBankImportError:
        return ()


def _env_bool(name: str, *, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _audit_log(settings: ApiSettings) -> AuditLog | None:
    if settings.audit_log_path is None:
        return None
    return AuditLog(path=settings.audit_log_path)


def _audit_event_ids(*, match_found: bool) -> tuple[str, ...]:
    if match_found:
        return ("ingest", "scan", "match", "decision")
    return ("ingest", "scan", "decision")


def _admin_token_matches(
    *,
    settings: ApiSettings,
    authorization: str | None,
    token: str | None,
) -> bool:
    expected = settings.admin_token
    if expected is None:
        return False
    bearer = f"Bearer {expected}"
    if authorization is not None and hmac.compare_digest(authorization, bearer):
        return True
    return token is not None and hmac.compare_digest(token, expected)


def _structured_response(*, error: StructuredApiError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content=ErrorResponse(error_code=error.error_code, message=error.message).model_dump(),
    )
