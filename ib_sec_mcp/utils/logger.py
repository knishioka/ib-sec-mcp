"""Unified logging configuration for IB Analytics

Provides centralized logging configuration with:
- stderr output (stdout reserved for MCP JSON-RPC)
- Environment-based debug mode
- Sensitive information masking
- Consistent formatting
"""

import logging
import sys
from pathlib import Path


def get_logger(name: str) -> logging.Logger:
    """
    Get configured logger instance for a module

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def configure_logging(debug: bool = False, log_file: Path | None = None) -> None:
    """
    Configure project-wide logging

    Args:
        debug: Enable debug mode (DEBUG level vs INFO level)
        log_file: Optional file path for log output (in addition to stderr)
    """
    # Configure root logger
    root_logger = logging.getLogger("ib_sec_mcp")

    # Set level based on debug mode
    level = logging.DEBUG if debug else logging.INFO
    root_logger.setLevel(level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Add stderr handler (stdout is reserved for JSON-RPC in MCP)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(level)
    stderr_handler.setFormatter(formatter)
    root_logger.addHandler(stderr_handler)

    # Add file handler if requested
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Log initial message
    root_logger.info(f"Logging configured (level={'DEBUG' if debug else 'INFO'})")


def mask_sensitive(value: str, show_chars: int = 4) -> str:
    """
    Mask sensitive information for logging

    Args:
        value: Value to mask
        show_chars: Number of characters to show at end

    Returns:
        Masked value (e.g., "****1234")
    """
    if not value or len(value) <= show_chars:
        return "****"

    return "*" * (len(value) - show_chars) + value[-show_chars:]
