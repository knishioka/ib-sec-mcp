"""IB Client Portal Gateway API client with session management

Provides async-only access to the IB Client Portal Gateway API for
real-time account data, orders, and positions.

Requires IB Gateway running locally with HTTPS enabled.
"""

import asyncio
import os
from decimal import Decimal

import httpx

from ib_sec_mcp.api.cp_models import (
    CPAccountBalance,
    CPAuthStatus,
    CPOrder,
    CPOrderReply,
    CPOrderRequest,
    CPPosition,
)
from ib_sec_mcp.utils.logger import get_logger, mask_sensitive

logger = get_logger(__name__)


class CPClientError(Exception):
    """Base exception for Client Portal Gateway errors"""

    pass


class CPAuthenticationError(CPClientError):
    """Authentication/session errors"""

    pass


class CPConnectionError(CPClientError):
    """Connection errors (gateway unreachable)"""

    pass


class CPClient:
    """
    Async client for IB Client Portal Gateway API

    Manages session authentication, TLS enforcement, and retry logic
    for accessing real-time account data through the local IB Gateway.

    Example:
        async with CPClient() as client:
            status = await client.check_auth_status()
            if status.authenticated:
                orders = await client.get_orders()

    Environment Variables:
        IB_GATEWAY_URL: Gateway URL (default: https://localhost:5000)
        IB_GATEWAY_VERIFY_SSL: Verify SSL certificates (default: false)
    """

    USER_AGENT = "ib-analytics/0.1.0"

    def __init__(
        self,
        gateway_url: str | None = None,
        verify_ssl: bool | None = None,
        max_retries: int = 3,
        retry_delay: float = 1,
    ):
        """
        Initialize Client Portal Gateway client

        Args:
            gateway_url: Gateway URL (default from IB_GATEWAY_URL env var)
            verify_ssl: Verify SSL certificates (default from env var)
            max_retries: Maximum retry attempts for failed requests
            retry_delay: Base delay between retries in seconds

        Raises:
            CPClientError: If gateway_url uses http:// instead of https://
        """
        self.gateway_url = (
            gateway_url or os.environ.get("IB_GATEWAY_URL", "https://localhost:5000")
        ).rstrip("/")

        # Enforce HTTPS
        if self.gateway_url.startswith("http://"):
            raise CPClientError(
                f"HTTP is not allowed. Use https:// for gateway URL. Got: {self.gateway_url}"
            )

        if verify_ssl is not None:
            self.verify_ssl = verify_ssl
        else:
            env_val = os.environ.get("IB_GATEWAY_VERIFY_SSL", "false")
            self.verify_ssl = env_val.lower() in ("true", "1", "yes")

        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "CPClient":
        """Create httpx async client on context entry"""
        timeout = httpx.Timeout(connect=5.0, read=10.0, write=10.0, pool=10.0)
        self._client = httpx.AsyncClient(
            base_url=self.gateway_url,
            verify=self.verify_ssl,
            timeout=timeout,
            headers={"User-Agent": self.USER_AGENT},
        )
        logger.info(
            "Connected to IB Gateway at %s (ssl_verify=%s)",
            self.gateway_url,
            self.verify_ssl,
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """Close httpx async client on context exit"""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.debug("Disconnected from IB Gateway")

    async def check_auth_status(self) -> CPAuthStatus:
        """
        Check current authentication status

        Returns:
            CPAuthStatus with session information

        Raises:
            CPConnectionError: If gateway is unreachable
            CPClientError: If request fails
        """
        data = await self._request("GET", "/v1/api/iserver/auth/status")
        return CPAuthStatus.model_validate(data)

    async def reauthenticate(self) -> bool:
        """
        Trigger reauthentication with the gateway

        Returns:
            True if reauthentication was successful

        Raises:
            CPAuthenticationError: If reauthentication fails
        """
        try:
            data = await self._request("POST", "/v1/api/iserver/reauthenticate")
            message = data.get("message", "")
            logger.info("Reauthentication response: %s", message)
            return True
        except CPClientError as e:
            raise CPAuthenticationError(f"Reauthentication failed: {e}") from e

    async def get_orders(self) -> list[CPOrder]:
        """
        Get current orders

        Returns:
            List of CPOrder objects

        Raises:
            CPClientError: If request fails
        """
        await self._ensure_authenticated()
        data = await self._request("GET", "/v1/api/iserver/account/orders")

        # IB API returns {"orders": [...]} or just [...]
        orders_data = data.get("orders", []) if isinstance(data, dict) else data
        return [CPOrder.model_validate(o) for o in orders_data]

    async def get_accounts(self) -> list[str]:
        """
        Get list of account IDs

        Returns:
            List of account ID strings

        Raises:
            CPClientError: If request fails
        """
        await self._ensure_authenticated()
        data = await self._request("GET", "/v1/api/portfolio/accounts")

        # IB API returns list of account objects with "id" field
        if isinstance(data, list):
            account_ids = []
            for item in data:
                if isinstance(item, dict):
                    acct_id = item.get("id") or item.get("accountId")
                    if acct_id:
                        account_ids.append(acct_id)
                elif isinstance(item, str):
                    account_ids.append(item)
            return account_ids
        return []

    async def get_account_balance(self, account_id: str) -> CPAccountBalance:
        """
        Get account balance summary

        Args:
            account_id: IB account ID

        Returns:
            CPAccountBalance with balance details

        Raises:
            CPClientError: If request fails
        """
        await self._ensure_authenticated()
        logger.debug(
            "Fetching balance for account %s",
            mask_sensitive(account_id, show_chars=3),
        )
        data = await self._request("GET", f"/v1/api/portfolio/{account_id}/summary")

        # IB API returns nested structure with {field: {amount: X}}
        # Flatten to simple key-value for model validation
        flat: dict[str, object] = {"account_id": account_id}
        for key in (
            "netliquidation",
            "totalcashvalue",
            "buyingpower",
            "grosspositionvalue",
        ):
            if key in data and isinstance(data[key], dict):
                flat[key] = data[key].get("amount", "0")
            elif key in data:
                flat[key] = data[key]

        return CPAccountBalance.model_validate(flat)

    async def get_positions(self, account_id: str) -> list[CPPosition]:
        """
        Get positions for an account

        Args:
            account_id: IB account ID

        Returns:
            List of CPPosition objects

        Raises:
            CPClientError: If request fails
        """
        await self._ensure_authenticated()
        logger.debug(
            "Fetching positions for account %s",
            mask_sensitive(account_id, show_chars=3),
        )
        data = await self._request("GET", f"/v1/api/portfolio/{account_id}/positions/0")

        if isinstance(data, list):
            return [CPPosition.model_validate(p) for p in data]
        return []

    async def place_order(
        self,
        order: CPOrderRequest,
    ) -> list[CPOrderReply]:
        """
        Place an order via Client Portal Gateway

        IB uses a 2-step process: submit order, then confirm replies.

        Args:
            order: Order request details

        Returns:
            List of CPOrderReply with order status

        Raises:
            CPClientError: If order placement fails
        """
        await self._ensure_authenticated()
        account_id = order.account_id
        logger.info(
            "Placing %s order for account %s: %s qty %s",
            order.order_type.value,
            mask_sensitive(account_id, show_chars=3),
            order.side.value,
            order.quantity,
        )

        payload = {"orders": [order.to_api_dict()]}
        data = await self._request(
            "POST",
            f"/v1/api/iserver/account/{account_id}/orders",
            json=payload,
        )

        # IB may return reply questions that need confirmation
        replies = data if isinstance(data, list) else [data]
        result: list[CPOrderReply] = []

        for reply in replies:
            parsed = CPOrderReply.model_validate(reply)
            # If reply has an ID but no order_id, it needs confirmation
            if parsed.reply_id and not parsed.order_id:
                confirmed = await self._confirm_order_reply(parsed.reply_id)
                result.extend(confirmed)
            else:
                result.append(parsed)

        return result

    async def modify_order(
        self,
        account_id: str,
        order_id: int,
        quantity: Decimal | None = None,
        limit_price: Decimal | None = None,
    ) -> list[CPOrderReply]:
        """
        Modify an existing order

        Args:
            account_id: IB account ID
            order_id: Order ID to modify
            quantity: New quantity (optional)
            limit_price: New limit price (optional)

        Returns:
            List of CPOrderReply with modification status

        Raises:
            CPClientError: If modification fails
        """
        await self._ensure_authenticated()
        logger.info(
            "Modifying order %d for account %s",
            order_id,
            mask_sensitive(account_id, show_chars=3),
        )

        payload: dict[str, object] = {}
        if quantity is not None:
            payload["quantity"] = float(quantity)
        if limit_price is not None:
            payload["price"] = float(limit_price)

        data = await self._request(
            "POST",
            f"/v1/api/iserver/account/{account_id}/order/{order_id}",
            json=payload,
        )

        replies = data if isinstance(data, list) else [data]
        result: list[CPOrderReply] = []
        for reply in replies:
            parsed = CPOrderReply.model_validate(reply)
            if parsed.reply_id and not parsed.order_id:
                confirmed = await self._confirm_order_reply(parsed.reply_id)
                result.extend(confirmed)
            else:
                result.append(parsed)
        return result

    async def cancel_order(self, account_id: str, order_id: int) -> dict[str, object]:
        """
        Cancel an existing order

        Args:
            account_id: IB account ID
            order_id: Order ID to cancel

        Returns:
            Cancellation response dict

        Raises:
            CPClientError: If cancellation fails
        """
        await self._ensure_authenticated()
        logger.info(
            "Cancelling order %d for account %s",
            order_id,
            mask_sensitive(account_id, show_chars=3),
        )
        data = await self._request(
            "DELETE",
            f"/v1/api/iserver/account/{account_id}/order/{order_id}",
        )
        return data

    async def _confirm_order_reply(self, reply_id: str) -> list[CPOrderReply]:
        """
        Confirm an order reply (IB 2-step confirmation)

        Args:
            reply_id: Reply ID to confirm

        Returns:
            List of CPOrderReply after confirmation
        """
        logger.debug("Confirming order reply %s", reply_id)
        data = await self._request(
            "POST",
            f"/v1/api/iserver/reply/{reply_id}",
            json={"confirmed": True},
        )
        replies = data if isinstance(data, list) else [data]
        return [CPOrderReply.model_validate(r) for r in replies]

    async def _ensure_authenticated(self) -> None:
        """
        Ensure session is authenticated, reauthenticate if needed

        Raises:
            CPAuthenticationError: If authentication cannot be established
        """
        try:
            status = await self.check_auth_status()
        except CPClientError as e:
            raise CPAuthenticationError(f"Cannot verify auth status: {e}") from e

        if not status.authenticated:
            logger.warning("Session not authenticated, attempting reauth")
            success = await self.reauthenticate()
            if not success:
                raise CPAuthenticationError("Failed to reauthenticate with gateway")

            # Verify authentication after reauth
            status = await self.check_auth_status()
            if not status.authenticated:
                raise CPAuthenticationError(
                    "Session still not authenticated after reauthentication"
                )

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: object,
    ) -> dict:  # type: ignore[type-arg]
        """
        Make HTTP request with retry logic

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (e.g., /v1/api/iserver/auth/status)
            **kwargs: Additional arguments passed to httpx request

        Returns:
            Parsed JSON response as dict

        Raises:
            CPConnectionError: If gateway is unreachable
            CPClientError: If request fails after retries
        """
        if not self._client:
            raise CPClientError(
                "Client not initialized. Use 'async with CPClient()' context manager."
            )

        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = await self._client.request(
                    method,
                    path,
                    **kwargs,  # type: ignore[arg-type]
                )
                response.raise_for_status()
                return response.json()  # type: ignore[no-any-return]

            except httpx.ConnectError as e:
                last_error = e
                logger.warning(
                    "Connection failed (attempt %d/%d): %s",
                    attempt + 1,
                    self.max_retries,
                    e,
                )
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2**attempt)
                    await asyncio.sleep(delay)

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                if status_code == 401:
                    raise CPAuthenticationError(f"Authentication required: {e}") from e
                last_error = e
                logger.warning(
                    "HTTP %d error (attempt %d/%d): %s",
                    status_code,
                    attempt + 1,
                    self.max_retries,
                    e,
                )
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2**attempt)
                    await asyncio.sleep(delay)

            except httpx.HTTPError as e:
                last_error = e
                logger.warning(
                    "HTTP error (attempt %d/%d): %s",
                    attempt + 1,
                    self.max_retries,
                    e,
                )
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2**attempt)
                    await asyncio.sleep(delay)

        # All retries exhausted
        if isinstance(last_error, httpx.ConnectError):
            raise CPConnectionError(
                f"Cannot connect to gateway at {self.gateway_url}: {last_error}"
            ) from last_error

        raise CPClientError(
            f"Request failed after {self.max_retries} attempts: {last_error}"
        ) from last_error
