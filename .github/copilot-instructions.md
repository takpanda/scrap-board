# Scrap-Board - ウェブコンテンツ収集・管理システム

まずこの指示書を参照し、ここに記載されていない予期しない情報に遭遇した場合のみ検索やbashコマンドを使用してください。
issue、ドキュメントは日本語を使用してください。

## プロジェクト概要
Scrap-Boardは、ウェブコンテンツとPDFの収集、処理、管理を行う日本語ウェブアプリケーションです。自動コンテンツ分類、検索機能、最適なコンテンツ消費のためのリーダーモードを備えています。システムはHTMXフロントエンドを持つFastAPI、SQLiteデータベースを使用し、LLM機能のためにLM StudioまたはOllamaと統合されています。

**現在の状況**: 開発初期段階 - リポジトリには基本的なREADME.mdのみが含まれています。issue #1の詳細要件に基づく完全な実装が計画されています。

## 技術スタック・アーキテクチャ
- **バックエンド**: Python 3.11+ with FastAPI
- **フロントエンド**: HTMX + Jinja2テンプレート with Tailwind CSS
- **データベース**: SQLite (開発/個人使用)
- **LLM統合**: LM Studio (デフォルト) または OpenAI互換API経由のOllama
- **PDF処理**: Docling (プライマリ) with pdfminer.six フォールバック
- **コンテンツ抽出**: HTMLのTrafilatura
- **デプロイメント**: 単一コンテナアーキテクチャのDocker
- **言語**: 全てのユーザー向けコンテンツ、記事、チャット機能で日本語サポートが必要

## 検証済みコマンド・タイミング

以下のコマンドはテスト済みで正常に動作することが確認されています：

### 環境検証 (テスト済み)
- **Python**: 3.12.3 利用可能 (3.11+要件と互換性あり)
- **Docker**: 28.0.4 コンテナ化で利用可能
- **Git**: 2.51.0 バージョン管理で利用可能
- **Curl**: 8.5.0 APIテストで利用可能

### パッケージインストール時間 (測定済み)
- **FastAPIコアパッケージ**: ~10秒 (fastapi, uvicorn, httpx)
- **コンテンツ抽出パッケージ**: ~7秒 (trafilatura with dependencies)
- **完全な依存関係セット**: MLパッケージ込みで推定15-20分
- **FastAPI起動**: 基本アプリケーションで~2-3秒

### テスト済みコマンド
```bash
# 基本依存関係インストール (検証済み)
pip install fastapi uvicorn[standard] httpx trafilatura

# FastAPIテストサーバー起動 (検証済み)
uvicorn app:app --host 0.0.0.0 --port 8000
# 予想起動時間: 2-3秒

# LLMサービス接続テスト (検証済みコマンド)
curl http://localhost:1234/v1/models  # LM Studio
curl http://localhost:11434/api/tags  # Ollama

# ファイル操作 (検証済み)
mkdir -p data && ls -la data
```

## 効果的な作業方法

### 初期リポジトリセットアップ
現在リポジトリには以下が含まれています：
```
.
├── README.md
├── .github/
│   └── copilot-instructions.md
├── .gitignore
└── .git/
```

### 予想開発環境セットアップ
開発開始時は、以下のコマンドを使用してください：

1. **Python依存関係のインストール**:
   ```bash
   pip install fastapi uvicorn[standard] httpx sqlalchemy trafilatura docling pdfminer.six numpy pandas jinja2
   # 絶対にキャンセルしないこと: コア依存関係は~10-20秒、MLパッケージ全体で5-10分かかる場合があります
   # 完全インストールには15分以上のタイムアウトを設定してください
   ```

