import hmac
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, ClassVar, Protocol, override, runtime_checkable
from uuid import uuid4

from anyio import to_thread
from fastapi import Depends, FastAPI, File, Header, Request, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from big_brother.audit.log import AuditLog, ScanAuditOutcome
from big_brother.decision.engine import DecisionEngine
from big_brother.decision.review import HumanReviewWorkflow, MissingOverrideReasonError
from big_brother.domain.hashes import HashBankEntry
from big_brother.domain.policy import ModelSignal, Policy
from big_brother.hashbank.ingest import HashBankImportError
from big_brother.matching.engine import KnownContentMatcher
from big_brother.matching.loader import load_hash_entries
from big_brother.models.config import load_moderation_config
from big_brother.models.hf_moderation import TransformersImageModerationClient

DEFAULT_MAX_UPLOAD_BYTES = 10 * 1024 * 1024
DEFAULT_AUDIT_LOG_PATH = Path(".omo/evidence/api-audit.jsonl")
DEFAULT_DEV_HASHBANK_PATH = Path("tests/fixtures/hashbanks/known-match.jsonl")
PLACEHOLDER_ADMIN_TOKENS = frozenset(
    {"", "change-this-local-admin-token", "replace-with-random-production-token"}
)
MODEL_TRIAGE_DISABLED_VALUES = frozenset({"", "0", "false", "no", "off"})


@runtime_checkable
class ModelModerator(Protocol):
    def classify(self, *, image_bytes: bytes) -> ModelSignal: ...


class ProductionConfigError(RuntimeError):
    pass


class ApiSettings(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    hash_entries: tuple[HashBankEntry, ...] = ()
    dev_mode: bool = True
    admin_token: str | None = None
    max_upload_bytes: int = Field(default=DEFAULT_MAX_UPLOAD_BYTES, gt=0)
    audit_log_path: Path | None = None
    hashbank_path: Path | None = None
    model_moderator: ModelModerator | None = None


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
    decision_engine: DecisionEngine

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
        known_decision = self.matcher.scan(image_bytes)
        model_signal = None
        if known_decision.decision != "blocked" and self.settings.model_moderator is not None:
            model_signal = await to_thread.run_sync(
                _classify_model_signal,
                self.settings.model_moderator,
                image_bytes,
            )
        decision = self.decision_engine.decide(
            known_match=known_decision,
            model_signal=model_signal,
        )
        match_found = known_decision.decision == "blocked"
        if self.audit_log is not None:
            self.audit_log.record_scan_flow(
                request_id=request_id,
                user_identifier="anonymous",
                outcome=ScanAuditOutcome(
                    match_found=match_found,
                    model_signal_recorded=model_signal is not None,
                    decision=decision.outcome,
                    decision_reason=decision.reason,
                ),
            )
        return ScanResponse(
            decision=decision.outcome,
            reason=decision.reason,
            request_id=request_id,
            audit_event_ids=_audit_event_ids(
                match_found=match_found,
                model_signal_recorded=model_signal is not None,
            ),
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
        decision_engine=DecisionEngine(),
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
    return create_app(settings=_default_settings_from_env())


def _default_settings_from_env() -> ApiSettings:
    dev_mode = _env_bool("BIG_BROTHER_DEV_MODE", default=True)
    hashbank_path = _env_path("BIG_BROTHER_HASHBANK_PATH")
    if hashbank_path is None and dev_mode:
        hashbank_path = DEFAULT_DEV_HASHBANK_PATH
    entries = _load_runtime_entries(path=hashbank_path, dev_mode=dev_mode)
    admin_token = os.environ.get("BIG_BROTHER_ADMIN_TOKEN")
    _validate_admin_token(dev_mode=dev_mode, admin_token=admin_token)
    return ApiSettings(
        hash_entries=entries,
        dev_mode=dev_mode,
        admin_token=admin_token,
        max_upload_bytes=_env_int("BIG_BROTHER_MAX_UPLOAD_BYTES", default=DEFAULT_MAX_UPLOAD_BYTES),
        audit_log_path=_env_path("BIG_BROTHER_AUDIT_LOG_PATH") or DEFAULT_AUDIT_LOG_PATH,
        hashbank_path=hashbank_path,
        model_moderator=_model_moderator_from_env(),
    )


def _load_runtime_entries(*, path: Path | None, dev_mode: bool) -> tuple[HashBankEntry, ...]:
    if path is None:
        if dev_mode:
            return ()
        message = "BIG_BROTHER_HASHBANK_PATH is required when BIG_BROTHER_DEV_MODE=false"
        raise ProductionConfigError(message)
    try:
        entries = load_hash_entries(path)
    except FileNotFoundError as error:
        if dev_mode and path == DEFAULT_DEV_HASHBANK_PATH:
            return ()
        message = f"hashbank file not found: {path}"
        raise ProductionConfigError(message) from error
    except HashBankImportError as error:
        message = f"invalid hashbank file {path}: {error}"
        raise ProductionConfigError(message) from error
    if not dev_mode and len(entries) == 0:
        message = f"production hashbank is empty: {path}"
        raise ProductionConfigError(message)
    return entries


def _env_bool(name: str, *, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, *, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except ValueError as error:
        message = f"{name} must be an integer"
        raise ProductionConfigError(message) from error
    if parsed <= 0:
        message = f"{name} must be greater than zero"
        raise ProductionConfigError(message)
    return parsed


def _env_path(name: str) -> Path | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return None
    return Path(value)


def _validate_admin_token(*, dev_mode: bool, admin_token: str | None) -> None:
    if dev_mode:
        return
    if admin_token is None or admin_token in PLACEHOLDER_ADMIN_TOKENS:
        message = (
            "BIG_BROTHER_ADMIN_TOKEN must be set to a non-placeholder value "
            "when BIG_BROTHER_DEV_MODE=false"
        )
        raise ProductionConfigError(message)


def _model_moderator_from_env() -> ModelModerator | None:
    enabled = os.environ.get("BIG_BROTHER_MODEL_TRIAGE_ENABLED", "false").casefold()
    if enabled in MODEL_TRIAGE_DISABLED_VALUES:
        return None
    config_path = _env_path("BIG_BROTHER_MODEL_CONFIG_PATH")
    if config_path is None:
        message = (
            "BIG_BROTHER_MODEL_CONFIG_PATH is required when BIG_BROTHER_MODEL_TRIAGE_ENABLED=true"
        )
        raise ProductionConfigError(message)
    return TransformersImageModerationClient(config=load_moderation_config(config_path))


def _classify_model_signal(moderator: ModelModerator, image_bytes: bytes) -> ModelSignal:
    return moderator.classify(image_bytes=image_bytes)


def _audit_log(settings: ApiSettings) -> AuditLog | None:
    if settings.audit_log_path is None:
        return None
    return AuditLog(path=settings.audit_log_path)


def _audit_event_ids(*, match_found: bool, model_signal_recorded: bool) -> tuple[str, ...]:
    event_ids = ["ingest", "scan"]
    if match_found:
        event_ids.append("match")
    if model_signal_recorded:
        event_ids.append("model_signal")
    event_ids.append("decision")
    return tuple(event_ids)


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
