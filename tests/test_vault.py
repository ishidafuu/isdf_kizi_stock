"""VaultStorage のユニットテスト

Requirement 5.8, 8.2, 8.3 のテスト
- 既存ファイルへのコメント追記確認
- 日付フォーマット確認
- ファイル不在時のエラーハンドリング確認
- pytest の tmp_path fixture を使用した一時ディレクトリテスト
"""

import re
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.storage.vault import VaultStorage


class TestVaultStorage:
    """VaultStorage クラスのテスト"""

    @pytest.fixture
    def vault_storage(self, tmp_path):
        """
        VaultStorageインスタンスを一時ディレクトリで作成

        Args:
            tmp_path: pytest の tmp_path fixture（一時ディレクトリ）
        """
        # Settings.get_vault_articles_path() をモック化して tmp_path を返す
        with patch('src.storage.vault.Settings.get_vault_articles_path', return_value=tmp_path):
            with patch('src.storage.vault.Settings.LOG_FILE_PATH', str(tmp_path / "test.log")):
                storage = VaultStorage()
                # articles_dir を tmp_path に設定
                storage.articles_dir = tmp_path
                return storage

    @pytest.fixture
    def sample_article_content(self):
        """サンプルの記事コンテンツ"""
        return """---
tags:
  - Python
  - テスト
url: https://example.com/test-article
created: 2025-12-04
---

# テスト記事

## 概要

これはテスト用の記事です。

**補足:** Geminiによる要約補足テキスト

## コメント

**2025-12-04:**
初回投稿時のコメント
"""

    @pytest.mark.asyncio
    async def test_save_article_creates_file(self, vault_storage, tmp_path):
        """Requirement 5.8: 記事ファイルが正常に保存される"""
        # Given
        title = "テスト記事タイトル"
        content = "# テスト記事\n\nこれはテストコンテンツです。"

        # When
        file_path = await vault_storage.save_article(title, content)

        # Then: ファイルが作成される
        assert file_path.exists()
        assert file_path.parent == tmp_path
        # コンテンツが正しく保存される
        saved_content = file_path.read_text(encoding="utf-8")
        assert saved_content == content

    @pytest.mark.asyncio
    async def test_save_article_filename_format(self, vault_storage):
        """Requirement 5.8: ファイル名が正しい形式で生成される"""
        # Given
        title = "記事タイトル"
        content = "# 記事"

        # When
        file_path = await vault_storage.save_article(title, content)

        # Then: ファイル名が YYYY-MM-DD_タイトル.md 形式
        expected_date = datetime.now().strftime("%Y-%m-%d")
        assert file_path.name.startswith(expected_date)
        assert file_path.name.endswith(".md")
        assert "記事タイトル" in file_path.name

    @pytest.mark.asyncio
    async def test_save_memo_creates_file(self, vault_storage, tmp_path):
        """メモが正常に保存される"""
        # Given
        content = "# メモ\n\nこれはテストメモです。"

        # When
        file_path = await vault_storage.save_memo(content)

        # Then: ファイルが作成される
        assert file_path.exists()
        assert file_path.parent == tmp_path
        assert "_memo.md" in file_path.name

    @pytest.mark.asyncio
    async def test_append_comment_to_existing_file(self, vault_storage, tmp_path, sample_article_content):
        """Requirement 8.2: 既存ファイルにコメントを追記できる"""
        # Given: 既存の記事ファイルを作成
        file_path = tmp_path / "2025-12-04_test_article.md"
        file_path.write_text(sample_article_content, encoding="utf-8")

        # When: コメントを追記
        new_comment = "これは追記されたコメントです。"
        await vault_storage.append_comment(file_path, new_comment)

        # Then: コメントが追記されている
        updated_content = file_path.read_text(encoding="utf-8")
        assert new_comment in updated_content
        # 元のコンテンツも保持されている
        assert "初回投稿時のコメント" in updated_content

    @pytest.mark.asyncio
    async def test_append_comment_date_format(self, vault_storage, tmp_path, sample_article_content):
        """Requirement 8.3: コメントの日付が YYYY-MM-DD 形式で記録される"""
        # Given: 既存の記事ファイルを作成
        file_path = tmp_path / "2025-12-04_test_article.md"
        file_path.write_text(sample_article_content, encoding="utf-8")

        # When: コメントを追記
        new_comment = "日付フォーマット確認用コメント"
        await vault_storage.append_comment(file_path, new_comment)

        # Then: YYYY-MM-DD形式の日付が含まれている
        updated_content = file_path.read_text(encoding="utf-8")
        date_pattern = r"\*\*\d{4}-\d{2}-\d{2}:\*\*"
        assert re.search(date_pattern, updated_content)
        # 現在日付が含まれている
        expected_date = datetime.now().strftime("%Y-%m-%d")
        assert f"**{expected_date}:**" in updated_content

    @pytest.mark.asyncio
    async def test_append_comment_to_file_without_comment_section(self, vault_storage, tmp_path):
        """Requirement 8.2: コメントセクションがないファイルに新規セクションを作成"""
        # Given: コメントセクションがない記事ファイル
        content_without_comment = """---
tags:
  - テスト
url: https://example.com/test
created: 2025-12-04
---

# テスト記事

## 概要

概要テキスト
"""
        file_path = tmp_path / "2025-12-04_test.md"
        file_path.write_text(content_without_comment, encoding="utf-8")

        # When: コメントを追記
        new_comment = "新規コメント"
        await vault_storage.append_comment(file_path, new_comment)

        # Then: コメントセクションが作成される
        updated_content = file_path.read_text(encoding="utf-8")
        assert "## コメント" in updated_content
        assert new_comment in updated_content
        # 日付も含まれる
        expected_date = datetime.now().strftime("%Y-%m-%d")
        assert f"**{expected_date}:**" in updated_content

    @pytest.mark.asyncio
    async def test_append_comment_multiple_times(self, vault_storage, tmp_path, sample_article_content):
        """Requirement 8.2: 複数回のコメント追記が正常に動作する"""
        # Given: 既存の記事ファイル
        file_path = tmp_path / "2025-12-04_test_article.md"
        file_path.write_text(sample_article_content, encoding="utf-8")

        # When: 複数回コメントを追記
        comment1 = "最初の追記コメント"
        comment2 = "二番目の追記コメント"
        comment3 = "三番目の追記コメント"

        await vault_storage.append_comment(file_path, comment1)
        await vault_storage.append_comment(file_path, comment2)
        await vault_storage.append_comment(file_path, comment3)

        # Then: すべてのコメントが追記されている
        updated_content = file_path.read_text(encoding="utf-8")
        assert comment1 in updated_content
        assert comment2 in updated_content
        assert comment3 in updated_content
        # 元のコメントも保持されている
        assert "初回投稿時のコメント" in updated_content

    @pytest.mark.asyncio
    async def test_append_comment_file_not_found_error(self, vault_storage, tmp_path):
        """Requirement 5.8, 8.2: ファイルが存在しない場合 FileNotFoundError が発生"""
        # Given: 存在しないファイルパス
        non_existent_file = tmp_path / "non_existent_file.md"

        # When/Then: FileNotFoundError が発生
        with pytest.raises(FileNotFoundError) as exc_info:
            await vault_storage.append_comment(non_existent_file, "コメント")

        # エラーメッセージにファイル名が含まれる
        assert str(non_existent_file) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_append_comment_preserves_formatting(self, vault_storage, tmp_path):
        """Requirement 8.2: コメント追記時に既存フォーマットが保持される"""
        # Given: フォーマットされた記事
        formatted_content = """---
tags:
  - Python
  - テスト
url: https://example.com/test
created: 2025-12-04
---

# テスト記事

## 概要

概要テキスト

## コメント

**2025-12-04:**
初回コメント
"""
        file_path = tmp_path / "2025-12-04_formatted.md"
        file_path.write_text(formatted_content, encoding="utf-8")

        # When: コメントを追記
        new_comment = "新規コメント"
        await vault_storage.append_comment(file_path, new_comment)

        # Then: フォーマットが保持される
        updated_content = file_path.read_text(encoding="utf-8")
        # YAMLフロントマターが保持される
        assert "---" in updated_content
        assert "tags:" in updated_content
        # セクションが保持される
        assert "## 概要" in updated_content
        assert "## コメント" in updated_content
        # 元のコメントも保持される
        assert "初回コメント" in updated_content

    @pytest.mark.asyncio
    async def test_append_comment_with_multiline_text(self, vault_storage, tmp_path, sample_article_content):
        """Requirement 8.2: 複数行のコメントを追記できる"""
        # Given: 既存の記事ファイル
        file_path = tmp_path / "2025-12-04_test_article.md"
        file_path.write_text(sample_article_content, encoding="utf-8")

        # When: 複数行のコメントを追記
        multiline_comment = """これは複数行の
コメントです。
複数行でも正常に動作します。"""
        await vault_storage.append_comment(file_path, multiline_comment)

        # Then: 複数行のコメントが追記される
        updated_content = file_path.read_text(encoding="utf-8")
        assert multiline_comment in updated_content

    def test_find_article_by_url_finds_article(self, vault_storage, tmp_path):
        """URLから記事ファイルを検索できる"""
        # Given: URLを含む記事ファイル
        test_url = "https://example.com/test-article"
        content = f"""---
tags:
  - テスト
url: {test_url}
created: 2025-12-04
---

# テスト記事
"""
        file_path = tmp_path / "2025-12-04_test.md"
        file_path.write_text(content, encoding="utf-8")

        # When: URLで記事を検索
        found_path = vault_storage.find_article_by_url(test_url)

        # Then: 記事が見つかる
        assert found_path is not None
        assert found_path == file_path

    def test_find_article_by_url_not_found(self, vault_storage, tmp_path):
        """URLが存在しない場合はNoneを返す"""
        # Given: 記事ファイルが存在しない
        non_existent_url = "https://example.com/non-existent"

        # When: URLで記事を検索
        found_path = vault_storage.find_article_by_url(non_existent_url)

        # Then: Noneが返る
        assert found_path is None

    def test_find_article_by_url_multiple_files(self, vault_storage, tmp_path):
        """複数のファイルがある場合に正しいファイルを検索できる"""
        # Given: 複数の記事ファイル
        url1 = "https://example.com/article1"
        url2 = "https://example.com/article2"

        content1 = f"---\ntags:\n  - テスト\nurl: {url1}\ncreated: 2025-12-04\n---\n\n# 記事1"
        content2 = f"---\ntags:\n  - テスト\nurl: {url2}\ncreated: 2025-12-04\n---\n\n# 記事2"

        file1 = tmp_path / "2025-12-04_article1.md"
        file2 = tmp_path / "2025-12-04_article2.md"

        file1.write_text(content1, encoding="utf-8")
        file2.write_text(content2, encoding="utf-8")

        # When: 特定のURLで検索
        found_path = vault_storage.find_article_by_url(url2)

        # Then: 正しいファイルが見つかる
        assert found_path == file2

    def test_ensure_directory_exists_creates_directory(self, tmp_path):
        """Requirement 5.8: ディレクトリが存在しない場合は自動作成される"""
        # Given: 存在しないディレクトリパス
        new_dir = tmp_path / "new_vault" / "articles"
        assert not new_dir.exists()

        # When: VaultStorageを初期化
        with patch('src.storage.vault.Settings.get_vault_articles_path', return_value=new_dir):
            with patch('src.storage.vault.Settings.LOG_FILE_PATH', str(tmp_path / "test.log")):
                storage = VaultStorage()

        # Then: ディレクトリが作成される
        assert new_dir.exists()
        assert new_dir.is_dir()

    @pytest.mark.asyncio
    async def test_append_comment_with_special_characters(self, vault_storage, tmp_path, sample_article_content):
        """Requirement 8.2: 特殊文字を含むコメントを追記できる"""
        # Given: 既存の記事ファイル
        file_path = tmp_path / "2025-12-04_test_article.md"
        file_path.write_text(sample_article_content, encoding="utf-8")

        # When: 特殊文字を含むコメントを追記
        special_comment = "特殊文字: **太字** _イタリック_ `コード` [リンク](https://example.com)"
        await vault_storage.append_comment(file_path, special_comment)

        # Then: 特殊文字が保持される
        updated_content = file_path.read_text(encoding="utf-8")
        assert special_comment in updated_content

    @pytest.mark.asyncio
    async def test_save_article_with_japanese_title(self, vault_storage, tmp_path):
        """Requirement 5.8: 日本語タイトルで記事を保存できる"""
        # Given
        title = "日本語のタイトル"
        content = "# 日本語記事\n\n日本語のコンテンツです。"

        # When
        file_path = await vault_storage.save_article(title, content)

        # Then: ファイルが作成され、日本語が保持される
        assert file_path.exists()
        assert "日本語のタイトル" in file_path.name
        saved_content = file_path.read_text(encoding="utf-8")
        assert saved_content == content


