# Technical Design: 統一Bot管理システム

## 設計概要

本設計書は、複数のDiscord BotをRaspberry Pi上で統一的に管理・デプロイするシステムの技術設計を定義する。既存のTennis Discovery Agentの運用方式を標準化し、Article Stock Botを含む全てのBotを同じ方式で管理できるようにする。

**設計原則:**
- **シンプルさ**: 標準的なLinuxツールのみ使用（venv、systemd、bash）
- **一貫性**: 全てのBotで同じ構造・運用方式
- **保守性**: ドキュメント充実、トラブルシューティング容易
- **拡張性**: 新しいBot追加が迅速かつ確実

---

## 1. システムアーキテクチャ

### 1.1 全体構成図

```
┌─────────────────────────────────────────────────────────┐
│              Raspberry Pi (isdf-pi)                     │
│              User: ishidafuu                            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  /home/ishidafuu/                                       │
│  ├── isdf_tennis_discovery_agent/  (既存Bot)            │
│  │   ├── venv/                                          │
│  │   ├── main.py                                        │
│  │   ├── requirements.txt                               │
│  │   ├── .env                                           │
│  │   └── update_bot.sh                                  │
│  │                                                       │
│  └── isdf_kizi_stock/  (Article Stock Bot - 新規統一化) │
│      ├── venv/                     ← Poetry削除         │
│      ├── main.py                   ← src/bot/client.py  │
│      ├── requirements.txt          ← pyproject.toml変換 │
│      ├── .env                                           │
│      └── update_bot.sh             ← 新規作成           │
│                                                          │
├─────────────────────────────────────────────────────────┤
│  systemd Services                                        │
│  ├── tennis-bot.service  (既存)                         │
│  └── article-bot.service (新規作成)                     │
└─────────────────────────────────────────────────────────┘
```

### 1.2 データフロー

**起動フロー:**
```
System Boot
  ↓
systemd.target
  ↓
network.target (ネットワーク待機)
  ↓
tennis-bot.service 起動
article-bot.service 起動
  ↓
venv/bin/python3 main.py 実行
  ↓
Bot稼働（Discord接続）
```

**更新フロー:**
```
./update_bot.sh 実行
  ↓
git pull (最新コード取得)
  ↓
source venv/bin/activate
pip install -r requirements.txt (依存関係更新)
  ↓
sudo systemctl restart <bot-name> (サービス再起動)
  ↓
journalctl でログ確認
```

---

## 2. ディレクトリ構造設計

### 2.1 標準プロジェクト構造

全てのBotプロジェクトは以下の構造に統一する。

```
/home/ishidafuu/<project_name>/
├── .git/                        # Gitリポジトリ
├── .gitignore                   # Git除外設定
├── .env                         # 環境変数（Git管理外）
├── .env.sample                  # 環境変数テンプレート
├── README.md                    # プロジェクト概要
├── main.py                      # エントリーポイント
├── requirements.txt             # 依存関係定義
├── update_bot.sh                # 簡易更新スクリプト
├── venv/                        # Python仮想環境（Git管理外）
│   ├── bin/
│   ├── lib/
│   └── ...
├── src/                         # ソースコード
│   ├── bot/                     # Bot関連
│   ├── utils/                   # ユーティリティ
│   └── ...
├── tests/                       # テストコード（オプション）
├── logs/                        # ログファイル（Git管理外）
│   └── bot.log
└── docs/                        # ドキュメント
    ├── RASPBERRY_PI_SETUP.md    # デプロイ手順
    └── ...
```

### 2.2 必須ファイルの詳細

#### main.py（エントリーポイント）

**目的**: Botの起動ポイント
**配置**: プロジェクトルート直下
**要件**:
- `if __name__ == "__main__":` で実行
- 環境変数の読み込み
- ロギング設定
- Botクライアントの起動

**実装例:**
```python
# main.py
import asyncio
import os
from dotenv import load_dotenv
from src.bot.client import BotClient
from src.utils.logger import setup_logger

def main():
    # 環境変数読み込み
    load_dotenv()

    # ロガー設定
    logger = setup_logger()

    # Botトークン取得
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        logger.error("DISCORD_BOT_TOKEN not found in .env")
        return

    # Bot起動
    client = BotClient()
    asyncio.run(client.start(token))

if __name__ == "__main__":
    main()
```

