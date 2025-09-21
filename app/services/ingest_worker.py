import logging
import json
from typing import Any, Dict, Optional
from datetime import datetime
import uuid

import httpx
from sqlalchemy import text
from urllib.parse import urljoin, urlparse
import os
from pathlib import Path

try:
    from PIL import Image
    from io import BytesIO
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

from app.core.database import SessionLocal
from app.services.extractor import content_extractor
from app.services.postprocess import kick_postprocess_async

logger = logging.getLogger(__name__)


def _insert_document_if_new(db, doc: Dict[str, Any], source_name: str):
    """Insert document into `documents` if not already present.

    - Skip insert when the same `url` already exists.
    - Otherwise, if a `hash` is present, skip when the same `hash` exists.
    - Insert is done transactionally and returns the new `id` or `None` when skipped/failed.
    """
    now = datetime.utcnow()
    # prefer provided id, otherwise generate
    doc_id = doc.get("id") or str(uuid.uuid4())

    # 1) check by URL to avoid duplicate URLs
    url = doc.get("url")
    if url:
        existing_by_url = db.execute(text("SELECT id FROM documents WHERE url = :url"), {"url": url}).fetchone()
        if existing_by_url:
            logger.info("Skipping insert — url already exists: %s (id=%s)", url, existing_by_url[0])
            return None

    # 2) check by hash to avoid near-duplicates when different URLs
    doc_hash = doc.get("hash")
    if doc_hash:
        existing_by_hash = db.execute(text("SELECT id, url FROM documents WHERE hash = :hash"), {"hash": doc_hash}).fetchone()
        if existing_by_hash:
            logger.info("Skipping insert — hash already exists: %s (id=%s url=%s)", doc_hash, existing_by_hash[0], existing_by_hash[1])
            return None

    insert_sql = text(
        """
        INSERT INTO documents (id, url, domain, title, author, published_at, content_md, content_text, hash, lang, created_at, updated_at, source, original_url, thumbnail_url, fetched_at)
        VALUES (:id, :url, :domain, :title, :author, :published_at, :content_md, :content_text, :hash, :lang, :created_at, :updated_at, :source, :original_url, :thumbnail_url, :fetched_at)
        """
    )

    params = {
        "id": doc_id,
        "url": url,
        "domain": doc.get("domain"),
        "title": doc.get("title"),
        "author": doc.get("author"),
        "published_at": doc.get("published_at"),
        "content_md": doc.get("content_md"),
        "content_text": doc.get("content_text"),
        "hash": doc_hash,
        "lang": doc.get("lang"),
        "created_at": now,
        "updated_at": now,
        "source": source_name,
        "original_url": doc.get("original_url") or url,
        "thumbnail_url": doc.get("thumbnail_url"),
        "fetched_at": doc.get("fetched_at") or now,
    }

    try:
        db.execute(insert_sql, params)
        db.commit()
        logger.info("Inserted document %s %s", doc_id, url)
        try:
            # kick post-processing (summary + embedding) asynchronously
            kick_postprocess_async(doc_id)
        except Exception:
            logger.exception("Failed to kick postprocess for %s", doc_id)
        return doc_id
    except Exception:
        db.rollback()
        logger.exception("Failed to insert document for %s", url)
        return None


def _fetch_qiita_items(config: Dict[str, Any]):
    """Fetch recent items from Qiita according to config.

    Expected config keys:
    - `user`: Qiita user ID to fetch recent items for
    - `tag`: tag to filter by (optional)
    - `per_page`: number of items to fetch
    """
    items = []
    base = "https://qiita.com/api/v2"
    per_page = config.get("per_page", 20)
    try:
        if config.get("user"):
            url = f"{base}/users/{config['user']}/items"
            params = {"per_page": per_page}
            if config.get("tag"):
                params["query"] = f"tag:{config['tag']}"
        elif config.get("tag"):
            url = f"{base}/items"
            params = {"per_page": per_page, "query": f"tag:{config['tag']}"}
        else:
            url = f"{base}/items"
            params = {"per_page": per_page}

        with httpx.Client(timeout=30.0) as client:
            r = client.get(url, params=params, headers={"User-Agent": "Scrap-Board/1.0"})
            r.raise_for_status()
            items = r.json()
    except Exception as e:
        logger.error(f"Qiita fetch error: {e}")

    return items


