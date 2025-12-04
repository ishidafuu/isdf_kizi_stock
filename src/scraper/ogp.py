"""OGP情報取得

Web ページからOGP（Open Graph Protocol）情報を取得します。
- 非同期HTTP通信による効率的なデータ取得
- OGPメタタグの抽出（og:title, og:description, og:image）
- フォールバック処理（<title>, <meta name="description">）
- タイムアウトとサイズ制限による安全性確保
"""

import logging
from typing import Dict, Optional

import aiohttp
from bs4 import BeautifulSoup

from config.settings import Settings
from src.utils.logger import log_exception, setup_logger
from src.utils.retry import retry_on_network_error


class OGPScraper:
    """OGP情報取得クラス

    指定されたURLからOGP情報を非同期で取得します。
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        OGPScraperの初期化

        Args:
            logger: ロガーインスタンス（オプション）
        """
        self.logger = logger or setup_logger(
            "OGPScraper",
            Settings.LOG_FILE_PATH
        )

    async def fetch_ogp(self, url: str) -> Dict[str, Optional[str]]:
        """
        OGP情報を取得（Requirement 3.1-3.7）

        Preconditions:
        - urlが有効なHTTP/HTTPS URL

        Postconditions:
        - OGP情報が取得できた場合: {"title": str, "description": str, "image": str}
        - フォールバック処理が適用された場合も同様の形式で返す
        - 完全に失敗した場合: {"title": "無題の記事", "description": None, "image": None}

        Args:
            url: 対象のURL

        Returns:
            Dict[str, Optional[str]]: OGP情報
                - title: 記事タイトル
                - description: 記事概要
                - image: OGP画像URL
        """
        try:
            # HTTP通信でHTMLを取得（タイムアウト: 10秒、サイズ制限: 10MB）
            html_content = await self._fetch_html(url)

            if not html_content:
                return self._get_fallback_ogp(url)

            # BeautifulSoupでHTMLを解析
            soup = BeautifulSoup(html_content, "html.parser")

            # OGPメタタグを抽出
            ogp_data = self._extract_ogp_tags(soup)

            # フォールバック処理
            ogp_data = self._apply_fallback(soup, ogp_data)

            self.logger.info(f"OGP取得成功: {url} - {ogp_data.get('title')}")
            return ogp_data

        except Exception as e:
            log_exception(
                self.logger,
                f"OGP取得中にエラーが発生: {url}",
                e
            )
            return self._get_fallback_ogp(url)

    async def _fetch_html(self, url: str) -> Optional[str]:
        """
        URLからHTMLを取得（Requirement 3.1, 3.6, 3.7, 9.4）

        ネットワークエラー時は自動的にリトライします。

        Args:
            url: 対象のURL

        Returns:
            Optional[str]: HTML文字列（失敗時None）
        """
        try:
            # ネットワークエラー時のリトライ処理を適用（Requirement 9.4）
            return await retry_on_network_error(
                self._fetch_html_internal,
                max_retries=Settings.NETWORK_RETRY_COUNT,
                delay=Settings.NETWORK_RETRY_DELAY,
                logger=self.logger,
                url=url
            )

        except asyncio.TimeoutError:
            self.logger.error(
                f"タイムアウト（{Settings.OGP_TIMEOUT_SECONDS}秒）: {url}"
            )
            return None
        except Exception as e:
            log_exception(
                self.logger,
                f"HTML取得中にエラーが発生（リトライ後）: {url}",
                e
            )
            return None

    async def _fetch_html_internal(self, url: str) -> str:
        """
        URLからHTMLを取得（内部実装）

        Args:
            url: 対象のURL

        Returns:
            str: HTML文字列

        Raises:
            aiohttp.ClientError: ネットワークエラー
            ValueError: コンテンツサイズ超過やHTTPステータスエラー
        """
        timeout = aiohttp.ClientTimeout(
            total=Settings.OGP_TIMEOUT_SECONDS
        )

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                # ステータスコードチェック
                if response.status != 200:
                    self.logger.warning(
                        f"HTTPステータスコードエラー: {response.status} - {url}"
                    )
                    # リトライしないようにValueErrorを発生
                    raise ValueError(f"HTTP {response.status}")

                # Content-Lengthチェック（10MB超過の場合は取得しない）
                content_length = response.headers.get("Content-Length")
                if content_length:
                    if int(content_length) > Settings.MAX_CONTENT_SIZE:
                        self.logger.error(
                            f"コンテンツサイズ超過: {content_length} bytes - {url}"
                        )
                        # リトライしないようにValueErrorを発生
                        raise ValueError("Content size exceeded")

                # HTMLを取得
                html = await response.text()

                # 取得後のサイズチェック
                if len(html.encode("utf-8")) > Settings.MAX_CONTENT_SIZE:
                    self.logger.error(
                        f"コンテンツサイズ超過（取得後）: {len(html.encode('utf-8'))} bytes - {url}"
                    )
                    # リトライしないようにValueErrorを発生
                    raise ValueError("Content size exceeded after fetch")

                return html

    def _extract_ogp_tags(self, soup: BeautifulSoup) -> Dict[str, Optional[str]]:
        """
        OGPメタタグを抽出（Requirement 3.2）

        Args:
            soup: BeautifulSoupオブジェクト

        Returns:
            Dict[str, Optional[str]]: OGP情報
        """
        ogp_data = {
            "title": None,
            "description": None,
            "image": None
        }

        # og:title を抽出
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            ogp_data["title"] = og_title["content"]

        # og:description を抽出
        og_description = soup.find("meta", property="og:description")
        if og_description and og_description.get("content"):
            ogp_data["description"] = og_description["content"]

        # og:image を抽出
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            ogp_data["image"] = og_image["content"]

        return ogp_data

    def _apply_fallback(
        self,
        soup: BeautifulSoup,
        ogp_data: Dict[str, Optional[str]]
    ) -> Dict[str, Optional[str]]:
        """
        フォールバック処理を適用（Requirement 3.3, 3.4）

        Args:
            soup: BeautifulSoupオブジェクト
            ogp_data: 抽出されたOGP情報

        Returns:
            Dict[str, Optional[str]]: フォールバック適用後のOGP情報
        """
        # og:title が取得できない場合、<title>タグを使用（Requirement 3.3）
        if not ogp_data["title"]:
            title_tag = soup.find("title")
            if title_tag and title_tag.string:
                ogp_data["title"] = title_tag.string.strip()
                self.logger.info("フォールバック: <title>タグを使用")

        # og:description が取得できない場合、<meta name="description">を使用（Requirement 3.4）
        if not ogp_data["description"]:
            meta_description = soup.find("meta", attrs={"name": "description"})
            if meta_description and meta_description.get("content"):
                ogp_data["description"] = meta_description["content"]
                self.logger.info("フォールバック: <meta name=\"description\">を使用")

        # タイトルが全く取得できない場合、「無題の記事」を使用（Requirement 3.5）
        if not ogp_data["title"]:
            ogp_data["title"] = "無題の記事"
            self.logger.warning("フォールバック: タイトルを「無題の記事」に設定")

        return ogp_data

    def _get_fallback_ogp(self, url: str) -> Dict[str, Optional[str]]:
        """
        OGP取得が完全に失敗した場合のフォールバック（Requirement 3.5）

        Args:
            url: 対象のURL

        Returns:
            Dict[str, Optional[str]]: フォールバックOGP情報
        """
        self.logger.warning(f"OGP取得完全失敗、フォールバック適用: {url}")

        return {
            "title": "無題の記事",
            "description": None,
            "image": None
        }


# asyncioのインポート（_fetch_htmlで使用）
import asyncio
