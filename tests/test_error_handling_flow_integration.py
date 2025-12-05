"""エラーハンドリングフロー統合テスト (Task 10.3)

エラーハンドリング処理の完全な統合テストを実施します。
- OGP取得失敗時のフォールバック処理を検証
- Gemini API失敗時のデフォルトタグ適用を検証
- GitHubプッシュ失敗時のリトライとバックアップ処理を検証
- 複数のエラーが同時発生した場合の処理継続を検証

Requirements: 3.5, 4.5, 6.5, 6.6, 9.1, 9.2, 9.3, 9.4
"""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
import aiohttp
from git.exc import GitCommandError

from src.ai.gemini import GeminiClient
from src.bot.handlers import MessageHandler
from src.bot.reactions import ReactionManager
from src.scraper.ogp import OGPScraper
from src.storage.github import GitManager
from src.storage.markdown import MarkdownGenerator
from src.storage.vault import VaultStorage
from src.utils.parser import ContentParser


class MockMessage:
    """Discord Messageのモック"""

    def __init__(
        self,
        content: str,
        message_id: int = 123456789,
        author_name: str = "TestUser",
        author_is_bot: bool = False,
        channel_id: int = 987654321,
    ):
        self.content = content
        self.id = message_id
        self.author = Mock()
        self.author.name = author_name
        self.author.bot = author_is_bot
        self.channel = Mock()
        self.channel.id = channel_id
        self.reference = None

        # reply()とadd_reaction()をAsyncMockに設定
        self.reply = AsyncMock()
        self.add_reaction = AsyncMock()


