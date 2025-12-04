"""Markdown生成

記事情報からMarkdownファイルを生成します。
- YAMLフロントマター（tags, url, created）
- Markdownボディ（タイトル、概要、コメント）
- ファイル名のサニタイゼーション
"""

import re
from datetime import datetime
from typing import List, Optional

from config.settings import Settings


class MarkdownGenerator:
    """Markdownファイル生成クラス

    記事情報からObsidian用のMarkdownファイルを生成します。
    """

    @staticmethod
    def generate(
        title: str,
        url: str,
        description: Optional[str],
        tags: List[str],
        summary: Optional[str] = None,
        comment: Optional[str] = None
    ) -> str:
        """
        Markdownファイルの内容を生成（Requirement 5.1-5.5）

        Preconditions:
        - titleが記事タイトル文字列
        - urlが有効なURL文字列
        - tagsがタグリスト（3〜5個）

        Postconditions:
        - YAMLフロントマターとMarkdownボディを含む文字列を返す

        Args:
            title: 記事タイトル
            url: 記事URL
            description: 記事概要
            tags: タグリスト
            summary: Geminiによる要約補足
            comment: ユーザーコメント

        Returns:
            str: Markdown形式の文字列
        """
        # 現在日時（YYYY-MM-DD形式）
        created_date = datetime.now().strftime("%Y-%m-%d")

        # YAMLフロントマターを生成（Requirement 5.2）
        yaml_front_matter = MarkdownGenerator._generate_yaml_front_matter(
            tags=tags,
            url=url,
            created=created_date
        )

        # Markdownボディを生成（Requirement 5.3）
        markdown_body = MarkdownGenerator._generate_markdown_body(
            title=title,
            description=description,
            summary=summary,
            comment=comment
        )

        # 結合して返す
        return f"{yaml_front_matter}\n{markdown_body}"

    @staticmethod
    def generate_memo(memo: str) -> str:
        """
        メモ用Markdownファイルの内容を生成

        Args:
            memo: メモテキスト

        Returns:
            str: Markdown形式の文字列
        """
        created_date = datetime.now().strftime("%Y-%m-%d")

        yaml_front_matter = MarkdownGenerator._generate_yaml_front_matter(
            tags=["メモ"],
            url=None,
            created=created_date
        )

        markdown_body = f"# メモ\n\n{memo}\n"

        return f"{yaml_front_matter}\n{markdown_body}"

    @staticmethod
    def _generate_yaml_front_matter(
        tags: List[str],
        url: Optional[str],
        created: str
    ) -> str:
        """
        YAMLフロントマターを生成（Requirement 5.2）

        Args:
            tags: タグリスト
            url: 記事URL
            created: 作成日（YYYY-MM-DD形式）

        Returns:
            str: YAMLフロントマター
        """
        # タグをYAML配列形式に変換
        tags_yaml = "\n".join([f"  - {tag}" for tag in tags])

        yaml = f"""---
tags:
{tags_yaml}
"""

        if url:
            yaml += f"url: {url}\n"

        yaml += f"created: {created}\n---\n"

        return yaml

    @staticmethod
    def _generate_markdown_body(
        title: str,
        description: Optional[str],
        summary: Optional[str],
        comment: Optional[str]
    ) -> str:
        """
        Markdownボディを生成（Requirement 5.3, 5.4, 5.5）

        Args:
            title: 記事タイトル
            description: 記事概要
            summary: Geminiによる要約補足
            comment: ユーザーコメント

        Returns:
            str: Markdownボディ
        """
        # タイトル（Requirement 5.3）
        body = f"# {title}\n\n"

        # 概要セクション（Requirement 5.4）
        if description or summary:
            body += "## 概要\n\n"
            if description:
                body += f"{description}\n\n"
            if summary:
                body += f"**補足:** {summary}\n\n"

        # コメントセクション（Requirement 5.5）
        if comment:
            created_date = datetime.now().strftime("%Y-%m-%d")
            body += "## コメント\n\n"
            body += f"**{created_date}:**\n{comment}\n\n"

        return body

    @staticmethod
    def generate_filename(title: str) -> str:
        """
        ファイル名を生成（Requirement 5.6, 5.7）

        Preconditions:
        - titleが記事タイトル文字列

        Postconditions:
        - YYYY-MM-DD_記事タイトル.md 形式のファイル名を返す
        - 使用できない文字はサニタイズされる
        - 最大100文字に制限される

        Args:
            title: 記事タイトル

        Returns:
            str: サニタイズされたファイル名
        """
        # 現在日付（YYYY-MM-DD形式）
        date_prefix = datetime.now().strftime("%Y-%m-%d")

        # タイトルをサニタイズ（Requirement 5.7）
        sanitized_title = MarkdownGenerator._sanitize_filename(title)

        # ファイル名を生成
        filename = f"{date_prefix}_{sanitized_title}.md"

        # 最大長を100文字に制限（Requirement 5.7）
        if len(filename) > Settings.MAX_FILENAME_LENGTH:
            # .mdの拡張子分（3文字）を考慮
            max_title_length = Settings.MAX_FILENAME_LENGTH - len(date_prefix) - 1 - 3
            sanitized_title = sanitized_title[:max_title_length]
            filename = f"{date_prefix}_{sanitized_title}.md"

        return filename

    @staticmethod
    def _sanitize_filename(title: str) -> str:
        """
        ファイル名をサニタイズ（Requirement 5.7）

        使用できない文字を除去: / \ : * ? " < > |

        Args:
            title: 元のタイトル

        Returns:
            str: サニタイズされたタイトル
        """
        # 使用できない文字を除去
        sanitized = re.sub(
            f"[{re.escape(Settings.INVALID_FILENAME_CHARS)}]",
            "",
            title
        )

        # 連続する空白を単一のスペースに置換
        sanitized = re.sub(r"\s+", " ", sanitized)

        # 前後の空白を除去
        sanitized = sanitized.strip()

        # 空文字列になった場合のフォールバック
        if not sanitized:
            sanitized = "untitled"

        return sanitized
