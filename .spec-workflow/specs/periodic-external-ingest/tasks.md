# Tasks: periodic-external-ingest

作成日: 2025-09-20

実行手順: 実装を始めるタスクの行頭の `- [ ]` を `- [-]` に変更してから作業を開始し、完了したら `- [x]` にすること。

- [x] Add `sources` table and DB migrations
  - _Prompt:
    - Role: データベースエンジニア
    - Task: `migrations/002_add_sources_and_thumbnails.sql` を追加して、`sources` テーブルと `documents` テーブルの `thumbnail_url`, `source`, `original_url`, `fetched_at` カラムを追加する。
    - Restrictions: 既存データを壊さない。マイグレーションは idempotent を意識する。
    - _Leverage: `app/core/database.py`, `migrations/` フォルダ
    - _Requirements: requirements.md のデータモデル変更を実装
    - Success: マイグレーションがステージングDBで適用でき、既存のテストに破壊的変更を与えない。

- [x] Implement `sources` API and admin UI
  - _Prompt:
    - Role: フルスタック開発者
    - Task: `GET/POST/PUT/DELETE /api/admin/sources` を追加し、HTMX を用いた `templates/admin/sources.html` を実装する。`sources` の CRUD と有効/無効切替、cron_schedule 編集を可能にする。
    - Restrictions: 認可は既存の管理エンドポイントと統一すること。UI は日本語であること。
  - _Leverage: `app/api/routes/`, `templates/`, `static/js/`（必要なら）
    - _Requirements: 要件の管理UI項目を満たす
  - Success: UI からソースを追加・編集・無効化でき、API 経由で `sources` テーブルが更新される。
  - Notes: 実装ファイル `app/api/routes/admin_sources.py`, `templates/admin/sources.html`, `migrations/002_add_sources_and_thumbnails.sql` を追加済み。

- [x] Scheduler: periodic polling worker
  - _Prompt:
    - Role: バックエンドエンジニア
    - Task: 軽量なスケジューラ（APScheduler での実装を推奨）を導入し、`sources.cron_schedule` に基づくジョブ登録と実行を行う。
    - Restrictions: 同一ジョブの重複実行を防ぐ排他制御を入れること。
  - _Leverage: `app/main.py`（アプリ起動時のジョブ登録）、`app/services/` にジョブ実行ロジックを作成
    - _Requirements: 定期ポーリングのみをサポート
  - Success: 設定した cron スケジュールで Ingest ジョブが登録・実行される。
  - Notes: 実装ファイル `app/services/scheduler.py`, `app/services/ingest_worker.py` を追加し、`app/main.py` の起動処理に組み込みました（スタブで fetch を呼び出します）。

- [x] Ingest Worker: source-specific fetchers
  - _Prompt:
    - Role: バックエンドエンジニア
    - Task: `hatena`, `qiita`, `rss` 向けのフェッチャを実装（config から tag / feed URL を読み取る）。フェッチ結果はエントリ単位で Ingest パイプラインに投入する。
    - Restrictions: API レートリミットに配慮し、エラー時はログとリトライを行うこと。
    - _Leverage: `app/services/extractor.py`、`app/services/llm_client.py`
    - _Requirements: 要件のソースタイプサポート
    - Success: 各ソースからエントリを取得して DB に取り込めること（手動テストで確認）。

- [x] Duplicate detection and merge policy
  - _Prompt:
    - Role: データエンジニア
    - Task: `original_url`、SHA256 ハッシュ、（オプションで）埋め込み類似度による重複検出ロジックを実装。重複時の更新ポリシーを定義する。
    - Restrictions: パフォーマンスを考慮すること。埋め込み類似度はオプションフラグで切り替えられること。
    - _Leverage: `app/services/similarity.py`、`app/core/database.py`
    - _Requirements: 重複排除と idempotent 性
    - Success: 同一コンテンツを再取得しても新規レコードが作成されないことを自動テストで確認。

- [x] Thumbnail extraction and storage
  - _Prompt:
    - Role: フロントエンド/バックエンド共同
    - Task: ページの `favicon.ico` を優先して取得し、無ければ `og:image` を利用してサムネイルを生成・保存する。Pillow を使って 64x64 にリサイズ。
    - Restrictions: 画像取得は外部リクエストの失敗に備えてタイムアウトを短く設定すること。
    - _Leverage: `static/` または `data/assets/thumbnails/`、`app/services/extractor.py`
    - _Requirements: thumbnail_url の保存と優先順
    - Success: 取り込んだドキュメントに `thumbnail_url` が保存され、一覧・詳細で表示される。

- [x] Post-processing: summary and embedding triggers
  - _Prompt:
    - Role: ML/バックエンドエンジニア
    - Task: 取り込み完了後に要約生成（短・中）と埋め込み生成ジョブを非同期でキックするロジックを実装する。
    - Restrictions: LLM エンドポイントのタイムアウトとエラーを扱うこと。
    - _Leverage: `app/services/llm_client.py`, `scripts/generate_summaries_for_existing.py`
    - _Requirements: 要件の要約・埋め込み生成
    - Success: ジョブがキューに入り、`summaries` と `embeddings` が生成される。

- [x] Tests: unit and integration tests
  - _Prompt:
    - Role: テストエンジニア
    - Task: 主要フロー（フェッチ → 抽出 → 保存 → 重複排除 → サムネイル → ポストプロセス）をカバーするユニットと統合テストを作成する。
    - Restrictions: テストはローカルで実行でき、外部APIはモック可能であること。
    - _Leverage: `tests/` フォルダ、`conftest.py`
    - _Requirements: Acceptance Tests をカバー
    - Success: テストスイートが CI 上で成功する。
