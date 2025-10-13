import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os

HERE = os.path.dirname(os.path.dirname(__file__))
TEMPLATES = os.path.join(HERE, 'app', 'templates')


def render_modal(document):
    env = Environment(
        loader=FileSystemLoader([TEMPLATES, os.path.join(TEMPLATES, 'partials')]),
        autoescape=select_autoescape(['html', 'xml'])
    )
    tmpl = env.get_template('partials/modal_content.html')
    return tmpl.render(document=document)


class Dummy:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_modal_content_scrollable_and_touch_scrolling():
    """モーダルのコンテンツ領域がスクロール可能で慣性スクロールが有効化されていることを検証する"""
    doc = Dummy(id=3, classifications=[], bookmarked=False, url=None, short_summary=None, content_md='')
    html = render_modal(doc)

    # コンテンツ領域のマークアップが存在すること
    assert 'data-modal-scrollable' in html, 'data-modal-scrollable がテンプレートに存在しません'

    # style.css に慣性スクロールのルールが存在すること（初回は False の想定）
    css_path = os.path.join(HERE, 'app', 'static', 'css', 'style.css')
    with open(css_path, 'r') as fh:
        css = fh.read()

    assert '-webkit-overflow-scrolling: touch' in css, 'style.css に -webkit-overflow-scrolling: touch が存在しません'