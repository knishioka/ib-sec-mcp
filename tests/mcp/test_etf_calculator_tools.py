"""Tests for the ETF calculator MCP tools.

Covers ``calculate_etf_swap`` and ``calculate_portfolio_swap`` wrappers, including
trading-fee resolution (param vs TRADING_FEE_USD env var) and payback serialization.
"""

import json

import pytest
from fastmcp import FastMCP

from ib_sec_mcp.mcp.tools.etf_calculator_tools import register_etf_calculator_tools
from tests.mcp._fastmcp_helpers import call_tool_fn

SINGLE_SWAP_KWARGS = {
    "from_symbol": "TLT",
    "from_shares": 200,
    "from_price": 91.34,
    "from_expense_ratio": 0.0015,
    "from_dividend_yield": 0.0433,
    "from_withholding_tax": 0.30,
    "to_symbol": "IDTL",
    "to_price": 3.40,
    "to_expense_ratio": 0.0007,
    "to_dividend_yield": 0.0445,
    "to_withholding_tax": 0.15,
}


@pytest.fixture()
def test_mcp() -> FastMCP:
    mcp = FastMCP("test")
    register_etf_calculator_tools(mcp)
    return mcp


class TestCalculateEtfSwap:
    async def test_returns_valid_json_with_expected_keys(self, test_mcp: FastMCP) -> None:
        result = await call_tool_fn(test_mcp, "calculate_etf_swap", **SINGLE_SWAP_KWARGS)
        data = json.loads(result)

        assert data["required_shares"] == 5373
        assert data["from_etf"]["symbol"] == "TLT"
        assert data["to_etf"]["symbol"] == "IDTL"
        assert "purchase_amount" in data
        assert "annual_net_benefit" in data
        assert "formatted_output" in data

    async def test_positive_benefit_payback_is_number(self, test_mcp: FastMCP) -> None:
        result = await call_tool_fn(test_mcp, "calculate_etf_swap", **SINGLE_SWAP_KWARGS)
        data = json.loads(result)
        assert isinstance(data["payback_period_months"], (int, float))
        assert data["payback_period_months"] > 0

    async def test_no_benefit_payback_serialized_as_null(self, test_mcp: FastMCP) -> None:
        kwargs = {
            "from_symbol": "GOOD",
            "from_shares": 100,
            "from_price": 100.0,
            "from_expense_ratio": 0.0003,
            "from_dividend_yield": 0.02,
            "from_withholding_tax": 0.00,
            "to_symbol": "BAD",
            "to_price": 100.0,
            "to_expense_ratio": 0.0015,
            "to_dividend_yield": 0.02,
            "to_withholding_tax": 0.30,
        }
        result = await call_tool_fn(test_mcp, "calculate_etf_swap", **kwargs)
        data = json.loads(result)
        # Infinite payback is converted to None (JSON null), never "inf".
        assert data["payback_period_months"] is None

    async def test_trading_fee_from_env_var(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TRADING_FEE_USD", "10")
        cheap = json.loads(await call_tool_fn(test_mcp, "calculate_etf_swap", **SINGLE_SWAP_KWARGS))

        monkeypatch.setenv("TRADING_FEE_USD", "150")
        pricey = json.loads(
            await call_tool_fn(test_mcp, "calculate_etf_swap", **SINGLE_SWAP_KWARGS)
        )

        assert pricey["payback_period_months"] > cheap["payback_period_months"]

    async def test_explicit_trading_fee_overrides_env(
        self, test_mcp: FastMCP, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TRADING_FEE_USD", "999")
        result = await call_tool_fn(
            test_mcp, "calculate_etf_swap", trading_fee_usd=10.0, **SINGLE_SWAP_KWARGS
        )
        explicit = json.loads(result)["payback_period_months"]

        result_env = await call_tool_fn(test_mcp, "calculate_etf_swap", **SINGLE_SWAP_KWARGS)
        env_based = json.loads(result_env)["payback_period_months"]
        # Explicit $10 fee gives a much shorter payback than the $999 env fee.
        assert explicit < env_based


class TestCalculatePortfolioSwap:
    async def test_portfolio_swap_returns_summary(self, test_mcp: FastMCP) -> None:
        swaps = json.dumps(
            [
                {
                    "from_symbol": "VOO",
                    "from_shares": 40,
                    "from_price": 607.39,
                    "from_expense_ratio": 0.0003,
                    "from_dividend_yield": 0.0115,
                    "from_withholding_tax": 0.30,
                    "to_symbol": "CSPX",
                    "to_price": 714.78,
                    "to_expense_ratio": 0.0007,
                    "to_dividend_yield": 0.0115,
                    "to_withholding_tax": 0.00,
                }
            ]
        )
        result = await call_tool_fn(test_mcp, "calculate_portfolio_swap", swaps=swaps)
        data = json.loads(result)

        assert len(data["individual_results"]) == 1
        assert data["summary"]["total_from_shares"] == 40
        assert "annual_net_benefit" in data["summary"]
        assert data["individual_results"][0]["from_etf"]["symbol"] == "VOO"

    async def test_malformed_swaps_json_raises(self, test_mcp: FastMCP) -> None:
        with pytest.raises(json.JSONDecodeError):
            await call_tool_fn(test_mcp, "calculate_portfolio_swap", swaps="not json")
