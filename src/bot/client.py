"""Discord Bot クライアント

Discord Bot のイベントリスナーと基本機能を提供します。
- メッセージ受信処理
- Bot自身と他のBotのメッセージ除外
- 監視対象チャンネルの制御
- 24時間稼働のための起動処理
"""

import asyncio
import logging
from typing import Optional

import discord
from discord import Client, Intents, Message

from config.settings import Settings
from src.utils.logger import setup_logger


class EventListener(Client):
    """Discord Bot イベントリスナークラス

    discord.py Clientを継承し、メッセージ受信イベントを処理します。
    """

    def __init__(
        self,
        *,
        intents: Intents,
        logger: Optional[logging.Logger] = None,
        **options
    ):
        """
        EventListenerの初期化

        Args:
            intents: Discord Intents設定
            logger: ロガーインスタンス（オプション）
            **options: Clientの追加オプション
        """
        super().__init__(intents=intents, **options)

        # ロガーを設定
        self.logger = logger or setup_logger(
            "EventListener",
            Settings.LOG_FILE_PATH
        )

        # 監視対象チャンネルID
        self.target_channel_id: Optional[int] = None
        if Settings.DISCORD_CHANNEL_ID:
            try:
                self.target_channel_id = int(Settings.DISCORD_CHANNEL_ID)
            except ValueError:
                self.logger.error(
                    f"無効なチャンネルID: {Settings.DISCORD_CHANNEL_ID}"
                )

        # メッセージハンドラ（後で注入される）
        self.message_handler = None

        self.logger.info("EventListenerを初期化しました")

    async def on_ready(self) -> None:
        """
        Bot起動完了時のイベントハンドラ

        Postconditions:
        - Botが正常に起動し、ログインユーザー名が記録される
        - 監視対象チャンネルIDが記録される
        """
        self.logger.info(f"Bot起動完了: {self.user.name} (ID: {self.user.id})")

        if self.target_channel_id:
            self.logger.info(
                f"監視対象チャンネルID: {self.target_channel_id}"
            )
        else:
            self.logger.warning(
                "監視対象チャンネルIDが設定されていません。"
                "すべてのチャンネルを監視します。"
            )

    async def on_message(self, message: Message) -> None:
        """
        メッセージ受信時のイベントハンドラ

        Preconditions:
        - messageが有効なDiscordメッセージオブジェクト

        Postconditions:
        - Bot自身のメッセージと他のBotのメッセージは除外される
        - 監視対象チャンネルのメッセージのみが処理される
        - メッセージハンドラが設定されている場合、処理が委譲される

        Args:
            message: 受信したDiscordメッセージ
        """
        # 1. Bot自身のメッセージを除外
        if message.author == self.user:
            return

        # 2. 他のBotのメッセージを除外（Requirement 1.5）
        if message.author.bot:
            self.logger.debug(
                f"Botメッセージを除外: {message.author.name}"
            )
            return

        # 3. 監視対象チャンネルのチェック
        if self.target_channel_id is not None:
            if message.channel.id != self.target_channel_id:
                self.logger.debug(
                    f"監視対象外のチャンネル: {message.channel.id}"
                )
                return

        # 4. メッセージ情報をログに記録
        self.logger.info(
            f"メッセージ受信: {message.author.name} - "
            f"{message.content[:50]}..."
        )

        # 5. メッセージハンドラに処理を委譲
        if self.message_handler:
            try:
                # スレッド内のメッセージかどうかを判定（Requirement 8.1）
                # message.referenceが存在する場合、スレッドまたはリプライ
                if message.reference and message.reference.message_id:
                    # スレッドコメント処理
                    self.logger.info(
                        f"スレッドコメントとして処理: {message.id}"
                    )
                    await self.message_handler.handle_thread_comment(message)
                else:
                    # 新規メッセージ処理
                    await self.message_handler.handle_new_message(message)
            except Exception as e:
                self.logger.error(
                    f"メッセージ処理中にエラーが発生: {str(e)}",
                    exc_info=True
                )
        else:
            self.logger.warning(
                "メッセージハンドラが設定されていません"
            )

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        """
        エラー発生時のイベントハンドラ

        Args:
            event_method: エラーが発生したイベントメソッド名
            *args: イベントの位置引数
            **kwargs: イベントのキーワード引数
        """
        self.logger.error(
            f"イベント '{event_method}' でエラーが発生しました",
            exc_info=True
        )

    def set_message_handler(self, handler) -> None:
        """
        メッセージハンドラを設定

        Args:
            handler: MessageHandlerインスタンス
        """
        self.message_handler = handler
        self.logger.info("メッセージハンドラを設定しました")

    def run_bot(self, token: str) -> None:
        """
        Botを起動（24時間稼働）

        Preconditions:
        - tokenが有効なDiscord Bot Token

        Args:
            token: Discord Bot Token
        """
        try:
            self.logger.info("Botを起動します...")
            self.run(token)
        except KeyboardInterrupt:
            self.logger.info("Botを手動停止しました")
        except Exception as e:
            self.logger.error(
                f"Bot起動中にエラーが発生: {str(e)}",
                exc_info=True
            )


def create_bot_client(
    logger: Optional[logging.Logger] = None
) -> EventListener:
    """
    Bot クライアントを作成

    Postconditions:
    - メッセージコンテンツの読み取り権限が有効なIntentsが設定される
    - EventListenerインスタンスが返される

    Args:
        logger: ロガーインスタンス（オプション）

    Returns:
        EventListener: Bot クライアントインスタンス
    """
    # Intentsの設定（メッセージコンテンツの読み取りを有効化）
    intents = Intents.default()
    intents.message_content = True
    intents.messages = True
    intents.guilds = True

    # Bot クライアントを作成
    client = EventListener(intents=intents, logger=logger)

    return client
