import os
import logging
import time

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    _SENTRY_AVAILABLE = True
except ImportError:
    _SENTRY_AVAILABLE = False

try:
    try:
        from pythonjsonlogger import json as jsonlogger  # pythonjsonlogger >= 3.x
    except ImportError:
        from pythonjsonlogger import jsonlogger          # pythonjsonlogger < 3.x
    _JSON_LOGGER = True
except ImportError:
    _JSON_LOGGER = False

SENTRY_DSN = os.getenv("SENTRY_DSN", "")
_ENV = os.getenv("ENV", "local")
_RELEASE = os.getenv("APP_VERSION", os.getenv("RENDER_GIT_COMMIT", "dev"))

if SENTRY_DSN and _SENTRY_AVAILABLE:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=_ENV,
        release=_RELEASE,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            LoggingIntegration(
                level=logging.WARNING,        # breadcrumb level
                event_level=logging.ERROR,    # send as Sentry event
            ),
        ],
        # Performance
        traces_sample_rate=0.1 if _ENV == "production" else 0.0,
        profiles_sample_rate=0.05 if _ENV == "production" else 0.0,
        # Filter noise
        ignore_errors=[
            KeyboardInterrupt,
            SystemExit,
        ],
        # Strip PII from request bodies / stack locals
        send_default_pii=False,
        # Attach request info to every event
        attach_stacktrace=True,
        # Cap breadcrumbs
        max_breadcrumbs=50,
    )


def capture_exception(exc: Exception, extra: dict = None) -> None:
    """Send an exception to Sentry (no-op when Sentry is not configured)."""
    if SENTRY_DSN and _SENTRY_AVAILABLE:
        with sentry_sdk.push_scope() as scope:
            if extra:
                for k, v in extra.items():
                    scope.set_extra(k, v)
            sentry_sdk.capture_exception(exc)


def capture_message(message: str, level: str = "warning", extra: dict = None) -> None:
    """Send a message event to Sentry (no-op when Sentry is not configured)."""
    if SENTRY_DSN and _SENTRY_AVAILABLE:
        with sentry_sdk.push_scope() as scope:
            if extra:
                for k, v in extra.items():
                    scope.set_extra(k, v)
            sentry_sdk.capture_message(message, level=level)


logger = logging.getLogger("api")
_handler = logging.StreamHandler()
if _JSON_LOGGER:
    _handler.setFormatter(jsonlogger.JsonFormatter())
logger.addHandler(_handler)
logger.setLevel(logging.INFO)

_rag_logger = logging.getLogger("rag.metrics")
_rag_handler = logging.StreamHandler()
if _JSON_LOGGER:
    _rag_handler.setFormatter(jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s"
    ))
_rag_logger.addHandler(_rag_handler)
_rag_logger.setLevel(logging.INFO)
_rag_logger.propagate = False
