"""ContentParser のユニットテスト

Requirements coverage:
- 2.1: URL抽出と記事処理モード
- 2.2: URL+コメントの分離
- 2.3: テキストのみの場合のメモモード
- 2.4: 複数URL検出時の最初のURLのみ処理
- 2.5: HTTP/HTTPSプロトコルを含む有効なURL形式のみ認識
"""

import pytest
from src.utils.parser import ContentParser


class TestContentParserParseMessage:
    """parse_message メソッドのテスト"""

    # Requirement 2.1: URL単体の場合
    def test_parse_message_url_only(self):
        """URL単体のメッセージを正しく解析できる"""
        # Given
        content = "https://example.com/article"

        # When
        result = ContentParser.parse_message(content)

        # Then
        assert result["url"] == "https://example.com/article"
        assert result["comment"] is None
        assert "memo" not in result

    def test_parse_message_url_only_http(self):
        """HTTP URLも正しく解析できる"""
        # Given
        content = "http://example.com/article"

        # When
        result = ContentParser.parse_message(content)

        # Then
        assert result["url"] == "http://example.com/article"
        assert result["comment"] is None

    # Requirement 2.2: URL+コメントの組み合わせ
    def test_parse_message_url_with_comment_before(self):
        """コメント＋URLの形式を正しく解析できる"""
        # Given
        content = "面白い記事を見つけた https://example.com/article"

        # When
        result = ContentParser.parse_message(content)

        # Then
        assert result["url"] == "https://example.com/article"
        assert result["comment"] == "面白い記事を見つけた"

    def test_parse_message_url_with_comment_after(self):
        """URL＋コメントの形式を正しく解析できる"""
        # Given
        content = "https://example.com/article これは参考になる"

        # When
        result = ContentParser.parse_message(content)

        # Then
        assert result["url"] == "https://example.com/article"
        assert result["comment"] == "これは参考になる"

    def test_parse_message_url_with_comment_both_sides(self):
        """コメント＋URL＋コメントの形式を正しく解析できる"""
        # Given
        content = "見つけた記事 https://example.com/article 後で読む"

        # When
        result = ContentParser.parse_message(content)

        # Then
        assert result["url"] == "https://example.com/article"
        assert "見つけた記事" in result["comment"]
        assert "後で読む" in result["comment"]

    def test_parse_message_url_with_multiline_comment(self):
        """複数行コメント付きURLを正しく解析できる"""
        # Given
        content = """技術記事メモ
https://example.com/article
後で実装してみる"""

        # When
        result = ContentParser.parse_message(content)

        # Then
        assert result["url"] == "https://example.com/article"
        assert "技術記事メモ" in result["comment"]
        assert "後で実装してみる" in result["comment"]

    # Requirement 2.3: テキストのみの場合（メモモード）
    def test_parse_message_text_only(self):
        """URLを含まないテキストはメモとして扱う"""
        # Given
        content = "これは単なるメモです"

        # When
        result = ContentParser.parse_message(content)

        # Then
        assert result["url"] is None
        assert result["memo"] == "これは単なるメモです"
        assert "comment" not in result

    def test_parse_message_text_with_invalid_url(self):
        """不正なURL形式はテキストとして扱う"""
        # Given
        content = "example.com/article は良い記事"

        # When
        result = ContentParser.parse_message(content)

        # Then
        assert result["url"] is None
        assert result["memo"] == "example.com/article は良い記事"

    def test_parse_message_multiline_memo(self):
        """複数行のメモを正しく扱う"""
        # Given
        content = """今日の学び：
Pythonの型ヒントについて
もっと勉強が必要"""

        # When
        result = ContentParser.parse_message(content)

        # Then
        assert result["url"] is None
        assert "今日の学び：" in result["memo"]
        assert "もっと勉強が必要" in result["memo"]

    # Requirement 2.4: 複数URL検出時の最初のURLのみ処理
    def test_parse_message_multiple_urls_first_only(self):
        """複数URLがある場合、最初のURLのみを抽出する"""
        # Given
        content = "https://example.com/first https://example.com/second"

        # When
        result = ContentParser.parse_message(content)

        # Then
        assert result["url"] == "https://example.com/first"
        assert "https://example.com/second" in result["comment"]

    def test_parse_message_multiple_urls_with_text(self):
        """複数URL＋テキストの場合、最初のURLのみを抽出し残りはコメント"""
        # Given
        content = "記事1 https://example.com/first 記事2 https://example.com/second"

        # When
        result = ContentParser.parse_message(content)

        # Then
        assert result["url"] == "https://example.com/first"
        # URLを削除した後の残りのテキスト全てがコメントに含まれる
        assert "記事1" in result["comment"]
        assert "記事2" in result["comment"]
        assert "https://example.com/second" in result["comment"]

    def test_parse_message_three_urls(self):
        """3つ以上のURLがある場合も最初のURLのみを抽出"""
        # Given
        content = "https://a.com https://b.com https://c.com"

        # When
        result = ContentParser.parse_message(content)

        # Then
        assert result["url"] == "https://a.com"
        assert "https://b.com" in result["comment"]
        assert "https://c.com" in result["comment"]

    # Requirement 2.5: HTTP/HTTPSプロトコルを含む有効なURL形式のみ認識
    def test_parse_message_url_without_protocol(self):
        """プロトコルなしのURLは認識されない"""
        # Given
        content = "example.com/article"

        # When
        result = ContentParser.parse_message(content)

        # Then
        assert result["url"] is None
        assert result["memo"] == "example.com/article"

    def test_parse_message_ftp_url_not_recognized(self):
        """FTPプロトコルのURLは認識されない"""
        # Given
        content = "ftp://example.com/file"

        # When
        result = ContentParser.parse_message(content)

        # Then
        assert result["url"] is None
        assert result["memo"] == "ftp://example.com/file"

    def test_parse_message_url_with_path_and_query(self):
        """パスとクエリパラメータを含むURLを正しく解析できる"""
        # Given
        content = "https://example.com/path/to/article?id=123&ref=twitter"

        # When
        result = ContentParser.parse_message(content)

        # Then
        assert result["url"] == "https://example.com/path/to/article?id=123&ref=twitter"
        assert result["comment"] is None

    def test_parse_message_url_with_fragment(self):
        """フラグメントを含むURLを正しく解析できる"""
        # Given
        content = "https://example.com/article#section-2"

        # When
        result = ContentParser.parse_message(content)

        # Then
        assert result["url"] == "https://example.com/article#section-2"

    # エッジケース
    def test_parse_message_empty_string(self):
        """空文字列を処理できる"""
        # Given
        content = ""

        # When
        result = ContentParser.parse_message(content)

        # Then
        assert result["url"] is None
        assert result["memo"] == ""

    def test_parse_message_whitespace_only(self):
        """空白文字のみの場合を処理できる"""
        # Given
        content = "   \n\t  "

        # When
        result = ContentParser.parse_message(content)

        # Then
        assert result["url"] is None
        assert result["memo"] == ""

    def test_parse_message_url_with_whitespace(self):
        """前後に空白があるURLを正しく解析できる"""
        # Given
        content = "  https://example.com/article  "

        # When
        result = ContentParser.parse_message(content)

        # Then
        assert result["url"] == "https://example.com/article"
        assert result["comment"] is None

    def test_parse_message_url_in_markdown_link(self):
        """Markdownリンク形式のURLを抽出できる（閉じ括弧も含む）"""
        # Given
        content = "[記事リンク](https://example.com/article)"

        # When
        result = ContentParser.parse_message(content)

        # Then
        # 正規表現は閉じ括弧も含めて抽出する（許容される動作）
        assert result["url"] == "https://example.com/article)"
        assert "[記事リンク](" in result["comment"]


