# Scrap-Board Development Guide

## アーキテクチャ概要

```
app/
├── main.py                 # FastAPI アプリケーションエントリーポイント
├── core/
│   ├── config.py          # 設定管理
│   └── database.py        # データベースモデルとセッション
├── services/
│   ├── extractor.py       # コンテンツ抽出サービス
│   └── llm_client.py      # LLM クライアント
├── api/routes/
│   ├── documents.py       # ドキュメント管理API
│   ├── ingest.py          # コンテンツ取り込みAPI
│   ├── collections.py     # コレクション管理API
│   └── utils.py           # ユーティリティAPI
├── templates/             # Jinja2 テンプレート
└── static/               # 静的ファイル (CSS, JS)
```

## データベーススキーマ

### Documents テーブル
- 収集したコンテンツの基本情報
- URL, タイトル, 作成者, 本文（Markdown/テキスト）
- 言語検出結果, ハッシュ値（重複検出用）

### Classifications テーブル  
- ドキュメントの分類情報
- プライマリカテゴリ（単一）, タグ（複数）
- 信頼度スコア, 分類手法（rules/knn/llm）

### Embeddings テーブル
- 検索・類似度計算用のベクトル表現
- チャンク単位での埋め込み保存

### Collections テーブル
- ユーザー作成のコレクション管理
- CollectionItems で Document との多対多関係

## API エンドポイント

### コンテンツ取り込み
- `POST /api/ingest/url` - URL からコンテンツ抽出
- `POST /api/ingest/pdf` - PDF ファイルアップロード
- `POST /api/ingest/rss` - RSS フィード登録

### ドキュメント管理
- `GET /api/documents` - 一覧取得（検索・フィルタ対応）
- `GET /api/documents/{id}` - 詳細取得
- `GET /api/documents/{id}/similar` - 類似ドキュメント
- `POST /api/documents/{id}/feedback` - 分類フィードバック

### ユーティリティ
- `GET /api/stats` - 統計情報
- `GET /api/search` - 全文検索
- `POST /api/export` - エクスポート機能

## フロントエンド

### 技術スタック
- **テンプレートエンジン**: Jinja2
- **インタラクション**: ネイティブ JavaScript（モーダル、キーボードショートカット）
- **スタイリング**: カスタム CSS（Tailwind 風ユーティリティクラス）
- **アイコン**: 絵文字（外部依存なし）

### デザインシステム
- **カラーパレット**: Emerald (#2BB673) アクセント
- **タイポグラフィ**: Inter フォント、日本語対応
- **レスポンシブ**: モバイルファースト設計

### キーボードショートカット
- `Ctrl+K` - 検索フォーカス
- `Ctrl+N` - 新規コンテンツ追加
- `Esc` - モーダルクローズ

## 開発ワークフロー

### 1. 開発環境セットアップ
```bash
# 依存関係インストール
pip install -r requirements.txt

# 環境変数設定
cp .env.example .env

# データベース初期化
python -c "from app.core.database import create_tables; create_tables()"

# 開発サーバー起動
uvicorn app.main:app --reload
```

### 2. テスト実行
```bash
# 基本テスト
pytest tests/test_basic.py -v

# 全テスト実行
pytest tests/ -v
```

### 3. 新機能追加の流れ

#### API エンドポイント追加
1. `app/api/routes/` に新しいルーターファイル作成
2. `app/main.py` でルーター登録
3. テストファイル作成（`tests/`）

#### フロントエンド追加
1. `app/templates/` にテンプレート作成
2. 必要に応じて `app/static/css/style.css` 更新
3. `app/main.py` でルート追加

#### データベーステーブル追加
1. `app/core/database.py` でモデル定義
2. マイグレーション実行（将来的にAlembic使用）

## LLM 統合

### 設定
```env
# LM Studio (推奨)
CHAT_API_BASE=http://localhost:1234/v1
EMBED_API_BASE=http://localhost:1234/v1

# Ollama (代替)
CHAT_API_BASE=http://localhost:11434/v1
EMBED_API_BASE=http://localhost:11434/v1
```

### 使用箇所
- `app/services/llm_client.py` - 基本クライアント
- `app/api/routes/ingest.py` - 取り込み時の分類・要約
- `app/api/routes/documents.py` - 要約生成

## パフォーマンス最適化

### データベース
- インデックス: `url`, `domain`, `created_at`, `hash`
- 全文検索: SQLite FTS拡張（将来的に）

### コンテンツ処理
- 非同期処理: 取り込み時のバックグラウンドタスク
- キャッシュ: 分類結果、埋め込みベクトル

## セキュリティ

### 入力検証
- URL検証: スキーム、ドメインチェック
- ファイル検証: MIME タイプ、サイズ制限
- XSS対策: テンプレートエスケープ

### レート制限
- API エンドポイント: 将来的に実装
- 外部サイトアクセス: robots.txt 遵守

## デプロイメント

### Docker
```bash
# ビルド
docker build -t scrap-board .

# 実行
docker-compose up -d
```

### 環境変数
- `DB_URL` - データベース接続先
- `CHAT_API_BASE` - LLM API エンドポイント
- `SECRET_KEY` - セッション暗号化キー

### ヘルスチェック
- `GET /health` - アプリケーション状態確認
- データベース接続確認
- 外部サービス依存関係チェック

## テスト

### 単体テスト
```bash
# API とサービステストの実行
pytest tests/test_basic.py -v -m unit
```

### ブラウザテスト（日本語対応）
```bash
# Playwright のインストール
pip install playwright pytest-playwright
playwright install chromium

# 日本語フォントサポートのインストール（Ubuntu/Debian）
sudo apt-get update
sudo apt-get install -y fonts-noto-cjk fonts-liberation

# ブラウザテストの実行
pytest tests/test_browser.py -v -m browser

# すべてのテストを実行
pytest -v
```

### テスト設定
- **Playwright設定**: 日本語ロケール（ja-JP）、UTF-8エンコーディング対応
- **フォントレンダリング**: 日本語文字の適切な表示を保証
- **ブラウザ引数**: `--lang=ja-JP`, `--accept-lang=ja,ja-JP,en` で日本語優先設定
- **文字化け防止**: UTF-8エンコーディングとフォントヒンティング最適化

### テストカバレッジ
- 日本語テキストの適切なレンダリング
- フォーム入力での日本語文字サポート
- 検索機能での日本語クエリ処理
- カテゴリ名など UI 要素の日本語表示
- Reader Mode での日本語フォント最適化

## 再スケジューリング

ポストプロセス（要約・分類・埋め込み）を再実行したい既存ドキュメントを再キュー化するスクリプトがあります。

例:
```bash
# 影響対象を確認 (dry-run)
env PYTHONPATH=. python scripts/reschedule_postprocess.py --dry-run --limit 20

# 実際に再キュー化する
env PYTHONPATH=. python scripts/reschedule_postprocess.py --limit 100
```

オプション:
- `--only-summaries`: 要約が空のドキュメントのみ対象
- `--only-classifications`: 分類がないドキュメントのみ対象

ドライランの説明:
- `--dry-run` を指定すると、実際に `postprocess_jobs` テーブルへ行を作成せず、対象となるドキュメント数とサンプルIDを表示します。
- 安全確認用に使い、まず影響範囲を確認してから実際の再キュー化を行ってください。
- 実行時はアプリのモジュールを読み込めるように `PYTHONPATH=.` を付けるか、仮想環境を有効化した上で実行してください。

