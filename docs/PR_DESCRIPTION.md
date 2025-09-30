# PR: AI summary on ingest

このPRは「URL取り込み時にAI要約を生成してDBへ保存する」機能を実装します。

## 変更内容（概要）
- DB: `documents` テーブルに `short_summary`, `medium_summary`, `summary_generated_at`, `summary_model` を追加するマイグレーションを追加。
- API: 取り込み時に要約を生成する同期/非同期フローを追加。`GET /api/documents/{id}` が要約フィールドを返します。
- LLM統合: `app/services/llm_client.py` に `generate_summary` を追加。
- 既存データ移行: `scripts/generate_summaries_for_existing.py` を追加（ドライラン・再開オプションあり）。
- テスト: 同期/非同期の単体・統合テストを追加しました。

## 検証手順
1. ローカルでマイグレーションを適用: `python migrations/apply_migrations.py`
2. 仮起動: `uvicorn app.main:app --reload`（LLMサービスが必要）
3. テスト実行: `pytest tests/ -q`
4. 既存データ確認: `sqlite3 data/scraps.db "SELECT COUNT(*) FROM documents WHERE short_summary IS NULL;"`
5. 既存データ移行（dry-run）: `python scripts/generate_summaries_for_existing.py --dry-run --limit 5`

## マージ手順
1. レビューで承認を得る
2. `main` ブランチへマージ
3. 本番環境へはローリングデプロイで段階的に反映し、移行は夜間に実行する

## 注意点
- LLMサービスの可用性に依存するため、モデルのエンドポイントやタイムアウト設定を環境ごとに調整してください。
- 大量データ移行はワーカーキューに移行することを推奨します。
