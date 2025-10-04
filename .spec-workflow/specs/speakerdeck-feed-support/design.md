# Design: SpeakerDeck Feed Support

## 概要
SpeakerDeckのRSS/Atomフィードからプレゼンテーションを自動取得し、PDFを永続保存して記事カードからダウンロード可能にする機能の技術設計です。既存のフィード取得メカニズムとingestionパイプラインを拡張し、新しいPDF管理機能を追加します。

## アーキテクチャ

### 全体フロー
```
┌─────────────────────┐
│  Scheduler (cron)   │
└──────────┬──────────┘
           │
           v
┌─────────────────────┐
│ trigger_fetch_for_  │
│   source()          │
└──────────┬──────────┘
           │
           v
┌─────────────────────┐
│ _fetch_speakerdeck_ │
│   items()           │ ← feedparser (RSS/Atom)
└──────────┬──────────┘
           │
           v (各エントリ)
┌─────────────────────┐
│ _insert_document_   │
│   from_url()        │
└──────────┬──────────┘
           │
           ├─→ extractor.extract_from_url()
           │
           ├─→ [SpeakerDeck検出]
           │      │
           │      v
           │   ┌─────────────────────┐
           │   │ SpeakerDeckHandler  │
           │   │ - get_pdf_url()     │
           │   │ - download_pdf()    │
           │   └─────────────────────┘
           │      │
           │      v
           │   data/assets/pdfs/speakerdeck/{doc_id}.pdf
           │
           v
    ┌──────────────┐
    │ DB: documents│
    │ + pdf_path   │
    └──────────────┘
           │
           v
    ┌──────────────┐
    │ UI: Card     │
    │ + DL button  │
    └──────────────┘
```

## コンポーネント設計

### 1. データベーススキーマ拡張

#### マイグレーション: `007_add_pdf_support.sql`
```sql
-- Add pdf_path column to documents table
ALTER TABLE documents ADD COLUMN pdf_path TEXT;

-- Create index for faster PDF queries
CREATE INDEX IF NOT EXISTS idx_documents_pdf_path ON documents(pdf_path) WHERE pdf_path IS NOT NULL;
```

**理由**: 
- `pdf_path`: ローカルに保存されたPDFファイルへの相対パス（例: `assets/pdfs/speakerdeck/abc123.pdf`）
- NULL許可により既存ドキュメントへの後方互換性を維持
- 部分インデックスでPDFを持つドキュメントの検索を高速化

### 2. SpeakerDeckフィード取得

#### `app/services/ingest_worker.py` に追加

```python
def _fetch_speakerdeck_items(config: Dict[str, Any]):
    """Fetch items from SpeakerDeck RSS/Atom feed.
    
    Config keys:
    - `username`: SpeakerDeck username (generates .rss URL)
    - `url`: Direct feed URL (.rss or .atom)
    - `per_page`: Max items to fetch (default: 20)
    - `format`: 'rss' or 'atom' (default: 'rss')
    
    Returns:
        List of dicts with keys: link, title, published, summary
    """
    items = []
    per_page = config.get("per_page", 20)
    
    try:
        import feedparser
        
        # Generate feed URL from username or use direct URL
        if config.get("username"):
            feed_format = config.get("format", "rss")
            username = config["username"]
            url = f"https://speakerdeck.com/{username}.{feed_format}"
        elif config.get("url"):
            url = config["url"]
        else:
            logger.warning("SpeakerDeck source missing username or url")
            return items
        
        logger.info(f"Fetching SpeakerDeck feed: {url}")
        parsed = feedparser.parse(url)
        
        for e in parsed.entries[:per_page]:
            items.append({
                "link": e.get("link"),
                "title": e.get("title"),
                "published": e.get("published"),
                "summary": e.get("summary", ""),
            })
        
        logger.info(f"Fetched {len(items)} items from SpeakerDeck")
    
    except ModuleNotFoundError:
        logger.warning("feedparser not installed; SpeakerDeck RSS fetch skipped")
    except Exception as e:
        logger.error(f"SpeakerDeck fetch error: {e}")
    
    return items
```

#### `trigger_fetch_for_source()` への統合

