"""
モーダルのインタラクション機能のE2Eテスト
"""
import re
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
def test_modal_opens_and_displays_content(page: Page, test_document, live_server):
    """モーダルが開いて記事コンテンツが表示される"""
    # ディープリンクで直接テスト記事のモーダルを開く
    page.goto(f"{live_server}/documents?doc={test_document.id}")
    page.wait_for_load_state("networkidle")

    # modal.jsとHTMXの初期化を待つ
    page.wait_for_function("typeof window.modalManager !== 'undefined' && typeof window.htmx !== 'undefined'", timeout=5000)

    # モーダルが表示されることを確認
    page.wait_for_selector("[data-modal-dialog]", state="visible", timeout=10000)

    # モーダル内にタイトルが表示されることを確認
    expect(page.locator("#modal-container")).to_contain_text("モーダルテスト記事")


@pytest.mark.playwright
def test_modal_closes_with_close_button(page: Page, test_document):
    """閉じるボタンでモーダルが閉じる"""
    # ディープリンクでモーダルを開く
    page.goto(f"http://localhost:8000/documents?doc={test_document.id}")
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("[data-modal-dialog]", state="visible")

    # 閉じるボタンをクリック
    close_button = page.locator('[data-modal-close]').first
    close_button.click()

    # モーダルが閉じることを確認
    page.wait_for_selector("#modal-container", state="hidden", timeout=3000)
    modal_container = page.locator("#modal-container")
    expect(modal_container).to_have_class(re.compile(r".*hidden.*"))


@pytest.mark.playwright
def test_modal_closes_with_escape_key(page: Page, test_document):
    """ESCキーでモーダルが閉じる"""
    page.goto("http://localhost:8000/documents")
    page.wait_for_load_state("networkidle")

    # モーダルを開く
    page.locator('a:has-text("詳細を見る")').first.click()
    page.wait_for_selector("[data-modal-dialog]", state="visible")

    # ESCキーを押す
    page.keyboard.press("Escape")

    # モーダルが閉じることを確認
    page.wait_for_selector("#modal-container", state="hidden", timeout=3000)
    modal_container = page.locator("#modal-container")
    expect(modal_container).to_have_class(re.compile(r".*hidden.*"))


@pytest.mark.playwright
def test_modal_closes_with_overlay_click(page: Page, test_document):
    """背景オーバーレイクリックでモーダルが閉じる"""
    page.goto("http://localhost:8000/documents")
    page.wait_for_load_state("networkidle")

    # モーダルを開く
    page.locator('a:has-text("詳細を見る")').first.click()
    page.wait_for_selector("[data-modal-dialog]", state="visible")

    # オーバーレイ（モーダルコンテナの背景）をクリック
    # モーダルダイアログの外をクリック
    modal_container = page.locator("#modal-container")
    box = modal_container.bounding_box()
    # コンテナの左上をクリック（ダイアログの外側）
    page.mouse.click(box["x"] + 10, box["y"] + 10)

    # モーダルが閉じることを確認
    page.wait_for_selector("#modal-container", state="hidden", timeout=3000)
    expect(modal_container).to_have_class(re.compile(r".*hidden.*"))


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
    page.wait_for_selector("[data-modal-dialog]", state="visible")

    # overflow: hidden が設定されることを確認
    overflow_when_open = page.evaluate("document.body.style.overflow")
    assert overflow_when_open == "hidden"

    # モーダルを閉じる
    page.locator('[data-modal-close]').first.click()
    page.wait_for_selector("#modal-container", state="hidden")

    # overflowが復元されることを確認
    overflow_after_close = page.evaluate("document.body.style.overflow")
    assert overflow_after_close in ["", "auto", "visible"]


@pytest.mark.playwright
def test_modal_adds_url_query_parameter(page: Page, test_document):
    """モーダルを開くとURLに?doc={id}が追加される"""
    page.goto("http://localhost:8000/documents")
    page.wait_for_load_state("networkidle")

    # 初期URLを確認（クエリパラメータなし）
    initial_url = page.url
    assert "?doc=" not in initial_url

    # モーダルを開く
    page.locator('a:has-text("詳細を見る")').first.click()
    page.wait_for_selector("[data-modal-dialog]", state="visible")

    # URLに?doc=test-modal-docが追加されることを確認
    page.wait_for_url(lambda url: "?doc=test-modal-doc" in url, timeout=3000)
    assert "?doc=test-modal-doc" in page.url


