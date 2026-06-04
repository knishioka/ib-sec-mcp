"""MCP server startup smoke tests.

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
from tests.mcp._fastmcp_helpers import (
    list_resource_template_uris,
    list_resource_uris,
    list_tool_names,
)

# All expected tool names
EXPECTED_TOOLS = {
    # ib_portfolio
    "fetch_ib_data",
    "analyze_performance",
    "analyze_costs",
    "analyze_bonds",
    "analyze_tax",
    "analyze_risk",
    "analyze_consolidated_portfolio",
    "calculate_tax_loss_harvesting",
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
    # sentiment_analysis
    "analyze_market_sentiment",
    # rebalancing
    "generate_rebalancing_trades",
    "simulate_rebalancing",
    # sector_fx
    "analyze_sector_allocation",
    "analyze_fx_exposure",
    # limit_orders (always-on, not gated)
    "add_limit_order",
    "update_limit_order",
    "get_pending_orders",
    "check_order_proximity",
    "get_order_history",
    "sync_limit_orders",
    # daily_monitor
    "sync_daily_snapshot",
    "get_sync_status",
    # earnings_calendar
    "get_earnings_calendar",
}

# CP Gateway live-trading tools gated behind IB_ENABLE_LIVE_TRADING (default OFF).
# Absent from the default server; present only when the flag is enabled.
LIVE_TRADING_TOOLS = {
    # live_trading
    "get_live_orders",
    "get_live_account_balance",
    "get_live_positions",
    "check_gateway_status",
    # order_management
    "place_order",
    "modify_order",
    "cancel_order",
    "cancel_all_orders",
}

# Non-template resources
EXPECTED_RESOURCES = {
    RESOURCE_PORTFOLIO_LIST,
    RESOURCE_PORTFOLIO_LATEST,
    RESOURCE_TRADES_RECENT,
    RESOURCE_POSITIONS_CURRENT,
    RESOURCE_STRATEGY_TAX,
    RESOURCE_STRATEGY_REBALANCING,
    RESOURCE_STRATEGY_RISK,
    RESOURCE_USER_PROFILE,
}

# Template resources
EXPECTED_RESOURCE_TEMPLATES = {
    RESOURCE_ACCOUNTS,
}


class TestMCPServerStartup:
    """Smoke tests for Issue #52: MCP server startup and component registration"""

    @pytest.fixture(scope="class")
    def server(self) -> FastMCP:
        """Create a server instance for testing (no network calls)"""
        return create_server()

    @pytest.fixture(scope="class")
    def registered_tools(self, server: FastMCP) -> set[str]:
        """Fetch registered tool names once for all tests in the class."""
        return asyncio.run(list_tool_names(server))

    @pytest.fixture(scope="class")
    def registered_resources(self, server: FastMCP) -> set[str]:
        """Fetch registered static resource URIs once for all tests in the class."""
        return asyncio.run(list_resource_uris(server))

    @pytest.fixture(scope="class")
    def registered_templates(self, server: FastMCP) -> set[str]:
        """Fetch registered resource template URIs once for all tests in the class."""
        return asyncio.run(list_resource_template_uris(server))

    def test_server_is_fastmcp_instance(self, server: FastMCP) -> None:
        """create_server() returns a FastMCP instance"""
        assert isinstance(server, FastMCP)

    def test_server_name(self, server: FastMCP) -> None:
        """Server is named ib-sec-mcp"""
        assert server.name == "ib-sec-mcp"

    def test_all_expected_tools_registered(self, registered_tools: set[str]) -> None:
        """All expected tools are registered, with no extras or missing"""
        assert registered_tools == EXPECTED_TOOLS, (
            f"Missing: {EXPECTED_TOOLS - registered_tools}, "
            f"Unexpected: {registered_tools - EXPECTED_TOOLS}"
        )

    def test_live_trading_tools_absent_by_default(self, registered_tools: set[str]) -> None:
        """CP Gateway live-trading tools are NOT advertised when the flag is unset"""
        assert registered_tools.isdisjoint(LIVE_TRADING_TOOLS), (
            f"Live-trading tools must be gated off by default, but found: "
            f"{registered_tools & LIVE_TRADING_TOOLS}"
        )

    def test_all_resource_uris_registered(
        self, registered_resources: set[str], registered_templates: set[str]
    ) -> None:
        """All expected resource URIs (static + templates) are registered"""
        all_registered = registered_resources | registered_templates
        all_expected = EXPECTED_RESOURCES | EXPECTED_RESOURCE_TEMPLATES
        assert all_registered == all_expected, (
            f"Missing: {all_expected - all_registered}, Unexpected: {all_registered - all_expected}"
        )

    def test_server_starts_without_credentials(self) -> None:
        """Server creation requires no API credentials or network calls"""
        server = create_server(enable_debug=False)
        assert isinstance(server, FastMCP)

    def test_debug_mode_server_creation(self) -> None:
        """create_server(enable_debug=True) also creates a valid FastMCP instance"""
        debug_server = create_server(enable_debug=True)
        assert isinstance(debug_server, FastMCP)


class TestLiveTradingGate:
    """Issue #140: IB_ENABLE_LIVE_TRADING registration gate for CP Gateway tools"""

    def test_gated_tools_absent_when_flag_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """With IB_ENABLE_LIVE_TRADING unset, the 8 gated tools are absent and base tools present"""
        monkeypatch.delenv("IB_ENABLE_LIVE_TRADING", raising=False)
        server = create_server()
        tools = asyncio.run(list_tool_names(server))
        assert tools.isdisjoint(LIVE_TRADING_TOOLS)
        assert tools >= EXPECTED_TOOLS

    @pytest.mark.parametrize("flag_value", ["1", "true", "yes"])
    def test_gated_tools_present_when_flag_enabled(
        self, monkeypatch: pytest.MonkeyPatch, flag_value: str
    ) -> None:
        """With IB_ENABLE_LIVE_TRADING enabled, all 8 gated tools are advertised"""
        monkeypatch.setenv("IB_ENABLE_LIVE_TRADING", flag_value)
        server = create_server()
        tools = asyncio.run(list_tool_names(server))
        assert tools >= LIVE_TRADING_TOOLS, f"Missing: {LIVE_TRADING_TOOLS - tools}"
        assert tools >= EXPECTED_TOOLS

    def test_local_limit_order_tools_present_in_both_states(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The 5 local limit_orders tools are advertised regardless of the flag"""
        local_tools = {
            "add_limit_order",
            "update_limit_order",
            "get_pending_orders",
            "check_order_proximity",
            "get_order_history",
        }
        monkeypatch.delenv("IB_ENABLE_LIVE_TRADING", raising=False)
        off_tools = asyncio.run(list_tool_names(create_server()))
        monkeypatch.setenv("IB_ENABLE_LIVE_TRADING", "1")
        on_tools = asyncio.run(list_tool_names(create_server()))
        assert local_tools <= off_tools
        assert local_tools <= on_tools