#### requirements.txt（依存関係定義）

**目的**: Pythonパッケージの依存関係管理
**配置**: プロジェクトルート直下
**フォーマット**: pip標準形式

**生成方法:**
```bash
# 開発環境で依存関係をインストール後
pip freeze > requirements.txt
```

**Article Stock Botの例:**
```txt
discord.py==2.3.2
python-dotenv==1.0.0
beautifulsoup4==4.12.2
aiohttp==3.9.1
google-generativeai==0.3.1
GitPython==3.1.40
pytest==7.4.3
pytest-asyncio==0.21.1
aioresponses==0.7.6
```

#### update_bot.sh（更新スクリプト）

**目的**: Botの更新とサービス再起動を自動化
**配置**: プロジェクトルート直下
**権限**: 実行可能（chmod +x）

**テンプレート:**
```bash
#!/bin/bash

# プロジェクト名（各Botで変更）
PROJECT_DIR="<project_name>"
# systemdサービス名（各Botで変更）
SERVICE_NAME="<bot-name>"

echo "========================================"
echo "🔄 ${PROJECT_DIR} の更新を開始します..."
echo "========================================"

# プロジェクトディレクトリに移動
cd ~/$PROJECT_DIR || exit 1

# Git Pull
echo "📥 Git Pull..."
git pull

# 仮想環境を有効化してライブラリ更新
echo "📦 ライブラリ更新..."
source venv/bin/activate
pip install -r requirements.txt

# サービス再起動
echo "========================================"
echo "🚀 サービスを再起動します..."
echo "========================================"

sudo systemctl restart $SERVICE_NAME

# 再起動確認
echo "✅ 再起動完了。直近のログを表示します（Ctrl+Cで終了）"
sudo journalctl -u $SERVICE_NAME -n 20 -f
```

**Article Stock Bot用の具体例:**
```bash
#!/bin/bash
PROJECT_DIR="isdf_kizi_stock"
SERVICE_NAME="article-bot"
# 以下、テンプレートと同じ
```

---

## 3. 依存関係管理設計

### 3.1 venv（Python仮想環境）

**選定理由:**
- Python標準ライブラリ（追加インストール不要）
- シンプルで理解しやすい
- Poetryより軽量で高速
- Raspberry Piのリソース制約に適合

**実装方法:**

```bash
# 仮想環境作成
python3 -m venv venv

# 有効化（Linux/macOS）
source venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt

# 無効化
deactivate
```

**ディレクトリ配置:**
- 場所: プロジェクトルート直下 (`./venv/`)
- Git管理: `.gitignore` で除外

### 3.2 Poetry → venv マイグレーション戦略

**Article Stock Botの現状分析:**
- 現在: Poetry + `pyproject.toml`
- 依存パッケージ: discord.py, python-dotenv, beautifulsoup4, aiohttp, google-generativeai, GitPython, pytest等

**マイグレーション手順:**

#### Step 1: requirements.txt の生成

**方法A: poetry exportを使用（推奨）**
```bash
# Poetry環境で実行
poetry export -f requirements.txt --output requirements.txt --without-hashes
```

**方法B: pip freezeを使用**
```bash
# Poetry環境内で実行
poetry shell
pip freeze > requirements.txt
exit
```

#### Step 2: venv環境の作成とテスト

```bash
# venv作成
python3 -m venv venv

# 有効化
source venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt

# 動作確認
python main.py  # または pytest
```

#### Step 3: Poetryファイルの削除

動作確認後、以下を削除:
```bash
rm -rf poetry.lock pyproject.toml
```

#### Step 4: .gitignoreの更新

```gitignore
# Python
venv/
__pycache__/
*.pyc

# Poetry（削除）
# poetry.lock は不要

# 環境変数
.env

# ログ
logs/
*.log
```

### 3.3 依存関係の固定とバージョン管理

**ベストプラクティス:**