def _ensure_thumbnail_for_url(db, url: str) -> Optional[str]:
    """Try to download favicon or og:image for `url`, resize to 64x64 and store under `data/assets/thumbnails/`.

    Returns relative thumbnail path (e.g. 'assets/thumbnails/<fname>') or None.
    """
    if not url or not PIL_AVAILABLE:
        if not PIL_AVAILABLE:
            logger.warning("Pillow not available; thumbnail generation skipped")
        return None

    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    thumb_dir = Path("data/assets/thumbnails")
    thumb_dir.mkdir(parents=True, exist_ok=True)

    candidates = []
    # 1) favicon.ico
    candidates.append(urljoin(base, "/favicon.ico"))

    # 2) attempt to fetch page and look for <meta property="og:image"> or <link rel="icon">
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(url)
            if r.status_code == 200:
                html = r.text
                # naive parse for og:image
                import re

                m = re.search(r"<meta[^>]+property=[\"']og:image[\"'][^>]+content=[\"']([^\"']+)[\"']", html, re.I)
                if m:
                    img = m.group(1)
                    if img.startswith("//"):
                        img = f"{parsed.scheme}:{img}"
                    elif img.startswith("/"):
                        img = urljoin(base, img)
                    candidates.append(img)
                # link rel icons
                m2 = re.search(r"<link[^>]+rel=[\"'](?:icon|shortcut icon)[\"'][^>]+href=[\"']([^\"']+)[\"']", html, re.I)
                if m2:
                    icon = m2.group(1)
                    if icon.startswith("/"):
                        icon = urljoin(base, icon)
                    candidates.append(icon)
    except Exception:
        logger.debug("Could not fetch page to discover images for %s", url)

    # Try candidates in order
    for c in candidates:
        try:
            with httpx.Client(timeout=15.0) as client:
                rr = client.get(c)
                if rr.status_code != 200 or 'image' not in rr.headers.get('content-type',''):
                    continue
                # resize via Pillow
                img = Image.open(BytesIO(rr.content)).convert('RGBA')
                img = img.resize((64,64), Image.LANCZOS)
                fname = f"thumb_{abs(hash(c))}.png"
                path = thumb_dir / fname
                img.save(path, format='PNG')
                rel = os.path.join('assets','thumbnails', fname)
                return rel
        except Exception:
            logger.debug("Failed to fetch/resize candidate %s", c)

    return None


def _fetch_hatena_items(config: Dict[str, Any]):
    """Fetch recent items from Hatena Bookmark.

    Supported config keys:
    - `user`: hatena user id (will try RSS at https://b.hatena.ne.jp/{user}/rss)
    - `per_page`: maximum items to return (best-effort)
    If feedparser is not available or fetch fails, returns empty list.
    """
    items = []
    per_page = config.get("per_page", 20)
    try:
        import feedparser

        if config.get("user"):
            url = f"https://b.hatena.ne.jp/{config['user']}/rss"
        elif config.get("url"):
            url = config["url"]
        else:
            # generic hot entries endpoint (best-effort)
            url = "https://b.hatena.ne.jp/entrylist.rss"

        parsed = feedparser.parse(url)
        for e in parsed.entries[:per_page]:
            items.append({
                "link": e.get("link"),
                "title": e.get("title"),
                "published": e.get("published"),
                "summary": e.get("summary", ""),
            })
    except ModuleNotFoundError:
        logger.warning("feedparser not installed; Hatena RSS fetch skipped")
    except Exception as e:
        logger.error(f"Hatena fetch error: {e}")

    return items


def _fetch_rss_items(config: Dict[str, Any]):
    """Fetch items from an arbitrary RSS/Atom feed.

    Expected config:
    - `url`: feed URL
    - `per_page`: number of entries to fetch
    """
    items = []
    feed_url = config.get("url")
    if not feed_url:
        logger.warning("RSS source missing `url` in config")
        return items

    per_page = config.get("per_page", 20)
    try:
        import feedparser

        parsed = feedparser.parse(feed_url)
        for e in parsed.entries[:per_page]:
            items.append({
                "link": e.get("link"),
                "title": e.get("title"),
                "published": e.get("published"),
                "summary": e.get("summary", ""),
            })
    except ModuleNotFoundError:
        logger.warning("feedparser not installed; RSS fetch skipped")
    except Exception as e:
        logger.error(f"RSS fetch error: {e}")

    return items


