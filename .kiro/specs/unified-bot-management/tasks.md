# Implementation Tasks: 統一Bot管理システム

## タスク概要

Article Stock BotをPoetryベースからvenv + requirements.txt方式に移行し、既存のTennis Discovery Agentと同じ統一的な運用方式を確立する。

**マイグレーション戦略:** 新しいブランチ（`migrate-to-venv`）で作業し、ローカルで十分にテスト後、Raspberry Piにデプロイし、動作確認後に本番ブランチにマージ。

---

## Phase 1: ローカル環境での準備

### 1.1 (P) マイグレーションブランチの作成

**タスク:** 新しいブランチを作成し、現状をバックアップ

**手順:**
```bash
# 新しいブランチ作成
git checkout -b migrate-to-venv
```

**完了条件:**
- `migrate-to-venv` ブランチが作成されている

**Requirements:** なし（準備タスク）

---

### 1.2 (P) requirements.txtの生成

**タスク:** Poetryから依存関係をエクスポートしてrequirements.txtを作成

**手順:**
```bash
# Poetry環境で実行
poetry export -f requirements.txt --output requirements.txt --without-hashes

# コミット
git add requirements.txt
git commit -m "Export dependencies from Poetry to requirements.txt"
```

**完了条件:**
- `requirements.txt` が作成されている
- 以下のパッケージが含まれている:
  - discord.py
  - python-dotenv
  - beautifulsoup4
  - aiohttp
  - google-generativeai
  - GitPython
  - pytest
  - pytest-asyncio
  - aioresponses

**Requirements:** 3.2

---

### 1.3 (P) main.pyの作成

**タスク:** プロジェクトルートに `main.py` エントリーポイントを作成

**実装:**
```python
# main.py
"""
Article Stock Bot - エントリーポイント
"""
import asyncio
import os
from dotenv import load_dotenv
from src.bot.client import EventListener
from src.utils.logger import setup_logger

def main():
    """Bot起動処理"""
    # 環境変数読み込み
    load_dotenv()

    # ロガー設定
    logger = setup_logger()
    logger.info("Article Stock Bot starting...")

    # Botトークン取得
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        logger.error("DISCORD_BOT_TOKEN not found in .env")
        return

    # Bot起動
    try:
        client = EventListener()
        asyncio.run(client.start(token))
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")

if __name__ == "__main__":
    main()
```

**完了条件:**
- `main.py` が作成されている
- `EventListener` を正しくインポートしている
- 環境変数の読み込みとエラーハンドリングが実装されている

**Requirements:** 2.2

---

### 1.4 (P) logsディレクトリの作成

**タスク:** ログ出力用のディレクトリを作成

**手順:**
```bash
# logsディレクトリ作成
mkdir -p logs

# .gitkeepを作成（Gitに追跡させるため）
touch logs/.gitkeep

# コミット
git add logs/.gitkeep
git commit -m "Add logs directory for application logging"
```

**完了条件:**
- `logs/` ディレクトリが作成されている
- `logs/.gitkeep` が存在する

**Requirements:** 2.1, 9.2

---

### 1.5 (P) venv環境の作成とテスト

**タスク:** venv仮想環境を作成し、依存関係をインストールしてテスト

**手順:**
```bash
# venv作成
python3 -m venv venv

# 有効化
source venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt

# ユニットテスト実行
pytest

# カバレッジ確認（オプション）
pytest --cov=src

# 動作確認（ローカル、Botトークンが必要）
# python main.py
```

**完了条件:**
- `venv/` ディレクトリが作成されている
- すべての依存パッケージがインストールされている
- すべてのユニットテストが合格している（pytest成功）
- （オプション）main.pyがローカルで起動できる

**Requirements:** 3.1, 3.2

---

### 1.6 (P) requirements.txtの最適化

**タスク:** 不要な依存関係を削除し、必要最小限にする

**手順:**
```bash
# 必要なパッケージのみリスト
pip freeze | grep -E "discord|dotenv|beautifulsoup|aiohttp|google-generativeai|GitPython|pytest" > requirements_minimal.txt

# 確認後、置き換え（または手動で調整）
# mv requirements_minimal.txt requirements.txt

# コミット
git add requirements.txt
git commit -m "Optimize requirements.txt with minimal dependencies"
```

