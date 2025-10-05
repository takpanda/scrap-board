# 技術スタック

## アーキテクチャ概要

Scrap-Boardは、シンプルで保守しやすいモノリシックWebアプリケーションとして設計されています。

### アーキテクチャパターン
- **モノリシック**: 単一のFastAPIアプリケーション
- **テンプレート駆動型**: Jinja2テンプレートによるサーバーサイドレンダリング
- **HTMXベースSPA風UI**: AJAX的な部分更新をHTMXで実現
- **非同期バックグラウンド処理**: APScheduler + スレッドプールで要約・埋め込み生成

### システム構成図

```
┌─────────────────┐
│  ブラウザ       │
│  (HTMX + Jinja2)│
└────────┬────────┘
         │ HTTP
┌────────▼────────┐
│  FastAPI App    │
│  (uvicorn)      │
├─────────────────┤
│  SQLite DB      │
│  (SQLAlchemy)   │
└─────────────────┘
         │
┌────────▼────────┐
│  LM Studio/     │
│  Ollama         │
│  (OpenAI API互換)│
└─────────────────┘
```

## バックエンド

### 言語・フレームワーク
- **Python 3.13+**: メイン開発言語
- **FastAPI 0.104+**: 高速なWeb APIフレームワーク
- **Uvicorn**: ASGI サーバー（標準モード、リロード対応）
- **SQLAlchemy 2.0+**: ORM（Object-Relational Mapping）
- **Alembic 1.12+**: データベースマイグレーション管理

### データベース
- **SQLite**: 軽量・ファイルベースのRDB
  - パス: `./data/scraps.db`
  - フルテキスト検索: FTS5（タイトル、コンテンツ）
  - ベクトル埋め込み: BLOBとして保存（将来的に専用ベクトルストア検討）

### コンテンツ抽出
- **Trafilatura 1.6+**: HTML→Markdown変換、Webページ抽出
- **Docling 2.0+**: PDF抽出（プライマリ、高精度）
- **pdfminer.six**: PDF抽出（フォールバック、軽量）
- **Feedparser 6.0+**: RSS/Atomフィード解析

### LLM統合
- **httpx 0.25+**: 非同期HTTPクライアント
- **OpenAI SDK 1.0+**: LM Studio/Ollama（OpenAI互換API）との連携
- **LM Studio**: ローカルLLM（推奨、GUIで簡単セットアップ）
- **Ollama**: ローカルLLM（代替、CLIベース）

### バックグラウンドジョブ
- **APScheduler 3.10+**: cron形式のスケジューリング
- **スレッドプール**: 要約・埋め込み生成の非同期実行
- **DBキュー**: `postprocess_jobs`テーブルでジョブ管理（リトライ対応）

### ユーティリティ
- **python-dotenv 1.0+**: 環境変数管理（`.env`ファイル）
- **Pydantic 2.0+**: データバリデーション・設定管理
- **langdetect 1.0.9+**: 言語検出（日本語/英語判定）
- **python-dateutil 2.8.2+**: RFC 2822等の日付パース
- **aiofiles 23.0+**: 非同期ファイル操作

## フロントエンド

### テンプレートエンジン
- **Jinja2 3.1+**: Pythonテンプレートエンジン
  - パス: `app/templates/`
  - 部分テンプレート: `app/templates/partials/`（再利用可能コンポーネント）

### CSSフレームワーク
- **Tailwind CSS**: ユーティリティファーストCSS
  - 最小化版: `app/static/css/tailwind.min.css`
  - カスタムスタイル: `app/static/css/style.css`（グローバルボタンスタイル等）
  - カード装飾: `app/static/css/card-edge-fix.css`

### JavaScript
- **Vanilla JavaScript**: フレームワークなし、軽量実装
  - `app/static/js/personalized-sort.js`: パーソナライズ機能のトグル・UI
  - `app/static/js/markdown-preview.js`: Markdown表示
  - `app/static/js/icons.js`: Lucideアイコンの初期化
- **HTMX（minimal版）**: `app/static/js/htmx-minimal.js`
  - AJAX的な部分更新（`hx-get`, `hx-post`, `hx-target`）
  - プッシュ履歴（`hx-push-url`）
  - ローディングインジケーター（`hx-indicator`）

### アイコンシステム
- **Lucide Icons**: SVGアイコンライブラリ
  - CDN経由で読み込み
  - `data-lucide`属性で動的にレンダリング

