"""Console logging utilities."""

import logging

logger = logging.getLogger("zapply")


def log_to_console(message: str) -> None:
    """Log message to console using standard Python logging."""
    logger.info(message)
