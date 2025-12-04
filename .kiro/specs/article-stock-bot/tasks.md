# Implementation Plan

## 1. プロジェクト基盤セットアップ

- [x] 1.1 (P) Python開発環境とプロジェクト構造の初期化
  - Python 3.11+の環境構築とPoetryによる依存関係管理の設定
  - `pyproject.toml`の作成と基本設定（プロジェクト名、バージョン、依存パッケージ）
  - `.gitignore`に`.env`, `logs/`, `vault/`を追加
  - _Requirements: なし（環境構築タスク）_

- [x] 1.2 (P) ディレクトリ構造の作成とロギング設定
  - `src/bot/`, `src/scraper/`, `src/ai/`, `src/storage/`, `src/utils/`, `config/`, `tests/`, `logs/`, `vault/articles/`ディレクトリを作成
  - `src/utils/logger.py`にRotatingFileHandlerを使用したロガー設定を実装
  - ログファイルのローテーション（最大10MB、7日分保持）を設定
  - _Requirements: 9.1, 9.2, 9.5, 9.6_

- [x] 1.3 (P) 環境変数管理と設定ファイルの実装
  - `.env.sample`を作成し、必要な環境変数のテンプレートを提供
  - `python-dotenv`を使用した環境変数読み込み処理を実装
  - `config/settings.py`にアプリケーション設定（タイムアウト値、タグ数、ファイル命名規則）を定義
  - _Requirements: なし（基盤タスク）_

## 2. Discord Bot Core実装

- [x] 2.1 Discord Bot クライアントとイベントリスナーの実装
  - `src/bot/client.py`にEventListenerクラスを実装（discord.py Clientを継承）
  - `on_message`イベントハンドラを実装し、Bot自身と他のBotのメッセージを除外
  - 監視対象チャンネルの設定と24時間稼働のための起動処理を実装
  - _Requirements: 1.1, 1.3, 1.5_

- [x] 2.2 リアクション管理機能の実装
  - `src/bot/reactions.py`にReactionManagerクラスを実装
  - 受信確認リアクション（👁️）、成功リアクション（✅）の追加処理を実装
  - リアクション追加失敗時のエラーログ記録を実装
  - _Requirements: 1.4, 7.5, 8.5_

- [x] 2.3 メッセージハンドラの実装（オーケストレーション層）
  - `src/bot/handlers.py`にMessageHandlerクラスを実装
  - `handle_new_message()`メソッドでメッセージ受信から保存までのパイプライン処理を統括
  - リアクション追加（受信確認）を1秒以内に実行
  - 成功・失敗通知のDiscordへの返信処理を実装
  - _Requirements: 1.2, 1.4, 7.1, 7.2, 7.3, 7.4, 7.6_

- [x] 2.4 並行処理制御と非同期処理の実装
  - `asyncio.Semaphore(max_concurrent=3)`を使用した並行処理数制限を実装
  - すべての処理パイプラインを`async/await`で非同期化
  - Discordイベントループをブロックしない処理フローを確立
  - _Requirements: 1.1, 1.3, 7.6_

## 3. メッセージ解析とコンテンツ処理

- [x] 3.1 (P) メッセージ内容の判別とURL抽出
  - `src/utils/parser.py`にContentParserクラスを実装
  - `parse_message()`メソッドでURL、コメント、メモを判別・抽出
  - 正規表現でHTTP/HTTPSプロトコルを含む有効なURL形式を認識
  - 複数URL検出時は最初のみ処理対象とし、残りをコメントとして扱う
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

## 4. OGP情報取得とWeb Scraping

- [x] 4.1 (P) OGP情報取得処理の実装
  - `src/scraper/ogp.py`にOGPScraperクラスを実装
  - `aiohttp`を使用した非同期HTTP通信で対象URLからHTMLを取得
  - `beautifulsoup4`でOGPメタタグ（`og:title`, `og:description`, `og:image`）を抽出
  - タイムアウト処理（10秒）とサイズ制限（10MB）を実装
  - _Requirements: 3.1, 3.2, 3.6, 3.7_

- [x] 4.2 (P) OGPフォールバック処理の実装
  - `og:title`が取得できない場合は`<title>`タグを使用
  - `og:description`が取得できない場合は`<meta name="description">`を使用
  - OGP取得が完全に失敗した場合はタイトルを「無題の記事」として記録
  - _Requirements: 3.3, 3.4, 3.5_

## 5. Gemini AI統合

- [x] 5.1 (P) Gemini APIクライアントの実装
  - `src/ai/gemini.py`にGeminiClientクラスを実装
  - `google-generativeai`を使用してGemini Flash 2.5 APIを呼び出し
  - `generate_tags_and_summary()`メソッドで記事タイトルと概要からタグと要約補足を生成
  - タイムアウト処理（30秒）を実装
  - _Requirements: 4.1, 4.6, 4.7_

