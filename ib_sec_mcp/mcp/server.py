"""FastMCP server for IB Analytics

Provides Model Context Protocol interface for Interactive Brokers portfolio analysis.
"""

import logging

from fastmcp import FastMCP
from fastmcp.utilities.logging import configure_logging

from ib_sec_mcp.mcp.middleware import (
    IBAnalyticsErrorMiddleware,
    IBAnalyticsLoggingMiddleware,
    IBAnalyticsRetryMiddleware,
)
from ib_sec_mcp.mcp.prompts import register_prompts
from ib_sec_mcp.mcp.resources import register_resources
from ib_sec_mcp.mcp.tools import register_all_tools


def create_server(enable_debug: bool = False) -> FastMCP:
    """
    Create and configure FastMCP server for IB Analytics

    Args:
        enable_debug: Enable debug logging and detailed error information

    Returns:
        Configured FastMCP server instance with security and middleware
    """
    # Create server with security settings
    mcp = FastMCP(
        name="ib-sec-mcp",
        instructions="""Interactive Brokers Portfolio Analytics MCP Server

This server provides tools and resources for analyzing Interactive Brokers trading data:

**Tools**: Fetch IB data, run various analyses (performance, costs, bonds, tax, risk), Yahoo Finance data
**Resources**: Access portfolio summaries, account data, trades, and positions
**Prompts**: Pre-configured analysis templates

Authentication: Requires QUERY_ID and TOKEN in environment variables or .env file.

**Security**: All sensitive information is protected. Internal errors are masked for security.
""",
        # Security: Mask internal error details from clients
        mask_error_details=not enable_debug,
    )

    # Add middleware (order matters: logging → retry → error)
    # 1. Logging middleware (logs all requests/responses)
    mcp.add_middleware(
        IBAnalyticsLoggingMiddleware(log_level=logging.DEBUG if enable_debug else logging.INFO)
    )

    # 2. Retry middleware (handles transient errors)
    mcp.add_middleware(
        IBAnalyticsRetryMiddleware(
            max_retries=3,
            retry_delay=1.0,
            retry_exceptions=(ConnectionError, TimeoutError),
        )
    )

    # 3. Error handling middleware (catches and logs all errors)
    mcp.add_middleware(IBAnalyticsErrorMiddleware(include_traceback=enable_debug))

    # Register all components
    register_all_tools(mcp)
    register_resources(mcp)
    register_prompts(mcp)

    return mcp


def main() -> None:
    """Entry point for MCP server"""
    # Check for debug mode from environment
    import os

    enable_debug = os.getenv("IB_DEBUG", "").lower() in ("1", "true", "yes")

    # Configure FastMCP logging with rich tracebacks
    configure_logging(
        level="DEBUG" if enable_debug else "INFO",
        enable_rich_tracebacks=enable_debug,
    )

    # Additional logging to stderr (stdout is reserved for JSON-RPC)
    logger = logging.getLogger("ib-sec-mcp")
    logger.info(f"Starting IB Analytics MCP Server (debug={'ON' if enable_debug else 'OFF'})")

    server = create_server(enable_debug=enable_debug)
    server.run()


if __name__ == "__main__":
    main()