**完了条件:**
- `requirements.txt` に不要なパッケージが含まれていない
- 本番環境に必要なパッケージがすべて含まれている

**Requirements:** 3.3

---

### 1.7 (P) Poetryファイルの削除

**タスク:** 動作確認後、Poetryファイルを削除

**手順:**
```bash
# 動作確認後
rm -rf poetry.lock pyproject.toml

# コミット
git add .
git commit -m "Remove Poetry files, migrate to venv"
```

**完了条件:**
- `poetry.lock` が削除されている
- `pyproject.toml` が削除されている

**Requirements:** 3.2

---

## Phase 2: update_bot.shスクリプト作成

### 2.1 (P) update_bot.shスクリプトの作成

**タスク:** Tennis Botと同じ形式の更新スクリプトを作成

**実装:**
```bash
#!/bin/bash

PROJECT_DIR="isdf_kizi_stock"
SERVICE_NAME="article-bot"

echo "========================================"
echo "🔄 ${PROJECT_DIR} の更新を開始します..."
echo "========================================"

cd ~/$PROJECT_DIR || exit 1

echo "📥 Git Pull..."
git pull

echo "📦 ライブラリ更新..."
source venv/bin/activate
pip install -r requirements.txt

echo "========================================"
echo "🚀 サービスを再起動します..."
echo "========================================"

sudo systemctl restart $SERVICE_NAME
echo "✅ 再起動完了。直近のログを表示します（Ctrl+Cで終了）"
sudo journalctl -u $SERVICE_NAME -n 20 -f
```

**手順:**
```bash
# スクリプト作成
cat > update_bot.sh << 'EOF'
[上記のスクリプト内容]
EOF

# 実行権限付与
chmod +x update_bot.sh

# コミット
git add update_bot.sh
git commit -m "Add update_bot.sh script for unified management"
```

**完了条件:**
- `update_bot.sh` が作成されている
- 実行権限が付与されている（`chmod +x`）
- Tennis Botと同じフォーマットである

**Requirements:** 5.1, 5.2

---

## Phase 3: systemdサービスファイル更新

### 3.1 (P) systemdサービスファイルの作成

**タスク:** Tennis Botスタイルの統一されたサービスファイルを作成

**実装:**
```ini
[Unit]
Description=Article Stock Bot - Discord Bot for article archiving with AI tagging
After=network.target

[Service]
Type=simple
User=ishidafuu
WorkingDirectory=/home/ishidafuu/isdf_kizi_stock
ExecStart=/home/ishidafuu/isdf_kizi_stock/venv/bin/python3 /home/ishidafuu/isdf_kizi_stock/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**手順:**
```bash
# deploymentディレクトリ作成（存在しない場合）
mkdir -p deployment

# 新しいサービスファイルを作成
cat > deployment/article-bot.service << 'EOF'
[上記の内容]
EOF

# 既存のarticle-stock-bot.serviceは残しておく（後で削除）

# コミット
git add deployment/article-bot.service
git commit -m "Add unified systemd service file (article-bot.service)"
```

**完了条件:**
- `deployment/article-bot.service` が作成されている
- User: `ishidafuu`
- ExecStart: `venv/bin/python3 main.py`（Poetryではない）
- 自動再起動設定あり（Restart=always）

**Requirements:** 4.1, 4.2

---

## Phase 4: ドキュメント更新

### 4.1 (P) RASPBERRY_PI_SETUP.mdの作成

**タスク:** `docs/DEPLOYMENT.md` を `docs/RASPBERRY_PI_SETUP.md` に変更し、Tennis Bot形式に統一

**手順:**
```bash
# ファイル移動
git mv docs/DEPLOYMENT.md docs/RASPBERRY_PI_SETUP.md

