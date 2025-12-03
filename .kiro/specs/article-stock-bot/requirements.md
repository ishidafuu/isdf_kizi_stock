# Requirements Document

## Introduction

本仕様書は、Discord Bot を活用した記事ストック・整理システムである「Article Stock Bot」の要件を定義します。ユーザーは Discord にURLや記事リンクを投稿するだけで、自動的にOGP情報を取得し、Gemini AIによるタグ付け・要約を行い、最終的にObsidian VaultにMarkdown形式で保存されます。このシステムにより、移動中に見つけた記事を簡単に保存し、後から「消化可能な状態」で振り返ることができます。

対象ユーザーは個人利用を想定し、Raspberry Pi上で24時間稼働するPython製Botとして実装されます。

## Requirements

### Requirement 1: Discord メッセージ受信と初期処理

**Objective:** Discord利用者として、指定されたチャンネルにURLやテキストを投稿するだけで、Botが自動的に処理を開始してほしい。そうすることで、手間なく記事を保存できる。

#### Acceptance Criteria

1. When ユーザーが指定されたDiscordチャンネルにメッセージを投稿した時、the Article Stock Bot shall メッセージ内容を受信し処理キューに追加する
2. When Botがメンションされたメッセージを受信した時、the Article Stock Bot shall 該当メッセージを優先的に処理対象とする
3. The Article Stock Bot shall 24時間365日稼働し、常にメッセージを監視する
4. When メッセージ受信後1秒以内に、the Article Stock Bot shall リアクション絵文字（目の絵文字など）を追加して受信確認を示す
5. The Article Stock Bot shall Bot自身の投稿メッセージおよび他のBotの投稿を処理対象から除外する

---

### Requirement 2: 入力内容の判別と検証

**Objective:** システム利用者として、URL単体、テキスト単体、またはURL+コメントの混在投稿のいずれでも適切に処理されてほしい。そうすることで、柔軟な投稿スタイルで記事を保存できる。

#### Acceptance Criteria

1. When メッセージ内にURLが含まれる時、the Article Stock Bot shall URL部分を抽出し記事処理モードに移行する
2. When メッセージがURL+コメントの組み合わせである時、the Article Stock Bot shall URL部分と初回コメント部分を分離して保存する
3. When メッセージにURLが含まれず、テキストのみの時、the Article Stock Bot shall メモとして処理し、OGP取得をスキップする
4. If 複数のURLが1つのメッセージに含まれている時、then the Article Stock Bot shall 最初のURLのみを処理対象とし、その他は初回コメントとして扱う
5. The Article Stock Bot shall HTTP/HTTPSプロトコルを含む有効なURL形式のみを記事URLとして認識する

---

### Requirement 3: OGP情報の取得とフォールバック処理

**Objective:** システム利用者として、記事URLから自動的にタイトルと概要が取得されてほしい。そうすることで、記事の内容を素早く把握できる。

#### Acceptance Criteria

1. When 有効なURLが検出された時、the Article Stock Bot shall 該当URLにHTTPリクエストを送信しHTMLを取得する
2. When HTMLが正常に取得できた時、the Article Stock Bot shall `og:title`, `og:description`, `og:image` のOGPメタタグを抽出する
3. If `og:title`が取得できない時、then the Article Stock Bot shall `<title>`タグの内容をタイトルとして使用する
4. If `og:description`が取得できない時、then the Article Stock Bot shall `<meta name="description">`の内容を概要として使用する
5. If OGP取得が完全に失敗した時、then the Article Stock Bot shall URLとユーザーコメントのみを保存し、タイトルは「無題の記事」として記録する
6. The Article Stock Bot shall OGP取得処理のタイムアウトを10秒に設定し、超過した場合はフォールバック処理に移行する
7. When 取得したHTMLが10MB以上の時、the Article Stock Bot shall 処理を中断し、エラーメッセージをDiscordに返す

---

### Requirement 4: Gemini AIによるタグ付けと要約生成

**Objective:** システム利用者として、記事の内容に基づいた適切なタグと要約が自動生成されてほしい。そうすることで、後から記事を探しやすくなり、要点を素早く理解できる。

#### Acceptance Criteria

1. When OGP情報が正常に取得された時、the Article Stock Bot shall 記事タイトルと概要をGemini Flash 2.5 APIに送信する
2. When Gemini APIからレスポンスを受信した時、the Article Stock Bot shall 3個から5個のタグを抽出する
3. The Article Stock Bot shall 生成されたタグを日本語の単語または短いフレーズ形式で取得する
4. When Gemini APIから要約補足テキストを受信した時、the Article Stock Bot shall 元の概要に加えて追加情報として保存する
5. If Gemini API呼び出しが失敗した時、then the Article Stock Bot shall デフォルトタグ（例: "未分類", "要確認"）を適用し、要約補足なしで処理を継続する
6. The Article Stock Bot shall Gemini API呼び出し時に適切なプロンプトテンプレートを使用し、タグの一貫性を保つ
7. If Gemini APIのレスポンスが30秒以内に返らない時、then the Article Stock Bot shall タイムアウトエラーとしてフォールバック処理に移行する

---

### Requirement 5: Markdownファイルの生成

**Objective:** システム利用者として、記事情報がObsidianで読みやすいMarkdown形式で保存されてほしい。そうすることで、Obsidian Vault内で快適に閲覧・検索できる。

#### Acceptance Criteria

1. When OGP取得とタグ付けが完了した時、the Article Stock Bot shall Markdown形式のファイルを生成する
2. The Article Stock Bot shall YAMLフロントマターに `tags` (配列)、`url` (文字列)、`created` (日付) フィールドを含める
3. The Article Stock Bot shall Markdownファイルのヘッダーに記事タイトルを `# タイトル` 形式で記述する
4. The Article Stock Bot shall 「## 概要」セクションにOGP descriptionとGeminiの補足要約を記述する
5. When ユーザーが初回投稿時にコメントを追加していた時、the Article Stock Bot shall 「## コメント」セクションに日付付きコメントを記述する
6. The Article Stock Bot shall ファイル名を `YYYY-MM-DD_記事タイトル.md` 形式で生成し、タイトルに使えない文字をサニタイズする
7. The Article Stock Bot shall ファイル名の最大長を100文字に制限し、超過分は切り詰める
8. The Article Stock Bot shall 生成したMarkdownファイルをローカルの `vault/articles/` ディレクトリに一時保存する

---

### Requirement 6: GitHub Repositoryへの自動プッシュ

**Objective:** システム管理者として、生成されたMarkdownファイルが自動的にGitHub経由でObsidian Vaultに同期されてほしい。そうすることで、手動での同期作業が不要になる。

#### Acceptance Criteria

1. When Markdownファイルが生成された時、the Article Stock Bot shall ローカルGitリポジトリに新規ファイルを追加する
2. When ファイルがGitリポジトリに追加された時、the Article Stock Bot shall 自動的にコミットを作成し、コミットメッセージに記事タイトルを含める
3. When コミットが作成された時、the Article Stock Bot shall GitHub Repositoryにプッシュする
4. The Article Stock Bot shall GitHub Personal Access Tokenを使用して認証を行う
5. If GitHubへのプッシュが失敗した時、then the Article Stock Bot shall ローカルにファイルをバックアップし、3回まで自動リトライを実行する
6. If 3回のリトライ後もプッシュが失敗した時、then the Article Stock Bot shall エラーログを記録し、Discordにエラー通知を送信する
7. When プッシュが成功した時、the Article Stock Bot shall 処理成功をログに記録する

---

### Requirement 7: Discordへのレスポンスとフィードバック

**Objective:** Discord利用者として、記事処理の結果を即座に確認したい。そうすることで、正常に保存されたかどうかを把握できる。

#### Acceptance Criteria

1. When 記事処理が正常に完了した時、the Article Stock Bot shall Discord上の元メッセージにリプライで成功通知を送信する
2. The Article Stock Bot shall 成功通知に記事タイトル、生成されたタグ、保存先ファイル名を含める
3. When OGP取得に失敗したが処理が継続された時、the Article Stock Bot shall 警告メッセージを含むリプライを送信する
4. If 処理全体が失敗した時、then the Article Stock Bot shall エラー内容を含むエラーメッセージをDiscordに返信する
5. When レスポンス送信が完了した時、the Article Stock Bot shall 元メッセージにチェックマーク絵文字のリアクションを追加する
6. The Article Stock Bot shall レスポンスメッセージを処理開始から30秒以内に送信する

---

### Requirement 8: 既存記事へのコメント追記

**Objective:** Discord利用者として、以前保存した記事のスレッドにコメントを追加することで、後から考察や感想を追記したい。そうすることで、記事に対する理解を深めながら情報を蓄積できる。

#### Acceptance Criteria

1. When ユーザーがBot返信メッセージのスレッドにコメントを投稿した時、the Article Stock Bot shall 該当する記事のMarkdownファイルを特定する
2. When 該当記事ファイルが特定された時、the Article Stock Bot shall ファイルの「## コメント」セクションに新しいコメントを追記する
3. The Article Stock Bot shall 追記コメントに日付（YYYY-MM-DD形式）とコメント内容を記録する
4. When コメント追記が完了した時、the Article Stock Bot shall 更新されたファイルをGitHubに再プッシュする
5. When コメント追記処理が成功した時、the Article Stock Bot shall スレッド内にチェックマーク絵文字でリアクションする
6. If 該当する記事ファイルが見つからない時、then the Article Stock Bot shall エラーメッセージをスレッドに返信する

---

### Requirement 9: エラーハンドリングとロギング

**Objective:** システム管理者として、エラー発生時に適切なログが記録され、システムが安定稼働を継続してほしい。そうすることで、問題の診断と対処が容易になる。

#### Acceptance Criteria

1. The Article Stock Bot shall すべての処理ステップで発生した例外をキャッチし、詳細なエラーログを記録する
2. The Article Stock Bot shall ログファイルに日時、エラーレベル（INFO/WARNING/ERROR）、エラー内容、スタックトレースを含める
3. When 致命的なエラーが発生した時、the Article Stock Bot shall Bot自体はクラッシュせず、次のメッセージ処理を継続する
4. If ネットワークエラーが発生した時、then the Article Stock Bot shall 自動的に再試行を行い、再試行回数をログに記録する
5. The Article Stock Bot shall ログファイルのローテーションを実行し、最大7日分のログを保持する
6. When ログファイルが10MBを超えた時、the Article Stock Bot shall 自動的に新しいログファイルを作成する
7. The Article Stock Bot shall 重要なエラー（GitHub push失敗、Gemini API継続失敗）をシステム管理者にメール通知する設定をサポートする
