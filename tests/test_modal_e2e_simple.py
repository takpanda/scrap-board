"""
モーダル機能の簡易E2Eテスト
既存のデータベースを使用して、主要な機能のみを検証
"""
import pytest
from playwright.sync_api import Page, expect
import re


@pytest.mark.playwright
def test_modal_opens_with_deep_link(page: Page):
    """ディープリンクでモーダルが開く"""
    # 実際に存在する記事IDを使用
    doc_id = "28661a78-3a53-4d87-934b-aee7a24e938f"

    # ディープリンクでアクセス
    page.goto(f"http://localhost:8000/documents?doc={doc_id}")
    page.wait_for_load_state("networkidle")

    # モーダルが表示されることを確認
    modal_container = page.locator("#modal-container")
    page.wait_for_function(
        "!document.getElementById('modal-container').classList.contains('hidden')",
        timeout=5000
    )
    expect(modal_container).not_to_have_class(re.compile(r".*hidden.*"))

    # モーダルにコンテンツが表示されることを確認
    expect(modal_container).to_contain_text("セルフレジ")


@pytest.mark.playwright
def test_modal_closes_with_escape_key(page: Page):
    """ESCキーでモーダルが閉じる"""
    doc_id = "28661a78-3a53-4d87-934b-aee7a24e938f"

    # モーダルを開く
    page.goto(f"http://localhost:8000/documents?doc={doc_id}")
    page.wait_for_load_state("networkidle")
    page.wait_for_function(
        "!document.getElementById('modal-container').classList.contains('hidden')",
        timeout=5000
    )

    # ESCキーを押す
    page.keyboard.press("Escape")

    # モーダルが閉じることを確認
    modal_container = page.locator("#modal-container")
    page.wait_for_function(
        "document.getElementById('modal-container').classList.contains('hidden')",
        timeout=3000
    )
    expect(modal_container).to_have_class(re.compile(r".*hidden.*"))


@pytest.mark.playwright
def test_modal_closes_with_close_button(page: Page):
    """閉じるボタンでモーダルが閉じる"""
    doc_id = "28661a78-3a53-4d87-934b-aee7a24e938f"

    # モーダルを開く
    page.goto(f"http://localhost:8000/documents?doc={doc_id}")
    page.wait_for_load_state("networkidle")
    page.wait_for_function(
        "!document.getElementById('modal-container').classList.contains('hidden')",
        timeout=5000
    )

    # JavaScriptで閉じるボタンをクリック
    page.evaluate("document.querySelector('[data-modal-close]').click()")

    # モーダルが閉じることを確認
    modal_container = page.locator("#modal-container")
    page.wait_for_function(
        "document.getElementById('modal-container').classList.contains('hidden')",
        timeout=3000
    )
    expect(modal_container).to_have_class(re.compile(r".*hidden.*"))


@pytest.mark.playwright
def test_modal_opens_from_card_click(page: Page):
    """記事カードからモーダルが開く"""
    # 記事一覧ページを開く
    page.goto("http://localhost:8000/documents")
    page.wait_for_load_state("networkidle")

    # 最初の「詳細を見る」ボタンをクリック
    detail_button = page.locator('a:has-text("詳細を見る")').first
    detail_button.click()

    # モーダルが表示されることを確認
    modal_container = page.locator("#modal-container")
    page.wait_for_function(
        "!document.getElementById('modal-container').classList.contains('hidden')",
        timeout=5000
    )
    expect(modal_container).not_to_have_class(re.compile(r".*hidden.*"))
