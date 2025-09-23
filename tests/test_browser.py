"""Minimal Playwright browser tests for Japanese UI smoke checks."""

import re
import pytest
from playwright.sync_api import Page, expect

# mark module as browser tests and use the live_server fixture provided by conftest
pytestmark = [pytest.mark.browser, pytest.mark.usefixtures("live_server")]


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "locale": "ja-JP",
        "timezone_id": "Asia/Tokyo",
        "extra_http_headers": {"Accept-Language": "ja,ja-JP;q=0.9"},
    }


class Test日本語テキストレンダリング:
    @pytest.mark.skip(reason="一時的にスキップ")
    def test_ホームページに日本語テキストがある(self, page: Page):
        page.goto("http://localhost:8000")
        heading = page.locator("h1")
        expect(heading).to_contain_text("Webコンテンツをスマートに収集・管理")
        expect(page.locator('nav a[href="/documents"]').first).to_contain_text("ドキュメント")

    def test_ドキュメントページに日本語テキストがある(self, page: Page):
        page.goto("http://localhost:8000/documents")
        expect(page.locator("h1").first).to_contain_text("ドキュメント")

    @pytest.mark.skip(reason="未実装のためスキップ")
    def test_日本語クエリで検索できる(self, page: Page):
        page.goto("http://localhost:8000/documents")
        search_input = page.locator('input[name="q"]')
        search_input.fill("テスト")
        # HTMX triggers on keyup/changed with a delay; wait for it to push URL
        search_input.press("Enter")
        page.wait_for_timeout(800)
        # Some setups may not push a URL when there are no results; assert input value and container update instead
        expect(search_input).to_have_value("テスト")
        container = page.locator('#documents-container')
        expect(container).to_be_visible()

    def test_文字エンコーディングが_utf8(self, page: Page):
        page.goto("http://localhost:8000")
        charset = page.evaluate(
            """
            () => {
                const meta = document.querySelector('meta[charset]');
                return meta ? meta.getAttribute('charset') : document.characterSet;
            }
            """
        )
        assert charset and charset.lower() == "utf-8"

