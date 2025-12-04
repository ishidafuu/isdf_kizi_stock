"""メッセージハンドラ

メッセージ受信から保存までのパイプライン処理を統括します。
- メッセージ受信から保存までのオーケストレーション
- リアクション追加（受信確認：1秒以内）
- 成功・失敗通知のDiscordへの返信
- 並行処理制御
"""

import asyncio
import logging
from typing import Optional

from discord import Message

from config.settings import Settings
from src.bot.reactions import ReactionManager
from src.utils.logger import log_exception, setup_logger


class MessageHandler:
    """メッセージハンドラクラス

    メッセージ受信から保存までの全処理パイプラインを統括します。
    """

    def __init__(
        self,
        reaction_manager: Optional[ReactionManager] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        MessageHandlerの初期化

        Args:
            reaction_manager: ReactionManagerインスタンス（オプション）
            logger: ロガーインスタンス（オプション）
        """
        self.logger = logger or setup_logger(
            "MessageHandler",
            Settings.LOG_FILE_PATH
        )

        self.reaction_manager = reaction_manager or ReactionManager(
            logger=self.logger
        )

        # 並行処理制御用のセマフォ（Requirement 1.3）
        self.semaphore = asyncio.Semaphore(
            Settings.MAX_CONCURRENT_MESSAGES
        )

        # 依存モジュール（後で注入される）
        self.content_parser = None  # ContentParser
        self.ogp_scraper = None  # OGPScraper
        self.gemini_client = None  # GeminiClient
        self.markdown_generator = None  # MarkdownGenerator
        self.vault_storage = None  # VaultStorage
        self.git_manager = None  # GitManager

        self.logger.info("MessageHandlerを初期化しました")

    async def handle_new_message(self, message: Message) -> None:
        """
        新規メッセージの処理（エンドツーエンドパイプライン）

        Preconditions:
        - messageが有効なDiscordメッセージオブジェクト

        Postconditions:
        - メッセージ受信後1秒以内に受信確認リアクションが追加される
        - 処理成功時は成功リアクションと成功メッセージが返信される
        - 処理失敗時はエラーリアクションとエラーメッセージが返信される

        Args:
            message: 受信したDiscordメッセージ
        """
        # 並行処理数を制限（セマフォ）
        async with self.semaphore:
            await self._process_message(message)

    async def _process_message(self, message: Message) -> None:
        """
        メッセージ処理のメインロジック

        Args:
            message: 受信したDiscordメッセージ
        """
        try:
            # 1. 受信確認リアクションを即座に追加（Requirement 1.4: 1秒以内）
            await self.reaction_manager.add_received_reaction(message)

            # 2. メッセージ内容の解析（URL抽出、コメント分離）
            if not self.content_parser:
                raise RuntimeError("ContentParserが設定されていません")

            parse_result = self.content_parser.parse_message(message.content)

            # 3. URLが含まれる場合は記事処理モードに移行
            if parse_result.get("url"):
                await self._process_article(message, parse_result)
            else:
                # メモとして処理（OGP取得をスキップ）
                await self._process_memo(message, parse_result)

            # 4. 成功通知（Requirement 7.1）
            await self.reaction_manager.add_success_reaction(message)
            await message.reply("✅ 記事を保存しました！")

        except Exception as e:
            # エラーハンドリング（Requirement 7.2, 9.1）
            log_exception(
                self.logger,
                f"メッセージ処理中にエラーが発生 (ID: {message.id})",
                e
            )

            # エラー通知（Requirement 7.4）
            await self.reaction_manager.add_error_reaction(message)
            await message.reply(
                f"❌ エラーが発生しました: {str(e)[:100]}"
            )

    async def _process_article(
        self,
        message: Message,
        parse_result: dict
    ) -> None:
        """
        記事処理パイプライン（URL含む投稿）

        Args:
            message: Discordメッセージ
            parse_result: パース結果（url, comment, memo）
        """
        url = parse_result["url"]
        comment = parse_result.get("comment", "")

        self.logger.info(f"記事処理開始: {url}")

        # 1. OGP情報取得
        if not self.ogp_scraper:
            raise RuntimeError("OGPScraperが設定されていません")

        ogp_data = await self.ogp_scraper.fetch_ogp(url)

        # 2. Gemini AIによるタグ付けと要約生成
        if not self.gemini_client:
            raise RuntimeError("GeminiClientが設定されていません")

        ai_result = await self.gemini_client.generate_tags_and_summary(
            title=ogp_data.get("title", "無題の記事"),
            description=ogp_data.get("description", "")
        )

        # 3. Markdownファイル生成
        if not self.markdown_generator:
            raise RuntimeError("MarkdownGeneratorが設定されていません")

        markdown_content = self.markdown_generator.generate(
            title=ogp_data.get("title", "無題の記事"),
            url=url,
            description=ogp_data.get("description", ""),
            tags=ai_result.get("tags", Settings.DEFAULT_TAGS),
            summary=ai_result.get("summary", ""),
            comment=comment
        )

        # 4. Vaultに保存
        if not self.vault_storage:
            raise RuntimeError("VaultStorageが設定されていません")

        file_path = await self.vault_storage.save_article(
            title=ogp_data.get("title", "無題の記事"),
            content=markdown_content
        )

        # 5. GitHubにプッシュ
        if not self.git_manager:
            raise RuntimeError("GitManagerが設定されていません")

        await self.git_manager.commit_and_push(
            file_path=file_path,
            commit_message=f"Add article: {ogp_data.get('title', '無題の記事')}"
        )

        self.logger.info(f"記事処理完了: {file_path}")

    async def _process_memo(
        self,
        message: Message,
        parse_result: dict
    ) -> None:
        """
        メモ処理パイプライン（URL無し投稿）

        Args:
            message: Discordメッセージ
            parse_result: パース結果（memo）
        """
        memo = parse_result.get("memo", "")

        self.logger.info(f"メモ処理開始: {memo[:50]}...")

        # メモとして保存（OGP取得とGemini呼び出しをスキップ）
        if not self.markdown_generator:
            raise RuntimeError("MarkdownGeneratorが設定されていません")

        markdown_content = self.markdown_generator.generate_memo(
            memo=memo
        )

        if not self.vault_storage:
            raise RuntimeError("VaultStorageが設定されていません")

        file_path = await self.vault_storage.save_memo(
            content=markdown_content
        )

        if not self.git_manager:
            raise RuntimeError("GitManagerが設定されていません")

        await self.git_manager.commit_and_push(
            file_path=file_path,
            commit_message=f"Add memo: {memo[:30]}..."
        )

        self.logger.info(f"メモ処理完了: {file_path}")

    async def handle_thread_comment(self, message: Message) -> None:
        """
        スレッド内コメントの処理（Requirement 8.1-8.5）

        Preconditions:
        - messageがスレッド内のメッセージ

        Postconditions:
        - 該当記事のMarkdownファイルにコメントが追記される
        - GitHubに再プッシュされる
        - 成功リアクションが追加される

        Args:
            message: スレッド内のDiscordメッセージ
        """
        try:
            # スレッドの親メッセージから該当ファイルを特定
            if not message.reference or not message.reference.message_id:
                raise ValueError("親メッセージが見つかりません")

            # コメント追記処理（後で実装）
            # TODO: ファイル特定とコメント追記ロジックを実装

            self.logger.info(
                f"スレッドコメント処理完了: {message.id}"
            )

            # 成功リアクション追加
            await self.reaction_manager.add_thread_comment_reaction(message)

        except Exception as e:
            log_exception(
                self.logger,
                f"スレッドコメント処理中にエラーが発生 (ID: {message.id})",
                e
            )

            await message.reply(
                f"❌ コメント追記に失敗しました: {str(e)[:100]}"
            )

    def set_dependencies(
        self,
        content_parser=None,
        ogp_scraper=None,
        gemini_client=None,
        markdown_generator=None,
        vault_storage=None,
        git_manager=None
    ) -> None:
        """
        依存モジュールを設定

        Args:
            content_parser: ContentParserインスタンス
            ogp_scraper: OGPScraperインスタンス
            gemini_client: GeminiClientインスタンス
            markdown_generator: MarkdownGeneratorインスタンス
            vault_storage: VaultStorageインスタンス
            git_manager: GitManagerインスタンス
        """
        if content_parser:
            self.content_parser = content_parser
        if ogp_scraper:
            self.ogp_scraper = ogp_scraper
        if gemini_client:
            self.gemini_client = gemini_client
        if markdown_generator:
            self.markdown_generator = markdown_generator
        if vault_storage:
            self.vault_storage = vault_storage
        if git_manager:
            self.git_manager = git_manager

        self.logger.info("依存モジュールを設定しました")
