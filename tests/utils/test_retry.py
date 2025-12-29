import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.exc import OperationalError
from app.utils.retry import retry_on_connection_error, with_retry


class TestRetry:
    """Test retry utilities"""

    @pytest.mark.asyncio
    async def test_successful_call_no_retry(self):
        """Test successful call doesn't retry"""
        mock_func = AsyncMock(return_value="success")

        result = await retry_on_connection_error(mock_func)

        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_function_call_with_args(self):
        """Test passing arguments to function"""
        mock_func = AsyncMock(return_value="success")

        result = await retry_on_connection_error(mock_func, "arg1", "arg2", kwarg1="value1")

        assert result == "success"
        mock_func.assert_called_once_with("arg1", "arg2", kwarg1="value1")

    @pytest.mark.asyncio
    async def test_retry_on_operational_error(self):
        """Test retrying on OperationalError"""
        mock_func = AsyncMock(side_effect=[
            OperationalError("connection failed", None, None),
            "success"
        ])

        result = await retry_on_connection_error(mock_func, max_retries=3, initial_delay=0.01)

        assert result == "success"
        assert mock_func.call_count == 2  # First attempt + 1 retry

    @pytest.mark.asyncio
    async def test_retry_with_multiple_failures(self):
        """Test multiple retries"""
        mock_func = AsyncMock(side_effect=[
            OperationalError("connection failed", None, None),
            OperationalError("connection failed again", None, None),
            "success"
        ])

        result = await retry_on_connection_error(mock_func, max_retries=3, initial_delay=0.01)

        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhaustion(self):
        """Test that function raises after max retries"""
        mock_func = AsyncMock(side_effect=OperationalError("connection failed", None, None))

        with pytest.raises(OperationalError):
            await retry_on_connection_error(mock_func, max_retries=2, initial_delay=0.01)

        assert mock_func.call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_non_retryable_error_raises_immediately(self):
        """Test that non-connection errors don't retry"""
        mock_func = AsyncMock(side_effect=ValueError("Some other error"))

        with pytest.raises(ValueError):
            await retry_on_connection_error(mock_func, max_retries=3, initial_delay=0.01)

        assert mock_func.call_count == 1  # No retries for non-connection error

    @pytest.mark.asyncio
    async def test_retry_with_custom_delay(self):
        """Test retry with custom initial delay"""
        mock_func = AsyncMock(side_effect=[
            OperationalError("connection failed", None, None),
            "success"
        ])

        start = asyncio.get_event_loop().time()
        result = await retry_on_connection_error(mock_func, max_retries=1, initial_delay=0.1)
        elapsed = asyncio.get_event_loop().time() - start

        assert result == "success"
        assert elapsed >= 0.09  # Should have waited at least initial_delay (allowing for small variance)

    @pytest.mark.asyncio
    async def test_retry_with_backoff(self):
        """Test exponential backoff"""
        mock_func = AsyncMock(side_effect=[
            OperationalError("connection failed", None, None),
            OperationalError("connection failed again", None, None),
            "success"
        ])

        await retry_on_connection_error(
            mock_func,
            max_retries=2,
            initial_delay=0.01,
            backoff_factor=2.0
        )

        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_with_connection_closed_message(self):
        """Test retry on connection closed message"""
        mock_func = AsyncMock(side_effect=[
            RuntimeError("connection is closed"),
            "success"
        ])

        result = await retry_on_connection_error(mock_func, max_retries=2, initial_delay=0.01)

        assert result == "success"
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_with_connection_refused_message(self):
        """Test retry on connection refused message"""
        mock_func = AsyncMock(side_effect=[
            RuntimeError("Connection refused"),
            "success"
        ])

        result = await retry_on_connection_error(mock_func, max_retries=2, initial_delay=0.01)

        assert result == "success"
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_with_retry_wrapper(self):
        """Test with_retry wrapper function"""
        mock_func = AsyncMock(side_effect=[
            OperationalError("connection failed", None, None),
            "success"
        ])

        result = await with_retry(mock_func, max_retries=2, initial_delay=0.01)

        assert result == "success"
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_with_retry_with_args(self):
        """Test with_retry with arguments"""
        mock_func = AsyncMock(side_effect=[
            OperationalError("connection failed", None, None),
            "result"
        ])

        result = await with_retry(
            mock_func,
            "arg1",
            "arg2",
            kwarg="value",
            max_retries=1,
            initial_delay=0.01
        )

        assert result == "result"
        mock_func.assert_called_with("arg1", "arg2", kwarg="value")

    @pytest.mark.asyncio
    async def test_zero_max_retries(self):
        """Test with zero max_retries (only initial attempt)"""
        mock_func = AsyncMock(side_effect=OperationalError("connection failed", None, None))

        with pytest.raises(OperationalError):
            await retry_on_connection_error(mock_func, max_retries=0, initial_delay=0.01)

        assert mock_func.call_count == 1  # Only initial attempt

    @pytest.mark.asyncio
    async def test_return_value_preservation(self):
        """Test that return values are preserved"""
        test_data = {"key": "value", "number": 123}
        mock_func = AsyncMock(return_value=test_data)

        result = await retry_on_connection_error(mock_func)

        assert result == test_data
        assert result["key"] == "value"
