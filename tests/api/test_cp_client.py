"""Tests for Client Portal Gateway API client"""

import logging
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from ib_sec_mcp.api.cp_client import (
    CPAuthenticationError,
    CPClient,
    CPClientError,
    CPConnectionError,
)
from ib_sec_mcp.api.cp_models import CPAccountBalance, CPAuthStatus, CPOrder, CPPosition

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_async_mock_response(
    json_data: dict | list,  # type: ignore[type-arg]
    status_code: int = 200,
) -> MagicMock:
    """Create a mock httpx.Response with JSON data"""
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data

    if status_code >= 400:
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=mock_response,
        )
    else:
        mock.raise_for_status = MagicMock()

    return mock


AUTH_AUTHENTICATED = {
    "authenticated": True,
    "competing": False,
    "connected": True,
    "message": "",
}

AUTH_NOT_AUTHENTICATED = {
    "authenticated": False,
    "competing": False,
    "connected": True,
    "message": "Session expired",
}

REAUTH_SUCCESS = {"message": "triggered"}

SAMPLE_ORDERS = {
    "orders": [
        {
            "orderId": 100,
            "symbol": "AAPL",
            "side": "BUY",
            "totalSize": "50",
            "price": "150.00",
            "avgPrice": "0",
            "status": "Submitted",
            "orderType": "LMT",
            "acct": "U1234567",
        },
        {
            "orderId": 101,
            "symbol": "MSFT",
            "side": "SELL",
            "totalSize": "25",
            "price": "300.00",
            "avgPrice": "300.50",
            "status": "Filled",
            "orderType": "LMT",
            "acct": "U1234567",
        },
    ]
}

SAMPLE_ACCOUNTS = [
    {"id": "U1234567", "accountId": "U1234567"},
    {"id": "U7654321", "accountId": "U7654321"},
]

SAMPLE_BALANCE = {
    "netliquidation": {"amount": "1000000.50", "currency": "USD"},
    "totalcashvalue": {"amount": "250000.75", "currency": "USD"},
    "buyingpower": {"amount": "500000.00", "currency": "USD"},
    "grosspositionvalue": {"amount": "750000.25", "currency": "USD"},
}

