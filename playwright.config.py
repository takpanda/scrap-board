"""Playwright configuration for Japanese text support."""

import os
from playwright.sync_api import Playwright


def pytest_configure():
    """Configure pytest for Playwright tests."""
    pass


def pytest_playwright_browsers(playwright: Playwright):
    """Configure browsers with Japanese locale and font support."""
    return [
        playwright.chromium.launch(
            headless=True,
            args=[
                '--font-render-hinting=none',
                '--disable-font-subpixel-positioning',
                '--disable-gpu-sandbox',
                '--no-sandbox',
                '--lang=ja-JP',
                '--accept-lang=ja,ja-JP,en',
            ]
        )
    ]


def pytest_playwright_context_args():
    """Configure browser context with Japanese locale."""
    return {
        "locale": "ja-JP",
        "timezone_id": "Asia/Tokyo",
        "color_scheme": "light",
        "viewport": {"width": 1280, "height": 720},
        "extra_http_headers": {
            "Accept-Language": "ja,ja-JP;q=0.9,en;q=0.8",
            "Accept-Charset": "UTF-8"
        }
    }