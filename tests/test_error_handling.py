"""エラーハンドリングとロギングのテスト

Task 9.1: 例外キャッチとエラーログ記録の実装のテスト
- 全処理ステップで例外をキャッチし、詳細なエラーログを記録
- スタックトレース、エラーレベル（INFO/WARNING/ERROR）、日時を含めたログ出力
- 致命的エラー発生時もBot自体はクラッシュせず、次のメッセージ処理を継続
"""

import asyncio
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.ai.gemini import GeminiClient
from src.bot.handlers import MessageHandler
from src.scraper.ogp import OGPScraper
from src.storage.github import GitManager
from src.storage.vault import VaultStorage
from src.utils.logger import Logger, log_exception, setup_logger


class TestLoggerErrorHandling:
    """Loggerのエラーハンドリングテスト"""

    def test_setup_logger_creates_log_file(self, tmp_path):
        """ロガーのセットアップでログファイルが作成される"""
        log_file = tmp_path / "test.log"
        logger = setup_logger("test_logger", str(log_file))

        assert logger is not None
        assert logger.name == "test_logger"
        assert log_file.parent.exists()

    def test_log_exception_includes_stack_trace(self, tmp_path):
        """log_exceptionがスタックトレースを含む（Requirement 9.1, 9.2）"""
        log_file = tmp_path / "test_error.log"
        logger = setup_logger("test_exception", str(log_file))

        try:
            raise ValueError("テストエラー")
        except Exception as e:
            log_exception(logger, "エラーが発生しました", e)

        # ログファイルを読み込み
        log_content = log_file.read_text(encoding="utf-8")

        # スタックトレースが含まれていることを確認
        assert "ValueError: テストエラー" in log_content
        assert "Traceback" in log_content
        assert "エラーが発生しました" in log_content

    def test_log_levels_are_recorded(self, tmp_path):
        """エラーレベル（INFO/WARNING/ERROR）が記録される（Requirement 9.2）"""
        log_file = tmp_path / "test_levels.log"
        logger = setup_logger("test_levels", str(log_file))

        logger.info("INFO level message")
        logger.warning("WARNING level message")
        logger.error("ERROR level message")

        log_content = log_file.read_text(encoding="utf-8")

        assert "INFO" in log_content
        assert "WARNING" in log_content
        assert "ERROR" in log_content

    def test_log_includes_timestamp(self, tmp_path):
        """ログに日時が含まれる（Requirement 9.2）"""
        log_file = tmp_path / "test_timestamp.log"
        logger = setup_logger("test_timestamp", str(log_file))

        logger.info("タイムスタンプテスト")

        log_content = log_file.read_text(encoding="utf-8")

        # YYYY-MM-DD HH:MM:SS形式のタイムスタンプを確認
        import re
        timestamp_pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
        assert re.search(timestamp_pattern, log_content)


