from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, case, or_
from sqlalchemy.orm import Session, aliased
from typing import Optional, List, Dict
from datetime import datetime
from html import escape

from app.core.database import get_db, Document, Classification, PersonalizedScore, Bookmark
from app.core.user_utils import normalize_user_id
from app.services.llm_client import LLMClient
from app.services.personalized_feedback import PersonalizedFeedbackService
from app.services.personalized_repository import PersonalizedScoreRepository
from app.services.similarity import calculate_document_similarity

router = APIRouter()

# LLMクライアントのインスタンス化
llm_client = LLMClient()

# テンプレート
templates = Jinja2Templates(directory="app/templates")


def _resolve_user_id(request: Request) -> str:
    """Resolve user ID from request, defaulting to 'guest' for unidentified users."""
    user = getattr(request.state, "user", None)
    if user is not None:
        user_id = getattr(user, "id", None) or getattr(user, "user_id", None)
        if user_id:
            return normalize_user_id(str(user_id))

    header_user = request.headers.get("X-User-Id")
    if header_user:
        return normalize_user_id(header_user)

    return normalize_user_id(None)


def _fetch_personalized_documents(query, user_id: str, offset: int, limit: int, db: Session):
    # user_id is now always a string (normalized to "guest" for unidentified users)
    # Try to prefer user-specific scores, then fall back to guest scores if user is not "guest".
    # For "guest" users, only return their own scores.
    from app.core.user_utils import GUEST_USER_ID
    
    if user_id != GUEST_USER_ID:
        # For identified users: prefer user-specific scores, fall back to guest (global) scores
        user_alias = aliased(PersonalizedScore)
        guest_alias = aliased(PersonalizedScore)

        user_join = and_(user_alias.document_id == Document.id, user_alias.user_id == user_id)
        guest_join = and_(guest_alias.document_id == Document.id, guest_alias.user_id == GUEST_USER_ID)

        personalized_query = query.outerjoin(user_alias, user_join).outerjoin(guest_alias, guest_join).add_entity(user_alias).add_entity(guest_alias)

        # ブックマーク済みの記事を除外（ユーザーが識別できる場合）
        bookmarked_subquery = db.query(Bookmark.document_id).filter(
            Bookmark.user_id == user_id
        ).subquery()
        personalized_query = personalized_query.filter(~Document.id.in_(db.query(bookmarked_subquery.c.document_id)))

        # Ordering: prefer documents with user-specific score, then those with guest score,
        # then others. Within scored docs prefer lower rank and higher score.
        ordering = [
            case((user_alias.id.isnot(None), 0), (guest_alias.id.isnot(None), 1), else_=2),
            case((user_alias.id.isnot(None), user_alias.rank), else_=guest_alias.rank).asc(),
            case((user_alias.id.isnot(None), user_alias.score), else_=guest_alias.score).desc(),
            Document.created_at.desc(),
        ]

        rows = personalized_query.order_by(*ordering).offset(offset).limit(limit).all()

        repo = PersonalizedScoreRepository(db)
        documents: List[Document] = []
        score_map = {}
        for row in rows:
            # row: (Document, user_alias_row | None, guest_alias_row | None)
            document = row[0]
            user_row = row[1]
            guest_row = row[2]
            documents.append(document)
            chosen = user_row if user_row is not None else guest_row
            if chosen is not None:
                score_map[document.id] = repo._row_to_dto(chosen)

        return documents, score_map

    # For guest users: only consider scores for the "guest" user
    score_alias = aliased(PersonalizedScore)
    join_condition = and_(
        score_alias.document_id == Document.id,
        or_(score_alias.user_id == GUEST_USER_ID, score_alias.user_id.is_(None))
    )
    personalized_query = query.outerjoin(score_alias, join_condition).add_entity(score_alias)

    ordering = [
        case((score_alias.id.isnot(None), 0), else_=1),
        score_alias.rank.asc(),
        score_alias.score.desc(),
        Document.created_at.desc(),
    ]

    rows = personalized_query.order_by(*ordering).offset(offset).limit(limit).all()

    repo = PersonalizedScoreRepository(db)
    documents: List[Document] = []
    score_map = {}
    for row in rows:
        document, score_row = row
        documents.append(document)
        if score_row is not None:
            score_map[document.id] = repo._row_to_dto(score_row)

    return documents, score_map


