import os
import pytest

BASE_URL = os.environ.get("TEST_BASE_URL", "http://localhost:8000")


@pytest.mark.parametrize("viewport", [
    (375, 812, "mobile"),  # iPhone-like
    (1280, 800, "desktop"),
])
def test_modal_opens_and_is_responsive(page, viewport):
    width, height, label = viewport
    page.set_viewport_size({"width": width, "height": height})

    # Try connecting to app
    try:
        page.goto(BASE_URL, timeout=5000)
    except Exception as e:
        pytest.skip(f"Cannot reach server at {BASE_URL}: {e}")

    # Wait for a document card anchor that triggers modal
    anchor = page.locator("[data-document-id] a[hx-get][hx-target=\"#modal-container\"]").first
    # If the dev server has no documents seeded, skip the test gracefully
    try:
        count = anchor.count()
    except Exception:
        pytest.skip("Unable to determine anchor count; skipping")
    if count == 0:
        pytest.skip("No modal trigger anchor found on the page - ensure demo data is present")

    # Click and wait for HTMX swap to insert modal content
    anchor.click()

    # HTMX should swap innerHTML into #modal-container; wait for modal dialog
    modal = page.locator("#modal-container [data-modal-dialog]")
    modal.wait_for(timeout=5000)

    assert modal.is_visible(), "Modal dialog should be visible after clicking trigger"

    # Take a screenshot for manual review (saved in Playwright output dir)
    page.screenshot(path=f"modal_{label}.png", full_page=True)

    # Basic responsive checks
    # Header/text should not overflow horizontally
    assert page.locator("#modal-container [data-modal-dialog]").bounding_box()["width"] <= width + 2