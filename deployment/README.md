# Deployment Files

このディレクトリには、Article Stock Bot をデプロイするための設定ファイルが含まれています。

## ファイル一覧

### `article-stock-bot.service`

systemd ユニットファイル。Bot を Linux システム上でバックグラウンドサービスとして実行するための設定です。

**主な機能:**
- Bot の自動起動（システム起動時）
- 自動再起動（クラッシュ時）
- ログ出力の管理（systemd journal への統合）
- リソース制限（メモリ使用量の制限）

**使用方法:**

1. ファイルをシステムにコピー:
   ```bash
   sudo cp article-stock-bot.service /etc/systemd/system/
   ```

2. 環境に合わせてパスを編集:
   ```bash
   sudo nano /etc/systemd/system/article-stock-bot.service
   ```

   編集が必要な項目:
   - `User`: 実行ユーザー（デフォルト: `pi`）
   - `WorkingDirectory`: プロジェクトのルートディレクトリ
   - `ExecStart`: Poetry の実行パス

3. サービスを有効化して起動:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable article-stock-bot
   sudo systemctl start article-stock-bot
   sudo systemctl status article-stock-bot
   ```

**詳細な手順:**

完全なデプロイ手順については、[`docs/DEPLOYMENT.md`](../docs/DEPLOYMENT.md) を参照してください。

## 設定のカスタマイズ

### リソース制限

Raspberry Pi のメモリが限られている場合、`MemoryLimit` を調整できます:

```ini
# デフォルト: 512MB
MemoryLimit=512M

# より多くのメモリを使用する場合
MemoryLimit=1G

# 制限を無効にする場合（非推奨）
# MemoryLimit= の行をコメントアウト
```

### 再起動設定

Bot がクラッシュした際の再起動動作を調整できます:

```ini
# デフォルト: 常に再起動、10秒待機
Restart=always
RestartSec=10

# より長い待機時間を設定する場合
RestartSec=30

# 失敗時のみ再起動する場合
Restart=on-failure
```

### ログ設定

ログの出力先を変更できます:

```ini
# デフォルト: systemd journal に出力
StandardOutput=journal
StandardError=journal
SyslogIdentifier=article-stock-bot

# ファイルに出力する場合
StandardOutput=append:/home/pi/article-stock-bot/logs/systemd.log
StandardError=append:/home/pi/article-stock-bot/logs/systemd.log
```

## トラブルシューティング

### サービスが起動しない

```bash
# ステータスを確認
sudo systemctl status article-stock-bot

# ログを確認
sudo journalctl -u article-stock-bot -n 50 --no-pager

# リアルタイムでログを監視
sudo journalctl -u article-stock-bot -f
```

### パスが正しくない

```bash
# Poetry のパスを確認
which poetry

# Python のパスを確認
poetry run which python

# プロジェクトディレクトリを確認
pwd
```

ユニットファイルの `ExecStart` と `WorkingDirectory` を確認して、正しいパスに更新してください。

### 権限の問題

```bash
# ユニットファイルの権限を確認
ls -l /etc/systemd/system/article-stock-bot.service

# 正しい権限を設定（root:root, 644）
sudo chown root:root /etc/systemd/system/article-stock-bot.service
sudo chmod 644 /etc/systemd/system/article-stock-bot.service
```

## 参考資料

- [systemd ドキュメント](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [Raspberry Pi での systemd 使用](https://www.raspberrypi.org/documentation/linux/usage/systemd.md)
- [デプロイメントガイド](../docs/DEPLOYMENT.md)

---

**Last Updated**: 2025-12-04
**Requirement**: 1.3 (24時間稼働)
