# Requirements Specification: 統一Bot管理システム

## プロジェクト概要

複数のDiscord BotをRaspberry Pi上で統一的な方式で管理・デプロイするシステムの構築。既存のTennis Discovery Agentで実績のある運用方式を標準化し、Article Stock Botを含む今後追加される全てのBotを同じ方式で管理できるようにする。

## ビジネス目標

- **目標1**: 複数のDiscord Botを一貫した方式で運用し、管理コストを削減する
- **目標2**: 新しいBotの追加を迅速かつ確実に行えるようにする
- **目標3**: 既存のTennis Botの実績ある運用方式を活用し、安定性を確保する

---

## 1. 環境・インフラ要件

### 1.1 Raspberry Pi環境
**While** Raspberry Pi上でBotを稼働させる場合、**the system shall** 以下の環境設定を使用すること。

- **ユーザー名**: `ishidafuu`
- **ホスト名**: `isdf-pi`
- **OS**: Raspberry Pi OS (64-bit)
- **ハードウェア**: Raspberry Pi 4 Model B 以上（推奨）

### 1.2 ネットワーク接続
**While** Raspberry Piをセットアップする場合、**the system shall** SSH接続（パスワード認証）を有効化すること。

- 接続形式: `ssh ishidafuu@isdf-pi.local`
- タイムゾーン: `Asia/Tokyo`

### 1.3 必要なソフトウェア
**Where** 新しいRaspberry Pi環境をセットアップする場合、**the system shall** 以下のソフトウェアをインストールすること。

- Python 3.8 以上
- pip（Pythonパッケージマネージャー）
- venv（Python仮想環境）
- Git
- Git LFS（画像・動画管理が必要な場合）

---

## 2. プロジェクト構造要件

### 2.1 プロジェクト配置
**Where** 新しいBotプロジェクトを配置する場合、**the system shall** ホームディレクトリ直下に配置すること。

- 配置パス: `/home/ishidafuu/<project_name>`
- 例: `/home/ishidafuu/isdf_tennis_discovery_agent`
- 例: `/home/ishidafuu/isdf_kizi_stock`（Article Stock Bot）

### 2.2 必須ファイル構成
**Where** 新しいBotプロジェクトをセットアップする場合、**the system shall** 以下のファイルを含むこと。

- `main.py`: エントリーポイント
- `requirements.txt`: 依存関係定義
- `.env`: 環境変数（Git管理外）
- `.env.sample`: 環境変数テンプレート（Git管理）
- `update_bot.sh`: 簡易更新スクリプト
- `README.md`: プロジェクト説明
- `docs/RASPBERRY_PI_SETUP.md`: デプロイメント手順

### 2.3 systemdサービスファイル
**Where** 新しいBotをsystemdサービス化する場合、**the system shall** 以下の命名規則と配置を使用すること。

- ファイル名: `<bot-name>.service`
- 配置: `/etc/systemd/system/<bot-name>.service`
- 例: `/etc/systemd/system/tennis-bot.service`
- 例: `/etc/systemd/system/article-bot.service`

---

## 3. 依存関係管理要件

### 3.1 venv使用
**Where** Pythonの依存関係を管理する場合、**the system shall** venv（Python標準の仮想環境）を使用すること。

- 仮想環境ディレクトリ: `venv/`（プロジェクトルート直下）
- 作成コマンド: `python3 -m venv venv`
- 有効化: `source venv/bin/activate`

**理由**: Poetryは使用せず、シンプルなvenv + requirements.txtで統一する。

### 3.2 requirements.txt
**Where** 依存パッケージを定義する場合、**the system shall** `requirements.txt` を使用すること。

- ファイル名: `requirements.txt`（プロジェクトルート直下）
- フォーマット: pip標準形式
- インストールコマンド: `pip install -r requirements.txt`

### 3.3 バージョン固定
**Where** 本番環境で使用する場合、**the system shall** 依存パッケージのバージョンを固定すること。

- 固定方法: `package==version` 形式
- 例: `discord.py==2.3.2`
- 生成コマンド: `pip freeze > requirements.txt`

---

## 4. systemdサービス要件

### 4.1 サービスファイル標準形式
**Where** systemdサービスファイルを作成する場合、**the system shall** 以下の標準形式を使用すること。

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

