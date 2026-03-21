"""Tests for order management MCP tools (place, modify, cancel)"""

import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastmcp import FastMCP

from ib_sec_mcp.api.cp_client import CPAuthenticationError, CPClientError, CPConnectionError
from ib_sec_mcp.api.cp_models import (
    CPOrder,
    CPOrderReply,
    CPOrderSide,
    CPOrderStatus,
)
from ib_sec_mcp.mcp.tools.order_management import (
    check_daily_limit,
    check_order_amount_limit,
    estimate_order_amount,
    get_daily_total,
    is_dry_run,
    is_read_only,
    mask_account_id,
    register_order_management_tools,
    write_order_log,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_mcp() -> FastMCP:
    """FastMCP instance with order management tools registered."""
    mcp = FastMCP("test")
    register_order_management_tools(mcp)
    return mcp


@pytest.fixture()
def order_log_path(tmp_path: Path) -> Path:
    """Temporary order log path."""
    return tmp_path / "order_log.jsonl"


@pytest.fixture()
def mock_order_reply() -> CPOrderReply:
    """Sample order reply."""
    return CPOrderReply(
        order_id="12345",
        order_status="Submitted",
        message=["Order submitted"],
    )


@pytest.fixture()
def mock_active_orders() -> list[CPOrder]:
    """Sample active orders for cancel_all tests."""
    return [
        CPOrder(
            orderId=1,
            symbol="AAPL",
            side=CPOrderSide.BUY,
            totalSize=Decimal("10"),
            price=Decimal("150.00"),
            avgPrice=Decimal("0"),
            status=CPOrderStatus.SUBMITTED,
            orderType="LMT",
            acct="U1234567",
        ),
        CPOrder(
            orderId=2,
            symbol="GLDM",
            side=CPOrderSide.BUY,
            totalSize=Decimal("25"),
            price=Decimal("89.00"),
            avgPrice=Decimal("0"),
            status=CPOrderStatus.SUBMITTED,
            orderType="LMT",
            acct="U1234567",
        ),
    ]


def _mock_cp_client(
    orders: list[CPOrder] | None = None,
    place_reply: list[CPOrderReply] | None = None,
    modify_reply: list[CPOrderReply] | None = None,
    cancel_result: dict | None = None,
    accounts: list[str] | None = None,
) -> MagicMock:
    """Create a mock CPClient as async context manager."""
    client = AsyncMock()
    client.get_orders = AsyncMock(return_value=orders or [])
    client.get_accounts = AsyncMock(return_value=accounts or ["U1234567"])
    client.place_order = AsyncMock(return_value=place_reply or [])
    client.modify_order = AsyncMock(return_value=modify_reply or [])
    client.cancel_order = AsyncMock(return_value=cancel_result or {"msg": "cancelled"})

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


# ---------------------------------------------------------------------------
# Tests: Safety helper functions
# ---------------------------------------------------------------------------


class TestIsReadOnly:
    """Tests for is_read_only helper."""

    def test_default_is_not_read_only(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            assert is_read_only() is False

    def test_read_only_when_set_to_1(self) -> None:
        with patch.dict("os.environ", {"IB_READ_ONLY": "1"}):
            assert is_read_only() is True

    def test_read_only_when_set_to_true(self) -> None:
        with patch.dict("os.environ", {"IB_READ_ONLY": "true"}):
            assert is_read_only() is True

    def test_not_read_only_when_set_to_0(self) -> None:
        with patch.dict("os.environ", {"IB_READ_ONLY": "0"}):
            assert is_read_only() is False


class TestIsDryRun:
    """Tests for is_dry_run helper."""

    def test_default_is_dry_run(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            assert is_dry_run() is True

    def test_dry_run_when_set_to_1(self) -> None:
        with patch.dict("os.environ", {"IB_ORDER_DRY_RUN": "1"}):
            assert is_dry_run() is True

    def test_not_dry_run_when_set_to_0(self) -> None:
        with patch.dict("os.environ", {"IB_ORDER_DRY_RUN": "0"}):
            assert is_dry_run() is False

    def test_not_dry_run_when_set_to_false(self) -> None:
        with patch.dict("os.environ", {"IB_ORDER_DRY_RUN": "false"}):
            assert is_dry_run() is False


class TestEstimateOrderAmount:
    """Tests for estimate_order_amount helper."""

    def test_calculates_amount(self) -> None:
        assert estimate_order_amount(Decimal("100"), Decimal("150.50")) == Decimal("15050.00")

    def test_returns_zero_for_no_price(self) -> None:
        assert estimate_order_amount(Decimal("100"), None) == Decimal("0")

    def test_returns_zero_for_zero_price(self) -> None:
        assert estimate_order_amount(Decimal("100"), Decimal("0")) == Decimal("0")

    def test_uses_absolute_value(self) -> None:
        assert estimate_order_amount(Decimal("-100"), Decimal("150")) == Decimal("15000")


class TestCheckOrderAmountLimit:
    """Tests for check_order_amount_limit helper."""

    def test_within_limit(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            result = check_order_amount_limit(Decimal("10"), Decimal("100"))
            assert result is None

    def test_exceeds_limit(self) -> None:
        with patch.dict("os.environ", {"IB_MAX_ORDER_AMOUNT_USD": "1000"}):
            result = check_order_amount_limit(Decimal("100"), Decimal("20"))
            assert result is not None
            assert "exceeds" in result
            assert "$2000" in result

    def test_no_check_for_market_orders(self) -> None:
        result = check_order_amount_limit(Decimal("100"), None)
        assert result is None

    def test_default_limit(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            result = check_order_amount_limit(Decimal("1"), Decimal("1"))
            assert result is None  # $1 is within $50,000 default


class TestMaskAccountId:
    """Tests for mask_account_id helper."""

    def test_masks_account_id(self) -> None:
        masked = mask_account_id("U1234567")
        assert "U1234567" not in masked
        assert "4567" in masked

    def test_short_account_id(self) -> None:
        masked = mask_account_id("U123")
        assert isinstance(masked, str)


class TestWriteOrderLog:
    """Tests for write_order_log helper."""

    def test_writes_log_entry(self, order_log_path: Path) -> None:
        record = write_order_log(
            log_path=order_log_path,
            action="place",
            account_id="U1234567",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("100"),
            limit_price=Decimal("150.50"),
            order_id="12345",
            status="submitted",
            dry_run=False,
        )
        assert record["action"] == "place"
        assert record["symbol"] == "AAPL"
        assert record["side"] == "BUY"
        assert record["quantity"] == "100"
        assert record["status"] == "submitted"
        assert record["dry_run"] is False
        # Account must be masked
        assert "U1234567" not in record["account_id"]

        # File must exist and contain valid JSONL
        lines = order_log_path.read_text().strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["symbol"] == "AAPL"

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        log_path = tmp_path / "nested" / "dir" / "log.jsonl"
        write_order_log(
            log_path=log_path,
            action="place",
            account_id="U1234567",
            symbol="GLDM",
            side="BUY",
            quantity=Decimal("25"),
            limit_price=Decimal("89.00"),
            order_id=None,
            status="dry_run",
            dry_run=True,
        )
        assert log_path.exists()

    def test_appends_to_existing_log(self, order_log_path: Path) -> None:
        for i in range(3):
            write_order_log(
                log_path=order_log_path,
                action="place",
                account_id="U1234567",
                symbol=f"SYM{i}",
                side="BUY",
                quantity=Decimal("1"),
                limit_price=Decimal("1"),
                order_id=str(i),
                status="submitted",
                dry_run=False,
            )
        lines = order_log_path.read_text().strip().split("\n")
        assert len(lines) == 3

    def test_account_id_is_masked_in_log(self, order_log_path: Path) -> None:
        write_order_log(
            log_path=order_log_path,
            action="place",
            account_id="U9995070",
            symbol="AAPL",
            side="BUY",
            quantity=Decimal("10"),
            limit_price=Decimal("150"),
            order_id=None,
            status="dry_run",
            dry_run=True,
        )
        content = order_log_path.read_text()
        assert "U9995070" not in content
        assert "5070" in content


class TestGetDailyTotal:
    """Tests for get_daily_total helper."""

    def test_returns_zero_for_missing_file(self, tmp_path: Path) -> None:
        assert get_daily_total(tmp_path / "nonexistent.jsonl") == Decimal("0")

    def test_calculates_daily_total(self, order_log_path: Path) -> None:
        from datetime import UTC, datetime

        today = datetime.now(UTC).isoformat()
        entries = [
            {
                "timestamp": today,
                "action": "place",
                "quantity": "100",
                "limit_price": "150",
                "status": "submitted",
                "dry_run": False,
            },
            {
                "timestamp": today,
                "action": "place",
                "quantity": "50",
                "limit_price": "200",
                "status": "submitted",
                "dry_run": False,
            },
        ]
        with open(order_log_path, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        total = get_daily_total(order_log_path)
        assert total == Decimal("25000")  # 100*150 + 50*200

    def test_excludes_dry_runs(self, order_log_path: Path) -> None:
        from datetime import UTC, datetime

        today = datetime.now(UTC).isoformat()
        entry = {
            "timestamp": today,
            "action": "place",
            "quantity": "100",
            "limit_price": "150",
            "status": "dry_run",
            "dry_run": True,
        }
        with open(order_log_path, "w") as f:
            f.write(json.dumps(entry) + "\n")

        assert get_daily_total(order_log_path) == Decimal("0")

    def test_excludes_cancellations(self, order_log_path: Path) -> None:
        from datetime import UTC, datetime

        today = datetime.now(UTC).isoformat()
        entry = {
            "timestamp": today,
            "action": "cancel",
            "quantity": "100",
            "limit_price": "150",
            "status": "submitted",
            "dry_run": False,
        }
        with open(order_log_path, "w") as f:
            f.write(json.dumps(entry) + "\n")

        assert get_daily_total(order_log_path) == Decimal("0")


class TestCheckDailyLimit:
    """Tests for check_daily_limit helper."""

    def test_within_limit(self, order_log_path: Path) -> None:
        with patch.dict("os.environ", {}, clear=True):
            result = check_daily_limit(Decimal("10"), Decimal("100"), order_log_path)
            assert result is None

    def test_exceeds_limit(self, order_log_path: Path) -> None:
        with patch.dict("os.environ", {"IB_DAILY_ORDER_LIMIT_USD": "1000"}):
            result = check_daily_limit(Decimal("100"), Decimal("20"), order_log_path)
            assert result is not None
            assert "daily limit" in result


# ---------------------------------------------------------------------------
# Tests: place_order MCP tool
# ---------------------------------------------------------------------------


class TestPlaceOrder:
    """Tests for the place_order MCP tool."""

    @pytest.mark.asyncio
    async def test_dry_run_mode_default(self, test_mcp: FastMCP, tmp_path: Path) -> None:
        """Dry-run mode is ON by default - no API call made."""
        with (
            patch.dict(
                "os.environ", {"IB_ORDER_LOG_PATH": str(tmp_path / "log.jsonl")}, clear=True
            ),
            patch("ib_sec_mcp.mcp.tools.order_management.CPClient") as mock_client_cls,
        ):
            tool = await test_mcp.get_tool("place_order")
            result = await tool.fn(
                account_id="U1234567",
                contract_id=265598,
                symbol="AAPL",
                side="BUY",
                quantity="100",
                order_type="LMT",
                limit_price="150.50",
                ctx=None,
            )
            data = json.loads(result)

        assert data["dry_run"] is True
        assert "DRY RUN" in data["message"]
        assert data["order_details"]["symbol"] == "AAPL"
        assert data["order_details"]["side"] == "BUY"
        assert data["order_details"]["quantity"] == "100"
        # CPClient should NOT have been used
        mock_client_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_dry_run_logs_to_file(self, test_mcp: FastMCP, tmp_path: Path) -> None:
        log_path = tmp_path / "log.jsonl"
        with patch.dict(
            "os.environ",
            {"IB_ORDER_LOG_PATH": str(log_path)},
            clear=True,
        ):
            tool = await test_mcp.get_tool("place_order")
            await tool.fn(
                account_id="U1234567",
                contract_id=265598,
                symbol="GLDM",
                side="BUY",
                quantity="25",
                order_type="LMT",
                limit_price="89.00",
                ctx=None,
            )

        assert log_path.exists()
        record = json.loads(log_path.read_text().strip())
        assert record["action"] == "place"
        assert record["dry_run"] is True
        assert record["symbol"] == "GLDM"

    @pytest.mark.asyncio
    async def test_live_order_placement(
        self, test_mcp: FastMCP, tmp_path: Path, mock_order_reply: CPOrderReply
    ) -> None:
        mock_cm = _mock_cp_client(place_reply=[mock_order_reply])
        log_path = tmp_path / "log.jsonl"
        with (
            patch.dict(
                "os.environ",
                {"IB_ORDER_DRY_RUN": "0", "IB_ORDER_LOG_PATH": str(log_path)},
            ),
            patch("ib_sec_mcp.mcp.tools.order_management.CPClient", return_value=mock_cm),
        ):
            tool = await test_mcp.get_tool("place_order")
            result = await tool.fn(
                account_id="U1234567",
                contract_id=265598,
                symbol="AAPL",
                side="BUY",
                quantity="10",
                order_type="LMT",
                limit_price="150.00",
                ctx=None,
            )
            data = json.loads(result)

        assert data["dry_run"] is False
        assert data["status"] == "Submitted"
        assert data["order_id"] == "12345"

    @pytest.mark.asyncio
    async def test_read_only_mode_blocks_placement(self, test_mcp: FastMCP) -> None:
        with patch.dict("os.environ", {"IB_READ_ONLY": "1"}):
            tool = await test_mcp.get_tool("place_order")
            result = await tool.fn(
                account_id="U1234567",
                contract_id=265598,
                symbol="AAPL",
                side="BUY",
                quantity="10",
                order_type="LMT",
                limit_price="150.00",
                ctx=None,
            )
            data = json.loads(result)

        assert "error" in data
        assert "IB_READ_ONLY" in data["error"]

    @pytest.mark.asyncio
    async def test_amount_limit_exceeded(self, test_mcp: FastMCP, tmp_path: Path) -> None:
        with patch.dict(
            "os.environ",
            {
                "IB_MAX_ORDER_AMOUNT_USD": "1000",
                "IB_ORDER_LOG_PATH": str(tmp_path / "log.jsonl"),
            },
        ):
            tool = await test_mcp.get_tool("place_order")
            result = await tool.fn(
                account_id="U1234567",
                contract_id=265598,
                symbol="AAPL",
                side="BUY",
                quantity="100",
                order_type="LMT",
                limit_price="150.00",
                ctx=None,
            )
            data = json.loads(result)

        assert "error" in data
        assert "exceeds" in data["error"]

    @pytest.mark.asyncio
    async def test_daily_limit_exceeded(self, test_mcp: FastMCP, tmp_path: Path) -> None:
        log_path = tmp_path / "log.jsonl"
        # Pre-populate with orders near the limit
        from datetime import UTC, datetime

        today = datetime.now(UTC).isoformat()
        entry = {
            "timestamp": today,
            "action": "place",
            "quantity": "100",
            "limit_price": "1900",
            "status": "submitted",
            "dry_run": False,
        }
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "w") as f:
            f.write(json.dumps(entry) + "\n")

        with patch.dict(
            "os.environ",
            {
                "IB_DAILY_ORDER_LIMIT_USD": "200000",
                "IB_ORDER_LOG_PATH": str(log_path),
            },
        ):
            tool = await test_mcp.get_tool("place_order")
            result = await tool.fn(
                account_id="U1234567",
                contract_id=265598,
                symbol="AAPL",
                side="BUY",
                quantity="100",
                order_type="LMT",
                limit_price="200",
                ctx=None,
            )
            data = json.loads(result)

        assert "error" in data
        assert "daily limit" in data["error"]

    @pytest.mark.asyncio
    async def test_invalid_side(self, test_mcp: FastMCP) -> None:
        with patch.dict("os.environ", {}, clear=True):
            tool = await test_mcp.get_tool("place_order")
            result = await tool.fn(
                account_id="U1234567",
                contract_id=265598,
                symbol="AAPL",
                side="INVALID",
                quantity="10",
                ctx=None,
            )
            data = json.loads(result)

        assert "error" in data
        assert "Invalid side" in data["error"]

    @pytest.mark.asyncio
    async def test_invalid_order_type(self, test_mcp: FastMCP) -> None:
        with patch.dict("os.environ", {}, clear=True):
            tool = await test_mcp.get_tool("place_order")
            result = await tool.fn(
                account_id="U1234567",
                contract_id=265598,
                symbol="AAPL",
                side="BUY",
                quantity="10",
                order_type="INVALID",
                ctx=None,
            )
            data = json.loads(result)

        assert "error" in data
        assert "Invalid order type" in data["error"]

    @pytest.mark.asyncio
    async def test_limit_price_required_for_lmt(self, test_mcp: FastMCP, tmp_path: Path) -> None:
        with patch.dict(
            "os.environ",
            {"IB_ORDER_LOG_PATH": str(tmp_path / "log.jsonl")},
            clear=True,
        ):
            tool = await test_mcp.get_tool("place_order")
            result = await tool.fn(
                account_id="U1234567",
                contract_id=265598,
                symbol="AAPL",
                side="BUY",
                quantity="10",
                order_type="LMT",
                ctx=None,
            )
            data = json.loads(result)

        assert "error" in data
        assert "Limit price is required" in data["error"]

    @pytest.mark.asyncio
    async def test_zero_quantity_rejected(self, test_mcp: FastMCP) -> None:
        with patch.dict("os.environ", {}, clear=True):
            tool = await test_mcp.get_tool("place_order")
            result = await tool.fn(
                account_id="U1234567",
                contract_id=265598,
                symbol="AAPL",
                side="BUY",
                quantity="0",
                ctx=None,
            )
            data = json.loads(result)

        assert "error" in data
        assert "positive" in data["error"]

    @pytest.mark.asyncio
    async def test_gateway_not_running(self, test_mcp: FastMCP, tmp_path: Path) -> None:
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=CPConnectionError("unreachable"))
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        with (
            patch.dict(
                "os.environ",
                {"IB_ORDER_DRY_RUN": "0", "IB_ORDER_LOG_PATH": str(tmp_path / "log.jsonl")},
            ),
            patch("ib_sec_mcp.mcp.tools.order_management.CPClient", return_value=mock_cm),
        ):
            tool = await test_mcp.get_tool("place_order")
            result = await tool.fn(
                account_id="U1234567",
                contract_id=265598,
                symbol="AAPL",
                side="BUY",
                quantity="10",
                order_type="LMT",
                limit_price="150.00",
                ctx=None,
            )
            data = json.loads(result)

        assert "error" in data
        assert "not running" in data["error"]

    @pytest.mark.asyncio
    async def test_session_expired(self, test_mcp: FastMCP, tmp_path: Path) -> None:
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=CPAuthenticationError("expired"))
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        with (
            patch.dict(
                "os.environ",
                {"IB_ORDER_DRY_RUN": "0", "IB_ORDER_LOG_PATH": str(tmp_path / "log.jsonl")},
            ),
            patch("ib_sec_mcp.mcp.tools.order_management.CPClient", return_value=mock_cm),
        ):
            tool = await test_mcp.get_tool("place_order")
            result = await tool.fn(
                account_id="U1234567",
                contract_id=265598,
                symbol="AAPL",
                side="BUY",
                quantity="10",
                order_type="LMT",
                limit_price="150.00",
                ctx=None,
            )
            data = json.loads(result)

        assert "error" in data
        assert "expired" in data["error"]

    @pytest.mark.asyncio
    async def test_api_error_logs_rejection(self, test_mcp: FastMCP, tmp_path: Path) -> None:
        mock_cm = _mock_cp_client()
        client = await mock_cm.__aenter__()
        client.place_order = AsyncMock(side_effect=CPClientError("Insufficient funds"))
        log_path = tmp_path / "log.jsonl"

        with (
            patch.dict(
                "os.environ",
                {"IB_ORDER_DRY_RUN": "0", "IB_ORDER_LOG_PATH": str(log_path)},
            ),
            patch("ib_sec_mcp.mcp.tools.order_management.CPClient", return_value=mock_cm),
        ):
            tool = await test_mcp.get_tool("place_order")
            result = await tool.fn(
                account_id="U1234567",
                contract_id=265598,
                symbol="AAPL",
                side="BUY",
                quantity="10",
                order_type="LMT",
                limit_price="150.00",
                ctx=None,
            )
            data = json.loads(result)

        assert "error" in data
        # Log should contain rejected entry
        record = json.loads(log_path.read_text().strip())
        assert record["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_decimal_precision_preserved(self, test_mcp: FastMCP, tmp_path: Path) -> None:
        log_path = tmp_path / "log.jsonl"
        with patch.dict(
            "os.environ",
            {"IB_ORDER_LOG_PATH": str(log_path)},
            clear=True,
        ):
            tool = await test_mcp.get_tool("place_order")
            result = await tool.fn(
                account_id="U1234567",
                contract_id=265598,
                symbol="AAPL",
                side="BUY",
                quantity="10.5",
                order_type="LMT",
                limit_price="150.75",
                ctx=None,
            )
            data = json.loads(result)

        assert data["order_details"]["quantity"] == "10.5"
        assert data["order_details"]["limit_price"] == "150.75"
        # Verify log record has Decimal strings
        Decimal(data["log"]["quantity"])
        Decimal(data["log"]["limit_price"])


# ---------------------------------------------------------------------------
# Tests: modify_order MCP tool
# ---------------------------------------------------------------------------


class TestModifyOrder:
    """Tests for the modify_order MCP tool."""

    @pytest.mark.asyncio
    async def test_dry_run_modify(self, test_mcp: FastMCP, tmp_path: Path) -> None:
        with patch.dict(
            "os.environ",
            {"IB_ORDER_LOG_PATH": str(tmp_path / "log.jsonl")},
            clear=True,
        ):
            tool = await test_mcp.get_tool("modify_order")
            result = await tool.fn(
                account_id="U1234567",
                order_id=12345,
                symbol="AAPL",
                quantity="50",
                limit_price="155.00",
                ctx=None,
            )
            data = json.loads(result)

        assert data["dry_run"] is True
        assert data["order_id"] == 12345

    @pytest.mark.asyncio
    async def test_live_modify(
        self, test_mcp: FastMCP, tmp_path: Path, mock_order_reply: CPOrderReply
    ) -> None:
        mock_cm = _mock_cp_client(modify_reply=[mock_order_reply])
        with (
            patch.dict(
                "os.environ",
                {"IB_ORDER_DRY_RUN": "0", "IB_ORDER_LOG_PATH": str(tmp_path / "log.jsonl")},
            ),
            patch("ib_sec_mcp.mcp.tools.order_management.CPClient", return_value=mock_cm),
        ):
            tool = await test_mcp.get_tool("modify_order")
            result = await tool.fn(
                account_id="U1234567",
                order_id=12345,
                symbol="AAPL",
                limit_price="160.00",
                ctx=None,
            )
            data = json.loads(result)

        assert data["dry_run"] is False
        assert data["status"] == "Submitted"

    @pytest.mark.asyncio
    async def test_read_only_blocks_modify(self, test_mcp: FastMCP) -> None:
        with patch.dict("os.environ", {"IB_READ_ONLY": "1"}):
            tool = await test_mcp.get_tool("modify_order")
            result = await tool.fn(
                account_id="U1234567",
                order_id=12345,
                symbol="AAPL",
                quantity="50",
                ctx=None,
            )
            data = json.loads(result)

        assert "error" in data
        assert "IB_READ_ONLY" in data["error"]

    @pytest.mark.asyncio
    async def test_no_modifications_provided(self, test_mcp: FastMCP) -> None:
        with patch.dict("os.environ", {}, clear=True):
            tool = await test_mcp.get_tool("modify_order")
            result = await tool.fn(
                account_id="U1234567",
                order_id=12345,
                symbol="AAPL",
                ctx=None,
            )
            data = json.loads(result)

        assert "error" in data
        assert "At least one" in data["error"]

    @pytest.mark.asyncio
    async def test_amount_limit_on_modify(self, test_mcp: FastMCP, tmp_path: Path) -> None:
        with patch.dict(
            "os.environ",
            {
                "IB_MAX_ORDER_AMOUNT_USD": "1000",
                "IB_ORDER_LOG_PATH": str(tmp_path / "log.jsonl"),
            },
        ):
            tool = await test_mcp.get_tool("modify_order")
            result = await tool.fn(
                account_id="U1234567",
                order_id=12345,
                symbol="AAPL",
                quantity="100",
                limit_price="20.00",
                ctx=None,
            )
            data = json.loads(result)

        assert "error" in data
        assert "exceeds" in data["error"]


# ---------------------------------------------------------------------------
# Tests: cancel_order MCP tool
# ---------------------------------------------------------------------------


class TestCancelOrder:
    """Tests for the cancel_order MCP tool."""

    @pytest.mark.asyncio
    async def test_dry_run_cancel(self, test_mcp: FastMCP, tmp_path: Path) -> None:
        with patch.dict(
            "os.environ",
            {"IB_ORDER_LOG_PATH": str(tmp_path / "log.jsonl")},
            clear=True,
        ):
            tool = await test_mcp.get_tool("cancel_order")
            result = await tool.fn(
                account_id="U1234567",
                order_id=12345,
                symbol="AAPL",
                ctx=None,
            )
            data = json.loads(result)

        assert data["dry_run"] is True
        assert data["order_id"] == 12345

    @pytest.mark.asyncio
    async def test_live_cancel(self, test_mcp: FastMCP, tmp_path: Path) -> None:
        mock_cm = _mock_cp_client(cancel_result={"msg": "Order cancelled"})
        with (
            patch.dict(
                "os.environ",
                {"IB_ORDER_DRY_RUN": "0", "IB_ORDER_LOG_PATH": str(tmp_path / "log.jsonl")},
            ),
            patch("ib_sec_mcp.mcp.tools.order_management.CPClient", return_value=mock_cm),
        ):
            tool = await test_mcp.get_tool("cancel_order")
            result = await tool.fn(
                account_id="U1234567",
                order_id=12345,
                symbol="AAPL",
                ctx=None,
            )
            data = json.loads(result)

        assert data["dry_run"] is False
        assert data["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_read_only_blocks_cancel(self, test_mcp: FastMCP) -> None:
        with patch.dict("os.environ", {"IB_READ_ONLY": "1"}):
            tool = await test_mcp.get_tool("cancel_order")
            result = await tool.fn(
                account_id="U1234567",
                order_id=12345,
                symbol="AAPL",
                ctx=None,
            )
            data = json.loads(result)

        assert "error" in data
        assert "IB_READ_ONLY" in data["error"]

    @pytest.mark.asyncio
    async def test_cancel_logs_entry(self, test_mcp: FastMCP, tmp_path: Path) -> None:
        log_path = tmp_path / "log.jsonl"
        with patch.dict(
            "os.environ",
            {"IB_ORDER_LOG_PATH": str(log_path)},
            clear=True,
        ):
            tool = await test_mcp.get_tool("cancel_order")
            await tool.fn(
                account_id="U1234567",
                order_id=12345,
                symbol="AAPL",
                ctx=None,
            )

        record = json.loads(log_path.read_text().strip())
        assert record["action"] == "cancel"
        assert "U1234567" not in record["account_id"]


# ---------------------------------------------------------------------------
# Tests: cancel_all_orders MCP tool
# ---------------------------------------------------------------------------


class TestCancelAllOrders:
    """Tests for the cancel_all_orders MCP tool."""

    @pytest.mark.asyncio
    async def test_dry_run_cancel_all(self, test_mcp: FastMCP, tmp_path: Path) -> None:
        with patch.dict(
            "os.environ",
            {"IB_ORDER_LOG_PATH": str(tmp_path / "log.jsonl")},
            clear=True,
        ):
            tool = await test_mcp.get_tool("cancel_all_orders")
            result = await tool.fn(ctx=None)
            data = json.loads(result)

        assert data["dry_run"] is True
        assert "DRY RUN" in data["message"]

    @pytest.mark.asyncio
    async def test_live_cancel_all(
        self, test_mcp: FastMCP, tmp_path: Path, mock_active_orders: list[CPOrder]
    ) -> None:
        mock_cm = _mock_cp_client(
            orders=mock_active_orders,
            cancel_result={"msg": "cancelled"},
        )
        with (
            patch.dict(
                "os.environ",
                {"IB_ORDER_DRY_RUN": "0", "IB_ORDER_LOG_PATH": str(tmp_path / "log.jsonl")},
            ),
            patch("ib_sec_mcp.mcp.tools.order_management.CPClient", return_value=mock_cm),
        ):
            tool = await test_mcp.get_tool("cancel_all_orders")
            result = await tool.fn(ctx=None)
            data = json.loads(result)

        assert data["dry_run"] is False
        assert data["total_cancelled"] == 2
        assert data["total_failed"] == 0

    @pytest.mark.asyncio
    async def test_no_active_orders(self, test_mcp: FastMCP, tmp_path: Path) -> None:
        mock_cm = _mock_cp_client(orders=[])
        with (
            patch.dict(
                "os.environ",
                {"IB_ORDER_DRY_RUN": "0", "IB_ORDER_LOG_PATH": str(tmp_path / "log.jsonl")},
            ),
            patch("ib_sec_mcp.mcp.tools.order_management.CPClient", return_value=mock_cm),
        ):
            tool = await test_mcp.get_tool("cancel_all_orders")
            result = await tool.fn(ctx=None)
            data = json.loads(result)

        assert "No active orders" in data["message"]

    @pytest.mark.asyncio
    async def test_read_only_blocks_cancel_all(self, test_mcp: FastMCP) -> None:
        with patch.dict("os.environ", {"IB_READ_ONLY": "1"}):
            tool = await test_mcp.get_tool("cancel_all_orders")
            result = await tool.fn(ctx=None)
            data = json.loads(result)

        assert "error" in data
        assert "IB_READ_ONLY" in data["error"]

    @pytest.mark.asyncio
    async def test_gateway_not_running(self, test_mcp: FastMCP, tmp_path: Path) -> None:
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(side_effect=CPConnectionError("unreachable"))
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        with (
            patch.dict(
                "os.environ",
                {"IB_ORDER_DRY_RUN": "0", "IB_ORDER_LOG_PATH": str(tmp_path / "log.jsonl")},
            ),
            patch("ib_sec_mcp.mcp.tools.order_management.CPClient", return_value=mock_cm),
        ):
            tool = await test_mcp.get_tool("cancel_all_orders")
            result = await tool.fn(ctx=None)
            data = json.loads(result)

        assert "error" in data
        assert "not running" in data["error"]
