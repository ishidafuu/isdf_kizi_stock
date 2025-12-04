# Technology Stack

## Architecture

**Event-Driven Bot Architecture**
- Discord Bot（イベントリスナー）→ 処理パイプライン → GitHub自動プッシュ
- ラズパイ上で24時間稼働
- 単一ユーザー、個人利用想定

## Core Technologies

- **Language**: Python 3.11+
- **Bot Framework**: discord.py
- **LLM**: Gemini Flash 2.5 (Google Generative AI)
- **Hosting**: Raspberry Pi（自宅、24時間稼働）
- **Storage**: GitHub Repository（Obsidian Vault同期用）

## Key Libraries

### Discord Bot
- `discord.py`: Discord Bot SDK
- `python-dotenv`: 環境変数管理

### Web Scraping
- `beautifulsoup4`: OGP取得・HTML解析
- `aiohttp`: 非同期HTTP通信（discord.pyとの統合のため、requestsではなくaiohttpを使用）

### AI Integration
- `google-generativeai`: Gemini API SDK

### Git Operations
- `GitPython`: GitHub操作の自動化

### Date/Time
- `python-dateutil`: 日付フォーマット処理

## Development Standards

### Type Safety
- Python 3.11+ の型ヒント（Type Hints）を活用
- 関数シグネチャには型アノテーションを必須とする

### Code Quality
- **Linter**: `ruff` または `flake8`
- **Formatter**: `black`
- **Import Sorting**: `isort`

### Testing
- **Framework**: `pytest`
- **重点テスト領域**:
  - OGP取得の成功/失敗ケース
  - Gemini API呼び出しのモック
  - Markdownファイル生成ロジック

### Error Handling
- OGP取得失敗時: URLとコメントのみ保存
- Gemini API失敗時: デフォルトタグで保存
- GitHub push失敗時: ローカルにバックアップ＋リトライ

## Development Environment

### Required Tools
- Python 3.11+
- Poetry または pip (依存管理)
- Git
- Discord Bot Token
- Gemini API Key
- GitHub Personal Access Token

### Environment Variables
```bash
DISCORD_BOT_TOKEN=xxx
GEMINI_API_KEY=xxx
GITHUB_TOKEN=xxx
GITHUB_REPO=username/obsidian-vault
OBSIDIAN_VAULT_PATH=./vault
```

### Common Commands
```bash
# Dev: poetry run python bot.py
# Test: poetry run pytest
# Lint: ruff check . && black --check .
# Format: black . && isort .
```

## Key Technical Decisions

### OGP取得方式
- `og:title`, `og:description` を優先取得
- フォールバック: `<title>` タグ、meta description

### Markdown形式
```yaml
---
tags: [tag1, tag2, tag3]
url: https://example.com
created: 2025-01-15
---

# タイトル

## 概要
OGP description + Geminiの補足要約

## コメント
- 2025-01-15: 初回投稿時のコメント
```

### ファイル命名規則
`YYYY-MM-DD_記事タイトル.md`（タイトルはサニタイズ済み）

### コスト制約
- 月500円以内の運用
- Gemini Flash 2.5 を利用（低コスト）
- ラズパイホスティングで外部サーバーコスト削減

---

_Note: This is a new project with no code yet. This file will be populated as technology choices are made and patterns emerge._

_Created: 2025-12-03_
