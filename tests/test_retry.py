"""ネットワークリトライ処理のテスト

ネットワークエラー発生時の自動再試行機能をテストします。
- リトライ回数のカウント
- リトライ結果のログ記録
- 最大リトライ回数の遵守
"""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from src.utils.retry import retry_on_network_error


class TestRetryOnNetworkError:
    """ネットワークエラーリトライ機能のテスト"""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """初回成功時はリトライしない"""
        # Arrange
        mock_func = AsyncMock(return_value="success")

        # Act
        result = await retry_on_network_error(mock_func, max_retries=3)

        # Assert
        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_aiohttp_client_error(self):
        """aiohttp.ClientError発生時にリトライする"""
        # Arrange
        mock_func = AsyncMock()
        mock_func.side_effect = [
            aiohttp.ClientError("Network error"),
            aiohttp.ClientError("Network error"),
            "success"
        ]

        # Act
        result = await retry_on_network_error(mock_func, max_retries=3, delay=0.01)

        # Assert
        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_on_timeout_error(self):
        """asyncio.TimeoutError発生時にリトライする"""
        # Arrange
        mock_func = AsyncMock()
        mock_func.side_effect = [
            asyncio.TimeoutError(),
            "success"
        ]

        # Act
        result = await retry_on_network_error(mock_func, max_retries=3, delay=0.01)

        # Assert
        assert result == "success"
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """最大リトライ回数を超えたら例外を再発生"""
        # Arrange
        mock_func = AsyncMock()
        mock_func.side_effect = aiohttp.ClientError("Network error")

        # Act & Assert
        with pytest.raises(aiohttp.ClientError):
            await retry_on_network_error(mock_func, max_retries=3, delay=0.01)

        # 3回リトライ + 初回 = 4回呼び出し
        assert mock_func.call_count == 4

    @pytest.mark.asyncio
    async def test_non_network_error_not_retried(self):
        """ネットワークエラー以外の例外はリトライしない"""
        # Arrange
        mock_func = AsyncMock()
        mock_func.side_effect = ValueError("Not a network error")

        # Act & Assert
        with pytest.raises(ValueError):
            await retry_on_network_error(mock_func, max_retries=3)

        # リトライせず1回のみ
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_logging(self, caplog):
        """リトライ時にログが記録される"""
        # Arrange
        mock_func = AsyncMock()
        mock_func.side_effect = [
            aiohttp.ClientError("Network error"),
            "success"
        ]

        logger = logging.getLogger("test_retry")

        # Act
        with caplog.at_level(logging.WARNING):
            await retry_on_network_error(
                mock_func,
                max_retries=3,
                delay=0.01,
                logger=logger
            )

        # Assert
        # リトライのログが記録されているか確認
        assert any("リトライ" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_retry_with_connection_error(self):
        """ConnectionError発生時にリトライする"""
        # Arrange
        mock_func = AsyncMock()
        mock_func.side_effect = [
            ConnectionError("Connection refused"),
            "success"
        ]

        # Act
        result = await retry_on_network_error(mock_func, max_retries=3, delay=0.01)

        # Assert
        assert result == "success"
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_count_in_logs(self, caplog):
        """リトライ回数がログに記録される"""
        # Arrange
        mock_func = AsyncMock()
        mock_func.side_effect = [
            aiohttp.ClientError("Network error"),
            aiohttp.ClientError("Network error"),
            "success"
        ]

        logger = logging.getLogger("test_retry_count")

        # Act
        with caplog.at_level(logging.WARNING):
            await retry_on_network_error(
                mock_func,
                max_retries=3,
                delay=0.01,
                logger=logger
            )

        # Assert
        # "1/3", "2/3" のような形式でリトライ回数が記録されているか
        retry_logs = [r.message for r in caplog.records if "リトライ" in r.message]
        assert len(retry_logs) == 2  # 2回リトライした
        assert "1/3" in retry_logs[0]
        assert "2/3" in retry_logs[1]