1. **本番環境**: 厳密なバージョン固定
   ```txt
   discord.py==2.3.2
   python-dotenv==1.0.0
   ```

2. **開発環境**: 許容範囲指定も可
   ```txt
   discord.py>=2.3.0,<3.0.0
   ```

3. **定期的なアップデート**
   ```bash
   # 古いバージョンの確認
   pip list --outdated

   # 個別アップデート
   pip install --upgrade <package>

   # requirements.txt更新
   pip freeze > requirements.txt
   ```

---

## 4. systemd サービス設計

### 4.1 サービスファイル標準テンプレート

**ファイル名:** `/etc/systemd/system/<bot-name>.service`
**所有者:** root
**権限:** 644

**テンプレート:**
```ini
[Unit]
Description=<Bot Description>
After=network.target

[Service]
Type=simple
User=ishidafuu
WorkingDirectory=/home/ishidafuu/<project_name>
ExecStart=/home/ishidafuu/<project_name>/venv/bin/python3 /home/ishidafuu/<project_name>/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 4.2 Article Stock Bot用サービスファイル

**ファイル名:** `/etc/systemd/system/article-bot.service`

**内容:**
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

**変更点（既存のarticle-stock-bot.serviceから）:**
- User: `pi` → `ishidafuu`
- WorkingDirectory: `/home/pi/article-stock-bot` → `/home/ishidafuu/isdf_kizi_stock`
- ExecStart: `/usr/bin/poetry run python main.py` → `venv/bin/python3 main.py`
- MemoryLimit: 削除（必要に応じて後で追加）

### 4.3 サービス管理コマンド標準化

**セットアップ:**
```bash
# サービスファイルを配置
sudo cp <bot-name>.service /etc/systemd/system/

# systemd設定リロード
sudo systemctl daemon-reload

# 自動起動を有効化
sudo systemctl enable <bot-name>

# サービス起動
sudo systemctl start <bot-name>
```

**運用:**
```bash
# 状態確認
sudo systemctl status <bot-name>

# ログ確認（リアルタイム）
sudo journalctl -u <bot-name> -f

# ログ確認（最新50行）
sudo journalctl -u <bot-name> -n 50 --no-pager

# 再起動
sudo systemctl restart <bot-name>

# 停止
sudo systemctl stop <bot-name>
```

### 4.4 ログ管理設計

**ログ出力先:**
- **systemd journal**: 標準出力・標準エラー
- **アプリケーションログ**: `logs/bot.log`（ファイルローテーション）

**journaldの設定（デフォルトで十分）:**
- 保存期間: 7日間（デフォルト）
- 最大サイズ: 500MB（デフォルト）

**アプリケーションログ（既存のArticle Botの設計を維持）:**
```python
# src/utils/logger.py
import logging
from logging.handlers import RotatingFileHandler

def setup_logger():
    logger = logging.getLogger("ArticleBot")
    logger.setLevel(logging.INFO)

    # ファイルハンドラ（ローテーション）
    handler = RotatingFileHandler(
        "logs/bot.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=7  # 7ファイル保持
    )

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
```

---

## 5. 環境変数管理設計

### 5.1 .env ファイル設計

**配置:** プロジェクトルート直下
**Git管理:** `.gitignore`で除外
**読み込み:** `python-dotenv`

**Article Stock Bot用テンプレート（.env.sample）:**
```bash
# Discord Bot設定
DISCORD_BOT_TOKEN=your_discord_bot_token_here
DISCORD_CHANNEL_ID=1234567890123456789

# Gemini API設定
GEMINI_API_KEY=your_gemini_api_key_here

# GitHub設定
GITHUB_TOKEN=your_github_personal_access_token_here
GITHUB_REPO_URL=https://github.com/username/obsidian-vault.git

# Obsidian Vault設定
OBSIDIAN_VAULT_PATH=./vault

# ログ設定
LOG_FILE_PATH=./logs/article_bot.log
LOG_LEVEL=INFO

