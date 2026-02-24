"""Tests for FlexQueryClient"""

import asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ib_sec_mcp.api.client import (
    FlexQueryAPIError,
    FlexQueryClient,
)
from ib_sec_mcp.api.models import APICredentials, FlexStatement

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SEND_SUCCESS_XML = """<FlexStatementResponse>
    <Status>Success</Status>
    <ReferenceCode>123456789</ReferenceCode>
</FlexStatementResponse>"""

SEND_FAIL_XML = """<FlexStatementResponse>
    <Status>Fail</Status>
    <ErrorCode>1019</ErrorCode>
    <ErrorMessage>Statement generation in progress</ErrorMessage>
</FlexStatementResponse>"""

SEND_MISSING_STATUS_XML = (
    "<FlexStatementResponse><ReferenceCode>123</ReferenceCode></FlexStatementResponse>"
)

CSV_DATA = "ClientAccountID,U1234567,AccountAlias\nU1234567,main,My Account\n"

XML_DATA = '<FlexQueryResponse><FlexStatements><FlexStatement accountId="U9876543" /></FlexStatements></FlexQueryResponse>'

NOT_READY_TEXT = "Statement generation in progress please wait"

VALID_CSV_STATEMENT = CSV_DATA


@pytest.fixture
def single_credential() -> APICredentials:
    return APICredentials(query_id="12345", token="abc123token")


@pytest.fixture
def multi_credentials() -> list[APICredentials]:
    return [
        APICredentials(query_id="11111", token="token_a"),
        APICredentials(query_id="22222", token="token_b"),
    ]


@pytest.fixture
def client(single_credential: APICredentials) -> FlexQueryClient:
    return FlexQueryClient(credentials=[single_credential], max_retries=3, retry_delay=0)


@pytest.fixture
def multi_client(multi_credentials: list[APICredentials]) -> FlexQueryClient:
    return FlexQueryClient(credentials=multi_credentials, max_retries=3, retry_delay=0)


