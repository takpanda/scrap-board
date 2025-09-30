# Scrap-Board - ウェブコンテンツ収集・管理システム

Webページ・PDF資料の収集、自動分類、読みやすい表示、検索・要約機能を備えた個人向けコンテンツ管理システム

## 概要


Scrap-BoardはWebコンテンツとPDFの収集、処理、管理を行う日本語ウェブアプリケーションです。自動コンテンツ分類、検索機能、最適なコンテンツ消費のためのリーダーモードを備えています。

## Steering documents

開発方針・構成・プロダクトビジョンは `docs/` 下の steering ドキュメントにまとめています:

- `docs/tech.md` - 技術方針／アーキテクチャ
- `docs/structure.md` - コードベース構造と責務
- `docs/product.md` - プロダクトビジョンとロードマップ

### 主要機能

- **コンテンツ収集**: URL・RSS・PDFの自動取り込み
- **自動分類**: LLM を活用したカテゴリ・タグ付け  
- **Reader Mode**: 快適な読書体験のための最適化表示
- **検索・要約**: 全文検索＋類似検索、AI要約生成
- **ブックマーク嗜好分析**: ブックマーク傾向の可視化と統計情報の表示
- **エクスポート**: Markdown/CSV/JSONL形式での出力

## 技術スタック

- **バックエンド**: FastAPI + SQLite + SQLAlchemy
- **フロントエンド**: HTMX + Jinja2 + Tailwind CSS
- **LLM統合**: LM Studio (既定) / Ollama (OpenAI互換API)
- **PDF処理**: Docling (プライマリ) + pdfminer.six (フォールバック)
- **HTML抽出**: Trafilatura

## クイックスタート

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. 環境設定

```bash
cp .env.example .env
# .envファイルを編集してLLMエンドポイントを設定
```

### 3. データベース初期化

```bash
python -m app.database.init
```

### DBマイグレーション

ローカル開発環境（SQLite）でスキーマ変更を適用するための手順を示します。リポジトリには簡易的なマイグレーションスクリプトが `migrations/` に含まれています。運用環境ではAlembic等の正式なマイグレーションツールを導入してください。

- **バックアップ（必須）**: 変更前にデータベースファイルのバックアップを作成します。fishシェル例:

```fish
mkdir -p data/backup
cp data/scraps.db data/backup/scraps.db.$(date +%Y%m%d%H%M%S)
```

- **利用可能なマイグレーション**: `migrations/` ディレクトリにSQLファイルや適用用スクリプトが入っています。現在のリポジトリには例として:

	- `migrations/001_add_summaries_to_documents.sql`
	- `migrations/002_add_sources_and_thumbnails.sql`

**マイグレーションの適用（ローカル開発向け推奨）**: 付属の Python スクリプト `migrations/apply_migrations.py` を使うことを推奨します。スクリプトは `migrations/*.sql` を辞書順に読み、順に適用します。ローカル向けに idempotent（既に存在するカラムやテーブルで発生する一般的なエラーは警告として無視）に動作するよう設計されています。

注意: 事前に必ずデータベースのバックアップを取り、本番環境では Alembic 等の正式なマイグレーション運用を推奨します。

使い方例（fish シェル）:

```fish
# 仮想環境を有効化
source .venv/bin/activate.fish

# migrations ディレクトリ内のSQLをすべて適用（既定DBパス）
python migrations/apply_migrations.py --db ./data/scraps.db

# もしくは sqlite3 で単一ファイルを適用する場合（補助的な方法）
sqlite3 data/scraps.db < migrations/002_add_sources_and_thumbnails.sql
```

スクリプトの挙動:
- `migrations/*.sql` を辞書順に適用します。
- 既知の "already exists" / "duplicate column" 等のエラーは警告としてログ出力し、処理を継続します（ローカル開発での再実行を想定）。
- 想定外のエラーが出た場合はスクリプトは例外を投げます。ログとバックアップを確認してください。

Docker コンテナでの実行例:

ローカルで Docker / docker-compose を使っている場合、コンテナ内でマイグレーションを実行することができます。以下はよく使うパターンの例です。コンテナ内の作業ディレクトリはリポジトリのルート（例: `/app`）にマウントされている前提です。

