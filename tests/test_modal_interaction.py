"""
モーダルのインタラクション機能のE2Eテスト
"""
import pytest
from playwright.sync_api import Page, expect
from sqlalchemy.orm import Session

from app.core.database import Document, Classification, create_tables
from app.core import database as app_db
from datetime import datetime, timezone


@pytest.fixture()
def db_session():
    """DBセッションのフィクスチャ"""
    create_tables()
    session = app_db.SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_document(db_session: Session):
    """テスト用の記事データを作成"""
    document = Document(
        id="test-modal-doc",
        title="モーダルテスト記事",
        url="https://example.com/modal-test",
        domain="example.com",
        content_md="# モーダルテスト\n\nこれはモーダルのテストです。",
        content_text="モーダルテスト\n\nこれはモーダルのテストです。",
        short_summary="モーダルテスト記事の要約",
        hash="test-modal-hash",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc)
    )
    db_session.add(document)

    classification = Classification(
        document_id="test-modal-doc",
        primary_category="テスト",
        topics=["モーダル"],
        tags=["playwright", "e2e"],
        confidence=0.9,
        method="manual"
    )
    db_session.add(classification)

    db_session.commit()
    db_session.refresh(document)

    yield document

    # クリーンアップ
    db_session.query(Classification).filter(Classification.document_id == "test-modal-doc").delete()
    db_session.query(Document).filter(Document.id == "test-modal-doc").delete()
    db_session.commit()


@pytest.mark.playwright
def test_modal_opens_and_displays_content(page: Page, test_document):
    """モーダルが開いて記事コンテンツが表示される"""
    # 記事一覧ページを開く
    page.goto("http://localhost:8000/documents")
    page.wait_for_load_state("networkidle")

    # モーダルコンテナが非表示であることを確認
    modal_container = page.locator("#modal-container")
    expect(modal_container).to_have_class(lambda c: "hidden" in c)

    # 詳細を見るボタンをクリック
    detail_button = page.locator('a:has-text("詳細を見る")').first
    detail_button.click()

    # モーダルが表示されることを確認
    page.wait_for_selector("#modal-container:not(.hidden)", timeout=5000)
    expect(modal_container).not_to_have_class(lambda c: "hidden" in c)

    # モーダル内にタイトルが表示されることを確認
    expect(page.locator("#modal-container")).to_contain_text("モーダルテスト記事")


@pytest.mark.playwright
def test_modal_closes_with_close_button(page: Page, test_document):
    """閉じるボタンでモーダルが閉じる"""
    page.goto("http://localhost:8000/documents")
    page.wait_for_load_state("networkidle")

    # モーダルを開く
    page.locator('a:has-text("詳細を見る")').first.click()
    page.wait_for_selector("#modal-container:not(.hidden)")

    # 閉じるボタンをクリック
    close_button = page.locator('[data-modal-close]').first
    close_button.click()

    # モーダルが閉じることを確認
    page.wait_for_selector("#modal-container.hidden", timeout=3000)
    modal_container = page.locator("#modal-container")
    expect(modal_container).to_have_class(lambda c: "hidden" in c)


@pytest.mark.playwright
def test_modal_closes_with_escape_key(page: Page, test_document):
    """ESCキーでモーダルが閉じる"""
    page.goto("http://localhost:8000/documents")
    page.wait_for_load_state("networkidle")

    # モーダルを開く
    page.locator('a:has-text("詳細を見る")').first.click()
    page.wait_for_selector("#modal-container:not(.hidden)")

    # ESCキーを押す
    page.keyboard.press("Escape")

    # モーダルが閉じることを確認
    page.wait_for_selector("#modal-container.hidden", timeout=3000)
    modal_container = page.locator("#modal-container")
    expect(modal_container).to_have_class(lambda c: "hidden" in c)


@pytest.mark.playwright
def test_modal_closes_with_overlay_click(page: Page, test_document):
    """背景オーバーレイクリックでモーダルが閉じる"""
    page.goto("http://localhost:8000/documents")
    page.wait_for_load_state("networkidle")

    # モーダルを開く
    page.locator('a:has-text("詳細を見る")').first.click()
    page.wait_for_selector("#modal-container:not(.hidden)")

    # オーバーレイ（モーダルコンテナの背景）をクリック
    # モーダルダイアログの外をクリック
    modal_container = page.locator("#modal-container")
    box = modal_container.bounding_box()
    # コンテナの左上をクリック（ダイアログの外側）
    page.mouse.click(box["x"] + 10, box["y"] + 10)

    # モーダルが閉じることを確認
    page.wait_for_selector("#modal-container.hidden", timeout=3000)
    expect(modal_container).to_have_class(lambda c: "hidden" in c)


@pytest.mark.playwright
def test_background_scroll_disabled_when_modal_open(page: Page, test_document):
    """モーダル表示中は背景のスクロールが無効化される"""
    page.goto("http://localhost:8000/documents")
    page.wait_for_load_state("networkidle")

    # 初期状態のbody overflowを確認
    initial_overflow = page.evaluate("document.body.style.overflow")
    assert initial_overflow in ["", "auto", "visible"]

    # モーダルを開く
    page.locator('a:has-text("詳細を見る")').first.click()
    page.wait_for_selector("#modal-container:not(.hidden)")

    # overflow: hidden が設定されることを確認
    overflow_when_open = page.evaluate("document.body.style.overflow")
    assert overflow_when_open == "hidden"

    # モーダルを閉じる
    page.locator('[data-modal-close]').first.click()
    page.wait_for_selector("#modal-container.hidden")

    # overflowが復元されることを確認
    overflow_after_close = page.evaluate("document.body.style.overflow")
    assert overflow_after_close in ["", "auto", "visible"]
