- [ ] DBマイグレーション追加
_Prompt:
Implement the task for spec ai-summary-on-ingest, first run spec-workflow-guide to get the workflow guide then implement the task:
- **Role**: Backendエンジニア（DBマイグレーション担当）
- **Task**: `documents` テーブルへ `short_summary`, `medium_summary`, `summary_generated_at`, `summary_model` カラムを追加するAlembicマイグレーションを作成する。ローカルSQLite向けに互換性を保つ。
- **Restrictions**: 既存データは破壊しないこと。NULL許容にする。
- **_Leverage**: `core/database.py`, プロジェクトの既存マイグレーションパターン
- **_Requirements**: requirements.md の DB 変更セクション
- **Success**: マイグレーションを適用して `documents` テーブルに新カラムが追加される。既存レコードは壊れない。

- [ ] LLMクライアントに `generate_summary` を追加
_Prompt:
Implement the task for spec ai-summary-on-ingest, first run spec-workflow-guide to get the workflow guide then implement the task:
- **Role**: Backendエンジニア（LLM統合担当）
- **Task**: `services/llm_client.py` に `generate_summary(text, style='short'|'medium', timeout_sec=None)` を追加する。タイムアウト、モデル名指定、エラーハンドリングを実装する。
- **Restrictions**: 既存のクライアントインターフェースを壊さない。外部呼び出しはタイムアウトで打ち切れること。
- **_Leverage**: 既存の `services/llm_client.py`、環境変数 `CHAT_API_BASE` など
- **_Requirements**: 要件の要約生成フロー、コンフィグ設定
- **Success**: モックで呼び出すテストが通る。タイムアウト・例外時は `None` を返すか明示的な例外を投げる仕様が通る。

- [ ] テキスト準備/チャンク処理を追加
_Prompt:
Implement the task for spec ai-summary-on-ingest, first run spec-workflow-guide to get the workflow guide then implement the task:
- **Role**: Backendエンジニア（テキスト処理担当）
- **Task**: `services/extractor.py` に `prepare_text_for_summary(text)` を追加。言語検出、日本語優先の取扱い、長文のチャンク分割と前処理（余計なスクリプト除去）を実装する。
- **Restrictions**: 文章の意味を壊さない簡潔なトランケートのみ。余計な外部依存を増やさない。
- **_Leverage**: 既存の抽出ロジック、Trafilatura出力
- **_Requirements**: 要件の言語検出とチャンク分割の記載
- **Success**: 長文入力でチャンク化が行われ、`generate_summary` に安全に渡せるテキストが生成される。

- [ ] `POST /ingest/url` の拡張（同期モード）
_Prompt:
Implement the task for spec ai-summary-on-ingest, first run spec-workflow-guide to get the workflow guide then implement the task:
- **Role**: Backendエンジニア（API担当）
- **Task**: `api/routes/ingest.py` の URL ingest ハンドラを更新し、取り込み直後に `prepare_text_for_summary` と `generate_summary` を呼び出して、結果をDBに保存する。デフォルトは同期モードでタイムアウト (`SUMMARY_TIMEOUT_SEC`) を遵守する。
- **Restrictions**: 取り込みの成功を妨げない。要約失敗時はNULLを保存し、エラーをログに記録する。
- **_Leverage**: `services/extractor.py`, `services/llm_client.py`, `core/database.py`
- **_Requirements**: API変更セクション
- **Success**: URL取り込み時に `short_summary` がDBに保存される（正常系）。要約失敗時も `document_id` は返る。

- [ ] 非同期モードのジョブキュー設計（オプション）
_Prompt:
Implement the task for spec ai-summary-on-ingest, first run spec-workflow-guide to get the workflow guide then implement the task:
- **Role**: Backendエンジニア（ジョブキュー担当）
- **Task**: 小規模なバックグラウンドジョブ実装（例: `concurrent.futures.ThreadPoolExecutor` を用いた簡易キュー）または既存のバックグラウンドワーカーへのフックを追加し、非同期モードで要約ジョブを処理する。
- **Restrictions**: 複雑なキュー依存（Redis/Celery）を導入しない（必要なら別タスクで提案）。
- **_Leverage**: アプリケーション起動時のバックグラウンドタスクパターン（FastAPI の startup event 等）
- **_Requirements**: 設計の同期/非同期選択
- **Success**: 非同期モードでAPIは直ちに `document_id` を返し、バックグラウンドで要約がDBに書き込まれる。

- [ ] フォールバック簡易要約実装
_Prompt:
Implement the task for spec ai-summary-on-ingest, first run spec-workflow-guide to get the workflow guide then implement the task:
- **Role**: Backendエンジニア（フォールバック担当）
- **Task**: LLM利用不可時に用いる簡易要約関数 `services/simple_summary.py` を実装する（見出し抽出、最初の N パラグラフの結合など）。
- **Restrictions**: LLMの代替であることを明記し、品質は限定される。
- **_Leverage**: `services/extractor.py` の出力
- **_Requirements**: 障害時フォールバック
- **Success**: LLM呼び出し失敗時に簡易要約がDBに保存される（NULLよりは有用な断片がある）。

- [ ] テスト実装
_Prompt:
Implement the task for spec ai-summary-on-ingest, first run spec-workflow-guide to get the workflow guide then implement the task:
- **Role**: テストエンジニア
- **Task**: ユニットテストと統合テストを追加する:
  - `services/llm_client.generate_summary()` のモックテスト
  - `api/routes/ingest.py` の取り込み→DB更新の統合テスト（要約成功/失敗ケース）
- **Restrictions**: テストは既存のテストスイート規約に従う（pytest）
- **_Leverage**: `tests/` ディレクトリの既存テストを参考
- **_Requirements**: テストケース（requirements.md）
- **Success**: 追加テストがCIで通る

- [ ] 既存データ用バッチ移行スクリプト
_Prompt:
Implement the task for spec ai-summary-on-ingest, first run spec-workflow-guide to get the workflow guide then implement the task:
- **Role**: バックエンドエンジニア（移行担当）
- **Task**: `scripts/generate_summaries_for_existing.py` を作成し、`documents` テーブルの本文を順次取り出して要約を生成・保存する。レート制御、失敗時の再試行ロジックを含む。
- **Restrictions**: 実行前に `--dry-run` オプションを用意する。大量リクエストを外部APIへ投げないように間隔制御を行う。
- **_Leverage**: `services/llm_client.py`, DBアクセスユーティリティ
- **_Requirements**: 移行項目
- **Success**: 移行スクリプトで既存レコードに要約が追加される（dry-run で安全性確認可能）。

- [ ] UI更新
_Prompt:
Implement the task for spec ai-summary-on-ingest, first run spec-workflow-guide to get the workflow guide then implement the task:
- **Role**: フロントエンド/テンプレートエンジニア
- **Task**: `templates/document_detail.html` と `templates/documents.html` を更新し、`short_summary` があれば表示、無ければ「要約は準備中です」を表示する。
- **Restrictions**: UIの日本語文言を保守的に変更すること。スタイル変更は最小限。
- **_Leverage**: 既存テンプレート
- **_Requirements**: UIの挙動記載
- **Success**: 要約がDBに入っている場合一覧・詳細で表示される。

---

実装手順:
- 各タスクを開始する前に `tasks.md` 内の該当タスクのチェックボックスを `[-]` に更新してください。
- タスク完了後は `[-]` を `[x]` に更新して次へ進んでください。
