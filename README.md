# Scrap-Board - ウェブコンテンツ収集・管理システム

Webページ・PDF資料の収集、自動分類、読みやすい表示、検索・要約機能を備えた個人向けコンテンツ管理システム

## 概要


Scrap-BoardはWebコンテンツとPDFの収集、処理、管理を行う日本語ウェブアプリケーションです。自動コンテンツ分類、検索機能、最適なコンテンツ消費のためのリーダーモードを備えています。

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

## ライセンス

MIT License