"""プロジェクト基盤セットアップのテスト"""
import tomli
from pathlib import Path


def test_pyproject_toml_exists():
    """pyproject.tomlが存在することを確認"""
    pyproject_path = Path("pyproject.toml")
    assert pyproject_path.exists(), "pyproject.toml が存在しません"


def test_pyproject_toml_has_required_fields():
    """pyproject.tomlに必要なフィールドが含まれていることを確認"""
    with open("pyproject.toml", "rb") as f:
        config = tomli.load(f)

    # プロジェクト基本情報の確認
    assert "tool" in config
    assert "poetry" in config["tool"]
    poetry = config["tool"]["poetry"]

    assert "name" in poetry
    assert poetry["name"] == "article-stock-bot"
    assert "version" in poetry
    assert "description" in poetry
    assert "python" in poetry["dependencies"]


def test_pyproject_toml_has_required_dependencies():
    """pyproject.tomlに必要な依存パッケージが含まれていることを確認"""
    with open("pyproject.toml", "rb") as f:
        config = tomli.load(f)

    deps = config["tool"]["poetry"]["dependencies"]

    # 必須の依存パッケージ
    required_deps = [
        "discord.py",
        "beautifulsoup4",
        "aiohttp",
        "google-generativeai",
        "GitPython",
        "python-dotenv",
    ]

    for dep in required_deps:
        assert dep in deps, f"{dep} が依存パッケージに含まれていません"


def test_gitignore_exists():
    """.gitignoreが存在することを確認"""
    gitignore_path = Path(".gitignore")
    assert gitignore_path.exists(), ".gitignore が存在しません"


def test_gitignore_has_required_entries():
    """.gitignoreに必要なエントリが含まれていることを確認"""
    with open(".gitignore", "r") as f:
        content = f.read()

    # 必須のエントリ
    required_entries = [".env", "logs/", "vault/"]

    for entry in required_entries:
        assert entry in content, f"{entry} が.gitignoreに含まれていません"