class TestVaultStorageEdgeCases:
    """エッジケースのテスト"""

    @pytest.fixture
    def vault_storage(self, tmp_path):
        """VaultStorageインスタンスを一時ディレクトリで作成"""
        with patch('src.storage.vault.Settings.get_vault_articles_path', return_value=tmp_path):
            with patch('src.storage.vault.Settings.LOG_FILE_PATH', str(tmp_path / "test.log")):
                storage = VaultStorage()
                storage.articles_dir = tmp_path
                return storage

    @pytest.mark.asyncio
    async def test_append_comment_empty_comment(self, vault_storage, tmp_path):
        """空のコメントを追記する"""
        # Given: 既存の記事ファイル
        content = """---
tags:
  - テスト
url: https://example.com/test
created: 2025-12-04
---

# テスト記事

## コメント

**2025-12-04:**
初回コメント
"""
        file_path = tmp_path / "2025-12-04_test.md"
        file_path.write_text(content, encoding="utf-8")

        # When: 空のコメントを追記
        await vault_storage.append_comment(file_path, "")

        # Then: 日付のみが追記される
        updated_content = file_path.read_text(encoding="utf-8")
        expected_date = datetime.now().strftime("%Y-%m-%d")
        assert f"**{expected_date}:**" in updated_content

    @pytest.mark.asyncio
    async def test_append_comment_to_empty_file(self, vault_storage, tmp_path):
        """空のファイルにコメントを追記する"""
        # Given: 空のファイル
        file_path = tmp_path / "empty.md"
        file_path.write_text("", encoding="utf-8")

        # When: コメントを追記
        new_comment = "空ファイルへのコメント"
        await vault_storage.append_comment(file_path, new_comment)

        # Then: コメントセクションが作成される
        updated_content = file_path.read_text(encoding="utf-8")
        assert "## コメント" in updated_content
        assert new_comment in updated_content

    @pytest.mark.asyncio
    async def test_save_article_very_long_content(self, vault_storage):
        """非常に長いコンテンツを保存できる"""
        # Given: 非常に長いコンテンツ
        title = "長いコンテンツの記事"
        long_content = "# 長い記事\n\n" + "あ" * 10000

        # When
        file_path = await vault_storage.save_article(title, long_content)

        # Then: ファイルが正常に保存される
        assert file_path.exists()
        saved_content = file_path.read_text(encoding="utf-8")
        assert len(saved_content) == len(long_content)

    def test_find_article_by_url_with_encoded_url(self, vault_storage, tmp_path):
        """エンコードされたURLで記事を検索できる"""
        # Given: URLエンコードされたURLを含む記事
        encoded_url = "https://example.com/test?query=%E3%83%86%E3%82%B9%E3%83%88"
        content = f"""---
tags:
  - テスト
url: {encoded_url}
created: 2025-12-04
---

# テスト記事
"""
        file_path = tmp_path / "2025-12-04_test.md"
        file_path.write_text(content, encoding="utf-8")

        # When: エンコードされたURLで検索
        found_path = vault_storage.find_article_by_url(encoded_url)

        # Then: 記事が見つかる
        assert found_path == file_path
