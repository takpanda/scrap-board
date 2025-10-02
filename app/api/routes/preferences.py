"""嗜好分析APIエンドポイント"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.user_utils import normalize_user_id
from app.services.preference_analysis import PreferenceAnalysisService
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

router = APIRouter()


def _resolve_user_id(request: Request) -> str:
    """リクエストからユーザーIDを解決、未特定時は'guest'を返す"""
    user = getattr(request.state, "user", None)
    if user is not None:
        user_id = getattr(user, "id", None) or getattr(user, "user_id", None)
        if user_id:
            return normalize_user_id(str(user_id))

    header_user = request.headers.get("X-User-Id")
    if header_user:
        return normalize_user_id(header_user)

    return normalize_user_id(None)


@router.get("/api/preferences/analysis")
async def get_preference_analysis(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    ブックマーク嗜好分析データをJSON形式で取得

    Returns:
        {
            "top_topics": [{"name": str, "count": int, "percentage": float}],
            "top_keywords": [{"keyword": str, "count": int}],
            "top_articles": [{"title": str, "domain": str, ...}],
            "recent_bookmarks": [{"title": str, "bookmarked_at": str, ...}],
            "summary": {"total_bookmarks": int, ...}
        }
    """
    user_id = _resolve_user_id(request)
    service = PreferenceAnalysisService()
    
    analysis = service.analyze_preferences(db, user_id)
    
    return JSONResponse(content=analysis)


@router.get("/preferences", response_class=HTMLResponse)
async def preferences_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    嗜好分析画面を表示
    """
    user_id = _resolve_user_id(request)
    service = PreferenceAnalysisService()
    
    analysis = service.analyze_preferences(db, user_id)
    
    return templates.TemplateResponse(
        "preferences.html",
        {
            "request": request,
            "analysis": analysis,
        },
    )
