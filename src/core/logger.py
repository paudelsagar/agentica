import logging
import sys

import structlog


def configure_logger():
    """
    Configures structlog for JSON logging.
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Redirect standard logging to structlog
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)


def get_logger(name: str):
    return structlog.get_logger(name)