- コンテナを一時起動してマイグレーションを実行（`docker-compose` を使用）:

```bash
# データボリュームが ./data をマウントしている前提
docker-compose run --rm app \
	python migrations/apply_migrations.py --db /app/data/scraps.db
```

- 既に `app` コンテナが起動している場合（稼働中コンテナへ exec）:

```bash
# コンテナ名は `docker-compose ps` などで確認
docker exec -it scrap-board-app-1 \
	python migrations/apply_migrations.py --db ./data/scraps.db
```

注意事項:
- Docker コンテナ内のパス（上例では `/app/data/scraps.db`）は `docker-compose.yml` でホスト側 `./data` がどのパスにマウントされているかに依存します。必要に応じてパスを調整してください。
- 本番環境ではマイグレーション適用前に必ずバックアップを取得し、メンテナンスウィンドウやトランザクション戦略を検討してください。

- **Alembicを使う（推奨・運用向け）**: 将来的な運用環境では `alembic` を導入してマイグレーション管理を行ってください。簡単な導入手順:

```bash
pip install alembic
alembic init alembic
# alembic.ini を編集して `sqlalchemy.url` を `sqlite:///./data/scraps.db` に設定
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

- **確認**: マイグレーション適用後にアプリが正常に起動するか確認します。

```bash
uvicorn app.main:app --reload
# ログとエンドポイントを確認し、`/documents` などを操作してエラーがないことを確認
```

注意: 本リポジトリの簡易スクリプトはローカル開発・手元検証向けです。データ損失を避けるため、本番環境ではダウンタイム計画、トランザクション、ロールバック戦略、そして検証済みのバックアップを必ず用意してください。

### 4. LLMサービス起動 (別プロセス)

**LM Studio (推奨):**
```bash
# LM Studioを起動し、チャット・埋め込みモデルをロード
# API設定: http://localhost:1234/v1
```

**Ollama (代替):**
```bash
ollama pull llama3.1:8b-instruct
ollama pull nomic-embed-text  
ollama serve  # http://localhost:11434
```

### 5. アプリケーション起動

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

http://localhost:8000 でアクセス

## Docker での実行

```bash
docker-compose up -d
```

## 使用方法

1. **コンテンツ追加**: URLまたはPDFをアップロード
2. **自動処理**: 抽出→正規化→分類→要約生成
3. **閲覧**: Reader Modeで快適な読書体験
4. **検索**: キーワード・カテゴリ・期間での絞り込み
5. **エクスポート**: 必要な形式でデータ出力

## 設定

主要な環境変数:

```env
DB_URL=sqlite:///./data/scraps.db
CHAT_API_BASE=http://localhost:1234/v1
CHAT_MODEL=your-local-chat-model
EMBED_API_BASE=http://localhost:1234/v1
EMBED_MODEL=your-local-embed-model
TIMEOUT_SEC=30
```

## Periodic External Ingest — ポストプロセッシング

- **目的**: ドキュメントを取り込んだ直後に非同期で要約（短いサマリ）と埋め込み（ベクトル）を生成し、検索とUI表示に即座に反映できるようにします。
- **実装概要**: `app/services/postprocess.py` にて、挿入後に `kick_postprocess_async(document_id)` を呼び出し、バックグラウンドスレッドで `llm_client.generate_summary` と `llm_client.create_embedding` を実行します。これは取り込み経路（`app/services/ingest_worker.py`）から呼ばれます。
- **データベース**: 開発用SQLiteではスキーマ互換性のため `app/core/database.py` の `create_tables()` が追加カラム（`source`, `original_url`, `thumbnail_url`, `fetched_at`, `short_summary` など）を確認・作成します。

### 確認手順（ローカル）

- 仮想環境をアクティブにする (fish):
	- `source .venv/bin/activate.fish`
- 手動テストスクリプト:
	- `python scripts/test_postprocess.py` を実行すると、テスト用ドキュメントを挿入してポストプロセスの結果（短い要約と埋め込みの保存）を標準出力で確認できます。
- 自動テスト:
	- `pytest tests/test_postprocess.py -q` でユニットテストを実行できます（テストは `llm_client` をモックして高速に実行します）。

