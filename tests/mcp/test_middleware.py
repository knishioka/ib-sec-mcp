"""Tests for IB Analytics MCP middleware.

Covers the error-tracking, retry, and logging middleware. A key acceptance
criterion (Issue #124) is that the middleware does not leak sensitive request
payloads into logs/error responses, which is verified explicitly below.
"""

import logging
from types import SimpleNamespace

import pytest

from ib_sec_mcp.mcp.middleware import (
    IBAnalyticsErrorMiddleware,
    IBAnalyticsLoggingMiddleware,
    IBAnalyticsRetryMiddleware,
)

MIDDLEWARE_LOGGER = "ib_sec_mcp.mcp.middleware"


def make_context(method: str = "tools/call", **extra: object) -> SimpleNamespace:
    """Build a minimal MiddlewareContext-like object."""
    return SimpleNamespace(method=method, source="client", **extra)


def ok_call_next(value: object = "result"):
    async def _call_next(context: object) -> object:
        return value

    return _call_next


def raising_call_next(exc: Exception):
    async def _call_next(context: object) -> object:
        raise exc

    return _call_next


class TestErrorMiddleware:
    async def test_success_passes_through(self) -> None:
        mw = IBAnalyticsErrorMiddleware()
        result = await mw.on_message(make_context(), ok_call_next("ok"))
        assert result == "ok"
        assert mw.get_error_stats() == {}

    async def test_exception_is_tracked_and_reraised(self) -> None:
        mw = IBAnalyticsErrorMiddleware()
        err = ValueError("boom")
        with pytest.raises(ValueError):
            await mw.on_message(make_context(method="tools/call"), raising_call_next(err))

        stats = mw.get_error_stats()
        assert stats["ValueError:tools/call"] == 1

    async def test_repeated_errors_increment_count(self) -> None:
        mw = IBAnalyticsErrorMiddleware()
        for _ in range(3):
            with pytest.raises(KeyError):
                await mw.on_message(make_context(), raising_call_next(KeyError("k")))
        assert mw.get_error_stats()["KeyError:tools/call"] == 3

    async def test_get_error_stats_returns_copy(self) -> None:
        mw = IBAnalyticsErrorMiddleware()
        with pytest.raises(ValueError):
            await mw.on_message(make_context(), raising_call_next(ValueError("x")))
        stats = mw.get_error_stats()
        stats["mutated"] = 999
        assert "mutated" not in mw.get_error_stats()


class TestRetryMiddleware:
    @pytest.fixture(autouse=True)
    def _no_sleep(self, monkeypatch: pytest.MonkeyPatch):
        """Record (and skip) backoff sleeps so tests run instantly."""
        self.delays: list[float] = []

        async def fake_sleep(delay: float) -> None:
            self.delays.append(delay)

        monkeypatch.setattr("ib_sec_mcp.mcp.middleware.asyncio.sleep", fake_sleep)

    async def test_retries_then_succeeds(self) -> None:
        mw = IBAnalyticsRetryMiddleware(max_retries=3, retry_delay=1.0)
        calls = {"n": 0}

        async def flaky(context: object) -> str:
            calls["n"] += 1
            if calls["n"] < 3:
                raise ConnectionError("transient")
            return "recovered"

        result = await mw.on_message(make_context(), flaky)
        assert result == "recovered"
        assert calls["n"] == 3

    async def test_exhausts_retries_and_raises_last(self) -> None:
        mw = IBAnalyticsRetryMiddleware(max_retries=2, retry_delay=1.0)
        calls = {"n": 0}

        async def always_fail(context: object) -> str:
            calls["n"] += 1
            raise TimeoutError("nope")

        with pytest.raises(TimeoutError):
            await mw.on_message(make_context(), always_fail)
        # Initial attempt + 2 retries = 3 calls.
        assert calls["n"] == 3

    async def test_exponential_backoff_delays(self) -> None:
        mw = IBAnalyticsRetryMiddleware(max_retries=3, retry_delay=1.0)

        async def always_fail(context: object) -> str:
            raise ConnectionError("transient")

        with pytest.raises(ConnectionError):
            await mw.on_message(make_context(), always_fail)
        # delay * 2**attempt for attempts 0,1,2 => 1, 2, 4
        assert self.delays == [1.0, 2.0, 4.0]

    async def test_non_retryable_exception_raised_immediately(self) -> None:
        mw = IBAnalyticsRetryMiddleware(max_retries=3, retry_delay=1.0)
        calls = {"n": 0}

        async def value_error(context: object) -> str:
            calls["n"] += 1
            raise ValueError("not retryable")

        with pytest.raises(ValueError):
            await mw.on_message(make_context(), value_error)
        assert calls["n"] == 1
        assert self.delays == []


class TestLoggingMiddleware:
    async def test_logs_request_and_response(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level(logging.DEBUG, logger=MIDDLEWARE_LOGGER)
        mw = IBAnalyticsLoggingMiddleware(log_level=logging.DEBUG)
        result = await mw.on_message(make_context(method="resources/read"), ok_call_next("data"))

        assert result == "data"
        messages = [r.getMessage() for r in caplog.records]
        assert any("→ resources/read" in m for m in messages)
        assert any("← resources/read" in m for m in messages)

    async def test_error_is_logged_and_reraised(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level(logging.DEBUG, logger=MIDDLEWARE_LOGGER)
        mw = IBAnalyticsLoggingMiddleware(log_level=logging.DEBUG)
        with pytest.raises(RuntimeError):
            await mw.on_message(make_context(), raising_call_next(RuntimeError("fail")))

        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert error_records, "expected an ERROR-level log on failure"

    async def test_request_payload_is_not_leaked_to_logs(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Sensitive data attached to the context must never appear in log output."""
        caplog.set_level(logging.DEBUG, logger=MIDDLEWARE_LOGGER)
        secret = "TOKEN_abcdef123456_SECRET"
        context = make_context(method="tools/call", message={"token": secret})

        mw = IBAnalyticsLoggingMiddleware(log_level=logging.DEBUG)
        await mw.on_message(context, ok_call_next("ok"))

        combined = "\n".join(r.getMessage() for r in caplog.records)
        assert secret not in combined

    async def test_error_message_payload_not_leaked_by_logging_middleware(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """On error, the logging middleware records only method + error type, not payload."""
        caplog.set_level(logging.DEBUG, logger=MIDDLEWARE_LOGGER)
        secret = "PASSWORD_supersecret"
        context = make_context(method="tools/call", message={"password": secret})

        mw = IBAnalyticsLoggingMiddleware(log_level=logging.DEBUG)
        with pytest.raises(RuntimeError):
            await mw.on_message(context, raising_call_next(RuntimeError("internal")))

        combined = "\n".join(r.getMessage() for r in caplog.records)
        assert secret not in combined
