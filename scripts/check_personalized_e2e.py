"""E2E check for personalized documents rendering.

Checks:
- GET /documents?sort=personalized returns HTML with article elements having
  data-personalized-* attributes (when personalized scores exist)
- GET /api/documents?sort=personalized returns JSON with 'personalized' entries

Run: python scripts/check_personalized_e2e.py
"""
from __future__ import annotations

import re
import json
from typing import List

from fastapi.testclient import TestClient

import app.main as main_app

client = TestClient(main_app.app)

ARTICLE_RE = re.compile(r"<article[^>]+data-document-id=[\"'](?P<id>[^\"']+)[\"'][^>]*>", re.I)


def fetch_html() -> str:
    r = client.get("/documents?sort=personalized")
    r.raise_for_status()
    return r.text


def fetch_api() -> dict:
    r = client.get("/api/documents?sort=personalized")
    r.raise_for_status()
    return r.json()


def extract_articles(html: str) -> List[str]:
    return ARTICLE_RE.findall(html)


def check_personalized_attrs(html: str) -> dict:
    results = {"checked": 0, "with_personalized_attrs": 0, "with_fallback": 0}
    # find article blocks
    articles = re.finditer(r"(<article[^>]+data-document-id=[\"'](?P<id>[^\"']+)[\"'][^>]*>)(?P<body>.*?)</article>", html, re.I | re.S)
    for m in articles:
        results["checked"] += 1
        body = m.group("body")
        if re.search(r"data-personalized-score=", m.group(1) + body):
            results["with_personalized_attrs"] += 1
        if re.search(r"data-personalized-fallback", m.group(1) + body):
            results["with_fallback"] += 1
    return results


def main() -> None:
    print("Fetching HTML /documents?sort=personalized ...")
    html = fetch_html()
    article_ids = extract_articles(html)
    print(f"Found {len(article_ids)} <article> elements")
    attrs_summary = check_personalized_attrs(html)
    print("HTML check summary:", json.dumps(attrs_summary, ensure_ascii=False))

    print("\nFetching API /api/documents?sort=personalized ...")
    data = fetch_api()
    docs = data.get("documents") or data.get("results") or []
    personalized_count = sum(1 for d in docs if d.get("personalized") is not None)
    print(f"API returned {len(docs)} documents, {personalized_count} have 'personalized' field")

    # quick consistency check: if API has personalized entries, HTML should have attributes
    if personalized_count > 0 and attrs_summary["with_personalized_attrs"] == 0:
        print("WARNING: API has personalized data but HTML has no personalized attributes")
    else:
        print("HTML/API consistency appears OK (basic check)")


if __name__ == "__main__":
    main()