@pytest.mark.playwright
def test_modal_removes_url_query_when_closed(page: Page, test_document):
    """モーダルを閉じるとURLから?doc={id}が削除される"""
    page.goto("http://localhost:8000/documents")
    page.wait_for_load_state("networkidle")

    # モーダルを開く
    page.locator('a:has-text("詳細を見る")').first.click()
    page.wait_for_selector("[data-modal-dialog]", state="visible")
    page.wait_for_url(lambda url: "?doc=test-modal-doc" in url)

    # モーダルを閉じる
    page.locator('[data-modal-close]').first.click()
    # Wait for the modal container to be hidden
    page.wait_for_selector("#modal-container", state="hidden")

    # URLから?doc={id}が削除されることを確認
    page.wait_for_url(lambda url: "?doc=" not in url, timeout=3000)
    assert "?doc=" not in page.url


@pytest.mark.playwright
def test_browser_back_button_closes_modal(page: Page, test_document):
    """ブラウザの戻るボタンでモーダルが閉じる"""
    page.goto("http://localhost:8000/documents")
    page.wait_for_load_state("networkidle")

    # モーダルを開く
    page.locator('a:has-text("詳細を見る")').first.click()
    page.wait_for_selector("[data-modal-dialog]", state="visible")
    page.wait_for_url(lambda url: "?doc=test-modal-doc" in url)

    # ブラウザの戻るボタンをクリック
    page.go_back()

    # モーダルが閉じることを確認
    page.wait_for_selector("#modal-container", state="hidden", timeout=3000)
    modal_container = page.locator("#modal-container")
    expect(modal_container).to_have_class(re.compile(r".*hidden.*"))

    # URLから?doc={id}が削除されることを確認
    assert "?doc=" not in page.url


@pytest.mark.playwright
def test_deep_link_opens_modal_automatically(page: Page, test_document):
    """?doc={id}付きURLに直接アクセスするとモーダルが自動的に開く"""
    # ?doc=test-modal-doc付きのURLに直接アクセス
    page.goto("http://localhost:8000/documents?doc=test-modal-doc")
    page.wait_for_load_state("networkidle")

    # モーダルが自動的に表示されることを確認
    page.wait_for_selector("[data-modal-dialog]", state="visible", timeout=5000)
    modal_container = page.locator("#modal-container")
    expect(modal_container).not_to_have_class('hidden')

    # モーダル内にタイトルが表示されることを確認
    expect(page.locator("#modal-container")).to_contain_text("モーダルテスト記事")


@pytest.mark.playwright
def test_bookmark_button_in_modal(page: Page, test_document, live_server):
    """モーダル内のブックマークボタンが動作する"""
    page.goto(f"{live_server}/documents")
    page.wait_for_load_state("networkidle")

    # モーダルを開く
    page.locator('a:has-text("詳細を見る")').first.click()
    page.wait_for_selector("[data-modal-dialog]", state="visible")

    # モーダル内のブックマークボタンをクリック
    bookmark_btn = page.locator("#modal-bookmark-btn")
    expect(bookmark_btn).to_be_visible()

    # 初期状態はブックマーク未設定
    expect(bookmark_btn).to_have_attribute("aria-pressed", "false")

    # ブックマークボタンをクリック
    bookmark_btn.click()
    page.wait_for_timeout(1000)  # HTMX処理待機

    # ブックマーク済み状態に変更されることを確認
    expect(bookmark_btn).to_have_attribute("aria-pressed", "true")