- [x] 5.2 (P) タグ付けと要約生成ロジックの実装
  - プロンプトテンプレートで3〜5個の日本語タグを生成
  - 要約補足テキスト（100字以内）を生成
  - 生成されたタグ数の検証（3〜5個の範囲内）を実装
  - _Requirements: 4.2, 4.3, 4.4_

- [x] 5.3 (P) Gemini APIフォールバック処理の実装
  - API呼び出し失敗時にデフォルトタグ（"未分類", "要確認"）を適用
  - タイムアウト時のエラーハンドリングとログ記録
  - エラー発生時も処理を継続し、デフォルト値で保存
  - _Requirements: 4.5, 4.7_

## 6. Markdown生成とファイル管理

- [x] 6.1 (P) Markdownファイル生成の実装
  - `src/storage/markdown.py`にMarkdownGeneratorクラスを実装
  - YAMLフロントマター（tags, url, created）を生成
  - Markdownボディ（タイトル、概要、コメント）を生成
  - ファイル名を`YYYY-MM-DD_記事タイトル.md`形式で生成
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.6_

- [x] 6.2 (P) ファイル名サニタイゼーションの実装
  - タイトルに使用できない文字（`/ \ : * ? " < > |`）を除去
  - ファイル名の最大長を100文字に制限し、超過分を切り詰め
  - _Requirements: 5.6, 5.7_

- [x] 6.3 (P) ローカルストレージ処理の実装
  - `src/storage/vault.py`にVaultStorageクラスを実装
  - `vault/articles/`ディレクトリへのMarkdownファイル保存
  - ディレクトリが存在しない場合の自動作成
  - _Requirements: 5.8_

## 7. Git操作とGitHub同期

- [x] 7.1 Git Manager基本実装
  - `src/storage/github.py`にGitManagerクラスを実装
  - GitPythonを使用したGitリポジトリ操作の基盤を構築
  - GitHub Personal Access Token認証の設定
  - _Requirements: 6.4_

- [x] 7.2 Git コミットとプッシュ処理の実装
  - `commit_and_push()`メソッドで新規ファイルの`git add`、コミット作成、プッシュを実行
  - コミットメッセージに記事タイトルを含める
  - GitPythonの同期操作を`asyncio.to_thread()`でラップして非同期化
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 7.3 Git操作の排他制御と競合回避
  - `asyncio.Lock`を使用したGit操作の排他制御を実装
  - 並行プッシュを直列化し、Git競合を回避
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 7.4 GitHubプッシュのリトライ処理とバックアップ
  - プッシュ失敗時の自動リトライ（最大3回）を実装
  - 3回のリトライ後もプッシュが失敗した場合、ローカルにバックアップを保持
  - エラーログ記録とDiscordへのエラー通知を実装
  - _Requirements: 6.5, 6.6, 6.7_

## 8. コメント追記機能

- [x] 8.1 スレッド内コメント検出とファイル特定
  - `src/bot/handlers.py`に`handle_thread_comment()`メソッドを実装
  - スレッドの親メッセージから該当する記事のMarkdownファイルを特定
  - ファイル特定失敗時のエラーメッセージ送信処理を実装
  - _Requirements: 8.1, 8.6_

- [x] 8.2 既存ファイルへのコメント追記処理
  - `src/storage/vault.py`に`append_comment()`メソッドを実装
  - コメント追記前に`git pull`を実行し、最新版を取得
  - 「## コメント」セクションに日付（YYYY-MM-DD形式）とコメント内容を追記
  - _Requirements: 8.2, 8.3_

- [x] 8.3 コメント追記後のGitHub再プッシュ
  - 更新されたファイルをコミットしてGitHubに再プッシュ
  - プッシュ成功時にスレッド内にチェックマークリアクションを追加
  - _Requirements: 8.4, 8.5_

## 9. エラーハンドリングとロギング

- [x] 9.1 (P) 例外キャッチとエラーログ記録の実装
  - 全処理ステップで例外をキャッチし、詳細なエラーログを記録
  - スタックトレース、エラーレベル（INFO/WARNING/ERROR）、日時を含めたログ出力
  - 致命的エラー発生時もBot自体はクラッシュせず、次のメッセージ処理を継続
  - _Requirements: 9.1, 9.2, 9.3_

- [x] 9.2 (P) ネットワークエラーのリトライ処理
  - ネットワークエラー発生時の自動再試行を実装
  - 再試行回数と結果をログに記録
  - _Requirements: 9.4_

- [x] 9.3 (P) 管理者通知設定のサポート
  - 重要なエラー（GitHub push失敗、Gemini API継続失敗）のメール通知設定をサポート
  - 通知設定の有効/無効を環境変数で制御
  - _Requirements: 9.7_

## 10. システム統合とエンドツーエンド検証

- [x] 10.1 メインフロー統合
  - Discord投稿からGitHubプッシュまでのエンドツーエンドフローを統合
  - 各処理ステップのデータ受け渡しを検証
  - 処理時間が30秒以内に完了することを確認（要件7.6）
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

