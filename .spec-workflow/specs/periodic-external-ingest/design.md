# Design: periodic-external-ingest

作成日: 2025-09-20

目的:
要件で定義した定期ポーリングによる外部ソース取り込み機能の技術設計を示す。既存の抽出・保存・要約・埋め込み生成パイプラインを再利用しつつ、ソース管理、スケジューラ、サムネイル取得、重複排除ロジックを追加する。

ハイレベルアーキテクチャ:
- Scheduler: 定期ポーリングを行うジョブコントローラ（軽量なジョブキュー/cronベース）。開発初期はプロセス内のスケジューラ（APScheduler）またはOSのcronを想定。将来的にCelery/RQなどの外部ワーカーに移行可能。
- Ingest Worker: 指定ソースからURL/エントリを取得 → `app/services/extractor.py` を使って本文抽出・正規化 → メタデータ付与 → データベース保存 → post-processing（要約/埋め込みキュー）をトリガー。
- Source Manager API/UI: `POST/GET/PUT/DELETE /api/admin/sources` と管理UI（`templates/admin/sources.html`）を追加。各ソースは `sources` テーブルで管理（id,name,type,config,enabled,cron_schedule,last_fetched_at）を保持。
- Duplicate Detection: 新規取得時に以下の順序で重複判定を行う。
  1. 同一 `original_url` が存在するかチェック。
  2. ペイロードの軽量ハッシュ（本文または正規化済みテキストの SHA256）で一致を確認。
  3. 必要に応じて埋め込み類似度（cosine）で閾値以下なら重複とみなす（オプション、性能負荷あり）。
- Thumbnail Extraction: 取得先サイトの `favicon.ico` を優先してダウンロード・保存し、存在しない場合は `og:image` を参照。保存先は `data/assets/thumbnails/`（相対パス）で、`documents.thumbnail_url` に格納する。

データモデル変更（概要）:
- 新規テーブル `sources`:
  - `id` INTEGER PRIMARY KEY
  - `name` TEXT
  - `type` TEXT (e.g., `hatena`, `qiita`, `rss`)
  - `config` JSON (例: tag 名、APIキー有無、feed URL)
  - `enabled` BOOLEAN
  - `cron_schedule` TEXT
  - `last_fetched_at` TIMESTAMP
- `documents` テーブル拡張:
  - `source` TEXT
  - `original_url` TEXT
  - `thumbnail_url` TEXT
  - `fetched_at` TIMESTAMP

データベース移行:
- `migrations/` にスクリプト追加（例: `002_add_sources_and_thumbnails.sql`）。`documents` の列追加と新しい `sources` テーブル作成を行う。

取り込みフロー（詳細）:
1. Scheduler が有効な `sources` を走査し、cron_schedule に従って取得ジョブをキューに入れる。
2. Ingest Worker がソースごとの API / feed を叩き、エントリを取得。
3. 各エントリに対して `app/services/extractor.py` を用いて本文を抽出、`published_at` と `author` を抽出可能なら格納。
4. 重複判定を実施。重複なら更新ポリシーに従い既存レコードを更新（例: メタの補完）またはスキップ。
5. Thumbnail: ページの `favicon.ico` を試行的に取得。HTTP 経路で失敗した場合は `og:image` を確認。画像は最小化したサムネイル（例: 64x64）に変換して保存。
6. 保存後、非同期で要約 & 埋め込みジョブを `app/services/llm_client.py` を通じてトリガー。

API と UI 変更点:
- `GET /api/admin/sources` : ソース一覧取得
- `POST /api/admin/sources` : 新規ソース作成
- `PUT /api/admin/sources/{id}` : 更新（有効/無効、cron の変更）
- `DELETE /api/admin/sources/{id}` : 削除
- 管理UI: `templates/admin/sources.html`（HTMX 部分テンプレートで動的操作）

実装上の注意点:
- 性能: ポーリング頻度が高い場合は外部APIのレート制限に注意。取得ロジックはバックオフ・キューイングを必須にする。
- 再現性: 同一ジョブの二重実行を防ぐためロック/排他制御を導入（DB ロック、ファイルロック、分散ロック等）。
- 画像処理: `Pillow` を使ってサムネイル生成。必要なら `static/uploads/thumbnails/` に配置して配信。
- 設定: `.env` に以下キーを追加推奨: `SCHEDULER_TYPE`, `DEFAULT_POLL_INTERVAL`, `THUMBNAIL_DIR`。

モニタリングとログ:
- 取得ジョブの成功/失敗をログに残し、簡易的なメトリクス（成功率、平均処理時間）を記録する。失敗が増えたソースは管理UIで警告表示。

セキュリティ:
- `robots.txt` 尊重、User-Agent 設定、リクエスト頻度制限。
- 外部APIキーは `config` に格納するが暗号化・環境変数参照を推奨。

移行・リリース手順（概要）:
1. マイグレーションを用意し、ステージングで実行。
2. 新しい `sources` 管理UI をデプロイし、既知ソースを登録。
3. 低頻度で初回取り込みを実行してデータ品質を確認。

参考実装ファイル:
- 抽出: `app/services/extractor.py`
- LLM 呼び出し: `app/services/llm_client.py`
- DB: `app/core/database.py`, `migrations/`

次のアクション:
1. この `design.md` をレビューしてください。
2. レビュー完了で承認リクエストを出します（承認はダッシュボードで行ってください）。
