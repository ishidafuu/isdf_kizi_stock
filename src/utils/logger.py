"""ロギングユーティリティ

全モジュール共通のロギング機能を提供します。
- 日時、エラーレベル（INFO/WARNING/ERROR）、エラー内容、スタックトレースの記録
- ログファイルのローテーション（7日分保持）
- ファイルサイズ制限（10MB超過で新規ファイル作成）
- 重要エラーの管理者通知設定サポート（オプション）
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class Logger:
    """ロギングユーティリティクラス"""

    MAX_LOG_SIZE: int = 10 * 1024 * 1024  # 10MB
    BACKUP_COUNT: int = 7  # 7日分

    @staticmethod
    def setup_logger(name: str, log_file: str) -> logging.Logger:
        """
        ロガーのセットアップ

        Preconditions:
        - name が一意のロガー名
        - log_file が有効なファイルパス

        Postconditions:
        - ログファイルが作成される
        - RotatingFileHandlerが設定される

        Args:
            name: ロガー名
            log_file: ログファイルパス

        Returns:
            logging.Logger: 設定済みロガー
        """
        # ログディレクトリを作成
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # ロガーを取得
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)

        # 既存のハンドラをクリア（重複防止）
        logger.handlers.clear()

        # フォーマッタを作成
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # RotatingFileHandlerを作成
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=Logger.MAX_LOG_SIZE,
            backupCount=Logger.BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        # コンソールハンドラを作成
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        # ハンドラを追加
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    @staticmethod
    def log_exception(
        logger: logging.Logger,
        message: str,
        exc: Exception,
        notify_admin: bool = False,
    ) -> None:
        """
        例外をログに記録

        Preconditions:
        - logger が有効なLoggerインスタンス

        Postconditions:
        - エラーログにメッセージとスタックトレースを記録
        - notify_admin=Trueの場合、管理者通知を送信（オプション）

        Args:
            logger: ロガーインスタンス
            message: エラーメッセージ
            exc: 例外オブジェクト
            notify_admin: 管理者通知フラグ（デフォルト: False）
        """
        # エラーログを記録（スタックトレース付き）
        logger.error(f"{message}: {str(exc)}", exc_info=True)

        # 管理者通知（オプション）
        if notify_admin:
            # TODO: 管理者通知機能を実装（メール等）
            logger.warning(f"管理者通知が必要です: {message}")


def setup_logger(name: str, log_file: str) -> logging.Logger:
    """
    ロガーのセットアップ（モジュールレベル関数）

    Args:
        name: ロガー名
        log_file: ログファイルパス

    Returns:
        logging.Logger: 設定済みロガー
    """
    return Logger.setup_logger(name, log_file)


def log_exception(
    logger: logging.Logger,
    message: str,
    exc: Exception,
    notify_admin: bool = False,
) -> None:
    """
    例外をログに記録（モジュールレベル関数）

    Args:
        logger: ロガーインスタンス
        message: エラーメッセージ
        exc: 例外オブジェクト
        notify_admin: 管理者通知フラグ（デフォルト: False）
    """
    Logger.log_exception(logger, message, exc, notify_admin)
