from fastapi import FastAPI, Request, Form, File, UploadFile, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os
import logging
import asyncio
from contextlib import asynccontextmanager
from markdown_it import MarkdownIt

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

# Markdownフィルタを追加
md = MarkdownIt()

def markdown_filter(text):
    """MarkdownテキストをHTMLに変換するJinja2フィルタ"""
    if not text:
        return ""
    return md.render(text)

templates.env.filters["markdown"] = markdown_filter

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


# Design Pattern Demo Routes
@app.get("/demo/patterns", response_class=HTMLResponse)
async def design_patterns_index(request: Request):
    """デザインパターン一覧ページ"""
    return templates.TemplateResponse("demo_patterns_index.html", {
        "request": request
    })


@app.get("/demo/pattern1/{document_id}", response_class=HTMLResponse)
async def document_detail_pattern1(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db)
):
    """ドキュメント詳細ページ - パターン1（従来型改良版）"""
    from app.core.database import Document
    
    # サンプルドキュメントを作成（実際のドキュメントが存在しない場合）
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        # サンプルデータを作成
        from datetime import datetime
        from app.core.database import Document, Classification
        
        sample_document = type('Document', (), {
            'id': document_id,
            'title': 'AI と機械学習の最新トレンド：2024年版',
            'url': 'https://example.com/ai-trends-2024',
            'domain': 'example.com',
            'author': '田中 太郎',
            'content_text': 'AI（人工知能）と機械学習の分野は、2024年に入っても急速な進歩を続けています。特に大規模言語モデル（LLM）の発展により、自然言語処理の精度が格段に向上し、様々な業界での実用化が進んでいます。ChatGPTやGPT-4などのモデルは、従来の枠を超えて、コンテンツ生成、コード開発、データ分析など幅広い分野で活用されています。また、コンピュータビジョンの分野でも、画像認識や動画解析の精度が向上し、医療診断、自動運転、製造業での品質管理など、より実用的なアプリケーションが登場しています。一方で、AI倫理や責任あるAI開発への関心も高まっており、技術の進歩と並行して、適切なガバナンスとレギュレーションの整備が重要な課題となっています。',
            'content_md': '# AI と機械学習の最新トレンド：2024年版\n\nAI（人工知能）と機械学習の分野は、2024年に入っても急速な進歩を続けています。\n\n## 大規模言語モデル（LLM）の進化\n\n特に**大規模言語モデル（LLM）**の発展により、自然言語処理の精度が格段に向上し、様々な業界での実用化が進んでいます。\n\n- ChatGPTやGPT-4などのモデル\n- コンテンツ生成への活用\n- コード開発の支援\n- データ分析の自動化\n\n## コンピュータビジョンの進歩\n\nまた、コンピュータビジョンの分野でも、画像認識や動画解析の精度が向上し、より実用的なアプリケーションが登場しています：\n\n1. **医療診断** - 画像診断の精度向上\n2. **自動運転** - 環境認識技術の発達\n3. **製造業** - 品質管理の自動化\n\n## AI倫理への取り組み\n\n一方で、AI倫理や責任あるAI開発への関心も高まっており、技術の進歩と並行して、適切なガバナンスとレギュレーションの整備が重要な課題となっています。',
            'published_at': datetime(2024, 1, 15),
            'fetched_at': datetime(2024, 1, 16),
            'created_at': datetime(2024, 1, 16),
            'classifications': [type('Classification', (), {
                'primary_category': 'テクノロジー/AI',
                'tags': ['機械学習', 'ChatGPT', 'コンピュータビジョン', 'AI倫理'],
                'confidence': 0.92
            })()]
        })()
        document = sample_document
    
    return templates.TemplateResponse("document_detail_pattern1.html", {
        "request": request,
        "document": document
    })