# 内容を編集
nano docs/RASPBERRY_PI_SETUP.md
```

**編集内容:**
- タイトル: "Raspberry Pi セットアップ"
- Poetry関連の記述を削除
- venv + requirements.txt に変更
- update_bot.sh セクションを追加
- Tennis Botと同じセクション構成に統一:
  1. 概要
  2. OSのインストール（キーボードレイアウト設定の注意事項を含む）
  3. 必要なソフトウェアのインストール
  4. プロジェクトのセットアップ
  5. systemdによる自動起動
  6. 運用・メンテナンス（update_bot.sh、よく使うコマンド一覧表）
  7. トラブルシューティング

**完了条件:**
- `docs/RASPBERRY_PI_SETUP.md` が存在する
- Poetry関連の記述がすべて削除されている
- venv + requirements.txt の手順になっている
- update_bot.sh の説明がある
- よく使うコマンド一覧表が含まれている（表形式）

**Requirements:** 7.1, 7.2

---

### 4.2 (P) GITHUB_SETUP.mdの確認と更新

**タスク:** `docs/GITHUB_SETUP.md` の内容を確認し、必要に応じて更新

**確認事項:**
- Obsidian Vaultリポジトリのセットアップ手順が最新か
- ユーザー名が `ishidafuu` に統一されているか

**手順:**
```bash
# 内容確認
nano docs/GITHUB_SETUP.md

# 必要に応じて更新（ユーザー名等）

# コミット
git add docs/GITHUB_SETUP.md
git commit -m "Update GITHUB_SETUP.md for unified management"
```

**完了条件:**
- GITHUB_SETUP.mdの内容が最新である
- ユーザー名が `ishidafuu` に統一されている

**Requirements:** 6.1, 6.4

---

## Phase 5: .gitignoreの更新

### 5.1 (P) .gitignoreの更新

**タスク:** Poetry関連の除外を削除し、venv関連を追加

**編集内容:**
```gitignore
# Python
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python

# 環境変数
.env

# ログ
logs/
*.log

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
*.swp
*.swo

# データ
vault/
data/

# Poetry（削除）
# poetry.lock は不要になった
```

**手順:**
```bash
# .gitignoreを編集
nano .gitignore

# コミット
git add .gitignore
git commit -m "Update .gitignore for venv-based setup"
```

**完了条件:**
- `venv/` が除外されている
- Poetry関連の除外が削除されている（またはコメントアウト）

**Requirements:** 3.2

---

## Phase 6: Raspberry Piへのデプロイ

### 6.1 (P) Obsidian Vault用リポジトリのセットアップ

**タスク:** Raspberry Pi上でObsidian Vaultリポジトリをセットアップ

**手順:**
```bash
# SSH接続
ssh ishidafuu@isdf-pi.local

# ホームディレクトリに移動
cd ~

# Obsidian Vault用リポジトリをクローン（存在しない場合は作成）
# オプションA: 既存リポジトリをクローン
git clone https://github.com/ishidafuu/obsidian-vault.git
cd obsidian-vault

# vault/articlesディレクトリを作成
mkdir -p vault/articles
touch vault/articles/.gitkeep

# 初回コミット（リポジトリが空の場合のみ）
git add vault/articles/.gitkeep
git commit -m "Initial setup: Create vault/articles directory"
git push origin main
```

**完了条件:**
- Raspberry Pi上に `~/obsidian-vault` が存在する
- `vault/articles/` ディレクトリが作成されている
- GitHubにプッシュされている

**Requirements:** 6.1, 6.4

---

### 6.2 (P) Article Botプロジェクトのクローン

**タスク:** Raspberry Pi上でArticle Botプロジェクトをクローン

**手順:**
```bash
# ホームディレクトリに移動
cd ~

# 既存のArticle Botが存在する場合は削除（または別名でバックアップ）
mv isdf_kizi_stock isdf_kizi_stock.backup

# 新しくクローン
git clone https://github.com/ishidafuu/isdf_kizi_stock.git
cd isdf_kizi_stock

# migrate-to-venvブランチをチェックアウト
git checkout migrate-to-venv
```

**完了条件:**
- Raspberry Pi上に `~/isdf_kizi_stock` が存在する
- `migrate-to-venv` ブランチがチェックアウトされている

**Requirements:** なし（セットアップタスク）

---

### 6.3 (P) venv環境の作成と依存関係インストール

**タスク:** Raspberry Pi上でvenv環境を作成し、依存関係をインストール

**手順:**
```bash
# venv作成
python3 -m venv venv

# 依存関係インストール
source venv/bin/activate
pip install -r requirements.txt
```

**完了条件:**
- `venv/` ディレクトリが作成されている
- すべての依存パッケージがインストールされている

**Requirements:** 3.1

---

### 6.4 (P) .envファイルの設定

**タスク:** 環境変数ファイルを設定

**手順:**
```bash
# .envファイルを作成（既存のものをコピー、または新規作成）
if [ -f ~/isdf_kizi_stock.backup/.env ]; then
  cp ~/isdf_kizi_stock.backup/.env .env