SAMPLE_POSITIONS = [
    {
        "acctId": "U1234567",
        "conid": 265598,
        "symbol": "AAPL",
        "position": "100",
        "mktPrice": "175.50",
        "mktValue": "17550.00",
        "avgCost": "150.25",
        "unrealizedPnl": "2525.00",
        "currency": "USD",
    }
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cp_client() -> CPClient:
    """Create a CPClient with test defaults"""
    return CPClient(
        gateway_url="https://localhost:5000",
        verify_ssl=False,
        max_retries=3,
        retry_delay=0,
    )


@pytest.fixture
def mock_httpx_client() -> AsyncMock:
    """Create a mock httpx.AsyncClient"""
    mock = AsyncMock()
    return mock


# ---------------------------------------------------------------------------
# TestCPClientInit
# ---------------------------------------------------------------------------


class TestCPClientInit:
    def test_default_url(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            client = CPClient()
            assert client.gateway_url == "https://localhost:5000"

    def test_custom_url(self) -> None:
        client = CPClient(gateway_url="https://myhost:5001")
        assert client.gateway_url == "https://myhost:5001"

    def test_url_from_env(self) -> None:
        with patch.dict("os.environ", {"IB_GATEWAY_URL": "https://envhost:9000"}):
            client = CPClient()
            assert client.gateway_url == "https://envhost:9000"

    def test_url_trailing_slash_stripped(self) -> None:
        client = CPClient(gateway_url="https://localhost:5000/")
        assert client.gateway_url == "https://localhost:5000"

    def test_http_url_rejected(self) -> None:
        with pytest.raises(CPClientError, match="HTTP is not allowed"):
            CPClient(gateway_url="http://localhost:5000")

    def test_http_env_url_rejected(self) -> None:
        with (
            patch.dict("os.environ", {"IB_GATEWAY_URL": "http://insecure:5000"}),
            pytest.raises(CPClientError, match="HTTP is not allowed"),
        ):
            CPClient()

    def test_verify_ssl_default_false(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            client = CPClient()
            assert client.verify_ssl is False

    def test_verify_ssl_from_env_true(self) -> None:
        with patch.dict("os.environ", {"IB_GATEWAY_VERIFY_SSL": "true"}):
            client = CPClient()
            assert client.verify_ssl is True

    def test_verify_ssl_explicit(self) -> None:
        client = CPClient(verify_ssl=True)
        assert client.verify_ssl is True

    def test_default_retries(self) -> None:
        client = CPClient()
        assert client.max_retries == 3
        assert client.retry_delay == 1

    def test_custom_retries(self) -> None:
        client = CPClient(max_retries=5, retry_delay=2)
        assert client.max_retries == 5
        assert client.retry_delay == 2


# ---------------------------------------------------------------------------
# TestCPClientAuthStatus
# ---------------------------------------------------------------------------


class TestCPClientAuthStatus:
    @pytest.mark.asyncio
    async def test_check_auth_authenticated(self, cp_client: CPClient) -> None:
        mock_response = make_async_mock_response(AUTH_AUTHENTICATED)

        async with cp_client as client:
            client._client.request = AsyncMock(return_value=mock_response)
            status = await client.check_auth_status()

            assert isinstance(status, CPAuthStatus)
            assert status.authenticated is True
            assert status.connected is True

    @pytest.mark.asyncio
    async def test_check_auth_expired(self, cp_client: CPClient) -> None:
        mock_response = make_async_mock_response(AUTH_NOT_AUTHENTICATED)

        async with cp_client as client:
            client._client.request = AsyncMock(return_value=mock_response)
            status = await client.check_auth_status()

            assert status.authenticated is False
            assert status.message == "Session expired"


# ---------------------------------------------------------------------------
# TestCPClientReauthenticate
# ---------------------------------------------------------------------------


class TestCPClientReauthenticate:
    @pytest.mark.asyncio
    async def test_reauthenticate_success(self, cp_client: CPClient) -> None:
        mock_response = make_async_mock_response(REAUTH_SUCCESS)

        async with cp_client as client:
            client._client.request = AsyncMock(return_value=mock_response)
            result = await client.reauthenticate()
            assert result is True

    @pytest.mark.asyncio
    async def test_reauthenticate_failure(self, cp_client: CPClient) -> None:
        async with cp_client as client:
            client._client.request = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            with pytest.raises(CPAuthenticationError, match="Reauthentication failed"):
                await client.reauthenticate()

    @pytest.mark.asyncio
    async def test_ensure_authenticated_reauth_still_fails(self, cp_client: CPClient) -> None:
        """Test that CPAuthenticationError is raised when reauth succeeds but session stays unauthenticated"""
        not_auth_resp = make_async_mock_response(AUTH_NOT_AUTHENTICATED)
        reauth_resp = make_async_mock_response(REAUTH_SUCCESS)

        async with cp_client as client:
            client._client.request = AsyncMock(
                side_effect=[not_auth_resp, reauth_resp, not_auth_resp]
            )
            with pytest.raises(
                CPAuthenticationError,
                match="Session still not authenticated",
            ):
                await client._ensure_authenticated()


# ---------------------------------------------------------------------------
# TestCPClientRetry
# ---------------------------------------------------------------------------


class TestCPClientRetry:
    @pytest.mark.asyncio
    async def test_retry_succeeds_on_second_attempt(self, cp_client: CPClient) -> None:
        fail_response = make_async_mock_response({}, status_code=500)
        ok_response = make_async_mock_response({"status": "ok"})

        async with cp_client as client:
            client._client.request = AsyncMock(side_effect=[fail_response, ok_response])
            result = await client._request("GET", "/test")
            assert result == {"status": "ok"}
            assert client._client.request.call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, cp_client: CPClient) -> None:
        fail_response = make_async_mock_response({}, status_code=500)

        async with cp_client as client:
            client._client.request = AsyncMock(
                side_effect=[fail_response, fail_response, fail_response]
            )
            with pytest.raises(CPClientError, match="Request failed after 3 attempts"):
                await client._request("GET", "/test")

    @pytest.mark.asyncio
    async def test_401_not_retried(self, cp_client: CPClient) -> None:
        fail_response = make_async_mock_response({}, status_code=401)

        async with cp_client as client:
            client._client.request = AsyncMock(return_value=fail_response)
            with pytest.raises(CPAuthenticationError, match="Authentication required"):
                await client._request("GET", "/test")
            assert client._client.request.call_count == 1


# ---------------------------------------------------------------------------
# TestCPClientOrders
# ---------------------------------------------------------------------------


class TestCPClientOrders:
    @pytest.mark.asyncio
    async def test_get_orders(self, cp_client: CPClient) -> None:
        auth_response = make_async_mock_response(AUTH_AUTHENTICATED)
        orders_response = make_async_mock_response(SAMPLE_ORDERS)

        async with cp_client as client:
            client._client.request = AsyncMock(side_effect=[auth_response, orders_response])
            orders = await client.get_orders()

            assert len(orders) == 2
            assert isinstance(orders[0], CPOrder)
            assert orders[0].symbol == "AAPL"
            assert orders[0].quantity == Decimal("50")
            assert orders[1].symbol == "MSFT"
            assert orders[1].status == "Filled"

    @pytest.mark.asyncio
    async def test_get_orders_empty(self, cp_client: CPClient) -> None:
        auth_response = make_async_mock_response(AUTH_AUTHENTICATED)
        empty_response = make_async_mock_response({"orders": []})

        async with cp_client as client:
            client._client.request = AsyncMock(side_effect=[auth_response, empty_response])
            orders = await client.get_orders()
            assert orders == []

    @pytest.mark.asyncio
    async def test_get_orders_error(self, cp_client: CPClient) -> None:
        auth_response = make_async_mock_response(AUTH_AUTHENTICATED)
        error_response = make_async_mock_response({}, status_code=500)

        async with cp_client as client:
            client._client.request = AsyncMock(
                side_effect=[
                    auth_response,
                    error_response,
                    error_response,
                    error_response,
                ]
            )
            with pytest.raises(CPClientError):
                await client.get_orders()


# ---------------------------------------------------------------------------
# TestCPClientAccounts
# ---------------------------------------------------------------------------


class TestCPClientAccounts:
    @pytest.mark.asyncio
    async def test_get_accounts(self, cp_client: CPClient) -> None:
        auth_response = make_async_mock_response(AUTH_AUTHENTICATED)
        accounts_response = make_async_mock_response(SAMPLE_ACCOUNTS)

        async with cp_client as client:
            client._client.request = AsyncMock(side_effect=[auth_response, accounts_response])
            accounts = await client.get_accounts()

            assert len(accounts) == 2
            assert "U1234567" in accounts
            assert "U7654321" in accounts


# ---------------------------------------------------------------------------
# TestCPClientBalance
# ---------------------------------------------------------------------------


class TestCPClientBalance:
    @pytest.mark.asyncio
    async def test_get_account_balance(self, cp_client: CPClient) -> None:
        auth_response = make_async_mock_response(AUTH_AUTHENTICATED)
        balance_response = make_async_mock_response(SAMPLE_BALANCE)

        async with cp_client as client:
            client._client.request = AsyncMock(side_effect=[auth_response, balance_response])
            balance = await client.get_account_balance("U1234567")

            assert isinstance(balance, CPAccountBalance)
            assert balance.account_id == "U1234567"
            assert balance.net_liquidation == Decimal("1000000.5")
            assert isinstance(balance.net_liquidation, Decimal)


# ---------------------------------------------------------------------------
# TestCPClientPositions
# ---------------------------------------------------------------------------


class TestCPClientPositions:
    @pytest.mark.asyncio
    async def test_get_positions(self, cp_client: CPClient) -> None:
        auth_response = make_async_mock_response(AUTH_AUTHENTICATED)
        positions_response = make_async_mock_response(SAMPLE_POSITIONS)
        empty_response = make_async_mock_response([])

        async with cp_client as client:
            client._client.request = AsyncMock(
                side_effect=[auth_response, positions_response, empty_response]
            )
            positions = await client.get_positions("U1234567")

            assert len(positions) == 1
            assert isinstance(positions[0], CPPosition)
            assert positions[0].symbol == "AAPL"
            assert positions[0].position == Decimal("100")

    @pytest.mark.asyncio
    async def test_get_positions_empty(self, cp_client: CPClient) -> None:
        auth_response = make_async_mock_response(AUTH_AUTHENTICATED)
        empty_response = make_async_mock_response([])

        async with cp_client as client:
            client._client.request = AsyncMock(side_effect=[auth_response, empty_response])
            positions = await client.get_positions("U1234567")
            assert positions == []

    @pytest.mark.asyncio
    async def test_get_positions_paginated(self, cp_client: CPClient) -> None:
        """Test that get_positions fetches all pages until empty response"""
        auth_response = make_async_mock_response(AUTH_AUTHENTICATED)
        page0_positions = [
            {
                "acctId": "U1234567",
                "conid": 265598,
                "symbol": "AAPL",
                "position": "100",
                "mktPrice": "175.50",
                "mktValue": "17550.00",
                "avgCost": "150.25",
                "unrealizedPnl": "2525.00",
                "currency": "USD",
            }
        ]
        page1_positions = [
            {
                "acctId": "U1234567",
                "conid": 272093,
                "symbol": "MSFT",
                "position": "50",
                "mktPrice": "400.00",
                "mktValue": "20000.00",
                "avgCost": "350.00",
                "unrealizedPnl": "2500.00",
                "currency": "USD",
            }
        ]
        page0_response = make_async_mock_response(page0_positions)
        page1_response = make_async_mock_response(page1_positions)
        empty_response = make_async_mock_response([])

        async with cp_client as client:
            client._client.request = AsyncMock(
                side_effect=[auth_response, page0_response, page1_response, empty_response]
            )
            positions = await client.get_positions("U1234567")

            assert len(positions) == 2
            assert positions[0].symbol == "AAPL"
            assert positions[1].symbol == "MSFT"
            # Verify all 3 pages were requested (page 0, 1, 2)
            assert client._client.request.call_count == 4  # auth + 3 pages


# ---------------------------------------------------------------------------
# TestCPClientSecurity
# ---------------------------------------------------------------------------


class TestCPClientSecurity:
    def test_http_url_rejected(self) -> None:
        with pytest.raises(CPClientError, match="HTTP is not allowed"):
            CPClient(gateway_url="http://localhost:5000")

    def test_https_url_accepted(self) -> None:
        client = CPClient(gateway_url="https://localhost:5000")
        assert client.gateway_url == "https://localhost:5000"

    @pytest.mark.asyncio
    async def test_account_number_masked_in_logs(
        self, cp_client: CPClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        auth_response = make_async_mock_response(AUTH_AUTHENTICATED)
        balance_response = make_async_mock_response(SAMPLE_BALANCE)

        with caplog.at_level(logging.DEBUG, logger="ib_sec_mcp.api.cp_client"):
            async with cp_client as client:
                client._client.request = AsyncMock(side_effect=[auth_response, balance_response])
                await client.get_account_balance("U1234567")

        # Account number should be masked in logs
        log_text = caplog.text
        if "U1234567" in log_text:
            # Full account number should not appear
            pytest.fail("Full account number found in logs without masking")

    @pytest.mark.asyncio
    async def test_client_not_initialized_error(self, cp_client: CPClient) -> None:
        # Do NOT use context manager — client is not initialized
        with pytest.raises(CPClientError, match="Client not initialized"):
            await cp_client._request("GET", "/test")


# ---------------------------------------------------------------------------
# TestCPClientConnection
# ---------------------------------------------------------------------------


class TestCPClientConnection:
    @pytest.mark.asyncio
    async def test_connection_refused(self, cp_client: CPClient) -> None:
        async with cp_client as client:
            client._client.request = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            with pytest.raises(CPConnectionError, match="Cannot connect to gateway"):
                await client._request("GET", "/test")

    @pytest.mark.asyncio
    async def test_ensure_authenticated_preserves_connection_error(
        self, cp_client: CPClient
    ) -> None:
        """Test that CPConnectionError is not masked as CPAuthenticationError"""
        async with cp_client as client:
            client._client.request = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            with pytest.raises(CPConnectionError, match="Cannot connect to gateway"):
                await client._ensure_authenticated()

    @pytest.mark.asyncio
    async def test_context_manager(self, cp_client: CPClient) -> None:
        assert cp_client._client is None
        async with cp_client as client:
            assert client._client is not None
        assert cp_client._client is None