### 4.2 自動起動設定
**Where** Botをシステム起動時に自動起動する場合、**the system shall** systemdの`enable`コマンドを使用すること。

- コマンド: `sudo systemctl enable <bot-name>`

### 4.3 自動再起動
**If** Botプロセスがクラッシュした場合、**the system shall** 10秒後に自動的に再起動すること。

- 設定: `Restart=always`、`RestartSec=10`

### 4.4 ログ出力
**While** Botが稼働中の場合、**the system shall** 標準出力と標準エラーをsystemd journalに出力すること。

- 設定: `StandardOutput=journal`、`StandardError=journal`
- 確認コマンド: `sudo journalctl -u <bot-name> -f`

---

## 5. 更新・運用要件

### 5.1 update_bot.sh スクリプト
**Where** Botを更新する場合、**the system shall** `update_bot.sh` スクリプトを提供すること。

スクリプトの標準構成:
```bash
#!/bin/bash
PROJECT_DIR="<project_name>"

echo "========================================"
echo "🔄 Botの更新を開始します..."
echo "========================================"

cd ~/$PROJECT_DIR

echo "📥 Git Pull..."
git pull

echo "📦 ライブラリ更新..."
source venv/bin/activate
pip install -r requirements.txt

echo "========================================"
echo "🚀 サービスを再起動します..."
echo "========================================"

sudo systemctl restart <bot-name>
echo "✅ 再起動完了。直近のログを表示します（Ctrl+Cで終了）"
sudo journalctl -u <bot-name> -n 20 -f
```

### 5.2 スクリプト実行権限
**Where** `update_bot.sh` を作成した場合、**the system shall** 実行権限を付与すること。

- コマンド: `chmod +x update_bot.sh`

### 5.3 更新手順の統一
**When** Botを最新版に更新する場合、**the system shall** `./update_bot.sh` のワンコマンドで完了すること。

処理フロー:
1. Git pull（最新コードの取得）
2. pip install -r requirements.txt（依存関係の更新）
3. systemctl restart（サービスの再起動）
4. journalctl（ログの表示）

---

## 6. 環境変数管理要件

### 6.1 .envファイル
**Where** Bot固有の設定を管理する場合、**the system shall** `.env` ファイルを使用すること。

- 配置: プロジェクトルート直下
- Git管理: `.gitignore` で除外
- 読み込み: `python-dotenv` を使用

### 6.2 .env.sample
**Where** プロジェクトをGitで管理する場合、**the system shall** `.env.sample` をリポジトリに含めること。

- 内容: 環境変数のテンプレート（値は空またはダミー）
- 目的: セットアップ時の参考資料

### 6.3 必須環境変数
**Where** Discord Botをセットアップする場合、**the system shall** 最低限以下の環境変数を定義すること。

- `DISCORD_BOT_TOKEN`: Discord Bot トークン
- `ENV`: 環境（`production`、`development`）
- `LOG_LEVEL`: ログレベル（`INFO`、`DEBUG`、`WARNING`、`ERROR`）

---

## 7. ドキュメント要件

### 7.1 README.md
**Where** プロジェクトをGitで管理する場合、**the system shall** `README.md` にプロジェクト概要を記載すること。

必須セクション:
- プロジェクト名と説明
- 機能概要
- セットアップ手順へのリンク

### 7.2 RASPBERRY_PI_SETUP.md
**Where** Raspberry Piにデプロイする場合、**the system shall** `docs/RASPBERRY_PI_SETUP.md` に詳細な手順を記載すること。

必須セクション:
1. OSのインストール
2. 必要なソフトウェアのインストール
3. プロジェクトのセットアップ
4. systemdによる自動起動
5. 運用・メンテナンス
6. トラブルシューティング

### 7.3 統一フォーマット
**Where** 複数のBotのドキュメントを作成する場合、**the system shall** Tennis Discovery Agentと同じフォーマットを使用すること。

- セクション構成の統一
- コマンド例の形式統一
- トラブルシューティングの項目統一

---

## 8. マイグレーション要件（既存Botの移行）

### 8.1 Poetry → venv 移行
**Where** Poetryベースのプロジェクトをマイグレーションする場合、**the system shall** 以下の手順を実行すること。