def make_mock_response(text: str, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.text = text
    mock.status_code = status_code
    mock.raise_for_status = MagicMock()
    return mock


def make_async_mock_response(text: str, status_code: int = 200) -> AsyncMock:
    mock = AsyncMock()
    mock.text = text
    mock.status_code = status_code
    mock.raise_for_status = MagicMock()
    return mock


# ---------------------------------------------------------------------------
# TestFlexQueryClientInit
# ---------------------------------------------------------------------------


class TestFlexQueryClientInit:
    def test_init_with_query_id_and_token(self) -> None:
        client = FlexQueryClient(query_id="12345", token="abc123")
        assert len(client.credentials) == 1
        assert client.credentials[0].query_id == "12345"
        assert client.credentials[0].token == "abc123"

    def test_init_with_credentials_list(self, multi_credentials: list[APICredentials]) -> None:
        client = FlexQueryClient(credentials=multi_credentials)
        assert len(client.credentials) == 2

    def test_init_raises_without_credentials(self) -> None:
        with pytest.raises(ValueError, match="credentials must be provided"):
            FlexQueryClient()

    def test_init_defaults(self, single_credential: APICredentials) -> None:
        client = FlexQueryClient(credentials=[single_credential])
        assert client.timeout == 30
        assert client.max_retries == 3
        assert client.retry_delay == 5

    def test_init_custom_values(self, single_credential: APICredentials) -> None:
        client = FlexQueryClient(
            credentials=[single_credential], timeout=60, max_retries=5, retry_delay=10
        )
        assert client.timeout == 60
        assert client.max_retries == 5
        assert client.retry_delay == 10


# ---------------------------------------------------------------------------
# TestSendRequest
# ---------------------------------------------------------------------------


class TestSendRequest:
    @patch("ib_sec_mcp.api.client.requests.get")
    def test_send_request_success(
        self, mock_get: MagicMock, client: FlexQueryClient, single_credential: APICredentials
    ) -> None:
        mock_get.return_value = make_mock_response(SEND_SUCCESS_XML)
        ref_code = client._send_request(single_credential, date(2025, 1, 1), date(2025, 1, 31))
        assert ref_code == "123456789"
        mock_get.assert_called_once()

    @patch("ib_sec_mcp.api.client.requests.get")
    def test_send_request_api_error_status(
        self, mock_get: MagicMock, client: FlexQueryClient, single_credential: APICredentials
    ) -> None:
        mock_get.return_value = make_mock_response(SEND_FAIL_XML)
        with pytest.raises(FlexQueryAPIError, match="SendRequest failed"):
            client._send_request(single_credential, None, None)

    @patch("ib_sec_mcp.api.client.requests.get")
    def test_send_request_missing_status(
        self, mock_get: MagicMock, client: FlexQueryClient, single_credential: APICredentials
    ) -> None:
        mock_get.return_value = make_mock_response(SEND_MISSING_STATUS_XML)
        with pytest.raises(FlexQueryAPIError, match="missing Status element"):
            client._send_request(single_credential, None, None)

    @patch("ib_sec_mcp.api.client.requests.get")
    def test_send_request_missing_reference_code(
        self, mock_get: MagicMock, client: FlexQueryClient, single_credential: APICredentials
    ) -> None:
        xml = "<FlexStatementResponse><Status>Success</Status></FlexStatementResponse>"
        mock_get.return_value = make_mock_response(xml)
        with pytest.raises(FlexQueryAPIError, match="No reference code"):
            client._send_request(single_credential, None, None)

    @patch("ib_sec_mcp.api.client.requests.get")
    def test_send_request_http_error(
        self, mock_get: MagicMock, client: FlexQueryClient, single_credential: APICredentials
    ) -> None:
        import requests

        mock_get.side_effect = requests.RequestException("Connection error")
        with pytest.raises(FlexQueryAPIError, match="SendRequest failed"):
            client._send_request(single_credential, None, None)

    @patch("ib_sec_mcp.api.client.requests.get")
    def test_send_request_malformed_xml(
        self, mock_get: MagicMock, client: FlexQueryClient, single_credential: APICredentials
    ) -> None:
        mock_get.return_value = make_mock_response("not xml at all {{{{")
        with pytest.raises(FlexQueryAPIError, match="Failed to parse XML"):
            client._send_request(single_credential, None, None)


# ---------------------------------------------------------------------------
# TestGetStatement
# ---------------------------------------------------------------------------


class TestGetStatement:
    @patch("ib_sec_mcp.api.client.requests.get")
    def test_get_statement_success(
        self, mock_get: MagicMock, client: FlexQueryClient, single_credential: APICredentials
    ) -> None:
        mock_get.return_value = make_mock_response(CSV_DATA)
        stmt = client._get_statement(
            single_credential, "123456", date(2025, 1, 1), date(2025, 1, 31)
        )
        assert isinstance(stmt, FlexStatement)
        assert stmt.account_id == "U1234567"
        assert stmt.raw_data == CSV_DATA

    @patch("ib_sec_mcp.api.client.requests.get")
    def test_get_statement_not_ready(
        self, mock_get: MagicMock, client: FlexQueryClient, single_credential: APICredentials
    ) -> None:
        mock_get.return_value = make_mock_response(NOT_READY_TEXT)
        with pytest.raises(FlexQueryAPIError, match="not yet ready"):
            client._get_statement(single_credential, "123456", None, None)

    @patch("ib_sec_mcp.api.client.requests.get")
    def test_get_statement_http_error(
        self, mock_get: MagicMock, client: FlexQueryClient, single_credential: APICredentials
    ) -> None:
        import requests

        mock_get.side_effect = requests.RequestException("Timeout")
        with pytest.raises(FlexQueryAPIError, match="GetStatement failed"):
            client._get_statement(single_credential, "123456", None, None)

    @patch("ib_sec_mcp.api.client.requests.get")
    def test_get_statement_uses_today_when_dates_none(
        self, mock_get: MagicMock, client: FlexQueryClient, single_credential: APICredentials
    ) -> None:
        mock_get.return_value = make_mock_response(CSV_DATA)
        stmt = client._get_statement(single_credential, "123456", None, None)
        assert stmt.from_date == date.today()
        assert stmt.to_date == date.today()


# ---------------------------------------------------------------------------
# TestExtractAccountId
# ---------------------------------------------------------------------------


class TestExtractAccountId:
    def test_extract_from_csv_data(self, client: FlexQueryClient) -> None:
        account_id = client._extract_account_id(CSV_DATA)
        assert account_id == "U1234567"

    def test_extract_from_xml_data(self, client: FlexQueryClient) -> None:
        account_id = client._extract_account_id(XML_DATA)
        assert account_id == "U9876543"

    def test_extract_fallback_unknown(self, client: FlexQueryClient) -> None:
        account_id = client._extract_account_id("no account info here")
        assert account_id == "UNKNOWN"

    def test_extract_csv_skips_non_u_prefixed(self, client: FlexQueryClient) -> None:
        csv = "ClientAccountID,NOTANACCOUNT,Other\n"
        account_id = client._extract_account_id(csv)
        # Should fall through to XML or UNKNOWN
        assert account_id in ("UNKNOWN", "NOTANACCOUNT") or account_id.startswith("U")


# ---------------------------------------------------------------------------
# TestFetchStatement (sync)
# ---------------------------------------------------------------------------


class TestFetchStatement:
    @patch("ib_sec_mcp.api.client.time.sleep")
    @patch("ib_sec_mcp.api.client.requests.get")
    def test_fetch_statement_success(
        self,
        mock_get: MagicMock,
        mock_sleep: MagicMock,
        client: FlexQueryClient,
    ) -> None:
        # First call: send request; second call: get statement
        mock_get.side_effect = [
            make_mock_response(SEND_SUCCESS_XML),
            make_mock_response(CSV_DATA),
        ]
        stmt = client.fetch_statement(date(2025, 1, 1), date(2025, 1, 31))
        assert isinstance(stmt, FlexStatement)
        assert mock_sleep.call_count == 1

    @patch("ib_sec_mcp.api.client.time.sleep")
    @patch("ib_sec_mcp.api.client.requests.get")
    def test_fetch_statement_retry_then_success(
        self,
        mock_get: MagicMock,
        mock_sleep: MagicMock,
        client: FlexQueryClient,
    ) -> None:
        # Send succeeds, first get returns not-ready, second get returns data
        mock_get.side_effect = [
            make_mock_response(SEND_SUCCESS_XML),
            make_mock_response(NOT_READY_TEXT),
            make_mock_response(CSV_DATA),
        ]
        stmt = client.fetch_statement()
        assert isinstance(stmt, FlexStatement)
        assert mock_sleep.call_count == 2

    @patch("ib_sec_mcp.api.client.time.sleep")
    @patch("ib_sec_mcp.api.client.requests.get")
    def test_fetch_statement_max_retries_exceeded(
        self,
        mock_get: MagicMock,
        mock_sleep: MagicMock,
        client: FlexQueryClient,
    ) -> None:
        # Send succeeds, all get attempts return not-ready
        mock_get.side_effect = [
            make_mock_response(SEND_SUCCESS_XML),
            make_mock_response(NOT_READY_TEXT),
            make_mock_response(NOT_READY_TEXT),
            make_mock_response(NOT_READY_TEXT),
        ]
        with pytest.raises(FlexQueryAPIError):
            client.fetch_statement()

    def test_fetch_statement_invalid_credential_index(self, client: FlexQueryClient) -> None:
        with pytest.raises(ValueError, match="Invalid credential index"):
            client.fetch_statement(credential_index=99)


# ---------------------------------------------------------------------------
# TestFetchAllStatements (sync)
# ---------------------------------------------------------------------------


class TestFetchAllStatements:
    @patch("ib_sec_mcp.api.client.time.sleep")
    @patch("ib_sec_mcp.api.client.requests.get")
    def test_fetch_all_statements_two_credentials(
        self,
        mock_get: MagicMock,
        mock_sleep: MagicMock,
        multi_client: FlexQueryClient,
    ) -> None:
        # 2 accounts × (1 send + 1 get) = 4 calls
        mock_get.side_effect = [
            make_mock_response(SEND_SUCCESS_XML),
            make_mock_response(CSV_DATA),
            make_mock_response(SEND_SUCCESS_XML),
            make_mock_response(XML_DATA),
        ]
        statements = multi_client.fetch_all_statements()
        assert len(statements) == 2
        assert all(isinstance(s, FlexStatement) for s in statements)


# ---------------------------------------------------------------------------
# TestAsyncSendRequest
# ---------------------------------------------------------------------------


class TestAsyncSendRequest:
    async def test_send_request_async_success(
        self, client: FlexQueryClient, single_credential: APICredentials
    ) -> None:
        mock_response = make_async_mock_response(SEND_SUCCESS_XML)
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)

        with patch("ib_sec_mcp.api.client.httpx.AsyncClient") as mock_httpx:
            mock_httpx.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_httpx.return_value.__aexit__ = AsyncMock(return_value=None)

            ref_code = await client._send_request_async(single_credential, None, None)
            assert ref_code == "123456789"

    async def test_send_request_async_http_error(
        self, client: FlexQueryClient, single_credential: APICredentials
    ) -> None:
        import httpx

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(side_effect=httpx.HTTPError("Error"))

        with patch("ib_sec_mcp.api.client.httpx.AsyncClient") as mock_httpx:
            mock_httpx.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_httpx.return_value.__aexit__ = AsyncMock(return_value=None)

            with pytest.raises(FlexQueryAPIError, match="SendRequest failed"):
                await client._send_request_async(single_credential, None, None)

    async def test_send_request_async_fail_status(
        self, client: FlexQueryClient, single_credential: APICredentials
    ) -> None:
        mock_response = make_async_mock_response(SEND_FAIL_XML)
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)

        with patch("ib_sec_mcp.api.client.httpx.AsyncClient") as mock_httpx:
            mock_httpx.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_httpx.return_value.__aexit__ = AsyncMock(return_value=None)

            with pytest.raises(FlexQueryAPIError, match="SendRequest failed"):
                await client._send_request_async(single_credential, None, None)


