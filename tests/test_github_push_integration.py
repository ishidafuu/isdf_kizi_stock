"""GitHubプッシュフロー統合テスト (Task 11.7)

Requirements 6.1, 6.2, 6.3, 6.5, 6.6 の統合テスト
- コミット作成 → プッシュ成功の確認
- プッシュ失敗時のリトライロジック確認
- ローカルバックアップ作成確認
- テスト用ローカルGitリポジトリを使用
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from git import Repo
from git.exc import GitCommandError

from config.settings import Settings
from src.storage.github import GitManager


@pytest.mark.asyncio
class TestGitHubPushFlowIntegration:
    """GitHubプッシュフロー統合テストクラス"""

    @pytest.fixture
    def setup_test_repo(self, tmp_path):
        """テスト用Gitリポジトリのセットアップ"""
        # テストリポジトリディレクトリを作成
        repo_dir = tmp_path / "test_repo"
        repo_dir.mkdir()

        # Gitリポジトリを初期化
        repo = Repo.init(repo_dir)

        # 初期コミットを作成（空のリポジトリではpushできないため）
        initial_file = repo_dir / "README.md"
        initial_file.write_text("# Test Repository", encoding="utf-8")
        repo.index.add(["README.md"])
        repo.index.commit("Initial commit")

        # articlesディレクトリを作成
        articles_dir = repo_dir / "articles"
        articles_dir.mkdir()

        return {
            "repo_dir": repo_dir,
            "articles_dir": articles_dir,
            "repo": repo
        }

    @pytest.fixture
    def git_manager(self, setup_test_repo, tmp_path):
        """テスト用GitManagerインスタンスを作成"""
        repo_dir = setup_test_repo["repo_dir"]
        log_file = tmp_path / "test.log"

        # Settings をモック化
        with patch('src.storage.github.Settings') as mock_settings:
            mock_settings.OBSIDIAN_VAULT_PATH = str(repo_dir)
            mock_settings.LOG_FILE_PATH = str(log_file)
            mock_settings.GITHUB_TOKEN = "test_token"
            mock_settings.GITHUB_REPO_URL = "https://github.com/test/test.git"
            mock_settings.MAX_RETRY_COUNT = 3

            manager = GitManager(repo_path=repo_dir)
            return manager

    async def test_commit_and_push_success(self, git_manager, setup_test_repo):
        """
        Requirement 6.1, 6.2, 6.3: コミット作成 → プッシュ成功の確認

        Given: テスト用Gitリポジトリと新規ファイル
        When: commit_and_push() を実行
        Then:
        - ファイルがgit addされる
        - コミットが作成される
        - GitHubにプッシュされる
        - True が返される
        """
        # Given: 新規記事ファイルを作成
        articles_dir = setup_test_repo["articles_dir"]
        test_file = articles_dir / "2025-12-04_test_article.md"
        test_file.write_text("# Test Article\n\nTest content", encoding="utf-8")
        commit_message = "Add test article"

        # プッシュ操作をモック化（成功ケース）
        with patch.object(git_manager, '_git_push', return_value=None):
            # When: commit_and_push を実行
            result = await git_manager.commit_and_push(test_file, commit_message)

            # Then: プッシュが成功
            assert result is True

            # コミットが作成されていることを確認
            repo = setup_test_repo["repo"]
            latest_commit = repo.head.commit
            assert commit_message in latest_commit.message

            # ファイルがコミットに含まれていることを確認
            committed_files = [item.path for item in latest_commit.tree.traverse()]
            assert "articles/2025-12-04_test_article.md" in committed_files

    async def test_commit_and_push_multiple_files_sequential(self, git_manager, setup_test_repo):
        """
        Requirement 6.1, 6.2, 6.3: 複数ファイルを順次コミット・プッシュ

        Given: 複数の新規ファイル
        When: 順次 commit_and_push() を実行
        Then: 各ファイルが個別にコミットされ、プッシュされる
        """
        # Given: 複数の記事ファイル
        articles_dir = setup_test_repo["articles_dir"]
        files = [
            (articles_dir / "2025-12-04_article1.md", "Article 1"),
            (articles_dir / "2025-12-04_article2.md", "Article 2"),
            (articles_dir / "2025-12-04_article3.md", "Article 3"),
        ]

        # プッシュ操作をモック化
        with patch.object(git_manager, '_git_push', return_value=None):
            # When: 各ファイルを順次コミット・プッシュ
            for file_path, commit_msg in files:
                file_path.write_text(f"# {commit_msg}\n\nContent", encoding="utf-8")
                result = await git_manager.commit_and_push(file_path, commit_msg)
                assert result is True

            # Then: すべてのファイルがコミットされている
            repo = setup_test_repo["repo"]
            committed_files = [item.path for item in repo.head.commit.tree.traverse()]
            assert "articles/2025-12-04_article1.md" in committed_files
            assert "articles/2025-12-04_article2.md" in committed_files
            assert "articles/2025-12-04_article3.md" in committed_files

    async def test_push_failure_with_retry_success(self, git_manager, setup_test_repo):
        """
        Requirement 6.5: プッシュ失敗後のリトライで成功

        Given: 最初はプッシュ失敗、2回目で成功するシナリオ
        When: commit_and_push() を実行
        Then:
        - 1回目のプッシュは失敗
        - リトライが実行される
        - 2回目のプッシュで成功
        - True が返される
        """
        # Given: 新規ファイル
        articles_dir = setup_test_repo["articles_dir"]
        test_file = articles_dir / "2025-12-04_retry_test.md"
        test_file.write_text("# Retry Test\n\nContent", encoding="utf-8")
        commit_message = "Test retry logic"

        # プッシュ操作をモック化: 1回目失敗、2回目成功
        call_count = 0

        def mock_push():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise GitCommandError("push", "Network error")
            # 2回目は成功

        with patch.object(git_manager, '_git_push', side_effect=mock_push):
            # When: commit_and_push を実行
            result = await git_manager.commit_and_push(test_file, commit_message)

            # Then: プッシュが成功（リトライ後）
            assert result is True
            assert call_count == 2  # 1回目失敗 + 2回目成功

    async def test_push_failure_retry_exhausted(self, git_manager, setup_test_repo):
        """
        Requirement 6.5, 6.6: プッシュが3回失敗してリトライ上限到達

        Given: プッシュが常に失敗するシナリオ
        When: commit_and_push() を実行
        Then:
        - 最大3回のリトライが実行される
        - すべて失敗する
        - False が返される
        - ローカルにファイルはバックアップされている（コミット済み）
        """
        # Given: 新規ファイル
        articles_dir = setup_test_repo["articles_dir"]
        test_file = articles_dir / "2025-12-04_fail_test.md"
        test_file.write_text("# Fail Test\n\nContent", encoding="utf-8")
        commit_message = "Test push failure"

        # プッシュ操作をモック化: すべて失敗
        call_count = 0

        def mock_push_fail():
            nonlocal call_count
            call_count += 1
            raise GitCommandError("push", "Network error")

        with patch.object(git_manager, '_git_push', side_effect=mock_push_fail):
            # When: commit_and_push を実行
            result = await git_manager.commit_and_push(test_file, commit_message)

            # Then: プッシュが失敗
            assert result is False
            assert call_count == 3  # 最大3回リトライ

            # ローカルにコミットは作成されている（バックアップされている）
            repo = setup_test_repo["repo"]
            latest_commit = repo.head.commit
            assert commit_message in latest_commit.message

            # ファイルがローカルリポジトリに存在する
            assert test_file.exists()
            committed_files = [item.path for item in latest_commit.tree.traverse()]
            assert "articles/2025-12-04_fail_test.md" in committed_files

    async def test_push_failure_different_error_types(self, git_manager, setup_test_repo):
        """
        Requirement 6.5, 6.6: 異なるタイプのエラーでもリトライが実行される

        Given: 様々なエラー（GitCommandError、一般Exception）
        When: commit_and_push() を実行
        Then: エラータイプに関わらずリトライが実行される
        """
        # Given: 新規ファイル
        articles_dir = setup_test_repo["articles_dir"]
        test_file = articles_dir / "2025-12-04_error_types.md"
        test_file.write_text("# Error Types Test\n\nContent", encoding="utf-8")
        commit_message = "Test different error types"

        # プッシュ操作をモック化: 異なるエラー、最後は成功
        call_count = 0

        def mock_push_various_errors():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise GitCommandError("push", "Git command failed")
            elif call_count == 2:
                raise Exception("Generic network error")
            # 3回目は成功

        with patch.object(git_manager, '_git_push', side_effect=mock_push_various_errors):
            # When: commit_and_push を実行
            result = await git_manager.commit_and_push(test_file, commit_message)

            # Then: 最終的に成功
            assert result is True
            assert call_count == 3  # 2回失敗 + 1回成功

    async def test_commit_with_article_title_in_message(self, git_manager, setup_test_repo):
        """
        Requirement 6.2: コミットメッセージに記事タイトルを含める

        Given: 記事タイトルを含むコミットメッセージ
        When: commit_and_push() を実行
        Then: コミットメッセージに記事タイトルが含まれる
        """
        # Given: 新規ファイルと記事タイトル
        articles_dir = setup_test_repo["articles_dir"]
        test_file = articles_dir / "2025-12-04_python_tutorial.md"
        test_file.write_text("# Python Tutorial\n\nContent", encoding="utf-8")
        article_title = "Python初心者のためのチュートリアル"
        commit_message = f"Add article: {article_title}"

        # プッシュ操作をモック化
        with patch.object(git_manager, '_git_push', return_value=None):
            # When: commit_and_push を実行
            result = await git_manager.commit_and_push(test_file, commit_message)

            # Then: コミットメッセージに記事タイトルが含まれる
            assert result is True
            repo = setup_test_repo["repo"]
            latest_commit = repo.head.commit
            assert article_title in latest_commit.message
            assert "Add article" in latest_commit.message

    async def test_git_lock_prevents_concurrent_operations(self, git_manager, setup_test_repo):
        """
        Git操作の排他制御: 並行操作が直列化される

        Given: 複数の並行commit_and_push操作
        When: 同時に実行
        Then: asyncio.Lockにより直列化され、競合が発生しない
        """
        # Given: 複数のファイル
        articles_dir = setup_test_repo["articles_dir"]
        files = [
            (articles_dir / f"2025-12-04_concurrent_{i}.md", f"Concurrent {i}")
            for i in range(3)
        ]

        # プッシュ操作をモック化
        with patch.object(git_manager, '_git_push', return_value=None):
            # When: 並行にcommit_and_pushを実行
            tasks = []
            for file_path, commit_msg in files:
                file_path.write_text(f"# {commit_msg}\n\nContent", encoding="utf-8")
                task = git_manager.commit_and_push(file_path, commit_msg)
                tasks.append(task)

            results = await asyncio.gather(*tasks)

            # Then: すべてが成功
            assert all(results)

            # すべてのファイルがコミットされている
            repo = setup_test_repo["repo"]
            committed_files = [item.path for item in repo.head.commit.tree.traverse()]
            for i in range(3):
                assert f"articles/2025-12-04_concurrent_{i}.md" in committed_files

    async def test_local_backup_preserved_on_push_failure(self, git_manager, setup_test_repo):
        """
        Requirement 6.6: プッシュ失敗時にローカルバックアップが保持される

        Given: プッシュが失敗するシナリオ
        When: commit_and_push() を実行
        Then:
        - ローカルリポジトリにコミットが作成される
        - ファイルがローカルに保存される
        - プッシュ失敗後もローカルデータは保持される
        """
        # Given: 新規ファイル
        articles_dir = setup_test_repo["articles_dir"]
        test_file = articles_dir / "2025-12-04_backup_test.md"
        test_content = "# Backup Test\n\nThis should be backed up locally"
        test_file.write_text(test_content, encoding="utf-8")
        commit_message = "Test local backup"

        # プッシュ操作をモック化: すべて失敗
        with patch.object(git_manager, '_git_push', side_effect=GitCommandError("push", "Network error")):
            # When: commit_and_push を実行
            result = await git_manager.commit_and_push(test_file, commit_message)

            # Then: プッシュは失敗
            assert result is False

            # ローカルバックアップが保持される
            # 1. ファイルが存在する
            assert test_file.exists()
            assert test_file.read_text(encoding="utf-8") == test_content

            # 2. コミットが作成されている
            repo = setup_test_repo["repo"]
            latest_commit = repo.head.commit
            assert commit_message in latest_commit.message

            # 3. ファイルがコミットに含まれている
            committed_files = [item.path for item in latest_commit.tree.traverse()]
            assert "articles/2025-12-04_backup_test.md" in committed_files

    async def test_push_with_retry_delay(self, git_manager, setup_test_repo):
        """
        Requirement 6.5: リトライ時に適切な待機時間が設定される

        Given: プッシュが失敗するシナリオ
        When: リトライが実行される
        Then: リトライ間に待機時間が設定される
        """
        import time

        # Given: 新規ファイル
        articles_dir = setup_test_repo["articles_dir"]
        test_file = articles_dir / "2025-12-04_retry_delay.md"
        test_file.write_text("# Retry Delay Test\n\nContent", encoding="utf-8")
        commit_message = "Test retry delay"

        # プッシュ操作をモック化: 2回失敗、3回目成功
        call_count = 0
        call_times = []

        def mock_push_with_timing():
            nonlocal call_count
            call_count += 1
            call_times.append(time.time())
            if call_count < 3:
                raise GitCommandError("push", "Network error")
            # 3回目は成功

        with patch.object(git_manager, '_git_push', side_effect=mock_push_with_timing):
            # When: commit_and_push を実行
            result = await git_manager.commit_and_push(test_file, commit_message)

            # Then: 成功
            assert result is True
            assert call_count == 3

            # リトライ間に待機時間がある（約2秒）
            if len(call_times) >= 2:
                delay1 = call_times[1] - call_times[0]
                assert delay1 >= 1.9  # 約2秒の待機（若干の誤差を許容）

    async def test_commit_message_sanitization(self, git_manager, setup_test_repo):
        """
        Requirement 6.2: コミットメッセージの特殊文字処理

        Given: 特殊文字を含む記事タイトル
        When: commit_and_push() を実行
        Then: コミットメッセージが正常に処理される
        """
        # Given: 特殊文字を含むファイル
        articles_dir = setup_test_repo["articles_dir"]
        test_file = articles_dir / "2025-12-04_special_chars.md"
        test_file.write_text("# Test\n\nContent", encoding="utf-8")
        # 特殊文字を含むコミットメッセージ
        commit_message = "Add article: Python「基礎」&「応用」- 100%理解する"

        # プッシュ操作をモック化
        with patch.object(git_manager, '_git_push', return_value=None):
            # When: commit_and_push を実行
            result = await git_manager.commit_and_push(test_file, commit_message)

            # Then: 成功
            assert result is True
            # コミットメッセージが保持される
            repo = setup_test_repo["repo"]
            latest_commit = repo.head.commit
            assert "Python「基礎」&「応用」" in latest_commit.message


@pytest.mark.asyncio
class TestGitHubPushEdgeCases:
    """GitHubプッシュのエッジケーステスト"""

    @pytest.fixture
    def setup_test_repo(self, tmp_path):
        """テスト用Gitリポジトリのセットアップ"""
        repo_dir = tmp_path / "test_repo"
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)

        # 初期コミット
        initial_file = repo_dir / "README.md"
        initial_file.write_text("# Test", encoding="utf-8")
        repo.index.add(["README.md"])
        repo.index.commit("Initial commit")

        articles_dir = repo_dir / "articles"
        articles_dir.mkdir()

        return {
            "repo_dir": repo_dir,
            "articles_dir": articles_dir,
            "repo": repo
        }

    @pytest.fixture
    def git_manager(self, setup_test_repo, tmp_path):
        """テスト用GitManagerインスタンス"""
        repo_dir = setup_test_repo["repo_dir"]
        log_file = tmp_path / "test.log"

        with patch('src.storage.github.Settings') as mock_settings:
            mock_settings.OBSIDIAN_VAULT_PATH = str(repo_dir)
            mock_settings.LOG_FILE_PATH = str(log_file)
            mock_settings.GITHUB_TOKEN = "test_token"
            mock_settings.GITHUB_REPO_URL = "https://github.com/test/test.git"
            mock_settings.MAX_RETRY_COUNT = 3

            manager = GitManager(repo_path=repo_dir)
            return manager

    async def test_commit_empty_file(self, git_manager, setup_test_repo):
        """空のファイルでもコミット・プッシュできる"""
        # Given: 空のファイル
        articles_dir = setup_test_repo["articles_dir"]
        empty_file = articles_dir / "2025-12-04_empty.md"
        empty_file.write_text("", encoding="utf-8")
        commit_message = "Add empty file"

        # プッシュ操作をモック化
        with patch.object(git_manager, '_git_push', return_value=None):
            # When: commit_and_push を実行
            result = await git_manager.commit_and_push(empty_file, commit_message)

            # Then: 成功
            assert result is True

    async def test_commit_very_long_message(self, git_manager, setup_test_repo):
        """非常に長いコミットメッセージでも処理できる"""
        # Given: 新規ファイルと長いコミットメッセージ
        articles_dir = setup_test_repo["articles_dir"]
        test_file = articles_dir / "2025-12-04_long_message.md"
        test_file.write_text("# Test\n\nContent", encoding="utf-8")
        long_message = "Add article: " + "あ" * 500  # 500文字の長いメッセージ

        # プッシュ操作をモック化
        with patch.object(git_manager, '_git_push', return_value=None):
            # When: commit_and_push を実行
            result = await git_manager.commit_and_push(test_file, long_message)

            # Then: 成功
            assert result is True
            # コミットメッセージが保持される
            repo = setup_test_repo["repo"]
            latest_commit = repo.head.commit
            assert "あ" * 500 in latest_commit.message

    async def test_push_failure_immediate_recovery(self, git_manager, setup_test_repo):
        """
        1回失敗後、即座に成功するケース

        Given: 1回目失敗、2回目成功
        When: リトライが実行される
        Then: 最小限のリトライ回数で成功
        """
        # Given: 新規ファイル
        articles_dir = setup_test_repo["articles_dir"]
        test_file = articles_dir / "2025-12-04_immediate_recovery.md"
        test_file.write_text("# Immediate Recovery\n\nContent", encoding="utf-8")
        commit_message = "Test immediate recovery"

        # プッシュ操作をモック化: 1回失敗、2回目成功
        call_count = 0

        def mock_push_immediate():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise GitCommandError("push", "Temporary failure")
            # 2回目は成功

        with patch.object(git_manager, '_git_push', side_effect=mock_push_immediate):
            # When: commit_and_push を実行
            result = await git_manager.commit_and_push(test_file, commit_message)

            # Then: 成功、リトライ回数は2回
            assert result is True
            assert call_count == 2
