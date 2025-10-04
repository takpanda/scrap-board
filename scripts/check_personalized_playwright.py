"""Playwright E2E check for personalized rendering.

This script expects the app to be available at http://127.0.0.1:8001
It will:
 - open /documents?sort=personalized
 - collect console messages
 - check if elements with data-personalized-fallback are visible after JS runs

Run:
 1) Start server: uvicorn app.main:app --host 127.0.0.1 --port 8001
 2) Run this script: python scripts/check_personalized_playwright.py

If Playwright is not installed, install with:
  pip install playwright
  playwright install
"""
from __future__ import annotations

import time
from typing import List
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8001/documents?sort=personalized"


def run_check() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="ja-JP", timezone_id="Asia/Tokyo")
        page = context.new_page()

        console_messages: List[str] = []

        def _on_console(msg):
            console_messages.append(f"{msg.type}: {msg.text}")

        page.on("console", _on_console)

        print(f"Opening {URL} ...")
        page.goto(URL, wait_until="networkidle")

        # Wait briefly for any client-side personalization fetch/decorate
        time.sleep(1.0)

        # Count fallback elements and visibility
        fallback_elements = page.query_selector_all("[data-personalized-fallback]")
        total = len(fallback_elements)
        visible = 0
        for el in fallback_elements:
            if el.is_visible():
                visible += 1

        print(f"Found {total} fallback elements; {visible} visible after JS run")

        # Log console messages
        print("Console messages:")
        for msg in console_messages:
            print(msg)

        browser.close()


if __name__ == "__main__":
    run_check()
