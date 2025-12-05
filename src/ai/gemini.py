"""Gemini AI統合

Gemini Flash 2.5 APIを使用して記事のタグ付けと要約生成を行います。
- 記事タイトルと概要からタグを3〜5個生成
- 要約補足テキストを生成（100字以内）
- タイムアウト処理とフォールバック処理
"""

import asyncio
import logging
from typing import Dict, List, Optional

import google.generativeai as genai

from config.settings import Settings
from src.utils.logger import log_exception, setup_logger
from src.utils.retry import retry_on_network_error


class GeminiClient:
    """Gemini AIクライアントクラス

    Gemini Flash 2.5 APIを使用して記事のタグ付けと要約生成を行います。
    """

    # プロンプトテンプレート（Requirement 4.6）
    PROMPT_TEMPLATE = """
以下の記事情報から、適切なタグと要約補足を生成してください。

# 記事タイトル
{title}

# 記事概要
{description}

# 出力形式
以下のJSON形式で出力してください：

{{
  "tags": ["タグ1", "タグ2", "タグ3"],
  "summary": "要約補足テキスト（100字以内）"
}}

# 要件
- タグは3個から5個の日本語の単語または短いフレーズ
- タグは記事の内容を的確に表すもの
- 要約補足は元の概要を補完する情報（100字以内）
- 要約補足がない場合は空文字列を返す
"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        GeminiClientの初期化

        Args:
            logger: ロガーインスタンス（オプション）
        """
        self.logger = logger or setup_logger(
            "GeminiClient",
            Settings.LOG_FILE_PATH
        )

        # Gemini APIキーを設定
        if Settings.GEMINI_API_KEY:
            genai.configure(api_key=Settings.GEMINI_API_KEY)
            self.logger.info("Gemini API設定完了")
        else:
            self.logger.warning("Gemini APIキーが設定されていません")

        # モデルを初期化（Gemini Flash 2.5）
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")

    async def generate_tags_and_summary(
        self,
        title: str,
        description: str
    ) -> Dict[str, any]:
        """
        タグと要約補足を生成（Requirement 4.1-4.7）

        Preconditions:
        - titleが記事タイトル文字列
        - descriptionが記事概要文字列

        Postconditions:
        - 成功時: {"tags": List[str], "summary": str}（タグ3〜5個）
        - 失敗時: {"tags": ["未分類", "要確認"], "summary": ""}

        Args:
            title: 記事タイトル
            description: 記事概要

        Returns:
            Dict[str, any]: タグと要約補足
                - tags: タグリスト（3〜5個）
                - summary: 要約補足テキスト
        """
        try:
            # プロンプトを生成
            prompt = self.PROMPT_TEMPLATE.format(
                title=title,
                description=description or "（概要なし）"
            )

            # Gemini API呼び出し（タイムアウト付き）
            result = await asyncio.wait_for(
                self._call_gemini_api(prompt),
                timeout=Settings.GEMINI_TIMEOUT_SECONDS
            )

            if not result:
                return self._get_fallback_result()

            # タグ数の検証（Requirement 4.2, 4.3）
            tags = result.get("tags", [])
            if not self._validate_tags(tags):
                self.logger.warning(
                    f"タグ数が範囲外: {len(tags)}個（3〜5個が期待値）"
                )
                # タグ数を調整
                tags = self._adjust_tags(tags)

            # 要約補足の長さチェック
            summary = result.get("summary", "")
            if len(summary) > 100:
                summary = summary[:100]
                self.logger.info("要約補足を100字に切り詰めました")

            self.logger.info(
                f"タグ生成成功: {len(tags)}個 - {tags}"
            )

            return {
                "tags": tags,
                "summary": summary
            }

        except asyncio.TimeoutError:
            # タイムアウトエラー（Requirement 4.7）
            self.logger.error(
                f"Gemini APIタイムアウト（{Settings.GEMINI_TIMEOUT_SECONDS}秒）"
            )
            return self._get_fallback_result()

        except Exception as e:
            # その他のエラー（Requirement 4.5）
            log_exception(
                self.logger,
                "Gemini API呼び出し中にエラーが発生",
                e
            )
            return self._get_fallback_result()

    async def _call_gemini_api(self, prompt: str) -> Optional[Dict]:
        """
        Gemini APIを呼び出し（非同期）（Requirement 9.4）

        ネットワークエラー時は自動的にリトライします。

        Args:
            prompt: プロンプトテキスト

        Returns:
            Optional[Dict]: API呼び出し結果（失敗時None）
        """
        try:
            # ネットワークエラー時のリトライ処理を適用（Requirement 9.4）
            return await retry_on_network_error(
                self._call_gemini_api_internal,
                max_retries=Settings.NETWORK_RETRY_COUNT,
                delay=Settings.NETWORK_RETRY_DELAY,
                logger=self.logger,
                prompt=prompt
            )

        except json.JSONDecodeError as e:
            log_exception(
                self.logger,
                "Gemini APIレスポンスのJSON解析に失敗",
                e
            )
            return None
        except Exception as e:
            log_exception(
                self.logger,
                "Gemini API呼び出しに失敗（リトライ後）",
                e
            )
            return None

    async def _call_gemini_api_internal(self, prompt: str) -> Dict:
        """
        Gemini APIを呼び出し（内部実装）

        Args:
            prompt: プロンプトテキスト

        Returns:
            Dict: API呼び出し結果

        Raises:
            Exception: API呼び出しエラー、JSON解析エラー
        """
        # 同期APIを非同期で実行
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.model.generate_content(prompt)
        )

        # レスポンステキストを取得
        if not response or not response.text:
            self.logger.error("Gemini APIレスポンスが空です")
            raise ValueError("Empty API response")

        # JSONを解析
        import json
        response_text = response.text.strip()

        # Markdown形式のコードブロックを除去
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        response_text = response_text.strip()

        result = json.loads(response_text)
        return result

    def _validate_tags(self, tags: List[str]) -> bool:
        """
        タグ数を検証（Requirement 4.2）

        Args:
            tags: タグリスト

        Returns:
            bool: タグ数が3〜5個の場合True
        """
        return Settings.MIN_TAG_COUNT <= len(tags) <= Settings.MAX_TAG_COUNT

    def _adjust_tags(self, tags: List[str]) -> List[str]:
        """
        タグ数を調整（3〜5個の範囲内に収める）

        Args:
            tags: タグリスト

        Returns:
            List[str]: 調整されたタグリスト
        """
        if len(tags) < Settings.MIN_TAG_COUNT:
            # タグが不足している場合、デフォルトタグを追加
            while len(tags) < Settings.MIN_TAG_COUNT:
                tags.append("その他")
            self.logger.info(f"タグを{Settings.MIN_TAG_COUNT}個に調整しました")

        elif len(tags) > Settings.MAX_TAG_COUNT:
            # タグが多すぎる場合、最初の5個のみを使用
            tags = tags[:Settings.MAX_TAG_COUNT]
            self.logger.info(f"タグを{Settings.MAX_TAG_COUNT}個に調整しました")

        return tags

    def _get_fallback_result(self) -> Dict[str, any]:
        """
        フォールバック結果を取得（Requirement 4.5）

        Returns:
            Dict[str, any]: デフォルトタグと空の要約
        """
        self.logger.warning(
            f"フォールバック適用: デフォルトタグ {Settings.DEFAULT_TAGS}"
        )

        return {
            "tags": Settings.DEFAULT_TAGS.copy(),
            "summary": ""
        }