既存の関数に `speakerdeck` タイプのハンドリングを追加：

```python
def trigger_fetch_for_source(source_id: int):
    # ... 既存コード ...
    
    if source_type == "qiita":
        items = _fetch_qiita_items(config)
    elif source_type == "hatena":
        items = _fetch_hatena_items(config)
    elif source_type == "rss":
        items = _fetch_rss_items(config)
    elif source_type == "speakerdeck":  # 追加
        items = _fetch_speakerdeck_items(config)
    else:
        logger.warning(f"Unknown source type: {source_type}")
        return
    
    # ... 残りの処理 ...
```

**設計判断**:
- 既存の `_fetch_*_items()` パターンに従う
- `feedparser` ライブラリを利用（既存のRSS/Hatena取得と同じ）
- RSS（`.rss`）とAtom（`.atom`）の両方に対応
- エラーハンドリングで他のソースに影響を与えない

### 3. SpeakerDeck PDF取得ハンドラー

#### 新規ファイル: `app/services/speakerdeck_handler.py`

```python
"""SpeakerDeck specific handlers for PDF download and metadata."""
import logging
import httpx
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse, quote
import hashlib
import uuid

logger = logging.getLogger(__name__)

class SpeakerDeckHandler:
    """Handle SpeakerDeck-specific operations."""
    
    OEMBED_API = "https://speakerdeck.com/oembed.json"
    TIMEOUT = 30.0
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    
    @staticmethod
    def is_speakerdeck_url(url: str) -> bool:
        """Check if URL is from SpeakerDeck."""
        if not url:
            return False
        parsed = urlparse(url)
        return parsed.netloc in ("speakerdeck.com", "www.speakerdeck.com")
    
    @staticmethod
    def get_pdf_url(presentation_url: str) -> Optional[str]:
        """Get PDF download URL from SpeakerDeck presentation URL.
        
        Uses oEmbed API: https://speakerdeck.com/oembed.json?url=<presentation_url>
        
        Returns:
            PDF download URL or None if not found/error
        """
        if not SpeakerDeckHandler.is_speakerdeck_url(presentation_url):
            return None
        
        try:
            with httpx.Client(timeout=SpeakerDeckHandler.TIMEOUT) as client:
                params = {"url": presentation_url}
                response = client.get(SpeakerDeckHandler.OEMBED_API, params=params)
                response.raise_for_status()
                data = response.json()
                
                # oEmbed response may not include direct PDF link
                # Extract from HTML or use alternative approach
                # SpeakerDeck PDFs are typically at: 
                # https://speakerd.s3.amazonaws.com/presentations/<id>/<slug>.pdf
                
                # Try to extract from HTML or metadata
                # For now, log and return None if not directly available
                # This may require scraping the presentation page
                
                logger.debug(f"oEmbed response: {data}")
                
                # Alternative: scrape presentation page
                return SpeakerDeckHandler._extract_pdf_from_page(presentation_url, client)
        
        except Exception as e:
            logger.error(f"Failed to get PDF URL for {presentation_url}: {e}")
            return None
    
    @staticmethod
    def _extract_pdf_from_page(presentation_url: str, client: httpx.Client) -> Optional[str]:
        """Extract PDF URL by scraping the presentation page.
        
        SpeakerDeck embeds PDF link in meta tags or download button.
        """
        try:
            response = client.get(presentation_url)
            response.raise_for_status()
            html = response.text
            
            # Look for PDF link patterns
            import re
            
            # Pattern 1: Direct PDF link in meta tags
            match = re.search(r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+\.pdf)["\']', html, re.I)
            if match:
                return match.group(1)
            
            # Pattern 2: Download button or link
            match = re.search(r'href=["\']([^"\']*speakerd\.s3\.amazonaws\.com[^"\']*\.pdf)["\']', html, re.I)
            if match:
                return match.group(1)
            
            # Pattern 3: JSON-LD or data attributes
            match = re.search(r'data-pdf-url=["\']([^"\']+)["\']', html, re.I)
            if match:
                return match.group(1)
            
            logger.warning(f"Could not extract PDF URL from {presentation_url}")
            return None
        
        except Exception as e:
            logger.error(f"Failed to scrape PDF URL from {presentation_url}: {e}")
            return None
    
    @staticmethod
    def download_pdf(pdf_url: str, document_id: str) -> Optional[str]:
        """Download PDF and save to local storage.
        
        Args:
            pdf_url: URL of the PDF file
            document_id: Document UUID for filename
        
        Returns:
            Relative path to saved PDF or None if failed
        """
        if not pdf_url:
            return None
        
        # Create directory
        pdf_dir = Path("data/assets/pdfs/speakerdeck")
        pdf_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        filename = f"{document_id}.pdf"
        file_path = pdf_dir / filename
        relative_path = f"assets/pdfs/speakerdeck/{filename}"
        
        try:
            with httpx.Client(timeout=SpeakerDeckHandler.TIMEOUT) as client:
                # Stream download to handle large files
                with client.stream("GET", pdf_url) as response:
                    response.raise_for_status()
                    
                    # Check content type
                    content_type = response.headers.get("content-type", "")
                    if "pdf" not in content_type.lower():
                        logger.warning(f"Unexpected content-type for PDF: {content_type}")
                    
                    # Check file size
                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > SpeakerDeckHandler.MAX_FILE_SIZE:
                        logger.error(f"PDF file too large: {content_length} bytes")
                        return None
                    
                    # Save to file
                    with open(file_path, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)
                
                logger.info(f"Downloaded PDF: {relative_path}")
                return relative_path
        
        except Exception as e:
            logger.error(f"Failed to download PDF from {pdf_url}: {e}")
            # Clean up partial file
            if file_path.exists():
                file_path.unlink()
            return None
```

