# Scrap-Board 要件定義書（フル版 v3）

> 目的：WebページやPDF資料を収集（スクラップ）→ 正規化 → **自動分類** → **読みやすい表示（Reader Mode）** → 検索／要約 → 共有までを、**個人利用**に最適化した最小構成で実現する。LLMは**別サーバーの LM Studio（既定）** または **Ollama** を用いる。

## 1. スコープ
- **対象**：公開Web記事、ブログ、ニュース、技術ドキュメント、**PDF**（必須対応）、RSS/Atom
- **非対象（初期）**：要ログイン／有償会員限定、強JS依存SPAの動的描画、動画音声の文字起こし、SNSの非公式API取得
- **成果物**：
  - 収集・抽出パイプライン（HTML／PDF）
  - 正規化データ保存（本文MD、メタ、埋め込み）
  - 自動分類器（カテゴリ／タグ／トピック）
  - 検索（全文＋類似）と要約表示
  - Reader Mode（可読性重視の本文ビュー）
  - エクスポート（Markdown/JSONL/CSV）

## 2. ゴール／非ゴール
- **ゴール**：個人が日々のスクラップを**手間なく集め、読み、見つけ直せる**状態にする
- **非ゴール**：高トラフィック対応、複雑なダッシュボード、外部通知連携（Slack/メール）、多人数同時編集

## 3. ペルソナ
- **個人キュレーター**：技術ニュースを収集し、自分用ナレッジに整理する
- **個人研究者**：テーマ別に記事を集約し、後で読み返す・引用する

## 4. ユースケース
1. URL/PDFを投入 → 抽出 → 自動分類 → 要約生成 → コレクションへ保存
2. RSS登録 → 定期クロール → 新着のみ取り込み → 要約／分類 → 一覧に表示
3. 検索（キーワード＋類似）→ ファセットで期間／ドメイン／カテゴリを絞り込み
4. Reader Modeで本文を**快適に読了**→ 重要箇所の引用を保存
5. エクスポート（MD/CSV）でブログ下書きや社内ノートへ再利用

## 5. 機能要件

### 5.1 収集・抽出
- 入力：単一URL、複数URL（CSV/貼り付け）、RSS/Atom、PDFアップロード
- HTML抽出：Trafilatura／Readability系。タイトル、本文、著者、公開日、OGP、主要画像
- **PDF抽出（必須）**：Docling で段落テキスト・表をMarkdown化（図はプレースホルダ保持）。失敗時は pdfminer.six にフォールバック
- ロボッツ：robots.txt尊重。ETag/Last-Modified で差分取得

### 5.2 正規化
- HTML→Markdown、言語判定、改行・箇条書き・表の整形、余分なナビ／広告要素の除去

### 5.3 自動分類
- 一次カテゴリ（単一必須）：テック/AI、ソフトウェア開発、ビジネス、セキュリティ、研究、プロダクト、法規制、データサイエンス、クラウド/インフラ、デザイン/UX、教育、ライフ、その他
- 二次トピック／タグ（複数任意）
- 方式：規則＋辞書 → 近傍（埋め込みkNN）→ LLM 0-shot の優先順で確定。`confidence` を保持

### 5.4 要約・ハイライト
- 要約（短／中）、重要引用（原文スニペット）とキーフレーズ抽出
- 読了予測時間（日本語 300wpm 目安）を計算し表示

### 5.5 検索／閲覧
- ハイブリッド検索：全文（軽量索引）＋ 類似（cosine）
- ファセット：期間、ドメイン、カテゴリ、言語、タグ
- 類似記事の提示、出典リンク、Reader Mode へのワンクリック遷移

### 5.6 共有／連携
- エクスポート：Markdown/CSV/JSONL。将来：Notion/Obsidian 連携（OUT OF SCOPE）

### 5.7 管理
- カテゴリ定義、辞書更新、NG／Allow ドメイン、RSSスケジュールの編集

## 6. 非機能要件
- パフォーマンス：単記事の取込〜要約表示 P50 < 8秒（ローカル環境／既定モデル）
- 可用性：個人利用の想定。アプリのクラッシュ耐性（再起動で復旧）
- セキュリティ：ローカル利用前提。外部送信は**LLM/Embedding先のみ**
- 監査性：操作ログ（取込、分類、要約）、モデル名／プロンプトバージョン
- バックアップ：SQLiteファイル＋`/assets`（抽出画像）