@app.get("/demo/pattern2/{document_id}", response_class=HTMLResponse)
async def document_detail_pattern2(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db)
):
    """ドキュメント詳細ページ - パターン2（分割レイアウト）"""
    from app.core.database import Document
    
    # サンプルドキュメントを作成（実際のドキュメントが存在しない場合）
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        # サンプルデータを作成
        from datetime import datetime
        
        sample_document = type('Document', (), {
            'id': document_id,
            'title': 'AI と機械学習の最新トレンド：2024年版',
            'url': 'https://example.com/ai-trends-2024',
            'domain': 'example.com',
            'author': '田中 太郎',
            'content_text': 'AI（人工知能）と機械学習の分野は、2024年に入っても急速な進歩を続けています。特に大規模言語モデル（LLM）の発展により、自然言語処理の精度が格段に向上し、様々な業界での実用化が進んでいます。ChatGPTやGPT-4などのモデルは、従来の枠を超えて、コンテンツ生成、コード開発、データ分析など幅広い分野で活用されています。また、コンピュータビジョンの分野でも、画像認識や動画解析の精度が向上し、医療診断、自動運転、製造業での品質管理など、より実用的なアプリケーションが登場しています。一方で、AI倫理や責任あるAI開発への関心も高まっており、技術の進歩と並行して、適切なガバナンスとレギュレーションの整備が重要な課題となっています。',
            'content_md': '# AI と機械学習の最新トレンド：2024年版\n\nAI（人工知能）と機械学習の分野は、2024年に入っても急速な進歩を続けています。\n\n## 大規模言語モデル（LLM）の進化\n\n特に**大規模言語モデル（LLM）**の発展により、自然言語処理の精度が格段に向上し、様々な業界での実用化が進んでいます。\n\n- ChatGPTやGPT-4などのモデル\n- コンテンツ生成への活用\n- コード開発の支援\n- データ分析の自動化\n\n## コンピュータビジョンの進歩\n\nまた、コンピュータビジョンの分野でも、画像認識や動画解析の精度が向上し、より実用的なアプリケーションが登場しています：\n\n1. **医療診断** - 画像診断の精度向上\n2. **自動運転** - 環境認識技術の発達\n3. **製造業** - 品質管理の自動化\n\n## AI倫理への取り組み\n\n一方で、AI倫理や責任あるAI開発への関心も高まっており、技術の進歩と並行して、適切なガバナンスとレギュレーションの整備が重要な課題となっています。',
            'published_at': datetime(2024, 1, 15),
            'fetched_at': datetime(2024, 1, 16),
            'created_at': datetime(2024, 1, 16),
            'classifications': [type('Classification', (), {
                'primary_category': 'テクノロジー/AI',
                'tags': ['機械学習', 'ChatGPT', 'コンピュータビジョン', 'AI倫理'],
                'confidence': 0.92
            })()]
        })()
        document = sample_document
    
    return templates.TemplateResponse("document_detail_pattern2.html", {
        "request": request,
        "document": document
    })


@app.get("/demo/pattern3/{document_id}", response_class=HTMLResponse)
async def document_detail_pattern3(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db)
):
    """ドキュメント詳細ページ - パターン3（タブベース）"""
    from app.core.database import Document
    
    # サンプルドキュメントを作成（実際のドキュメントが存在しない場合）
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        # サンプルデータを作成
        from datetime import datetime
        
        sample_document = type('Document', (), {
            'id': document_id,
            'title': 'AI と機械学習の最新トレンド：2024年版',
            'url': 'https://example.com/ai-trends-2024',
            'domain': 'example.com',
            'author': '田中 太郎',
            'content_text': 'AI（人工知能）と機械学習の分野は、2024年に入っても急速な進歩を続けています。特に大規模言語モデル（LLM）の発展により、自然言語処理の精度が格段に向上し、様々な業界での実用化が進んでいます。ChatGPTやGPT-4などのモデルは、従来の枠を超えて、コンテンツ生成、コード開発、データ分析など幅広い分野で活用されています。また、コンピュータビジョンの分野でも、画像認識や動画解析の精度が向上し、医療診断、自動運転、製造業での品質管理など、より実用的なアプリケーションが登場しています。一方で、AI倫理や責任あるAI開発への関心も高まっており、技術の進歩と並行して、適切なガバナンスとレギュレーションの整備が重要な課題となっています。',
            'content_md': '# AI と機械学習の最新トレンド：2024年版\n\nAI（人工知能）と機械学習の分野は、2024年に入っても急速な進歩を続けています。\n\n## 大規模言語モデル（LLM）の進化\n\n特に**大規模言語モデル（LLM）**の発展により、自然言語処理の精度が格段に向上し、様々な業界での実用化が進んでいます。\n\n- ChatGPTやGPT-4などのモデル\n- コンテンツ生成への活用\n- コード開発の支援\n- データ分析の自動化\n\n## コンピュータビジョンの進歩\n\nまた、コンピュータビジョンの分野でも、画像認識や動画解析の精度が向上し、より実用的なアプリケーションが登場しています：\n\n1. **医療診断** - 画像診断の精度向上\n2. **自動運転** - 環境認識技術の発達\n3. **製造業** - 品質管理の自動化\n\n## AI倫理への取り組み\n\n一方で、AI倫理や責任あるAI開発への関心も高まっており、技術の進歩と並行して、適切なガバナンスとレギュレーションの整備が重要な課題となっています。',
            'published_at': datetime(2024, 1, 15),
            'fetched_at': datetime(2024, 1, 16),
            'created_at': datetime(2024, 1, 16),
            'classifications': [type('Classification', (), {
                'primary_category': 'テクノロジー/AI',
                'tags': ['機械学習', 'ChatGPT', 'コンピュータビジョン', 'AI倫理'],
                'confidence': 0.92
            })()]
        })()
        document = sample_document
    
    return templates.TemplateResponse("document_detail_pattern3.html", {
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