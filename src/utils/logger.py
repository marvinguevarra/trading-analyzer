"""Structured logging for Trading Analyzer.

Provides consistent logging with timestamps, component names, and levels.
Logs to both console and file.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "trading_analyzer",
    level: str = "INFO",
    log_file: Optional[str] = None,
    console: bool = True,
) -> logging.Logger:
    """Create and configure a logger.

    Args:
        name: Logger name, typically the component name.
        level: Log level (DEBUG, INFO, WARNING, ERROR).
        log_file: Path to log file. None disables file logging.
        console: Whether to log to console.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(component: str) -> logging.Logger:
    """Get a child logger for a specific component.

    Usage:
        logger = get_logger("csv_parser")
        logger.info("Loaded 500 rows")
    """
    return logging.getLogger(f"trading_analyzer.{component}")
