"""
ETF Calculator MCP Tools

Provides MCP tool wrappers for ETF swap calculations.
All arithmetic calculations are performed in Python to prevent LLM calculation errors.
"""

import json
import os
from decimal import Decimal

from fastmcp import FastMCP

from ib_sec_mcp.tools.etf_calculator import (
    ETFSwapCalculator,
    validate_etf_price,
)

_DEFAULT_TRADING_FEE_USD = 75.0


def _get_etf_swap_calculator(trading_fee_usd: float | None) -> ETFSwapCalculator:
    """Create ETFSwapCalculator with trading fee from parameter or TRADING_FEE_USD env var."""
    if trading_fee_usd is None:
        trading_fee_usd = float(os.environ.get("TRADING_FEE_USD", str(_DEFAULT_TRADING_FEE_USD)))
    return ETFSwapCalculator(trading_fee_usd=Decimal(str(trading_fee_usd)))


def register_etf_calculator_tools(mcp: FastMCP) -> None:
    """Register ETF calculator tools with MCP server"""

    @mcp.tool()
    def calculate_etf_swap(
        from_symbol: str,
        from_shares: int,
        from_price: float,
        from_expense_ratio: float,
        from_dividend_yield: float,
        from_withholding_tax: float,
        to_symbol: str,
        to_price: float,
        to_expense_ratio: float,
        to_dividend_yield: float,
        to_withholding_tax: float,
        trading_fee_usd: float | None = None,
    ) -> str:
        """
        Calculate ETF swap requirements with exact share counts

        **IMPORTANT**: This tool performs all arithmetic calculations to prevent LLM errors.
        Always use this tool instead of manual calculation.

        Args:
            from_symbol: Symbol of ETF to sell (e.g., "VOO")
            from_shares: Number of shares to sell
            from_price: Current price of from_symbol
            from_expense_ratio: Expense ratio as decimal (e.g., 0.0003 for 0.03%)
            from_dividend_yield: Dividend yield as decimal (e.g., 0.0115 for 1.15%)
            from_withholding_tax: Withholding tax rate as decimal (e.g., 0.30 for 30%)
            to_symbol: Symbol of ETF to buy (e.g., "CSPX")
            to_price: Current price of to_symbol
            to_expense_ratio: Expense ratio as decimal
            to_dividend_yield: Dividend yield as decimal
            to_withholding_tax: Withholding tax rate as decimal (e.g., 0.00 for 0%, 0.15 for 15%)
            trading_fee_usd: Trading fee in USD. If not provided, reads from
                TRADING_FEE_USD env var (default: 75.0)

        Returns:
            JSON string with calculation results including:
            - Required shares to purchase
            - Purchase amount and surplus/deficit cash
            - Annual tax savings and expense changes
            - Payback period in months

        Example:
            >>> result = calculate_etf_swap(
            ...     from_symbol="TLT",
            ...     from_shares=200,
            ...     from_price=91.34,
            ...     from_expense_ratio=0.0015,
            ...     from_dividend_yield=0.0433,
            ...     from_withholding_tax=0.30,
            ...     to_symbol="IDTL",
            ...     to_price=3.40,
            ...     to_expense_ratio=0.0007,
            ...     to_dividend_yield=0.0445,
            ...     to_withholding_tax=0.15
            ... )
        """
        calculator = _get_etf_swap_calculator(trading_fee_usd)

        calc = calculator.calculate_swap(
            from_symbol=from_symbol,
            from_shares=from_shares,
            from_price=Decimal(str(from_price)),
            from_expense_ratio=Decimal(str(from_expense_ratio)),
            from_dividend_yield=Decimal(str(from_dividend_yield)),
            from_withholding_tax=Decimal(str(from_withholding_tax)),
            to_symbol=to_symbol,
            to_price=Decimal(str(to_price)),
            to_expense_ratio=Decimal(str(to_expense_ratio)),
            to_dividend_yield=Decimal(str(to_dividend_yield)),
            to_withholding_tax=Decimal(str(to_withholding_tax)),
        )

        # Convert to JSON-serializable format
        result = {
            "from_etf": {
                "symbol": calc.from_etf.symbol,
                "shares": int(calc.from_etf.shares),
                "price": float(calc.from_etf.price),
                "total_value": float(calc.from_etf.total_value),
                "expense_ratio": float(calc.from_etf.expense_ratio),
                "dividend_yield": float(calc.from_etf.dividend_yield),
                "withholding_tax_rate": float(calc.from_etf.withholding_tax_rate),
            },
            "to_etf": {
                "symbol": calc.to_etf.symbol,
                "shares": int(calc.to_etf.shares),
                "price": float(calc.to_etf.price),
                "total_value": float(calc.to_etf.total_value),
                "expense_ratio": float(calc.to_etf.expense_ratio),
                "dividend_yield": float(calc.to_etf.dividend_yield),
                "withholding_tax_rate": float(calc.to_etf.withholding_tax_rate),
            },
            "required_shares": calc.required_shares,
            "purchase_amount": float(calc.purchase_amount),
            "surplus_cash": float(calc.surplus_cash),
            "annual_withholding_tax_savings": float(calc.annual_withholding_tax_savings),
            "annual_expense_change": float(calc.annual_expense_change),
            "annual_net_benefit": float(calc.annual_net_benefit),
            "payback_period_months": (
                calc.payback_period_months if calc.payback_period_months != float("inf") else None
            ),
            "formatted_output": calculator.format_calculation_result(calc),
        }

        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool()
    def calculate_portfolio_swap(
        swaps: str,
        trading_fee_usd: float | None = None,
    ) -> str:
        """
        Calculate multiple ETF swaps for portfolio restructuring

        **IMPORTANT**: This tool performs all arithmetic calculations to prevent LLM errors.
        Use this for portfolio-wide analysis.

        Args:
            swaps: JSON string containing list of swap specifications
                Format:
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
                        "to_withholding_tax": 0.00
                    },
                    ...
                ]
            trading_fee_usd: Trading fee in USD. If not provided, reads from
                TRADING_FEE_USD env var (default: 75.0)

        Returns:
            JSON string with:
            - Individual swap calculations
            - Portfolio-wide summary
            - Total tax savings and payback period

        Example:
            >>> swaps_json = json.dumps([...])
            >>> result = calculate_portfolio_swap(swaps=swaps_json)
        """
        calculator = _get_etf_swap_calculator(trading_fee_usd)

        # Parse JSON input
        swaps_list = json.loads(swaps)

        # Calculate
        portfolio_result = calculator.calculate_portfolio_swap(swaps_list)

        # Format individual results for JSON
        formatted_results = []
        for calc in portfolio_result["individual_results"]:
            formatted_results.append(
                {
                    "from_etf": {
                        "symbol": calc.from_etf.symbol,
                        "shares": int(calc.from_etf.shares),
                        "price": float(calc.from_etf.price),
                        "total_value": float(calc.from_etf.total_value),
                    },
                    "to_etf": {
                        "symbol": calc.to_etf.symbol,
                        "shares": int(calc.to_etf.shares),
                        "price": float(calc.to_etf.price),
                        "total_value": float(calc.to_etf.total_value),
                    },
                    "required_shares": calc.required_shares,
                    "purchase_amount": float(calc.purchase_amount),
                    "surplus_cash": float(calc.surplus_cash),
                    "annual_net_benefit": float(calc.annual_net_benefit),
                    "payback_period_months": (
                        calc.payback_period_months
                        if calc.payback_period_months != float("inf")
                        else None
                    ),
                }
            )

        result = {
            "individual_results": formatted_results,
            "summary": portfolio_result["summary"],
        }

        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool()
    def validate_etf_price_mcp(
        symbol: str,
        price: float,
        reference_symbol: str | None = None,
        reference_price: float | None = None,
    ) -> str:
        """
        Validate ETF price for potential errors

        **IMPORTANT**: Use this before calculations to catch price errors early.
        This helps prevent calculation mistakes like the IDTL incident (stated $88.67, actual $3.40).

        Args:
            symbol: ETF symbol to validate
            price: Price to validate
            reference_symbol: Optional reference ETF symbol (tracking same index)
            reference_price: Optional reference ETF price

        Returns:
            JSON string with validation results:
            - is_valid: Boolean indicating if price seems correct
            - warnings: List of warning messages
            - price_ratio: Ratio compared to reference (if provided)

        Example:
            >>> result = validate_etf_price_mcp(
            ...     symbol="IDTL",
            ...     price=3.40,
            ...     reference_symbol="TLT",
            ...     reference_price=91.34
            ... )
        """
        validation = validate_etf_price(
            symbol=symbol,
            price=Decimal(str(price)),
            reference_symbol=reference_symbol,
            reference_price=Decimal(str(reference_price)) if reference_price else None,
        )

        return json.dumps(validation, indent=2, ensure_ascii=False)


__all__ = ["register_etf_calculator_tools"]