2. **外部LLMサービスのセットアップ** (どちらか一つを選択):
   
   **LM Studio (推奨)**:
   ```bash
   # LM Studioを別途ダウンロードして実行
   # APIエンドポイント設定: http://localhost:1234/v1
   # チャットと埋め込み用の互換モデルをロード
   ```
   
   **Ollama代替案**:
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ollama pull llama3.1:8b-instruct
   ollama pull nomic-embed-text
   ollama serve  # http://localhost:11434で実行
   ```

3. **環境設定**:
   ```bash
   # .envファイルを作成:
   DB_URL=sqlite:///./data/scraps.db
   CHAT_API_BASE=http://localhost:1234/v1
   CHAT_MODEL=your-local-chat-model
   EMBED_API_BASE=http://localhost:1234/v1  
   EMBED_MODEL=your-local-embed-model
   TIMEOUT_SEC=30
   # LLMモデルがチャットとコンテンツ処理で日本語をサポートすることを確認
   ```

4. **開発サーバーの実行**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   # 絶対にキャンセルしないこと: 初期起動時はモデルロードに2-3分かかる場合があります
   ```

### Docker開発 (計画中)
```bash
# コンテナビルド
docker build -t scrap-board .
# 絶対にキャンセルしないこと: ML依存関係により10-15分かかります

# docker-composeで実行
docker-compose up -d
# 絶対にキャンセルしないこと: 初回実行時はデータベース初期化とモデルロードに5-8分かかります
```

## テスト・検証

### 手動検証シナリオ
変更後は、必ずこれらのコアワークフローをテストしてください：

1. **コンテンツ取り込みテスト**:
   ```bash
   curl -X POST http://localhost:8000/ingest/url \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com/article"}'
   # 期待値: 8秒以内にドキュメントIDを含む200レスポンス
   ```

2. **PDF処理テスト**:
   ```bash
   curl -X POST http://localhost:8000/ingest/pdf \
     -F "file=@sample.pdf"
   # 期待値: Markdownフォーマットでの抽出成功
   ```

3. **検索機能テスト**:
   ```bash
   curl "http://localhost:8000/documents?q=test&category=テック/AI"
   # 期待値: フィルタリングされた結果のJSONレスポンス
   ```

4. **Web UIテスト**:
   - http://localhost:8000にナビゲート
   - URL入力とコンテンツ取り込みテスト
   - リーダーモード切り替えとテキストサイズコントロールの確認
   - 日本語キーワードでの検索テスト
   - カテゴリフィルタリング動作確認

### ビルド・テストコマンド
```bash
# テスト実行 (テストスイートが存在する場合)
pytest tests/ -v
# 絶対にキャンセルしないこと: MLモデルロードによりテストスイートは10-15分かかる場合があります

# コード品質チェック
black app/ --check
flake8 app/
mypy app/
# 絶対にキャンセルしないこと: mypyの初回実行は3-5分かかる場合があります
```

## 主要機能・コンポーネント

### コンテンツ処理パイプライン
1. **入力受け入れ**: URL、RSSフィード、PDFアップロード
2. **コンテンツ抽出**: HTML (Trafilatura) + PDF (Docling)
3. **正規化**: Markdownへの変換、言語検出
4. **埋め込み生成**: LM Studio/Ollama API経由
5. **分類**: ルール → kNN → LLM投票システム
6. **要約**: LLM経由の短/中要約
7. **保存**: 全文検索インデックス付きSQLite

### データベーススキーマ (計画中)
- `documents`: コアコンテンツ保存
- `classifications`: カテゴリ/タグ割り当て
- `embeddings`: 類似検索用ベクトル表現
- `collections`: ユーザー組織化コンテンツグループ
- `feedbacks`: 分類改善用修正データ

### UIコンポーネント・スタイリング
- **デザイン**: モダンでミニマルな日本語UI
- **カラー**: Ink/Charcoalベース with Emerald or Indigo アクセント
- **タイポグラフィ**: Inter + Noto Sans JP
- **レイアウト**: 固定ヘッダー (64px)、折りたたみ可能サイドバー (264px)
- **リーダーモード**: 複数テーマ付き最適化タイポグラフィ

## 共通開発タスク

### 新規分類ルール追加
```python
# app/core/classification.pyを編集
rules = [
    {
        "name": "ai-content",
        "if_title": ["AI", "機械学習", "LLM"],
        "then_category": "テック/AI"
    }
]
```

### コンテンツ抽出更新
```python
# app/services/extractor.pyを変更
# 常にHTMLとPDFサンプル両方でテスト
# 日本語テキスト処理が正しく動作することを確認
```

