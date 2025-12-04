"""アプリケーション設定

アプリケーション全体で使用する設定値を定義します。
- タイムアウト値
- タグ数
- ファイル命名規則
- 環境変数の読み込み
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# .envファイルを読み込み（プロジェクトルートの.envファイル）
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


class Settings:
    """アプリケーション設定クラス"""

    # ==================== Discord設定 ====================
    DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
    DISCORD_CHANNEL_ID: str = os.getenv("DISCORD_CHANNEL_ID", "")

    # ==================== Gemini API設定 ====================
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # ==================== GitHub設定 ====================
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GITHUB_REPO_URL: str = os.getenv("GITHUB_REPO_URL", "")

    # ==================== Obsidian Vault設定 ====================
    OBSIDIAN_VAULT_PATH: str = os.getenv("OBSIDIAN_VAULT_PATH", "./vault")

    # ==================== ログ設定 ====================
    LOG_FILE_PATH: str = os.getenv("LOG_FILE_PATH", "./logs/article_bot.log")

    # ==================== タイムアウト設定 ====================
    # OGP取得のタイムアウト（秒）
    OGP_TIMEOUT_SECONDS: int = 10

    # Gemini APIのタイムアウト（秒）
    GEMINI_TIMEOUT_SECONDS: int = 30

    # GitHubプッシュのリトライ最大回数
    MAX_RETRY_COUNT: int = 3

    # ==================== タグ設定 ====================
    # 最小タグ数
    MIN_TAG_COUNT: int = 3

    # 最大タグ数
    MAX_TAG_COUNT: int = 5

    # デフォルトタグ（Gemini API失敗時）
    DEFAULT_TAGS: list[str] = ["未分類", "要確認"]

    # ==================== ファイル命名規則 ====================
    # ファイル名の最大長
    MAX_FILENAME_LENGTH: int = 100

    # ファイル名に使用できない文字
    INVALID_FILENAME_CHARS: str = r'/\:*?"<>|'

    # ==================== OGP取得設定 ====================
    # 最大コンテンツサイズ（バイト）
    MAX_CONTENT_SIZE: int = 10 * 1024 * 1024  # 10MB

    # ==================== ログローテーション設定 ====================
    # ログファイルの最大サイズ（バイト）
    MAX_LOG_SIZE: int = 10 * 1024 * 1024  # 10MB

    # ログファイルのバックアップカウント（日数）
    LOG_BACKUP_COUNT: int = 7

    # ==================== 並行処理設定 ====================
    # 最大同時処理数
    MAX_CONCURRENT_MESSAGES: int = 3

    @classmethod
    def validate(cls) -> bool:
        """
        設定値の検証

        Returns:
            bool: すべての必須設定が有効な場合True
        """
        required_vars = [
            "DISCORD_BOT_TOKEN",
            "DISCORD_CHANNEL_ID",
            "GEMINI_API_KEY",
            "GITHUB_TOKEN",
            "GITHUB_REPO_URL",
        ]

        for var in required_vars:
            value = getattr(cls, var, "")
            if not value:
                print(f"警告: {var} が設定されていません")
                return False

        return True

    @classmethod
    def get_vault_articles_path(cls) -> Path:
        """
        Vault内のarticlesディレクトリパスを取得

        Returns:
            Path: articlesディレクトリのパス
        """
        return Path(cls.OBSIDIAN_VAULT_PATH) / "articles"