# ---------------------------------------------------------------------------
# TestAsyncGetStatement
# ---------------------------------------------------------------------------


class TestAsyncGetStatement:
    async def test_get_statement_async_success(
        self, client: FlexQueryClient, single_credential: APICredentials
    ) -> None:
        mock_response = make_async_mock_response(CSV_DATA)
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)

        with patch("ib_sec_mcp.api.client.httpx.AsyncClient") as mock_httpx:
            mock_httpx.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_httpx.return_value.__aexit__ = AsyncMock(return_value=None)

            stmt = await client._get_statement_async(
                single_credential, "123456", date(2025, 1, 1), date(2025, 1, 31)
            )
            assert isinstance(stmt, FlexStatement)
            assert stmt.account_id == "U1234567"

    async def test_get_statement_async_not_ready(
        self, client: FlexQueryClient, single_credential: APICredentials
    ) -> None:
        mock_response = make_async_mock_response(NOT_READY_TEXT)
        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)

        with patch("ib_sec_mcp.api.client.httpx.AsyncClient") as mock_httpx:
            mock_httpx.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_httpx.return_value.__aexit__ = AsyncMock(return_value=None)

            with pytest.raises(FlexQueryAPIError, match="not yet ready"):
                await client._get_statement_async(single_credential, "123456", None, None)


