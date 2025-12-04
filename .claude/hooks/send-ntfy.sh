#!/bin/bash

# Claude Codeタスク完了時にNTFYで通知を送信
# トピックURL: ntfy.sh/a2b574c90314d3a5873add21211540ae

NTFY_URL="https://ntfy.sh/a2b574c90314d3a5873add21211540ae"
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
PROJECT_NAME=$(basename "$PROJECT_DIR")

# タイムスタンプ
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# 現在のブランチ名を取得
BRANCH=$(cd "$PROJECT_DIR" && git branch --show-current 2>/dev/null || echo 'unknown')

# メッセージの構築
MESSAGE="Claude Codeのタスクが完了しました

プロジェクト: $PROJECT_NAME
ブランチ: $BRANCH
完了時刻: $TIMESTAMP"

# NTFY通知を送信
curl -X POST \
  -H "Title: ✅ Claude Code タスク完了" \
  -H "Priority: high" \
  -H "Tags: white_check_mark,robot" \
  -d "$MESSAGE" \
  "$NTFY_URL" \
  --silent --show-error --max-time 5

exit 0
