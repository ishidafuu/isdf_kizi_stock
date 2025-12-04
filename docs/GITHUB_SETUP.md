# GitHub Repository セットアップガイド

このドキュメントは、Article Stock Bot が記事を保存するための GitHub Repository（Obsidian Vault）のセットアップ手順を説明します。

## 目次

1. [概要](#概要)
2. [前提条件](#前提条件)
3. [GitHub Personal Access Token の作成](#github-personal-access-token-の作成)
4. [Obsidian Vault リポジトリの準備](#obsidian-vault-リポジトリの準備)
5. [リポジトリのクローンと初期設定](#リポジトリのクローンと初期設定)
6. [Git 認証の設定](#git-認証の設定)
7. [動作確認](#動作確認)
8. [トラブルシューティング](#トラブルシューティング)

---

## 概要

Article Stock Bot は、Discord に投稿された記事を自動的に Markdown 形式で保存し、GitHub Repository にプッシュします。このリポジトリは Obsidian Vault として機能し、記事を整理・検索・閲覧できます。

**処理フロー:**
```
Discord投稿 → Bot処理 → Markdownファイル生成 → GitHub Repository → Obsidian同期
```

**Requirements:**
- Requirement 6.1: ローカルGitリポジトリに新規ファイルを追加
- Requirement 6.4: GitHub Personal Access Token を使用して認証

---

## 前提条件

- GitHub アカウント
- Git がインストールされていること（`git --version` で確認）
- Raspberry Pi または開発環境へのアクセス
- Article Stock Bot のプロジェクトが既にクローンされていること

---

## GitHub Personal Access Token の作成

GitHub Personal Access Token (PAT) は、Bot が GitHub にプッシュする際の認証に使用されます。

### 1. GitHub Settings にアクセス

1. GitHub にログイン
2. 右上のプロフィールアイコンをクリック → **Settings**
3. 左サイドバーの一番下の **Developer settings** をクリック
4. **Personal access tokens** → **Tokens (classic)** をクリック

または、直接以下の URL にアクセス:
- https://github.com/settings/tokens

### 2. 新しいトークンの生成

1. **Generate new token** → **Generate new token (classic)** をクリック
2. トークンの設定を入力:

   **Note (トークン名):**
   ```
   Article Stock Bot - Obsidian Vault Access
   ```

   **Expiration (有効期限):**
   - 推奨: **No expiration**（無期限）
   - または、長期間（例: 1年）を設定
   - 注意: 有効期限が切れると Bot がプッシュできなくなります

   **Select scopes (権限):**
   - ✅ **repo** (Full control of private repositories)
     - このスコープにチェックを入れると、以下のサブスコープも自動的に有効になります:
       - `repo:status`
       - `repo_deployment`
       - `public_repo`
       - `repo:invite`
       - `security_events`

3. ページ下部の **Generate token** をクリック

### 3. トークンのコピーと保存

1. 生成されたトークンが表示されます（`ghp_` で始まる文字列）
2. **重要**: このトークンは一度しか表示されません。必ずコピーして安全な場所に保存してください
3. トークンをコピー（クリップボードアイコンをクリック）

**トークンの例:**
```
ghp_1234567890abcdefghijklmnopqrstuvwxyz12
```

**セキュリティ上の注意:**
- トークンは絶対に公開しないでください
- Git にコミットしないでください
- `.env` ファイルに保存し、`.gitignore` で除外されていることを確認してください

### 4. トークンの保存

後で使用するため、トークンを安全な場所に保存します:

**推奨方法:**
- パスワード管理ツール（1Password, Bitwarden, LastPass など）
- ローカルの暗号化されたファイル

**非推奨:**
- 平文のテキストファイル
- クラウドストレージ（暗号化されていない場合）
- メール

---

## Obsidian Vault リポジトリの準備

### オプション A: 既存リポジトリを使用する場合

既に Obsidian Vault 用の GitHub Repository がある場合は、そのリポジトリを使用できます。

1. リポジトリの URL を確認:
   ```
   https://github.com/username/obsidian-vault
   ```

2. [リポジトリのクローンと初期設定](#リポジトリのクローンと初期設定) に進みます

### オプション B: 新規リポジトリを作成する場合

新しく Obsidian Vault 用のリポジトリを作成します。

#### 1. GitHub で新規リポジトリを作成

1. GitHub にログイン
2. 右上の **+** アイコン → **New repository** をクリック
3. リポジトリの設定を入力:

   **Repository name:**
   ```
   obsidian-vault
   ```
   または、任意の名前（例: `article-archive`, `knowledge-base`）

   **Description (オプション):**
   ```
   Article Stock Bot - Obsidian Vault for archived articles
   ```

   **Visibility:**
   - **Private** を推奨（個人的な記事ストックのため）
   - Public も可能（公開しても問題ない場合）

   **Initialize this repository with:**
   - ✅ **Add a README file** にチェック（推奨）
   - ❌ **Add .gitignore** は不要
   - ❌ **Choose a license** は不要（プライベートリポジトリの場合）

4. **Create repository** をクリック

#### 2. リポジトリ URL の確認

作成されたリポジトリのページで、URL をコピーします:

**HTTPS URL (推奨):**
```
https://github.com/username/obsidian-vault.git
```

---

## リポジトリのクローンと初期設定

### 1. 作業ディレクトリの準備

Bot が記事を保存するディレクトリを準備します。

**パターン A: Bot プロジェクト内に配置する場合（推奨）**

```bash
# Bot プロジェクトディレクトリに移動
cd ~/article-stock-bot

# vault ディレクトリが既に存在する場合は削除（テストデータのクリーンアップ）
rm -rf vault

# GitHub リポジトリをクローン（vault という名前で）
git clone https://github.com/username/obsidian-vault.git vault
```

**パターン B: 別の場所に配置する場合**

```bash
# 任意のディレクトリ（例: ホームディレクトリ）に移動
cd ~

# GitHub リポジトリをクローン
git clone https://github.com/username/obsidian-vault.git

# Bot の設定ファイル (.env) でパスを指定
# OBSIDIAN_VAULT_PATH=/home/pi/obsidian-vault
```

### 2. 初期ディレクトリ構造の作成

Bot が記事を保存するための `vault/articles/` ディレクトリを作成します。

```bash
# クローンしたリポジトリに移動
cd vault  # または cd ~/obsidian-vault

# articles ディレクトリを作成
mkdir -p vault/articles

# .gitkeep ファイルを作成（空ディレクトリを Git に追跡させるため）
touch vault/articles/.gitkeep

# ディレクトリ構造を確認
tree -L 2
```

**期待される出力:**
```
.
├── README.md
└── vault
    └── articles
        └── .gitkeep
```

### 3. 初期コミットとプッシュ

作成したディレクトリ構造を GitHub にプッシュします。

```bash
# Git の設定確認（初回のみ）
git config user.name  # 未設定の場合は以下を実行
git config user.email

# 未設定の場合は設定
git config --global user.name "Your Name"
git config --global user.email "your-email@example.com"

# ディレクトリを Git に追加
git add vault/articles/.gitkeep

# コミット
git commit -m "Initial setup: Create vault/articles directory"

# GitHub にプッシュ
git push origin main
```

**注意**: デフォルトブランチ名は `main` または `master` の場合があります。以下で確認できます:
```bash
git branch
```

### 4. ディレクトリ構造の確認

GitHub のリポジトリページで、以下のディレクトリ構造が作成されていることを確認します:

```
obsidian-vault/
├── README.md
└── vault/
    └── articles/
        └── .gitkeep
```

---

## Git 認証の設定

Bot が GitHub にプッシュする際の認証を設定します。

### 1. Personal Access Token の設定

`.env` ファイルに Personal Access Token を設定します。

```bash
# Bot プロジェクトディレクトリに移動
cd ~/article-stock-bot

# .env ファイルを編集
nano .env
```

以下の行を追加または更新します:

```bash
# GitHub Personal Access Token
GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz12

# GitHub Repository URL（Obsidian Vault のリポジトリ）
GITHUB_REPO_URL=https://github.com/username/obsidian-vault.git
```

**注意:**
- `GITHUB_TOKEN` には、先ほど作成した Personal Access Token をペースト
- `GITHUB_REPO_URL` には、リポジトリの HTTPS URL を指定（`.git` 拡張子を含む）

### 2. Obsidian Vault パスの設定

`.env` ファイルで Vault のローカルパスを指定します。

```bash
# Obsidian Vault のローカルパス
# パターン A（プロジェクト内）
OBSIDIAN_VAULT_PATH=./vault

# パターン B（別の場所）
# OBSIDIAN_VAULT_PATH=/home/pi/obsidian-vault
```

### 3. Git の認証情報キャッシュ（オプション）

Git の認証情報をキャッシュすることで、手動でプッシュする際にパスワードを毎回入力しなくて済みます。

```bash
# 認証情報を永続的に保存（推奨）
git config --global credential.helper store

# または、一定期間キャッシュ（例: 1時間）
git config --global credential.helper 'cache --timeout=3600'
```

**セキュリティ上の注意:**
- `credential.helper store` は認証情報を平文で保存します
- Raspberry Pi がローカルネットワーク内で安全に管理されている場合のみ使用してください

---

## 動作確認

### 1. Bot の設定確認

環境変数が正しく読み込まれるか確認します。

```bash
# Bot プロジェクトディレクトリに移動
cd ~/article-stock-bot

# 環境変数を確認（Token の最初の10文字のみ表示）
poetry run python -c "
from dotenv import load_dotenv
import os
load_dotenv()
print('GitHub Token:', os.getenv('GITHUB_TOKEN', 'Not set')[:10] + '...')
print('GitHub Repo URL:', os.getenv('GITHUB_REPO_URL', 'Not set'))
print('Vault Path:', os.getenv('OBSIDIAN_VAULT_PATH', 'Not set'))
"
```

**期待される出力:**
```
GitHub Token: ghp_123456...
GitHub Repo URL: https://github.com/username/obsidian-vault.git
Vault Path: ./vault
```

### 2. ディレクトリの存在確認

```bash
# vault/articles/ ディレクトリが存在するか確認
ls -la vault/articles/

# 期待される出力:
# drwxr-xr-x 2 pi pi 4096 Dec  4 12:00 .
# drwxr-xr-x 3 pi pi 4096 Dec  4 12:00 ..
# -rw-r--r-- 1 pi pi    0 Dec  4 12:00 .gitkeep
```

### 3. Git の状態確認

```bash
# vault ディレクトリに移動
cd vault

# Git の状態を確認
git status

# 期待される出力:
# On branch main
# Your branch is up to date with 'origin/main'.
# nothing to commit, working tree clean

# リモートリポジトリの確認
git remote -v

# 期待される出力:
# origin  https://github.com/username/obsidian-vault.git (fetch)
# origin  https://github.com/username/obsidian-vault.git (push)
```

### 4. 手動でのテストプッシュ

Bot を起動する前に、手動で Git プッシュできるか確認します。

```bash
# vault ディレクトリに移動
cd ~/article-stock-bot/vault

# テストファイルを作成
echo "# Test Article" > vault/articles/test.md

# Git に追加
git add vault/articles/test.md

# コミット
git commit -m "Test: Manual push test"

# プッシュ
git push origin main
```

**認証プロンプトが表示された場合:**
- Username: GitHub のユーザー名
- Password: **Personal Access Token** を入力（GitHub のパスワードではありません）

**プッシュが成功した場合:**
```
Enumerating objects: 5, done.
Counting objects: 100% (5/5), done.
Delta compression using up to 4 threads
Compressing objects: 100% (3/3), done.
Writing objects: 100% (4/4), 400 bytes | 400.00 KiB/s, done.
Total 4 (delta 1), reused 0 (delta 0)
To https://github.com/username/obsidian-vault.git
   abc1234..def5678  main -> main
```

GitHub のリポジトリページで `vault/articles/test.md` が追加されていることを確認してください。

### 5. テストファイルのクリーンアップ

```bash
# テストファイルを削除
git rm vault/articles/test.md
git commit -m "Remove test file"
git push origin main
```

---

## トラブルシューティング

### プッシュ時に認証エラーが発生する

#### エラーメッセージ例:
```
remote: Support for password authentication was removed on August 13, 2021.
fatal: Authentication failed for 'https://github.com/username/obsidian-vault.git/'
```

#### 原因:
GitHub パスワードを使用しようとしています。Personal Access Token を使用する必要があります。

#### 解決方法:

1. **Personal Access Token を確認:**
   - Token が正しくコピーされているか確認
   - Token の有効期限が切れていないか確認
   - Token に `repo` スコープが付与されているか確認

2. **Token を再入力:**
   ```bash
   # 認証情報キャッシュをクリア
   git config --global --unset credential.helper
   rm ~/.git-credentials

   # 再度プッシュを試す
   git push origin main

   # Username: GitHub のユーザー名
   # Password: Personal Access Token を入力
   ```

3. **`.env` ファイルの Token を確認:**
   ```bash
   # Bot の .env ファイルを確認
   grep GITHUB_TOKEN .env
   ```

### リポジトリが見つからないエラー

#### エラーメッセージ例:
```
fatal: repository 'https://github.com/username/obsidian-vault.git/' not found
```

#### 原因:
- リポジトリの URL が間違っている
- リポジトリがプライベートで、認証情報が正しくない
- リポジトリが削除された

#### 解決方法:

1. **リポジトリ URL を確認:**
   ```bash
   # リモート URL を確認
   git remote -v

   # 正しい URL に変更
   git remote set-url origin https://github.com/username/obsidian-vault.git
   ```

2. **GitHub でリポジトリの存在を確認:**
   - ブラウザで `https://github.com/username/obsidian-vault` にアクセス
   - リポジトリが存在するか確認

3. **Personal Access Token の権限を確認:**
   - Token に `repo` スコープが付与されているか確認

### Permission denied エラー

#### エラーメッセージ例:
```
remote: Permission to username/obsidian-vault.git denied to another-user.
fatal: unable to access 'https://github.com/username/obsidian-vault.git/': The requested URL returned error: 403
```

#### 原因:
- 間違った Personal Access Token を使用している
- Token の権限が不足している

#### 解決方法:

1. **Token の所有者を確認:**
   - Token が正しい GitHub アカウントで作成されているか確認

2. **Token のスコープを確認:**
   - GitHub Settings → Developer settings → Personal access tokens で Token を確認
   - `repo` スコープが有効になっているか確認

3. **新しい Token を作成:**
   - 古い Token を削除
   - 新しい Token を作成（`repo` スコープを含む）
   - `.env` ファイルを更新

### ディレクトリが存在しないエラー

#### エラーメッセージ例（Bot 実行時）:
```
FileNotFoundError: [Errno 2] No such file or directory: 'vault/articles'
```

#### 原因:
- `vault/articles/` ディレクトリが作成されていない
- Vault のパス設定が間違っている

#### 解決方法:

1. **ディレクトリを作成:**
   ```bash
   mkdir -p vault/articles
   ```

2. **Vault パスを確認:**
   ```bash
   # .env ファイルを確認
   grep OBSIDIAN_VAULT_PATH .env

   # パスが正しいか確認
   ls -la $OBSIDIAN_VAULT_PATH/vault/articles
   ```

3. **ディレクトリ構造を再確認:**
   ```bash
   tree vault -L 2
   # または
   find vault -type d
   ```

### Git の競合エラー

#### エラーメッセージ例:
```
error: Your local changes to the following files would be overwritten by merge:
  vault/articles/some-file.md
Please commit your changes or stash them before you merge.
```

#### 原因:
- ローカルとリモートで同じファイルが変更されている
- Bot が複数のインスタンスで同時にプッシュしようとしている

#### 解決方法:

1. **Bot のインスタンスを確認:**
   ```bash
   # Bot が複数起動していないか確認
   ps aux | grep python | grep bot
   ```

2. **Git の状態を確認:**
   ```bash
   cd vault
   git status
   ```

3. **最新版を取得してマージ:**
   ```bash
   # 変更をコミット
   git add .
   git commit -m "Resolve conflicts"

   # 最新版を取得
   git pull origin main

   # 競合を解決（必要に応じて）
   # git mergetool または手動で編集

   # プッシュ
   git push origin main
   ```

---

## セキュリティベストプラクティス

### Personal Access Token の管理

1. **Token の定期的な更新:**
   - 3〜6ヶ月ごとに Token を再生成することを推奨
   - 古い Token は削除

2. **最小限の権限:**
   - 必要最低限のスコープのみを付与（`repo` のみ）

3. **Token の保管:**
   - パスワード管理ツールで管理
   - `.env` ファイルは `.gitignore` で除外されていることを確認

### リポジトリのセキュリティ

1. **プライベートリポジトリの使用:**
   - 個人的な記事ストックはプライベートリポジトリを推奨

2. **ブランチ保護（オプション）:**
   - GitHub Settings → Branches で `main` ブランチの保護を設定
   - ただし、Bot は直接プッシュする必要があるため、注意が必要

---

## 次のステップ

GitHub Repository のセットアップが完了したら、以下のドキュメントを参照してください:

1. **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Bot の起動と systemd サービス化
2. **テスト投稿** - Discord チャンネルに URL を投稿して、Bot が正常に動作するか確認

---

## サポート

問題が解決しない場合は、以下の情報を含めて Issue を作成してください:

- エラーメッセージの全文
- Git のバージョン（`git --version`）
- リポジトリの URL（プライベート情報を除く）
- 実行したコマンドとその出力

---

**Document Version**: 1.0
**Last Updated**: 2025-12-04
**Requirements**: 6.1, 6.4
**Status**: Production Ready