1. `pyproject.toml` から依存関係を抽出
2. `requirements.txt` を作成
3. `poetry.lock` を削除
4. `venv` ディレクトリを作成
5. `pip install -r requirements.txt` で依存関係をインストール

### 8.2 systemdサービスファイルの更新
**Where** 既存のsystemdサービスファイルを更新する場合、**the system shall** 標準形式に合わせること。

変更点:
- `ExecStart` のパスを `/usr/bin/poetry run` から `venv/bin/python3` に変更
- `User` を `pi` から `ishidafuu` に変更（該当する場合）

### 8.3 ドキュメントの書き換え
**Where** 既存ドキュメントをマイグレーションする場合、**the system shall** Tennis Botのフォーマットに統一すること。

- `docs/DEPLOYMENT.md` → `docs/RASPBERRY_PI_SETUP.md`
- セクション構成の統一
- Poetry関連の記述を削除

---

## 9. 拡張性要件

### 9.1 新しいBotの追加
**When** 新しいBotを追加する場合、**the system shall** 既存Botと同じセットアップ手順を使用できること。

標準手順:
1. プロジェクトテンプレートから開始
2. `main.py`、`requirements.txt`、`.env.sample` を作成
3. `update_bot.sh` をコピー・編集
4. systemdサービスファイルを作成
5. `docs/RASPBERRY_PI_SETUP.md` を作成

### 9.2 テンプレート化
**Where** 新しいBotを迅速にセットアップする場合、**the system shall** プロジェクトテンプレートを提供すること。

テンプレートの内容:
- 標準ディレクトリ構造
- `.env.sample`
- `update_bot.sh`
- systemdサービスファイルのテンプレート
- `docs/RASPBERRY_PI_SETUP.md` のテンプレート

---

## 10. 品質・保守性要件

### 10.1 一貫性
**Where** 複数のBotを管理する場合、**the system shall** 全てのBotで同じ運用方式を使用すること。

- 依存関係管理: venv + requirements.txt
- サービス管理: systemd
- 更新方法: update_bot.sh
- ドキュメント: 統一フォーマット

### 10.2 シンプルさ
**Where** 運用方式を設計する場合、**the system shall** 可能な限りシンプルな構成を維持すること。

- 複雑なツール（Poetry、Docker等）は使用しない
- 標準的なLinuxツール（systemd、venv、pip）を優先
- ワンコマンドで更新できる仕組み

### 10.3 保守性
**Where** 長期運用を想定する場合、**the system shall** 保守しやすい構成を採用すること。

- ドキュメントの充実
- トラブルシューティングガイドの提供
- よく使うコマンドの一覧化

---

## 11. セキュリティ要件

### 11.1 環境変数の保護
**Where** 機密情報を扱う場合、**the system shall** `.env` ファイルをGit管理外とすること。

- `.gitignore` に `.env` を追加
- リポジトリに機密情報をコミットしない

### 11.2 SSH接続
**Where** Raspberry Piにリモートアクセスする場合、**the system shall** SSHを使用すること。

- パスワード認証または公開鍵認証
- デフォルトのSSHポート（22）またはカスタムポート

---

## 成功基準

### 必須基準
1. ✅ Article Stock BotがPoetryからvenv方式に完全移行できること
2. ✅ Tennis BotとArticle Botが同じ運用方式で管理できること
3. ✅ `update_bot.sh` で両方のBotを更新できること
4. ✅ 両方のBotがsystemdで自動起動すること
5. ✅ ドキュメントが統一フォーマットで整備されていること

### 推奨基準
1. ✅ 新しいBotを30分以内にセットアップできるテンプレートがあること
2. ✅ トラブルシューティングガイドが充実していること
3. ✅ よく使うコマンドが一覧化されていること

---

## 制約事項

1. **ハードウェア**: Raspberry Pi 4 Model B（既存環境）
2. **OS**: Raspberry Pi OS (64-bit)（既存環境）
3. **ユーザー**: `ishidafuu`（既存環境に合わせる）
4. **依存関係管理**: venv + requirements.txt（Poetryは使用しない）
5. **後方互換性**: 既存のTennis Botの動作に影響を与えないこと

---

**Document Version**: 1.0
**Last Updated**: 2025-12-06
**Status**: Draft - Approval Pending
