"""Central logging configuration for OWL runtime diagnostics."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys


LOGGER_NAME = "owl"
DEFAULT_LOG_DIRECTORY = Path("logs")
DEFAULT_LOG_FILE = "owl.log"
LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s %(message)s"


def configure_logging(
    *,
    debug: bool = False,
    log_directory: Path = DEFAULT_LOG_DIRECTORY,
) -> Path:
    """Configure private rotating-file logs and optional terminal diagnostics."""
    log_directory.mkdir(parents=True, exist_ok=True)
    log_path = log_directory / DEFAULT_LOG_FILE

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    formatter = logging.Formatter(LOG_FORMAT)
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if debug:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return log_path


def get_logger(component: str) -> logging.Logger:
    """Return a child logger under OWL's configured logging namespace."""
    return logging.getLogger(f"{LOGGER_NAME}.{component}")
