"""Vaultストレージ

Obsidian VaultへのMarkdownファイル保存を管理します。
- vault/articles/ディレクトリへのファイル保存
- ディレクトリの自動作成
- コメント追記機能
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.settings import Settings
from src.storage.markdown import MarkdownGenerator
from src.utils.logger import log_exception, setup_logger


class VaultStorage:
    """Vaultストレージクラス

    Obsidian Vaultへのファイル保存を管理します。
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        VaultStorageの初期化

        Args:
            logger: ロガーインスタンス（オプション）
        """
        self.logger = logger or setup_logger(
            "VaultStorage",
            Settings.LOG_FILE_PATH
        )

        # Vaultのarticlesディレクトリパスを取得
        self.articles_dir = Settings.get_vault_articles_path()

        # ディレクトリを作成（存在しない場合）（Requirement 5.8）
        self._ensure_directory_exists()

    def _ensure_directory_exists(self) -> None:
        """
        Vaultディレクトリが存在することを確認（Requirement 5.8）

        Postconditions:
        - vault/articles/ディレクトリが存在する
        """
        self.articles_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(
            f"Vaultディレクトリを確認: {self.articles_dir}"
        )

    async def save_article(
        self,
        title: str,
        content: str
    ) -> Path:
        """
        記事をVaultに保存（Requirement 5.8）

        Preconditions:
        - titleが記事タイトル文字列
        - contentがMarkdown形式の文字列

        Postconditions:
        - vault/articles/ディレクトリにMarkdownファイルが保存される
        - ファイルパスが返される

        Args:
            title: 記事タイトル
            content: Markdown形式のコンテンツ

        Returns:
            Path: 保存されたファイルのパス
        """
        try:
            # ファイル名を生成
            filename = MarkdownGenerator.generate_filename(title)
            file_path = self.articles_dir / filename

            # ファイルに書き込み
            file_path.write_text(content, encoding="utf-8")

            self.logger.info(f"記事を保存: {file_path}")
            return file_path

        except Exception as e:
            log_exception(
                self.logger,
                f"記事保存中にエラーが発生: {title}",
                e
            )
            raise

    async def save_memo(self, content: str) -> Path:
        """
        メモをVaultに保存

        Args:
            content: Markdown形式のコンテンツ

        Returns:
            Path: 保存されたファイルのパス
        """
        try:
            # ファイル名を生成（メモは日時ベース）
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            filename = f"{timestamp}_memo.md"
            file_path = self.articles_dir / filename

            # ファイルに書き込み
            file_path.write_text(content, encoding="utf-8")

            self.logger.info(f"メモを保存: {file_path}")
            return file_path

        except Exception as e:
            log_exception(
                self.logger,
                "メモ保存中にエラーが発生",
                e
            )
            raise

    async def append_comment(
        self,
        file_path: Path,
        comment: str
    ) -> None:
        """
        既存ファイルにコメントを追記（Requirement 8.2, 8.3）

        Preconditions:
        - file_pathが有効なファイルパス
        - ファイルが存在する
        - commentがコメント文字列

        Postconditions:
        - ファイルの「## コメント」セクションにコメントが追記される

        Args:
            file_path: 対象ファイルのパス
            comment: 追記するコメント
        """
        try:
            # ファイルが存在するか確認
            if not file_path.exists():
                raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

            # 既存のコンテンツを読み込み
            existing_content = file_path.read_text(encoding="utf-8")

            # コメントセクションを検索
            comment_section_pattern = r"## コメント"

            # 現在日付（YYYY-MM-DD形式）
            created_date = datetime.now().strftime("%Y-%m-%d")

            # コメント追記テキスト
            new_comment = f"\n**{created_date}:**\n{comment}\n"

            # コメントセクションが存在する場合
            if comment_section_pattern in existing_content:
                # 既存のコメントセクションに追記
                updated_content = existing_content.rstrip() + new_comment
            else:
                # コメントセクションを新規作成
                updated_content = existing_content.rstrip() + f"\n\n## コメント\n{new_comment}"

            # ファイルに書き戻し
            file_path.write_text(updated_content, encoding="utf-8")

            self.logger.info(f"コメントを追記: {file_path}")

        except Exception as e:
            log_exception(
                self.logger,
                f"コメント追記中にエラーが発生: {file_path}",
                e
            )
            raise

    def find_article_by_url(self, url: str) -> Optional[Path]:
        """
        URLから該当する記事ファイルを検索

        Args:
            url: 検索するURL

        Returns:
            Optional[Path]: 見つかったファイルのパス（見つからない場合None）
        """
        try:
            # articlesディレクトリ内の全Markdownファイルを検索
            for file_path in self.articles_dir.glob("*.md"):
                content = file_path.read_text(encoding="utf-8")

                # YAMLフロントマター内のURLをチェック
                if f"url: {url}" in content:
                    self.logger.info(f"記事ファイルを発見: {file_path}")
                    return file_path

            self.logger.warning(f"URLに対応する記事が見つかりません: {url}")
            return None

        except Exception as e:
            log_exception(
                self.logger,
                f"記事検索中にエラーが発生: {url}",
                e
            )
            return None
