"""リアクション管理

Discordメッセージへのリアクション追加機能を提供します。
- 受信確認リアクション（👁️）
- 成功リアクション（✅）
- リアクション追加失敗時のエラーハンドリング
"""

import logging
from typing import Optional

from discord import Message

from src.utils.logger import log_exception, setup_logger


class ReactionManager:
    """リアクション管理クラス

    Discordメッセージにリアクションを追加する機能を提供します。
    """

    # リアクション絵文字定数
    REACTION_RECEIVED = "👁️"  # 受信確認
    REACTION_SUCCESS = "✅"  # 処理成功
    REACTION_ERROR = "❌"  # 処理失敗

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        ReactionManagerの初期化

        Args:
            logger: ロガーインスタンス（オプション）
        """
        self.logger = logger or setup_logger(
            "ReactionManager",
            "logs/article_bot.log"
        )

    async def add_received_reaction(self, message: Message) -> bool:
        """
        受信確認リアクションを追加（Requirement 1.4）

        Preconditions:
        - messageが有効なDiscordメッセージオブジェクト

        Postconditions:
        - メッセージに👁️リアクションが追加される
        - 成功時はTrueを返す
        - 失敗時はエラーログを記録しFalseを返す

        Args:
            message: 対象のDiscordメッセージ

        Returns:
            bool: リアクション追加成功時True、失敗時False
        """
        try:
            await message.add_reaction(self.REACTION_RECEIVED)
            self.logger.info(
                f"受信確認リアクションを追加: {message.id}"
            )
            return True
        except Exception as e:
            log_exception(
                self.logger,
                f"受信確認リアクション追加失敗 (メッセージID: {message.id})",
                e
            )
            return False

    async def add_success_reaction(self, message: Message) -> bool:
        """
        成功リアクションを追加（Requirement 7.5）

        Preconditions:
        - messageが有効なDiscordメッセージオブジェクト

        Postconditions:
        - メッセージに✅リアクションが追加される
        - 成功時はTrueを返す
        - 失敗時はエラーログを記録しFalseを返す

        Args:
            message: 対象のDiscordメッセージ

        Returns:
            bool: リアクション追加成功時True、失敗時False
        """
        try:
            await message.add_reaction(self.REACTION_SUCCESS)
            self.logger.info(
                f"成功リアクションを追加: {message.id}"
            )
            return True
        except Exception as e:
            log_exception(
                self.logger,
                f"成功リアクション追加失敗 (メッセージID: {message.id})",
                e
            )
            return False

    async def add_error_reaction(self, message: Message) -> bool:
        """
        エラーリアクションを追加

        Preconditions:
        - messageが有効なDiscordメッセージオブジェクト

        Postconditions:
        - メッセージに❌リアクションが追加される
        - 成功時はTrueを返す
        - 失敗時はエラーログを記録しFalseを返す

        Args:
            message: 対象のDiscordメッセージ

        Returns:
            bool: リアクション追加成功時True、失敗時False
        """
        try:
            await message.add_reaction(self.REACTION_ERROR)
            self.logger.info(
                f"エラーリアクションを追加: {message.id}"
            )
            return True
        except Exception as e:
            log_exception(
                self.logger,
                f"エラーリアクション追加失敗 (メッセージID: {message.id})",
                e
            )
            return False

    async def add_thread_comment_reaction(self, message: Message) -> bool:
        """
        スレッドコメント追記成功リアクションを追加（Requirement 8.5）

        Preconditions:
        - messageが有効なDiscordメッセージオブジェクト（スレッド内）

        Postconditions:
        - スレッドメッセージに✅リアクションが追加される
        - 成功時はTrueを返す
        - 失敗時はエラーログを記録しFalseを返す

        Args:
            message: 対象のDiscordメッセージ（スレッド内）

        Returns:
            bool: リアクション追加成功時True、失敗時False
        """
        # スレッドコメント追記も成功リアクションを使用
        return await self.add_success_reaction(message)

    async def remove_received_reaction(self, message: Message) -> bool:
        """
        受信確認リアクションを削除

        Preconditions:
        - messageが有効なDiscordメッセージオブジェクト
        - Bot自身が該当リアクションを追加している

        Postconditions:
        - 👁️リアクションが削除される
        - 成功時はTrueを返す
        - 失敗時はエラーログを記録しFalseを返す

        Args:
            message: 対象のDiscordメッセージ

        Returns:
            bool: リアクション削除成功時True、失敗時False
        """
        try:
            await message.remove_reaction(
                self.REACTION_RECEIVED,
                message.guild.me
            )
            self.logger.info(
                f"受信確認リアクションを削除: {message.id}"
            )
            return True
        except Exception as e:
            log_exception(
                self.logger,
                f"受信確認リアクション削除失敗 (メッセージID: {message.id})",
                e
            )
            return False
