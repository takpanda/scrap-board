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

    initial = btn.get_attribute('aria-pressed')

    # Act: click the bookmark button
    btn.click()

    # Allow network/microtasks
    page.wait_for_timeout(300)
    # Debug: capture screenshot to verify toast visibility
    page.screenshot(path='tests/screenshots/bookmark_click.png')

    # Assert: a POST or DELETE request occurred and aria-pressed toggled
    assert len(requests) >= 1, "ブックマーク API へのリクエストが発生しませんでした"
    assert btn.get_attribute('aria-pressed') != initial
    # Check that a toast notification appeared
    page.wait_for_selector('#toast-container [role="status"]', timeout=2000)
    toast = page.query_selector('#toast-container [role="status"]')
    assert toast is not None and toast.inner_text().strip() != ''
    # Debug: print the toast outerHTML to inspect inline styles
    print('\n--- TOAST OUTER HTML FOR DEBUG ---\n')
    print(toast.evaluate('node => node.outerHTML'))
