from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any

from app.core.database import get_db, Document, Classification, Collection

router = APIRouter()


@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """統計情報を取得"""
    
    # ドキュメント数
    total_docs = db.query(func.count(Document.id)).scalar() or 0
    
    # 今日追加されたドキュメント数
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).date()
    today_docs = db.query(func.count(Document.id)).filter(
        func.date(Document.created_at) == today
    ).scalar() or 0
    
    # カテゴリ数（分類済みのもの）
    total_categories = db.query(func.count(func.distinct(Classification.primary_category))).scalar() or 0
    
    # コレクション数
    total_collections = db.query(func.count(Collection.id)).scalar() or 0
    
    return {
        "total_documents": total_docs,
        "today_documents": today_docs,
        "total_categories": total_categories,
        "total_collections": total_collections
    }


@router.get("/search")
async def search_content(
    q: str = Query(..., description="検索クエリ"),
    limit: int = Query(10, le=20),
    db: Session = Depends(get_db)
):
    """コンテンツ検索"""
    
    if not q or len(q.strip()) < 2:
        return {"results": [], "total": 0}
    
    # 簡単な全文検索
    query = db.query(Document).filter(
        Document.content_text.contains(q.strip())
    )
    
    documents = query.limit(limit).all()
    
    results = []
    for doc in documents:
        results.append({
            "id": doc.id,
            "title": doc.title,
            "url": doc.url,
            "domain": doc.domain,
            "created_at": doc.created_at.isoformat(),
            "content_preview": doc.content_text[:150] + "..." if len(doc.content_text) > 150 else doc.content_text
        })
    
    return {
        "results": results,
        "total": len(results),
        "query": q
    }


@router.post("/export")
async def export_content(
    format: str = Query(..., regex="^(md|csv|jsonl)$"),
    category: str = Query(None),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db)
):
    """コンテンツエクスポート"""
    
    query = db.query(Document)
    
    # カテゴリフィルタ
    if category:
        query = query.join(Classification).filter(Classification.primary_category == category)
    
    documents = query.limit(limit).all()
    
    if format == "md":
        # Markdown形式
        content = "# Scrap-Board Export\n\n"
        for doc in documents:
            content += f"## {doc.title}\n\n"
            if doc.url:
                content += f"**URL**: {doc.url}\n\n"
            content += f"**作成日**: {doc.created_at.strftime('%Y年%m月%d日')}\n\n"
            content += f"{doc.content_md}\n\n---\n\n"
        
        return {"content": content, "filename": f"scrap-board-export.md"}
    
    elif format == "csv":
        # CSV形式（簡易）
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Title", "URL", "Domain", "Created", "Content Preview"])
        
        for doc in documents:
            writer.writerow([
                doc.id,
                doc.title,
                doc.url or "",
                doc.domain or "",
                doc.created_at.isoformat(),
                doc.content_text[:200].replace('\n', ' ') if doc.content_text else ""
            ])
        
        return {"content": output.getvalue(), "filename": "scrap-board-export.csv"}
    
    elif format == "jsonl":
        # JSONL形式
        import json
        
        lines = []
        for doc in documents:
            data = {
                "id": doc.id,
                "title": doc.title,
                "url": doc.url,
                "domain": doc.domain,
                "created_at": doc.created_at.isoformat(),
                "content_md": doc.content_md,
                "content_text": doc.content_text
            }
            
            # 分類情報があれば追加
            if doc.classifications:
                classification = doc.classifications[0]
                data["classification"] = {
                    "primary_category": classification.primary_category,
                    "tags": classification.tags,
                    "confidence": classification.confidence
                }
            
            lines.append(json.dumps(data, ensure_ascii=False))
        
        return {"content": "\n".join(lines), "filename": "scrap-board-export.jsonl"}
    
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")