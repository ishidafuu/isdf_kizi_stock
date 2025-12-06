# Raspberry Pi 環境構築ガイド

このドキュメントは、Article Stock Bot を Raspberry Pi 上で24時間稼働させるための環境構築手順を説明します。

## 目次

1. [概要](#概要)
2. [OSのインストール](#osのインストール)
3. [必要なソフトウェアのインストール](#必要なソフトウェアのインストール)
4. [プロジェクトのセットアップ](#プロジェクトのセットアップ)
5. [systemdによる自動起動](#systemdによる自動起動)
6. [運用・メンテナンス](#運用メンテナンス)
7. [トラブルシューティング](#トラブルシューティング)

---

## 概要

Article Stock BotはDiscordで共有された記事URLを自動的に保存し、AIでタグ付けを行うシステムです。
Raspberry Pi上で24時間稼働させることで、記事の収集・整理を自動化できます。

**主な機能:**
- Discord上の記事URL自動検出
- OGP情報取得
- Gemini APIによる自動タグ付け
- Markdownファイル生成
- GitHubへの自動プッシュ

---

## OSのインストール

### 1. Raspberry Pi OS のインストール

**必要なもの:**
- Raspberry Pi 3以降（推奨: Raspberry Pi 4）
- microSDカード（最低8GB、推奨: 16GB以上）
- Raspberry Pi Imagerソフトウェア

**インストール手順:**

1. Raspberry Pi Imagerをダウンロード: https://www.raspberrypi.com/software/
2. Imagerを起動し、以下を選択：
   - OS: Raspberry Pi OS (64-bit)
   - ストレージ: microSDカード
3. 設定（歯車アイコン）で以下を設定：
   - ホスト名: `isdf-pi`
   - SSHを有効化
   - ユーザー名: `ishidafuu`
   - パスワード: （任意）
   - **重要:** キーボードレイアウトを`us`（米国配列）に設定
     - デフォルトは`gb`（英国配列）になっており、記号の位置が異なる
4. 書き込み開始

### 2. 初回起動とSSH接続

```bash
# ローカルPCからSSH接続
ssh ishidafuu@isdf-pi.local
```

### 3. システムアップデート

```bash
sudo apt update && sudo apt upgrade -y
```

---

## 必要なソフトウェアのインストール

### 1. Python 3.11+ のインストール

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

## プロジェクトセットアップ

### 1. リポジトリのクローン

```bash
# ホームディレクトリに移動
cd ~

# プロジェクトをクローン
git clone https://github.com/ishidafuu/isdf_kizi_stock.git
cd isdf_kizi_stock
```

### 2. venv仮想環境の作成

```bash
# venv環境を作成
python3 -m venv venv

# 仮想環境を有効化
source venv/bin/activate
```

### 3. 依存関係のインストール

```bash
# pip を最新版に更新
pip install --upgrade pip

# requirements.txt から依存関係をインストール
pip install -r requirements.txt
```

インストールには数分かかる場合があります。Raspberry Pi の性能によっては10分以上かかることもあります。

### 4. インストールの確認

```bash
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
cd ~/isdf_kizi_stock

# venv環境を有効化
source venv/bin/activate

# Botを起動
python main.py
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
cd ~/isdf_kizi_stock

# systemd ユニットファイルをシステムにコピー
sudo cp deployment/article-bot.service /etc/systemd/system/

# ファイルを編集して環境に合わせてパスを調整（必要に応じて）
sudo nano /etc/systemd/system/article-bot.service
```

### 2. ユニットファイルの設定内容

`deployment/article-bot.service` の内容を確認・編集します：

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

**重要な設定項目**:
- `User`: ユーザー名（`ishidafuu`）
- `WorkingDirectory`: プロジェクトのルートディレクトリ（`/home/ishidafuu/isdf_kizi_stock`）
- `ExecStart`: venv環境のPython実行パス（`/home/ishidafuu/isdf_kizi_stock/venv/bin/python3`）
- `Restart=always`: Bot がクラッシュしても自動再起動
- `RestartSec=10`: 再起動までの待機時間（秒）
- `StandardOutput/StandardError=journal`: ログを systemd の journal に出力

### 3. ログディレクトリの作成

```bash
mkdir -p ~/isdf_kizi_stock/logs
```

### 4. サービスの有効化と起動

```bash
# systemd 設定をリロード
sudo systemctl daemon-reload

# サービスを有効化（起動時に自動起動）
sudo systemctl enable article-bot

# サービスを起動
sudo systemctl start article-bot

# サービスの状態を確認
sudo systemctl status article-bot
```

### 5. 自動起動の確認

Raspberry Pi を再起動して、Bot が自動起動するか確認します。

```bash
sudo reboot
```

再起動後、以下のコマンドで Bot が起動していることを確認：

```bash
sudo systemctl status article-bot
```

---

## 運用・メンテナンス

### 1. update_bot.sh を使った更新

プロジェクトには便利な更新スクリプト `update_bot.sh` が含まれています。
このスクリプトを使うことで、以下の操作を一度に実行できます：

1. GitHubから最新コードを取得（git pull）
2. 依存関係を更新（pip install -r requirements.txt）
3. サービスを再起動（systemctl restart article-bot）
4. ログを表示（journalctl -f）

**使い方:**

```bash
# プロジェクトディレクトリに移動
cd ~/isdf_kizi_stock

# update_bot.sh を実行
./update_bot.sh
```

**実行結果:**

```
========================================
🔄 isdf_kizi_stock の更新を開始します...
========================================
📥 Git Pull...
Already up to date.
📦 ライブラリ更新...
Requirement already satisfied: ...
========================================
🚀 サービスを再起動します...
========================================
✅ 再起動完了。直近のログを表示します（Ctrl+Cで終了）
Dec 06 12:34:56 isdf-pi article-bot[1234]: INFO: Bot起動完了...
```

### 2. よく使うコマンド一覧

| カテゴリ | コマンド | 説明 |
|---------|---------|------|
| **サービス操作** | `sudo systemctl start article-bot` | サービス起動 |
| | `sudo systemctl stop article-bot` | サービス停止 |
| | `sudo systemctl restart article-bot` | サービス再起動 |
| | `sudo systemctl status article-bot` | サービス状態確認 |
| | `sudo systemctl enable article-bot` | 自動起動を有効化 |
| | `sudo systemctl disable article-bot` | 自動起動を無効化 |
| **ログ確認** | `sudo journalctl -u article-bot -f` | リアルタイムログ確認 |
| | `sudo journalctl -u article-bot -n 50` | 最新50行のログ表示 |
| | `sudo journalctl -u article-bot --since today` | 今日のログ表示 |
| | `tail -f ~/isdf_kizi_stock/logs/article_bot.log` | アプリケーションログ確認 |
| **コード更新** | `./update_bot.sh` | ワンコマンド更新（推奨） |
| | `git pull` | 最新コードを取得 |
| | `source venv/bin/activate && pip install -r requirements.txt` | 依存関係更新 |
| **環境確認** | `python3 --version` | Pythonバージョン確認 |
| | `source venv/bin/activate && pip list` | インストール済みパッケージ一覧 |
| | `df -h` | ディスク使用量確認 |
| | `free -h` | メモリ使用量確認 |
| **Git操作** | `git status` | 変更状態確認 |
| | `git log -n 5` | 最新5件のコミット履歴 |
| | `git branch` | ブランチ一覧 |

### 3. 定期メンテナンス

**毎月:**
- ディスク使用量の確認: `df -h`
- ログファイルのローテーション確認: `ls -lh logs/`
- システムアップデート: `sudo apt update && sudo apt upgrade -y`

**アップデート手順:**

```bash
# 1. Botを停止
sudo systemctl stop article-bot

# 2. システムアップデート
sudo apt update && sudo apt upgrade -y

# 3. コード更新
cd ~/isdf_kizi_stock
git pull

# 4. 依存関係更新
source venv/bin/activate
pip install -r requirements.txt

# 5. Botを起動
sudo systemctl start article-bot

# 6. 動作確認
sudo systemctl status article-bot
```

または、`update_bot.sh` を使えば上記の手順（2を除く）を自動で実行できます。

---

## トラブルシューティング

### Bot が起動しない

#### 1. Python バージョンの確認

```bash
source venv/bin/activate
python --version
# Python 3.11.x と表示されることを確認
```

#### 2. 依存関係の再インストール

```bash
source venv/bin/activate
pip install --no-cache-dir -r requirements.txt
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
# venv Python のパスを確認
ls -l ~/isdf_kizi_stock/venv/bin/python3

# 実行権限の確認
~/isdf_kizi_stock/venv/bin/python3 --version
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
cd ~/isdf_kizi_stock

# update_bot.sh を使った簡単な更新
./update_bot.sh
```

または手動で実行する場合：

```bash
# Bot を停止
sudo systemctl stop article-bot

# 最新コードを取得
git pull

# 依存関係を更新
source venv/bin/activate
pip install -r requirements.txt

# Bot を再起動
sudo systemctl start article-bot

# 動作確認
sudo systemctl status article-bot
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
