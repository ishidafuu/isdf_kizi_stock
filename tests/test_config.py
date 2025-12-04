"""環境変数管理と設定ファイルのテスト"""
from pathlib import Path


def test_env_sample_exists():
    """.env.sampleファイルが存在することを確認"""
    env_sample_path = Path(".env.sample")
    assert env_sample_path.exists(), ".env.sample が存在しません"


def test_env_sample_has_required_variables():
    """.env.sampleに必要な環境変数テンプレートが含まれていることを確認"""
    with open(".env.sample", "r") as f:
        content = f.read()

    # 必須の環境変数
    required_vars = [
        "DISCORD_BOT_TOKEN",
        "DISCORD_CHANNEL_ID",
        "GEMINI_API_KEY",
        "GITHUB_TOKEN",
        "GITHUB_REPO_URL",
        "OBSIDIAN_VAULT_PATH",
        "LOG_FILE_PATH",
    ]

    for var in required_vars:
        assert var in content, f"{var} が.env.sampleに含まれていません"


def test_settings_module_exists():
    """config/settings.pyモジュールが存在することを確認"""
    settings_path = Path("config/settings.py")
    assert settings_path.exists(), "config/settings.py が存在しません"


def test_settings_has_required_constants():
    """settings.pyに必要な設定定数が含まれていることを確認"""
    from config.settings import Settings

    # タイムアウト設定の確認
    assert hasattr(Settings, "OGP_TIMEOUT_SECONDS")
    assert Settings.OGP_TIMEOUT_SECONDS == 10

    assert hasattr(Settings, "GEMINI_TIMEOUT_SECONDS")
    assert Settings.GEMINI_TIMEOUT_SECONDS == 30

    # タグ数の設定確認
    assert hasattr(Settings, "MIN_TAG_COUNT")
    assert Settings.MIN_TAG_COUNT == 3

    assert hasattr(Settings, "MAX_TAG_COUNT")
    assert Settings.MAX_TAG_COUNT == 5

    # ファイル命名規則の確認
    assert hasattr(Settings, "MAX_FILENAME_LENGTH")
    assert Settings.MAX_FILENAME_LENGTH == 100

    # Git設定の確認
    assert hasattr(Settings, "MAX_RETRY_COUNT")
    assert Settings.MAX_RETRY_COUNT == 3


def test_settings_loads_environment_variables():
    """settings.pyが環境変数を読み込むことを確認"""
    import os
    from config.settings import Settings

    # テスト環境変数を設定
    os.environ["DISCORD_BOT_TOKEN"] = "test_token"
    os.environ["GEMINI_API_KEY"] = "test_api_key"

    # Settingsを再読み込み
    import importlib
    import config.settings

    importlib.reload(config.settings)

    # 環境変数が読み込まれていることを確認
    assert hasattr(config.settings.Settings, "DISCORD_BOT_TOKEN")
    assert config.settings.Settings.DISCORD_BOT_TOKEN == "test_token"

    assert hasattr(config.settings.Settings, "GEMINI_API_KEY")
    assert config.settings.Settings.GEMINI_API_KEY == "test_api_key"

    # クリーンアップ
    del os.environ["DISCORD_BOT_TOKEN"]
    del os.environ["GEMINI_API_KEY"]