## 開発環境

### 必須ツール
- **Python 3.13+**: 開発言語
- **pip**: パッケージ管理
- **virtualenv**: 仮想環境（推奨: `.venv/`）
- **SQLite3**: データベースCLI（デバッグ・マイグレーション）

### 推奨ツール
- **LM Studio**: ローカルLLM（GUI、簡単セットアップ）
- **Ollama**: ローカルLLM（CLI、代替）
- **Docker + docker-compose**: コンテナ実行（オプション）
- **pytest**: テスト実行
- **Playwright**: E2Eテスト（ブラウザ自動化）

### エディタ/IDE
- **VS Code**: 推奨（Python拡張、Jinja2シンタックスハイライト）
- **PyCharm**: 代替
- **Claude Code**: AI駆動開発（spec-driven development）

## よく使うコマンド

### 開発環境セットアップ

```bash
# 仮想環境作成（fishシェル例）
python -m venv .venv
source .venv/bin/activate.fish

# 依存パッケージインストール
pip install -r requirements.txt

# 環境変数設定
cp .env.example .env
# .envを編集してLLMエンドポイントを設定

# データベース初期化
python -m app.database.init

# マイグレーション適用（必要に応じて）
python migrations/apply_migrations.py --db ./data/scraps.db
```

### アプリケーション起動

```bash
# 開発サーバー起動（ホットリロード有効）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# ポストプロセスワーカー起動（別ターミナル）
python -m app.services.postprocess_queue

# パーソナライゼーションワーカー起動（別ターミナル）
PYTHONPATH=. python scripts/run_preference_worker.py --interval 2.0 
```

### テスト実行

```bash
# 全テスト実行
pytest

# 特定テスト実行
pytest tests/test_postprocess.py -v

# Playwrightテスト（E2E）
pytest tests/test_browser.py --headed

# カバレッジ付きテスト
pytest --cov=app --cov-report=html
```

### データベース操作

```bash
# SQLite CLIで接続
sqlite3 data/scraps.db

# スキーマ確認
sqlite3 data/scraps.db ".schema documents"

# バックアップ作成
cp data/scraps.db data/backup/scraps.db.$(date +%Y%m%d%H%M%S)
```

### Docker実行

```bash
# コンテナビルド＆起動
docker-compose up -d --build

# ログ確認
docker-compose logs -f app
docker-compose logs -f worker

# コンテナ停止
docker-compose down
```

## 環境変数

### 必須設定（`.env`ファイル）

```env
# データベース
DB_URL=sqlite:///./data/scraps.db

# LLM設定（LM Studio）
CHAT_API_BASE=http://localhost:1234/v1
CHAT_MODEL=your-local-chat-model
EMBED_API_BASE=http://localhost:1234/v1
EMBED_MODEL=your-local-embed-model

# タイムアウト設定
TIMEOUT_SEC=30

# パーソナライゼーション設定
PERSONALIZATION_ENABLED=true
PERSONALIZATION_MIN_BOOKMARKS=3
```

### オプション設定

```env
# ログレベル
LOG_LEVEL=INFO

# ワーカー設定
WORKER_POLL_INTERVAL=5
WORKER_MAX_RETRIES=3

# フィードバック設定
FEEDBACK_SCORE_PENALTY=-0.3
```

## ポート設定

| サービス | ポート | 用途 |
|---------|--------|------|
| FastAPI App | 8000 | メインWebアプリケーション |
| LM Studio | 1234 | ローカルLLM（OpenAI互換API） |
| Ollama | 11434 | ローカルLLM（代替） |

## CSS競合問題と対策

### グローバルボタンスタイルの影響

`app/static/css/style.css`に定義されたグローバルなボタンスタイルが、Tailwindクラスだけでは上書きできない問題が存在します。

**影響範囲**: すべての`<button>`要素

**対策**: アイコンのみのボタンを実装する際は、インラインスタイルで`!important`を使用してリセット：

```html
<button
    type="button"
    style="background: none !important; border: none !important; padding: 0 !important; margin: 0 !important; outline: none !important;">
    <i data-lucide="icon-name"></i>
</button>
```

**理由**: グローバルCSSルールがボタンに背景、ボーダー、パディングを強制的に適用しているため。

**今後の改善**: グローバルボタンスタイルをクラスベース（`.btn`等）に変更し、デフォルトボタンへの影響を削減する。

## 依存関係管理

### requirements.txtの構成

