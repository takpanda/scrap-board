from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional
from math import ceil

from app.core.database import get_db
from app.core.user_utils import normalize_user_id
from app.services.bookmark_service import get_user_bookmarked_documents
from fastapi.templating import Jinja2Templates
from markdown_it import MarkdownIt
from datetime import timezone, timedelta
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

templates = Jinja2Templates(directory="app/templates")

# register minimal filters used by the template if not already present
md = MarkdownIt()
def markdown_filter(text):
    if not text:
        return ""
    return md.render(text)

def to_jst(dt, fmt="%Y年%m月%d日 %H:%M"):
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

templates.env.filters.setdefault("markdown", markdown_filter)
templates.env.filters.setdefault("to_jst", to_jst)

router = APIRouter()


@router.get("/bookmarks", response_class=HTMLResponse)
async def bookmarks_only_page(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    # Resolve current user. Authentication middleware should populate request.state.user;
    # for tests/local tooling allow header override.
    uid = _resolve_user_id(request)

    # Fetch bookmarks. When page is out of range but bookmarks exist, snap to last page.
    documents, total = get_user_bookmarked_documents(db, user_id=uid, page=page, per_page=per_page)

    if page > 1 and not documents and total > 0:
        last_page = max(1, ceil(total / per_page))
        if last_page != page:
            documents, total = get_user_bookmarked_documents(db, user_id=uid, page=last_page, per_page=per_page)
            page = last_page

    last_page = max(1, ceil(total / per_page)) if total else 1
    has_previous = page > 1
    has_next = (page * per_page) < total
    start_index = (page - 1) * per_page + 1 if total else 0
    end_index = start_index + len(documents) - 1 if documents else 0

    return templates.TemplateResponse(
        "bookmarks_only.html",
        {
            "request": request,
            "documents": documents,
            "page": page,
            "per_page": per_page,
            "total": total,
            "last_page": last_page,
            "has_previous": has_previous,
            "has_next": has_next,
            "start_index": start_index,
            "end_index": end_index,
        },
    )


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
