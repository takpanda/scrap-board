"""Playwright E2E: モーダルのキーボードフォーカス可視化（アクセシビリティ）テスト"""
import pytest
from playwright.sync_api import Page, expect
from datetime import datetime, timezone

from app.core.database import Document, Classification, create_tables
from app.core import database as app_db


@pytest.fixture()
def test_document():
    create_tables()
    session = app_db.SessionLocal()
    doc = Document(
        id="test-modal-doc-a11y",
        title="モーダルアクセシビリティテスト",
        url="https://example.com/modal-a11y",
        domain="example.com",
        content_md="# アクセシビリティテスト\n\nフォーカスの確認",
        content_text="アクセシビリティテスト",
        short_summary="アクセシビリティテスト要約",
        hash="test-modal-a11y-hash",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc)
    )
    session.add(doc)
    classification = Classification(
        document_id="test-modal-doc-a11y",
        primary_category="テスト",
        topics=["a11y"],
        tags=["playwright", "a11y"],
        confidence=0.9,
        method="manual"
    )
    session.add(classification)
    session.commit()
    session.refresh(doc)
    yield doc

    # cleanup
    session.query(Classification).filter(Classification.document_id == "test-modal-doc-a11y").delete()
    session.query(Document).filter(Document.id == "test-modal-doc-a11y").delete()
    session.commit()
    session.close()


@pytest.mark.playwright
def test_modal_keyboard_focus_outline(page: Page, test_document, live_server):
    """モーダルが開いた後、キーボードフォーカス要素にフォーカスインジケータが表示されることを検証する"""
    # モバイルビューポートで確認（仕様の対象）
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto(f"{live_server}/documents")
    page.wait_for_load_state("networkidle")

    # モーダルを開く
    page.locator('a:has-text("詳細を見る")').first.click()
    page.wait_for_selector('[data-modal-dialog]', state='visible')

    # モーダルが開いた直後にフォーカスが移動しているはず
    # activeElement の outline スタイルを取得して、無効（none/0px）でないことを確認
    result = page.evaluate(
        "() => { const el = document.activeElement; if (!el) return null; const cs = window.getComputedStyle(el); return { tag: el.tagName, outlineStyle: cs.outlineStyle, outlineWidth: cs.outlineWidth }; }"
    )
    assert result is not None, "フォーカス要素が存在しません"
    # outline が none でなく、幅が 0px でないことを期待する
    assert result["outlineStyle"] != 'none' or result["outlineWidth"] != '0px', f"フォーカスインジケータが表示されていません: {result}"