```
# Core FastAPI dependencies
fastapi>=0.104.0
uvicorn[standard]>=0.24.0

# Database
sqlalchemy>=2.0.0
alembic>=1.12.0

# Content extraction
trafilatura>=1.6.0
docling>=2.0.0
pdfminer.six>=20221105

# LLM and embeddings
httpx>=0.25.0
openai>=1.0.0

# Background jobs
apscheduler>=3.10.0

# Development dependencies
pytest>=7.0.0
pytest-asyncio>=0.21.0
playwright>=1.40.0
```

### バージョン管理戦略
- **メジャーバージョン固定**: 破壊的変更を避ける（`>=`で最小バージョン指定）
- **定期更新**: 月1回程度、依存関係の更新を確認
- **セキュリティパッチ**: 脆弱性報告があれば即座に更新

## パフォーマンス最適化

### データベース
- **インデックス**: `documents.title`, `documents.created_at`等に作成
- **FTS5**: フルテキスト検索の高速化
- **PRAGMA最適化**: `journal_mode=WAL`, `synchronous=NORMAL`

### 非同期処理
- **バックグラウンドジョブ**: 要約・埋め込み生成は非同期実行
- **DBキュー**: リトライ・エラーハンドリング対応
- **スレッドプール**: 並列処理で高速化

### フロントエンド
- **HTMX**: 部分更新で全ページリロードを回避
- **Lazy loading**: 画像の遅延読み込み（`loading="lazy"`）
- **Tailwind CSS圧縮**: 最小化版を使用

## セキュリティ考慮事項

### プライバシー保護
- **ローカル実行**: LLMはローカルで動作、データは外部送信なし
- **個人データ**: すべてローカルSQLiteに保存

### 入力バリデーション
- **Pydantic**: リクエストデータの型検証
- **SQLAlchemy**: SQLインジェクション対策（パラメータ化クエリ）
- **HTMLエスケープ**: Jinja2のautoescapeでXSS対策

### 認証・認可
- **現状**: 単一ユーザー前提（認証なし）
- **将来**: マルチユーザー対応時に認証機能追加予定

## テスト戦略

### 単体テスト
- **pytest**: 関数・クラス単位のテスト
- **モック**: LLMクライアント等の外部依存をモック化

### 統合テスト
- **データベース**: テスト用SQLiteで実データ操作
- **APIエンドポイント**: FastAPIのTestClientで検証

### E2Eテスト
- **Playwright**: ブラウザ自動化でUI操作テスト
- **日本語対応**: フォント設定（Noto Sans JP）で日本語文字化け対策

## 開発ワークフロー

### 1. 仕様駆動開発（Spec-Driven Development）
- `/kiro:spec-init`: 機能仕様の初期化
- `/kiro:spec-requirements`: 要件定義の生成
- `/kiro:spec-design`: 技術設計の作成
- `/kiro:spec-tasks`: 実装タスクの生成
- `/kiro:spec-impl`: タスクの実装

### 2. Git運用
- **ブランチ戦略**: main（本番）、feature/〇〇（機能開発）
- **コミットメッセージ**: `feat:`, `fix:`, `docs:`等のプレフィックス
- **プルリクエスト**: `gh pr create`でPR作成

### 3. デプロイ
- **ローカル開発**: `uvicorn --reload`でホットリロード
- **本番環境**: Docker Composeで複数サービス管理（app + worker）
- **データバックアップ**: `data/backup/`に定期バックアップ

## トラブルシューティング

### LLM接続エラー
- **確認**: LM Studio/Ollamaが起動しているか
- **エンドポイント**: `.env`の`CHAT_API_BASE`, `EMBED_API_BASE`が正しいか
- **モデル**: LM Studioでモデルがロードされているか

### データベースエラー
- **マイグレーション**: `migrations/apply_migrations.py`で最新スキーマに更新
- **破損**: バックアップから復元（`data/backup/`）
- **ロック**: WALモード（`journal_mode=WAL`）で改善

### ワーカー未起動
- **確認**: `postprocess_jobs`テーブルに`pending`ジョブがあるか
- **ワーカー**: `python -m app.services.postprocess_queue`が起動しているか
- **ログ**: ワーカーログでエラーを確認

### Playwrightテスト失敗
- **フォント**: Noto Sans JPがインストールされているか
- **ブラウザ**: `playwright install`でブラウザをインストール
- **タイムアウト**: `--timeout=30000`でタイムアウトを延長
