import os
import pytest
from pathlib import Path


@pytest.mark.usefixtures("page")
def test_modal_opens_on_mobile_and_no_horizontal_scroll(page, live_server):
    """
    ビューポートを iPhone SE 相当に設定し、記事カードをクリックしてモーダルを開き、
    横スクロールが発生しないこととヘッダ高さを検証する。
    """
    # Set mobile viewport (iPhone SE-ish)
    page.set_viewport_size({"width": 375, "height": 667})

    # Navigate to app root (live_server fixture should provide URL)
    try:
        page.goto(f"{live_server}/documents", timeout=5000)
    except Exception:
        pytest.skip(f"Cannot reach server at {live_server}")

    # Use the same modal trigger selector used elsewhere in tests
    anchor = page.locator('[data-document-id] a[hx-get][hx-target="#modal-container"]').first
    try:
        count = anchor.count()
    except Exception:
        count = 0

    if count == 0:
        # Fallback: wait for any article with data-document-id and click its internal hx-get anchor
        try:
            page.wait_for_selector('article[data-document-id]', timeout=3000)
            card_anchor = page.locator('article[data-document-id] a[hx-get][hx-target="#modal-container"]').first
            if card_anchor.count() == 0:
                # Diagnostic HTML if still not found
                try:
                    html = page.content()
                    print("--- PAGE HTML START ---")
                    print(html[:2000])
                    print("--- PAGE HTML END (truncated) ---")
                except Exception:
                    pass
                pytest.skip("No modal trigger anchor found on the page - ensure demo data is present")
            card_anchor.click()
        except Exception:
            pytest.skip("No modal trigger anchor found on the page - ensure demo data is present")
    else:
        anchor.click()

    # Wait for HTMX swap and modal to appear
    page.wait_for_selector("#modal-container [data-modal-dialog]", timeout=5000)

    # Check body scroll width does not exceed viewport width
    body_scroll_width = page.evaluate("() => document.body.scrollWidth")
    assert body_scroll_width <= 375, f"横スクロールが発生しています: body.scrollWidth={body_scroll_width} > 375"

    # Check header height <= 56px
    header = page.locator("#modal-container [data-modal-dialog] > div").first
    assert header.count() > 0, "モーダルヘッダが見つかりません"
    header_height = page.evaluate("el => Math.ceil(el.getBoundingClientRect().height)", header.element_handle())
    assert header_height <= 56, f"ヘッダ高さが56pxを超えています: {header_height}px"

    # Take screenshot for baseline (stored under tmp/screenshots)
    out_dir = Path("tmp/screenshots")
    out_dir.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(out_dir / "modal_mobile_baseline.png"), full_page=False)


@pytest.mark.usefixtures("page")
def test_labels_truncated_and_have_title_attribute(page, live_server):
    """
    長いカテゴリ/タグを持つ記事でモーダルを開き、ラベルが省略され title 属性があることを確認する。
    """
    page.set_viewport_size({"width": 375, "height": 667})
    try:
        page.goto(f"{live_server}/documents", timeout=5000)
    except Exception:
        pytest.skip(f"Cannot reach server at {live_server}")

    anchor = page.locator('[data-document-id] a[hx-get][hx-target="#modal-container"]').first
    try:
        count = anchor.count()
    except Exception:
        count = 0

    if count == 0:
        try:
            page.wait_for_selector('article[data-document-id]', timeout=3000)
            card_anchor = page.locator('article[data-document-id] a[hx-get][hx-target="#modal-container"]').first
            if card_anchor.count() == 0:
                pytest.skip("No modal trigger anchor found on the page - ensure demo data is present")
            card_anchor.click()
        except Exception:
            pytest.skip("No modal trigger anchor found on the page - ensure demo data is present")
    else:
        anchor.click()

    page.wait_for_selector("#modal-container [data-modal-dialog]", timeout=5000)

    # Find labels inside modal
    labels = page.locator("#modal-container [data-modal-dialog] .tag-list span")
    assert labels.count() > 0, "モーダル内のラベルが見つかりません"

    # Check each label has title attribute and that overflow can occur (scrollWidth > clientWidth) for at least one
    has_overflowing = False
    for i in range(labels.count()):
        lbl = labels.nth(i)
        title = lbl.get_attribute("title")
        assert title is not None and title != "", "ラベルに title 属性が設定されていません"
        # Evaluate if scrollWidth > clientWidth
        overflowing = page.evaluate("el => el.scrollWidth > el.clientWidth", lbl.element_handle())
        if overflowing:
            has_overflowing = True

    assert has_overflowing, "少なくとも1つのラベルはクライアント幅を超えていないため切り詰めが検証できません"