### 運用上の注意

- 現状は軽量なデーモンスレッドで非同期処理を行っています。高負荷・大量取り込みを行う場合は、Celery/RQ などのワーカーキューを導入して処理の信頼性と再試行を担保してください。
- 埋め込みの永続化先は現在SQLiteのテーブルです。将来的にはFAISSやMilvus、Weaviateなどのベクトルストア統合を検討してください。


### 実行方法（手順）

以下はローカル開発環境で「定期外部取り込み（Periodic External Ingest）」を有効にし、動作確認するための手順です。fishシェル向けのコマンド例を含みます。

前提:
- Python 仮想環境（例: `.venv`）を用意していること
- LLM サービス（LM Studio や Ollama 等）が起動しており、`.env` に `CHAT_API_BASE` / `EMBED_API_BASE` 等が設定されていること

1) 仮想環境を有効化（fish）

```fish
source .venv/bin/activate.fish
```

2) 依存パッケージのインストール（必要な場合）

```fish
pip install -r requirements.txt
```

3) 環境変数ファイルを用意

```fish
cp .env.example .env
# .envを編集してLMのエンドポイント(CHAT_API_BASE, EMBED_API_BASE等)を設定
```

4) サーバ起動（Scheduler が起動し、`sources` テーブルに登録された cron に従って取り込みが実行されます）

```fish
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

- サーバ起動ログに "Scheduler started" が出ていることを確認してください。

5) `sources` の登録
- 管理UI (http://localhost:8000/admin) でソースを追加するか、SQLite に直接行を追加します。
- `sources` の主なカラム: `id, name, type, config, enabled, cron_schedule`
- 例（sqlite3 で直接追加、Qiita ユーザを毎時取得する場合の例）:

```fish
sqlite3 data/scraps.db "INSERT INTO sources (name,type,config,enabled,cron_schedule) VALUES ('qiita-user','qiita','{\"user\":\"someuser\",\"per_page\":10}',1,'0 * * * *');"
```

6) ポストプロセスワーカーを常駐させる（推奨）

開発時はアプリのフォールバックで短時間のスレッド処理が動きますが、永続的にリトライやバックオフを効かせるには DB キューのワーカーを起動してください。

```fish
# 別ターミナルで
python -m app.services.postprocess_queue
```

ワーカーは `postprocess_jobs` テーブルのジョブをポーリングして処理します。

7) 手動テスト（即時動作確認）

```fish
python scripts/test_postprocess.py
```

このスクリプトはテスト用ドキュメントを挿入し、数秒待って `short_summary` や `embeddings` を DB から確認します。

8) Docker での起動

`docker-compose.yml` には `app` と `worker` のサービス定義が含まれています。LM サービスは別途準備してください。

```fish
docker-compose up -d --build
docker-compose logs -f app
docker-compose logs -f worker
```

トラブルシューティング（よくある点）:
- Scheduler が起動していない: `uvicorn` ログに "Scheduler started" があるか確認。pytest 実行時はスケジューラがスキップされる実装があります。
- `sources` がスケジュールされない: `enabled` が 1 か、`cron_schedule` が正しい crontab 式かを確認。
- Postprocess ジョブが処理されない: `postprocess_jobs` テーブルに `pending` ジョブが存在するか、ワーカーが起動しているかを確認。
- LLM への接続失敗: `.env` のエンドポイントとモデル名、LM サービスの稼働状況を確認。

短いチェックリスト:
- 仮想環境を有効化
- `.env` を設定
- `uvicorn` を起動して Scheduler が立ち上がることを確認
- `sources` を追加（UI/DB）
- ワーカーを起動（または docker-compose でworkerを立てる）


## 変更: カードのエッジ強調スタイル

- **確認方法**: サーバーを起動後、`/documents` と `/` を開き、カードの角にグラデーションの境界とホバー時のグローが表示されることを確認してください。
- **該当ファイル**: `app/static/css/style.css` の `.card-edge`、テンプレートは `app/templates/documents.html`, `app/templates/document_detail.html`, `app/templates/index.html` にクラス適用済みです。

## ライセンス

MIT License
