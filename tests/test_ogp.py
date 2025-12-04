"""OGPScraper のユニットテスト

Requirements coverage:
- 3.1: URLへのHTTPリクエスト送信とHTML取得
- 3.2: OGPメタタグの抽出（og:title, og:description, og:image）
- 3.3: og:titleが取得できない場合は<title>タグを使用
- 3.4: og:descriptionが取得できない場合は<meta name="description">を使用
- 3.5: OGP取得が完全に失敗した場合は「無題の記事」として記録
- 3.6: OGP取得処理のタイムアウトを10秒に設定
- 3.7: 取得したHTMLが10MB以上の場合は処理を中断
"""

import asyncio

import aiohttp
import pytest
from aioresponses import aioresponses

from config.settings import Settings
from src.scraper.ogp import OGPScraper


class TestOGPScraperFetchOgp:
    """fetch_ogp メソッドのテスト"""

    # Requirement 3.1, 3.2: OGP正常取得ケース
    @pytest.mark.asyncio
    async def test_fetch_ogp_complete_success(self):
        """完全なOGP情報を正常に取得できる"""
        # Given
        url = "https://example.com/article"
        html_content = """
        <html>
        <head>
            <meta property="og:title" content="テスト記事タイトル" />
            <meta property="og:description" content="これはテスト記事の説明です。" />
            <meta property="og:image" content="https://example.com/image.jpg" />
            <title>HTML Title</title>
        </head>
        <body>Content</body>
        </html>
        """

        scraper = OGPScraper()

        with aioresponses() as m:
            m.get(url, status=200, body=html_content)

            # When
            result = await scraper.fetch_ogp(url)

            # Then
            assert result["title"] == "テスト記事タイトル"
            assert result["description"] == "これはテスト記事の説明です。"
            assert result["image"] == "https://example.com/image.jpg"

    @pytest.mark.asyncio
    async def test_fetch_ogp_partial_tags(self):
        """一部のOGPタグのみ存在する場合"""
        # Given
        url = "https://example.com/article"
        html_content = """
        <html>
        <head>
            <meta property="og:title" content="部分的なOGP記事" />
            <title>HTML Title</title>
        </head>
        <body>Content</body>
        </html>
        """

        scraper = OGPScraper()

        with aioresponses() as m:
            m.get(url, status=200, body=html_content)

            # When
            result = await scraper.fetch_ogp(url)

            # Then
            assert result["title"] == "部分的なOGP記事"
            assert result["description"] is None
            assert result["image"] is None

    # Requirement 3.3: og:titleフォールバック
    @pytest.mark.asyncio
    async def test_fetch_ogp_fallback_to_title_tag(self):
        """og:titleがない場合、<title>タグにフォールバックする"""
        # Given
        url = "https://example.com/article"
        html_content = """
        <html>
        <head>
            <title>HTMLタイトルタグ</title>
            <meta property="og:description" content="説明文" />
        </head>
        <body>Content</body>
        </html>
        """

        scraper = OGPScraper()

        with aioresponses() as m:
            m.get(url, status=200, body=html_content)

            # When
            result = await scraper.fetch_ogp(url)

            # Then
            assert result["title"] == "HTMLタイトルタグ"
            assert result["description"] == "説明文"

    # Requirement 3.4: og:descriptionフォールバック
    @pytest.mark.asyncio
    async def test_fetch_ogp_fallback_to_meta_description(self):
        """og:descriptionがない場合、<meta name="description">にフォールバックする"""
        # Given
        url = "https://example.com/article"
        html_content = """
        <html>
        <head>
            <meta property="og:title" content="OGPタイトル" />
            <meta name="description" content="メタディスクリプション" />
        </head>
        <body>Content</body>
        </html>
        """

        scraper = OGPScraper()

        with aioresponses() as m:
            m.get(url, status=200, body=html_content)

            # When
            result = await scraper.fetch_ogp(url)

            # Then
            assert result["title"] == "OGPタイトル"
            assert result["description"] == "メタディスクリプション"

    # Requirement 3.3, 3.4: 複合フォールバック
    @pytest.mark.asyncio
    async def test_fetch_ogp_fallback_both_title_and_description(self):
        """og:titleとog:descriptionの両方がない場合、フォールバックする"""
        # Given
        url = "https://example.com/article"
        html_content = """
        <html>
        <head>
            <title>フォールバックタイトル</title>
            <meta name="description" content="フォールバック説明" />
        </head>
        <body>Content</body>
        </html>
        """

        scraper = OGPScraper()

        with aioresponses() as m:
            m.get(url, status=200, body=html_content)

            # When
            result = await scraper.fetch_ogp(url)

            # Then
            assert result["title"] == "フォールバックタイトル"
            assert result["description"] == "フォールバック説明"

    # Requirement 3.5: 完全失敗時のフォールバック
    @pytest.mark.asyncio
    async def test_fetch_ogp_complete_fallback_no_tags(self):
        """タイトルタグが全くない場合、「無題の記事」として記録する"""
        # Given
        url = "https://example.com/article"
        html_content = """
        <html>
        <head>
        </head>
        <body>Content only</body>
        </html>
        """

        scraper = OGPScraper()

        with aioresponses() as m:
            m.get(url, status=200, body=html_content)

            # When
            result = await scraper.fetch_ogp(url)

            # Then
            assert result["title"] == "無題の記事"
            assert result["description"] is None
            assert result["image"] is None

    # Requirement 3.6: タイムアウト処理
    @pytest.mark.asyncio
    async def test_fetch_ogp_timeout_error(self):
        """タイムアウト時にフォールバック処理に移行する"""
        # Given
        url = "https://example.com/slow-article"
        scraper = OGPScraper()

        with aioresponses() as m:
            # タイムアウトエラーをシミュレート
            m.get(url, exception=asyncio.TimeoutError())

            # When
            result = await scraper.fetch_ogp(url)

            # Then
            assert result["title"] == "無題の記事"
            assert result["description"] is None
            assert result["image"] is None

    # Requirement 3.7: Content-Lengthによるサイズ超過チェック
    @pytest.mark.asyncio
    async def test_fetch_ogp_content_length_exceeded(self):
        """Content-Lengthが10MBを超える場合、処理を中断する"""
        # Given
        url = "https://example.com/large-article"
        scraper = OGPScraper()
        large_size = Settings.MAX_CONTENT_SIZE + 1

        with aioresponses() as m:
            m.get(
                url,
                status=200,
                headers={"Content-Length": str(large_size)},
                body="content"
            )

            # When
            result = await scraper.fetch_ogp(url)

            # Then
            assert result["title"] == "無題の記事"
            assert result["description"] is None

    # Requirement 3.7: 実際のコンテンツサイズ超過
    @pytest.mark.asyncio
    async def test_fetch_ogp_actual_content_size_exceeded(self):
        """取得後のコンテンツサイズが10MBを超える場合、処理を中断する"""
        # Given
        url = "https://example.com/large-content"
        scraper = OGPScraper()
        # 10MB + 1バイトの大きなコンテンツを生成
        large_content = "x" * (Settings.MAX_CONTENT_SIZE + 1)

        with aioresponses() as m:
            m.get(url, status=200, body=large_content)

            # When
            result = await scraper.fetch_ogp(url)

            # Then
            assert result["title"] == "無題の記事"
            assert result["description"] is None

    # HTTPステータスエラー
    @pytest.mark.asyncio
    async def test_fetch_ogp_http_404_error(self):
        """HTTP 404エラー時にフォールバック処理に移行する"""
        # Given
        url = "https://example.com/not-found"
        scraper = OGPScraper()

        with aioresponses() as m:
            m.get(url, status=404)

            # When
            result = await scraper.fetch_ogp(url)

            # Then
            assert result["title"] == "無題の記事"
            assert result["description"] is None

    @pytest.mark.asyncio
    async def test_fetch_ogp_http_500_error(self):
        """HTTP 500エラー時にフォールバック処理に移行する"""
        # Given
        url = "https://example.com/server-error"
        scraper = OGPScraper()

        with aioresponses() as m:
            m.get(url, status=500)

            # When
            result = await scraper.fetch_ogp(url)

            # Then
            assert result["title"] == "無題の記事"
            assert result["description"] is None

    # ネットワークエラー（リトライ含む）
    @pytest.mark.asyncio
    async def test_fetch_ogp_network_error_with_retry(self):
        """ネットワークエラー発生時、リトライ後にフォールバックする"""
        # Given
        url = "https://example.com/network-error"
        scraper = OGPScraper()

        with aioresponses() as m:
            # すべてのリトライでネットワークエラーをシミュレート
            for _ in range(Settings.NETWORK_RETRY_COUNT + 1):
                m.get(url, exception=aiohttp.ClientError("Network error"))

            # When
            result = await scraper.fetch_ogp(url)

            # Then
            assert result["title"] == "無題の記事"
            assert result["description"] is None

    # エッジケース: 空のOGP content属性
    @pytest.mark.asyncio
    async def test_fetch_ogp_empty_og_content(self):
        """OGPタグは存在するがcontent属性が空の場合"""
        # Given
        url = "https://example.com/empty-og"
        html_content = """
        <html>
        <head>
            <meta property="og:title" content="" />
            <meta property="og:description" content="" />
            <title>フォールバックタイトル</title>
        </head>
        <body>Content</body>
        </html>
        """

        scraper = OGPScraper()

        with aioresponses() as m:
            m.get(url, status=200, body=html_content)

            # When
            result = await scraper.fetch_ogp(url)

            # Then
            # 空のcontent属性はNoneとして扱われ、フォールバックされる
            assert result["title"] == "フォールバックタイトル"
            assert result["description"] is None

    # エッジケース: Unicodeを含むコンテンツ
    @pytest.mark.asyncio
    async def test_fetch_ogp_unicode_content(self):
        """Unicodeを含むOGP情報を正しく処理できる"""
        # Given
        url = "https://example.com/unicode-article"
        html_content = """
        <html>
        <head>
            <meta property="og:title" content="日本語タイトル 🚀 テスト" />
            <meta property="og:description" content="日本語説明文：特殊文字→←↑↓" />
        </head>
        <body>Content</body>
        </html>
        """

        scraper = OGPScraper()

        with aioresponses() as m:
            m.get(url, status=200, body=html_content)

            # When
            result = await scraper.fetch_ogp(url)

            # Then
            assert result["title"] == "日本語タイトル 🚀 テスト"
            assert result["description"] == "日本語説明文：特殊文字→←↑↓"

    # エッジケース: 改行を含むタイトル
    @pytest.mark.asyncio
    async def test_fetch_ogp_multiline_title(self):
        """<title>タグに改行や空白が含まれる場合、正しくトリムされる"""
        # Given
        url = "https://example.com/multiline-title"
        html_content = """
        <html>
        <head>
            <title>
                改行を含む
                タイトル
            </title>
        </head>
        <body>Content</body>
        </html>
        """

        scraper = OGPScraper()

        with aioresponses() as m:
            m.get(url, status=200, body=html_content)

            # When
            result = await scraper.fetch_ogp(url)

            # Then
            # strip()によって前後の空白・改行が除去される
            assert "改行を含む" in result["title"]
            assert "タイトル" in result["title"]