**設計判断**:
- クラスベースの設計で関連機能をカプセル化
- oEmbed APIを第一の手段として利用
- フォールバックとして HTML スクレイピング（SpeakerDeckのHTML構造に依存）
- ストリーミングダウンロードで大容量PDFに対応
- ファイルサイズ制限とタイムアウトでリソース保護
- エラー時の部分ファイルクリーンアップ

### 4. Ingestionパイプラインの拡張

#### `app/services/ingest_worker.py` の `_insert_document_from_url()` を拡張

既存の関数に SpeakerDeck PDF 処理を統合：

```python
def _insert_document_from_url(db, url: str, source_name: str = "manual"):
    """Extract content from URL and insert into database.
    
    ... 既存docstring ...
    """
    # ... 既存のextraction処理 ...
    
    # Insert document
    doc_id = _insert_document_if_new(db, doc, source_name)
    
    if doc_id:
        # SpeakerDeck PDF handling (新規追加)
        if SpeakerDeckHandler.is_speakerdeck_url(url):
            try:
                logger.info(f"Detected SpeakerDeck URL, attempting PDF download: {url}")
                pdf_url = SpeakerDeckHandler.get_pdf_url(url)
                
                if pdf_url:
                    pdf_path = SpeakerDeckHandler.download_pdf(pdf_url, doc_id)
                    
                    if pdf_path:
                        # Update document with pdf_path
                        db.execute(
                            text("UPDATE documents SET pdf_path = :pdf_path WHERE id = :id"),
                            {"pdf_path": pdf_path, "id": doc_id}
                        )
                        db.commit()
                        logger.info(f"Saved PDF for document {doc_id}: {pdf_path}")
                    else:
                        logger.warning(f"Failed to download PDF for {url}")
                else:
                    logger.warning(f"Could not extract PDF URL from {url}")
            
            except Exception as e:
                logger.error(f"SpeakerDeck PDF processing failed for {url}: {e}")
                # Don't fail document insertion on PDF error
        
        # ... 既存のpostprocess処理 ...
    
    return doc_id
```

**設計判断**:
- PDF取得はドキュメント挿入後の追加処理（失敗してもドキュメントは保存される）
- トランザクション管理: PDF path の更新は別のUPDATE文で実行
- 非同期処理は避け、同期的にPDFをダウンロード（将来的な最適化候補）
- エラーログは残すが、処理は継続

### 5. PDFダウンロードAPIエンドポイント

