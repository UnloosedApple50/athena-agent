"""Structured logging for Athena Agent."""

from __future__ import annotations

import sys
from functools import lru_cache

from loguru import logger

from athena.models.config import get_settings


class InterceptHandler:
    """Intercept standard logging and redirect to loguru."""

    def write(self, message: str) -> None:
        if message.strip():
            logger.info(message.strip())

    def flush(self) -> None:
        pass


@lru_cache
def get_logger(name: str = "athena") -> logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger namespace.

    Returns:
        Configured loguru logger instance.
    """
    settings = get_settings()

    # Remove default handler
    logger.remove()

    # Add stderr handler with structured format
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        backtrace=False,
        diagnose=False,
    )

    # Add file handler for production
    logger.add(
        "logs/athena_{time:YYYY-MM-DD}.log",
        rotation="10 MB",
        retention="30 days",
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        enqueue=True,  # Thread-safe
    )

    return logger.bind(name=name)