else
  cp .env.sample .env
  # nanoで.envを編集し、トークン等を設定
  nano .env
fi

# .envでOBSIDIAN_VAULT_PATHを設定
# OBSIDIAN_VAULT_PATH=/home/ishidafuu/obsidian-vault
```

**完了条件:**
- `.env` ファイルが作成されている
- `DISCORD_BOT_TOKEN` が設定されている
- `GEMINI_API_KEY` が設定されている
- `GITHUB_TOKEN` が設定されている
- `OBSIDIAN_VAULT_PATH=/home/ishidafuu/obsidian-vault` が設定されている

**Requirements:** 5.1, 5.2

---

### 6.5 (P) logsディレクトリの作成

**タスク:** ログ出力用のディレクトリを作成

**手順:**
```bash
# ディレクトリ作成
mkdir -p logs
```

**完了条件:**
- `logs/` ディレクトリが作成されている

**Requirements:** 9.2

---

### 6.6 (P) systemdサービスの設定

**タスク:** systemdサービスファイルを配置し、サービスを有効化

**手順:**
```bash
# systemdサービスファイルを配置
sudo cp deployment/article-bot.service /etc/systemd/system/

# systemd設定リロード
sudo systemctl daemon-reload

# 自動起動を有効化
sudo systemctl enable article-bot

# サービス起動
sudo systemctl start article-bot

# 状態確認
sudo systemctl status article-bot

# ログ確認
sudo journalctl -u article-bot -f
```

**完了条件:**
- `/etc/systemd/system/article-bot.service` が存在する
- サービスが `enabled` 状態である
- サービスが `active (running)` 状態である

**Requirements:** 1.3, 4.1, 4.2

---

## Phase 7: 動作確認

### 7.1 (P) サービス起動確認

**タスク:** systemdサービスが正常に起動していることを確認

**確認手順:**
```bash
# サービス状態確認
sudo systemctl status article-bot

# 期待される出力:
# ● article-bot.service - Article Stock Bot - Discord Bot for article archiving with AI tagging
#    Loaded: loaded (/etc/systemd/system/article-bot.service; enabled; vendor preset: enabled)
#    Active: active (running) since ...
```

**完了条件:**
- サービスが `active (running)` 状態である
- エラーが発生していない

**Requirements:** 1.3

---

### 7.2 (P) ログ確認

**タスク:** Botが正常に起動し、Discordに接続できているか確認

**確認手順:**
```bash
# リアルタイムログ確認
sudo journalctl -u article-bot -f

# 期待されるログ出力:
# INFO: Article Stock Bot starting...
# INFO: Logged in as ArticleStockBot#1234
# INFO: Connected to Discord
# INFO: Monitoring channel: <channel-name> (ID: 1234567890123456789)
```

**完了条件:**
- Botが起動している
- Discordに接続している
- エラーログがない
- Discord上でBotがオンライン状態になっている

**Requirements:** 1.1, 1.5

---

### 7.3 (P) 記事URL投稿テスト

**タスク:** Discord上で記事URLを投稿し、全機能が動作するか確認

**テスト手順:**
1. Discord上で記事URLを投稿
2. Botが受信確認リアクション（👁️）を1秒以内に追加するか確認
3. OGP情報取得、Gemini呼び出し、Markdown生成、GitHubプッシュが完了するか確認
4. 成功通知がリプライされ、成功リアクション（✅）が追加されるか確認

**完了条件:**
- 受信確認リアクション（👁️）が追加される
- 成功通知がリプライされる
- 成功リアクション（✅）が追加される
- エラーが発生していない

**Requirements:** 1.1, 1.2, 1.4, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 7.5

---

### 7.4 (P) GitHubプッシュ確認

**タスク:** GitHubにMarkdownファイルが正しくプッシュされているか確認

**確認手順:**
1. `https://github.com/ishidafuu/obsidian-vault` にアクセス
2. `vault/articles/YYYY-MM-DD_記事タイトル.md` が作成されているか確認
3. ファイル内容を確認（YAMLフロントマター、タイトル、概要、コメント）

**完了条件:**
- Markdownファイルが作成されている
- ファイル名が正しい形式である（`YYYY-MM-DD_記事タイトル.md`）
- YAMLフロントマターが正しい
- OGP情報が正しく取得されている
- Geminiで生成されたタグが含まれている

