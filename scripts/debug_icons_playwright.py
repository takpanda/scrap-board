from playwright.sync_api import sync_playwright

URL = "http://localhost:8000/documents"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(locale='ja-JP', timezone_id='Asia/Tokyo')
    page = context.new_page()

    console_messages = []
    def on_console(msg):
        console_messages.append((msg.type, msg.text))
    page.on('console', on_console)

    print('navigating...')
    page.goto(URL)
    page.wait_for_timeout(500)

    print('console messages:')
    for t, m in console_messages:
        print(f'[{t}] {m}')

    elems = page.query_selector_all('[data-lucide]')
    print(f'found {len(elems)} elements with data-lucide')

    for i, el in enumerate(elems[:30]):
        name = el.get_attribute('data-lucide')
        inner = el.inner_html()
        has_svg = bool(el.query_selector('svg'))
        print(f'{i:02d}: {name} - has_svg={has_svg} - inner_len={len(inner)} - snippet={inner[:120]!r}')

    # print outer HTML of a failing element if any
    for i, el in enumerate(elems[:30]):
        if not el.query_selector('svg'):
            print('\nExample failing element outer_html:')
            print(el.evaluate('e => e.outerHTML'))
            break

    browser.close()
