from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db, Collection, CollectionItem, Document

router = APIRouter()


@router.get("")
async def list_collections(
    db: Session = Depends(get_db)
):
    """コレクション一覧取得"""
    
    collections = db.query(Collection).order_by(Collection.created_at.desc()).all()
    
    result = []
    for collection in collections:
        result.append({
            "id": collection.id,
            "name": collection.name,
            "description": collection.description,
            "created_at": collection.created_at.isoformat(),
            "item_count": len(collection.items)
        })
    
    return {"collections": result}


@router.post("")
async def create_collection(
    name: str,
    description: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """コレクション作成"""
    
    collection = Collection(
        name=name,
        description=description
    )
    
    db.add(collection)
    db.commit()
    db.refresh(collection)
    
    return {
        "id": collection.id,
        "name": collection.name,
        "description": collection.description,
        "created_at": collection.created_at.isoformat()
    }


@router.get("/{collection_id}")
async def get_collection(
    collection_id: str,
    db: Session = Depends(get_db)
):
    """コレクション詳細取得"""
    
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    # アイテム一覧
    items = []
    for item in collection.items:
        items.append({
            "id": item.id,
            "document": {
                "id": item.document.id,
                "title": item.document.title,
                "url": item.document.url,
                "domain": item.document.domain,
                "created_at": item.document.created_at.isoformat()
            },
            "note": item.note,
            "created_at": item.created_at.isoformat()
        })
    
    return {
        "id": collection.id,
        "name": collection.name,
        "description": collection.description,
        "created_at": collection.created_at.isoformat(),
        "items": items
    }


@router.post("/{collection_id}/items")
async def add_to_collection(
    collection_id: str,
    document_id: str,
    note: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """コレクションにドキュメント追加"""
    
    collection = db.query(Collection).filter(Collection.id == collection_id).first()
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # 重複チェック
    existing = db.query(CollectionItem).filter(
        CollectionItem.collection_id == collection_id,
        CollectionItem.document_id == document_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Document already in collection")
    
    item = CollectionItem(
        collection_id=collection_id,
        document_id=document_id,
        note=note
    )
    
    db.add(item)
    db.commit()
    
    return {"message": "Document added to collection successfully"}


@router.delete("/{collection_id}/items/{item_id}")
async def remove_from_collection(
    collection_id: str,
    item_id: str,
    db: Session = Depends(get_db)
):
    """コレクションからドキュメント削除"""
    
    item = db.query(CollectionItem).filter(
        CollectionItem.id == item_id,
        CollectionItem.collection_id == collection_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db.delete(item)
    db.commit()
    
    return {"message": "Document removed from collection successfully"}