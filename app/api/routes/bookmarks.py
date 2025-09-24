from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from app.core.database import get_db, Bookmark, Document

router = APIRouter()


class BookmarkCreate(BaseModel):
    document_id: str
    note: Optional[str] = None


@router.post("")
async def create_bookmark(payload: BookmarkCreate, db: Session = Depends(get_db)):
    """ブックマーク作成（最小実装）"""
    document_id = payload.document_id
    note = payload.note
    # document の存在確認
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # 重複チェック（user_id は未実装のため NULL として扱う）
    existing = db.query(Bookmark).filter(Bookmark.user_id == None, Bookmark.document_id == document_id).first()
    if existing:
        # Return existing bookmark instead of 409 to make POST idempotent for UI convenience
        return {
            "id": existing.id,
            "document_id": existing.document_id,
            "note": existing.note,
            "created_at": existing.created_at.isoformat(),
        }

    bm = Bookmark(user_id=None, document_id=document_id, note=note)
    db.add(bm)
    db.commit()
    db.refresh(bm)

    return {
        "id": bm.id,
        "document_id": bm.document_id,
        "note": bm.note,
        "created_at": bm.created_at.isoformat()
    }


@router.delete("/{bookmark_id}")
async def delete_bookmark(bookmark_id: str, db: Session = Depends(get_db)):
    bm = db.query(Bookmark).filter(Bookmark.id == bookmark_id).first()
    if not bm:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    db.delete(bm)
    db.commit()
    return {"message": "deleted"}


@router.get("")
async def list_bookmarks(limit: int = Query(50, le=200), offset: int = Query(0), db: Session = Depends(get_db)):
    """ユーザー（匿名含む）のブックマーク一覧。現状 user_id=NULL のものを返す。"""
    q = db.query(Bookmark).filter(Bookmark.user_id == None).order_by(Bookmark.created_at.desc()).offset(offset).limit(limit)
    items = q.all()

    result = []
    for b in items:
        result.append({
            "id": b.id,
            "document_id": b.document_id,
            "note": b.note,
            "created_at": b.created_at.isoformat(),
            "document": {
                "id": b.document.id,
                "title": b.document.title,
                "url": b.document.url
            } if b.document else None
        })

    return {"bookmarks": result, "total": len(result), "limit": limit, "offset": offset}


@router.delete("")
async def delete_bookmark_by_document(document_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Delete bookmark by document_id via query parameter. Used by UI where only document_id is known.
    If no document_id provided, return 400.
    """
    if not document_id:
        raise HTTPException(status_code=400, detail="document_id query parameter required")

    bm = db.query(Bookmark).filter(Bookmark.user_id == None, Bookmark.document_id == document_id).first()
    if not bm:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    db.delete(bm)
    db.commit()
    return {"message": "deleted"}
