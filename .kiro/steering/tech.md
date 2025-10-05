# 技術スタック

## アーキテクチャ概要

Scrap-Boardは、FastAPIバックエンド、HTMX駆動のフロントエンド、ローカルLLMサービスの3層構成で設計されています。

```
┌─────────────────┐
│   HTMX + Jinja2 │ フロントエンド（ブラウザ）
└────────┬────────┘
         │ HTTP/HTMX
┌────────▼────────┐
│     FastAPI     │ アプリケーションサーバー
├─────────────────┤
│  SQLite + ORM   │ データ永続化層
└────────┬────────┘
         │ HTTP API
┌────────▼────────┐
│  LM Studio/     │ LLMサービス（ローカル）
│    Ollama       │
└─────────────────┘
```

## バックエンド

### 言語・フレームワーク
- **Python 3.13+**: メイン言語
- **FastAPI**: 高速・モダンなWeb フレームワーク
- **SQLAlchemy 2.0+**: ORM/データベース抽象化
- **Pydantic 2.0+**: データバリデーション・設定管理

### データベース
- **SQLite**: 開発・個人利用向けの軽量DB
- **Alembic**: マイグレーション管理（将来的な本番運用向け）
- **カスタムマイグレーションスクリプト**: ローカル開発向け簡易スクリプト（`migrations/`）

### 主要ライブラリ

#### コンテンツ抽出
- **Trafilatura**: HTML記事抽出（プライマリ）
- **Docling 2.0+**: PDF処理（高精度テキスト・構造抽出）
- **pdfminer.six**: PDFフォールバック処理

#### LLM統合
- **httpx**: 非同期HTTPクライアント
- **openai**: OpenAI互換API クライアント（LM Studio/Ollama向け）

#### データ処理
- **numpy**: 数値計算・埋め込みベクトル処理
- **pandas**: データ分析・統計処理
- **langdetect**: 言語検出

#### バックグラウンドジョブ
- **APScheduler**: スケジューラ（RSS定期取得等）
- **カスタムジョブキュー**: `postprocess_jobs`, `personalization_jobs` テーブルベース

#### その他
- **feedparser**: RSSフィード解析
- **python-dateutil**: 日付パース（RFC 2822等）
- **aiofiles**: 非同期ファイルI/O

## フロントエンド

### アーキテクチャ
- **HTMX**: サーバーサイドHTMLレンダリング + 部分更新
- **Jinja2**: テンプレートエンジン
- **Tailwind CSS**: ユーティリティファーストCSSフレームワーク

### JavaScript（最小限）
- **htmx-minimal.js**: HTMX拡張
- **markdown-preview.js**: マークダウンプレビュー
- **personalized-sort.js**: パーソナライズソートUI
- **icons.js**: アイコン表示ヘルパー

### 設計方針
- **SPAフレームワーク不使用**: React/Vueなどに依存しない軽量実装
- **プログレッシブエンハンスメント**: JavaScriptなしでも基本機能が動作
- **サーバーサイドレンダリング**: SEO対応・初期表示高速化

## LLM統合

### サポート対象
- **LM Studio**（推奨）: GUIでモデル管理、OpenAI互換API提供
- **Ollama**: CLIベースのローカルLLM実行環境

### API構成
- **チャットAPI** (`CHAT_API_BASE`): 要約・分類生成
- **埋め込みAPI** (`EMBED_API_BASE`): ベクトル化・類似検索

### 接続設定
```env
CHAT_API_BASE=http://localhost:1234/v1
CHAT_MODEL=gpt-4o-mini-compat-or-your-local
EMBED_API_BASE=http://localhost:1234/v1
EMBED_MODEL=text-embedding-3-large-or-nomic-embed-text
```

## 開発環境

### 必須ツール
- **Python 3.13+**: ランタイム
- **pip**: パッケージマネージャ
- **venv**: 仮想環境（`.venv/`）
- **Git**: バージョン管理

### 推奨ツール
- **Docker + docker-compose**: コンテナ環境構築
- **Playwright**: E2Eテスト・スクリーンショットテスト
- **pytest**: ユニット・統合テスト