- [x] 10.2 コメント追記フロー統合
  - スレッド検出からファイル更新、GitHubプッシュまでの一連の流れを統合
  - ファイル特定失敗時のエラーハンドリングを検証
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [x] 10.3 エラーハンドリングフロー統合
  - OGP取得失敗時のフォールバック処理を検証
  - Gemini API失敗時のデフォルトタグ適用を検証
  - GitHubプッシュ失敗時のリトライとバックアップ処理を検証
  - _Requirements: 3.5, 4.5, 6.5, 6.6, 9.1, 9.2, 9.3, 9.4_

## 11. テスト実装

- [x] 11.1 (P) ユニットテスト: ContentParser
  - URL単体、URL+コメント、テキストのみの各パターンのテスト
  - 複数URL検出時の最初のURL抽出確認
  - 不正なURL形式の除外確認
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 11.2 (P) ユニットテスト: OGPScraper
  - OGP正常取得ケースのテスト
  - OGP不在時のフォールバック動作確認
  - タイムアウト・サイズ超過時のエラーハンドリング確認
  - `aioresponses`を使用したHTTPリクエストのモック
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [x] 11.3 (P) ユニットテスト: GeminiClient
  - 正常なタグ生成（3〜5個）確認
  - タイムアウト時のデフォルトタグ適用確認
  - API呼び出し失敗時のフォールバック動作確認
  - `unittest.mock.patch`を使用したGemini APIのモック
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

- [x] 11.4 (P) ユニットテスト: MarkdownGenerator
  - YAMLフロントマター生成確認
  - ファイル名サニタイゼーション確認
  - 最大100文字制限の動作確認
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

- [x] 11.5 (P) ユニットテスト: VaultStorage
  - 既存ファイルへのコメント追記確認
  - 日付フォーマット確認
  - ファイル不在時のエラーハンドリング確認
  - `pytest`の`tmp_path` fixtureを使用した一時ディレクトリテスト
  - _Requirements: 5.8, 8.2, 8.3_

- [x] 11.6 (P) 統合テスト: メッセージ受信からファイル生成までのフロー
  - メッセージ受信 → OGP取得 → Gemini呼び出し → ファイル生成の正常系確認
  - 各ステップのデータ受け渡し確認
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1_

- [ ] 11.7 (P) 統合テスト: GitHubプッシュフロー
  - コミット作成 → プッシュ成功の確認
  - プッシュ失敗時のリトライロジック確認
  - ローカルバックアップ作成確認
  - テスト用ローカルGitリポジトリを使用
  - _Requirements: 6.1, 6.2, 6.3, 6.5, 6.6_

- [ ] 11.8 (P) 統合テスト: コメント追記フロー
  - スレッド検出 → ファイル特定 → コメント追記 → プッシュの一連の流れ確認
  - ファイル特定失敗時のエラー通知確認
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [ ] 11.9 (P) 統合テスト: エラーハンドリング統合
  - OGP取得失敗 → フォールバック → 処理継続の確認
  - Gemini失敗 → デフォルトタグ → 処理継続の確認
  - GitHub失敗 → リトライ → バックアップの確認
  - _Requirements: 3.5, 4.5, 6.5, 9.1, 9.3_

- [ ]*11.10 E2Eテスト: Discord投稿から成功通知までのエンドツーエンド
  - 実際のDiscord Bot環境でのURL投稿テスト
  - リアクション追加とリプライメッセージの確認
  - 開発環境専用のDiscordサーバーを使用
  - _Requirements: 1.1, 1.4, 7.1, 7.5, 7.6_

- [ ]*11.11 E2Eテスト: スレッドコメント追記のエンドツーエンド
  - スレッド内コメント → ファイル更新 → GitHubプッシュの確認
  - 実際のDiscord Bot環境でのテスト
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ]*11.12 パフォーマンステスト: タイムアウトとレスポンス時間
  - OGP取得のタイムアウト動作確認（10秒）
  - Gemini APIレスポンス時間測定（目標: 5秒以内）
  - GitHubプッシュのレスポンス時間測定（目標: 3秒以内）
  - 全処理完了時間の測定（目標: 30秒以内）
  - _Requirements: 3.6, 4.7, 7.6_

## 12. デプロイ準備

- [ ] 12.1 Raspberry Pi環境構築ドキュメントの作成
  - Python 3.11+環境構築手順
  - 必要なライブラリのインストール手順（poetry install）
  - `.env`ファイルの設定例と環境変数の説明
  - _Requirements: なし（ドキュメント作成タスク）_

- [ ] 12.2 systemdサービス化の設定
  - Botをバックグラウンドで起動するためのsystemdユニットファイル作成
  - 自動再起動の設定
  - ログ出力の設定
  - _Requirements: 1.3_

- [ ] 12.3 GitHub Repositoryのクローンと初期設定
  - Obsidian Vault用のGitHubリポジトリのクローン手順
  - Personal Access Tokenの設定手順
  - 初期ディレクトリ構造（`vault/articles/`）の作成
  - _Requirements: 6.1, 6.4_
