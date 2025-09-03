from fastapi import FastAPI, Request, Form, File, UploadFile, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os
import logging
import asyncio
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import get_db, create_tables
from app.api.routes import documents, ingest, collections, utils

# ログ設定
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションライフサイクル"""
    # 起動時
    logger.info("Scrap-Board starting up...")
    create_tables()
    logger.info("Database tables created/verified")
    
    yield
    
    # 終了時
    logger.info("Scrap-Board shutting down...")


# FastAPIアプリケーション
app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    lifespan=lifespan
)

# 静的ファイル
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# テンプレート
templates = Jinja2Templates(directory="app/templates")

# APIルーター
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(ingest.router, prefix="/api/ingest", tags=["ingest"])
app.include_router(collections.router, prefix="/api/collections", tags=["collections"])
app.include_router(utils.router, prefix="/api", tags=["utils"])


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
    db: Session = Depends(get_db)
):
    """ドキュメント一覧ページ"""
    # 基本的なクエリ（後で改善）
    from app.core.database import Document
    
    query = db.query(Document)
    
    if q:
        query = query.filter(Document.content_text.contains(q))
    
    documents = query.order_by(Document.created_at.desc()).limit(50).all()
    
    return templates.TemplateResponse("documents.html", {
        "request": request,
        "documents": documents,
        "q": q,
        "category": category
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower()
    )