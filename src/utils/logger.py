"""ロギングユーティリティ

全モジュール共通のロギング機能を提供します。
- 日時、エラーレベル（INFO/WARNING/ERROR）、エラー内容、スタックトレースの記録
- ログファイルのローテーション（7日分保持）
- ファイルサイズ制限（10MB超過で新規ファイル作成）
- 重要エラーの管理者通知設定サポート（オプション）
"""

import logging
import smtplib
import sys
from datetime import datetime
from email.mime.text import MIMEText
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from config.settings import Settings


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
            logger.warning(f"管理者通知が必要です: {message}")
            send_admin_notification(
                subject=f"[Article Stock Bot] {message}",
                message=f"エラーが発生しました:\n\n{message}\n\n例外: {str(exc)}\n\n時刻: {datetime.now().isoformat()}"
            )


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


def send_admin_notification(subject: str, message: str) -> None:
    """
    管理者にメール通知を送信（Task 9.3）

    重要なエラー（GitHub push失敗、Gemini API継続失敗）を管理者に通知します。
    環境変数ADMIN_NOTIFICATION_ENABLEDがtrueの場合のみ送信されます。

    Preconditions:
    - 環境変数が適切に設定されている（ADMIN_EMAIL_FROM, ADMIN_EMAIL_TO, SMTP_HOST等）

    Postconditions:
    - ADMIN_NOTIFICATION_ENABLED=trueの場合、メールが送信される
    - ADMIN_NOTIFICATION_ENABLED=falseの場合、何もしない
    - SMTP送信エラーが発生してもクラッシュしない

    Args:
        subject: メールの件名
        message: メールの本文

    Raises:
        なし（エラーが発生してもキャッチされる）
    """
    # 管理者通知が無効な場合は何もしない
    if not Settings.ADMIN_NOTIFICATION_ENABLED:
        return

    # 必須設定のチェック
    if not Settings.ADMIN_EMAIL_FROM or not Settings.ADMIN_EMAIL_TO:
        logging.warning("管理者通知が有効ですが、メールアドレスが設定されていません")
        return

    try:
        # メールメッセージを作成
        msg = MIMEText(message, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = Settings.ADMIN_EMAIL_FROM
        msg['To'] = Settings.ADMIN_EMAIL_TO
        msg['Date'] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")

        # SMTPサーバーに接続して送信
        with smtplib.SMTP(Settings.SMTP_HOST, Settings.SMTP_PORT) as server:
            # SMTP認証が必要な場合
            if Settings.SMTP_USER and Settings.SMTP_PASSWORD:
                server.starttls()
                server.login(Settings.SMTP_USER, Settings.SMTP_PASSWORD)

            # メール送信
            server.sendmail(
                Settings.ADMIN_EMAIL_FROM,
                [Settings.ADMIN_EMAIL_TO],
                msg.as_string()
            )

        logging.info(f"管理者通知メールを送信しました: {subject}")

    except Exception as e:
        # SMTP送信エラーが発生してもクラッシュしない
        logging.error(f"管理者通知メールの送信に失敗しました: {str(e)}", exc_info=True)
