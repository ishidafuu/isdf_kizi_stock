"""MarkdownGenerator のユニットテスト

Requirement 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7 のテスト
- YAMLフロントマター生成確認
- ファイル名サニタイゼーション確認
- 最大100文字制限の動作確認
"""

import re
from datetime import datetime
from unittest.mock import patch

import pytest

from config.settings import Settings
from src.storage.markdown import MarkdownGenerator


class TestMarkdownGenerator:
    """MarkdownGenerator クラスのテスト"""

    def test_generate_yaml_frontmatter_with_all_fields(self):
        """Requirement 5.2: YAMLフロントマター生成（全フィールド）"""
        # Given
        tags = ["Python", "Discord Bot", "AI要約"]
        url = "https://example.com/article"
        created = "2025-12-04"

        # When
        yaml = MarkdownGenerator._generate_yaml_front_matter(tags, url, created)

        # Then
        assert "---" in yaml
        assert "tags:" in yaml
        assert "  - Python" in yaml
        assert "  - Discord Bot" in yaml
        assert "  - AI要約" in yaml
        assert f"url: {url}" in yaml
        assert f"created: {created}" in yaml
        # YAMLは開始と終了のデリミタを持つ
        assert yaml.startswith("---\n")
        assert yaml.endswith("---\n")

    def test_generate_yaml_frontmatter_without_url(self):
        """Requirement 5.2: YAMLフロントマター生成（URL無し）"""
        # Given
        tags = ["メモ"]
        url = None
        created = "2025-12-04"

        # When
        yaml = MarkdownGenerator._generate_yaml_front_matter(tags, url, created)

        # Then
        assert "tags:" in yaml
        assert "  - メモ" in yaml
        assert "url:" not in yaml  # URLが無い場合は含まれない
        assert f"created: {created}" in yaml

    def test_sanitize_filename_removes_invalid_chars(self):
        """Requirement 5.7: ファイル名に使用できない文字を除去"""
        # Given: 使用できない文字を含むタイトル (/ \ : * ? " < > |)
        invalid_title = 'Test/Article\\Name:With*Invalid?Chars"<>|'

        # When
        sanitized = MarkdownGenerator._sanitize_filename(invalid_title)

        # Then: 使用できない文字が除去されている
        for char in Settings.INVALID_FILENAME_CHARS:
            assert char not in sanitized
        # 有効な文字は残っている
        assert "Test" in sanitized
        assert "Article" in sanitized
        assert "Name" in sanitized

    def test_sanitize_filename_handles_consecutive_spaces(self):
        """Requirement 5.7: 連続する空白を単一のスペースに置換"""
        # Given
        title_with_spaces = "Article   With    Many     Spaces"

        # When
        sanitized = MarkdownGenerator._sanitize_filename(title_with_spaces)

        # Then: 連続する空白が単一のスペースに置換されている
        assert "   " not in sanitized
        assert "Article With Many Spaces" == sanitized

    def test_sanitize_filename_trims_whitespace(self):
        """Requirement 5.7: 前後の空白を除去"""
        # Given
        title_with_padding = "  Article Title  "

        # When
        sanitized = MarkdownGenerator._sanitize_filename(title_with_padding)

        # Then: 前後の空白が除去されている
        assert sanitized == "Article Title"
        assert not sanitized.startswith(" ")
        assert not sanitized.endswith(" ")

    def test_sanitize_filename_fallback_to_untitled(self):
        """Requirement 5.7: 空文字列になった場合のフォールバック"""
        # Given: すべて無効な文字で構成されたタイトル
        invalid_only_title = "///:::**??<<>>"

        # When
        sanitized = MarkdownGenerator._sanitize_filename(invalid_only_title)

        # Then: "untitled" にフォールバック
        assert sanitized == "untitled"

    def test_generate_filename_format(self):
        """Requirement 5.6: ファイル名形式 YYYY-MM-DD_記事タイトル.md"""
        # Given
        title = "テスト記事タイトル"
        expected_date = datetime.now().strftime("%Y-%m-%d")

        # When
        filename = MarkdownGenerator.generate_filename(title)

        # Then: 形式が正しい
        assert filename.startswith(expected_date)
        assert filename.endswith(".md")
        assert "_" in filename
        # タイトルが含まれている
        assert "テスト記事タイトル" in filename

    def test_generate_filename_max_length_100(self):
        """Requirement 5.7: ファイル名の最大長を100文字に制限"""
        # Given: 非常に長いタイトル
        long_title = "あ" * 200  # 200文字の日本語タイトル

        # When
        filename = MarkdownGenerator.generate_filename(long_title)

        # Then: ファイル名が100文字以下
        assert len(filename) <= Settings.MAX_FILENAME_LENGTH
        # .md拡張子は保持されている
        assert filename.endswith(".md")
        # 日付プレフィックスは保持されている
        expected_date = datetime.now().strftime("%Y-%m-%d")
        assert filename.startswith(expected_date)

    def test_generate_filename_truncates_correctly(self):
        """Requirement 5.7: 100文字超過時の切り詰め動作確認"""
        # Given: 100文字を超えるタイトル
        long_title = "A" * 150

        # When
        filename = MarkdownGenerator.generate_filename(long_title)

        # Then
        assert len(filename) == Settings.MAX_FILENAME_LENGTH
        # 日付部分（10文字）+ アンダースコア（1文字）+ タイトル部分 + .md（3文字） = 100
        expected_date = datetime.now().strftime("%Y-%m-%d")
        date_prefix_length = len(expected_date) + 1  # "_" を含む
        extension_length = 3  # ".md"
        max_title_length = Settings.MAX_FILENAME_LENGTH - date_prefix_length - extension_length
        # タイトル部分が正しく切り詰められている
        assert len(filename) - date_prefix_length - extension_length <= max_title_length

    def test_generate_markdown_with_all_fields(self):
        """Requirement 5.1-5.5: 全フィールドを含むMarkdown生成"""
        # Given
        title = "テスト記事"
        url = "https://example.com/test"
        description = "これはテスト記事の概要です。"
        tags = ["テスト", "Python", "技術記事"]
        summary = "Geminiによる要約補足テキスト"
        comment = "初回投稿時のコメント"

        # When
        markdown = MarkdownGenerator.generate(
            title=title,
            url=url,
            description=description,
            tags=tags,
            summary=summary,
            comment=comment
        )

        # Then: 各セクションが含まれている
        # YAMLフロントマター（Requirement 5.2）
        assert "---" in markdown
        assert "tags:" in markdown
        assert "  - テスト" in markdown
        assert f"url: {url}" in markdown
        assert "created:" in markdown

        # タイトル（Requirement 5.3）
        assert f"# {title}" in markdown

        # 概要セクション（Requirement 5.4）
        assert "## 概要" in markdown
        assert description in markdown
        assert f"**補足:** {summary}" in markdown

        # コメントセクション（Requirement 5.5）
        assert "## コメント" in markdown
        assert comment in markdown

    def test_generate_markdown_without_optional_fields(self):
        """Requirement 5.1-5.4: オプションフィールド無しでもMarkdown生成可能"""
        # Given
        title = "シンプル記事"
        url = "https://example.com/simple"
        description = None
        tags = ["記事"]
        summary = None
        comment = None

        # When
        markdown = MarkdownGenerator.generate(
            title=title,
            url=url,
            description=description,
            tags=tags,
            summary=summary,
            comment=comment
        )

        # Then: 必須フィールドのみ含まれている
        assert "---" in markdown
        assert f"# {title}" in markdown
        # オプションセクションは含まれない
        assert "## 概要" not in markdown
        assert "## コメント" not in markdown

    def test_generate_markdown_with_description_only(self):
        """Requirement 5.4: 概要のみ（要約補足なし）"""
        # Given
        title = "記事タイトル"
        url = "https://example.com/article"
        description = "記事の概要テキスト"
        tags = ["記事"]

        # When
        markdown = MarkdownGenerator.generate(
            title=title,
            url=url,
            description=description,
            tags=tags,
            summary=None,
            comment=None
        )

        # Then
        assert "## 概要" in markdown
        assert description in markdown
        assert "**補足:**" not in markdown

    def test_generate_markdown_with_summary_only(self):
        """Requirement 5.4: 要約補足のみ（概要なし）"""
        # Given
        title = "記事タイトル"
        url = "https://example.com/article"
        tags = ["記事"]
        summary = "要約補足テキスト"

        # When
        markdown = MarkdownGenerator.generate(
            title=title,
            url=url,
            description=None,
            tags=tags,
            summary=summary,
            comment=None
        )

        # Then
        assert "## 概要" in markdown
        assert f"**補足:** {summary}" in markdown

    def test_generate_markdown_body_date_format(self):
        """Requirement 5.5: コメントの日付フォーマット（YYYY-MM-DD）"""
        # Given
        title = "記事"
        description = "概要"
        comment = "テストコメント"

        # When
        body = MarkdownGenerator._generate_markdown_body(
            title=title,
            description=description,
            summary=None,
            comment=comment
        )

        # Then: YYYY-MM-DD形式の日付が含まれている
        date_pattern = r"\d{4}-\d{2}-\d{2}"
        assert re.search(date_pattern, body)
        # 期待される日付
        expected_date = datetime.now().strftime("%Y-%m-%d")
        assert expected_date in body

    def test_generate_memo(self):
        """メモ用Markdown生成のテスト"""
        # Given
        memo = "これはテストメモです。"

        # When
        markdown = MarkdownGenerator.generate_memo(memo)

        # Then
        assert "---" in markdown
        assert "tags:" in markdown
        assert "  - メモ" in markdown
        assert "# メモ" in markdown
        assert memo in markdown
        # URLフィールドは含まれない（メモなので）
        assert "url:" not in markdown

    def test_generate_filename_with_sanitized_title(self):
        """ファイル名生成時のサニタイゼーション統合テスト"""
        # Given: 無効な文字を含む長いタイトル
        title_with_invalid = 'Test/Article:With*Invalid?Chars"<>|And Very Long Title ' * 3

        # When
        filename = MarkdownGenerator.generate_filename(title_with_invalid)

        # Then: 無効な文字が除去され、100文字以内に制限されている
        for char in Settings.INVALID_FILENAME_CHARS:
            assert char not in filename
        assert len(filename) <= Settings.MAX_FILENAME_LENGTH
        assert filename.endswith(".md")

    def test_generate_with_multiple_tags(self):
        """Requirement 5.2: 複数タグ（3-5個）の生成確認"""
        # Given
        title = "記事"
        url = "https://example.com"
        tags = ["Python", "Discord", "AI", "技術", "Bot"]  # 5個

        # When
        markdown = MarkdownGenerator.generate(
            title=title,
            url=url,
            description=None,
            tags=tags
        )

        # Then: すべてのタグが含まれている
        for tag in tags:
            assert f"  - {tag}" in markdown

    def test_generate_preserves_japanese_characters(self):
        """日本語文字の保持確認"""
        # Given
        title = "日本語のタイトル"
        description = "日本語の概要テキスト"
        tags = ["日本語", "テスト"]

        # When
        markdown = MarkdownGenerator.generate(
            title=title,
            url="https://example.com",
            description=description,
            tags=tags
        )

        # Then: 日本語が正しく保持されている
        assert title in markdown
        assert description in markdown
        for tag in tags:
            assert tag in markdown

    def test_sanitize_filename_preserves_japanese(self):
        """ファイル名サニタイゼーション時の日本語保持"""
        # Given
        japanese_title = "日本語のタイトル"

        # When
        sanitized = MarkdownGenerator._sanitize_filename(japanese_title)

        # Then: 日本語がそのまま保持されている
        assert sanitized == japanese_title

    def test_generate_filename_with_japanese_title(self):
        """日本語タイトルでのファイル名生成"""
        # Given
        japanese_title = "日本語の記事タイトル"

        # When
        filename = MarkdownGenerator.generate_filename(japanese_title)

        # Then
        assert japanese_title in filename
        assert filename.endswith(".md")
        expected_date = datetime.now().strftime("%Y-%m-%d")
        assert filename.startswith(expected_date)