# 環境
ENV=production
```

**Tennis Bot用（参考）:**
```bash
DISCORD_BOT_TOKEN=your_token_here
GEMINI_API_KEY=your_key_here
OBSIDIAN_VAULT_PATH=/home/ishidafuu/obsidian-vault
ADMIN_USER_ID=your_discord_user_id
ENV=production
LOG_LEVEL=INFO
```

### 5.2 環境変数の読み込み

**実装（main.py）:**
```python
import os
from dotenv import load_dotenv

# .envファイル読み込み
load_dotenv()

# 環境変数取得
discord_token = os.getenv("DISCORD_BOT_TOKEN")
gemini_key = os.getenv("GEMINI_API_KEY")
env = os.getenv("ENV", "development")  # デフォルト値
```

---

## 6. 新規Bot追加のテンプレート設計

### 6.1 プロジェクトテンプレート

新しいBotを追加する際のテンプレートを標準化する。

**テンプレートリポジトリ構造:**
```
bot-template/
├── .gitignore
├── .env.sample
├── README.md
├── main.py
├── requirements.txt
├── update_bot.sh
├── src/
│   ├── bot/
│   │   └── client.py
│   └── utils/
│       └── logger.py
├── tests/
│   └── test_sample.py
└── docs/
    └── RASPBERRY_PI_SETUP.md
```

### 6.2 .gitignore（標準）

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
```

### 6.3 README.md（テンプレート）

```markdown
# [Bot Name]

[Bot Description]

## 機能

- 機能1
- 機能2
- 機能3

## セットアップ

詳細は [docs/RASPBERRY_PI_SETUP.md](docs/RASPBERRY_PI_SETUP.md) を参照してください。

## 更新方法

```bash
./update_bot.sh
```

## ログ確認

```bash
# systemdログ
sudo journalctl -u <bot-name> -f

# アプリケーションログ
tail -f logs/bot.log
```

## 開発

```bash
# 仮想環境作成
python3 -m venv venv
source venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt

# テスト実行
pytest
```
```

### 6.4 update_bot.sh（テンプレート）

```bash
#!/bin/bash

# ===== 以下を各Botに合わせて変更 =====
PROJECT_DIR="project_name_here"
SERVICE_NAME="bot-name-here"
# ===================================

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

---

## 7. ドキュメント設計

### 7.1 RASPBERRY_PI_SETUP.md（統一フォーマット）

全てのBotで以下のセクション構成を統一する。

**必須セクション:**
1. **概要** - Botの説明と動作環境
2. **OSのインストール** - Raspberry Pi Imagerの使用手順
3. **必要なソフトウェアのインストール** - Python、Git等
4. **プロジェクトのセットアップ** - クローン、venv作成、依存関係インストール
5. **systemdによる自動起動** - サービスファイル作成と有効化
6. **運用・メンテナンス** - update_bot.sh、よく使うコマンド
7. **トラブルシューティング** - よくある問題と解決方法

**Tennis Bot形式をベースにする:**
- OSインストールの詳細設定（ホスト名、SSH、Wi-Fi、タイムゾーン、キーボード）
- systemdサービス化の詳細手順
- update_bot.shスクリプトの説明
- よく使うコマンド一覧表
- トラブルシューティングセクション

### 7.2 Article Stock Bot用RASPBERRY_PI_SETUP.md（新規作成）

既存の `docs/DEPLOYMENT.md` を `docs/RASPBERRY_PI_SETUP.md` に統一する。

**主な変更点:**
- タイトル: "Raspberry Pi 環境構築ガイド" → "Raspberry Pi セットアップ"
- Poetry関連の記述を削除
- venv + requirements.txt に変更
- update_bot.sh セクションを追加
- Tennis Botと同じフォーマットに統一

---

## 8. マイグレーション実装計画

### 8.1 Article Stock Botマイグレーションの詳細手順

#### Phase 1: 事前準備（ローカル環境）

**1. 現状のバックアップ**
```bash
# ブランチ作成
git checkout -b migrate-to-venv

# Poetryで依存関係をエクスポート
poetry export -f requirements.txt --output requirements.txt --without-hashes

# コミット
git add requirements.txt
git commit -m "Export dependencies from Poetry to requirements.txt"
```

**2. main.pyの作成**

既存の `src/bot/client.py` をラップする `main.py` を作成:

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

**3. venv環境の作成とテスト**
```bash
# venv作成
python3 -m venv venv

