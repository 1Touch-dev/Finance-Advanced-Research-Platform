import logging
from pythonjsonlogger import jsonlogger

logger = logging.getLogger("api")
_handler = logging.StreamHandler()
_handler.setFormatter(jsonlogger.JsonFormatter())
logger.addHandler(_handler)
logger.setLevel(logging.INFO)