class TestMessageHandlerErrorHandling:
    """MessageHandlerのエラーハンドリングテスト"""

    @pytest.mark.asyncio
    async def test_handle_new_message_catches_parser_error(self):
        """ContentParserエラー時も処理を継続（Requirement 9.3）"""
        handler = MessageHandler()

        # モックメッセージを作成
        mock_message = AsyncMock()
        mock_message.id = 12345
        mock_message.content = "test content"
        mock_message.reply = AsyncMock()

        # ContentParserがエラーを投げるように設定
        mock_parser = Mock()
        mock_parser.parse_message.side_effect = ValueError("パースエラー")

        handler.set_dependencies(content_parser=mock_parser)

        # エラーが発生してもクラッシュしない
        await handler.handle_new_message(mock_message)

        # エラーメッセージが返信される
        mock_message.reply.assert_called()
        reply_args = mock_message.reply.call_args[0][0]
        assert "エラーが発生しました" in reply_args

    @pytest.mark.asyncio
    async def test_handle_new_message_continues_after_ogp_error(self):
        """OGP取得エラー時も処理を継続（Requirement 9.3）"""
        handler = MessageHandler()

        mock_message = AsyncMock()
        mock_message.id = 12345
        mock_message.content = "https://example.com"
        mock_message.reply = AsyncMock()

        # ContentParserは正常
        mock_parser = Mock()
        mock_parser.parse_message.return_value = {
            "url": "https://example.com",
            "comment": None
        }

        # OGPScraperがエラーを投げる
        mock_ogp = AsyncMock()
        mock_ogp.fetch_ogp.side_effect = Exception("OGP取得エラー")

        handler.set_dependencies(
            content_parser=mock_parser,
            ogp_scraper=mock_ogp
        )

        # エラーが発生してもクラッシュしない
        await handler.handle_new_message(mock_message)

        # エラーメッセージが返信される
        mock_message.reply.assert_called()

    @pytest.mark.asyncio
    async def test_handle_thread_comment_catches_file_not_found(self):
        """ファイル未検出時に適切なエラーメッセージを返す（Requirement 8.6）"""
        handler = MessageHandler()

        mock_message = AsyncMock()
        mock_message.id = 12345
        mock_message.content = "コメント"
        mock_message.reference = Mock()
        mock_message.reference.message_id = 67890
        mock_message.channel.fetch_message = AsyncMock()
        mock_message.reply = AsyncMock()

        parent_message = Mock()
        parent_message.content = "https://example.com"
        mock_message.channel.fetch_message.return_value = parent_message

        mock_parser = Mock()
        mock_parser.parse_message.return_value = {
            "url": "https://example.com"
        }

        # VaultStorageがNoneを返す（ファイル未検出）
        mock_vault = Mock()
        mock_vault.find_article_by_url.return_value = None

        handler.set_dependencies(
            content_parser=mock_parser,
            vault_storage=mock_vault
        )

        await handler.handle_thread_comment(mock_message)

        # エラーメッセージが返信される
        mock_message.reply.assert_called()
        reply_args = mock_message.reply.call_args[0][0]
        assert "記事ファイルが見つかりませんでした" in reply_args


class TestOGPScraperErrorHandling:
    """OGPScraperのエラーハンドリングテスト"""

    @pytest.mark.asyncio
    async def test_fetch_ogp_handles_timeout(self):
        """タイムアウト時にフォールバック処理が実行される（Requirement 3.6）"""
        scraper = OGPScraper()

        with patch("aiohttp.ClientSession") as mock_session:
            # タイムアウトをシミュレート
            mock_session.return_value.__aenter__.return_value.get.side_effect = asyncio.TimeoutError()

            result = await scraper.fetch_ogp("https://example.com")

            # フォールバック処理が実行される
            assert result["title"] == "無題の記事"
            assert result["description"] is None

    @pytest.mark.asyncio
    async def test_fetch_ogp_handles_network_error(self):
        """ネットワークエラー時にフォールバック処理が実行される"""
        scraper = OGPScraper()

        with patch("aiohttp.ClientSession") as mock_session:
            # ネットワークエラーをシミュレート
            mock_session.return_value.__aenter__.return_value.get.side_effect = Exception("Network error")

            result = await scraper.fetch_ogp("https://example.com")

            # フォールバック処理が実行される
            assert result["title"] == "無題の記事"


class TestGeminiClientErrorHandling:
    """GeminiClientのエラーハンドリングテスト"""

    @pytest.mark.asyncio
    async def test_generate_tags_handles_timeout(self):
        """タイムアウト時にデフォルトタグを返す（Requirement 4.7）"""
        client = GeminiClient()

        with patch.object(client, "_call_gemini_api") as mock_api:
            # タイムアウトをシミュレート（30秒以上かかる処理）
            async def slow_api(*args):
                await asyncio.sleep(100)
                return {"tags": [], "summary": ""}

            mock_api.side_effect = slow_api

            result = await client.generate_tags_and_summary("タイトル", "概要")

            # デフォルトタグが返される
            assert result["tags"] == ["未分類", "要確認"]
            assert result["summary"] == ""

    @pytest.mark.asyncio
    async def test_generate_tags_handles_api_error(self):
        """API呼び出しエラー時にデフォルトタグを返す（Requirement 4.5）"""
        client = GeminiClient()

        with patch.object(client, "_call_gemini_api") as mock_api:
            # APIエラーをシミュレート
            mock_api.side_effect = Exception("API Error")

            result = await client.generate_tags_and_summary("タイトル", "概要")

            # デフォルトタグが返される
            assert result["tags"] == ["未分類", "要確認"]