# 有効化
source venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt

# 動作確認（ローカル）
python main.py
```

**4. requirements.txtの調整**

不要な依存関係を削除し、最小限にする:
```bash
# 必要なパッケージのみリスト
pip freeze | grep -E "discord|dotenv|beautifulsoup|aiohttp|google-generativeai|GitPython" > requirements_minimal.txt

# 確認後、置き換え
mv requirements_minimal.txt requirements.txt
```

**5. Poetryファイルの削除**
```bash
# 動作確認後
rm -rf poetry.lock pyproject.toml

# コミット
git add .
git commit -m "Remove Poetry files, migrate to venv"
```

#### Phase 2: update_bot.sh作成

```bash
# テンプレートからコピー
cat > update_bot.sh << 'EOF'
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
EOF

# 実行権限付与
chmod +x update_bot.sh

# コミット
git add update_bot.sh
git commit -m "Add update_bot.sh script for unified management"
```

#### Phase 3: systemdサービスファイル更新

既存の `deployment/article-stock-bot.service` を更新:

```bash
# 新しいサービスファイルを作成
cat > deployment/article-bot.service << 'EOF'
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
EOF

# コミット
git add deployment/article-bot.service
git commit -m "Update systemd service file for unified management"
```

#### Phase 4: ドキュメント更新

`docs/DEPLOYMENT.md` を `docs/RASPBERRY_PI_SETUP.md` に変更し、Tennis Bot形式に統一:

```bash
# ファイル移動
git mv docs/DEPLOYMENT.md docs/RASPBERRY_PI_SETUP.md

# 内容を編集（Poetryの記述を削除、venv + requirements.txtに変更）
nano docs/RASPBERRY_PI_SETUP.md

# コミット
git add docs/RASPBERRY_PI_SETUP.md
git commit -m "Rename and update deployment docs to match Tennis Bot format"
```

#### Phase 5: .gitignore更新

```bash
# .gitignoreを編集
nano .gitignore

# 以下を確認・追加
# venv/
# poetry.lock (削除)

# コミット
git add .gitignore
git commit -m "Update .gitignore for venv-based setup"
```

#### Phase 6: Raspberry Piへのデプロイ

```bash
# SSH接続
ssh ishidafuu@isdf-pi.local

# ホームディレクトリに移動
cd ~

# 既存のArticle Botが存在する場合は削除（または別名でバックアップ）
mv isdf_kizi_stock isdf_kizi_stock.backup

# 新しくクローン
git clone https://github.com/ishidafuu/isdf_kizi_stock.git
cd isdf_kizi_stock

# migrate-to-venvブランチをチェックアウト
git checkout migrate-to-venv

# venv作成
python3 -m venv venv

# 依存関係インストール
source venv/bin/activate
pip install -r requirements.txt

# .envファイルを作成（既存のものをコピー）
cp ~/isdf_kizi_stock.backup/.env .env

# ディレクトリ作成
mkdir -p logs vault/articles

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

#### Phase 7: 動作確認

1. Discord上で記事URLを投稿
2. Botが正常に反応するか確認
3. GitHubにMarkdownファイルがプッシュされるか確認
4. スレッドコメント追記機能が動作するか確認

#### Phase 8: 本番マージ

```bash
# ローカルに戻る
exit

# マージ
git checkout main
git merge migrate-to-venv

# プッシュ
git push origin main

# Raspberry Piで本番ブランチに切り替え
ssh ishidafuu@isdf-pi.local
cd ~/isdf_kizi_stock
git checkout main
git pull
sudo systemctl restart article-bot
```

---

## 9. セキュリティ設計

### 9.1 環境変数の保護

**実装:**
- `.env` ファイルは `.gitignore` で除外
- `.env.sample` のみリポジトリに含める
- ファイル権限: `chmod 600 .env`（所有者のみ読み書き可）

### 9.2 SSH接続のセキュリティ

