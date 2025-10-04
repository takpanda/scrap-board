from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, List
import json
import tempfile
import os
import logging

from app.core.database import get_db, Document, Classification, Embedding
from app.services.extractor import content_extractor
from app.services.llm_client import llm_client
from app.core.config import settings
from datetime import datetime
import asyncio
from app.core.database import SessionLocal
from app.services.ingest_worker import _ensure_thumbnail_for_url

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/url")
async def ingest_url(
    url: str = Form(...),
    force: bool = Form(False),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """URLからコンテンツを取り込み"""
    
    # 重複チェック
    existing = db.query(Document).filter(Document.url == url).first()
    if existing:
        if not force:
            return {"message": "URL already exists", "document_id": existing.id}
        else:
            # force が指定されている場合は既存レコードを削除してから再作成する
            try:
                db.delete(existing)
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to delete existing document {existing.id} for force ingest: {e}")
                raise HTTPException(status_code=500, detail="Failed to overwrite existing document")
    
    # コンテンツ抽出
    content_data = await content_extractor.extract_from_url(url)
    if not content_data:
        raise HTTPException(status_code=400, detail="Failed to extract content")
    
    # ドキュメント保存
    # Try to ensure thumbnail (reuse existing ingest worker helper)
    try:
        thumb = _ensure_thumbnail_for_url(db, content_data.get("url"))
        if thumb:
            content_data["thumbnail_url"] = thumb
    except Exception:
        logger.debug("Thumbnail fetch failed for %s", url)

    document = Document(**content_data)
    # 手動取り込みであることを明示的に記録
    try:
        document.source = "manual"
    except Exception:
        # 安全側: もし Document に source 属性がない場合は無視
        logger.debug("Document model has no 'source' attribute; skipping manual source tag")
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # 要約生成（同期モードでは即時生成してDBに保存、非同期モードではバックグラウンドで処理）
    try:
        if settings.summary_mode == "sync":
            text_for_summary = content_extractor.prepare_text_for_summary(content_data.get("content_text", ""), max_chars=settings.short_summary_max_chars)
            short = await llm_client.generate_summary(text_for_summary, style="short", timeout_sec=settings.summary_timeout_sec)
            # short のみ同期保存
            if short is not None:
                document.short_summary = short[:settings.short_summary_max_chars]
                document.summary_generated_at = datetime.utcnow()
                document.summary_model = settings.summary_model or settings.chat_model
                db.add(document)
                db.commit()

            # 続けて分類・埋め込みなどの非同期処理は待機して実行
            await _process_document_async(document.id, content_data, db)
        else:
            # 非同期モード: BackgroundTasks に処理を登録してレスポンスを即時返す
            if background_tasks is not None:
                background_tasks.add_task(_process_document_background_sync, document.id)
            else:
                # fallback: create_task
                asyncio.create_task(_process_document_background(document.id))
    except Exception as e:
        logger.error(f"Summary/background processing scheduling failed for {document.id}: {e}")
    
    return {
        "message": "Content ingested successfully",
        "document_id": document.id,
        "title": document.title
    }


@router.post("/pdf")
async def ingest_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """PDFファイルを取り込み"""
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF file required")
    
    # 一時ファイルに保存
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name
    
    try:
        # PDF抽出
        content_data = await content_extractor.extract_from_pdf(tmp_file_path, file.filename)
        if not content_data:
            raise HTTPException(status_code=400, detail="Failed to extract PDF content")
        
        # ドキュメント保存
        document = Document(**content_data)
        # 手動取り込みであることを明示的に記録
        try:
            document.source = "manual"
        except Exception:
            logger.debug("Document model has no 'source' attribute; skipping manual source tag")
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # 非同期でバックグラウンド処理
        await _process_document_async(document.id, content_data, db)
        
        return {
            "message": "PDF ingested successfully",
            "document_id": document.id,
            "title": document.title
        }
        
    finally:
        # 一時ファイル削除
        os.unlink(tmp_file_path)


@router.post("/rss")
async def ingest_rss(
    feed_url: str = Form(...),
    schedule: bool = Form(False),
    max_items: int = Form(20),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """RSSフィードを取り込み"""
    try:
        import feedparser
    except ModuleNotFoundError:
        raise HTTPException(status_code=500, detail="feedparser not installed")
    
    try:
        # RSSフィードをパース
        parsed = feedparser.parse(feed_url)
        
        if not parsed.entries:
            raise HTTPException(status_code=400, detail="No entries found in RSS feed")
        
        # 取り込むアイテムのリストを作成
        items_to_ingest = []
        for entry in parsed.entries[:max_items]:
            link = entry.get("link")
            if link:
                # 重複チェック
                existing = db.query(Document).filter(Document.url == link).first()
                if not existing:
                    items_to_ingest.append({
                        "url": link,
                        "title": entry.get("title", ""),
                        "published": entry.get("published"),
                        "summary": entry.get("summary", "")
                    })
        
        if not items_to_ingest:
            return {
                "message": "All items already exist",
                "total_entries": len(parsed.entries),
                "new_items": 0
            }
        
        # バックグラウンドでアイテムを取り込む
        if background_tasks is not None:
            background_tasks.add_task(_ingest_rss_items_background, items_to_ingest)
        else:
            asyncio.create_task(_ingest_rss_items_background_async(items_to_ingest))
        
        return {
            "message": f"RSS feed ingestion started for {len(items_to_ingest)} items",
            "total_entries": len(parsed.entries),
            "new_items": len(items_to_ingest),
            "feed_title": parsed.feed.get("title", "")
        }
        
    except Exception as e:
        logger.error(f"RSS feed ingestion error: {e}")
        raise HTTPException(status_code=500, detail=f"RSS feed ingestion failed: {str(e)}")


async def _process_document_async(document_id: str, content_data: dict, db: Session):
    """ドキュメントの非同期処理（分類・要約・埋め込み）"""
    try:
        # 分類実行
        classification_result = await llm_client.classify_content(
            content_data["title"],
            content_data["content_text"][:2000]  # 最初の2000文字
        )
        
        if classification_result:
            classification = Classification(
                document_id=document_id,
                primary_category=classification_result.get("primary_category", "その他"),
                topics=None,
                tags=classification_result.get("tags", []),
                confidence=classification_result.get("confidence", 0.5),
                method="llm"
            )
            db.add(classification)
        
        # 埋め込み生成
        embedding_vector = await llm_client.create_embedding(content_data["content_text"][:1000])
        if embedding_vector:
            embedding = Embedding(
                document_id=document_id,
                chunk_id=0,
                vec=json.dumps(embedding_vector),
                chunk_text=content_data["content_text"][:1000]
            )
            db.add(embedding)
        
        db.commit()
        logger.info(f"Document {document_id} processed successfully")
        
    except Exception as e:
        logger.error(f"Document processing error for {document_id}: {e}")
        db.rollback()


async def _process_document_background(document_id: str):
    """バックグラウンドで要約・分類・埋め込みを実行する（async モード用）。

    新しいDBセッションを作成して操作する。
    """
    db = SessionLocal()
    try:
        # ドキュメント取得
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.error(f"Background process: document not found {document_id}")
            return

        content_text = doc.content_text or ""

        # 要約生成（short）
        try:
            text_for_summary = content_extractor.prepare_text_for_summary(content_text, max_chars=settings.short_summary_max_chars)
            short = await llm_client.generate_summary(text_for_summary, style="short", timeout_sec=settings.summary_timeout_sec)
            if short is not None:
                doc.short_summary = short[:settings.short_summary_max_chars]
                doc.summary_generated_at = datetime.utcnow()
                doc.summary_model = settings.summary_model or settings.chat_model
                db.add(doc)
                db.commit()
        except Exception as e:
            logger.error(f"Background summary generation failed for {document_id}: {e}")
            db.rollback()

        # 続けて分類・埋め込み
        try:
            classification_result = await llm_client.classify_content(
                doc.title,
                (content_text[:2000] if content_text else "")
            )
            if classification_result:
                classification = Classification(
                    document_id=document_id,
                    primary_category=classification_result.get("primary_category", "その他"),
                    topics=None,
                    tags=classification_result.get("tags", []),
                    confidence=classification_result.get("confidence", 0.5),
                    method="llm"
                )
                db.add(classification)

            embedding_vector = await llm_client.create_embedding(content_text[:1000])
            if embedding_vector:
                embedding = Embedding(
                    document_id=document_id,
                    chunk_id=0,
                    vec=json.dumps(embedding_vector),
                    chunk_text=content_text[:1000]
                )
                db.add(embedding)

            db.commit()
            logger.info(f"Background document {document_id} processed successfully")
        except Exception as e:
            logger.error(f"Background document processing error for {document_id}: {e}")
            db.rollback()

    finally:
        db.close()


def _process_document_background_sync(document_id: str):
    """同期ラッパー: BackgroundTasks が呼べる形で非同期処理を実行する。

    この関数は内部で新しいイベントループを作ってコルーチンを実行する。
    """
    try:
        asyncio.run(_process_document_background(document_id))
    except Exception as e:
        logger.error(f"Background sync wrapper failed for {document_id}: {e}")


async def _ingest_rss_items_background_async(items: List[dict]):
    """RSSアイテムをバックグラウンドで取り込む（async版）"""
    db = SessionLocal()
    try:
        for item in items:
            try:
                url = item["url"]
                
                # コンテンツ抽出
                content_data = await content_extractor.extract_from_url(url)
                if not content_data:
                    logger.warning(f"Failed to extract content from {url}")
                    continue
                
                # サムネイル取得を試行
                try:
                    thumb = _ensure_thumbnail_for_url(db, content_data.get("url"))
                    if thumb:
                        content_data["thumbnail_url"] = thumb
                except Exception:
                    logger.debug("Thumbnail fetch failed for %s", url)
                
                # ドキュメント保存
                document = Document(**content_data)
                document.source = "rss"
                db.add(document)
                db.commit()
                db.refresh(document)
                
                # 要約・分類・埋め込みを実行
                await _process_document_async(document.id, content_data, db)
                
                logger.info(f"RSS item ingested successfully: {url}")
                
            except Exception as e:
                logger.error(f"Failed to ingest RSS item {item.get('url')}: {e}")
                db.rollback()
                
    finally:
        db.close()


def _ingest_rss_items_background(items: List[dict]):
    """RSSアイテムをバックグラウンドで取り込む（同期ラッパー）"""
    try:
        asyncio.run(_ingest_rss_items_background_async(items))
    except Exception as e:
        logger.error(f"RSS background ingestion failed: {e}")