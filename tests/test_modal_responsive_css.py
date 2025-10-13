import re
from pathlib import Path


def test_style_css_has_modal_responsive_section():
    css_path = Path("app/static/css/style.css")
    assert css_path.exists(), "style.css が存在しません"
    content = css_path.read_text(encoding="utf-8")
    # テストは末尾に Modal Responsive Styles セクションがあることを期待する
    assert "Modal Responsive Styles" in content, "style.css に 'Modal Responsive Styles' セクションが見つかりません"


def test_media_query_present_for_modal():
    css_path = Path("app/static/css/style.css")
    content = css_path.read_text(encoding="utf-8")
    # モバイル用メディアクエリが含まれていること
    assert re.search(r"@media \(max-width: 768px\)", content), "@media (max-width: 768px) が見つかりません"


def test_modal_dialog_selector_scoped():
    css_path = Path("app/static/css/style.css")
    content = css_path.read_text(encoding="utf-8")
    # セクタが[data-modal-dialog]でスコープされていること
    assert "[data-modal-dialog]" in content, "[data-modal-dialog] セレクタが見つかりません"
