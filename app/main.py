from fastapi import FastAPI, Request, Form, File, UploadFile, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.orm import Session
import os
import logging
import asyncio
from contextlib import asynccontextmanager
from markdown_it import MarkdownIt

from app.core.config import settings
from app.core.database import get_db, create_tables
from app.services.scheduler import start_scheduler, stop_scheduler
from app.api.routes import documents, ingest, collections, utils, admin_sources
from app.api.routes import admin as admin_routes
from datetime import timezone, timedelta
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

# ログ設定
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションライフサイクル"""
    # 起動時
    logger.info("Scrap-Board starting up...")
    # 在テスト環境(pytest)では、テストごとに独自のDBセットアップを行うため
    # アプリ起動時にグローバルなテーブル作成をスキップする。
    # pytest は `PYTEST_CURRENT_TEST` 環境変数をセットするためこれを利用する。
    import os
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        try:
            create_tables()
            logger.info("Database tables created/verified")
        except Exception:
            logger.exception("create_tables() failed during startup")
        try:
            start_scheduler()
            logger.info("Scheduler started")
        except Exception:
            logger.exception("Failed to start scheduler")
    
    yield
    
    # 終了時
    logger.info("Scrap-Board shutting down...")
    try:
        stop_scheduler()
        logger.info("Scheduler stopped")
    except Exception:
        logger.exception("Failed to stop scheduler")


# FastAPIアプリケーション
app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    lifespan=lifespan
)

# 静的ファイル
app.mount("/static", StaticFiles(directory="app/static"), name="static")
# Serve uploaded/generated data assets (thumbnails, uploads)
app.mount("/data", StaticFiles(directory="data"), name="data")

# テンプレート
templates = Jinja2Templates(directory="app/templates")

# Markdownフィルタを追加
md = MarkdownIt()

def markdown_filter(text):
    """MarkdownテキストをHTMLに変換するJinja2フィルタ"""
    if not text:
        return ""
    return md.render(text)

templates.env.filters["markdown"] = markdown_filter
def to_jst(dt, fmt="%Y年%m月%d日 %H:%M"):
    """日時を日本標準時(JST)に変換してフォーマットする Jinja2 フィルタ。

    - dt が None の場合は空文字を返す。
    - dt.tzinfo が None の場合は UTC とみなして変換する。
    - ZoneInfo が利用できない場合は timezone offset +9 を適用する。
    """
    if not dt:
        return ""
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if ZoneInfo is not None:
            jst = dt.astimezone(ZoneInfo("Asia/Tokyo"))
        else:
            jst = dt.astimezone(timezone(timedelta(hours=9)))
        return jst.strftime(fmt)
    except Exception:
        try:
            return dt.strftime(fmt)
        except Exception:
            return ""

templates.env.filters["to_jst"] = to_jst

# APIルーター
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(ingest.router, prefix="/api/ingest", tags=["ingest"])
app.include_router(collections.router, prefix="/api/collections", tags=["collections"])
app.include_router(utils.router, prefix="/api", tags=["utils"])
app.include_router(admin_sources.router)
app.include_router(admin_routes.router)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    """ホームページ"""
    from app.core.database import Document
    from datetime import datetime, timedelta
    
    # 最近のドキュメント（最新5件）を取得
    recent_documents = db.query(Document).order_by(Document.created_at.desc()).limit(5).all()
    
    # 統計情報の取得
    total_documents = db.query(Document).count()
    
    # 今日追加されたドキュメント数
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_documents = db.query(Document).filter(Document.created_at >= today_start).count()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "recent_documents": recent_documents,
        "total_documents": total_documents,
        "today_documents": today_documents
    })


@app.get("/documents", response_class=HTMLResponse)
async def documents_page(
    request: Request,
    q: str = "",
    category: str = "",
    tag: str = "",
    db: Session = Depends(get_db)
):
    """ドキュメント一覧ページ"""
    # 基本的なクエリ（後で改善）
    from app.core.database import Document, Classification
    
    query = db.query(Document)
    
    if q:
        query = query.filter(Document.content_text.contains(q))

    # タグによるフィルタ（SQLite の JSON 配列を考慮して json_extract + LIKE を利用）
    if tag:
        # Join classifications and filter where the tags JSON array contains the given tag string.
        # This uses a best-effort SQLite json_extract + LIKE check which matches '"tag"' inside the JSON array text.
        # SQLite may store JSON with non-ASCII characters escaped (e.g. "\\u81ea\\u52d5\\u5316").
        # Comparing the raw column text with LIKE is more robust for matching either
        # the UTF-8 characters or their escaped \uXXXX representations.
        raw_like = f'%"{tag}"%'
        def to_escaped(s: str) -> str:
            return s.encode('unicode_escape').decode('ascii')
        escaped_tag = to_escaped(tag)
        escaped_like = f'%"{escaped_tag}"%'

        query = query.join(Classification).filter(
            text("(classifications.tags LIKE :raw_like OR classifications.tags LIKE :escaped_like)")
        ).params(raw_like=raw_like, escaped_like=escaped_like)
    
    documents = query.order_by(Document.created_at.desc()).limit(50).all()
    
    return templates.TemplateResponse("documents.html", {
        "request": request,
        "documents": documents,
        "q": q,
        "category": category,
        "tag": tag
    })


@app.get("/documents/{document_id}", response_class=HTMLResponse)
async def document_detail(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db)
):
    """ドキュメント詳細ページ"""
    from app.core.database import Document
    
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return templates.TemplateResponse("document_detail.html", {
        "request": request,
        "document": document
    })


@app.get("/reader/{document_id}", response_class=HTMLResponse)
async def reader_mode(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db)
):
    """Reader Mode"""
    from app.core.database import Document
    
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return templates.TemplateResponse("reader.html", {
        "request": request,
        "document": document
    })


@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {"status": "healthy", "version": settings.app_version}


@app.get("/admin", response_class=HTMLResponse)
async def admin_sources_page(request: Request, db: Session = Depends(get_db)):
    """ソース管理ページ（HTMX を使った CRUD UI を提供）"""
    # サーバー側で一覧を取得して初回レンダリングに含める（JSが無効な環境向けフォールバック）
    try:
        result = db.execute(text("SELECT id,name,type,config,enabled,cron_schedule,last_fetched_at FROM sources"))
        rows = result.fetchall()
        sources = [dict(r._mapping) for r in rows]
    except Exception:
        sources = []

    return templates.TemplateResponse("admin/sources.html", {"request": request, "sources": sources})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower()
    )