def _render_feedback_fragment(document_id: str, state: str, message: str) -> str:
    """Render a lightweight HTML snippet for HTMX swaps."""

    icon = "smile" if state == "submitted" else "info"
    base_classes = "flex items-center gap-2 text-xs font-medium rounded-lg px-3 py-2"
    if state == "submitted":
        palette = " bg-emerald/10 text-emerald-700 border border-emerald/30"
    else:
        palette = " bg-mist/70 text-graphite border border-mist"
    escaped_message = escape(message)
    return "".join(
        [
            f'<div class="{base_classes}{palette}" '
            f'data-personalized-feedback-container '
            f'data-document-id="{escape(document_id)}" '
            f'data-feedback-state="{escape(state)}" '
            f'data-feedback-message="{escaped_message}">',
            f'<i data-lucide="{icon}" class="w-4 h-4" aria-hidden="true"></i>',
            f'<span>{escaped_message}</span>',
            "</div>",
        ]
    )


@router.get("")
async def list_documents(
    request: Request,
    q: Optional[str] = Query(None, description="検索クエリ"),
    category: Optional[str] = Query(None, description="カテゴリフィルタ"),
    domain: Optional[str] = Query(None, description="ドメインフィルタ"),
    from_date: Optional[str] = Query(None, alias="from", description="開始日 (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, alias="to", description="終了日 (YYYY-MM-DD)"),
    sort: Optional[str] = Query("recent", description="ソート順 (recent|personalized)"),
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
            # Accept ISO and common RFC date formats
            from dateutil import parser as _dateutil_parser
            from_dt = _dateutil_parser.parse(from_date)
            query = query.filter(Document.created_at >= from_dt)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid from date format")
    
    if to_date:
        try:
            from dateutil import parser as _dateutil_parser
            to_dt = _dateutil_parser.parse(to_date)
            query = query.filter(Document.created_at <= to_dt)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid to date format")
    
    sort_mode = (sort or "recent").lower()
    use_personalized = sort_mode == "personalized"

    score_map = {}
    if use_personalized:
        # パーソナライズドソート時はuser_idを取得してブックマーク除外などを適用
        user_id = _resolve_user_id(request)
        documents, score_map = _fetch_personalized_documents(query, user_id, offset, limit, db)
    else:
        documents = query.order_by(Document.created_at.desc()).offset(offset).limit(limit).all()
    
    # 結果整形
    result = []
    display_rank = 1  # 表示用の連番rank
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
        
        score_dto = score_map.get(doc.id)
        if score_dto is not None:
            is_cold_start = bool(getattr(score_dto, "cold_start", False))
            rank_for_display = None
            if not is_cold_start:
                rank_for_display = display_rank
                display_rank += 1  # おすすめ記事の場合のみrankをインクリメント
            doc_data["personalized"] = {
                "score": score_dto.score,
                "rank": rank_for_display,
                "explanation": score_dto.explanation,
                "components": score_dto.components.to_dict(),
                "computed_at": score_dto.computed_at.isoformat(),
                "cold_start": is_cold_start,
            }

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
        "fetched_at": document.fetched_at.isoformat() if document.fetched_at else None,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None,
        "lang": document.lang,
        "content_md": document.content_md,
        "content_text": document.content_text,
        "hash": document.hash
    }

    # 要約フィールド
    result["short_summary"] = document.short_summary
    result["medium_summary"] = document.medium_summary
    
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


@router.post("/{document_id}/personalized-feedback")
async def submit_personalized_feedback(
    request: Request,
    document_id: str,
    db: Session = Depends(get_db)
):
    """Record "low relevance" feedback for personalized ranking."""

    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    payload: Dict[str, str] = {}
    content_type = request.headers.get("content-type", "") or ""
    try:
        if "application/json" in content_type:
            json_body = await request.json()
            if isinstance(json_body, dict):
                payload = {str(k): str(v) for k, v in json_body.items() if v is not None}
        else:
            form = await request.form()
            payload = {str(k): str(form.get(k)) for k in form.keys() if form.get(k) is not None}
    except Exception:
        payload = {}

    reason = (payload.get("reason") or "low_relevance").strip().lower()
    if reason != "low_relevance":
        raise HTTPException(status_code=400, detail="Unsupported feedback reason")

    session_token = payload.get("session_token") or request.headers.get("X-Feedback-Session")
    if session_token:
        session_token = str(session_token).strip()
    if session_token == "":
        session_token = None

    note = payload.get("note")
    metadata_keys = {"score", "rank", "cold_start"}
    metadata = {key: payload[key] for key in metadata_keys if key in payload}

    service = PersonalizedFeedbackService(db)
    result = service.submit_low_relevance(
        document=document,
        user_id=_resolve_user_id(request),
        session_token=session_token,
        note=note,
        metadata=metadata or None,
    )

    if result.created:
        state = "submitted"
        status_label = "accepted"
        message = "フィードバックありがとうございました。おすすめ改善に活用します。"
    else:
        state = "duplicate"
        status_label = "duplicate"
        duplicate_messages = {
            "duplicate_user": "すでに同じユーザーからフィードバックを受け付けています。",
            "duplicate_session": "このセッションではすでにフィードバック済みです。",
            "duplicate_constraint": "同じ内容のフィードバックを受け付けています。",
        }
        message = duplicate_messages.get(result.state, "すでにこのフィードバックを処理しました。")

    response_payload = {
        "status": status_label,
        "message": message,
        "state": state,
        "duplicate": not result.created,
        "document_id": document.id,
    }

    if request.headers.get("HX-Request"):
        fragment = _render_feedback_fragment(document.id, state, message)
        hx_trigger = "personalized-feedback:submitted" if result.created else "personalized-feedback:duplicate"
        response = HTMLResponse(content=fragment)
        response.headers["HX-Trigger"] = hx_trigger
        return response

    return JSONResponse(response_payload)


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
    
    # 埋め込みベースの類似度計算実装
    # 同じカテゴリの他のドキュメントを取得して類似度を計算
    
    similar_docs = []
    if document.classifications:
        category = document.classifications[0].primary_category
        similar_query = db.query(Document).join(Classification).filter(
            Classification.primary_category == category,
            Document.id != document_id
        ).limit(limit * 2)  # 類似度計算後にソートするため、多めに取得
        
        candidate_docs = similar_query.all()
        
        # 類似度を計算
        docs_with_similarity = calculate_document_similarity(document_id, candidate_docs, db)
        
        # 上位limit件を取得
        similar_docs = docs_with_similarity[:limit]
    
    # Format the documents for template
    formatted_docs = []
    for doc, similarity_score in similar_docs:
        formatted_docs.append({
            "id": doc.id,
            "title": doc.title,
            "url": doc.url,
            "domain": doc.domain,
            "created_at": doc.created_at.strftime('%Y年%m月%d日'),
            "similarity_score": similarity_score
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


@router.get("/{document_id}/pdf")
async def download_pdf(
    document_id: str,
    db: Session = Depends(get_db)
):
    """
    Download PDF file for a document.
    
    Returns the PDF file if available, otherwise raises 404.
    Includes security validations to prevent path traversal attacks.
    """
    from fastapi.responses import FileResponse, RedirectResponse
    from pathlib import Path
    from sqlalchemy import text
    import re
    
    # Fetch document from database
    result = db.execute(
        text("SELECT id, title, pdf_path FROM documents WHERE id = :id"),
        {"id": document_id}
    ).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc_id, title, pdf_path = result[0], result[1], result[2]
    
    # Check if PDF path exists
    if not pdf_path:
        raise HTTPException(status_code=404, detail="PDF not available for this document")

    # If pdf_path is an external URL, redirect to it
    if isinstance(pdf_path, str) and pdf_path.lower().startswith(('http://', 'https://')):
        # Use RedirectResponse so browser navigates to the external PDF URL
        return RedirectResponse(url=pdf_path)
    
    # Construct full file path
    base_dir = Path("data")
    full_path = base_dir / pdf_path
    
    # Security: Resolve paths and check that file is within data directory
    try:
        resolved_base = base_dir.resolve()
        resolved_full = full_path.resolve()
        
        # Check if resolved path is within base directory
        if not str(resolved_full).startswith(str(resolved_base)):
            raise HTTPException(status_code=403, detail="Access denied")
    except Exception as e:
        raise HTTPException(status_code=403, detail="Invalid file path")
    
    # Check if file exists
    if not resolved_full.exists() or not resolved_full.is_file():
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    # Generate safe filename from title
    # Remove non-alphanumeric characters except spaces, hyphens, underscores
    safe_title = re.sub(r'[^\w\s\-]', '', title)
    safe_title = re.sub(r'\s+', '_', safe_title)  # Replace spaces with underscores
    # Limit filename length
    safe_title = safe_title[:100] if len(safe_title) > 100 else safe_title
    # Ensure filename is not empty
    if not safe_title:
        safe_title = document_id
    
    filename = f"{safe_title}.pdf"
    
    # Return file with appropriate headers
    return FileResponse(
        path=str(resolved_full),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )