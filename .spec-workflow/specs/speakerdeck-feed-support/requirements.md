# Requirements: SpeakerDeck Feed Support

## 概要
SpeakerDeckの RSS/Atom フィードを登録・自動取り込みし、各プレゼンテーションのPDFをサーバー上に保存して、記事カードからダウンロードできるようにする機能を実装します。これにより、プレゼンテーション資料を効率的に収集・管理できるようになります。

## 背景・動機
- **問題**: 現在、Scrap-Boardは一般的なウェブ記事とPDFアップロードに対応していますが、SpeakerDeckのような専門的なコンテンツソースからの自動収集には対応していません
- **ニーズ**: 技術者やジャーナリストがプレゼンテーション資料を継続的に収集し、オフラインでもアクセスできるようにしたい
- **価値**: フィード登録により新しいプレゼンテーションの自動取り込み、PDFの永続保存によりコンテンツの可用性向上

## ユーザーストーリー

### US-1: SpeakerDeckフィードの登録
**As a** コンテンツ収集者  
**I want to** SpeakerDeckのユーザーアカウントのRSS/Atomフィードを登録できる  
**So that** 新しいプレゼンテーションが自動的に取り込まれる

**Acceptance Criteria:**
- 管理画面のソース登録フォームで「SpeakerDeck」タイプを選択できる
- SpeakerDeckのユーザー名を入力すると、適切なフィードURL（`.rss` または `.atom`）が生成される
- フィードURLを直接入力することもできる
- 登録後、cron スケジュールに従って自動的にフィードが取得される

**EARS:**
- **Event**: ユーザーが管理画面でSpeakerDeckソースを作成する時
- **Condition**: ユーザー名またはフィードURLが入力されている場合
- **Action**: システムは適切なフィードURLを保存し、定期取得スケジュールに追加する
- **Response**: 成功メッセージとソース一覧への追加

### US-2: SpeakerDeckフィードからのエントリ取得
**As a** システム  
**I want to** 登録されたSpeakerDeckフィードから最新エントリを取得する  
**So that** 新しいプレゼンテーションがデータベースに保存される

**Acceptance Criteria:**
- cron スケジュールに従って自動的にフィードを取得する
- RSS/Atom フィードの両方の形式に対応する
- 各エントリから title, link, published, summary を抽出する
- 重複URLは自動的にスキップする（既存の仕組みを利用）
- エラー発生時も他のソースに影響を与えない

**EARS:**
- **Event**: スケジューラーが指定時刻にSpeakerDeckソースをトリガーする時
- **Condition**: ソースが有効（enabled=1）である場合
- **Action**: システムはフィードをパースし、各エントリをingestionパイプラインに送る
- **Response**: ログに取得件数とエラー情報を記録

### US-3: SpeakerDeck PDFの自動ダウンロードと保存
**As a** システム  
**I want to** SpeakerDeckのプレゼンテーションページからPDFを自動的にダウンロードして保存する  
**So that** ユーザーがオフラインでもアクセスできる

**Acceptance Criteria:**
- SpeakerDeckのURL（例: `https://speakerdeck.com/username/presentation-slug`）を検出する
- SpeakerDeck APIまたはoembed機能を利用してPDFダウンロードURLを取得する
- PDFを `data/assets/pdfs/speakerdeck/` ディレクトリに保存する
- ファイル名は `{document_id}.pdf` または `{unique_slug}.pdf` とする
- データベースの documents テーブルに PDF パス（`pdf_path` カラム）を記録する
- ダウンロードエラー時はログに記録するが、ドキュメント登録自体は失敗させない

**EARS:**
- **Event**: SpeakerDeckソースからのドキュメントがingestionパイプラインで処理される時
- **Condition**: URLがSpeakerDeckドメインで、PDF取得が可能な場合
- **Action**: システムはPDFをダウンロードし、指定ディレクトリに保存し、パスをDBに記録する
- **Response**: ドキュメントに `pdf_path` フィールドが設定される

### US-4: 記事カードからのPDFダウンロード
**As a** ユーザー  
**I want to** 記事カード上でダウンロードボタンをクリックしてPDFをダウンロードできる  
**So that** ローカルにPDFを保存できる

**Acceptance Criteria:**
- PDFが保存されているドキュメントのカードに「PDFダウンロード」アイコンまたはボタンが表示される
- ボタンをクリックすると、保存されたPDFファイルがダウンロードされる
- PDFが存在しない場合、ボタンは表示されない
- ダウンロードは `/api/documents/{id}/pdf` エンドポイント経由で行われる
- 適切なContent-Typeヘッダー（`application/pdf`）とContent-Dispositionヘッダーが設定される

**EARS:**
- **Event**: ユーザーがPDFダウンロードボタンをクリックする時
- **Condition**: ドキュメントに `pdf_path` が設定されており、ファイルが存在する場合
- **Action**: システムは指定されたPDFファイルを読み込み、HTTPレスポンスとして返す
- **Response**: ブラウザがPDFファイルのダウンロードを開始する

### US-5: PDF保存状態の管理画面での確認
**As a** 管理者  
**I want to** 管理画面でどのドキュメントにPDFが保存されているか確認できる  
**So that** ストレージ使用状況を把握し、必要に応じて管理できる

**Acceptance Criteria:**
- ドキュメント一覧に「PDF」カラムまたはアイコンが表示される
- PDFが保存されているドキュメントには✓マークまたはファイルサイズが表示される
- PDF保存エラーがあった場合、エラーステータスが表示される
- 検索/フィルターでPDF有無による絞り込みができる（将来的）

**EARS:**
- **Event**: 管理者が管理画面のドキュメント一覧を開く時
- **Condition**: ドキュメントに `pdf_path` が設定されている場合
- **Action**: システムはPDF保存状態を示すUIを表示する
- **Response**: 一目でPDF保存状態を確認できる

## 機能要件

### FR-1: データベーススキーマの拡張
- documents テーブルに `pdf_path TEXT` カラムを追加する
- マイグレーションスクリプトを作成する（`007_add_pdf_support.sql`）

### FR-2: SpeakerDeckソースタイプの実装
- `app/services/ingest_worker.py` に `_fetch_speakerdeck_items()` 関数を追加する
- RSS（`.rss`）とAtom（`.atom`）の両方に対応する
- 設定項目: `username`（オプション）、`url`（直接指定）、`per_page`（デフォルト20）

### FR-3: SpeakerDeck PDF取得機能
- `app/services/speakerdeck_handler.py` を新規作成する
- SpeakerDeck URLからPDFダウンロードURLを取得する関数を実装する
- oembed API（`https://speakerdeck.com/oembed.json?url={url}`）を利用する
- PDFをダウンロードして保存する関数を実装する

### FR-4: Ingestionパイプラインの拡張
- `app/services/ingest_worker.py` の `_insert_document_from_url()` 関数を拡張する
- SpeakerDeckドメインを検出し、PDF取得処理を呼び出す
- PDF保存後、`pdf_path` をドキュメントレコードに保存する

### FR-5: PDFダウンロードAPIエンドポイント
- `app/api/routes/documents.py` に `GET /api/documents/{id}/pdf` エンドポイントを追加する
- ファイルの存在確認とセキュリティチェックを実装する
- `FileResponse` を使用してPDFを返す

### FR-6: UIコンポーネントの追加
- `app/templates/components/_document_card.html` にPDFダウンロードボタンを追加する
- アイコンは既存のアイコンセット（Heroicons等）から選択する
- PDF未保存の場合はボタンを表示しない

## 非機能要件

### NFR-1: パフォーマンス
- PDFダウンロードは非同期処理で行い、ingestionパイプラインをブロックしない
- タイムアウトは30秒とする
- 大きなPDFファイル（>50MB）の処理に注意する

### NFR-2: ストレージ管理
- PDFファイルは `data/assets/pdfs/speakerdeck/` ディレクトリに保存する
- ディレクトリが存在しない場合は自動作成する
- ファイル名の衝突を避けるため、document IDまたはユニークなハッシュを使用する

### NFR-3: エラーハンドリング
- PDF取得失敗時もドキュメント登録は成功させる（PDFはオプショナル）
- エラーログに詳細情報を記録する
- ネットワークエラー、タイムアウト、ファイルシステムエラーを適切に処理する

### NFR-4: セキュリティ
- PDFダウンロードエンドポイントでパストラバーサル攻撃を防ぐ
- ダウンロード元のURLを検証する（SpeakerDeckドメインのみ許可）
- ファイルサイズ制限を設ける（デフォルト100MB）

### NFR-5: 互換性
- 既存のフィード取得メカニズム（RSS、Qiita、Hatena）に影響を与えない
- 既存のドキュメントテーブルへの後方互換性を維持する（`pdf_path` はNULL許可）

## 技術的制約
- Python 3.11+、FastAPI フレームワーク
- SQLite データベース（マイグレーション対応）
- feedparser ライブラリ（RSS/Atom解析）
- httpx ライブラリ（HTTP通信）
- 既存のingestionパイプラインとの統合

## 依存関係
- **前提条件**: 既存のRSSフィード取得機能（hatena, qiita, rss）が動作している
- **ブロッカー**: なし
- **関連機能**: PDF抽出機能（既存）、サムネイル取得機能（既存）

## 除外項目
- SpeakerDeck以外のスライド共有サービス（SlideShare、Docswell等）のサポート
- PDFの自動OCR処理（既存のPDF処理機能を利用）
- PDFのバージョン管理や差分検出
- ユーザー毎のPDFアクセス権限管理（将来のマルチユーザー機能で検討）
- 埋め込みプレビュー機能（PDFビューアー）

## 成功指標
- SpeakerDeckソースが正常に登録され、フィードが取得できること
- 新しいプレゼンテーションが自動的にドキュメントとして保存されること
- PDFファイルが正常にダウンロード・保存されること（成功率 > 90%）
- ユーザーが記事カードからPDFをダウンロードできること
- 既存機能に影響がないこと（全テストが成功）

## 参考資料
- [SpeakerDeck RSS Feed Documentation](https://help.speakerdeck.com/help/is-there-an-rss-feed-for-speaker-deck)
- [SpeakerDeck oEmbed API](https://help.speakerdeck.com/help/how-do-i-use-oembed-to-display-a-deck-on-my-site)
- 既存実装: `app/services/ingest_worker.py` (_fetch_hatena_items, _fetch_rss_items)
- 既存実装: `app/api/routes/ingest.py` (RSS ingestion)
- 既存実装: `app/services/extractor.py` (PDF extraction)
