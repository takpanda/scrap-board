from playwright.sync_api import sync_playwright

URL = "http://localhost:8000/documents"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 375, "height": 667})
    page.goto(URL)
    page.wait_for_load_state("networkidle")

    anchors = page.query_selector_all('[data-document-id] a[hx-get][hx-target="#modal-container"]')
    print("anchors found:", len(anchors))
    if anchors:
        # outer_html isn't available on ElementHandle; use evaluate to get outerHTML
        print(anchors[0].evaluate("el => el.outerHTML"))
    # also try article count
    articles = page.query_selector_all('article[data-document-id]')
    print("articles found:", len(articles))
    if articles:
        print(articles[0].get_attribute('data-document-id'))

    browser.close()
