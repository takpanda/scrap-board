from typing import Tuple, List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import OperationalError
from app.core.database import Bookmark, Document


def get_user_bookmarked_documents(
    db: Session,
    user_id: Optional[str],
    page: int = 1,
    per_page: int = 20
) -> Tuple[List[Document], int]:
    """Return a tuple (documents, total) for the user's bookmarked documents.

    Documents are ordered by Bookmark.created_at desc and include transient
    bookmark metadata (bookmark_id, bookmarked_at, bookmark_note).
    """
    # Clamp page/per_page to sane values in case other callers pass invalid numbers.
    try:
        safe_page = max(int(page), 1)
    except Exception:
        safe_page = 1

    try:
        safe_per_page = max(min(int(per_page), 200), 1)
    except Exception:
        safe_per_page = 20

    offset = (safe_page - 1) * safe_per_page

    q = db.query(Bookmark).options(
        joinedload(Bookmark.document).joinedload(Document.classifications)
    )

    if user_id is None:
        q = q.filter(Bookmark.user_id == None)  # noqa: E711 - intentional SQL NULL comparison
    else:
        q = q.filter(Bookmark.user_id == user_id)

    q = q.order_by(Bookmark.created_at.desc())

    try:
        total = q.count()
        items = q.offset(offset).limit(safe_per_page).all()
    except OperationalError:
        # If the bookmarks table does not exist (e.g. older test DB),
        # return empty results rather than raising so the UI can render
        # an empty state. This keeps tests and dev servers resilient
        # when schema migrations have not been applied.
        return [], 0

    documents: List[Document] = []
    for bookmark in items:
        document = bookmark.document
        if not document:
            # Skip bookmarks without a document (possible if doc was deleted).
            continue

        # Attach transient bookmark metadata for template usage.
        try:
            document.bookmarked = True
            document.bookmark_id = bookmark.id
            document.bookmark_note = bookmark.note
            document.bookmark_created_at = bookmark.created_at
        except Exception:
            # Transient attributes are best-effort.
            pass

        documents.append(document)

    return documents, total
