"""systemdサービスファイルの検証テスト

タスク12.2: systemdサービス化の設定
- Botをバックグラウンドで起動するためのsystemdユニットファイル作成
- 自動再起動の設定
- ログ出力の設定
"""

from pathlib import Path


def test_systemd_service_file_exists():
    """systemdサービスファイルが存在することを確認"""
    service_file = Path("deployment/article-stock-bot.service")
    assert service_file.exists(), "systemdサービスファイルが存在しません"


def test_systemd_service_file_has_required_sections():
    """systemdサービスファイルに必須セクションが含まれることを確認"""
    service_file = Path("deployment/article-stock-bot.service")
    content = service_file.read_text()

    # 必須セクションの確認
    assert "[Unit]" in content, "[Unit]セクションが存在しません"
    assert "[Service]" in content, "[Service]セクションが存在しません"
    assert "[Install]" in content, "[Install]セクションが存在しません"


def test_systemd_service_file_has_restart_configuration():
    """自動再起動の設定が含まれることを確認"""
    service_file = Path("deployment/article-stock-bot.service")
    content = service_file.read_text()

    # 自動再起動の設定
    assert "Restart=" in content, "Restart設定が存在しません"
    assert "RestartSec=" in content, "RestartSec設定が存在しません"


def test_systemd_service_file_has_logging_configuration():
    """ログ出力の設定が含まれることを確認"""
    service_file = Path("deployment/article-stock-bot.service")
    content = service_file.read_text()

    # ログ出力の設定（StandardOutput/StandardError）
    assert (
        "StandardOutput=" in content or "SyslogIdentifier=" in content
    ), "ログ出力設定が存在しません"


def test_systemd_service_file_has_correct_exec_start():
    """ExecStartが正しく設定されていることを確認"""
    service_file = Path("deployment/article-stock-bot.service")
    content = service_file.read_text()

    # ExecStartの設定
    assert "ExecStart=" in content, "ExecStart設定が存在しません"
    # Poetryまたはpython3を使用した起動コマンドが含まれる
    assert (
        "poetry run python main.py" in content or
        "python3 main.py" in content or
        "/usr/bin/python3" in content
    ), "起動コマンドが正しく設定されていません"


def test_systemd_service_file_has_working_directory():
    """WorkingDirectoryが設定されていることを確認"""
    service_file = Path("deployment/article-stock-bot.service")
    content = service_file.read_text()

    # WorkingDirectoryの設定
    assert "WorkingDirectory=" in content, "WorkingDirectory設定が存在しません"


def test_systemd_service_file_has_user_configuration():
    """ユーザー設定が含まれることを確認"""
    service_file = Path("deployment/article-stock-bot.service")
    content = service_file.read_text()

    # User設定（オプションだが、セキュリティのため推奨）
    assert "User=" in content, "User設定が存在しません"


def test_systemd_service_file_has_wantedby_multi_user():
    """multi-user.targetでの起動設定が含まれることを確認"""
    service_file = Path("deployment/article-stock-bot.service")
    content = service_file.read_text()

    # multi-user.targetでの起動
    assert "WantedBy=multi-user.target" in content, "WantedBy設定が正しくありません"