### データベースマイグレーション
```bash
# Alembicマイグレーション実行 (実装時)
alembic upgrade head
# 絶対にキャンセルしないこと: 大きなデータセットではマイグレーションに5-10分かかる場合があります
```

## パフォーマンス・タイミング期待値

### レスポンス時間目標
- **単一URL取り込み**: P50 < 8秒 (LLM処理含む)
- **検索クエリ**: P95 < 300ms (インデックス化データ)
- **PDF処理**: サイズにより異なる、50ページドキュメントで30秒
- **バルク取り込み**: 100 URLで45-60分かかる場合があります

### リソース要件
- **メモリ**: 最小4GB (大きなモデルには8GB推奨)
- **ストレージ**: SQLite + アセットディレクトリ
- **CPU**: モデル推論はCPU集約的、処理中は高使用率が予想されます

## トラブルシューティング・よくある問題

### LLM接続問題
```bash
# LM Studio接続テスト
curl http://localhost:1234/v1/models
# 利用可能モデルリストが返されるはずです

# Ollama接続テスト
curl http://localhost:11434/api/tags
# インストール済みモデルが返されるはずです
```

### PDF処理失敗
- Doclingプライマリ抽出、pdfminer.sixフォールバック
- 画像のみPDFは警告とともにスキップされます
- 詳細なエラーメッセージはログを確認してください

### 分類精度
- UIでフィードバック収集をモニター
- 設定でルール閾値を調整
- 蓄積されたフィードバックでkNN分類器を再訓練

## セキュリティ・コンプライアンス
- **robots.txt遵守**: クローリング中は常に尊重
- **レート制限**: ターゲットサイトの過負荷防止のため実装
- **データプライバシー**: 設定されたLLMエンドポイント以外への外部データ送信なし
- **ドメインフィルタリング**: コンテンツソースの許可/ブロックリスト維持

## ファイル構造 (予想)
```
app/
├── main.py                 # FastAPIアプリケーションエントリー
├── core/
│   ├── config.py          # 環境設定
│   ├── database.py        # SQLite接続
│   └── classification.py  # ML分類ロジック
├── services/
│   ├── extractor.py       # コンテンツ抽出
│   ├── llm_client.py      # LM Studio/Ollama統合
│   └── search.py          # 検索機能
├── api/
│   └── routes/            # APIエンドポイント
├── templates/             # Jinja2 HTMLテンプレート
└── static/               # CSS、JS、画像
tests/                    # テストスイート
data/                     # SQLiteデータベース保存
docker-compose.yml        # コンテナオーケストレーション
requirements.txt          # Python依存関係
.env                      # 環境変数
```

## 開発ガイドライン

### 言語使用要件
- **UIテキスト**: すべてのユーザーインターフェーステキストは日本語である必要があります
- **記事・コンテンツ**: 処理されたすべての記事とコンテンツは日本語で表示されるべきです
- **チャット機能**: LLMチャット相互作用と応答は日本語である必要があります
- **ユーザーコミュニケーション**: すべてのユーザー向けメッセージ、通知、フィードバックは日本語であるべきです
- **コードコメント**: 内部コードコメントは開発者の明確性のため英語であるべきです
- **APIドキュメント**: 技術ドキュメントは英語でも構いません

### その他のガイドライン
- **エラーハンドリング**: LLMサービス利用不可時の優雅な機能低下
- **ロギング**: デバッグ用の包括的操作ログ
- **テスト**: コンテンツ処理パイプラインの信頼性に焦点
- **ドキュメント**: コード進化に合わせてAPIドキュメントを維持

## 外部依存関係
- **LM Studio**: プライマリLLMサービス (推奨)
- **Ollama**: 代替LLMサービス
- **インターネット接続**: コンテンツクローリングに必要
- **ストレージ**: SQLiteと抽出アセット用のローカルファイルシステム

アプリケーション開始前に外部LLMサービスが実行されていることを常に確認してください。システムは埋め込みとチャット完了APIへのアクセスなしには機能できません。
