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
