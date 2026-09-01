"""Central logging configuration for OWL runtime diagnostics."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys


LOGGER_NAME = "owl"
DEFAULT_LOG_DIRECTORY = Path("logs")
DEFAULT_LOG_FILE = "owl.log"
LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s %(message)s"
TERMINAL_PREFIX = "[OWL LOG]"
_RESET = "\033[0m"
_BOLD_CYAN = "\033[1;36m"
_MAGENTA = "\033[35m"
_LEVEL_COLORS = {
    logging.DEBUG: "\033[90m",
    logging.INFO: "\033[32m",
    logging.WARNING: "\033[33m",
    logging.ERROR: "\033[31m",
    logging.CRITICAL: "\033[1;31m",
}


class OwlTerminalFormatter(logging.Formatter):
    """Format debug-terminal records for quick visual scanning."""

    def __init__(self, *, use_color: bool) -> None:
        super().__init__()
        self._use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, "%H:%M:%S")
        level = f"{record.levelname:<8}"
        component = record.name.removeprefix(f"{LOGGER_NAME}.").upper()
        message = record.getMessage()

        if self._use_color:
            level_color = _LEVEL_COLORS.get(record.levelno, "")
            rendered = (
                f"{_BOLD_CYAN}{TERMINAL_PREFIX}{_RESET} {timestamp} │ "
                f"{level_color}{level}{_RESET} │ "
                f"{_MAGENTA}{component:<18}{_RESET} │ {message}"
            )
        else:
            rendered = (
                f"{TERMINAL_PREFIX} {timestamp} │ {level} │ "
                f"{component:<18} │ {message}"
            )

        if record.exc_info:
            rendered = f"{rendered}\n{self.formatException(record.exc_info)}"
        return rendered


def configure_logging(
    *,
    debug: bool = False,
    log_directory: Path = DEFAULT_LOG_DIRECTORY,
    color: bool | None = None,
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
        color_supported = sys.stderr.isatty() if color is None else color
        color_enabled = color_supported and "NO_COLOR" not in os.environ
        console_handler.setFormatter(
            OwlTerminalFormatter(use_color=color_enabled)
        )
        logger.addHandler(console_handler)

    return log_path


def get_logger(component: str) -> logging.Logger:
    """Return a child logger under OWL's configured logging namespace."""
    return logging.getLogger(f"{LOGGER_NAME}.{component}")