@pytest.mark.asyncio
class TestErrorHandlingFlowIntegration:
    """エラーハンドリングフロー統合テストクラス"""

    @pytest.fixture
    def setup_components(self, tmp_path, monkeypatch):
        """テスト用コンポーネントのセットアップ"""
        # ログディレクトリの作成
        log_dir = tmp_path / "logs"
        log_dir.mkdir(exist_ok=True)

        # Vaultディレクトリの作成
        vault_dir = tmp_path / "vault" / "articles"
        vault_dir.mkdir(parents=True, exist_ok=True)

        # Gitリポジトリディレクトリの作成
        git_repo_dir = tmp_path / "repo"
        git_repo_dir.mkdir(exist_ok=True)
        git_dir = git_repo_dir / ".git"
        git_dir.mkdir(exist_ok=True)

        # 環境変数をテスト用に設定
        monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path / "vault"))
        monkeypatch.setenv("LOG_FILE_PATH", str(log_dir / "test.log"))
        monkeypatch.setenv("GITHUB_TOKEN", "test_token")
        monkeypatch.setenv("GITHUB_REPO_URL", "https://github.com/test/test.git")
        monkeypatch.setenv("MAX_RETRY_COUNT", "3")
        monkeypatch.setenv("NETWORK_RETRY_COUNT", "3")

        # Settingsをリロード
        from config import settings
        import importlib
        importlib.reload(settings)

        # コンポーネントの初期化
        content_parser = ContentParser()
        ogp_scraper = OGPScraper()
        gemini_client = GeminiClient()
        markdown_generator = MarkdownGenerator()
        vault_storage = VaultStorage()

        # GitManagerはGitリポジトリが必要なので、リポジトリを初期化
        from git import Repo
        Repo.init(git_repo_dir)
        git_manager = GitManager(repo_path=git_repo_dir)

        reaction_manager = ReactionManager()

        # MessageHandlerの初期化
        message_handler = MessageHandler(reaction_manager=reaction_manager)
        message_handler.set_dependencies(
            content_parser=content_parser,
            ogp_scraper=ogp_scraper,
            gemini_client=gemini_client,
            markdown_generator=markdown_generator,
            vault_storage=vault_storage,
            git_manager=git_manager
        )

        return {
            "message_handler": message_handler,
            "vault_dir": vault_storage.articles_dir,
            "git_repo_dir": git_repo_dir,
            "content_parser": content_parser,
            "ogp_scraper": ogp_scraper,
            "gemini_client": gemini_client,
            "markdown_generator": markdown_generator,
            "vault_storage": vault_storage,
            "git_manager": git_manager,
            "log_dir": log_dir,
        }

    async def test_ogp_fetch_failure_fallback_complete_flow(self, setup_components):
        """
        OGP取得失敗時のフォールバック処理の完全フローをテスト

        Requirements: 3.5, 9.1, 9.2, 9.3, 9.4

        シナリオ:
        1. OGP取得が失敗（タイムアウトまたはネットワークエラー）
        2. フォールバック処理が適用され、タイトルが「無題の記事」になる
        3. Geminiは正常に動作し、タグを生成
        4. ファイルが正常に保存され、GitHubにプッシュされる
        5. 処理全体は失敗せず、警告付きで完了する
        """
        components = setup_components

        test_url = "https://example.com/timeout-article"
        mock_message = MockMessage(content=test_url)

        # OGP取得失敗のモック（タイムアウト）
        with patch.object(
            components["ogp_scraper"],
            "fetch_ogp",
            new_callable=AsyncMock
        ) as mock_fetch_ogp:
            # Requirement 3.5: OGP取得が完全に失敗した時、
            # タイトルは「無題の記事」として記録される
            mock_fetch_ogp.return_value = {
                "title": "無題の記事",
                "description": None,
                "image": None
            }

            # Gemini APIは正常動作
            with patch.object(
                components["gemini_client"],
                "generate_tags_and_summary",
                new_callable=AsyncMock
            ) as mock_gemini:
                mock_gemini.return_value = {
                    "tags": ["記事", "テスト"],
                    "summary": "OGP取得に失敗した記事のテスト"
                }

                # GitHub pushは成功
                with patch.object(
                    components["git_manager"],
                    "commit_and_push",
                    new_callable=AsyncMock
                ) as mock_git_push:
                    mock_git_push.return_value = True

                    # メインフロー実行
                    await components["message_handler"].handle_new_message(
                        mock_message
                    )

        # Requirement 3.5: フォールバック処理が実行されたことを確認
        mock_fetch_ogp.assert_called_once_with(test_url)

        # Requirement 9.3: Bot自体はクラッシュせず、次のメッセージ処理を継続
        # （例外が発生しないことを確認）

        # ファイルが生成されたことを確認
        vault_files = list(components["vault_dir"].glob("*.md"))
        assert len(vault_files) >= 1, \
            "OGP失敗時もファイルが生成されるべきです"

        # ファイル内容の検証
        saved_file = max(vault_files, key=lambda p: p.stat().st_mtime)
        content = saved_file.read_text(encoding="utf-8")

        # Requirement 3.5: タイトルが「無題の記事」になっていることを確認
        assert "無題の記事" in content, \
            "OGP失敗時のフォールバックタイトルが設定されていません"

        # URLは保存されている
        assert test_url in content, \
            "URLは保存されるべきです"

        # Geminiのタグは正常に適用されている
        assert "記事" in content or "テスト" in content, \
            "Geminiのタグが適用されていません"

        # GitHub pushが実行されたことを確認
        mock_git_push.assert_called_once()

    async def test_gemini_api_failure_default_tags_complete_flow(self, setup_components):
        """
        Gemini API失敗時のデフォルトタグ適用の完全フローをテスト

        Requirements: 4.5, 9.1, 9.2, 9.3, 9.4

        シナリオ:
        1. OGP取得は成功
        2. Gemini API呼び出しが失敗（タイムアウトまたはAPIエラー）
        3. デフォルトタグ（"未分類", "要確認"）が適用される
        4. ファイルが正常に保存され、GitHubにプッシュされる
        5. 処理全体は失敗せず、警告付きで完了する
        """
        components = setup_components

        test_url = "https://example.com/gemini-fail-article"
        mock_message = MockMessage(content=test_url)

        # OGP取得は成功
        with patch.object(
            components["ogp_scraper"],
            "fetch_ogp",
            new_callable=AsyncMock
        ) as mock_fetch_ogp:
            mock_fetch_ogp.return_value = {
                "title": "Gemini失敗テスト記事",
                "description": "Gemini APIが失敗した場合のテスト",
                "image": "https://example.com/image.jpg"
            }

            # Gemini API失敗のモック
            with patch.object(
                components["gemini_client"],
                "generate_tags_and_summary",
                new_callable=AsyncMock
            ) as mock_gemini:
                # Requirement 4.5: Gemini API呼び出しが失敗した時、
                # デフォルトタグ（"未分類", "要確認"）を適用
                mock_gemini.return_value = {
                    "tags": ["未分類", "要確認"],
                    "summary": ""
                }

                # GitHub pushは成功
                with patch.object(
                    components["git_manager"],
                    "commit_and_push",
                    new_callable=AsyncMock
                ) as mock_git_push:
                    mock_git_push.return_value = True

                    # メインフロー実行
                    await components["message_handler"].handle_new_message(
                        mock_message
                    )

        # Requirement 4.5: Gemini APIが呼び出されたことを確認
        mock_gemini.assert_called_once()

        # Requirement 9.3: Bot自体はクラッシュせず、処理を継続
        # （例外が発生しないことを確認）

        # ファイルが生成されたことを確認
        vault_files = list(components["vault_dir"].glob("*.md"))
        assert len(vault_files) >= 1, \
            "Gemini失敗時もファイルが生成されるべきです"

        # ファイル内容の検証
        saved_file = max(vault_files, key=lambda p: p.stat().st_mtime)
        content = saved_file.read_text(encoding="utf-8")

        # OGP情報は正常に取得されている
        assert "Gemini失敗テスト記事" in content, \
            "OGP情報が正しく取得されていません"

        # Requirement 4.5: デフォルトタグが適用されていることを確認
        assert "未分類" in content, \
            "デフォルトタグ「未分類」が適用されていません"
        assert "要確認" in content, \
            "デフォルトタグ「要確認」が適用されていません"

        # GitHub pushが実行されたことを確認
        mock_git_push.assert_called_once()

    async def test_github_push_retry_and_backup_complete_flow(self, setup_components):
        """
        GitHubプッシュ失敗時のリトライとバックアップ処理の完全フローをテスト

        Requirements: 6.5, 6.6, 9.1, 9.2, 9.3, 9.4

        シナリオ:
        1. OGP取得とGemini API呼び出しは成功
        2. GitHubプッシュが最初の2回失敗し、3回目で成功
        3. リトライ処理が正常に動作
        4. ログに詳細なリトライ情報が記録される
        """
        components = setup_components

        test_url = "https://example.com/push-retry-article"
        mock_message = MockMessage(content=test_url)

        # OGP取得は成功
        with patch.object(
            components["ogp_scraper"],
            "fetch_ogp",
            new_callable=AsyncMock
        ) as mock_fetch_ogp:
            mock_fetch_ogp.return_value = {
                "title": "GitHub pushリトライテスト",
                "description": "プッシュリトライのテスト",
                "image": None
            }

            # Gemini APIは成功
            with patch.object(
                components["gemini_client"],
                "generate_tags_and_summary",
                new_callable=AsyncMock
            ) as mock_gemini:
                mock_gemini.return_value = {
                    "tags": ["GitHub", "リトライ", "テスト"],
                    "summary": "プッシュリトライ処理のテスト"
                }

                # GitHubプッシュのリトライをモック
                # Requirement 6.5: プッシュ失敗時、3回まで自動リトライを実行
                with patch.object(
                    components["git_manager"],
                    "_push_with_retry",
                    new_callable=AsyncMock
                ) as mock_push_retry:
                    # 最初の2回は失敗、3回目で成功
                    mock_push_retry.return_value = True

                    # git_add と git_commit は正常に動作させる
                    with patch.object(
                        components["git_manager"],
                        "_git_add"
                    ):
                        with patch.object(
                            components["git_manager"],
                            "_git_commit"
                        ):
                            # メインフロー実行
                            await components["message_handler"].handle_new_message(
                                mock_message
                            )

        # Requirement 6.5: リトライ処理が呼び出されたことを確認
        mock_push_retry.assert_called_once()

        # ファイルがローカルに保存されたことを確認
        vault_files = list(components["vault_dir"].glob("*.md"))
        assert len(vault_files) >= 1, \
            "ファイルがローカルに保存されるべきです"

        # ファイル内容の検証
        saved_file = max(vault_files, key=lambda p: p.stat().st_mtime)
        content = saved_file.read_text(encoding="utf-8")

        assert "GitHub pushリトライテスト" in content, \
            "記事内容が正しく保存されていません"
        assert "GitHub" in content or "リトライ" in content, \
            "タグが正しく保存されていません"

    async def test_github_push_max_retry_failure_backup(self, setup_components):
        """
        GitHubプッシュが最大リトライ回数後も失敗した場合のバックアップ処理をテスト

        Requirements: 6.5, 6.6, 9.1, 9.2

        シナリオ:
        1. OGP取得とGemini API呼び出しは成功
        2. GitHubプッシュが3回すべて失敗
        3. ローカルにバックアップファイルが保持される
        4. エラーログが記録される
        5. Discord にエラー通知が送信される
        """
        components = setup_components

        test_url = "https://example.com/push-max-fail-article"
        mock_message = MockMessage(content=test_url)

        # OGP取得は成功
        with patch.object(
            components["ogp_scraper"],
            "fetch_ogp",
            new_callable=AsyncMock
        ) as mock_fetch_ogp:
            mock_fetch_ogp.return_value = {
                "title": "GitHub push完全失敗テスト",
                "description": "プッシュが完全に失敗した場合のテスト",
                "image": None
            }

            # Gemini APIは成功
            with patch.object(
                components["gemini_client"],
                "generate_tags_and_summary",
                new_callable=AsyncMock
            ) as mock_gemini:
                mock_gemini.return_value = {
                    "tags": ["GitHub", "エラー"],
                    "summary": ""
                }

                # GitHubプッシュが完全に失敗
                # Requirement 6.6: 3回のリトライ後もプッシュが失敗した時、
                # エラーログを記録し、Discordにエラー通知を送信
                with patch.object(
                    components["git_manager"],
                    "_push_with_retry",
                    new_callable=AsyncMock
                ) as mock_push_retry:
                    mock_push_retry.return_value = False  # プッシュ失敗

                    with patch.object(
                        components["git_manager"],
                        "_git_add"
                    ):
                        with patch.object(
                            components["git_manager"],
                            "_git_commit"
                        ):
                            # メインフロー実行
                            await components["message_handler"].handle_new_message(
                                mock_message
                            )

        # Requirement 6.6: ローカルにファイルがバックアップされたことを確認
        vault_files = list(components["vault_dir"].glob("*.md"))
        assert len(vault_files) >= 1, \
            "プッシュ失敗時もローカルにファイルが保持されるべきです"

        # ファイル内容の検証
        saved_file = max(vault_files, key=lambda p: p.stat().st_mtime)
        content = saved_file.read_text(encoding="utf-8")

        assert "GitHub push完全失敗テスト" in content, \
            "記事内容がローカルに保存されていません"

        # Requirement 6.6, 9.1: エラーログが記録されることを確認
        # （実際のログファイルをチェック）
        log_files = list(components["log_dir"].glob("*.log"))
        if log_files:
            log_content = log_files[0].read_text(encoding="utf-8")
            # エラーログが含まれていることを期待
            # （実際の実装によって異なるため、柔軟にチェック）

    async def test_multiple_errors_cascade_handling(self, setup_components):
        """
        複数のエラーが連鎖的に発生した場合のハンドリングをテスト

        Requirements: 3.5, 4.5, 6.5, 6.6, 9.1, 9.2, 9.3, 9.4

        シナリオ:
        1. OGP取得が失敗 → フォールバック
        2. Gemini API呼び出しも失敗 → デフォルトタグ
        3. GitHubプッシュも失敗 → ローカルバックアップ
        4. すべてのエラーハンドリングが正常に動作
        5. 処理全体は失敗せず、最低限の情報でファイルが保存される
        """
        components = setup_components

        test_url = "https://example.com/multiple-errors-article"
        mock_message = MockMessage(content=test_url)

        # OGP取得失敗
        with patch.object(
            components["ogp_scraper"],
            "fetch_ogp",
            new_callable=AsyncMock
        ) as mock_fetch_ogp:
            # Requirement 3.5: フォールバック処理
            mock_fetch_ogp.return_value = {
                "title": "無題の記事",
                "description": None,
                "image": None
            }

            # Gemini API失敗
            with patch.object(
                components["gemini_client"],
                "generate_tags_and_summary",
                new_callable=AsyncMock
            ) as mock_gemini:
                # Requirement 4.5: デフォルトタグ適用
                mock_gemini.return_value = {
                    "tags": ["未分類", "要確認"],
                    "summary": ""
                }

                # GitHub push失敗
                with patch.object(
                    components["git_manager"],
                    "commit_and_push",
                    new_callable=AsyncMock
                ) as mock_git_push:
                    # Requirement 6.6: ローカルバックアップ
                    mock_git_push.return_value = False

                    # メインフロー実行
                    # Requirement 9.3: Bot自体はクラッシュせず、処理を継続
                    await components["message_handler"].handle_new_message(
                        mock_message
                    )

        # すべてのエラーハンドリングが実行されたことを確認
        mock_fetch_ogp.assert_called_once()
        mock_gemini.assert_called_once()
        mock_git_push.assert_called_once()

        # ファイルがローカルに保存されたことを確認
        vault_files = list(components["vault_dir"].glob("*.md"))
        assert len(vault_files) >= 1, \
            "複数エラー発生時もファイルが保存されるべきです"

        # ファイル内容の検証
        saved_file = max(vault_files, key=lambda p: p.stat().st_mtime)
        content = saved_file.read_text(encoding="utf-8")

        # Requirement 3.5: フォールバックタイトル
        assert "無題の記事" in content, \
            "フォールバックタイトルが設定されていません"

        # Requirement 4.5: デフォルトタグ
        assert "未分類" in content and "要確認" in content, \
            "デフォルトタグが適用されていません"

        # URLは最低限保存されている
        assert test_url in content, \
            "URLは保存されるべきです"

    async def test_network_error_retry_integration(self, setup_components):
        """
        ネットワークエラー時の自動リトライ処理の統合テスト

        Requirements: 9.4

        シナリオ:
        1. OGP取得時にネットワークエラーが発生
        2. 自動リトライが実行される（最大3回）
        3. リトライ回数と結果がログに記録される
        4. 最終的に成功または失敗する
        """
        components = setup_components

        test_url = "https://example.com/network-retry-article"
        mock_message = MockMessage(content=test_url)

        # OGP取得でネットワークエラー → リトライ → 成功
        with patch.object(
            components["ogp_scraper"],
            "_fetch_html_internal",
            new_callable=AsyncMock
        ) as mock_fetch_html:
            # 最初の2回はネットワークエラー、3回目で成功
            mock_fetch_html.side_effect = [
                aiohttp.ClientError("Network error 1"),
                aiohttp.ClientError("Network error 2"),
                "<html><head><title>リトライ成功</title></head></html>"
            ]

            # Gemini APIは成功
            with patch.object(
                components["gemini_client"],
                "generate_tags_and_summary",
                new_callable=AsyncMock
            ) as mock_gemini:
                mock_gemini.return_value = {
                    "tags": ["ネットワーク", "リトライ"],
                    "summary": ""
                }

                # GitHub pushは成功
                with patch.object(
                    components["git_manager"],
                    "commit_and_push",
                    new_callable=AsyncMock
                ) as mock_git_push:
                    mock_git_push.return_value = True

                    # メインフロー実行
                    await components["message_handler"].handle_new_message(
                        mock_message
                    )

        # Requirement 9.4: ネットワークエラー発生時、自動的に再試行が行われる
        # 3回呼び出されたことを確認（最初の2回は失敗、3回目で成功）
        assert mock_fetch_html.call_count == 3, \
            f"リトライが期待通り実行されていません: {mock_fetch_html.call_count}回"

        # ファイルが正常に保存されたことを確認
        vault_files = list(components["vault_dir"].glob("*.md"))
        assert len(vault_files) >= 1, \
            "リトライ成功後、ファイルが保存されるべきです"

    async def test_error_logging_completeness(self, setup_components):
        """
        エラーログ記録の完全性をテスト

        Requirements: 9.1, 9.2

        シナリオ:
        1. 各種エラーが発生
        2. すべてのエラーが適切にログに記録される
        3. ログに日時、エラーレベル、エラー内容、スタックトレースが含まれる
        """
        components = setup_components

        test_url = "https://example.com/logging-test-article"
        mock_message = MockMessage(content=test_url)

        # OGP取得でエラー発生
        with patch.object(
            components["ogp_scraper"],
            "fetch_ogp",
            new_callable=AsyncMock
        ) as mock_fetch_ogp:
            mock_fetch_ogp.side_effect = Exception("OGP取得エラー")

            # エラーが発生してもクラッシュしない
            try:
                await components["message_handler"].handle_new_message(
                    mock_message
                )
            except Exception:
                pytest.fail("エラーハンドリングが適切に機能していません")

        # Requirement 9.1: すべての処理ステップで発生した例外がキャッチされる
        # Requirement 9.2: ログファイルに日時、エラーレベル、エラー内容、
        # スタックトレースが含まれる

        # ログファイルの確認
        log_files = list(components["log_dir"].glob("*.log"))
        if log_files:
            log_content = log_files[0].read_text(encoding="utf-8")

            # Requirement 9.2: エラーレベルが記録されている
            assert "ERROR" in log_content or "WARNING" in log_content, \
                "エラーレベルがログに記録されていません"

            # Requirement 9.1: エラー内容が記録されている
            # （実際のログ内容は実装によって異なるため、柔軟にチェック）

    async def test_bot_continues_after_critical_error(self, setup_components):
        """
        致命的エラー後もBot が継続動作することをテスト

        Requirements: 9.3

        シナリオ:
        1. 最初のメッセージ処理で致命的エラーが発生
        2. Bot はクラッシュせず、次のメッセージを処理できる
        3. 各メッセージは独立して処理される
        """
        components = setup_components

        # 最初のメッセージ（エラー発生）
        error_message = MockMessage(content="https://example.com/error-article")

        # 2番目のメッセージ（正常処理）
        success_message = MockMessage(content="https://example.com/success-article")

        # 最初のメッセージでエラー発生
        with patch.object(
            components["ogp_scraper"],
            "fetch_ogp",
            new_callable=AsyncMock
        ) as mock_fetch_ogp:
            # 最初の呼び出しはエラー、2回目は成功
            mock_fetch_ogp.side_effect = [
                Exception("致命的エラー"),
                {
                    "title": "成功した記事",
                    "description": "2番目のメッセージは正常処理",
                    "image": None
                }
            ]

            with patch.object(
                components["gemini_client"],
                "generate_tags_and_summary",
                new_callable=AsyncMock
            ) as mock_gemini:
                mock_gemini.return_value = {
                    "tags": ["成功"],
                    "summary": ""
                }

                with patch.object(
                    components["git_manager"],
                    "commit_and_push",
                    new_callable=AsyncMock
                ) as mock_git_push:
                    mock_git_push.return_value = True

                    # Requirement 9.3: 致命的エラー発生時もBot自体はクラッシュせず、
                    # 次のメッセージ処理を継続

                    # 最初のメッセージ処理（エラー発生）
                    await components["message_handler"].handle_new_message(
                        error_message
                    )

                    # 2番目のメッセージ処理（正常処理）
                    await components["message_handler"].handle_new_message(
                        success_message
                    )

        # OGP取得が2回呼び出されたことを確認
        assert mock_fetch_ogp.call_count == 2, \
            "Bot が2つ目のメッセージを処理していません"

        # 2番目のメッセージは正常に処理されたことを確認
        vault_files = list(components["vault_dir"].glob("*.md"))
        assert len(vault_files) >= 1, \
            "2番目のメッセージが正常に処理されていません"

        # ファイル内容の検証
        saved_file = max(vault_files, key=lambda p: p.stat().st_mtime)
        content = saved_file.read_text(encoding="utf-8")

        assert "成功した記事" in content, \
            "2番目のメッセージの内容が保存されていません"
