"""ネットワークリトライユーティリティ

ネットワークエラー発生時の自動再試行機能を提供します。
- 設定可能なリトライ回数と遅延時間
- ネットワーク関連エラーの自動検出
- リトライ回数と結果のログ記録
"""

import asyncio
import logging
from typing import Any, Callable, Optional, TypeVar

import aiohttp

from config.settings import Settings

T = TypeVar('T')


async def retry_on_network_error(
    func: Callable[..., Any],
    max_retries: Optional[int] = None,
    delay: Optional[float] = None,
    logger: Optional[logging.Logger] = None,
    *args,
    **kwargs
) -> Any:
    """
    ネットワークエラー発生時に自動リトライを行う

    Requirement 9.4: ネットワークエラーが発生した時、自動的に再試行を行い、
    再試行回数をログに記録する

    Args:
        func: 実行する非同期関数
        max_retries: 最大リトライ回数（デフォルト: Settings.NETWORK_RETRY_COUNT）
        delay: リトライ間の待機時間（秒）（デフォルト: Settings.NETWORK_RETRY_DELAY）
        logger: ロガーインスタンス（オプション）
        *args: funcに渡す位置引数
        **kwargs: funcに渡すキーワード引数

    Returns:
        Any: func の実行結果

    Raises:
        Exception: 最大リトライ回数を超えた場合、または
                   ネットワークエラー以外の例外が発生した場合

    Examples:
        >>> async def fetch_data():
        ...     return await http_client.get("https://example.com")
        >>> result = await retry_on_network_error(fetch_data, max_retries=3)
    """
    if max_retries is None:
        max_retries = getattr(Settings, 'NETWORK_RETRY_COUNT', 3)

    if delay is None:
        delay = getattr(Settings, 'NETWORK_RETRY_DELAY', 1.0)

    if logger is None:
        logger = logging.getLogger(__name__)

    # ネットワークエラーとして扱う例外のタプル
    network_exceptions = (
        aiohttp.ClientError,
        asyncio.TimeoutError,
        ConnectionError,
        OSError,  # DNS解決失敗など
    )

    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            # 関数を実行
            result = await func(*args, **kwargs)

            # 成功時: リトライ情報をログに記録
            if attempt > 0:
                logger.info(
                    f"リトライ成功: {attempt}回目の試行で成功しました"
                )

            return result

        except network_exceptions as e:
            last_exception = e

            # 最後の試行でなければリトライ
            if attempt < max_retries:
                logger.warning(
                    f"ネットワークエラー発生、リトライします "
                    f"({attempt + 1}/{max_retries}): {type(e).__name__}: {str(e)}"
                )

                # 待機してからリトライ
                await asyncio.sleep(delay)
            else:
                # 最大リトライ回数に到達
                logger.error(
                    f"ネットワークエラー: 最大リトライ回数({max_retries})に到達しました: "
                    f"{type(e).__name__}: {str(e)}"
                )
                raise

        except Exception as e:
            # ネットワークエラー以外の例外はリトライしない
            logger.error(
                f"ネットワークエラー以外の例外が発生: {type(e).__name__}: {str(e)}"
            )
            raise

    # このコードには到達しないが、型チェッカーのために必要
    if last_exception:
        raise last_exception


class RetryConfig:
    """リトライ設定クラス

    リトライ処理の設定をカプセル化します。
    """

    def __init__(
        self,
        max_retries: int = 3,
        delay: float = 1.0,
        logger: Optional[logging.Logger] = None
    ):
        """
        RetryConfigの初期化

        Args:
            max_retries: 最大リトライ回数
            delay: リトライ間の待機時間（秒）
            logger: ロガーインスタンス
        """
        self.max_retries = max_retries
        self.delay = delay
        self.logger = logger or logging.getLogger(__name__)


async def retry_async(
    func: Callable[..., Any],
    config: Optional[RetryConfig] = None,
    *args,
    **kwargs
) -> Any:
    """
    リトライ設定を使用して非同期関数を実行

    Args:
        func: 実行する非同期関数
        config: リトライ設定（オプション）
        *args: funcに渡す位置引数
        **kwargs: funcに渡すキーワード引数

    Returns:
        Any: func の実行結果
    """
    if config is None:
        config = RetryConfig()

    return await retry_on_network_error(
        func,
        max_retries=config.max_retries,
        delay=config.delay,
        logger=config.logger,
        *args,
        **kwargs
    )
