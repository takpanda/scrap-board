from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db, Document, Classification
from app.services.llm_client import LLMClient

router = APIRouter()

# LLMクライアントのインスタンス化
llm_client = LLMClient()

# テンプレート
templates = Jinja2Templates(directory="app/templates")


@router.get("")
async def list_documents(
    q: Optional[str] = Query(None, description="検索クエリ"),
    category: Optional[str] = Query(None, description="カテゴリフィルタ"),
    domain: Optional[str] = Query(None, description="ドメインフィルタ"),
    from_date: Optional[str] = Query(None, alias="from", description="開始日 (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, alias="to", description="終了日 (YYYY-MM-DD)"),
    limit: int = Query(50, le=100, description="取得件数"),
    offset: int = Query(0, description="オフセット"),
    db: Session = Depends(get_db)
):
    """ドキュメント一覧取得"""
    
    query = db.query(Document)
    
    # 検索クエリ
    if q:
        query = query.filter(Document.content_text.contains(q))
    
    # カテゴリフィルタ
    if category:
        query = query.join(Classification).filter(Classification.primary_category == category)
    
    # ドメインフィルタ
    if domain:
        query = query.filter(Document.domain == domain)
    
    # 日付フィルタ
    if from_date:
        try:
            from_dt = datetime.fromisoformat(from_date)
            query = query.filter(Document.created_at >= from_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid from date format")
    
    if to_date:
        try:
            to_dt = datetime.fromisoformat(to_date)
            query = query.filter(Document.created_at <= to_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid to date format")
    
    # ソート・ページング
    documents = query.order_by(Document.created_at.desc()).offset(offset).limit(limit).all()
    
    # 結果整形
    result = []
    for doc in documents:
        doc_data = {
            "id": doc.id,
            "title": doc.title,
            "url": doc.url,
            "domain": doc.domain,
            "author": doc.author,
            "published_at": doc.published_at.isoformat() if doc.published_at else None,
            "created_at": doc.created_at.isoformat(),
            "lang": doc.lang,
            "content_preview": doc.content_text[:200] + "..." if len(doc.content_text) > 200 else doc.content_text
        }
        
        # 分類情報
        if doc.classifications:
            classification = doc.classifications[0]  # 最新の分類
            doc_data["category"] = classification.primary_category
            doc_data["tags"] = classification.tags or []
            doc_data["confidence"] = classification.confidence
        
        result.append(doc_data)
    
    return {
        "documents": result,
        "total": len(result),
        "limit": limit,
        "offset": offset
    }


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    """ドキュメント詳細取得"""
    
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    result = {
        "id": document.id,
        "title": document.title,
        "url": document.url,
        "domain": document.domain,
        "author": document.author,
        "published_at": document.published_at.isoformat() if document.published_at else None,
        "fetched_at": document.fetched_at.isoformat(),
        "created_at": document.created_at.isoformat(),
        "updated_at": document.updated_at.isoformat(),
        "lang": document.lang,
        "content_md": document.content_md,
        "content_text": document.content_text,
        "hash": document.hash
    }
    
    # 分類情報
    if document.classifications:
        classification = document.classifications[0]
        result["classification"] = {
            "primary_category": classification.primary_category,
            "topics": classification.topics,
            "tags": classification.tags,
            "confidence": classification.confidence,
            "method": classification.method
        }
    
    return result


@router.post("/{document_id}/feedback")
async def submit_feedback(
    document_id: str,
    label: str,
    comment: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """分類フィードバック送信"""
    
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if label not in ["correct", "incorrect"]:
        raise HTTPException(status_code=400, detail="Label must be 'correct' or 'incorrect'")
    
    from app.core.database import Feedback
    
    feedback = Feedback(
        document_id=document_id,
        label=label,
        comment=comment
    )
    
    db.add(feedback)
    db.commit()
    
    return {"message": "Feedback submitted successfully"}


@router.post("/{document_id}/summarize")
async def summarize_document(
    document_id: str,
    db: Session = Depends(get_db)
):
    """ドキュメント要約生成"""
    
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        # LLMクライアントを使用して要約を生成
        summary = await llm_client.summarize_text(document.content_text, "short")
        
        if summary:
            return {"short_summary": summary}
        else:
            return {"short_summary": "要約の生成に失敗しました。LLMサービスに接続できませんでした。"}
    
    except Exception as e:
        # エラーが発生した場合はログに記録してユーザーフレンドリーなメッセージを返す
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Summary generation error for document {document_id}: {e}")
        
        return {"short_summary": "要約の生成中にエラーが発生しました。"}


@router.get("/{document_id}/similar")
async def get_similar_documents(
    request: Request,
    document_id: str,
    limit: int = Query(5, le=20),
    db: Session = Depends(get_db)
):
    """類似ドキュメント取得"""
    
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # TODO: 埋め込みベースの類似度計算実装
    # 現在は同じカテゴリの他のドキュメントを返す簡易実装
    
    similar_docs = []
    if document.classifications:
        category = document.classifications[0].primary_category
        similar_query = db.query(Document).join(Classification).filter(
            Classification.primary_category == category,
            Document.id != document_id
        ).limit(limit)
        
        similar_docs = similar_query.all()
    
    # Format the documents for template
    formatted_docs = []
    for doc in similar_docs:
        formatted_docs.append({
            "id": doc.id,
            "title": doc.title,
            "url": doc.url,
            "domain": doc.domain,
            "created_at": doc.created_at.strftime('%Y年%m月%d日'),
            "similarity_score": 0.7  # プレースホルダー
        })
    
    # Check if this is an HTMX request
    if request.headers.get("HX-Request"):
        # Return HTML partial for HTMX
        return templates.TemplateResponse(
            "partials/similar_documents.html",
            {
                "request": request,
                "similar_documents": formatted_docs
            }
        )
    else:
        # Return JSON for API calls
        return {"similar_documents": formatted_docs}