@pytest.mark.playwright
def test_bookmark_sync_between_modal_and_card(page: Page, test_document, live_server):
    """モーダル内でブックマークすると記事カードも更新される"""
    page.goto(f"{live_server}/documents")
    page.wait_for_load_state("networkidle")

    # 記事カードのブックマークボタンの初期状態を確認
    card_bookmark_btn = page.locator(f'button[data-doc-id="test-modal-doc"]').first
    initial_pressed = card_bookmark_btn.get_attribute("aria-pressed")

    # モーダルを開く
    page.locator('a:has-text("詳細を見る")').first.click()
    page.wait_for_selector("[data-modal-dialog]", state="visible")

    # モーダル内のブックマークボタンをクリック
    modal_bookmark_btn = page.locator("#modal-bookmark-btn")
    modal_bookmark_btn.click()
    page.wait_for_timeout(1000)  # HTMX out-of-band swap待機

    # 記事カードのブックマーク状態も更新されることを確認
    updated_pressed = card_bookmark_btn.get_attribute("aria-pressed")
    assert initial_pressed != updated_pressed, "記事カードのブックマーク状態が更新されていません"


@pytest.mark.playwright
def test_modal_desktop_responsive_styling(page: Page, test_document):
    """デスクトップ画面でモーダルが正しくスタイリングされる"""
    # デスクトップサイズに設定（1280x720）
    page.set_viewport_size({"width": 1280, "height": 720})

    page.goto("http://localhost:8000/documents")
    page.wait_for_load_state("networkidle")

    # モーダルを開く
    page.locator('a:has-text("詳細を見る")').first.click()
    page.wait_for_selector("[data-modal-dialog]", state="visible")

    # モーダルダイアログを取得
    modal_dialog = page.locator('[data-modal-dialog]')
    expect(modal_dialog).to_be_visible()

    # モーダルの幅が制限されていることを確認（max-w-4xl = 896px）
    box = modal_dialog.bounding_box()
    assert box["width"] <= 896, f"モーダル幅が896pxを超えています: {box['width']}px"

    # モーダルが中央に配置されていることを確認
    viewport_center_x = 1280 / 2
    modal_center_x = box["x"] + box["width"] / 2
    assert abs(viewport_center_x - modal_center_x) < 50, "モーダルが中央に配置されていません"


@pytest.mark.playwright
def test_modal_mobile_fullscreen(page: Page, test_document):
    """モバイル画面でモーダルがフルスクリーン表示される"""
    # モバイルサイズに設定（375x667 iPhone SE）
    page.set_viewport_size({"width": 375, "height": 667})

    page.goto("http://localhost:8000/documents")
    page.wait_for_load_state("networkidle")

    # モーダルを開く
    page.locator('a:has-text("詳細を見る")').first.click()
    page.wait_for_selector("[data-modal-dialog]", state="visible")

    # モーダルダイアログを取得
    modal_dialog = page.locator('[data-modal-dialog]')
    expect(modal_dialog).to_be_visible()

    # モーダルがほぼ画面全体を占めることを確認
    box = modal_dialog.bounding_box()
    # モバイルではフルスクリーンに近いサイズになるべき（余白を考慮して90%以上）
    width_ratio = box["width"] / 375
    assert width_ratio >= 0.9, f"モーダル幅が画面幅の90%未満です: {width_ratio*100:.1f}%"


@pytest.mark.playwright
def test_modal_content_scrollable(page: Page, test_document, live_server):
    """モーダル内のコンテンツが長い場合にスクロール可能である"""
    # test_documentを使用してモーダルを開く
    page.goto(f"{live_server}/documents?doc={test_document.id}")
    page.wait_for_load_state("networkidle")

    # モーダルが表示されることを確認
    page.wait_for_selector("[data-modal-dialog]", state="visible", timeout=10000)

    # モーダルのコンテンツ領域を取得 (data-modal-scrollable属性を使用)
    content_area = page.locator('[data-modal-scrollable]')
    expect(content_area).to_be_visible()

    # コンテンツ領域がスクロール可能であることを確認
    overflow_y = content_area.evaluate("el => window.getComputedStyle(el).overflowY")
    assert overflow_y in ["auto", "scroll"], f"コンテンツ領域がスクロール可能ではありません: overflow-y={overflow_y}"

    # スクロールプロパティが存在することを確認
    scroll_height = content_area.evaluate("el => el.scrollHeight")
    client_height = content_area.evaluate("el => el.clientHeight")
    assert scroll_height >= 0 and client_height >= 0, "スクロール領域が正しく設定されていません"
