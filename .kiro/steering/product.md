# Product Overview

Discord経由で記事をストックし、AI要約とタグ付けでObsidianに整理保存するシステム

## 根本課題

**保存した情報を実際に消化・活用できていない**

- NotionにURLを保存するだけで満足し、後から読まない
- 読んでも「なぜ保存したか」を忘れている
- 結果、情報が死蔵される

## ユーザーストーリー

> 「**電車でXを見ている時**」に「**面白い技術記事を見つけた**」ので「**Discordに共有する**」。そうすれば「**後で要約を見て把握でき、必要な時に活用できる**」から。

## Core Capabilities

- **簡単な投げ込み**: DiscordにURL/メモを投稿するだけで自動処理
- **自動整理**: Gemini AIによる自動タグ付け（3〜5個）と要約補足
- **即座の把握**: OGP取得による記事概要の自動抽出
- **継続的な追記**: 後からスレッドにコメントを追加可能
- **Obsidian連携**: GitHubリポジトリ経由でObsidian Vaultに同期

## Target Use Cases

### 移動中の情報キャッチ
電車やバスでSNSを見ている時に見つけた記事を即座に保存

### 技術記事の消化
要約を見て「一旦把握」し、必要な時に元記事を深掘り

### 後からの振り返り
適切なタグで整理され、関連記事を探しやすい

## Scope

### Must Have
- Discord共有でURL/メモを投げ込み
- 投げ込み内容の自動判別（URL / テキスト / URL+コメント）
- OGP取得（タイトル・概要）
- Geminiによるタグ付け（3〜5個）と要約補足
- Obsidianへの出力（GitHub経由、Markdown）
- 「受け取ったよ」のレスポンス
- 後からコメント追記可能

### Nice to Have
- 大カテゴリでの分類
- 関連記事の取得
- 未読通知
- 音声メモ対応

### Out of Scope
- Notion連携
- 複数ユーザー対応
- ペイウォール記事の全文取得

## Value Proposition

記事を保存するだけでなく、AI要約とタグ付けで「消化可能な状態」で整理し、Obsidianで活用できるまでを自動化

---

_Note: This is a new project. As features are implemented, this document will evolve to reflect actual capabilities and patterns._

_Created: 2025-12-03_
