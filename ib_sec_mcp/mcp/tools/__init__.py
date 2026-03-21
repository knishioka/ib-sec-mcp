"""MCP Tools Registry

Central registration point for all MCP tools.
"""

from fastmcp import FastMCP


def register_all_tools(mcp: FastMCP) -> None:
    """Register all IB Analytics tools with MCP server"""

    # Import and register tools from each module
    from ib_sec_mcp.mcp.tools.composable_data import register_composable_data_tools
    from ib_sec_mcp.mcp.tools.daily_monitor import register_daily_monitor_tools
    from ib_sec_mcp.mcp.tools.etf_calculator_tools import (
        register_etf_calculator_tools,
    )
    from ib_sec_mcp.mcp.tools.etf_comparison import register_etf_comparison_tools
    from ib_sec_mcp.mcp.tools.ib_portfolio import register_ib_portfolio_tools
    from ib_sec_mcp.mcp.tools.limit_orders import register_limit_order_tools
    from ib_sec_mcp.mcp.tools.live_trading import register_live_trading_tools
    from ib_sec_mcp.mcp.tools.market_comparison import register_market_comparison_tools
    from ib_sec_mcp.mcp.tools.options import register_options_tools
    from ib_sec_mcp.mcp.tools.order_management import register_order_management_tools
    from ib_sec_mcp.mcp.tools.portfolio_analytics import (
        register_portfolio_analytics_tools,
    )
    from ib_sec_mcp.mcp.tools.position_history import register_position_history_tools
    from ib_sec_mcp.mcp.tools.rebalancing import register_rebalancing_tools
    from ib_sec_mcp.mcp.tools.sector_fx import register_sector_fx_tools
    from ib_sec_mcp.mcp.tools.sentiment_analysis import (
        register_sentiment_analysis_tools,
    )
    from ib_sec_mcp.mcp.tools.stock_data import register_stock_data_tools
    from ib_sec_mcp.mcp.tools.stock_news import register_stock_news_tools
    from ib_sec_mcp.mcp.tools.technical_analysis import (
        register_technical_analysis_tools,
    )

    # Register all tool groups
    register_ib_portfolio_tools(mcp)
    register_composable_data_tools(mcp)  # Add composable data tools
    register_stock_data_tools(mcp)
    register_stock_news_tools(mcp)
    register_options_tools(mcp)
    register_portfolio_analytics_tools(mcp)
    register_market_comparison_tools(mcp)
    register_etf_comparison_tools(mcp)  # Add ETF comparison tools
    register_technical_analysis_tools(mcp)  # Add technical analysis tools
    register_position_history_tools(mcp)  # Add position history tools
    register_etf_calculator_tools(mcp)  # Add ETF calculator tools
    register_sentiment_analysis_tools(mcp)  # Add sentiment analysis tools
    register_rebalancing_tools(mcp)  # Add rebalancing tools
    register_sector_fx_tools(mcp)  # Add sector allocation and FX exposure tools
    register_limit_order_tools(mcp)  # Add limit order management tools
    register_live_trading_tools(mcp)  # Add live trading tools via CP Gateway
    register_order_management_tools(mcp)  # Add order management tools (place/modify/cancel)
    register_daily_monitor_tools(mcp)  # Add daily monitor tools


__all__ = ["register_all_tools"]
