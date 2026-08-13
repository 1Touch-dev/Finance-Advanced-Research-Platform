import logging
from pythonjsonlogger import jsonlogger

logger = logging.getLogger("api")
_handler = logging.StreamHandler()
_handler.setFormatter(jsonlogger.JsonFormatter())
logger.addHandler(_handler)
logger.setLevel(logging.INFO)

_rag_logger = logging.getLogger("rag.metrics")
_rag_handler = logging.StreamHandler()
_rag_handler.setFormatter(jsonlogger.JsonFormatter(
    fmt="%(asctime)s %(name)s %(levelname)s %(message)s"
))
_rag_logger.addHandler(_rag_handler)
_rag_logger.setLevel(logging.INFO)
_rag_logger.propagate = False
