"""Fixtures and skip conditions for Client Portal API integration tests

These tests require:
- IB Client Portal Gateway running locally (https://localhost:5000)
- Authenticated session (browser login completed)
- Paper Trading account
"""

import asyncio
import contextlib
import os
from collections.abc import AsyncGenerator

import pytest

from ib_sec_mcp.api.cp_client import CPClient, CPConnectionError


def gateway_available() -> bool:
    """Check if IB Client Portal Gateway is running and authenticated."""
    try:
        loop = asyncio.new_event_loop()
        try:

            async def _check() -> bool:
                async with CPClient(max_retries=1) as client:
                    status = await client.check_auth_status()
                    return status.authenticated

            return loop.run_until_complete(_check())
        finally:
            loop.close()
    except (CPConnectionError, Exception):
        return False


requires_gateway = pytest.mark.skipif(
    not gateway_available(),
    reason="IB Client Portal Gateway not running or not authenticated",
)

# Apply markers to all tests in this directory
pytestmark = [
    requires_gateway,
    pytest.mark.integration,
    pytest.mark.paper_trading,
    pytest.mark.manual,
]


@pytest.fixture()
async def cp_client() -> AsyncGenerator[CPClient, None]:
    """Provide an authenticated CPClient connected to the Paper Trading Gateway."""
    async with CPClient() as client:
        yield client


@pytest.fixture()
async def paper_account_id(cp_client: CPClient) -> str:
    """Get the Paper Trading account ID.

    Uses IB_PAPER_ACCOUNT_ID env var if set, otherwise fetches from Gateway.
    """
    env_id = os.environ.get("IB_PAPER_ACCOUNT_ID")
    if env_id:
        return env_id

    accounts = await cp_client.get_accounts()
    assert len(accounts) > 0, "No accounts found on Gateway"
    return accounts[0]


@pytest.fixture()
async def cleanup_orders(
    cp_client: CPClient, paper_account_id: str
) -> AsyncGenerator[list[int], None]:
    """Track and clean up test orders after each test.

    Yields a list that tests can append order IDs to.
    All tracked orders are cancelled in cleanup.
    """
    order_ids: list[int] = []
    yield order_ids

    for order_id in order_ids:
        with contextlib.suppress(Exception):
            await cp_client.cancel_order(paper_account_id, order_id)
