"""GeminiClient のユニットテスト

Requirements coverage:
- 4.1: 記事タイトルと概要をGemini Flash 2.5 APIに送信
- 4.2: 3個から5個のタグを抽出
- 4.3: 日本語の単語または短いフレーズ形式のタグ
- 4.4: 要約補足テキストを受信
- 4.5: API呼び出し失敗時のデフォルトタグ適用
- 4.6: 適切なプロンプトテンプレートを使用
- 4.7: タイムアウト時のフォールバック処理
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config.settings import Settings
from src.ai.gemini import GeminiClient


class TestGeminiClientGenerateTagsAndSummary:
    """generate_tags_and_summary メソッドのテスト"""

    @pytest.mark.asyncio
    @patch("src.ai.gemini.genai.GenerativeModel")
    async def test_generate_tags_and_summary_success_3_tags(self, mock_model_class):
        """正常系: 3個のタグと要約補足を生成できる (Requirement 4.1, 4.2, 4.3, 4.4)"""
        # Given
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "tags": ["Python", "Web開発", "Flask"],
            "summary": "Flaskを使った簡単なWebアプリケーションの構築方法を解説。"
        })

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        client = GeminiClient()

        # When
        result = await client.generate_tags_and_summary(
            title="FlaskでWebアプリを作る",
            description="Flaskフレームワークの基本的な使い方"
        )

        # Then
        assert result["tags"] == ["Python", "Web開発", "Flask"]
        assert result["summary"] == "Flaskを使った簡単なWebアプリケーションの構築方法を解説。"
        assert len(result["tags"]) >= Settings.MIN_TAG_COUNT
        assert len(result["tags"]) <= Settings.MAX_TAG_COUNT

    @pytest.mark.asyncio
    @patch("src.ai.gemini.genai.GenerativeModel")
    async def test_generate_tags_and_summary_success_5_tags(self, mock_model_class):
        """正常系: 5個のタグと要約補足を生成できる (Requirement 4.2)"""
        # Given
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "tags": ["Python", "Django", "Web開発", "API", "REST"],
            "summary": "Django REST frameworkを使ったAPI開発の実践的なチュートリアル。"
        })

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        client = GeminiClient()

        # When
        result = await client.generate_tags_and_summary(
            title="Django REST APIの作り方",
            description="Django REST frameworkの使い方"
        )

        # Then
        assert len(result["tags"]) == 5
        assert result["tags"] == ["Python", "Django", "Web開発", "API", "REST"]
        assert len(result["summary"]) > 0

    @pytest.mark.asyncio
    @patch("src.ai.gemini.genai.GenerativeModel")
    async def test_generate_tags_and_summary_success_4_tags(self, mock_model_class):
        """正常系: 4個のタグを生成できる (Requirement 4.2)"""
        # Given
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "tags": ["機械学習", "TensorFlow", "Python", "AI"],
            "summary": "TensorFlowを使った機械学習モデルの構築方法。"
        })

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        client = GeminiClient()

        # When
        result = await client.generate_tags_and_summary(
            title="TensorFlowで機械学習",
            description="TensorFlowの基礎から応用まで"
        )

        # Then
        assert len(result["tags"]) == 4
        assert "機械学習" in result["tags"]

    @pytest.mark.asyncio
    @patch("src.ai.gemini.genai.GenerativeModel")
    async def test_generate_tags_and_summary_with_markdown_code_block(
        self, mock_model_class
    ):
        """正常系: Markdownコードブロック形式のレスポンスを処理できる"""
        # Given
        mock_response = MagicMock()
        mock_response.text = """```json
{
  "tags": ["Python", "非同期処理", "asyncio"],
  "summary": "Pythonの非同期処理の基礎とasyncioの使い方を解説。"
}
```"""

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        client = GeminiClient()

        # When
        result = await client.generate_tags_and_summary(
            title="Python非同期処理入門",
            description="asyncioの使い方"
        )

        # Then
        assert result["tags"] == ["Python", "非同期処理", "asyncio"]
        assert "非同期処理" in result["summary"]

    @pytest.mark.asyncio
    @patch("src.ai.gemini.genai.GenerativeModel")
    async def test_generate_tags_and_summary_adjusts_too_few_tags(
        self, mock_model_class
    ):
        """タグ数調整: タグが2個の場合、3個に調整される (Requirement 4.2)"""
        # Given
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "tags": ["Python", "Web"],
            "summary": "Webアプリケーション開発の基礎。"
        })

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        client = GeminiClient()

        # When
        result = await client.generate_tags_and_summary(
            title="Web開発入門",
            description="Webアプリの作り方"
        )

        # Then
        assert len(result["tags"]) == Settings.MIN_TAG_COUNT
        assert "Python" in result["tags"]
        assert "Web" in result["tags"]
        assert "その他" in result["tags"]

    @pytest.mark.asyncio
    @patch("src.ai.gemini.genai.GenerativeModel")
    async def test_generate_tags_and_summary_adjusts_too_many_tags(
        self, mock_model_class
    ):
        """タグ数調整: タグが6個以上の場合、5個に調整される (Requirement 4.2)"""
        # Given
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "tags": ["Python", "Django", "Web", "API", "REST", "PostgreSQL", "Docker"],
            "summary": "Django REST APIの開発環境構築から本番デプロイまで。"
        })

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        client = GeminiClient()

        # When
        result = await client.generate_tags_and_summary(
            title="Django REST API開発",
            description="実践的なAPI開発"
        )

        # Then
        assert len(result["tags"]) == Settings.MAX_TAG_COUNT
        assert result["tags"] == ["Python", "Django", "Web", "API", "REST"]

    @pytest.mark.asyncio
    @patch("src.ai.gemini.genai.GenerativeModel")
    async def test_generate_tags_and_summary_truncates_long_summary(
        self, mock_model_class
    ):
        """要約補足が100字を超える場合、切り詰められる (Requirement 4.4)"""
        # Given
        long_summary = "これは非常に長い要約補足テキストです。" * 10  # 100字を超える
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "tags": ["Python", "Django", "Web"],
            "summary": long_summary
        })

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        client = GeminiClient()

        # When
        result = await client.generate_tags_and_summary(
            title="Django入門",
            description="Djangoの基礎"
        )

        # Then
        assert len(result["summary"]) == 100

    @pytest.mark.asyncio
    @patch("src.ai.gemini.genai.GenerativeModel")
    async def test_generate_tags_and_summary_with_empty_summary(
        self, mock_model_class
    ):
        """要約補足が空の場合も正常に処理できる"""
        # Given
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "tags": ["Python", "Flask", "Web"],
            "summary": ""
        })

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        client = GeminiClient()

        # When
        result = await client.generate_tags_and_summary(
            title="Flask入門",
            description="Flaskの基礎"
        )

        # Then
        assert result["tags"] == ["Python", "Flask", "Web"]
        assert result["summary"] == ""

    @pytest.mark.asyncio
    @patch("src.ai.gemini.genai.GenerativeModel")
    async def test_generate_tags_and_summary_timeout(self, mock_model_class):
        """タイムアウト時にデフォルトタグを返す (Requirement 4.7)"""
        # Given
        mock_model = MagicMock()

        async def slow_generate(*args, **kwargs):
            await asyncio.sleep(Settings.GEMINI_TIMEOUT_SECONDS + 1)
            return MagicMock(text='{"tags": ["tag1"], "summary": ""}')

        mock_model.generate_content.return_value = None
        mock_model_class.return_value = mock_model

        client = GeminiClient()
        # _call_gemini_apiをモックして、タイムアウトをシミュレート
        client._call_gemini_api = slow_generate

        # When
        result = await client.generate_tags_and_summary(
            title="テスト記事",
            description="テスト概要"
        )

        # Then
        assert result["tags"] == Settings.DEFAULT_TAGS
        assert result["summary"] == ""

    @pytest.mark.asyncio
    @patch("src.ai.gemini.genai.GenerativeModel")
    async def test_generate_tags_and_summary_api_failure(self, mock_model_class):
        """API呼び出し失敗時にデフォルトタグを返す (Requirement 4.5)"""
        # Given
        mock_model = MagicMock()
        mock_model.generate_content.side_effect = Exception("API Error")
        mock_model_class.return_value = mock_model

        client = GeminiClient()

        # When
        result = await client.generate_tags_and_summary(
            title="テスト記事",
            description="テスト概要"
        )

        # Then
        assert result["tags"] == Settings.DEFAULT_TAGS
        assert result["summary"] == ""

    @pytest.mark.asyncio
    @patch("src.ai.gemini.genai.GenerativeModel")
    async def test_generate_tags_and_summary_invalid_json_response(
        self, mock_model_class
    ):
        """無効なJSONレスポンス時にデフォルトタグを返す (Requirement 4.5)"""
        # Given
        mock_response = MagicMock()
        mock_response.text = "This is not JSON"

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        client = GeminiClient()

        # When
        result = await client.generate_tags_and_summary(
            title="テスト記事",
            description="テスト概要"
        )

        # Then
        assert result["tags"] == Settings.DEFAULT_TAGS
        assert result["summary"] == ""

    @pytest.mark.asyncio
    @patch("src.ai.gemini.genai.GenerativeModel")
    async def test_generate_tags_and_summary_empty_response(self, mock_model_class):
        """空のレスポンス時にデフォルトタグを返す"""
        # Given
        mock_response = MagicMock()
        mock_response.text = None

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        client = GeminiClient()

        # When
        result = await client.generate_tags_and_summary(
            title="テスト記事",
            description="テスト概要"
        )

        # Then
        assert result["tags"] == Settings.DEFAULT_TAGS
        assert result["summary"] == ""

    @pytest.mark.asyncio
    @patch("src.ai.gemini.genai.GenerativeModel")
    async def test_generate_tags_and_summary_with_no_description(
        self, mock_model_class
    ):
        """概要がない場合も正常に処理できる"""
        # Given
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "tags": ["Python", "プログラミング", "入門"],
            "summary": "Python入門記事。"
        })

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        client = GeminiClient()

        # When
        result = await client.generate_tags_and_summary(
            title="Python入門",
            description=""
        )

        # Then
        assert len(result["tags"]) == 3
        assert "Python" in result["tags"]

    @pytest.mark.asyncio
    @patch("src.ai.gemini.genai.GenerativeModel")
    async def test_generate_tags_and_summary_uses_prompt_template(
        self, mock_model_class
    ):
        """適切なプロンプトテンプレートを使用する (Requirement 4.6)"""
        # Given
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "tags": ["Python", "テスト", "pytest"],
            "summary": "pytestを使ったPythonのテスト実践。"
        })

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model

        client = GeminiClient()

        title = "Pythonテスト入門"
        description = "pytestの使い方"

        # When
        result = await client.generate_tags_and_summary(
            title=title,
            description=description
        )

        # Then
        # generate_contentが呼び出されたことを確認
        mock_model.generate_content.assert_called_once()

        # 呼び出されたプロンプトにタイトルと概要が含まれていることを確認
        call_args = mock_model.generate_content.call_args[0][0]
        assert title in call_args
        assert description in call_args
        assert "タグ" in call_args
        assert "要約補足" in call_args
        assert "JSON形式" in call_args


class TestGeminiClientValidateTags:
    """_validate_tags メソッドのテスト"""

    def test_validate_tags_valid_3_tags(self):
        """3個のタグは有効 (Requirement 4.2)"""
        # Given
        client = GeminiClient()
        tags = ["Python", "Web", "Django"]

        # When
        is_valid = client._validate_tags(tags)

        # Then
        assert is_valid is True

    def test_validate_tags_valid_5_tags(self):
        """5個のタグは有効 (Requirement 4.2)"""
        # Given
        client = GeminiClient()
        tags = ["Python", "Web", "Django", "API", "REST"]

        # When
        is_valid = client._validate_tags(tags)

        # Then
        assert is_valid is True

    def test_validate_tags_invalid_2_tags(self):
        """2個のタグは無効 (Requirement 4.2)"""
        # Given
        client = GeminiClient()
        tags = ["Python", "Web"]

        # When
        is_valid = client._validate_tags(tags)

        # Then
        assert is_valid is False

    def test_validate_tags_invalid_6_tags(self):
        """6個のタグは無効 (Requirement 4.2)"""
        # Given
        client = GeminiClient()
        tags = ["Python", "Web", "Django", "API", "REST", "PostgreSQL"]

        # When
        is_valid = client._validate_tags(tags)

        # Then
        assert is_valid is False

    def test_validate_tags_empty_list(self):
        """空のタグリストは無効"""
        # Given
        client = GeminiClient()
        tags = []

        # When
        is_valid = client._validate_tags(tags)

        # Then
        assert is_valid is False


class TestGeminiClientAdjustTags:
    """_adjust_tags メソッドのテスト"""

    def test_adjust_tags_too_few(self):
        """タグが不足している場合、3個に調整される"""
        # Given
        client = GeminiClient()
        tags = ["Python"]

        # When
        adjusted = client._adjust_tags(tags)

        # Then
        assert len(adjusted) == Settings.MIN_TAG_COUNT
        assert "Python" in adjusted
        assert "その他" in adjusted

    def test_adjust_tags_too_many(self):
        """タグが多すぎる場合、5個に調整される"""
        # Given
        client = GeminiClient()
        tags = ["Python", "Django", "Web", "API", "REST", "PostgreSQL", "Docker"]

        # When
        adjusted = client._adjust_tags(tags)

        # Then
        assert len(adjusted) == Settings.MAX_TAG_COUNT
        assert adjusted == ["Python", "Django", "Web", "API", "REST"]

    def test_adjust_tags_already_valid(self):
        """既に有効なタグ数の場合、そのまま返される"""
        # Given
        client = GeminiClient()
        tags = ["Python", "Django", "Web", "API"]

        # When
        adjusted = client._adjust_tags(tags)

        # Then
        assert len(adjusted) == 4
        assert adjusted == tags


class TestGeminiClientGetFallbackResult:
    """_get_fallback_result メソッドのテスト"""

    def test_get_fallback_result(self):
        """フォールバック結果を正しく返す (Requirement 4.5)"""
        # Given
        client = GeminiClient()

        # When
        result = client._get_fallback_result()

        # Then
        assert result["tags"] == Settings.DEFAULT_TAGS
        assert result["summary"] == ""

    def test_get_fallback_result_does_not_modify_settings(self):
        """フォールバック結果の取得がSettings.DEFAULT_TAGSを変更しない"""
        # Given
        client = GeminiClient()
        original_tags = Settings.DEFAULT_TAGS.copy()

        # When
        result = client._get_fallback_result()
        result["tags"].append("追加タグ")

        # Then
        assert Settings.DEFAULT_TAGS == original_tags
