import os


def test_style_css_contains_modal_scope():
    # modal styles may be in style.css or split into modal.css
    base_dir = os.path.join('app', 'static', 'css')
    candidates = [os.path.join(base_dir, 'style.css'), os.path.join(base_dir, 'modal.css')]
    found = False
    for css_path in candidates:
        if not os.path.exists(css_path):
            continue
        with open(css_path, 'r', encoding='utf-8') as f:
            content = f.read()
        if '[data-modal-dialog]' in content:
            found = True
            break
    assert found, f"Modal responsive styles not found in any of: {candidates}"


def test_modal_template_has_data_attributes():
    tpl_path = os.path.join('app', 'templates', 'partials', 'modal_content.html')
    assert os.path.exists(tpl_path), f"modal_content.html not found at {tpl_path}"
    with open(tpl_path, 'r', encoding='utf-8') as f:
        tpl = f.read()
    assert 'data-modal-dialog' in tpl, "modal_content.html missing data-modal-dialog"
    assert 'data-modal-scrollable' in tpl, "modal_content.html missing data-modal-scrollable"