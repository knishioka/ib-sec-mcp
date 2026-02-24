"""MCP server startup smoke tests

Verifies that the server starts correctly and all expected tools and resources are registered.
"""

import asyncio

import pytest
from fastmcp import FastMCP

from ib_sec_mcp.mcp.resources import (
    RESOURCE_ACCOUNTS,
    RESOURCE_PORTFOLIO_LATEST,
    RESOURCE_PORTFOLIO_LIST,
    RESOURCE_POSITIONS_CURRENT,
    RESOURCE_STRATEGY_REBALANCING,
    RESOURCE_STRATEGY_RISK,
    RESOURCE_STRATEGY_TAX,
    RESOURCE_TRADES_RECENT,
    RESOURCE_USER_PROFILE,
)
from ib_sec_mcp.mcp.server import create_server

# All 45 expected tool names
EXPECTED_TOOLS = [
    # ib_portfolio
    "fetch_ib_data",
    "analyze_performance",
    "analyze_costs",
    "analyze_bonds",
    "analyze_tax",
    "analyze_risk",
    "analyze_consolidated_portfolio",
    "calculate_tax_loss_harvesting",
    "get_portfolio_summary",
    # composable_data
    "get_trades",
    "get_positions",
    "get_account_summary",
    "calculate_metric",
    "compare_periods",
    "analyze_dividend_income",
    # stock_data
    "get_stock_data",
    "get_current_price",
    "get_stock_info",
    # stock_news
    "get_stock_news",
    # options
    "get_options_chain",
    "calculate_put_call_ratio",
    "calculate_greeks",
    "calculate_iv_metrics",
    "calculate_max_pain",
    # portfolio_analytics
    "calculate_portfolio_metrics",
    "analyze_portfolio_correlation",
    # market_comparison
    "compare_with_benchmark",
    "get_analyst_consensus",
    # etf_comparison
    "compare_etf_performance",
    # technical_analysis
    "get_stock_analysis",
    "get_multi_timeframe_analysis",
    # position_history
    "get_position_history",
    "get_portfolio_snapshot",
    "compare_portfolio_snapshots",
    "get_position_statistics",
    "get_available_snapshot_dates",
    # etf_calculator_tools
    "calculate_etf_swap",
    "calculate_portfolio_swap",
    "validate_etf_price_mcp",
    # sentiment_analysis
    "analyze_market_sentiment",
    "get_news_sentiment",
    # rebalancing
    "generate_rebalancing_trades",
    "simulate_rebalancing",
    # sector_fx
    "analyze_sector_allocation",
    "analyze_fx_exposure",
]

# 8 non-template resources (RESOURCE_ACCOUNTS is a template with {account_id})
EXPECTED_RESOURCES = [
    RESOURCE_PORTFOLIO_LIST,
    RESOURCE_PORTFOLIO_LATEST,
    RESOURCE_TRADES_RECENT,
    RESOURCE_POSITIONS_CURRENT,
    RESOURCE_STRATEGY_TAX,
    RESOURCE_STRATEGY_REBALANCING,
    RESOURCE_STRATEGY_RISK,
    RESOURCE_USER_PROFILE,
]

# 1 template resource
EXPECTED_RESOURCE_TEMPLATES = [
    RESOURCE_ACCOUNTS,
]


class TestMCPServerStartup:
    """Smoke tests for Issue #52: MCP server startup and component registration"""

    @pytest.fixture(scope="class")
    def server(self) -> FastMCP:
        """Create a server instance for testing (no network calls)"""
        return create_server()

    def test_server_is_fastmcp_instance(self, server: FastMCP) -> None:
        """create_server() returns a FastMCP instance"""
        assert isinstance(server, FastMCP)

    def test_server_name(self, server: FastMCP) -> None:
        """Server is named ib-sec-mcp"""
        assert server.name == "ib-sec-mcp"

    def test_all_45_tools_registered(self, server: FastMCP) -> None:
        """All 45 tools are registered on the server"""
        tools = asyncio.run(server.get_tools())
        registered_names = set(tools.keys())
        assert len(registered_names) == 45, (
            f"Expected 45 tools, got {len(registered_names)}. "
            f"Missing: {set(EXPECTED_TOOLS) - registered_names}"
        )

    def test_spot_check_tools_registered(self, server: FastMCP) -> None:
        """Spot-check: required tools from acceptance criteria are registered"""
        tools = asyncio.run(server.get_tools())
        registered_names = set(tools.keys())

        required_tools = [
            "generate_rebalancing_trades",
            "analyze_sector_allocation",
            "analyze_dividend_income",
            "calculate_tax_loss_harvesting",
            "analyze_fx_exposure",
            "fetch_ib_data",
            "get_trades",
            "analyze_performance",
            "compare_etf_performance",
            "get_stock_analysis",
        ]
        for tool_name in required_tools:
            assert tool_name in registered_names, f"Required tool '{tool_name}' not registered"

    def test_all_expected_tool_names_registered(self, server: FastMCP) -> None:
        """Every tool in the expected list is registered"""
        tools = asyncio.run(server.get_tools())
        registered_names = set(tools.keys())

        missing = [t for t in EXPECTED_TOOLS if t not in registered_names]
        assert not missing, f"Missing tools: {missing}"

    def test_all_8_resources_registered(self, server: FastMCP) -> None:
        """All 8 non-template resources are registered"""
        resources = asyncio.run(server.get_resources())
        registered_uris = set(resources.keys())

        missing = [r for r in EXPECTED_RESOURCES if r not in registered_uris]
        assert not missing, f"Missing resources: {missing}"
        assert len(registered_uris) == len(EXPECTED_RESOURCES), (
            f"Expected {len(EXPECTED_RESOURCES)} resources, got {len(registered_uris)}"
        )

    def test_account_resource_template_registered(self, server: FastMCP) -> None:
        """The ib://accounts/{account_id} template resource is registered"""
        templates = asyncio.run(server.get_resource_templates())
        registered_uris = set(templates.keys())

        for template_uri in EXPECTED_RESOURCE_TEMPLATES:
            assert template_uri in registered_uris, (
                f"Template resource '{template_uri}' not registered"
            )

    def test_all_9_resource_uris_present(self, server: FastMCP) -> None:
        """All 9 resource URIs (8 static + 1 template) are registered"""
        resources = asyncio.run(server.get_resources())
        templates = asyncio.run(server.get_resource_templates())

        all_uris = set(resources.keys()) | set(templates.keys())
        all_expected = set(EXPECTED_RESOURCES) | set(EXPECTED_RESOURCE_TEMPLATES)

        missing = all_expected - all_uris
        assert not missing, f"Missing resource URIs: {missing}"
        assert len(all_uris) == 9, f"Expected 9 total resource URIs, got {len(all_uris)}"

    def test_server_starts_without_credentials(self) -> None:
        """Server creation requires no API credentials or network calls"""
        # Should succeed with no environment variables set
        server = create_server(enable_debug=False)
        assert isinstance(server, FastMCP)

    def test_debug_mode_server_creation(self) -> None:
        """create_server(enable_debug=True) also creates a valid FastMCP instance"""
        debug_server = create_server(enable_debug=True)
        assert isinstance(debug_server, FastMCP)