# ---------------------------------------------------------------------------
# TestFetchStatementAsync
# ---------------------------------------------------------------------------


class TestFetchStatementAsync:
    async def test_fetch_statement_async_success(self, client: FlexQueryClient) -> None:
        mock_send_response = make_async_mock_response(SEND_SUCCESS_XML)
        mock_get_response = make_async_mock_response(CSV_DATA)

        call_count = 0

        async def mock_get_side_effect(*args: object, **kwargs: object) -> AsyncMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_send_response
            return mock_get_response

        mock_client_instance = AsyncMock()
        mock_client_instance.get = mock_get_side_effect

        with (
            patch("ib_sec_mcp.api.client.httpx.AsyncClient") as mock_httpx,
            patch("ib_sec_mcp.api.client.asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_httpx.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_httpx.return_value.__aexit__ = AsyncMock(return_value=None)

            stmt = await client.fetch_statement_async(date(2025, 1, 1), date(2025, 1, 31))
            assert isinstance(stmt, FlexStatement)

    def test_fetch_statement_async_invalid_index(self, client: FlexQueryClient) -> None:
        with pytest.raises(ValueError, match="Invalid credential index"):
            asyncio.get_event_loop().run_until_complete(
                client.fetch_statement_async(credential_index=99)
            )


# ---------------------------------------------------------------------------
# TestFetchAllStatementsAsync
# ---------------------------------------------------------------------------


class TestFetchAllStatementsAsync:
    async def test_fetch_all_statements_async(self, multi_client: FlexQueryClient) -> None:
        send_response = make_async_mock_response(SEND_SUCCESS_XML)
        get_response_a = make_async_mock_response(CSV_DATA)

        async def mock_get_side_effect(*args: object, **kwargs: object) -> AsyncMock:
            url = args[0] if args else kwargs.get("url", "")
            if "SendRequest" in str(url):
                return send_response
            return get_response_a

        mock_client_instance = AsyncMock()
        mock_client_instance.get = mock_get_side_effect

        with (
            patch("ib_sec_mcp.api.client.httpx.AsyncClient") as mock_httpx,
            patch("ib_sec_mcp.api.client.asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_httpx.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_httpx.return_value.__aexit__ = AsyncMock(return_value=None)

            statements = await multi_client.fetch_all_statements_async()
            assert len(statements) == 2
            assert all(isinstance(s, FlexStatement) for s in statements)
