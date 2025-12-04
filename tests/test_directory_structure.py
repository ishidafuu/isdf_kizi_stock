"""ディレクトリ構造とロギング設定のテスト"""
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler


def test_required_directories_exist():
    """必要なディレクトリが存在することを確認"""
    required_dirs = [
        "src/bot",
        "src/scraper",
        "src/ai",
        "src/storage",
        "src/utils",
        "config",
        "tests",
        "logs",
        "vault/articles",
    ]

    for dir_path in required_dirs:
        path = Path(dir_path)
        assert path.exists(), f"{dir_path} ディレクトリが存在しません"
        assert path.is_dir(), f"{dir_path} がディレクトリではありません"


def test_logger_module_exists():
    """logger.pyモジュールが存在することを確認"""
    logger_path = Path("src/utils/logger.py")
    assert logger_path.exists(), "src/utils/logger.py が存在しません"


def test_logger_setup_function():
    """ロガーセットアップ関数が正しく動作することを確認"""
    from src.utils.logger import setup_logger

    # テスト用ロガーを作成
    test_log_file = "logs/test.log"
    logger = setup_logger("test_logger", test_log_file)

    # ロガーが正しく作成されていることを確認
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"

    # RotatingFileHandlerが設定されていることを確認
    handlers = [h for h in logger.handlers if isinstance(h, RotatingFileHandler)]
    assert len(handlers) > 0, "RotatingFileHandler が設定されていません"

    # ファイルサイズ制限の確認（10MB）
    rotating_handler = handlers[0]
    assert rotating_handler.maxBytes == 10 * 1024 * 1024, "ログファイルサイズ制限が10MBではありません"

    # バックアップカウントの確認（7日分）
    assert rotating_handler.backupCount == 7, "ログファイルのバックアップカウントが7ではありません"


def test_log_exception_function():
    """例外ログ記録関数が存在することを確認"""
    from src.utils.logger import log_exception

    # テスト用ロガーを作成
    logger = logging.getLogger("test_exception_logger")

    # 例外を発生させてログ記録をテスト
    try:
        raise ValueError("テスト例外")
    except ValueError as e:
        # 関数が正常に呼び出せることを確認
        log_exception(logger, "テストメッセージ", e, notify_admin=False)
