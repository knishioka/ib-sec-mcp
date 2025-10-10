"""Custom middleware for IB Analytics MCP Server

Provides error handling, retry logic, and request/response logging.
"""

import asyncio
import logging
import time
from typing import Any, Optional

from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext

logger = logging.getLogger(__name__)


class IBAnalyticsErrorMiddleware(Middleware):
    """
    Error handling middleware for IB Analytics MCP server

    Catches exceptions, logs them with context, and ensures proper error responses.
    """

    def __init__(self, include_traceback: bool = False):
        """
        Initialize error handling middleware

        Args:
            include_traceback: Whether to include traceback in error logs
        """
        self.include_traceback = include_traceback
        self.error_counts: dict[str, int] = {}

    async def on_message(self, context: MiddlewareContext, call_next: CallNext) -> Any:
        """
        Handle message with error catching and logging

        Args:
            context: Middleware context with request information
            call_next: Next middleware in chain

        Returns:
            Result from next middleware or error response
        """
        try:
            return await call_next(context)

        except Exception as error:
            # Track error statistics
            error_key = f"{type(error).__name__}:{context.method}"
            self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

            # Log error with context
            logger.error(
                f"Error in {context.method}: {type(error).__name__}: {error}",
                exc_info=self.include_traceback,
                extra={
                    "method": context.method,
                    "error_type": type(error).__name__,
                    "error_count": self.error_counts[error_key],
                },
            )

            # Re-raise to let FastMCP handle the error response
            raise

    def get_error_stats(self) -> dict[str, int]:
        """
        Get error statistics

        Returns:
            Dictionary mapping error patterns to counts
        """
        return self.error_counts.copy()


class IBAnalyticsRetryMiddleware(Middleware):
    """
    Retry middleware for transient errors

    Automatically retries failed requests for specific error types.
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        retry_exceptions: tuple[type[Exception], ...] = (ConnectionError, TimeoutError),
    ):
        """
        Initialize retry middleware

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries (exponential backoff)
            retry_exceptions: Exception types that trigger retries
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_exceptions = retry_exceptions

    async def on_message(self, context: MiddlewareContext, call_next: CallNext) -> Any:
        """
        Handle message with retry logic

        Args:
            context: Middleware context
            call_next: Next middleware in chain

        Returns:
            Result from next middleware
        """
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                return await call_next(context)

            except self.retry_exceptions as error:
                last_exception = error

                if attempt < self.max_retries:
                    # Calculate exponential backoff delay
                    delay = self.retry_delay * (2**attempt)

                    logger.warning(
                        f"Retry attempt {attempt + 1}/{self.max_retries} for {context.method} "
                        f"after {type(error).__name__}. Retrying in {delay:.1f}s...",
                        extra={
                            "method": context.method,
                            "attempt": attempt + 1,
                            "max_retries": self.max_retries,
                            "error_type": type(error).__name__,
                            "delay": delay,
                        },
                    )

                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Max retries ({self.max_retries}) exceeded for {context.method}",
                        extra={
                            "method": context.method,
                            "max_retries": self.max_retries,
                            "error_type": type(error).__name__,
                        },
                    )

            except Exception:
                # Other exceptions are not retried
                raise

        # If we get here, all retries failed
        if last_exception:
            raise last_exception
        else:
            # This should never happen, but just in case
            raise RuntimeError("Retry loop completed without exception or result")


class IBAnalyticsLoggingMiddleware(Middleware):
    """
    Request/response logging middleware

    Logs all MCP messages with timing and context information.
    """

    def __init__(self, log_level: int = logging.DEBUG):
        """
        Initialize logging middleware

        Args:
            log_level: Logging level for request/response logs
        """
        self.log_level = log_level

    async def on_message(self, context: MiddlewareContext, call_next: CallNext) -> Any:
        """
        Log request and response

        Args:
            context: Middleware context
            call_next: Next middleware in chain

        Returns:
            Result from next middleware
        """
        start_time = time.time()

        # Log request
        logger.log(
            self.log_level,
            f"→ {context.method}",
            extra={
                "method": context.method,
                "source": context.source,
                "direction": "request",
            },
        )

        try:
            result = await call_next(context)

            # Log successful response
            duration_ms = (time.time() - start_time) * 1000
            logger.log(
                self.log_level,
                f"← {context.method} ({duration_ms:.1f}ms)",
                extra={
                    "method": context.method,
                    "duration_ms": duration_ms,
                    "direction": "response",
                    "status": "success",
                },
            )

            return result

        except Exception as error:
            # Log error response
            duration_ms = (time.time() - start_time) * 1000
            logger.log(
                logging.ERROR,
                f"← {context.method} ({duration_ms:.1f}ms) - {type(error).__name__}",
                extra={
                    "method": context.method,
                    "duration_ms": duration_ms,
                    "direction": "response",
                    "status": "error",
                    "error_type": type(error).__name__,
                },
            )

            raise