**推奨設定:**
```bash
# Raspberry Pi側の設定
sudo nano /etc/ssh/sshd_config

# 推奨設定
PermitRootLogin no
PasswordAuthentication yes  # または公開鍵認証のみ
PubkeyAuthentication yes
```

### 9.3 systemdサービスの権限

- サービスは一般ユーザー（ishidafuu）で実行
- rootでは実行しない
- 必要最小限の権限のみ

---

## 10. テスト・検証計画

### 10.1 マイグレーションテスト

**ローカル環境でのテスト:**
1. venv作成と依存関係インストール
2. main.pyの実行確認
3. 全ての機能の動作確認（メッセージ処理、OGP取得、Gemini呼び出し、GitHub push）

**Raspberry Pi環境でのテスト:**
1. systemdサービスの起動確認
2. 自動起動の確認（再起動後）
3. update_bot.shの動作確認
4. ログ出力の確認

### 10.2 統合テスト

**両Botの並行動作確認:**
1. Tennis BotとArticle Botが同時に稼働
2. リソース競合がないことを確認
3. それぞれのBotが独立して動作

---

## 11. 運用設計

### 11.1 定期メンテナンス

**週次:**
- ログの確認（エラーがないか）
- ディスク使用量の確認

**月次:**
- 依存パッケージのアップデート検討
- ログファイルのクリーンアップ（自動ローテーションされるが念のため）

**四半期:**
- Raspberry Pi OSのアップデート
- セキュリティパッチの適用

### 11.2 バックアップ戦略

**自動バックアップ（GitHub）:**
- コード: GitHubで管理
- 記事データ: Obsidian Vault（GitHub）で管理

**手動バックアップ（推奨）:**
```bash
# .envファイル（機密情報）
cp .env .env.backup
# 安全な場所に保存

# ログファイル（必要に応じて）
tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/
```

### 11.3 モニタリング

**サービス状態確認:**
```bash
# 定期的にチェック（cronで自動化も可）
sudo systemctl status tennis-bot
sudo systemctl status article-bot
```

**ログ監視:**
```bash
# エラーログの抽出
sudo journalctl -u article-bot --since "1 hour ago" | grep ERROR
```

---

## 12. 拡張性とメンテナンス性

### 12.1 新しいBot追加の標準フロー

1. **テンプレートからプロジェクト作成**
2. **Bot固有のコード実装**
3. **requirements.txt作成**
4. **update_bot.sh作成（テンプレートから）**
5. **systemdサービスファイル作成**
6. **docs/RASPBERRY_PI_SETUP.md作成**
7. **Raspberry Piにデプロイ**

**所要時間目標:** 30分以内（コード実装を除く）

### 12.2 ドキュメント保守

**原則:**
- 全てのBotで同じフォーマットを維持
- 変更があれば全Botのドキュメントを同期更新
- トラブルシューティングセクションを充実

---

## 成功基準

### 技術的成功基準

1. ✅ Article Stock BotがvenvベースでRaspberry Pi上で稼働
2. ✅ systemdで自動起動し、クラッシュ時に自動再起動
3. ✅ update_bot.shでワンコマンド更新可能
4. ✅ Tennis BotとArticle Botが並行稼働
5. ✅ 全ての機能が移行前と同じく動作

### 運用的成功基準

1. ✅ ドキュメントが統一フォーマットで整備
2. ✅ トラブルシューティングガイドが充実
3. ✅ 新しいBot追加が30分以内に完了可能
4. ✅ よく使うコマンドが一覧化

---

## リスクと対策

### リスク1: マイグレーション中のダウンタイム

**対策:**
- 新しいブランチで作業
- ローカルで十分にテスト
- Raspberry Pi上で並行して新旧両方を起動可能にする

### リスク2: 依存関係の互換性問題

**対策:**
- requirements.txtで厳密にバージョン固定
- 事前にローカル環境で全機能をテスト

### リスク3: systemdサービスの起動失敗

**対策:**
- サービスファイルのパスを二重チェック
- `systemctl status` で詳細なエラーメッセージを確認
- journalctlでログを確認

---

**Document Version**: 1.0
**Last Updated**: 2025-12-06
**Status**: Draft - Approval Pending
