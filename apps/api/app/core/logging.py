import os
import logging

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    _SENTRY_AVAILABLE = True
except ImportError:
    _SENTRY_AVAILABLE = False

try:
    from pythonjsonlogger import jsonlogger
    _JSON_LOGGER = True
except ImportError:
    _JSON_LOGGER = False

SENTRY_DSN = os.getenv("SENTRY_DSN", "")

if SENTRY_DSN and _SENTRY_AVAILABLE:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        traces_sample_rate=0.1,
        environment=os.getenv("ENV", "local"),
    )

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
