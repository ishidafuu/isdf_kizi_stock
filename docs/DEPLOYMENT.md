# Raspberry Pi 環境構築ガイド

このドキュメントは、Article Stock Bot を Raspberry Pi 上で24時間稼働させるための環境構築手順を説明します。

## 目次

1. [前提条件](#前提条件)
2. [Python 3.11+ 環境構築](#python-311-環境構築)
3. [Poetry インストール](#poetry-インストール)
4. [プロジェクトセットアップ](#プロジェクトセットアップ)
5. [環境変数の設定](#環境変数の設定)
6. [Bot の起動](#bot-の起動)
7. [systemd サービス化（24時間稼働）](#systemd-サービス化24時間稼働)
8. [トラブルシューティング](#トラブルシューティング)

---

## 前提条件

- **Raspberry Pi**: Raspberry Pi 3 以降（推奨: Raspberry Pi 4）
- **OS**: Raspberry Pi OS (Debian ベース)
- **ネットワーク**: インターネット接続が可能な環境
- **ストレージ**: 最低 8GB の空き容量（推奨: 16GB 以上）
- **RAM**: 最低 1GB（推奨: 2GB 以上）

---

## Python 3.11+ 環境構築

Raspberry Pi OS には標準で Python がインストールされていますが、Python 3.11+ が必要です。

### 1. 現在のPythonバージョンを確認

```bash
python3 --version
```

### 2. Python 3.11+ のインストール

#### オプション A: pyenv を使用したインストール（推奨）

```bash
# 必要なパッケージをインストール
sudo apt update
sudo apt install -y make build-essential libssl-dev zlib1g-dev \
  libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
  libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev \
  libffi-dev liblzma-dev git

# pyenv のインストール
curl https://pyenv.run | bash

# .bashrc に pyenv の設定を追加
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc

# 設定を反映
source ~/.bashrc

# Python 3.11 をインストール
pyenv install 3.11.7
pyenv global 3.11.7

# インストール確認
python --version  # Python 3.11.7 と表示されることを確認
```

#### オプション B: ソースからビルド

```bash
# 必要なパッケージをインストール
sudo apt update
sudo apt install -y build-essential zlib1g-dev libncurses5-dev \
  libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev \
  libsqlite3-dev wget libbz2-dev

# Python 3.11.7 をダウンロード
cd /tmp
wget https://www.python.org/ftp/python/3.11.7/Python-3.11.7.tgz
tar -xf Python-3.11.7.tgz
cd Python-3.11.7

# ビルドとインストール
./configure --enable-optimizations
make -j $(nproc)
sudo make altinstall

# インストール確認
python3.11 --version
```

---

## Poetry インストール

Poetry は Python の依存関係管理ツールです。

### 1. Poetry のインストール

```bash
# Poetry 公式インストーラーを使用
curl -sSL https://install.python-poetry.org | python3 -

# PATH に追加（pyenv を使用している場合は不要な場合があります）
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# インストール確認
poetry --version
```

### 2. Poetry の設定

```bash
# 仮想環境をプロジェクトディレクトリ内に作成する設定（推奨）
poetry config virtualenvs.in-project true
```

---

## プロジェクトセットアップ

### 1. リポジトリのクローン

```bash
# ホームディレクトリに移動
cd ~

# プロジェクトをクローン
git clone https://github.com/your-username/article-stock-bot.git
cd article-stock-bot
```

### 2. 依存関係のインストール

```bash
# Poetry を使用して依存関係をインストール
poetry install

# 開発用依存関係を除外する場合（本番環境向け）
poetry install --only main
```

インストールには数分かかる場合があります。Raspberry Pi の性能によっては10分以上かかることもあります。

### 3. インストールの確認

```bash
# 仮想環境に入る
poetry shell

# Python とパッケージの確認
python --version
pip list | grep discord
pip list | grep google-generativeai
```

---

## 環境変数の設定

### 1. `.env` ファイルの作成

プロジェクトルートディレクトリに `.env` ファイルを作成します。

```bash
# .env.sample をコピー
cp .env.sample .env

# エディタで編集（nano, vim, など）
nano .env
```

### 2. 環境変数の設定内容

`.env` ファイルに以下の環境変数を設定します。

#### Discord Bot 設定

```bash
# Discord Bot Token
# 取得方法: https://discord.com/developers/applications
# 1. Applications → New Application
# 2. Bot → Add Bot
# 3. TOKEN → Copy
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# Discord Channel ID（監視対象チャンネル）
# 取得方法:
# 1. Discord の設定 → 詳細設定 → 開発者モードを有効化
# 2. 監視したいチャンネルを右クリック → ID をコピー
DISCORD_CHANNEL_ID=1234567890123456789
```

#### Gemini API 設定

```bash
# Gemini API Key
# 取得方法: https://ai.google.dev/
# 1. Google AI Studio にアクセス
# 2. Get API key → Create API key
GEMINI_API_KEY=your_gemini_api_key_here
```

#### GitHub 設定

```bash
# GitHub Personal Access Token
# 取得方法: https://github.com/settings/tokens
# 1. Settings → Developer settings → Personal access tokens → Tokens (classic)
# 2. Generate new token (classic)
# 3. 必要なスコープ: repo（Full control of private repositories）
GITHUB_TOKEN=your_github_personal_access_token_here

# GitHub Repository URL（Obsidian Vault のリポジトリ）
# 例: https://github.com/username/obsidian-vault.git
GITHUB_REPO_URL=https://github.com/username/obsidian-vault.git
```

#### Obsidian Vault 設定

```bash
# Obsidian Vault のローカルパス
# デフォルトは ./vault（プロジェクトルートからの相対パス）
OBSIDIAN_VAULT_PATH=./vault
```

#### ログファイル設定

```bash
# ログファイルのパス
# デフォルトは ./logs/article_bot.log
LOG_FILE_PATH=./logs/article_bot.log
```

#### 管理者通知設定（オプション）

重要なエラー（GitHub push 失敗、Gemini API 継続失敗）のメール通知を設定できます。

```bash
# 管理者通知の有効化
# 有効: true または 1、無効: false または 0
ADMIN_NOTIFICATION_ENABLED=false

# メール設定（通知を有効にする場合のみ設定）
ADMIN_EMAIL_FROM=bot@example.com
ADMIN_EMAIL_TO=admin@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

**Gmail を使用する場合の注意**:
- 2段階認証を有効化
- アプリパスワードを生成して `SMTP_PASSWORD` に設定
- 取得方法: https://myaccount.google.com/apppasswords

### 3. 環境変数の確認

設定した環境変数が正しく読み込まれるか確認します。

```bash
# Python で確認
poetry run python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('Discord Token:', os.getenv('DISCORD_BOT_TOKEN')[:10] + '...')"
```

---

## Bot の起動

### 1. GitHub Repository の準備

Bot が記事を保存するための GitHub Repository を準備します。

```bash
# Obsidian Vault 用のリポジトリをクローン
cd ~
git clone https://github.com/username/obsidian-vault.git

# または、新規作成する場合
mkdir obsidian-vault
cd obsidian-vault
git init
mkdir -p vault/articles
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/username/obsidian-vault.git
git push -u origin main
```

### 2. Bot の起動

```bash
# プロジェクトディレクトリに移動
cd ~/article-stock-bot

# Poetry の仮想環境で Bot を起動
poetry run python -m src.bot.client
```

### 3. 起動確認

Bot が正常に起動すると、以下のようなログが表示されます。

```
INFO: Logged in as ArticleStockBot#1234
INFO: Connected to Discord
INFO: Monitoring channel: general (ID: 1234567890123456789)
```

Discord 上で Bot がオンライン状態になっていることを確認してください。

### 4. テスト投稿

監視対象チャンネルに記事 URL を投稿して、Bot が正常に動作するかテストします。

```
https://example.com/test-article
```

Bot が以下の動作を行えば成功です：
1. 受信確認リアクション（👁️）を追加
2. OGP 情報を取得
3. Gemini でタグ付けと要約生成
4. Markdown ファイルを生成
5. GitHub にプッシュ
6. 成功通知をリプライ
7. 成功リアクション（✅）を追加

---

## systemd サービス化（24時間稼働）

Bot をバックグラウンドで24時間稼働させるため、systemd サービスとして登録します。

### 1. systemd ユニットファイルのコピー

プロジェクトには systemd ユニットファイルのテンプレートが含まれています。

```bash
# プロジェクトディレクトリに移動
cd ~/article-stock-bot

# systemd ユニットファイルをシステムにコピー
sudo cp deployment/article-stock-bot.service /etc/systemd/system/

# ファイルを編集して環境に合わせてパスを調整
sudo nano /etc/systemd/system/article-stock-bot.service
```

### 2. ユニットファイルの設定内容

`deployment/article-stock-bot.service` の内容を確認・編集します：

```ini
[Unit]
Description=Article Stock Bot - Discord Bot for article archiving with AI tagging
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/article-stock-bot
ExecStart=/usr/bin/poetry run python main.py
Restart=always
RestartSec=10

# ログ出力設定
StandardOutput=journal
StandardError=journal
SyslogIdentifier=article-stock-bot

# 環境変数（.envファイルから自動読み込み）
Environment="PYTHONUNBUFFERED=1"

# リソース制限（オプション）
# メモリ使用量を制限（Raspberry Pi向け）
MemoryLimit=512M

# プロセスのタイムアウト設定
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

**重要な設定項目**:
- `User`: Raspberry Pi のユーザー名（デフォルト: `pi`、環境に合わせて変更）
- `WorkingDirectory`: プロジェクトのルートディレクトリ（例: `/home/pi/article-stock-bot`）
- `ExecStart`: Poetry の実行パス（`which poetry` で確認し、必要に応じて調整）
- `Restart=always`: Bot がクラッシュしても自動再起動
- `RestartSec=10`: 再起動までの待機時間（秒）
- `StandardOutput/StandardError=journal`: ログを systemd の journal に出力
- `MemoryLimit=512M`: メモリ使用量の制限（Raspberry Pi 向け最適化）

**パスの確認方法**:

```bash
# Poetry のパスを確認
which poetry
# 出力例: /usr/bin/poetry または /home/pi/.local/bin/poetry

# プロジェクトのパスを確認
pwd
# 出力例: /home/pi/article-stock-bot
```

### 3. ログディレクトリの作成

```bash
mkdir -p ~/article-stock-bot/logs
```

### 4. サービスの有効化と起動

```bash
# systemd 設定をリロード
sudo systemctl daemon-reload

# サービスを有効化（起動時に自動起動）
sudo systemctl enable article-stock-bot

# サービスを起動
sudo systemctl start article-stock-bot

# サービスの状態を確認
sudo systemctl status article-stock-bot
```

### 5. サービスの管理コマンド

```bash
# サービスの起動
sudo systemctl start article-stock-bot

# サービスの停止
sudo systemctl stop article-stock-bot

# サービスの再起動
sudo systemctl restart article-stock-bot

# サービスの状態確認
sudo systemctl status article-stock-bot

# ログの確認
sudo journalctl -u article-stock-bot -f

# アプリケーションログの確認
tail -f ~/article-stock-bot/logs/article_bot.log
```

### 6. 自動起動の確認

Raspberry Pi を再起動して、Bot が自動起動するか確認します。

```bash
sudo reboot
```

再起動後、以下のコマンドで Bot が起動していることを確認：

```bash
sudo systemctl status article-stock-bot
```

---

## トラブルシューティング

### Bot が起動しない

#### 1. Python バージョンの確認

```bash
poetry run python --version
# Python 3.11.x と表示されることを確認
```

#### 2. 依存関係の再インストール

```bash
poetry install --no-cache
```

#### 3. 環境変数の確認

```bash
# .env ファイルが存在するか確認
ls -la .env

# 環境変数の内容を確認（Token は表示されないので注意）
cat .env
```

### Discord に接続できない

#### Discord Bot Token の確認

```bash
# Token が有効か Discord Developer Portal で確認
# https://discord.com/developers/applications
```

#### Bot の権限確認

Bot に以下の権限が付与されているか確認：
- View Channels（チャンネルの閲覧）
- Send Messages（メッセージの送信）
- Read Message History（メッセージ履歴の閲覧）
- Add Reactions（リアクションの追加）

#### Intent の有効化

Discord Developer Portal で以下の Intent を有効化：
- Presence Intent
- Server Members Intent
- Message Content Intent

### OGP 取得が失敗する

#### ネットワーク接続の確認

```bash
# インターネット接続を確認
ping -c 3 google.com

# DNS 解決を確認
nslookup example.com
```

#### User-Agent の設定

一部のサイトは User-Agent がないとアクセスを拒否します。コード内で適切な User-Agent を設定しているか確認してください。

### Gemini API が失敗する

#### API Key の確認

```bash
# Gemini API Key が有効か確認
# https://ai.google.dev/
```

#### API 利用制限の確認

無料枠の場合、1日あたりのリクエスト制限があります。Google AI Studio で利用状況を確認してください。

### GitHub プッシュが失敗する

#### Personal Access Token の確認

```bash
# Token が有効か GitHub で確認
# https://github.com/settings/tokens
```

#### Git の認証情報設定

```bash
# Git の認証情報キャッシュを設定
git config --global credential.helper store

# リモートリポジトリの URL を確認
cd ~/obsidian-vault
git remote -v
```

#### リポジトリの権限確認

Personal Access Token に `repo` スコープが付与されているか確認してください。

### systemd サービスが起動しない

#### サービスログの確認

```bash
# systemd のログを確認
sudo journalctl -u article-stock-bot -n 50 --no-pager

# リアルタイムでログを監視
sudo journalctl -u article-stock-bot -f
```

#### パスの確認

```bash
# Poetry のパスを確認
which poetry

# Python のパスを確認
poetry run which python
```

ユニットファイルの `ExecStart` に正しいパスを設定してください。

### ログファイルが作成されない

#### ディレクトリの権限確認

```bash
# logs ディレクトリの権限を確認
ls -ld ~/article-stock-bot/logs

# 権限がない場合は作成
mkdir -p ~/article-stock-bot/logs
chmod 755 ~/article-stock-bot/logs
```

### メモリ不足

Raspberry Pi のメモリが不足している場合、スワップ領域を増やします。

```bash
# 現在のスワップサイズを確認
free -h

# スワップファイルのサイズを変更（例: 2GB）
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# CONF_SWAPSIZE=2048 に変更
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

---

## 追加情報

### パフォーマンス最適化

Raspberry Pi のリソースが限られている場合、以下の最適化を検討してください：

1. **並行処理数の制限**: `config/settings.py` で `MAX_CONCURRENT_MESSAGES = 1` に設定
2. **ログレベルの調整**: `.env` に `LOG_LEVEL=WARNING` を追加してログ出力を減らす
3. **不要なサービスの停止**: `sudo systemctl disable <service>` で不要なサービスを無効化

### バックアップ

定期的にデータをバックアップすることを推奨します。

```bash
# vault ディレクトリのバックアップ
tar -czf vault_backup_$(date +%Y%m%d).tar.gz ~/obsidian-vault/vault

# .env ファイルのバックアップ（機密情報を含むので安全な場所に保存）
cp .env .env.backup
```

### アップデート

Bot を最新バージョンにアップデートする手順：

```bash
# プロジェクトディレクトリに移動
cd ~/article-stock-bot

# Bot を停止
sudo systemctl stop article-stock-bot

# 最新コードを取得
git pull origin main

# 依存関係を更新
poetry install

# Bot を再起動
sudo systemctl start article-stock-bot

# 動作確認
sudo systemctl status article-stock-bot
```

---

## サポート

問題が解決しない場合は、以下の情報を含めて Issue を作成してください：

- Raspberry Pi のモデルと OS バージョン
- Python のバージョン（`python --version`）
- Poetry のバージョン（`poetry --version`）
- エラーメッセージの全文
- ログファイルの内容（`logs/article_bot.log`, `logs/systemd.log`）

---

**Document Version**: 1.0
**Last Updated**: 2025-12-04
**Status**: Production Ready