### セットアップ手順
```bash
# 仮想環境作成・有効化
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# または .venv\Scripts\activate  # Windows

# 依存関係インストール
pip install -r requirements.txt

# 環境変数設定
cp .env.example .env
# .envを編集してLLMエンドポイント設定

# データベース初期化
python -m app.database.init

# マイグレーション適用（必要に応じて）
python migrations/apply_migrations.py --db ./data/scraps.db
```

## 共通コマンド

### 開発サーバー起動
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### ワーカープロセス起動
```bash
# ポストプロセスワーカー（要約・埋め込み生成）
python -m app.services.postprocess_queue

# パーソナライゼーションワーカー（嗜好プロファイル更新）
python -m app.services.personalization_queue
```

### テスト実行
```bash
# 全テスト実行
pytest

# 特定テスト実行
pytest tests/test_postprocess.py -v

# Playwrightテスト
pytest tests/test_browser.py --headed
```

### マイグレーション
```bash
# バックアップ作成（必須）
mkdir -p data/backup
cp data/scraps.db data/backup/scraps.db.$(date +%Y%m%d%H%M%S)

# マイグレーション適用
python migrations/apply_migrations.py --db ./data/scraps.db

# ゲストユーザーマイグレーション
python migrations/migrate_null_to_guest.py --dry-run
python migrations/migrate_null_to_guest.py
```

### Docker運用
```bash
# コンテナ起動
docker-compose up -d --build

# ログ確認
docker-compose logs -f app
docker-compose logs -f worker

# コンテナ内でコマンド実行
docker exec -it scrap-board-app-1 python migrations/apply_migrations.py --db ./data/scraps.db
```

## 環境変数

### データベース
- `DB_URL`: SQLite接続文字列（例: `sqlite:///./data/scraps.db`）

### LLM設定
- `CHAT_API_BASE`: チャットAPIエンドポイント
- `CHAT_MODEL`: チャットモデル名
- `EMBED_API_BASE`: 埋め込みAPIエンドポイント
- `EMBED_MODEL`: 埋め込みモデル名
- `TIMEOUT_SEC`: APIタイムアウト（デフォルト: 30秒）
- `MAX_RETRIES`: リトライ回数（デフォルト: 3回）

### アプリケーション
- `APP_TITLE`: アプリケーション名（デフォルト: "Scrap-Board"）
- `APP_VERSION`: バージョン（デフォルト: "1.0.0"）
- `SECRET_KEY`: セッション暗号化キー（本番環境では変更必須）
- `LOG_LEVEL`: ログレベル（INFO/DEBUG/WARNING/ERROR）

### ファイル管理
- `UPLOAD_DIR`: アップロードファイル保存先（デフォルト: `./data/uploads`）
- `ASSETS_DIR`: 静的アセット保存先（デフォルト: `./data/assets`）
- `MAX_FILE_SIZE`: 最大ファイルサイズ（デフォルト: 50MB）

## ポート構成

### 開発環境（標準）
- **8000**: FastAPIアプリケーション（uvicorn）
- **1234**: LM Studio APIサーバー
- **11434**: Ollama APIサーバー

### Docker環境
- **8000**: 公開ポート（ホスト → コンテナ）
- `host.docker.internal`: コンテナ→ホストLLMサービス接続用

## アーキテクチャ設計の主要原則

### シンプルさ優先
- **最小限のJavaScript**: サーバーサイドレンダリング中心
- **モノリシック構成**: マイクロサービスではなく単一アプリケーション
- **標準ライブラリ優先**: 独自実装よりも実績あるライブラリを活用

### プライバシー・セキュリティ
- **ローカルLLM対応**: データ外部送信なし
- **セルフホスト可能**: 外部サービス依存なし
- **認証・認可**: ゲストユーザーモデル（将来的にマルチユーザー拡張可能）

### スケーラビリティ
- **非同期処理**: バックグラウンドジョブキュー
- **キャッシング**: 埋め込みベクトルのDB永続化
- **DB抽象化**: SQLAlchemyによるDB切り替え容易性（PostgreSQL等への移行可能）

### テスタビリティ
- **pytest + モック**: ユニット・統合テスト
- **Playwright**: E2Eテスト・UI回帰テスト
- **CI/CD対応**: テスト自動化前提の設計
