"""コンテンツパーサー

Discord メッセージの内容を解析し、URL、コメント、メモを判別・抽出します。
- URL抽出（HTTP/HTTPSプロトコルのみ）
- 複数URL検出時は最初のURLのみ処理、残りはコメントとして扱う
- URL単体、URL+コメント、テキストのみの各パターンに対応
"""

import re
from typing import Dict, Optional


class ContentParser:
    """コンテンツパーサークラス

    DiscordメッセージからURL、コメント、メモを抽出します。
    """

    # HTTP/HTTPSプロトコルを含む有効なURL形式の正規表現
    URL_PATTERN = re.compile(
        r"https?://[^\s<>\"]+",
        re.IGNORECASE
    )

    @classmethod
    def parse_message(cls, content: str) -> Dict[str, Optional[str]]:
        """
        メッセージ内容を解析（Requirement 2.1-2.5）

        Preconditions:
        - contentが文字列

        Postconditions:
        - URLが含まれる場合: {"url": str, "comment": str or None}
        - URLが含まれない場合: {"url": None, "memo": str}
        - 複数URLが含まれる場合: 最初のURLのみを抽出、残りはコメントに含める

        Args:
            content: Discordメッセージの内容

        Returns:
            Dict[str, Optional[str]]: 解析結果
                - url: 抽出されたURL（なければNone）
                - comment: URL以外のテキスト（URL投稿時）
                - memo: テキスト全体（URL無し投稿時）
        """
        if not content or not content.strip():
            return {"url": None, "memo": ""}

        # URLを検索
        urls = cls.URL_PATTERN.findall(content)

        # URL が含まれない場合はメモとして扱う（Requirement 2.3）
        if not urls:
            return {
                "url": None,
                "memo": content.strip()
            }

        # 最初のURLのみを処理対象とする（Requirement 2.4）
        first_url = urls[0]

        # URL以外のテキストを抽出（コメント部分）
        comment_text = content.replace(first_url, "", 1).strip()

        # 複数URLがある場合、2番目以降のURLもコメントに含まれる
        if len(urls) > 1:
            # 既にcomment_textに含まれているのでそのまま使用
            pass

        # URL+コメントの組み合わせ（Requirement 2.2）
        return {
            "url": first_url,
            "comment": comment_text if comment_text else None
        }

    @classmethod
    def extract_urls(cls, content: str) -> list[str]:
        """
        メッセージから全URLを抽出（デバッグ・テスト用）

        Args:
            content: Discordメッセージの内容

        Returns:
            list[str]: 抽出されたURLのリスト
        """
        return cls.URL_PATTERN.findall(content)

    @classmethod
    def validate_url(cls, url: str) -> bool:
        """
        URLの妥当性を検証（Requirement 2.5）

        Args:
            url: 検証するURL

        Returns:
            bool: 有効なURL形式の場合True
        """
        if not url:
            return False

        match = cls.URL_PATTERN.fullmatch(url)
        return match is not None

    @classmethod
    def is_url_message(cls, content: str) -> bool:
        """
        メッセージにURLが含まれるか判定

        Args:
            content: Discordメッセージの内容

        Returns:
            bool: URLが含まれる場合True
        """
        urls = cls.URL_PATTERN.findall(content)
        return len(urls) > 0
