"""Unit tests for example job handlers."""
import pytest
import asyncio


class TestEchoHandler:
    """Tests for echo handler."""

    @pytest.mark.asyncio
    async def test_echo_handler_returns_payload(self):
        """Test echo handler returns the payload unchanged."""
        from schedora.worker.handlers.echo_handler import echo_handler

        payload = {"message": "hello", "value": 42}
        result = await echo_handler(payload)

        assert result == payload

    @pytest.mark.asyncio
    async def test_echo_handler_with_empty_payload(self):
        """Test echo handler with empty payload."""
        from schedora.worker.handlers.echo_handler import echo_handler

        payload = {}
        result = await echo_handler(payload)

        assert result == payload

    @pytest.mark.asyncio
    async def test_echo_handler_with_nested_data(self):
        """Test echo handler with nested data structures."""
        from schedora.worker.handlers.echo_handler import echo_handler

        payload = {
            "user": {"name": "Alice", "age": 30},
            "items": [1, 2, 3],
            "metadata": {"timestamp": "2025-01-01"},
        }
        result = await echo_handler(payload)

        assert result == payload


class TestSleepHandler:
    """Tests for sleep handler."""

    @pytest.mark.asyncio
    async def test_sleep_handler_completes_successfully(self):
        """Test sleep handler completes successfully."""
        from schedora.worker.handlers.sleep_handler import sleep_handler

        payload = {"duration": 0.01}
        result = await sleep_handler(payload)

        assert result["status"] == "completed"
        assert result["duration"] == 0.01

    @pytest.mark.asyncio
    async def test_sleep_handler_default_duration(self):
        """Test sleep handler uses default duration when not specified."""
        from schedora.worker.handlers.sleep_handler import sleep_handler

        payload = {}
        result = await sleep_handler(payload)

        assert result["status"] == "completed"
        assert result["duration"] == 1  # default

    @pytest.mark.asyncio
    async def test_sleep_handler_respects_duration(self):
        """Test sleep handler actually sleeps for specified duration."""
        from schedora.worker.handlers.sleep_handler import sleep_handler
        import time

        start = time.time()
        payload = {"duration": 0.1}
        await sleep_handler(payload)
        elapsed = time.time() - start

        # Should take at least 0.1 seconds
        assert elapsed >= 0.1


class TestFailHandler:
    """Tests for fail handler."""

    @pytest.mark.asyncio
    async def test_fail_handler_raises_exception(self):
        """Test fail handler always raises exception."""
        from schedora.worker.handlers.fail_handler import fail_handler

        payload = {}

        with pytest.raises(Exception, match="Simulated job failure"):
            await fail_handler(payload)

    @pytest.mark.asyncio
    async def test_fail_handler_with_custom_message(self):
        """Test fail handler uses custom error message."""
        from schedora.worker.handlers.fail_handler import fail_handler

        payload = {"error_message": "Custom error"}

        with pytest.raises(Exception, match="Custom error"):
            await fail_handler(payload)

    @pytest.mark.asyncio
    async def test_fail_handler_with_error_type(self):
        """Test fail handler can raise different error types."""
        from schedora.worker.handlers.fail_handler import fail_handler

        payload = {"error_type": "ValueError"}

        with pytest.raises(ValueError):
            await fail_handler(payload)
