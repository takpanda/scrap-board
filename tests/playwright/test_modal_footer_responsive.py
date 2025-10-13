# Playwright E2E: モーダルフッターのレスポンシブ検証
import re
import pytest
from playwright.sync_api import Page, expect
from sqlalchemy.orm import Session

from app.core.database import Document, Classification, create_tables
from app.core import database as app_db
from datetime import datetime, timezone


@pytest.fixture()
def test_document():
    """tests/test_modal_interaction.py と同様のテストドキュメント作成フィクスチャ"""
    create_tables()
    session = app_db.SessionLocal()
    document = Document(
        id="test-modal-doc-footer",
        title="モーダルフッターテスト記事",
        url="https://example.com/modal-footer-test",
        domain="example.com",
        content_md="# モーダルフッターテスト\n\nこれはモーダルのテストです。",
        content_text="モーダルフッターテスト\n\nこれはモーダルのテストです。",
        short_summary="モーダルフッターテスト記事の要約",
        hash="test-modal-footer-hash",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc)
    )
    session.add(document)

    classification = Classification(
        document_id="test-modal-doc-footer",
        primary_category="テスト",
        topics=["モーダル"],
        tags=["playwright", "e2e"],
        confidence=0.9,
        method="manual"
    )
    session.add(classification)

    session.commit()
    session.refresh(document)

    yield document

    # cleanup
    session.query(Classification).filter(Classification.document_id == "test-modal-doc-footer").delete()
    session.query(Document).filter(Document.id == "test-modal-doc-footer").delete()
    session.commit()
    session.close()


@pytest.mark.playwright
def test_modal_footer_padding_and_touch_targets_on_mobile(page: Page, test_document, live_server):
    """モバイルビューポートでフッターのパディングがp-4で、フッターボタンが44x44以上であることを検証する"""
    # iPhone SE相当のビューポート
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto(f"{live_server}/documents")
    page.wait_for_load_state("networkidle")

    # モーダルを開く
    page.locator('a:has-text("詳細を見る")').first.click()
    page.wait_for_selector("[data-modal-dialog]", state="visible")

    # フッター要素を取得
    footer = page.locator('[data-modal-dialog] > .flex.items-center.justify-between.border-t').first
    # padding を取得
    computed = footer.evaluate('el => window.getComputedStyle(el).padding')
    # モバイルでは p-4 (1rem = 16px) のはず
    assert "16px" in computed

    # フッターボタンのサイズ検証
    buttons = footer.locator('button, a')
    count = buttons.count()
    assert count > 0
    for i in range(count):
        box = buttons.nth(i).bounding_box()
        assert box['width'] >= 44
        assert box['height'] >= 44
