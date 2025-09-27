from playwright.sync_api import Page, expect


def test_bookmark_button_toggles_and_calls_api(page: Page):
    # Arrange: navigate to a sample document; pick an existing document id from test DB
    # We'll use the first document in the list page for a deterministic flow
    page.goto("http://localhost:8000/documents")

    # Wait for the document list and pick the first document article
    page.wait_for_selector("article")
    article = page.query_selector("article")
    assert article is not None, "ドキュメント一覧の記事が見つかりません"
    # Find the detail link inside the article (title or '詳細を見る')
    link = article.query_selector("a[href^='/documents/']")
    assert link is not None, "記事内の詳細リンクが見つかりません"
    url = link.get_attribute('href')

    # Intercept bookmark API calls
    requests = []

    def handle_route(route, request):
        if request.method in ("POST", "DELETE") and "/api/bookmarks" in request.url:
            requests.append({
                'method': request.method,
                'url': request.url,
            })
            route.fulfill(status=200, body='')
        else:
            route.continue_()

    page.route("**/api/bookmarks**", handle_route)

    # Instead of navigating to detail, operate on the bookmark button in the article listing
    page.goto("http://localhost:8000/documents")
    page.wait_for_selector("article")
    article = page.query_selector("article")
    assert article is not None
    btn = article.query_selector("button.bookmark-btn")
    assert btn is not None, "一覧のブックマークボタンが見つかりません"

    # locate inner heart icon if present (may be replaced by lucide into an <svg>)
    icon = btn.query_selector('i[data-lucide="heart"]')
    # record initial attributes to compare after click
    initial = btn.get_attribute('aria-pressed')
    initial_icon_class = icon.get_attribute('class') if icon else None
    initial_icon_style = icon.get_attribute('style') if icon else None

    # Act: click the bookmark button
    btn.click()

    # Allow network/microtasks
    page.wait_for_timeout(300)
    # Wait for the icon's computed color or class to reflect bookmarked state.
    try:
        page.wait_for_function(
            """
            () => {
                const btn = document.querySelector('article button.bookmark-btn');
                if (!btn) return false;
                const el = btn.querySelector("i[data-lucide='heart']") || btn.querySelector('svg');
                if (!el) return false;
                const style = el.getAttribute('style') || '';
                const cls = el.getAttribute('class') || '';
                const cs = window.getComputedStyle(el) || {};
                const color = cs.color || '';
                const fill = cs.fill || '';
                const stroke = cs.stroke || '';
                // check inline styles, classes, computed color/fill/stroke for rose color (#9f1239 -> rgb(159, 18, 57))
                return cls.includes('text-rose-600') || style.includes('#9f1239') || color === 'rgb(159, 18, 57)' || fill === 'rgb(159, 18, 57)' || stroke === 'rgb(159, 18, 57)';
            }
            """,
            timeout=3000,
        )
    except Exception:
        # continue; assertion below will fail if necessary
        pass
    # Re-query article and button to avoid stale references if lucide replaced nodes
    article = page.query_selector('article')
    btn = article.query_selector('button.bookmark-btn') if article else btn
    # Debug: capture screenshot to verify toast visibility
    page.screenshot(path='tests/screenshots/bookmark_click.png')

    # Assert: a POST or DELETE request occurred and aria-pressed toggled
    assert len(requests) >= 1, "ブックマーク API へのリクエストが発生しませんでした"
    assert btn.get_attribute('aria-pressed') != initial
    # If icon exists, assert its class/style changed as expected
    # Re-query the icon after click because lucide may have replaced the element
    icon_after = btn.query_selector('i[data-lucide="heart"]') or btn.query_selector('svg')
    new_pressed = btn.get_attribute('aria-pressed')
    # Prefer checking explicit data attribute set by UI
    data_bookmarked = btn.get_attribute('data-bookmarked')
    if data_bookmarked is not None:
        if new_pressed == 'true':
            assert data_bookmarked == 'true', 'data-bookmarked 属性が true になっていません'
        else:
            assert data_bookmarked == 'false', 'data-bookmarked 属性が false になっていません'
    else:
        # Fallback: inspect icon color/class as before
        if icon_after:
            new_icon_class = icon_after.get_attribute('class') or ''
            new_icon_style = icon_after.get_attribute('style') or ''
            if new_pressed == 'true':
                assert ('text-rose-600' in new_icon_class) or ('#9f1239' in new_icon_style), "ブックマーク後に心アイコンがローズ色になっていません"
            else:
                assert ('text-graphite' in new_icon_class) or ('#9f1239' not in new_icon_style), "ブックマーク解除後に心アイコンがグラファイト色になっていません"
    # Check that a toast notification appeared
    page.wait_for_selector('#toast-container [role="status"]', timeout=2000)
    toast = page.query_selector('#toast-container [role="status"]')
    assert toast is not None and toast.inner_text().strip() != ''
    # Debug: print the toast outerHTML to inspect inline styles
    print('\n--- TOAST OUTER HTML FOR DEBUG ---\n')
    print(toast.evaluate('node => node.outerHTML'))
