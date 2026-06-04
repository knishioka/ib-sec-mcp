"""Regression tests for Pydantic v2 JSON serialization (Issue #118).

After migrating away from the deprecated ``class Config`` / ``json_encoders``
pattern, these tests lock in the externally observable serialization behavior
that MCP JSON output depends on:

- ``Decimal`` values serialize to JSON **strings** (precision preserved,
  including trailing zeros), never floats.
- ``date`` / ``datetime`` values serialize to ISO 8601 strings.
- Serialization emits no ``DeprecationWarning`` (e.g. ``PydanticDeprecatedSince20``).
"""

from __future__ import annotations

import json
import warnings
from datetime import date, datetime
from decimal import Decimal

import pytest
from pydantic import PydanticDeprecationWarning

from ib_sec_mcp.analyzers.sentiment.base import SentimentScore
from ib_sec_mcp.api.models import CashSummary, FlexStatement
from ib_sec_mcp.models.account import Account, CashBalance
from ib_sec_mcp.models.position import Position
from ib_sec_mcp.models.trade import AssetClass, BuySell, Trade


@pytest.fixture
def sample_trade() -> Trade:
    return Trade(
        account_id="U1234567",
        trade_id="T001",
        trade_date=date(2025, 1, 15),
        settle_date=date(2025, 1, 17),
        symbol="AAPL",
        description="APPLE INC",
        asset_class=AssetClass.STOCK,
        buy_sell=BuySell.BUY,
        quantity=Decimal("100"),
        trade_price=Decimal("150.50"),
        trade_money=Decimal("-15050.00"),
        currency="USD",
        fx_rate_to_base=Decimal("1.0"),
        ib_commission=Decimal("-1.50"),
        fifo_pnl_realized=Decimal("500.00"),
        mtm_pnl=Decimal("200.00"),
    )


@pytest.fixture
def sample_position() -> Position:
    return Position(
        account_id="U1234567",
        symbol="AAPL",
        asset_class=AssetClass.STOCK,
        quantity=Decimal("100"),
        mark_price=Decimal("150.00"),
        position_value=Decimal("15000.00"),
        average_cost=Decimal("120.00"),
        cost_basis=Decimal("12000.00"),
        unrealized_pnl=Decimal("3000.00"),
        position_date=date(2025, 6, 30),
    )


@pytest.fixture
def sample_account(sample_position: Position, sample_trade: Trade) -> Account:
    return Account(
        account_id="U1234567",
        account_alias="Test Account",
        from_date=date(2025, 1, 1),
        to_date=date(2025, 6, 30),
        cash_balances=[
            CashBalance(
                currency="USD",
                starting_cash=Decimal("10000.00"),
                ending_cash=Decimal("11000.00"),
                ending_settled_cash=Decimal("10500.00"),
            )
        ],
        positions=[sample_position],
        trades=[sample_trade],
    )


class TestDecimalSerialization:
    """Decimal must serialize to JSON strings, preserving precision."""

    def test_trade_decimals_are_json_strings(self, sample_trade: Trade) -> None:
        data = json.loads(sample_trade.model_dump_json())
        # Trailing zeros preserved exactly as the source Decimal.
        assert data["trade_price"] == "150.50"
        assert data["trade_money"] == "-15050.00"
        assert data["ib_commission"] == "-1.50"
        # Strings, not floats.
        assert isinstance(data["trade_price"], str)
        assert isinstance(data["quantity"], str)

    def test_position_decimals_are_json_strings(self, sample_position: Position) -> None:
        data = json.loads(sample_position.model_dump_json())
        assert data["mark_price"] == "150.00"
        assert data["position_value"] == "15000.00"
        assert isinstance(data["unrealized_pnl"], str)

    def test_cash_summary_decimals_are_json_strings(self) -> None:
        summary = CashSummary(
            ClientAccountID="U1234567",
            Currency="USD",
            FromDate=date(2025, 1, 1),
            ToDate=date(2025, 6, 30),
            StartingCash=Decimal("1000.1200"),
            EndingCash=Decimal("2000.00"),
            EndingSettledCash=Decimal("1900.00"),
        )
        data = json.loads(summary.model_dump_json())
        assert data["starting_cash"] == "1000.1200"
        assert isinstance(data["ending_cash"], str)

    def test_sentiment_score_decimals_are_json_strings(self) -> None:
        score = SentimentScore(
            score=Decimal("0.50"),
            confidence=Decimal("0.80"),
            timestamp=datetime(2025, 1, 2, 3, 4, 5),
        )
        data = json.loads(score.model_dump_json())
        assert data["score"] == "0.50"
        assert data["confidence"] == "0.80"

    def test_nested_account_decimals_are_json_strings(self, sample_account: Account) -> None:
        """Nested models (positions/trades/cash) keep Decimal-as-string."""
        data = json.loads(sample_account.model_dump_json())
        assert isinstance(data["positions"][0]["mark_price"], str)
        assert isinstance(data["trades"][0]["trade_price"], str)
        assert isinstance(data["cash_balances"][0]["ending_cash"], str)


class TestDateSerialization:
    """date / datetime must serialize to ISO 8601 strings."""

    def test_trade_dates_are_iso_strings(self, sample_trade: Trade) -> None:
        data = json.loads(sample_trade.model_dump_json())
        assert data["trade_date"] == "2025-01-15"
        assert data["settle_date"] == "2025-01-17"

    def test_flex_statement_dates_are_iso_strings(self) -> None:
        statement = FlexStatement(
            query_id="Q1",
            account_id="U1234567",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 6, 30),
            when_generated=datetime(2025, 7, 1, 12, 30, 0),
            raw_data="<xml/>",
        )
        data = json.loads(statement.model_dump_json())
        assert data["from_date"] == "2025-01-01"
        assert data["when_generated"] == "2025-07-01T12:30:00"


class TestNoDeprecationWarnings:
    """Serialization must not emit Pydantic v1 deprecation warnings."""

    def test_model_dump_json_emits_no_deprecation_warning(
        self, sample_account: Account, sample_trade: Trade, sample_position: Position
    ) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error", PydanticDeprecationWarning)
            sample_account.model_dump_json()
            sample_trade.model_dump_json()
            sample_position.model_dump_json()
            sample_account.model_dump(mode="json")
