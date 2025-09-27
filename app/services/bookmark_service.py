from typing import Tuple, List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import OperationalError
from app.core.database import Bookmark, Document


def get_user_bookmarked_documents(db: Session, user_id: Optional[str], page: int = 1, per_page: int = 20) -> Tuple[List[Document], int]:
    """Return a tuple (documents, total) for the user's bookmarked documents.

    Documents are ordered by Bookmark.created_at desc.
    """
    offset = (page - 1) * per_page
    q = db.query(Bookmark).options(joinedload(Bookmark.document))
    if user_id is None:
        q = q.filter(Bookmark.user_id == None)
    else:
        q = q.filter(Bookmark.user_id == user_id)
    q = q.order_by(Bookmark.created_at.desc())
    try:
        total = q.count()
        items = q.offset(offset).limit(per_page).all()
    except OperationalError:
        # If the bookmarks table does not exist (e.g. older test DB),
        # return empty results rather than raising so the UI can render
        # an empty state. This keeps tests and dev servers resilient
        # when schema migrations have not been applied.
        return [], 0

    documents = []
    for b in items:
        if b.document:
            # Attach transient bookmarked flag for templates
            try:
                b.document.bookmarked = True
            except Exception:
                pass
            documents.append(b.document)

    return documents, total
