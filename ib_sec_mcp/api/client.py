"""Interactive Brokers Flex Query API client with multi-account support"""

import asyncio
import time
from datetime import date, datetime

import defusedxml.ElementTree as ET
import httpx
import requests
from pydantic import ValidationError

from ib_sec_mcp.api.models import APICredentials, FlexStatement


class FlexQueryError(Exception):
    """Base exception for Flex Query errors"""

    pass


class FlexQueryAPIError(FlexQueryError):
    """API request/response errors"""

    pass


class FlexQueryValidationError(FlexQueryError):
    """Data validation errors"""

    pass


class FlexQueryClient:
    """
    Interactive Brokers Flex Query API client (Version 3)

    Supports both single and multi-account data fetching with async capabilities.

    Example:
        # Single account
        client = FlexQueryClient(query_id="123", token="abc")
        data = client.fetch_statement(start_date=date(2025, 1, 1))

        # Multiple accounts
        client = FlexQueryClient(credentials=[cred1, cred2])
        results = await client.fetch_all_statements_async(start_date=date(2025, 1, 1))
    """

    BASE_URL_SEND = (
        "https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService/SendRequest"
    )
    BASE_URL_GET = (
        "https://gdcdyn.interactivebrokers.com/AccountManagement/FlexWebService/GetStatement"
    )
    API_VERSION = "3"
    USER_AGENT = "ib-analytics/0.1.0"

    def __init__(
        self,
        query_id: str | None = None,
        token: str | None = None,
        credentials: list[APICredentials] | None = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: int = 5,
    ):
        """
        Initialize Flex Query client

        Args:
            query_id: Single account query ID
            token: Single account token
            credentials: List of credentials for multi-account support
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries in seconds
        """
        if credentials:
            self.credentials = credentials
        elif query_id and token:
            self.credentials = [APICredentials(query_id=query_id, token=token)]
        else:
            raise ValueError("Either (query_id, token) or credentials must be provided")

        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def fetch_statement(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        credential_index: int = 0,
    ) -> FlexStatement:
        """
        Fetch statement for a single account (synchronous)

        Args:
            start_date: Statement start date (uses query default if None)
            end_date: Statement end date (uses query default if None)
            credential_index: Index of credentials to use (for multi-account)

        Returns:
            FlexStatement with raw data

        Raises:
            FlexQueryAPIError: If API request fails
            FlexQueryValidationError: If response validation fails
        """
        if credential_index >= len(self.credentials):
            raise ValueError(f"Invalid credential index: {credential_index}")

        cred = self.credentials[credential_index]

        # Step 1: Send request
        reference_code = self._send_request(cred, start_date, end_date)

        # Step 2: Poll for statement (with retries)
        for attempt in range(self.max_retries):
            time.sleep(self.retry_delay)

            try:
                statement = self._get_statement(cred, reference_code, start_date, end_date)
                return statement
            except FlexQueryAPIError as e:
                if "not yet ready" in str(e).lower() and attempt < self.max_retries - 1:
                    continue
                raise

        raise FlexQueryAPIError(f"Statement not ready after {self.max_retries} attempts")

    def _send_request(
        self,
        cred: APICredentials,
        start_date: date | None,
        end_date: date | None,
    ) -> str:
        """Send request to generate statement"""
        params: dict[str, str] = {
            "t": cred.token,
            "q": cred.query_id,
            "v": self.API_VERSION,
        }

        headers = {"User-Agent": self.USER_AGENT}

        try:
            response = requests.get(
                self.BASE_URL_SEND,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            raise FlexQueryAPIError(f"SendRequest failed: {e}") from e

        # Parse XML response
        try:
            root = ET.fromstring(response.text)
            status_elem = root.find(".//Status")
            reference_code_elem = root.find(".//ReferenceCode")
            error_code_elem = root.find(".//ErrorCode")
            error_msg_elem = root.find(".//ErrorMessage")

            if status_elem is None:
                raise FlexQueryAPIError("Invalid response: missing Status element")

            status = status_elem.text
            reference_code = reference_code_elem.text if reference_code_elem is not None else None
            error_code = error_code_elem.text if error_code_elem is not None else None
            error_msg = error_msg_elem.text if error_msg_elem is not None else None

            if status != "Success":
                raise FlexQueryAPIError(f"SendRequest failed: {error_code} - {error_msg}")

            if not reference_code:
                raise FlexQueryAPIError("No reference code in response")

            return str(reference_code)

        except ET.ParseError as e:
            raise FlexQueryAPIError(f"Failed to parse XML response: {e}") from e

    def _get_statement(
        self,
        cred: APICredentials,
        reference_code: str,
        start_date: date | None,
        end_date: date | None,
    ) -> FlexStatement:
        """Get statement using reference code"""
        params: dict[str, str] = {
            "t": cred.token,
            "q": reference_code,
            "v": self.API_VERSION,
        }

        headers = {"User-Agent": self.USER_AGENT}

        try:
            response = requests.get(
                self.BASE_URL_GET,
                params=params,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            raise FlexQueryAPIError(f"GetStatement failed: {e}") from e

        # Check if statement is ready
        if "Statement generation in progress" in response.text:
            raise FlexQueryAPIError("Statement not yet ready")

        # Parse response to extract metadata
        account_id = self._extract_account_id(response.text)
        generated_time = datetime.now()

        # Use provided dates or extract from response
        from_date = start_date or date.today()
        to_date = end_date or date.today()

        try:
            return FlexStatement(
                query_id=cred.query_id,
                account_id=account_id,
                from_date=from_date,
                to_date=to_date,
                when_generated=generated_time,
                raw_data=response.text,
            )
        except ValidationError as e:
            raise FlexQueryValidationError(f"Statement validation failed: {e}") from e

    def _extract_account_id(self, data: str) -> str:
        """Extract account ID from CSV/XML data"""
        # Try CSV format first
        lines = data.strip().split("\n")
        for line in lines:
            if "ClientAccountID" in line and "," in line:
                # Next line should have the account ID
                parts = line.split(",")
                if len(parts) > 0:
                    # Look for account ID pattern (U followed by digits)
                    for part in parts:
                        if part.startswith("U") and part[1:].isdigit():
                            return part

        # Try XML format
        try:
            root = ET.fromstring(data)
            account_elem = root.find(".//*[@accountId]")
            if account_elem is not None:
                account_id = account_elem.get("accountId")
                if account_id:
                    return str(account_id)
        except ET.ParseError:
            pass

        # Fallback: return query ID
        return "UNKNOWN"

    async def fetch_statement_async(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        credential_index: int = 0,
    ) -> FlexStatement:
        """Async version of fetch_statement"""
        if credential_index >= len(self.credentials):
            raise ValueError(f"Invalid credential index: {credential_index}")

        cred = self.credentials[credential_index]

        # Step 1: Send request
        reference_code = await self._send_request_async(cred, start_date, end_date)

        # Step 2: Poll for statement
        for attempt in range(self.max_retries):
            await asyncio.sleep(self.retry_delay)

            try:
                statement = await self._get_statement_async(
                    cred, reference_code, start_date, end_date
                )
                return statement
            except FlexQueryAPIError as e:
                if "not yet ready" in str(e).lower() and attempt < self.max_retries - 1:
                    continue
                raise

        raise FlexQueryAPIError(f"Statement not ready after {self.max_retries} attempts")

    async def _send_request_async(
        self,
        cred: APICredentials,
        start_date: date | None,
        end_date: date | None,
    ) -> str:
        """Async version of _send_request"""
        params: dict[str, str] = {
            "t": cred.token,
            "q": cred.query_id,
            "v": self.API_VERSION,
        }

        headers = {"User-Agent": self.USER_AGENT}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(self.BASE_URL_SEND, params=params, headers=headers)
                response.raise_for_status()
            except httpx.HTTPError as e:
                raise FlexQueryAPIError(f"SendRequest failed: {e}") from e

            # Parse XML (same logic as sync version)
            try:
                root = ET.fromstring(response.text)
                status_elem = root.find(".//Status")
                reference_code_elem = root.find(".//ReferenceCode")
                error_code_elem = root.find(".//ErrorCode")
                error_msg_elem = root.find(".//ErrorMessage")

                if status_elem is None:
                    raise FlexQueryAPIError("Invalid response: missing Status element")

                status = status_elem.text
                reference_code = (
                    reference_code_elem.text if reference_code_elem is not None else None
                )
                error_code = error_code_elem.text if error_code_elem is not None else None
                error_msg = error_msg_elem.text if error_msg_elem is not None else None

                if status != "Success":
                    raise FlexQueryAPIError(f"SendRequest failed: {error_code} - {error_msg}")

                if not reference_code:
                    raise FlexQueryAPIError("No reference code in response")

                return str(reference_code)

            except ET.ParseError as e:
                raise FlexQueryAPIError(f"Failed to parse XML response: {e}") from e

    async def _get_statement_async(
        self,
        cred: APICredentials,
        reference_code: str,
        start_date: date | None,
        end_date: date | None,
    ) -> FlexStatement:
        """Async version of _get_statement"""
        params: dict[str, str] = {
            "t": cred.token,
            "q": reference_code,
            "v": self.API_VERSION,
        }

        headers = {"User-Agent": self.USER_AGENT}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(self.BASE_URL_GET, params=params, headers=headers)
                response.raise_for_status()
            except httpx.HTTPError as e:
                raise FlexQueryAPIError(f"GetStatement failed: {e}") from e

            if "Statement generation in progress" in response.text:
                raise FlexQueryAPIError("Statement not yet ready")

            account_id = self._extract_account_id(response.text)
            generated_time = datetime.now()
            from_date = start_date or date.today()
            to_date = end_date or date.today()

            try:
                return FlexStatement(
                    query_id=cred.query_id,
                    account_id=account_id,
                    from_date=from_date,
                    to_date=to_date,
                    when_generated=generated_time,
                    raw_data=response.text,
                )
            except ValidationError as e:
                raise FlexQueryValidationError(f"Statement validation failed: {e}") from e

    async def fetch_all_statements_async(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[FlexStatement]:
        """
        Fetch statements for all configured accounts in parallel

        Args:
            start_date: Statement start date
            end_date: Statement end date

        Returns:
            List of FlexStatements for all accounts
        """
        tasks = [
            self.fetch_statement_async(start_date, end_date, i)
            for i in range(len(self.credentials))
        ]
        return await asyncio.gather(*tasks)

    def fetch_all_statements(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[FlexStatement]:
        """
        Fetch statements for all configured accounts (synchronous)

        Args:
            start_date: Statement start date
            end_date: Statement end date

        Returns:
            List of FlexStatements for all accounts
        """
        return [self.fetch_statement(start_date, end_date, i) for i in range(len(self.credentials))]