class TestMarkdownGeneratorEdgeCases:
    """エッジケースのテスト"""

    def test_empty_tags_list(self):
        """空のタグリストの処理"""
        # Given
        tags = []

        # When
        yaml = MarkdownGenerator._generate_yaml_front_matter(
            tags=tags,
            url="https://example.com",
            created="2025-12-04"
        )

        # Then: YAMLは生成されるが、タグは空
        assert "tags:" in yaml
        assert "url:" in yaml

    def test_single_tag(self):
        """単一タグの処理"""
        # Given
        tags = ["単一タグ"]

        # When
        yaml = MarkdownGenerator._generate_yaml_front_matter(
            tags=tags,
            url="https://example.com",
            created="2025-12-04"
        )

        # Then
        assert "  - 単一タグ" in yaml

    def test_very_short_title(self):
        """非常に短いタイトル"""
        # Given
        short_title = "A"

        # When
        filename = MarkdownGenerator.generate_filename(short_title)

        # Then: 正常に生成される
        assert short_title in filename
        assert len(filename) <= Settings.MAX_FILENAME_LENGTH

    def test_title_with_only_spaces(self):
        """空白のみのタイトル"""
        # Given
        spaces_only = "     "

        # When
        sanitized = MarkdownGenerator._sanitize_filename(spaces_only)

        # Then: "untitled" にフォールバック
        assert sanitized == "untitled"

    def test_generate_with_newlines_in_description(self):
        """改行を含む概要テキスト"""
        # Given
        description = "これは\n複数行の\n概要テキストです。"

        # When
        markdown = MarkdownGenerator.generate(
            title="記事",
            url="https://example.com",
            description=description,
            tags=["テスト"]
        )

        # Then: 改行が保持されている
        assert description in markdown

    def test_generate_with_special_markdown_characters(self):
        """Markdown特殊文字を含むタイトル"""
        # Given
        title_with_markdown = "記事タイトル **太字** _イタリック_ `コード`"

        # When
        markdown = MarkdownGenerator.generate(
            title=title_with_markdown,
            url="https://example.com",
            description=None,
            tags=["テスト"]
        )

        # Then: 特殊文字がそのまま含まれている（エスケープされない）
        assert title_with_markdown in markdown
