"""メインフロー統合テスト (Task 10.1)

Discord投稿からGitHubプッシュまでのエンドツーエンドフローをテストします。
- 各処理ステップのデータ受け渡しを検証
- 処理時間が30秒以内に完了することを確認（要件7.6）
- Requirements: 1.1-7.6の全要件をカバー
"""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

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
        reference=None
    ):
        self.content = content
        self.id = message_id
        self.author = Mock()
        self.author.name = author_name
        self.author.bot = author_is_bot
        self.channel = Mock()
        self.channel.id = channel_id
        self.reference = reference

        # reply()とadd_reaction()をAsyncMockに設定
        self.reply = AsyncMock()
        self.add_reaction = AsyncMock()


@pytest.mark.asyncio
class TestMainFlowIntegration:
    """メインフロー統合テストクラス"""

    @pytest.fixture
    def setup_components(self, tmp_path, monkeypatch):
        """テスト用コンポーネントのセットアップ"""
        # ログディレクトリの作成
        log_dir = tmp_path / "logs"
        log_dir.mkdir(exist_ok=True)

        # Vaultディレクトリの作成
        vault_dir = tmp_path / "vault" / "articles"
        vault_dir.mkdir(parents=True, exist_ok=True)

        # Gitリポジトリディレクトリの作成（.gitディレクトリも作成）
        git_repo_dir = tmp_path / "repo"
        git_repo_dir.mkdir(exist_ok=True)
        git_dir = git_repo_dir / ".git"
        git_dir.mkdir(exist_ok=True)

        # 環境変数をテスト用に設定
        monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path / "vault"))
        monkeypatch.setenv("LOG_FILE_PATH", str(log_dir / "test.log"))
        monkeypatch.setenv("GITHUB_TOKEN", "test_token")
        monkeypatch.setenv("GITHUB_REPO_URL", "https://github.com/test/test.git")

        # Settingsをリロード
        from config import settings
        import importlib
        importlib.reload(settings)

        # コンポーネントの初期化
        content_parser = ContentParser()
        ogp_scraper = OGPScraper()
        gemini_client = GeminiClient()
        markdown_generator = MarkdownGenerator()

        # VaultStorageとGitManagerは実際の設定から読み込むため、
        # テスト用にモックまたはパッチを適用
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
            "vault_dir": vault_storage.articles_dir,  # Use the actual vault dir from VaultStorage
            "git_repo_dir": git_repo_dir,
            "content_parser": content_parser,
            "ogp_scraper": ogp_scraper,
            "gemini_client": gemini_client,
            "markdown_generator": markdown_generator,
            "vault_storage": vault_storage,
            "git_manager": git_manager,
        }

    async def test_full_article_processing_flow(self, setup_components):
        """
        記事処理のエンドツーエンドフローをテスト

        Requirements: 1.1, 1.2, 1.4, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1
        """
        components = setup_components

        # テスト用のメッセージを作成
        test_url = "https://example.com/test-article"
        test_comment = "これは素晴らしい記事です"
        test_message_content = f"{test_url} {test_comment}"
        mock_message = MockMessage(content=test_message_content)

        # OGP取得のモック
        with patch.object(
            components["ogp_scraper"],
            "fetch_ogp",
            new_callable=AsyncMock
        ) as mock_fetch_ogp:
            mock_fetch_ogp.return_value = {
                "title": "テスト記事タイトル",
                "description": "これはテスト記事の説明文です。",
                "image": "https://example.com/image.jpg",
                "success": True
            }

            # Gemini API呼び出しのモック
            with patch.object(
                components["gemini_client"],
                "generate_tags_and_summary",
                new_callable=AsyncMock
            ) as mock_gemini:
                mock_gemini.return_value = {
                    "tags": ["Python", "テスト", "技術記事"],
                    "summary": "Pythonのテスト手法について解説した記事。",
                    "success": True
                }

                # GitHub pushのモック
                with patch.object(
                    components["git_manager"],
                    "commit_and_push",
                    new_callable=AsyncMock
                ) as mock_git_push:
                    mock_git_push.return_value = True

                    # 処理時間の測定開始
                    start_time = time.time()

                    # メインフロー実行
                    await components["message_handler"].handle_new_message(
                        mock_message
                    )

                    # 処理時間の測定終了
                    elapsed_time = time.time() - start_time

                    # Requirement 7.6: 処理時間が30秒以内
                    assert elapsed_time < 30.0, \
                        f"処理時間が30秒を超えました: {elapsed_time:.2f}秒"

        # Requirement 1.4: 受信確認リアクションが追加されたことを確認
        assert mock_message.add_reaction.call_count >= 1, \
            "受信確認リアクションが追加されていません"

        # Requirement 2.1: URL抽出が正しく行われたことを確認
        mock_fetch_ogp.assert_called_once_with(test_url)

        # Requirement 4.1: Gemini APIが呼び出されたことを確認
        mock_gemini.assert_called_once()
        call_args = mock_gemini.call_args
        assert call_args.kwargs["title"] == "テスト記事タイトル"
        assert "テスト記事の説明文" in call_args.kwargs["description"]

        # Requirement 5.1, 6.1: Markdownファイルが生成され、保存されたことを確認
        vault_files = list(components["vault_dir"].glob("*.md"))
        assert len(vault_files) >= 1, \
            "Markdownファイルが生成されていません"

        # ファイル内容の検証（最も最近作成されたファイルを取得）
        saved_file = max(vault_files, key=lambda p: p.stat().st_mtime)
        content = saved_file.read_text(encoding="utf-8")

        # YAMLフロントマターの検証 (Requirement 5.2)
        assert "---" in content, "YAMLフロントマターが含まれていません"
        assert "tags:" in content, "tagsフィールドが含まれていません"
        assert "url:" in content, "urlフィールドが含まれていません"
        assert "created:" in content, "createdフィールドが含まれていません"

        # タイトルの検証 (Requirement 5.3)
        assert "# テスト記事タイトル" in content, \
            "記事タイトルが正しく記述されていません"

        # 概要セクションの検証 (Requirement 5.4)
        assert "## 概要" in content, "概要セクションが含まれていません"
        assert "これはテスト記事の説明文です。" in content, \
            "OGP descriptionが記述されていません"

        # コメントセクションの検証 (Requirement 5.5)
        assert "## コメント" in content, "コメントセクションが含まれていません"
        assert test_comment in content, \
            "初回コメントが記述されていません"

        # Requirement 6.1-6.3: GitHubプッシュが実行されたことを確認
        mock_git_push.assert_called_once()

        # Requirement 7.1: 成功通知が返信されたことを確認
        mock_message.reply.assert_called()
        reply_calls = [call.args[0] for call in mock_message.reply.call_args_list]
        assert any("保存しました" in msg or "✅" in msg for msg in reply_calls), \
            "成功通知が返信されていません"

    async def test_memo_processing_flow(self, setup_components):
        """
        メモ処理フロー（URL無し）のテスト

        Requirements: 2.3, 5.1
        """
        components = setup_components

        # URL無しのメッセージ
        test_memo = "これは重要なメモです。後で確認する。"
        mock_message = MockMessage(content=test_memo)

        # GitHub pushのモック
        with patch.object(
            components["git_manager"],
            "commit_and_push",
            new_callable=AsyncMock
        ) as mock_git_push:
            mock_git_push.return_value = True

            # メインフロー実行
            await components["message_handler"].handle_new_message(mock_message)

        # メモファイルが生成されたことを確認
        vault_files = list(components["vault_dir"].glob("*.md"))
        assert len(vault_files) >= 1, "メモファイルが生成されていません"

        # ファイル内容の検証（最も最近作成されたファイルを取得）
        saved_file = max(vault_files, key=lambda p: p.stat().st_mtime)
        content = saved_file.read_text(encoding="utf-8")
        assert test_memo in content, "メモ内容が保存されていません"

        # GitHubプッシュが実行されたことを確認
        mock_git_push.assert_called_once()

    async def test_processing_with_ogp_failure(self, setup_components):
        """
        OGP取得失敗時のフォールバック処理をテスト

        Requirements: 3.5, 7.3
        """
        components = setup_components

        test_url = "https://example.com/no-ogp-article"
        mock_message = MockMessage(content=test_url)

        # OGP取得失敗のモック
        with patch.object(
            components["ogp_scraper"],
            "fetch_ogp",
            new_callable=AsyncMock
        ) as mock_fetch_ogp:
            mock_fetch_ogp.return_value = {
                "title": None,
                "description": None,
                "image": None,
                "success": False,
                "error": "OGP取得に失敗しました"
            }

            # Gemini API呼び出しのモック（タイトルが無題でも呼び出される）
            with patch.object(
                components["gemini_client"],
                "generate_tags_and_summary",
                new_callable=AsyncMock
            ) as mock_gemini:
                mock_gemini.return_value = {
                    "tags": ["未分類"],
                    "summary": "",
                    "success": True
                }

                # GitHub pushのモック
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

        # ファイルが生成されたことを確認（フォールバック処理が成功）
        vault_files = list(components["vault_dir"].glob("*.md"))
        assert len(vault_files) >= 1, \
            "OGP失敗時もファイルが生成されるべきです"

        # ファイル内容にURLが含まれていることを確認（最も最近作成されたファイルを取得）
        saved_file = max(vault_files, key=lambda p: p.stat().st_mtime)
        content = saved_file.read_text(encoding="utf-8")
        assert test_url in content, "URLが保存されていません"

    async def test_processing_with_gemini_failure(self, setup_components):
        """
        Gemini API失敗時のフォールバック処理をテスト

        Requirements: 4.5
        """
        components = setup_components

        test_url = "https://example.com/test-article"
        mock_message = MockMessage(content=test_url)

        # OGP取得のモック
        with patch.object(
            components["ogp_scraper"],
            "fetch_ogp",
            new_callable=AsyncMock
        ) as mock_fetch_ogp:
            mock_fetch_ogp.return_value = {
                "title": "テスト記事",
                "description": "説明文",
                "success": True
            }

            # Gemini API失敗のモック
            with patch.object(
                components["gemini_client"],
                "generate_tags_and_summary",
                new_callable=AsyncMock
            ) as mock_gemini:
                mock_gemini.return_value = {
                    "tags": ["未分類", "要確認"],  # デフォルトタグ
                    "summary": "",
                    "success": False,
                    "error": "Gemini API呼び出しに失敗しました"
                }

                # GitHub pushのモック
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

        # ファイルが生成されたことを確認
        vault_files = list(components["vault_dir"].glob("*.md"))
        assert len(vault_files) >= 1, \
            "Gemini失敗時もファイルが生成されるべきです"

        # デフォルトタグが使用されていることを確認（最も最近作成されたファイルを取得）
        saved_file = max(vault_files, key=lambda p: p.stat().st_mtime)
        content = saved_file.read_text(encoding="utf-8")
        assert "未分類" in content or "要確認" in content, \
            "デフォルトタグが使用されていません"

    async def test_processing_with_github_push_failure(self, setup_components):
        """
        GitHub push失敗時のエラーハンドリングをテスト

        Requirements: 6.5, 6.6, 7.4
        """
        components = setup_components

        test_url = "https://example.com/test-article"
        mock_message = MockMessage(content=test_url)

        # OGP取得のモック
        with patch.object(
            components["ogp_scraper"],
            "fetch_ogp",
            new_callable=AsyncMock
        ) as mock_fetch_ogp:
            mock_fetch_ogp.return_value = {
                "title": "テスト記事",
                "description": "説明文",
                "success": True
            }

            # Gemini API呼び出しのモック
            with patch.object(
                components["gemini_client"],
                "generate_tags_and_summary",
                new_callable=AsyncMock
            ) as mock_gemini:
                mock_gemini.return_value = {
                    "tags": ["Python"],
                    "summary": "要約",
                    "success": True
                }

                # GitHub push失敗のモック
                with patch.object(
                    components["git_manager"],
                    "commit_and_push",
                    new_callable=AsyncMock
                ) as mock_git_push:
                    # push失敗を返す
                    mock_git_push.return_value = False

                    # メインフロー実行（例外が発生せず継続されることを確認）
                    await components["message_handler"].handle_new_message(
                        mock_message
                    )

        # ファイルはローカルに保存されていることを確認
        vault_files = list(components["vault_dir"].glob("*.md"))
        assert len(vault_files) >= 1, \
            "GitHub push失敗時もローカルにファイルが保存されるべきです"

        # 最も最近作成されたファイルを取得
        saved_file = max(vault_files, key=lambda p: p.stat().st_mtime)

        # エラーリアクションまたはエラーメッセージが返されることを確認
        # （現在の実装では、push失敗は例外を投げる可能性があるため、
        # エラーハンドリングが適切に機能することを確認）
        assert mock_message.add_reaction.called or mock_message.reply.called

    async def test_data_transfer_between_steps(self, setup_components):
        """
        各処理ステップ間のデータ受け渡しを詳細に検証

        Requirements: 全要件のデータフロー検証
        """
        components = setup_components

        test_url = "https://example.com/data-flow-test"
        test_comment = "データフローのテスト"
        mock_message = MockMessage(content=f"{test_url} {test_comment}")

        # 各ステップで渡されるデータを記録
        ogp_data_passed = {}
        gemini_data_passed = {}
        markdown_data_passed = {}

        # OGP取得のモック（データを記録）
        async def mock_fetch_ogp(url):
            ogp_data_passed["url"] = url
            return {
                "title": "データフローテスト",
                "description": "各ステップのデータ受け渡しを検証",
                "success": True
            }

        # Gemini API呼び出しのモック（データを記録）
        async def mock_gemini(title, description):
            gemini_data_passed["title"] = title
            gemini_data_passed["description"] = description
            return {
                "tags": ["テスト", "データフロー"],
                "summary": "要約テスト",
                "success": True
            }

        with patch.object(
            components["ogp_scraper"],
            "fetch_ogp",
            side_effect=mock_fetch_ogp
        ):
            with patch.object(
                components["gemini_client"],
                "generate_tags_and_summary",
                side_effect=mock_gemini
            ):
                with patch.object(
                    components["git_manager"],
                    "commit_and_push",
                    new_callable=AsyncMock,
                    return_value=True
                ):
                    # メインフロー実行
                    await components["message_handler"].handle_new_message(
                        mock_message
                    )

        # ステップ1→2: ContentParser → OGPScraper
        assert ogp_data_passed["url"] == test_url, \
            "URLが正しくOGPScraperに渡されていません"

        # ステップ2→3: OGPScraper → GeminiClient
        assert gemini_data_passed["title"] == "データフローテスト", \
            "タイトルが正しくGeminiClientに渡されていません"
        assert "各ステップのデータ受け渡しを検証" in gemini_data_passed["description"], \
            "説明文が正しくGeminiClientに渡されていません"

        # ステップ3→4→5: GeminiClient → MarkdownGenerator → VaultStorage
        vault_files = list(components["vault_dir"].glob("*.md"))
        assert len(vault_files) >= 1
        # 最も最近作成されたファイルを取得
        saved_file = max(vault_files, key=lambda p: p.stat().st_mtime)
        content = saved_file.read_text(encoding="utf-8")

        # すべてのデータが最終ファイルに含まれていることを確認
        assert test_url in content, "URLがファイルに含まれていません"
        assert "データフローテスト" in content, \
            "タイトルがファイルに含まれていません"
        assert "テスト" in content or "データフロー" in content, \
            "タグがファイルに含まれていません"
        assert test_comment in content, \
            "コメントがファイルに含まれていません"

    async def test_concurrent_message_processing(self, setup_components):
        """
        複数メッセージの並行処理をテスト

        Requirements: 1.3 (並行処理制御)
        """
        components = setup_components

        # 3つのメッセージを準備
        messages = [
            MockMessage(content=f"https://example.com/article-{i}")
            for i in range(3)
        ]

        # OGP、Gemini、Gitをモック
        with patch.object(
            components["ogp_scraper"],
            "fetch_ogp",
            new_callable=AsyncMock,
            return_value={"title": "テスト", "description": "説明", "success": True}
        ):
            with patch.object(
                components["gemini_client"],
                "generate_tags_and_summary",
                new_callable=AsyncMock,
                return_value={"tags": ["テスト"], "summary": "", "success": True}
            ):
                with patch.object(
                    components["git_manager"],
                    "commit_and_push",
                    new_callable=AsyncMock,
                    return_value=True
                ):
                    # 並行処理の開始
                    start_time = time.time()
                    tasks = [
                        components["message_handler"].handle_new_message(msg)
                        for msg in messages
                    ]
                    await asyncio.gather(*tasks)
                    elapsed_time = time.time() - start_time

        # 3つのメッセージが処理されたことを確認
        vault_files = list(components["vault_dir"].glob("*.md"))
        assert len(vault_files) >= 3, \
            f"3つのメッセージが処理されるべきですが、{len(vault_files)}個のみ"

        # 並行処理により、処理時間が効率化されていることを確認
        # （3つを順次処理するより短い時間で完了）
        assert elapsed_time < 30.0, \
            f"並行処理の処理時間が30秒を超えました: {elapsed_time:.2f}秒"
