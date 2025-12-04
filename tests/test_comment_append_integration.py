"""コメント追記フロー統合テスト (Task 10.2)

スレッド検出からファイル更新、GitHubプッシュまでの一連の流れをテストします。
- スレッドの親メッセージからファイルを特定
- git pullで最新版を取得
- コメント追記
- git pushで再プッシュ
- ファイル特定失敗時のエラーハンドリング
- Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.bot.handlers import MessageHandler
from src.bot.reactions import ReactionManager
from src.storage.github import GitManager
from src.storage.vault import VaultStorage
from src.utils.parser import ContentParser


class MockMessageReference:
    """Discord MessageReferenceのモック"""

    def __init__(self, message_id: int):
        self.message_id = message_id


class MockChannel:
    """Discord Channelのモック"""

    def __init__(self, parent_message_content: str):
        self.id = 987654321
        self._parent_message_content = parent_message_content

    async def fetch_message(self, message_id: int):
        """親メッセージを返す"""
        return MockParentMessage(self._parent_message_content, message_id)


class MockParentMessage:
    """親メッセージのモック"""

    def __init__(self, content: str, message_id: int = 111111111):
        self.content = content
        self.id = message_id
        self.author = Mock()
        self.author.name = "TestUser"
        self.author.bot = False


class MockThreadMessage:
    """スレッド内メッセージのモック"""

    def __init__(
        self,
        content: str,
        parent_message_content: str,
        message_id: int = 222222222,
        parent_message_id: int = 111111111
    ):
        self.content = content
        self.id = message_id
        self.author = Mock()
        self.author.name = "TestUser"
        self.author.bot = False

        # スレッドの親メッセージへの参照
        self.reference = MockMessageReference(parent_message_id)

        # チャンネルのモック
        self.channel = MockChannel(parent_message_content)

        # reply()とadd_reaction()をAsyncMockに設定
        self.reply = AsyncMock()
        self.add_reaction = AsyncMock()


@pytest.mark.asyncio
class TestCommentAppendFlowIntegration:
    """コメント追記フロー統合テストクラス"""

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

        # Settingsをリロード
        from config import settings
        import importlib
        importlib.reload(settings)

        # コンポーネントの初期化
        content_parser = ContentParser()
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
            vault_storage=vault_storage,
            git_manager=git_manager
        )

        return {
            "message_handler": message_handler,
            "vault_storage": vault_storage,
            "vault_dir": vault_storage.articles_dir,
            "git_manager": git_manager,
            "content_parser": content_parser,
        }

    async def test_successful_comment_append_flow(self, setup_components):
        """
        コメント追記の正常フローをテスト

        Requirements: 8.1, 8.2, 8.3, 8.4, 8.5

        フロー:
        1. スレッドメッセージを受信
        2. 親メッセージからURLを抽出
        3. URLから該当ファイルを特定
        4. git pullで最新版を取得
        5. コメントを追記
        6. git pushで再プッシュ
        7. 成功リアクションを追加
        """
        components = setup_components

        # テスト用の記事ファイルを事前に作成
        test_url = "https://example.com/test-article"
        test_article_content = f"""---
tags: [Python, テスト]
url: {test_url}
created: 2025-12-04
---

# テスト記事タイトル

## 概要

これはテスト記事の説明文です。

## コメント