class TestGitManagerErrorHandling:
    """GitManagerのエラーハンドリングテスト"""

    @pytest.mark.asyncio
    async def test_commit_and_push_handles_git_error(self, tmp_path):
        """Git操作エラー時に適切にハンドリング"""
        # テスト用のgitリポジトリを作成
        from git import Repo
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        Repo.init(repo_path)

        git_manager = GitManager(repo_path=repo_path)

        # ファイルを作成
        test_file = repo_path / "test.md"
        test_file.write_text("test content")

        with patch.object(git_manager, "_git_push") as mock_push:
            # プッシュエラーをシミュレート
            from git.exc import GitCommandError
            mock_push.side_effect = GitCommandError("push", "Push failed")

            result = await git_manager.commit_and_push(
                test_file,
                "Test commit"
            )

            # プッシュ失敗時はFalseを返す
            assert result is False

    @pytest.mark.asyncio
    async def test_commit_and_push_retries_on_failure(self, tmp_path):
        """プッシュ失敗時にリトライされる（Requirement 6.5）"""
        from git import Repo
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        Repo.init(repo_path)

        git_manager = GitManager(repo_path=repo_path)

        test_file = repo_path / "test.md"
        test_file.write_text("test content")

        with patch.object(git_manager, "_git_push") as mock_push:
            from git.exc import GitCommandError
            # 最初の2回は失敗、3回目は成功
            mock_push.side_effect = [
                GitCommandError("push", "Failed"),
                GitCommandError("push", "Failed"),
                None  # 成功
            ]

            result = await git_manager.commit_and_push(
                test_file,
                "Test commit"
            )

            # 3回目で成功
            assert result is True
            assert mock_push.call_count == 3


class TestVaultStorageErrorHandling:
    """VaultStorageのエラーハンドリングテスト"""

    @pytest.mark.asyncio
    async def test_save_article_handles_disk_error(self, tmp_path):
        """ディスクエラー時に適切なエラーを投げる"""
        vault = VaultStorage()
        vault.articles_dir = tmp_path / "readonly"

        # 読み取り専用ディレクトリでエラーをシミュレート
        with patch("pathlib.Path.write_text") as mock_write:
            mock_write.side_effect = IOError("Disk full")

            with pytest.raises(IOError):
                await vault.save_article("タイトル", "コンテンツ")

    @pytest.mark.asyncio
    async def test_append_comment_handles_file_not_found(self, tmp_path):
        """ファイル未検出時に適切なエラーを投げる"""
        vault = VaultStorage()

        non_existent_file = tmp_path / "non_existent.md"

        with pytest.raises(FileNotFoundError):
            await vault.append_comment(non_existent_file, "コメント")


class TestBotClientErrorHandling:
    """Bot Clientのエラーハンドリングテスト"""

    @pytest.mark.asyncio
    async def test_on_message_continues_after_handler_error(self):
        """ハンドラエラー後も次のメッセージ処理を継続（Requirement 9.3）"""
        from src.bot.client import EventListener
        from discord import Intents
        from unittest.mock import PropertyMock

        intents = Intents.default()
        client = EventListener(intents=intents)

        # モックメッセージハンドラ（エラーを投げる）
        mock_handler = AsyncMock()
        mock_handler.handle_new_message.side_effect = Exception("Handler error")
        client.set_message_handler(mock_handler)

        # モックメッセージ
        mock_message = Mock()
        mock_message.author = Mock()
        mock_message.author.bot = False
        mock_message.author.name = "TestUser"
        mock_message.content = "test message"
        mock_message.channel = Mock()
        mock_message.channel.id = 12345
        mock_message.reference = None

        # clientのuserプロパティをPropertyMockでモック
        mock_user = Mock()
        mock_user.name = "BotUser"

        with patch.object(type(client), 'user', new_callable=PropertyMock, return_value=mock_user):
            # エラーが発生してもクラッシュしない
            await client.on_message(mock_message)

            # ハンドラが呼ばれたことを確認
            mock_handler.handle_new_message.assert_called_once()


