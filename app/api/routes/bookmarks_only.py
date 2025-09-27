from fastapi import APIRouter, Depends, Request, Query, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
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
async def bookmarks_only_page(request: Request, page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    # Obtain current user from request.state or dependency. The project uses
    # anonymous bookmarks in some tests; attempt to read request.state.user if present.
    user = getattr(request.state, "user", None)
    # Show anonymous bookmarks when user is not present (the app stores some
    # bookmarks with user_id == NULL). Call service with user_id=None in that case.
    uid = user.id if user else None
    documents, total = get_user_bookmarked_documents(db, user_id=uid, page=page, per_page=per_page)

    return templates.TemplateResponse("bookmarks_only.html", {
        "request": request,
        "documents": documents,
        "page": page,
        "per_page": per_page,
        "total": total
    })
