"""Playwright browser tests for Japanese text rendering."""

import pytest
from playwright.sync_api import Page, expect

# Mark all tests in this file as browser tests
pytestmark = [pytest.mark.browser, pytest.mark.slow]


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Override browser context with Japanese locale settings."""
    return {
        **browser_context_args,
        "locale": "ja-JP",
        "timezone_id": "Asia/Tokyo",
        "extra_http_headers": {
            "Accept-Language": "ja,ja-JP;q=0.9,en;q=0.8",
            "Accept-Charset": "UTF-8"
        }
    }


class TestJapaneseTextRendering:
    """Test Japanese text rendering and functionality."""

    def test_homepage_japanese_text(self, page: Page):
        """Test that Japanese text renders correctly on homepage."""
        page.goto("http://localhost:8000")
        
        # Check main heading
        heading = page.locator("h1")
        expect(heading).to_contain_text("Webコンテンツ収集管理システム")
        
        # Check navigation links
        nav_link = page.locator('nav a[href="/documents"]')
        expect(nav_link).to_contain_text("ドキュメント")
        
        collection_link = page.locator('nav a[href="/collections"]')
        expect(collection_link).to_contain_text("コレクション")

    def test_documents_page_japanese_text(self, page: Page):
        """Test Japanese text on documents page."""
        page.goto("http://localhost:8000/documents")
        
        # Check page title
        expect(page.locator("h1")).to_contain_text("ドキュメント一覧")
        
        # Check filter labels
        expect(page.locator('label[for="category"]')).to_contain_text("カテゴリ")
        expect(page.locator('label[for="domain"]')).to_contain_text("ドメイン")

    def test_add_content_modal_japanese_text(self, page: Page):
        """Test Japanese text in add content modal."""
        page.goto("http://localhost:8000")
        
        # Click add content button
        add_button = page.locator('button:has-text("コンテンツを追加")')
        add_button.click()
        
        # Check modal title
        modal_title = page.locator('#addContentModal h3')
        expect(modal_title).to_contain_text("コンテンツを追加")
        
        # Check form labels
        expect(page.locator('label[for="url"]')).to_contain_text("URL")
        expect(page.locator('label[for="pdf"]')).to_contain_text("PDF ファイル")

    def test_reader_mode_japanese_text(self, page: Page):
        """Test Japanese text rendering in reader mode."""
        page.goto("http://localhost:8000/documents")
        
        # Check if there are any documents with reader links
        reader_links = page.locator('a:has-text("Reader")')
        if reader_links.count() > 0:
            # Click first reader link
            reader_links.first.click()
            
            # Check reader mode controls have Japanese text
            expect(page.locator('select[id*="font"]')).to_be_visible()
            
            # Check font size controls
            font_controls = page.locator('.reader-controls')
            expect(font_controls).to_be_visible()

    def test_search_with_japanese_query(self, page: Page):
        """Test search functionality with Japanese text."""
        page.goto("http://localhost:8000/documents")
        
        # Search with Japanese keywords
        search_input = page.locator('input[name="q"]')
        search_input.fill("テスト")
        search_input.press("Enter")
        
        # Verify search was executed (URL should contain query)
        expect(page).to_have_url(lambda url: "q=テスト" in url or "q=%E3%83%86%E3%82%B9%E3%83%88" in url)

    def test_category_filter_japanese_options(self, page: Page):
        """Test category filter contains Japanese options."""
        page.goto("http://localhost:8000/documents")
        
        # Check category dropdown has Japanese options
        category_select = page.locator('select[name="category"]')
        
        # Open dropdown to see options
        category_select.click()
        
        # Check for common Japanese categories
        options = category_select.locator('option')
        option_texts = [options.nth(i).text_content() for i in range(options.count())]
        
        # Should contain some Japanese category names
        japanese_categories = ["テック/AI", "ソフトウェア開発", "セキュリティ"]
        has_japanese = any(cat in text for cat in japanese_categories for text in option_texts if text)
        
        # If we have demo content, we should see Japanese categories
        if options.count() > 1:  # More than just "すべて" option
            assert has_japanese, f"Expected Japanese categories in options: {option_texts}"

    def test_font_rendering_quality(self, page: Page):
        """Test that fonts render Japanese characters properly."""
        page.goto("http://localhost:8000")
        
        # Check that Japanese text is rendered with proper fonts
        japanese_text = page.locator('text="Webコンテンツ収集管理システム"').first
        
        # Take a screenshot to verify rendering
        screenshot = japanese_text.screenshot()
        assert len(screenshot) > 0, "Failed to capture screenshot of Japanese text"
        
        # Verify text is visible and has proper dimensions
        box = japanese_text.bounding_box()
        assert box and box["width"] > 100, "Japanese text appears too narrow or not rendered"
        assert box and box["height"] > 10, "Japanese text appears too short or not rendered"

    def test_input_japanese_text(self, page: Page):
        """Test inputting Japanese text in forms."""
        page.goto("http://localhost:8000")
        
        # Open add content modal
        page.locator('button:has-text("コンテンツを追加")').click()
        
        # Input Japanese text in URL field
        url_input = page.locator('input[name="url"]')
        japanese_url = "https://example.com/記事/テスト"
        url_input.fill(japanese_url)
        
        # Verify the text was input correctly
        expect(url_input).to_have_value(japanese_url)

    def test_page_encoding_utf8(self, page: Page):
        """Test that pages use UTF-8 encoding."""
        page.goto("http://localhost:8000")
        
        # Check meta charset tag
        charset_meta = page.locator('meta[charset]')
        if charset_meta.count() > 0:
            charset = charset_meta.get_attribute('charset')
            assert charset.lower() == 'utf-8', f"Expected UTF-8 charset, got {charset}"
        
        # Alternative: check Content-Type header
        content_type = page.evaluate("""
            () => document.contentType || document.characterSet || 'unknown'
        """)
        assert 'utf' in content_type.lower(), f"Expected UTF encoding, got {content_type}"