# Project Structure

## Organization Philosophy

**機能ベースの単純構造** - Discord Bot の処理フローに沿ったシンプルなモジュール分割

## Directory Patterns

### Source Code
```
src/
├── bot/              # Discord Bot本体
│   ├── client.py     # Bot起動・イベントハンドラ
│   └── handlers.py   # メッセージ処理ロジック
├── scraper/          # Web記事取得
│   └── ogp.py        # OGP取得処理
├── ai/               # AI処理
│   └── gemini.py     # Gemini API呼び出し（タグ付け・要約）
├── storage/          # 保存処理
│   ├── markdown.py   # Markdown生成
│   └── github.py     # GitHub push処理
└── utils/            # 共通ユーティリティ
    ├── validators.py # URL判定・サニタイズ
    └── logger.py     # ログ設定
```

### Configuration
```
.
├── .env              # 環境変数（Git管理外）
├── pyproject.toml    # Poetry依存管理
└── config/
    └── settings.py   # アプリ設定（タグ数、ファイル命名規則など）
```

### Tests
```
tests/
├── test_ogp.py
├── test_gemini.py
├── test_markdown.py
└── fixtures/         # テストデータ
```

### Output (Obsidian Vault)
```
vault/
└── articles/
    └── YYYY-MM-DD_記事タイトル.md
```

## Naming Conventions

- **Files**: `snake_case.py`
- **Classes**: `PascalCase`（例: `GeminiClient`, `OGPScraper`）
- **Functions**: `snake_case`（例: `fetch_ogp`, `generate_tags`）
- **Constants**: `UPPER_SNAKE_CASE`（例: `MAX_TAG_COUNT`）

## Import Organization

```python
# 1. 標準ライブラリ
import os
from datetime import datetime

# 2. サードパーティ
import discord
from google import generativeai as genai

# 3. ローカルモジュール
from src.scraper.ogp import fetch_ogp
from src.ai.gemini import generate_tags
```

## Code Organization Principles

### 処理フロー中心の設計
各モジュールは処理フローの1ステップに対応
```
Discord投稿 → handlers.py → ogp.py → gemini.py → markdown.py → github.py
```

### 依存関係の最小化
- 各モジュールは独立してテスト可能
- 共通処理は `utils/` に集約

### エラーハンドリングの一貫性
- 各モジュールで例外をキャッチし、ログ出力
- 上位レイヤーにはシンプルな結果のみ返す

### 設定の外部化
- API Key等は `.env` で管理
- アプリ設定は `config/settings.py` に集約

---

_Note: This is a new project with no code yet. This file will be populated as the project structure is established and patterns are implemented._

_Created: 2025-12-03_