## 7. アーキテクチャ（個人向け・コンパクト）

### 7.1 Personal-MVP（**1コンテナ + 外部LLM**／既定）
- **app**：FastAPIモノリス（UI=Jinja+HTMX、API、APScheduler）
- **DB**：SQLite（ファイル1本）
- **埋め込み/LLM**：**別サーバ**の **LM Studio（既定）** または **Ollama**（OpenAI互換）
- **抽出**：Trafilatura（HTML）＋ **Docling（PDF必須）**／pdfminer.six フォールバック
- **検索**：全文（SQLite簡易索引）＋ 類似（メモリ内 cosine, NumPy）

## 8. データモデル
- `documents`: id(uuid), url(unique), domain, title, author, published_at, fetched_at, lang, content_md, content_text, hash, created_at, updated_at
- `classifications`: id, document_id, primary_category, topics(jsonb), tags(text[]), confidence(real), method(prompt|rules|knn)
- `embeddings`: id, document_id, chunk_id, vec(blob/array), chunk_text
- `collections`: id, name, description
- `collection_items`: id, collection_id, document_id, note
- `feedbacks`: id, document_id, label(correct|incorrect), comment, created_at

## 9. 分類設計
- **カテゴリ（単一）**：テック/AI、ソフトウェア開発、ビジネス、セキュリティ、研究、プロダクト、法規制、データサイエンス、クラウド/インフラ、デザイン/UX、教育、ライフ、その他
- **タグ**：自由語＋管理タグ（例：RAG、Qdrant、Docling、Copilot、Node-RED、保険）
- **ルール例**：`title contains "CVE|脆弱性" → セキュリティ`、`domain=openai.com → テック/AI`
- **判定順**：Rules → kNN → LLM。閾値により早期確定。`confidence` 付与

## 10. UI要件（主要画面・デザイン指針）

### 10.1 デザインコンセプト
- スタイリッシュ／おしゃれ／**大人向き**／落ち着き／余白の美学／可読性
- 強いアクセントは要所のみ。タイポと余白でリッチ感を出す

### 10.2 カラーパレット（WCAG AA）
- Base：Ink #0B1221 / Charcoal #1C2430 / Graphite #2E3642 / Mist #E8ECF2 / Ivory #F9FAFB
- Accent：**Emerald #2BB673** *or* **Indigo #5A6FF0**（どちらかを製品決定）
- Dark：背景 #0E1116、カード #141A22、テキスト #E6EAF0

### 10.3 タイポグラフィ
- 英字：Inter / IBM Plex Sans、 日本語：Noto Sans JP（400/500/700）
- スケール：12/14/16/18/20/24/28/32px（Body16、H1 32、H2 24、H3 20、行間1.6）

### 10.4 Reader Mode（**可読性最優先**）
- 本文：行幅28–38em、行間1.8、段落間+0.4、サイズ16/18/20px切替（保存）
- フォント：Sans標準／**Serif切替可（Noto Serif JP）**
- 配色：ライト／ダーク／セピア。コントラストAA+
- ショートカット：`A+/A-` 文字サイズ、`R` Reader切替、`F` フォーカス

## 11. API設計（抜粋）
- `POST /ingest/url` { url, force? }
- `POST /ingest/rss` { feed_url, schedule? }
- `POST /ingest/pdf` multipart { file }
- `GET /documents` ?q=&category=&tags=&from=&to=&domain=
- `GET /documents/{id}`
- `POST /documents/{id}/feedback` { label, comment }
- `POST /classify/test` { text }
- `POST /export` { format: md|csv|jsonl, filter }

## 12. 受け入れ基準
- URL/PDF投入後、平均8秒以内に「本文・要約・カテゴリ」を表示
- 検索でカテゴリ・期間・ドメインのAND絞り込みが有効
- Reader Modeで3種の文字サイズ切替、ライト/ダーク/セピア切替が保存される
- 同一URLの二重登録防止（hash/unique）

## 13. 環境変数設定例

```env
DB_URL=sqlite:///./data/scraps.db
CHAT_API_BASE=http://localhost:1234/v1
CHAT_MODEL=gpt-4o-mini-compat-or-your-local
EMBED_API_BASE=http://localhost:1234/v1
EMBED_MODEL=text-embedding-3-large-or-nomic-embed-text
TIMEOUT_SEC=30
```