**Requirements:** 3.1, 4.1, 5.1, 6.1, 6.2

---

### 7.5 (P) スレッドコメント追記テスト

**タスク:** スレッド内コメントが既存ファイルに追記されるか確認

**テスト手順:**
1. 投稿したメッセージのスレッドにコメントを追加
2. コメントが既存のMarkdownファイルに追記されるか確認
3. GitHubに再プッシュされるか確認

**完了条件:**
- スレッドコメントが検出される
- 既存ファイルにコメントが追記される
- GitHubに再プッシュされる
- スレッド内にチェックマークリアクションが追加される

**Requirements:** 8.1, 8.2, 8.3, 8.4, 8.5

---

## Phase 8: 本番マージ

### 8.1 (P) 本番ブランチへのマージ

**タスク:** 動作確認が完了したら、本番ブランチにマージ

**手順:**
```bash
# ローカルに戻る
exit

# マージ
git checkout main
git merge migrate-to-venv

# プッシュ
git push origin main
```

**完了条件:**
- `migrate-to-venv` ブランチが `main` にマージされている
- GitHubにプッシュされている

**Requirements:** なし（マージタスク）

---

### 8.2 (P) Raspberry Piで本番ブランチに切り替え

**タスク:** Raspberry Piで本番ブランチに切り替え、サービスを再起動

**手順:**
```bash
# SSH接続
ssh ishidafuu@isdf-pi.local

# プロジェクトディレクトリに移動
cd ~/isdf_kizi_stock

# 本番ブランチに切り替え
git checkout main
git pull

# サービス再起動
sudo systemctl restart article-bot

# 状態確認
sudo systemctl status article-bot
```

**完了条件:**
- Raspberry Piが `main` ブランチになっている
- サービスが正常に動作している

**Requirements:** なし（デプロイタスク）

---

### 8.3 (P) 最終動作確認

**タスク:** 本番ブランチで最終動作確認

**確認手順:**
1. Discord上で記事URLを投稿
2. すべての機能が正常に動作するか確認
3. ログにエラーがないか確認

**完了条件:**
- すべての機能が正常に動作している
- エラーログがない

**Requirements:** 全要件

---

### 8.4 (P) 旧サービスファイルの削除

**タスク:** 旧サービスファイル（article-stock-bot.service）を削除

**手順:**
```bash
# Raspberry Pi上で実行
sudo systemctl stop article-stock-bot  # 念のため停止
sudo systemctl disable article-stock-bot
sudo rm /etc/systemd/system/article-stock-bot.service
sudo systemctl daemon-reload

# ローカルでも削除
git rm deployment/article-stock-bot.service
git commit -m "Remove old systemd service file"
git push origin main
```

**完了条件:**
- `/etc/systemd/system/article-stock-bot.service` が削除されている
- `deployment/article-stock-bot.service` がリポジトリから削除されている

**Requirements:** なし（クリーンアップタスク）

---

## 成功基準

### 必須基準
1. ✅ Article Stock BotがvenvベースでRaspberry Pi上で稼働
2. ✅ systemdで自動起動し、クラッシュ時に自動再起動
3. ✅ update_bot.shでワンコマンド更新可能
4. ✅ Tennis BotとArticle Botが並行稼働
5. ✅ 全ての機能が移行前と同じく動作（記事保存、コメント追記）

### 推奨基準
1. ✅ ドキュメントが統一フォーマットで整備（RASPBERRY_PI_SETUP.md）
2. ✅ よく使うコマンドが一覧化
3. ✅ トラブルシューティングガイドが充実

---

## タスク実行順序

**推奨実行順序:**
1. Phase 1（ローカル準備） → Phase 2（update_bot.sh） → Phase 3（systemd） → Phase 4（ドキュメント） → Phase 5（.gitignore）
2. ローカルでの動作確認とテスト
3. Phase 6（Raspberry Piデプロイ）
4. Phase 7（動作確認）
5. Phase 8（本番マージ）

**並行実行可能なタスク:**
- Phase 2, 3, 4, 5は並行実行可能
- ただし、すべて完了してからPhase 6に進むこと

---

**Document Version**: 1.0
**Last Updated**: 2025-12-06
**Status**: Draft - Approval Pending
**Total Tasks**: 30タスク（Phase 1-8）