class TestOGPScraperExtractOgpTags:
    """_extract_ogp_tags メソッドのテスト（内部メソッドの直接テスト）"""

    def test_extract_ogp_tags_all_present(self):
        """すべてのOGPタグが存在する場合"""
        # Given
        from bs4 import BeautifulSoup

        html = """
        <html>
        <head>
            <meta property="og:title" content="タイトル" />
            <meta property="og:description" content="説明" />
            <meta property="og:image" content="https://example.com/img.jpg" />
        </head>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        scraper = OGPScraper()

        # When
        result = scraper._extract_ogp_tags(soup)

        # Then
        assert result["title"] == "タイトル"
        assert result["description"] == "説明"
        assert result["image"] == "https://example.com/img.jpg"

    def test_extract_ogp_tags_none_present(self):
        """OGPタグが全く存在しない場合"""
        # Given
        from bs4 import BeautifulSoup

        html = """
        <html>
        <head>
            <title>HTML Title</title>
        </head>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        scraper = OGPScraper()

        # When
        result = scraper._extract_ogp_tags(soup)

        # Then
        assert result["title"] is None
        assert result["description"] is None
        assert result["image"] is None


class TestOGPScraperApplyFallback:
    """_apply_fallback メソッドのテスト（内部メソッドの直接テスト）"""

    def test_apply_fallback_title_only(self):
        """og:titleがない場合、<title>タグにフォールバック"""
        # Given
        from bs4 import BeautifulSoup

        html = """
        <html>
        <head>
            <title>HTMLタイトル</title>
        </head>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        scraper = OGPScraper()
        ogp_data = {"title": None, "description": None, "image": None}

        # When
        result = scraper._apply_fallback(soup, ogp_data)

        # Then
        assert result["title"] == "HTMLタイトル"

    def test_apply_fallback_description_only(self):
        """og:descriptionがない場合、<meta name="description">にフォールバック"""
        # Given
        from bs4 import BeautifulSoup

        html = """
        <html>
        <head>
            <meta name="description" content="メタ説明" />
        </head>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        scraper = OGPScraper()
        ogp_data = {"title": "既存タイトル", "description": None, "image": None}

        # When
        result = scraper._apply_fallback(soup, ogp_data)

        # Then
        assert result["description"] == "メタ説明"

    def test_apply_fallback_to_untitled(self):
        """タイトルが全く取得できない場合、「無題の記事」を設定"""
        # Given
        from bs4 import BeautifulSoup

        html = """
        <html>
        <head>
        </head>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        scraper = OGPScraper()
        ogp_data = {"title": None, "description": None, "image": None}

        # When
        result = scraper._apply_fallback(soup, ogp_data)

        # Then
        assert result["title"] == "無題の記事"

    def test_apply_fallback_preserves_existing_ogp(self):
        """既存のOGPデータは保持される"""
        # Given
        from bs4 import BeautifulSoup

        html = """
        <html>
        <head>
            <title>HTMLタイトル</title>
            <meta name="description" content="メタ説明" />
        </head>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        scraper = OGPScraper()
        ogp_data = {
            "title": "OGPタイトル",
            "description": "OGP説明",
            "image": "https://example.com/img.jpg"
        }

        # When
        result = scraper._apply_fallback(soup, ogp_data)

        # Then
        # 既存のOGPデータはそのまま保持される
        assert result["title"] == "OGPタイトル"
        assert result["description"] == "OGP説明"
        assert result["image"] == "https://example.com/img.jpg"


class TestOGPScraperGetFallbackOgp:
    """_get_fallback_ogp メソッドのテスト（内部メソッドの直接テスト）"""

    def test_get_fallback_ogp_returns_untitled(self):
        """フォールバックOGP情報は「無題の記事」を返す"""
        # Given
        url = "https://example.com/failed"
        scraper = OGPScraper()

        # When
        result = scraper._get_fallback_ogp(url)

        # Then
        assert result["title"] == "無題の記事"
        assert result["description"] is None
        assert result["image"] is None
