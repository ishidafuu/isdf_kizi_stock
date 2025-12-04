"""Article Stock Bot - メインエントリーポイント

Discord Bot を起動し、24時間稼働させます。
- 非同期処理の統合
- 並行処理制御（最大3メッセージ同時処理）
- 依存モジュールの初期化と注入
"""

import sys
from pathlib import Path

from config.settings import Settings
from src.ai.gemini import GeminiClient
from src.bot.client import create_bot_client
from src.bot.handlers import MessageHandler
from src.bot.reactions import ReactionManager
from src.scraper.ogp import OGPScraper
from src.storage.github import GitManager
from src.storage.markdown import MarkdownGenerator
from src.storage.vault import VaultStorage
from src.utils.logger import setup_logger
from src.utils.parser import ContentParser


def main() -> None:
    """
    Article Stock Bot のメインエントリーポイント

    Preconditions:
    - .envファイルに必要な環境変数が設定されている
    - Pythonバージョンが3.11以上

    Postconditions:
    - Discord Botが起動し、24時間稼働する
    - メッセージ受信処理が非同期で実行される
    - 並行処理数が最大3に制限される
    """
    # ロガーを初期化
    logger = setup_logger("ArticleStockBot", Settings.LOG_FILE_PATH)

    logger.info("=" * 60)
    logger.info("Article Stock Bot を起動します")
    logger.info("=" * 60)

    # 環境変数の検証
    if not Settings.validate():
        logger.error("必須の環境変数が設定されていません")
        logger.error(".envファイルを確認してください")
        sys.exit(1)

    logger.info("環境変数の検証が完了しました")

    # Vaultディレクトリの作成
    vault_path = Settings.get_vault_articles_path()
    vault_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Vaultディレクトリを確認: {vault_path}")

    # コンポーネントの初期化
    logger.info("コンポーネントを初期化しています...")

    # ReactionManagerの初期化
    reaction_manager = ReactionManager(logger=logger)

    # MessageHandlerの初期化（並行処理制御を含む）
    message_handler = MessageHandler(
        reaction_manager=reaction_manager,
        logger=logger
    )

    # コンポーネントを初期化
    logger.info("依存モジュールを初期化しています...")

    # ContentParser (タスク3.1)
    content_parser = ContentParser()

    # OGPScraper (タスク4.1)
    ogp_scraper = OGPScraper(logger=logger)

    # GeminiClient (タスク5.1)
    gemini_client = GeminiClient(logger=logger)

    # MarkdownGenerator (タスク6.1)
    markdown_generator = MarkdownGenerator()

    # VaultStorage (タスク6.3)
    vault_storage = VaultStorage(logger=logger)

    # GitManager (タスク7.1)
    git_manager = GitManager(logger=logger)

    # MessageHandlerに依存モジュールを注入
    message_handler.set_dependencies(
        content_parser=content_parser,
        ogp_scraper=ogp_scraper,
        gemini_client=gemini_client,
        markdown_generator=markdown_generator,
        vault_storage=vault_storage,
        git_manager=git_manager
    )

    # Discord Bot クライアントの作成
    logger.info("Discord Bot クライアントを作成しています...")
    bot_client = create_bot_client(logger=logger)

    # MessageHandlerをBotクライアントに設定
    bot_client.set_message_handler(message_handler)

    logger.info("初期化が完了しました")
    logger.info(f"並行処理最大数: {Settings.MAX_CONCURRENT_MESSAGES}")
    logger.info(f"監視対象チャンネルID: {Settings.DISCORD_CHANNEL_ID}")

    # Botを起動（24時間稼働）
    try:
        logger.info("Botを起動します...")
        bot_client.run_bot(Settings.DISCORD_BOT_TOKEN)
    except KeyboardInterrupt:
        logger.info("Botを手動停止しました")
    except Exception as e:
        logger.error(f"Botの起動中にエラーが発生しました: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