**2025-12-04:**
初回コメントです。
"""
        # ファイルを保存
        test_file_path = components["vault_dir"] / "2025-12-04_テスト記事タイトル.md"
        test_file_path.write_text(test_article_content, encoding="utf-8")

        # 親メッセージの内容（URLを含む）
        parent_message_content = f"{test_url} これは元の投稿です"

        # スレッド内のコメントメッセージ
        thread_comment = "これは追加コメントです。とても参考になりました。"
        mock_thread_message = MockThreadMessage(
            content=thread_comment,
            parent_message_content=parent_message_content
        )

        # git pull と git push をモック
        with patch.object(
            components["git_manager"],
            "pull_latest",
            new_callable=AsyncMock
        ) as mock_git_pull:
            mock_git_pull.return_value = True

            with patch.object(
                components["git_manager"],
                "commit_and_push",
                new_callable=AsyncMock
            ) as mock_git_push:
                mock_git_push.return_value = True

                # コメント追記フロー実行
                await components["message_handler"].handle_thread_comment(
                    mock_thread_message
                )

        # Requirement 8.2: git pullが実行されたことを確認
        mock_git_pull.assert_called_once()

        # Requirement 8.3: コメントが追記されたことを確認
        updated_content = test_file_path.read_text(encoding="utf-8")
        assert thread_comment in updated_content, \
            "コメントがファイルに追記されていません"

        # 日付フォーマットの確認
        today = datetime.now().strftime("%Y-%m-%d")
        assert f"**{today}:**" in updated_content, \
            "コメントに日付が含まれていません"

        # Requirement 8.4: git pushが実行されたことを確認
        mock_git_push.assert_called_once()

        # Requirement 8.5: 成功リアクションが追加されたことを確認
        mock_thread_message.add_reaction.assert_called_once()

    async def test_file_not_found_error_handling(self, setup_components):
        """
        ファイル特定失敗時のエラーハンドリングをテスト

        Requirements: 8.6

        シナリオ:
        - 親メッセージにURLが含まれているが、対応するファイルが存在しない
        - エラーメッセージが返信される
        """
        components = setup_components

        # 存在しないURLを含む親メッセージ
        parent_message_content = "https://example.com/non-existent-article"
        thread_comment = "このファイルは存在しません"

        mock_thread_message = MockThreadMessage(
            content=thread_comment,
            parent_message_content=parent_message_content
        )

        # コメント追記フロー実行
        await components["message_handler"].handle_thread_comment(
            mock_thread_message
        )

        # Requirement 8.6: エラーメッセージが返信されたことを確認
        mock_thread_message.reply.assert_called_once()

        # エラーメッセージの内容を確認
        reply_call_args = mock_thread_message.reply.call_args
        error_message = reply_call_args.args[0]
        assert "見つかりませんでした" in error_message or "見つかりません" in error_message, \
            "ファイル未発見のエラーメッセージが返信されていません"

    async def test_parent_message_without_url(self, setup_components):
        """
        親メッセージにURLが含まれていない場合のエラーハンドリングをテスト

        Requirements: 8.6

        シナリオ:
        - 親メッセージがテキストのみ（URL無し）
        - エラーメッセージが返信される
        """
        components = setup_components

        # URL無しの親メッセージ
        parent_message_content = "これはメモです。URLは含まれていません。"
        thread_comment = "追加コメントを試みます"

        mock_thread_message = MockThreadMessage(
            content=thread_comment,
            parent_message_content=parent_message_content
        )

        # コメント追記フロー実行
        await components["message_handler"].handle_thread_comment(
            mock_thread_message
        )

        # エラーメッセージが返信されたことを確認
        mock_thread_message.reply.assert_called_once()

        # エラーメッセージの内容を確認
        reply_call_args = mock_thread_message.reply.call_args
        error_message = reply_call_args.args[0]
        assert "URLが含まれていません" in error_message or "URL" in error_message, \
            "URL不在のエラーメッセージが返信されていません"

    async def test_git_pull_failure_continues_processing(self, setup_components):
        """
        git pull失敗時も処理が継続されることをテスト

        Requirements: 8.2

        シナリオ:
        - git pullが失敗しても、処理が継続される
        - コメント追記とpushは実行される
        """
        components = setup_components

        # テスト用の記事ファイルを事前に作成
        test_url = "https://example.com/test-article-pull-fail"
        test_article_content = f"""---
tags: [テスト]
url: {test_url}
created: 2025-12-04
---

# テスト記事

## 概要

説明文

## コメント

**2025-12-04:**
初回コメント
"""
        test_file_path = components["vault_dir"] / "2025-12-04_テスト記事.md"
        test_file_path.write_text(test_article_content, encoding="utf-8")

        parent_message_content = test_url
        thread_comment = "pull失敗でも追記されるべき"

        mock_thread_message = MockThreadMessage(
            content=thread_comment,
            parent_message_content=parent_message_content
        )

        # git pull失敗のモック
        with patch.object(
            components["git_manager"],
            "pull_latest",
            new_callable=AsyncMock
        ) as mock_git_pull:
            mock_git_pull.return_value = False  # pull失敗

            with patch.object(
                components["git_manager"],
                "commit_and_push",
                new_callable=AsyncMock
            ) as mock_git_push:
                mock_git_push.return_value = True

                # コメント追記フロー実行
                await components["message_handler"].handle_thread_comment(
                    mock_thread_message
                )

        # git pullは実行されたが失敗した
        mock_git_pull.assert_called_once()

        # それでもコメントは追記される
        updated_content = test_file_path.read_text(encoding="utf-8")
        assert thread_comment in updated_content, \
            "git pull失敗時もコメントが追記されるべきです"

        # git pushも実行される
        mock_git_push.assert_called_once()

    async def test_git_push_failure_handling(self, setup_components):
        """
        git push失敗時のエラーハンドリングをテスト

        Requirements: 8.4

        シナリオ:
        - コメント追記は成功するが、git pushが失敗する
        - ファイルはローカルに保存される
        """
        components = setup_components

        # テスト用の記事ファイルを事前に作成
        test_url = "https://example.com/test-article-push-fail"
        test_article_content = f"""---
tags: [テスト]
url: {test_url}
created: 2025-12-04
---

# テスト記事

## 概要

