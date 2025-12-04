"""GitHub同期

GitPythonを使用したGit操作とGitHub同期を管理します。
- Git add、commit、pushの自動化
- 排他制御による競合回避
- リトライ処理とエラーハンドリング
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from git import Repo
from git.exc import GitCommandError

from config.settings import Settings
from src.utils.logger import log_exception, setup_logger


class GitManager:
    """GitManager クラス

    Gitリポジトリ操作とGitHub同期を管理します。
    """

    def __init__(
        self,
        repo_path: Optional[Path] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        GitManagerの初期化

        Args:
            repo_path: Gitリポジトリのパス（デフォルト: vault_path）
            logger: ロガーインスタンス（オプション）
        """
        self.logger = logger or setup_logger(
            "GitManager",
            Settings.LOG_FILE_PATH
        )

        # Gitリポジトリのパス
        self.repo_path = repo_path or Path(Settings.OBSIDIAN_VAULT_PATH)

        # GitPythonのRepoオブジェクト
        try:
            self.repo = Repo(self.repo_path)
            self.logger.info(f"Gitリポジトリを初期化: {self.repo_path}")
        except Exception as e:
            log_exception(
                self.logger,
                f"Gitリポジトリの初期化に失敗: {self.repo_path}",
                e
            )
            raise

        # Git操作の排他制御用ロック（Requirement 6.1, 6.2, 6.3）
        self._git_lock = asyncio.Lock()

        # GitHub Personal Access Tokenを設定（Requirement 6.4）
        self._setup_github_auth()

    def _setup_github_auth(self) -> None:
        """
        GitHub Personal Access Token認証を設定（Requirement 6.4）

        Postconditions:
        - リモートURLにアクセストークンが含まれる
        """
        try:
            if not Settings.GITHUB_TOKEN or not Settings.GITHUB_REPO_URL:
                self.logger.warning(
                    "GitHub TokenまたはRepo URLが設定されていません"
                )
                return

            # リモートURLにトークンを埋め込む
            # 例: https://token@github.com/user/repo.git
            repo_url = Settings.GITHUB_REPO_URL
            if "github.com" in repo_url:
                # https://github.com/user/repo.git -> https://token@github.com/user/repo.git
                authenticated_url = repo_url.replace(
                    "https://github.com",
                    f"https://{Settings.GITHUB_TOKEN}@github.com"
                )

                # リモートURLを更新
                if "origin" in self.repo.remotes:
                    origin = self.repo.remote("origin")
                    origin.set_url(authenticated_url)
                    self.logger.info("GitHub認証を設定しました")
                else:
                    self.logger.warning("リモート 'origin' が見つかりません")

        except Exception as e:
            log_exception(
                self.logger,
                "GitHub認証設定中にエラーが発生",
                e
            )

    async def commit_and_push(
        self,
        file_path: Path,
        commit_message: str
    ) -> bool:
        """
        ファイルをコミットしてGitHubにプッシュ（Requirement 6.1-6.7）

        Preconditions:
        - file_pathが有効なファイルパス
        - ファイルがGitリポジトリ内に存在する
        - commit_messageがコミットメッセージ文字列

        Postconditions:
        - ファイルがgit addされる
        - コミットが作成される
        - GitHubにプッシュされる
        - プッシュ失敗時は最大3回リトライされる

        Args:
            file_path: コミットするファイルのパス
            commit_message: コミットメッセージ

        Returns:
            bool: プッシュ成功時True、失敗時False
        """
        # 排他制御（Requirement 6.1, 6.2, 6.3）
        async with self._git_lock:
            return await self._commit_and_push_internal(
                file_path,
                commit_message
            )

    async def _commit_and_push_internal(
        self,
        file_path: Path,
        commit_message: str
    ) -> bool:
        """
        コミットとプッシュの内部実装

        Args:
            file_path: コミットするファイルのパス
            commit_message: コミットメッセージ

        Returns:
            bool: プッシュ成功時True、失敗時False
        """
        try:
            # Git操作を非同期化（Requirement 6.2）
            await asyncio.to_thread(self._git_add, file_path)
            await asyncio.to_thread(self._git_commit, commit_message)

            # プッシュをリトライ付きで実行（Requirement 6.5）
            push_success = await self._push_with_retry()

            if push_success:
                self.logger.info(
                    f"GitHubプッシュ成功: {commit_message}"
                )
                return True
            else:
                # リトライ失敗時のバックアップ処理（Requirement 6.6）
                self.logger.error(
                    f"GitHubプッシュ失敗（リトライ上限到達）: {commit_message}"
                )
                return False

        except Exception as e:
            log_exception(
                self.logger,
                f"commit_and_push中にエラーが発生: {commit_message}",
                e
            )
            return False

    def _git_add(self, file_path: Path) -> None:
        """
        git add を実行（Requirement 6.1）

        Args:
            file_path: 追加するファイルのパス
        """
        # ファイルパスを相対パスに変換
        relative_path = file_path.relative_to(self.repo_path)

        # git add
        self.repo.index.add([str(relative_path)])
        self.logger.info(f"git add: {relative_path}")

    def _git_commit(self, commit_message: str) -> None:
        """
        git commit を実行（Requirement 6.2）

        Args:
            commit_message: コミットメッセージ
        """
        self.repo.index.commit(commit_message)
        self.logger.info(f"git commit: {commit_message}")

    async def _push_with_retry(self) -> bool:
        """
        プッシュをリトライ付きで実行（Requirement 6.5, 6.6, 6.7）

        Postconditions:
        - プッシュが成功するか、最大3回リトライされる
        - 成功時はTrueを返す
        - 失敗時はFalseを返す

        Returns:
            bool: プッシュ成功時True、失敗時False
        """
        max_retries = Settings.MAX_RETRY_COUNT

        for attempt in range(1, max_retries + 1):
            try:
                self.logger.info(f"GitHubプッシュ試行 {attempt}/{max_retries}")

                # git push を非同期で実行
                await asyncio.to_thread(self._git_push)

                self.logger.info("GitHubプッシュ成功")
                return True

            except GitCommandError as e:
                log_exception(
                    self.logger,
                    f"GitHubプッシュ失敗（試行 {attempt}/{max_retries}）",
                    e
                )

                # 最後の試行でなければ少し待つ
                if attempt < max_retries:
                    await asyncio.sleep(2)

            except Exception as e:
                log_exception(
                    self.logger,
                    f"GitHubプッシュ中に予期しないエラー（試行 {attempt}/{max_retries}）",
                    e
                )

                if attempt < max_retries:
                    await asyncio.sleep(2)

        # 全てのリトライが失敗
        self.logger.error(
            f"GitHubプッシュが{max_retries}回失敗しました"
        )
        return False

    def _git_push(self) -> None:
        """
        git push を実行（Requirement 6.3）
        """
        origin = self.repo.remote("origin")
        origin.push()
        self.logger.info("git push実行")

    async def pull_latest(self) -> bool:
        """
        最新版をgit pullで取得（Requirement 8.2）

        Postconditions:
        - リモートの最新版がローカルにマージされる

        Returns:
            bool: pull成功時True、失敗時False
        """
        try:
            # 排他制御
            async with self._git_lock:
                self.logger.info("git pull実行")

                # git pull を非同期で実行
                await asyncio.to_thread(self._git_pull)

                self.logger.info("git pull成功")
                return True

        except Exception as e:
            log_exception(
                self.logger,
                "git pull中にエラーが発生",
                e
            )
            return False

    def _git_pull(self) -> None:
        """
        git pull を実行
        """
        origin = self.repo.remote("origin")
        origin.pull()
