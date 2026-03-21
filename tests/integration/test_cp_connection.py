"""Integration tests for Client Portal Gateway connection and authentication"""

import pytest

from ib_sec_mcp.api.cp_client import CPClient, CPClientError, CPConnectionError


class TestGatewayConnection:
    """Test Gateway connectivity and session management"""

    async def test_check_auth_status(self, cp_client: CPClient) -> None:
        """Verify Gateway returns valid auth status."""
        status = await cp_client.check_auth_status()
        assert status.authenticated is True
        assert status.connected is True

    async def test_auth_status_fields(self, cp_client: CPClient) -> None:
        """Verify auth status contains expected fields."""
        status = await cp_client.check_auth_status()
        assert isinstance(status.authenticated, bool)
        assert isinstance(status.connected, bool)
        assert isinstance(status.competing, bool)

    async def test_reauthenticate(self, cp_client: CPClient) -> None:
        """Verify reauthentication succeeds on an active session."""
        result = await cp_client.reauthenticate()
        assert result is True

    async def test_get_accounts(self, cp_client: CPClient) -> None:
        """Verify Gateway returns at least one account."""
        accounts = await cp_client.get_accounts()
        assert len(accounts) > 0
        # Paper Trading account IDs typically start with 'D' or 'U'
        for account_id in accounts:
            assert isinstance(account_id, str)
            assert len(account_id) > 0


class TestGatewayNotRunning:
    """Test behavior when Gateway is not available"""

    @pytest.mark.skip(reason="Only run manually to verify graceful handling")
    async def test_connection_error_on_wrong_port(self) -> None:
        """Verify CPConnectionError when Gateway is unreachable."""
        async with CPClient(
            gateway_url="https://localhost:59999", max_retries=1, retry_delay=0.1
        ) as client:
            with pytest.raises(CPConnectionError):
                await client.check_auth_status()

    async def test_https_enforcement(self) -> None:
        """Verify HTTP URLs are rejected."""
        with pytest.raises(CPClientError, match="HTTP is not allowed"):
            CPClient(gateway_url="http://localhost:5000")
