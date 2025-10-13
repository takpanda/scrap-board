#!/usr/bin/env python3
"""
簡易デモ用ドキュメントを SQLite DB に挿入するスクリプト
開発サーバが動作している状態で実行してください。
"""
from datetime import datetime, timezone
import sys
from pathlib import Path

# Ensure project root is importable when running this script directly
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.database import Document, Classification, create_tables
from app.core import database as app_db


def seed():
    create_tables()
    session = app_db.SessionLocal()

    doc_id = "demo-seed-doc-1"
    # 既存なら上書きのため一旦削除
    session.query(Classification).filter(Classification.document_id == doc_id).delete()
    session.query(Document).filter(Document.id == doc_id).delete()
    session.commit()

    document = Document(
        id=doc_id,
        title="デモ記事: モバイルモーダルテスト",
        url="https://example.com/demo-mobile-modal",
        domain="example.com",
        content_md="# デモコンテンツ\n\nこれはテスト用のデモ記事です。ラベルを長めにして省略を確認します。",
        content_text="デモコンテンツ - これはテスト用のデモ記事です。",
        short_summary="モバイルモーダルのデモ記事",
        hash="demo-seed-hash-1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc)
    )
    session.add(document)

    classification = Classification(
        document_id=doc_id,
        primary_category="テスト長いカテゴリ名を入れて省略を確認するためのカテゴリ名テスト",
        topics=["モーダル", "レスポンシブ"],
        tags=["very-long-tag-name-for-testing-overflow-behavior", "e2e", "playwright"],
        confidence=0.95,
        method="manual"
    )
    session.add(classification)

    session.commit()
    session.close()
    print(f"Seeded demo document {doc_id}")


if __name__ == "__main__":
    seed()
