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
	- `migrations/apply_migration_002.py`（Pythonでの適用例）

- **マイグレーションの適用（簡易スクリプト使用）**: 付属のスクリプトを使って適用できます。

```bash
# SQLファイルを直接適用する例（sqlite3が必要）
sqlite3 data/scraps.db < migrations/001_add_summaries_to_documents.sql

# Pythonスクリプトで適用する例
python migrations/apply_migration_002.py
```

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


## 変更: カードのエッジ強調スタイル

- **確認方法**: サーバーを起動後、`/documents` と `/` を開き、カードの角にグラデーションの境界とホバー時のグローが表示されることを確認してください。
- **該当ファイル**: `app/static/css/style.css` の `.card-edge`、テンプレートは `app/templates/documents.html`, `app/templates/document_detail.html`, `app/templates/index.html` にクラス適用済みです。

## ライセンス

MIT License