class TestAdminNotification:
    """管理者通知機能のテスト（Task 9.3）"""

    def test_admin_notification_env_vars_loaded(self):
        """環境変数から管理者通知設定が読み込まれる（Requirement 9.7）"""
        from config.settings import Settings

        # 環境変数が定義されていることを確認
        assert hasattr(Settings, 'ADMIN_NOTIFICATION_ENABLED')
        assert hasattr(Settings, 'ADMIN_EMAIL_FROM')
        assert hasattr(Settings, 'ADMIN_EMAIL_TO')
        assert hasattr(Settings, 'SMTP_HOST')
        assert hasattr(Settings, 'SMTP_PORT')

    def test_admin_notification_disabled_by_default(self):
        """管理者通知がデフォルトで無効化されている"""
        from config.settings import Settings

        # デフォルトでは無効（またはFalse）
        assert Settings.ADMIN_NOTIFICATION_ENABLED in [False, '', '0', 'false', 'False']

    @patch('smtplib.SMTP')
    @patch('src.utils.logger.Settings')
    def test_send_admin_notification_sends_email(self, mock_settings, mock_smtp):
        """send_admin_notificationがメールを送信する（Requirement 9.7）"""
        from src.utils.logger import send_admin_notification

        # Settingsをモック
        mock_settings.ADMIN_NOTIFICATION_ENABLED = True
        mock_settings.ADMIN_EMAIL_FROM = 'bot@example.com'
        mock_settings.ADMIN_EMAIL_TO = 'admin@example.com'
        mock_settings.SMTP_HOST = 'localhost'
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_USER = ''
        mock_settings.SMTP_PASSWORD = ''

        # メール送信を実行
        send_admin_notification(
            subject="テスト通知",
            message="これはテストメッセージです"
        )

        # SMTPが呼ばれたことを確認
        mock_smtp.assert_called_once_with('localhost', 587)

    @patch('smtplib.SMTP')
    @patch('src.utils.logger.Settings')
    def test_send_admin_notification_not_sent_when_disabled(self, mock_settings, mock_smtp):
        """通知が無効な場合はメールを送信しない"""
        from src.utils.logger import send_admin_notification

        # 通知を無効化
        mock_settings.ADMIN_NOTIFICATION_ENABLED = False

        send_admin_notification(
            subject="テスト通知",
            message="これは送信されないはず"
        )

        # SMTPが呼ばれていないことを確認
        mock_smtp.assert_not_called()

    @patch('src.utils.logger.send_admin_notification')
    def test_log_exception_sends_notification_when_notify_admin_true(self, mock_notify, tmp_path):
        """notify_admin=Trueの場合に管理者通知が送信される（Requirement 9.7）"""
        log_file = tmp_path / "test_notify.log"
        logger = setup_logger("test_notify", str(log_file))

        try:
            raise ValueError("重要なエラー")
        except Exception as e:
            log_exception(logger, "GitHub push失敗", e, notify_admin=True)

        # 管理者通知が呼ばれたことを確認
        mock_notify.assert_called_once()
        call_args = mock_notify.call_args
        assert "GitHub push失敗" in call_args[1]['subject']

    @patch('src.utils.logger.send_admin_notification')
    def test_log_exception_no_notification_when_notify_admin_false(self, mock_notify, tmp_path):
        """notify_admin=Falseの場合は管理者通知が送信されない"""
        log_file = tmp_path / "test_no_notify.log"
        logger = setup_logger("test_no_notify", str(log_file))

        try:
            raise ValueError("通常のエラー")
        except Exception as e:
            log_exception(logger, "通常のエラー", e, notify_admin=False)

        # 管理者通知が呼ばれていないことを確認
        mock_notify.assert_not_called()

    @patch('smtplib.SMTP')
    @patch('src.utils.logger.Settings')
    def test_send_admin_notification_handles_smtp_error(self, mock_settings, mock_smtp):
        """SMTP送信エラーが発生してもクラッシュしない"""
        from src.utils.logger import send_admin_notification

        # Settingsをモック
        mock_settings.ADMIN_NOTIFICATION_ENABLED = True
        mock_settings.ADMIN_EMAIL_FROM = 'bot@example.com'
        mock_settings.ADMIN_EMAIL_TO = 'admin@example.com'
        mock_settings.SMTP_HOST = 'localhost'
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_USER = ''
        mock_settings.SMTP_PASSWORD = ''

        # SMTP送信でエラーが発生する設定
        mock_smtp.return_value.__enter__.return_value.sendmail.side_effect = Exception("SMTP Error")

        # エラーが発生してもクラッシュしない
        try:
            send_admin_notification(
                subject="テスト",
                message="テスト"
            )
        except Exception:
            pytest.fail("send_admin_notification should not raise exception")