#### 新規ファイル: `app/api/routes/documents.py` に追加

```python
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy import text
from pathlib import Path
from app.core.database import get_db

router = APIRouter(prefix="/api/documents", tags=["documents"])

@router.get("/{document_id}/pdf")
async def download_pdf(document_id: str, db=Depends(get_db)):
    """Download PDF file for a document.
    
    Args:
        document_id: Document UUID
    
    Returns:
        PDF file as FileResponse
    
    Raises:
        404: Document not found or PDF not available
        500: File system error
    """
    # Get document from database
    result = db.execute(
        text("SELECT id, title, pdf_path FROM documents WHERE id = :id"),
        {"id": document_id}
    ).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = dict(result._mapping)
    pdf_path = doc.get("pdf_path")
    
    if not pdf_path:
        raise HTTPException(status_code=404, detail="PDF not available for this document")
    
    # Construct full file path
    full_path = Path("data") / pdf_path
    
    # Security: validate path is within data directory
    try:
        full_path = full_path.resolve()
        data_dir = Path("data").resolve()
        if not str(full_path).startswith(str(data_dir)):
            raise HTTPException(status_code=403, detail="Invalid file path")
    except Exception:
        raise HTTPException(status_code=403, detail="Invalid file path")
    
    # Check file exists
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="PDF file not found on disk")
    
    # Generate safe filename for download
    title = doc.get("title", "document")
    # Sanitize title for filename
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_title = safe_title[:100]  # Limit length
    filename = f"{safe_title}.pdf" if safe_title else f"{document_id}.pdf"
    
    # Return file
    return FileResponse(
        path=str(full_path),
        media_type="application/pdf",
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
```

#### `app/main.py` にルーターを登録

```python
from app.api.routes import documents

app.include_router(documents.router)
```

**設計判断**:
- RESTful APIパターン: `GET /api/documents/{id}/pdf`
- セキュリティ: パストラバーサル攻撃を防ぐための厳密なパス検証
- ファイル名のサニタイゼーション: ドキュメントタイトルから安全なファイル名を生成
- `FileResponse` を使用した効率的なファイル転送
- `Content-Disposition: attachment` でダウンロードを強制

### 6. UIコンポーネント

#### `app/templates/partials/document_card.html` にPDFダウンロードボタンを追加

```html
<!-- 既存の「元記事」ボタンの後に追加 -->
<div class="mt-1 text-xs text-gray-400 truncate flex items-center gap-2">
    {% if document.source %}
        <span class="pill nowrap-tag inline-flex items-center h-6 px-2 text-xs">
            {{ '手動' if document.source == 'manual' else document.source }}
        </span>
    {% endif %}
    
    {% if document.domain %}
        <span class="inline-block truncate max-w-[12rem]">{{ document.domain }}</span>
    {% endif %}
    
    {% if document.url %}
        <a href="{{ document.url }}" target="_blank" rel="noopener noreferrer" 
           class="pill nowrap-tag inline-flex items-center h-6 px-2 text-xs bg-mist/80 text-graphite border border-mist">
            <i data-lucide="external-link" class="w-4 h-4 mr-2"></i>
            元記事
        </a>
    {% endif %}
    
    <!-- 新規追加: PDFダウンロードボタン -->
    {% if document.pdf_path %}
        <a href="/api/documents/{{ document.id }}/pdf" 
           download
           class="pill nowrap-tag inline-flex items-center h-6 px-2 text-xs bg-red-50 text-red-600 border border-red-200 hover:bg-red-100 transition-colors"
           title="PDFをダウンロード">
            <i data-lucide="file-down" class="w-4 h-4 mr-1"></i>
            PDF
        </a>
    {% endif %}
    
    <a href="/documents/{{ document.id }}" 
       class="text-xs bg-emerald text-white px-3 py-1 rounded-md hover:bg-emerald/90 ml-2">
        詳細を見る
    </a>
</div>
```

**設計判断**:
- 条件付き表示: `{% if document.pdf_path %}` でPDFが存在する場合のみ表示
- アイコン: `file-down` (Lucide Icons) でダウンロードアクションを明示
- カラー: 赤系統でPDFファイルを視覚的に識別
- `download` 属性でブラウザにダウンロードを指示
- ツールチップ（title属性）でアクションを説明

