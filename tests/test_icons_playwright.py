import pytest
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.browser, pytest.mark.usefixtures("live_server")]


def test_icons_render_as_svg(page: Page):
    # collect console messages for debugging (attach before navigation)
    console_messages = []
    def on_console(msg):
        console_messages.append(f"{msg.type}: {msg.text}")

    page.on('console', on_console)

    page.goto("http://localhost:8000/documents")

    # wait for createIcons to run by waiting for at least one svg in place
    page.wait_for_selector('[data-lucide] svg, i[data-lucide] svg', timeout=3000)

    # grab all elements that originally had data-lucide
    elems = page.locator('[data-lucide]')
    count = elems.count()
    # ensure at least one was found
    assert count >= 1

    # check that each has an inner svg element (sample up to 10)
    for i in range(min(10, count)):
        el = elems.nth(i)
        # ensure the element contains an svg child
        svg = el.locator('svg')
        assert svg.count() == 1

    # give console a moment to flush
    page.wait_for_timeout(200)

    # assert createIcons logged a message
    assert any('createIcons called' in m or 'createIcons completed' in m for m in console_messages)
