"""Playwright tests for Bookmarks page mobile layout."""

import pytest
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.browser, pytest.mark.slow]


class TestBookmarksMobileLayout:
    def test_ブックマーク一覧_モバイル_オーバーフローなし(self, page: Page):
        """ブックマーク一覧ページのモバイル表示で横スクロールが発生しないことを確認する。"""
        # Set mobile viewport (iPhone 12 Pro size)
        page.set_viewport_size({"width": 390, "height": 844})
        
        # Navigate to bookmarks page
        page.goto("http://localhost:8000/bookmarks")
        page.wait_for_load_state("networkidle")
        
        # Check that the page body doesn't have horizontal scroll
        # Get the document width and viewport width
        body_width = page.evaluate("document.body.scrollWidth")
        viewport_width = page.evaluate("window.innerWidth")
        
        # Body scroll width should not exceed viewport width (allowing 1px tolerance for rounding)
        assert body_width <= viewport_width + 1, (
            f"横スクロールが発生しています: body width={body_width}px, viewport={viewport_width}px"
        )
        
        # Check bookmarks container if it exists
        bookmarks_container = page.locator("#bookmarks-container")
        if bookmarks_container.count() > 0:
            container_width = bookmarks_container.evaluate("el => el.scrollWidth")
            assert container_width <= viewport_width + 1, (
                f"ブックマークコンテナが横にはみ出しています: container={container_width}px, viewport={viewport_width}px"
            )
        
        # Take screenshot for visual verification
        path = 'tests/screenshots/bookmarks_mobile_no_overflow.png'
        page.screenshot(path=path, full_page=True)
        import os
        assert os.path.exists(path) and os.path.getsize(path) > 0

    def test_ブックマークカード_モバイル_レイアウト(self, page: Page):
        """ブックマークカードがモバイルで適切にレイアウトされることを確認する。"""
        # Set mobile viewport
        page.set_viewport_size({"width": 375, "height": 667})  # iPhone SE size
        
        # Navigate to bookmarks page
        page.goto("http://localhost:8000/bookmarks")
        page.wait_for_load_state("networkidle")
        
        # Check if any cards exist
        cards = page.locator("#bookmarks-container article")
        if cards.count() == 0:
            pytest.skip("ブックマークが存在しないためテストをスキップします")
        
        # Check first card doesn't overflow
        first_card = cards.first
        card_width = first_card.evaluate("el => el.getBoundingClientRect().width")
        viewport_width = page.evaluate("window.innerWidth")
        
        # Card should fit within viewport with some padding
        # Considering px-4 (1rem = 16px per side), cards should be narrower than viewport
        assert card_width < viewport_width, (
            f"カードが画面幅を超えています: card={card_width}px, viewport={viewport_width}px"
        )
        
        # Check that cards are stacked vertically (grid-cols-1 on mobile)
        # All cards should have roughly the same x position
        if cards.count() > 1:
            first_x = first_card.evaluate("el => el.getBoundingClientRect().x")
            second_card = cards.nth(1)
            second_x = second_card.evaluate("el => el.getBoundingClientRect().x")
            
            # Cards should be aligned vertically (same x position, tolerance of 5px)
            assert abs(first_x - second_x) < 5, (
                f"カードが横に並んでいます（縦に並ぶべき）: card1_x={first_x}, card2_x={second_x}"
            )