#### ドキュメント詳細ページにも追加

`app/templates/document_detail.html` にも同様のボタンを追加：

```html
<!-- ヘッダーセクションのアクションボタン群に追加 -->
{% if document.pdf_path %}
    <a href="/api/documents/{{ document.id }}/pdf" 
       download
       class="inline-flex items-center px-4 py-2 bg-red-50 text-red-600 border border-red-200 rounded-md hover:bg-red-100 transition-colors">
        <i data-lucide="file-down" class="w-5 h-5 mr-2"></i>
        PDFをダウンロード
    </a>
{% endif %}
```

### 7. 管理画面での表示

#### `app/templates/admin/documents.html` (存在する場合)

ドキュメント一覧に PDF 状態を表示：

```html
<table class="min-w-full">
    <thead>
        <tr>
            <!-- 既存カラム -->
            <th>タイトル</th>
            <th>ドメイン</th>
            <th>作成日</th>
            <!-- 新規追加 -->
            <th>PDF</th>
        </tr>
    </thead>
    <tbody>
        {% for doc in documents %}
        <tr>
            <!-- 既存データ -->
            <td>{{ doc.title }}</td>
            <td>{{ doc.domain }}</td>
            <td>{{ doc.created_at|to_jst('%Y-%m-%d') }}</td>
            <!-- 新規追加 -->
            <td class="text-center">
                {% if doc.pdf_path %}
                    <a href="/api/documents/{{ doc.id }}/pdf" 
                       class="text-red-600 hover:text-red-800" 
                       title="PDFダウンロード">
                        <i data-lucide="file-check" class="w-5 h-5"></i>
                    </a>
                {% else %}
                    <span class="text-gray-300">
                        <i data-lucide="file-x" class="w-5 h-5"></i>
                    </span>
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
```

## データフロー

### 1. フィード登録フロー
```
ユーザー入力（管理画面）
  → POST /api/admin/sources
    → DB: sources テーブルに登録
      → cron スケジュール設定
```

### 2. 自動取得フロー
```
Scheduler (cron)
  → trigger_fetch_for_source(source_id)
    → _fetch_speakerdeck_items(config)
      → feedparser.parse(feed_url)
        → [エントリリスト]
          → _insert_document_from_url(url)
            → extractor.extract_from_url()
            → _insert_document_if_new()
              → [SpeakerDeck検出]
                → SpeakerDeckHandler.get_pdf_url()
                → SpeakerDeckHandler.download_pdf()
                → UPDATE documents SET pdf_path
```

### 3. PDFダウンロードフロー
```
ユーザークリック（UIボタン）
  → GET /api/documents/{id}/pdf
    → DB: pdf_path 取得
      → File System: PDFファイル読み込み
        → FileResponse (HTTP)
          → ブラウザ: ダウンロード開始
```

## エラーハンドリング

### 1. フィード取得エラー
- **ネットワークエラー**: ログに記録、次回スケジュールで再試行
- **フォーマットエラー**: feedparser が処理、エラーエントリはスキップ
- **認証エラー**: 404/403レスポンス時はログに記録、ソースを無効化推奨

### 2. PDF取得エラー
- **URL抽出失敗**: 警告ログ、ドキュメントは登録（pdf_path = NULL）
- **ダウンロード失敗**: エラーログ、部分ファイル削除、pdf_path = NULL
- **タイムアウト**: 30秒で中断、エラーログ
- **ファイルサイズ超過**: ダウンロード中止、エラーログ

### 3. PDFダウンロードエラー（エンドポイント）
- **ドキュメント不存在**: 404 Not Found
- **PDF未保存**: 404 Not Found (詳細メッセージ付き)
- **ファイル不存在**: 404 Not Found (ディスク上にファイルがない)
- **パス不正**: 403 Forbidden (セキュリティエラー)

## セキュリティ考慮事項

### 1. パストラバーサル対策
```python
# 必ず data/ ディレクトリ内に限定
full_path = full_path.resolve()
data_dir = Path("data").resolve()
if not str(full_path).startswith(str(data_dir)):
    raise HTTPException(status_code=403)
```