def trigger_fetch_for_source(source_id: int):
    """Fetch entries for a given source and push to ingest pipeline.

    Currently implements Qiita fetcher. Other source types may be added.
    """
    db = SessionLocal()
    try:
        row = db.execute(text("SELECT id, name, type, config FROM sources WHERE id=:id"), {"id": source_id}).fetchone()
        if not row:
            logger.warning(f"Source {source_id} not found")
            return

        sid, name, stype, config_raw = row[0], row[1], row[2], row[3]
        logger.info(f"Fetching entries for source {sid} ({stype})")

        try:
            config = json.loads(config_raw) if config_raw else {}
        except Exception:
            config = {}

        if stype == "qiita":
            items = _fetch_qiita_items(config)
            for it in items:
                # Qiita item has `url`, `title`, `body` (markdown), `user` etc.
                url = it.get("url") or it.get("id")
                # Use extractor to normalize / re-extract content where possible
                extracted = None
                try:
                    # synchronous call to async extractor via running loop
                    import asyncio

                    extracted = asyncio.get_event_loop().run_until_complete(content_extractor.extract_from_url(url))
                except Exception as e:
                    logger.warning(f"Extractor failed for {url}: {e}")

                if not extracted:
                    # fallback to using Qiita-provided fields
                    content_md = it.get("body") or ""
                    content_text = content_md
                    content_hash = hashlib_sha256(content_text)
                    extracted = {
                        "url": url,
                        "domain": "qiita.com",
                        "title": it.get("title") or "無題",
                        "author": it.get("user", {}).get("id") if it.get("user") else None,
                        "published_at": it.get("created_at"),
                        "content_md": content_md,
                        "content_text": content_text,
                        "hash": content_hash,
                        "lang": "ja",
                    }

                # Ensure thumbnail if missing
                if not extracted.get("thumbnail_url"):
                    try:
                        thumb = _ensure_thumbnail_for_url(db, extracted.get("url"))
                        if thumb:
                            extracted["thumbnail_url"] = thumb
                    except Exception:
                        logger.debug("Thumbnail generation failed for %s", extracted.get("url"))

                # Insert if new
                try:
                    _insert_document_if_new(db, extracted, name)
                except Exception as e:
                    logger.error(f"Failed to insert document for {url}: {e}")
        elif stype == "hatena":
            items = _fetch_hatena_items(config)
            for it in items:
                url = it.get("link")
                extracted = None
                try:
                    import asyncio

                    extracted = asyncio.get_event_loop().run_until_complete(content_extractor.extract_from_url(url))
                except Exception as e:
                    logger.warning(f"Extractor failed for {url}: {e}")

                if not extracted:
                    content_text = it.get("summary") or ""
                    content_hash = hashlib_sha256(content_text)
                    extracted = {
                        "url": url,
                        "domain": "b.hatena.ne.jp",
                        "title": it.get("title") or "無題",
                        "author": None,
                        "published_at": it.get("published"),
                        "content_md": content_text,
                        "content_text": content_text,
                        "hash": content_hash,
                        "lang": "ja",
                    }

                # Ensure thumbnail if missing
                if not extracted.get("thumbnail_url"):
                    try:
                        thumb = _ensure_thumbnail_for_url(db, extracted.get("url"))
                        if thumb:
                            extracted["thumbnail_url"] = thumb
                    except Exception:
                        logger.debug("Thumbnail generation failed for %s", extracted.get("url"))

                try:
                    _insert_document_if_new(db, extracted, name)
                except Exception as e:
                    logger.error(f"Failed to insert Hatena document for {url}: {e}")
        elif stype == "rss":
            items = _fetch_rss_items(config)
            for it in items:
                url = it.get("link")
                extracted = None
                try:
                    import asyncio

                    extracted = asyncio.get_event_loop().run_until_complete(content_extractor.extract_from_url(url))
                except Exception as e:
                    logger.warning(f"Extractor failed for {url}: {e}")

                if not extracted:
                    content_text = it.get("summary") or ""
                    content_hash = hashlib_sha256(content_text)
                    extracted = {
                        "url": url,
                        "domain": (url.split('/')[2] if url and '//' in url else 'rss'),
                        "title": it.get("title") or "無題",
                        "author": None,
                        "published_at": it.get("published"),
                        "content_md": content_text,
                        "content_text": content_text,
                        "hash": content_hash,
                        "lang": "ja",
                    }

                # Ensure thumbnail if missing
                if not extracted.get("thumbnail_url"):
                    try:
                        thumb = _ensure_thumbnail_for_url(db, extracted.get("url"))
                        if thumb:
                            extracted["thumbnail_url"] = thumb
                    except Exception:
                        logger.debug("Thumbnail generation failed for %s", extracted.get("url"))

                try:
                    _insert_document_if_new(db, extracted, name)
                except Exception as e:
                    logger.error(f"Failed to insert RSS document for {url}: {e}")
        else:
            logger.info(f"Source type {stype} not implemented yet")
    finally:
        db.close()


def hashlib_sha256(text: str) -> str:
    import hashlib as _hashlib

    return _hashlib.sha256((text or "").encode("utf-8")).hexdigest()
