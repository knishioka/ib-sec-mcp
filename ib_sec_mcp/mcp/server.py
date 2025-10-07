"""FastMCP server for IB Analytics

Provides Model Context Protocol interface for Interactive Brokers portfolio analysis.
"""

import sys

from fastmcp import FastMCP

from ib_sec_mcp.mcp.prompts import register_prompts
from ib_sec_mcp.mcp.resources import register_resources
from ib_sec_mcp.mcp.tools import register_tools


def create_server() -> FastMCP:
    """
    Create and configure FastMCP server for IB Analytics

    Returns:
        Configured FastMCP server instance
    """
    mcp = FastMCP(
        name="ib-sec-mcp",
        instructions="""Interactive Brokers Portfolio Analytics MCP Server

This server provides tools and resources for analyzing Interactive Brokers trading data:

**Tools**: Fetch IB data, run various analyses (performance, costs, bonds, tax, risk)
**Resources**: Access portfolio summaries, account data, trades, and positions
**Prompts**: Pre-configured analysis templates

Authentication: Requires QUERY_ID and TOKEN in environment variables or .env file.
""",
    )

    # Register all components
    register_tools(mcp)
    register_resources(mcp)
    register_prompts(mcp)

    return mcp


def main() -> None:
    """Entry point for MCP server"""
    # Log to stderr (stdout is reserved for JSON-RPC)
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
