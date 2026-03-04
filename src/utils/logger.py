"""Logging utilities for CAD Repair Assistant."""

import logging
import os
from datetime import datetime
from pathlib import Path

# Create logs directory in project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Generate log filename with timestamp
LOG_FILENAME = f"cad_repair_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
LOG_FILE_PATH = LOGS_DIR / LOG_FILENAME

# Configure the logger
_logger = logging.getLogger("cad_repair_assistant")
_logger.setLevel(logging.DEBUG)

# Prevent adding duplicate handlers if module is reloaded
if not _logger.handlers:
    # File handler - logs everything to file
    file_handler = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    _logger.addHandler(file_handler)

    # Console handler - logs INFO and above to console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    _logger.addHandler(console_handler)

# Map string levels to logging levels
_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def log(message: str, level: str = "INFO") -> None:
    """
    Log a message with timestamp.

    Args:
        message: The message to log
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_level = _LEVEL_MAP.get(level.upper(), logging.INFO)
    _logger.log(log_level, message)


def get_logger() -> logging.Logger:
    """
    Get the underlying logger instance for advanced usage.

    Returns:
        The configured logger instance
    """
    return _logger


def get_log_file_path() -> Path:
    """
    Get the current log file path.

    Returns:
        Path to the current log file
    """
    return LOG_FILE_PATH