### 2. ファイルサイズ制限
- デフォルト: 100MB
- 設定で調整可能

### 3. URL検証
```python
# SpeakerDeckドメインのみ許可
if parsed.netloc not in ("speakerdeck.com", "www.speakerdeck.com"):
    return None
```

### 4. ファイル名サニタイゼーション
```python
# 英数字とスペース、ハイフン、アンダースコアのみ許可
safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_'))
```

## パフォーマンス最適化

### 1. 非同期処理の検討（将来的）
- PDF ダウンロードをバックグラウンドタスクに移行
- Celery や rq を使用したワーカープロセス
- 現状: 同期処理で実装（シンプルさ優先）

### 2. キャッシュ戦略
- PDFファイルは永続保存、再ダウンロード不要
- ブラウザキャッシュヘッダー設定（将来的）

### 3. データベースインデックス
```sql
CREATE INDEX idx_documents_pdf_path ON documents(pdf_path) WHERE pdf_path IS NOT NULL;
```

## テスト戦略

### 1. ユニットテスト
- `SpeakerDeckHandler.is_speakerdeck_url()`
- `SpeakerDeckHandler.get_pdf_url()` (モック使用)
- `SpeakerDeckHandler.download_pdf()` (モック使用)
- `_fetch_speakerdeck_items()` (feedparserモック)

### 2. 統合テスト
- フィード登録 → 自動取得 → ドキュメント登録
- PDF ダウンロード → ファイル保存 → DB更新
- PDFダウンロードAPIエンドポイント

### 3. E2Eテスト（Playwright）
- SpeakerDeckソース登録
- ドキュメントカードでPDFボタン表示確認
- PDFダウンロードボタンクリック → ファイルダウンロード確認

## 監視・ログ

### ログレベル
- **INFO**: フィード取得成功、PDF保存成功
- **WARNING**: PDF URL抽出失敗、ダウンロード失敗（ドキュメントは登録）
- **ERROR**: ネットワークエラー、ファイルシステムエラー

### メトリクス（将来的）
- フィード取得成功率
- PDF保存成功率
- PDFダウンロード数
- ストレージ使用量

## 依存関係

### 既存ライブラリ
- `feedparser`: RSS/Atom解析
- `httpx`: HTTP通信
- `Pillow`: サムネイル生成（既存）
- `FastAPI`: APIフレームワーク
- `SQLAlchemy`: データベース

### 新規依存関係
なし（既存ライブラリで実装可能）

## 後方互換性

- 既存ドキュメントは `pdf_path = NULL` で動作継続
- 既存フィード（qiita, hatena, rss）に影響なし
- UI: PDFボタンは条件付き表示、既存UIを破壊しない
- API: 新規エンドポイント追加のみ

## デプロイ手順

1. **マイグレーション実行**
   ```bash
   python migrations/apply_migrations.py
   ```

2. **コード更新**
   - `app/services/speakerdeck_handler.py` 追加
   - `app/services/ingest_worker.py` 更新
   - `app/api/routes/documents.py` 更新
   - `app/templates/partials/document_card.html` 更新

3. **ディレクトリ作成**
   ```bash
   mkdir -p data/assets/pdfs/speakerdeck
   ```

4. **アプリケーション再起動**
   ```bash
   systemctl restart scrap-board
   # または docker-compose restart
   ```

5. **動作確認**
   - SpeakerDeckソース登録
   - フィード取得実行
   - PDFダウンロード確認

## 将来の拡張候補

1. **PDFプレビュー機能**
   - ブラウザ内PDFビューアー統合
   - サムネイル生成（最初のページ）

2. **バックグラウンド処理**
   - PDF取得を非同期タスクキューに移行
   - 再試行ロジック実装

3. **ストレージ管理**
   - 古いPDFの自動削除
   - ストレージ使用量アラート

4. **他のスライドサービス対応**
   - SlideShare
   - Docswell
   - Google Slides

5. **PDF分析機能**
   - OCR（日本語対応）
   - テキスト抽出・検索
   - スライド枚数カウント
