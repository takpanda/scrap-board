"""Playwright tests for Document Detail UI and reader-mode snapshots."""

import pytest
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.browser, pytest.mark.slow]


def goto_first_document(page: Page):
    page.goto("http://localhost:8000/documents")
    # Wait for documents list and click first document link if present
    page.wait_for_load_state("networkidle")
    first = page.locator('a:has(h2), a.document-link').first
    if first.count() == 0:
        pytest.skip("No documents available for UI snapshot tests")
    first.click()
    page.wait_for_load_state("networkidle")


class TestDocumentDetailUI:
    def test_document_detail_desktop_snapshot(self, page: Page):
        """Capture desktop snapshot of document detail page."""
        page.set_viewport_size({"width": 1280, "height": 800})
        goto_first_document(page)

        # Ensure meta and content are visible
        expect(page.locator('.document-meta')).to_be_visible()
        expect(page.locator('.prose, .document-body')).to_be_visible()

        # Take screenshot
        path = 'tests/screenshots/document_detail_desktop.png'
        page.screenshot(path=path, full_page=True)
        import os
        assert os.path.exists(path) and os.path.getsize(path) > 0

    def test_document_detail_mobile_snapshot_reader_mode(self, page: Page):
        """Capture mobile snapshot and reader-mode toggle."""
        page.set_viewport_size({"width": 390, "height": 844})
        goto_first_document(page)

        # Toggle reader mode if control exists
        reader_btn = page.locator('.btn-reader')
        if reader_btn.count() > 0:
            reader_btn.first.click()

        # Set large font preset if available
        font_btn = page.locator('.font-presets button[data-size="large"]')
        if font_btn.count() > 0:
            font_btn.first.click()

        # Wait a moment for styles to apply
        page.wait_for_timeout(500)

        path = 'tests/screenshots/document_detail_mobile_reader.png'
        page.screenshot(path=path, full_page=True)
        import os
        assert os.path.exists(path) and os.path.getsize(path) > 0
