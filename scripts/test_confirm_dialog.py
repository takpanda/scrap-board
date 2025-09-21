from playwright.sync_api import sync_playwright

url = "http://localhost:8000/admin"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    def on_dialog(dialog):
        print("DIALOG:", dialog.type, dialog.message)
        dialog.dismiss()

    page.on("dialog", lambda dialog: on_dialog(dialog))
    page.goto(url)
    page.wait_for_timeout(500)

    # Wait for the sources list to be loaded (htmx may replace it)
    try:
        page.wait_for_selector('#sources-list .source-card', timeout=5000)
    except Exception:
        # fallback: wait a bit longer
        page.wait_for_timeout(1000)

    # Try clicking the create button inside the create form
    try:
        page.click('#create-source-form button[type="submit"]', timeout=2000)
        page.wait_for_timeout(500)
    except Exception as e:
        print("Click error:", e)

    # Try clicking a delete button in the list (first one)
    try:
        page.click('[data-confirm][hx-delete]', timeout=5000)
        # Wait briefly for modal to be created
        try:
            page.wait_for_selector('#inpage-confirm-modal', timeout=2000)
            # Read message and click OK
            msg = page.eval_on_selector('#inpage-confirm-message', 'el => el.textContent')
            print('modal_message=', msg)
            page.click('#inpage-confirm-ok')
            page.wait_for_timeout(200)
        except Exception as me:
            print('Modal not found after click:', me)
    except Exception as e:
        print("Click delete error:", e)

    # Check if inpage modal exists now (final check)
    try:
        exists = page.evaluate("() => !!document.getElementById('inpage-confirm-modal')")
        print('modal_exists=', exists)
    except Exception as e:
        print('readback error', e)

    browser.close()
    print("done")