説明文
"""
        test_file_path = components["vault_dir"] / "2025-12-04_テスト記事_push.md"
        test_file_path.write_text(test_article_content, encoding="utf-8")

        parent_message_content = test_url
        thread_comment = "push失敗でもローカルには保存"

        mock_thread_message = MockThreadMessage(
            content=thread_comment,
            parent_message_content=parent_message_content
        )

        # git pull成功、git push失敗のモック
        with patch.object(
            components["git_manager"],
            "pull_latest",
            new_callable=AsyncMock
        ) as mock_git_pull:
            mock_git_pull.return_value = True

            with patch.object(
                components["git_manager"],
                "commit_and_push",
                new_callable=AsyncMock
            ) as mock_git_push:
                mock_git_push.return_value = False  # push失敗

                # コメント追記フロー実行
                await components["message_handler"].handle_thread_comment(
                    mock_thread_message
                )

        # コメントはローカルに保存されている
        updated_content = test_file_path.read_text(encoding="utf-8")
        assert thread_comment in updated_content, \
            "git push失敗時もコメントはローカルに保存されるべきです"

        # push失敗時もリアクションは追加される（ローカル保存成功）
        mock_thread_message.add_reaction.assert_called_once()

    async def test_multiple_comments_append(self, setup_components):
        """
        複数回のコメント追記をテスト

        Requirements: 8.2, 8.3

        シナリオ:
        - 同じ記事に複数回コメントを追記
        - すべてのコメントが時系列順に保存される
        """
        components = setup_components

        # テスト用の記事ファイルを事前に作成
        test_url = "https://example.com/test-article-multiple"
        test_article_content = f"""---
tags: [テスト]
url: {test_url}
created: 2025-12-04
---

# テスト記事

## 概要

説明文

## コメント

**2025-12-04:**
初回コメント
"""
        test_file_path = components["vault_dir"] / "2025-12-04_テスト記事_multiple.md"
        test_file_path.write_text(test_article_content, encoding="utf-8")

        parent_message_content = test_url

        # 3つのコメントを順次追記
        comments = [
            "1つ目の追加コメント",
            "2つ目の追加コメント",
            "3つ目の追加コメント"
        ]

        # git操作をモック
        with patch.object(
            components["git_manager"],
            "pull_latest",
            new_callable=AsyncMock,
            return_value=True
        ):
            with patch.object(
                components["git_manager"],
                "commit_and_push",
                new_callable=AsyncMock,
                return_value=True
            ):
                for comment in comments:
                    mock_thread_message = MockThreadMessage(
                        content=comment,
                        parent_message_content=parent_message_content
                    )

                    await components["message_handler"].handle_thread_comment(
                        mock_thread_message
                    )

        # すべてのコメントが追記されていることを確認
        final_content = test_file_path.read_text(encoding="utf-8")

        for comment in comments:
            assert comment in final_content, \
                f"コメント '{comment}' が追記されていません"

        # コメントが時系列順に並んでいることを確認
        # (初回コメント → 1つ目 → 2つ目 → 3つ目)
        assert "初回コメント" in final_content
        assert final_content.index("初回コメント") < final_content.index("1つ目の追加コメント")
        assert final_content.index("1つ目の追加コメント") < final_content.index("2つ目の追加コメント")
        assert final_content.index("2つ目の追加コメント") < final_content.index("3つ目の追加コメント")

    async def test_comment_append_with_special_characters(self, setup_components):
        """
        特殊文字を含むコメント追記をテスト

        Requirements: 8.3

        シナリオ:
        - 特殊文字（改行、記号、絵文字など）を含むコメントを追記
        - 正しくエスケープされて保存される
        """
        components = setup_components

        # テスト用の記事ファイルを事前に作成
        test_url = "https://example.com/test-article-special"
        test_article_content = f"""---
tags: [テスト]
url: {test_url}
created: 2025-12-04
---

# テスト記事

## 概要

説明文
"""
        test_file_path = components["vault_dir"] / "2025-12-04_テスト記事_special.md"
        test_file_path.write_text(test_article_content, encoding="utf-8")

        parent_message_content = test_url

        # 特殊文字を含むコメント
        special_comment = """これは特殊文字を含むコメントです:
- 改行あり
- 記号: !@#$%^&*()
- 絵文字: 👍 🎉 🚀
- Markdownリンク: [リンク](https://example.com)"""

        mock_thread_message = MockThreadMessage(
            content=special_comment,
            parent_message_content=parent_message_content
        )

        # git操作をモック
        with patch.object(
            components["git_manager"],
            "pull_latest",
            new_callable=AsyncMock,
            return_value=True
        ):
            with patch.object(
                components["git_manager"],
                "commit_and_push",
                new_callable=AsyncMock,
                return_value=True
            ):
                await components["message_handler"].handle_thread_comment(
                    mock_thread_message
                )

        # 特殊文字が正しく保存されていることを確認
        updated_content = test_file_path.read_text(encoding="utf-8")
        assert "改行あり" in updated_content
        assert "!@#$%^&*()" in updated_content
        assert "👍" in updated_content or "🎉" in updated_content
        assert "[リンク]" in updated_content