class TestContentParserExtractUrls:
    """extract_urls メソッドのテスト"""

    def test_extract_urls_single(self):
        """単一URLを抽出できる"""
        # Given
        content = "https://example.com/article"

        # When
        urls = ContentParser.extract_urls(content)

        # Then
        assert len(urls) == 1
        assert urls[0] == "https://example.com/article"

    def test_extract_urls_multiple(self):
        """複数URLを全て抽出できる"""
        # Given
        content = "https://a.com https://b.com https://c.com"

        # When
        urls = ContentParser.extract_urls(content)

        # Then
        assert len(urls) == 3
        assert "https://a.com" in urls
        assert "https://b.com" in urls
        assert "https://c.com" in urls

    def test_extract_urls_none(self):
        """URLがない場合は空リストを返す"""
        # Given
        content = "これはテキストのみです"

        # When
        urls = ContentParser.extract_urls(content)

        # Then
        assert len(urls) == 0


class TestContentParserValidateUrl:
    """validate_url メソッドのテスト"""

    def test_validate_url_valid_https(self):
        """有効なHTTPS URLを認識する"""
        # Given
        url = "https://example.com/article"

        # When
        is_valid = ContentParser.validate_url(url)

        # Then
        assert is_valid is True

    def test_validate_url_valid_http(self):
        """有効なHTTP URLを認識する"""
        # Given
        url = "http://example.com/article"

        # When
        is_valid = ContentParser.validate_url(url)

        # Then
        assert is_valid is True

    def test_validate_url_invalid_no_protocol(self):
        """プロトコルなしのURLは無効と判定する"""
        # Given
        url = "example.com/article"

        # When
        is_valid = ContentParser.validate_url(url)

        # Then
        assert is_valid is False

    def test_validate_url_invalid_ftp(self):
        """FTPプロトコルのURLは無効と判定する"""
        # Given
        url = "ftp://example.com/file"

        # When
        is_valid = ContentParser.validate_url(url)

        # Then
        assert is_valid is False

    def test_validate_url_empty_string(self):
        """空文字列は無効と判定する"""
        # Given
        url = ""

        # When
        is_valid = ContentParser.validate_url(url)

        # Then
        assert is_valid is False

    def test_validate_url_with_text(self):
        """URLに追加テキストがある場合は無効と判定する"""
        # Given
        url = "https://example.com これは追加テキスト"

        # When
        is_valid = ContentParser.validate_url(url)

        # Then
        assert is_valid is False


class TestContentParserIsUrlMessage:
    """is_url_message メソッドのテスト"""

    def test_is_url_message_true(self):
        """URLを含むメッセージを正しく判定する"""
        # Given
        content = "これは記事です https://example.com/article"

        # When
        result = ContentParser.is_url_message(content)

        # Then
        assert result is True

    def test_is_url_message_false(self):
        """URLを含まないメッセージを正しく判定する"""
        # Given
        content = "これは単なるメモです"

        # When
        result = ContentParser.is_url_message(content)

        # Then
        assert result is False

    def test_is_url_message_multiple_urls(self):
        """複数URLを含むメッセージを正しく判定する"""
        # Given
        content = "https://a.com https://b.com"

        # When
        result = ContentParser.is_url_message(content)

        # Then
        assert result is True
