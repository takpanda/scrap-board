# 設計: AI要約をURL取り込み時に事前生成してDB保存する

## 目的
`requirements.md` の承認に基づき、取り込み時に要約を生成してデータベースへ保存するための具体的な技術設計を示す。

## 全体アーキテクチャ概要
- 既存のURL取り込みフロー（`POST /ingest/url`）に要約生成のステップを追加する。
- 要約生成は非同期もしくは同期のいずれかで行える設計とし、デフォルトは同期（取り込みレスポンス後に要約生成ジョブを完了）だが、長時間処理を回避するためにタイムアウトとフォールバックを設ける。
- LLM呼び出しは `services/llm_client.py` を通して行い、モデル名・タイムアウト・最大トークン等は設定から注入する。

## データベース設計（マイグレーション）
- 既存の`documents`テーブルに以下のカラムを追加するマイグレーションを作成する。
  - `short_summary` TEXT NULL
  - `medium_summary` TEXT NULL
  - `summary_generated_at` TIMESTAMP NULL
  - `summary_model` TEXT NULL

- カラム制約・インデックス
  - 要約は全文検索対象ではないため、インデックス不要。ただし将来的に要約でフィルタする場合は部分インデックスを検討する。

## API変更
- `POST /ingest/url` のハンドラ（`api/routes/ingest.py`）のフローを以下のように拡張する:
  1. リクエストを受け取り、URLの正当性チェックを行う。
 2. 既存の抽出処理（`services/extractor.py`）で本文を取得・正規化する。
 3. ドキュメントレコードをDBに挿入（本文等は保存）して `document_id` を返す（既存動作）。
 4. 要約生成処理を呼び出す（同期/非同期の選択に従う）:
     - 同期モード: 要約生成を実行し、結果を`documents`テーブルの該当レコードに更新。成功/失敗に関わらず最終的にAPIは`document_id`を返す。要約失敗はログに記録。
     - 非同期モード: 要約生成ジョブをキューに投入（例: 内部ジョブキューやバックグラウンドスレッド）。取り込みAPIは直ちに`document_id`を返す。フロントは要約が利用可能かポーリングまたはWebSocketで確認。

## 要約生成フロー（推奨）
- デフォルト: 同期モードだが、要約生成の最大許容時間（`SUMMARY_TIMEOUT_SEC`、例: 8秒）を設定。時間内に完了しない場合はタイムアウトして要約をスキップ（NULL保存）する。
- 手順:
  1. 取得した本文から言語検出（`langdetect`等）を行い、要約の言語を決定（日本語優先）。
  2. 本文を要約向けにトランケート/チャンク分割する（長文対策）。
  3. `services/llm_client.py` の `generate_summary(document_text, length='short'|'medium')` を呼び出す。内部で埋め込みモデル/チャット完了モデルを使い分ける。
  4. 生成した要約は最大長に収める（短: 1024文字, 中: 4096文字）。必要なら切り捨てて末尾に省略記号を付与。
  5. DBの該当レコードを更新し、`summary_generated_at` と `summary_model` を記録。

## 障害時フォールバック
- LLM呼び出し失敗（接続不能、タイムアウト、異常応答）:
  - ログ出力（エラー種別、retry回数、elapsed_ms）
  - 要約カラムはNULLのままにする。
  - （オプション）簡易ルールベースの代替要約を提供（見出し抽出や最初の数段落の抜粋）
- DB更新失敗:
  - 取り込み自体は成功させ、要約更新で障害が起きた場合は再試行キューに入れる。

## コンフィグレーション
- `core/config.py` に以下設定を追加:
  - `SUMMARY_MODE` = `sync` | `async`
  - `SUMMARY_TIMEOUT_SEC` = 8
  - `SHORT_SUMMARY_MAX_CHARS` = 1024
  - `MEDIUM_SUMMARY_MAX_CHARS` = 4096
  - `SUMMARY_MODEL` = 環境依存（LM Studio または Ollama のモデル名）

## 実装詳細（ファイル/関数）
- `api/routes/ingest.py`:
  - `ingest_url()` の中で要約処理の呼び出し（`services/extractor.py` の戻り値を渡す）
- `services/extractor.py`:
  - 既存の `extract_text_from_url()` を再利用
  - 必要に応じて `prepare_text_for_summary(text)` を追加
- `services/llm_client.py`:
  - 新しい関数 `generate_summary(text, style='short'|'medium', timeout_sec=None)` を追加
  - 生成に成功したら要約文字列を返す。失敗時は例外を投げるか `None` を返す
- `core/database.py`:
  - マイグレーション計画を追加（Alembic等を利用する想定）

## メトリクスとログ
- ログ: `summary_generation_start`, `summary_generation_success`, `summary_generation_failure` を含む。
- メトリクス: 要約生成成功率、平均生成時間、モデル別呼び出し回数、要約スキップ回数
- これらをPrometheusやログ集約（例: ELK）へ送るためのフックを用意する。

## テスト戦略
- ユニットテスト:
  - `services/llm_client.generate_summary()` をモックして正常系/異常系を検証
  - `api/routes/ingest.py` の要約フローを統合テスト（要約成功時・失敗時）
- 結合テスト:
  - ローカルでLMサービスをスタブして、取り込み→DB更新→表示までの流れを検証

## 移行（既存データ）
- 既存 `documents` レコードにはマイグレーション後、バッチジョブで要約を生成するスクリプトを作成する（`scripts/generate_summaries_for_existing.py`）。

## セキュリティ/プライバシー
- 外部LLMに送信する前に、機密情報（APIキー、ユーザー個人情報など）が含まれていないかを確認する。必要に応じてマスク処理を導入する。

## 付録: UIの挙動
- `templates/document_detail.html` は `short_summary` が存在すればそれを表示し、存在しない場合は「要約は準備中です」と表示する。

## 次のアクション
1. この設計ドキュメントをレビューの上、承認フローへ提出する。
2. 承認後、`tasks.md` を作成して実装タスクを分割する。
