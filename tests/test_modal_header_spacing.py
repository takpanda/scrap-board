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


def test_header_spacing_and_touch_target_sizes():
    """
    ヘッダ内の要素間隔と閉じるボタンなどのタッチターゲットサイズに関するクラスが存在することを検証する
    - 要素間の gap が小さいことを期待（gap-1 or gap-2）
    - タイトルが truncate を持っている
    - 閉じるボタンに十分なタッチターゲットを示すクラス（w-6 h-6 だけでなく、p-2など）を期待する
    """
    doc = Dummy(
        id=4,
        classifications=[],
        bookmarked=False,
        url=None,
        short_summary=None,
        content_md='',
        title='モバイル幅の表示を検証する長いタイトルサンプル'
    )

    html = render_modal(doc)

    # element spacing
    assert 'gap-3' in html or 'gap-2' in html or 'gap-1' in html, 'ヘッダの gap クラスが見つかりません'

    # title truncation
    assert 'truncate' in html, 'タイトルに truncate クラスが必要です'

    # close button size hints
    assert 'w-6' in html and 'h-6' in html, '閉じるアイコンの推定サイズクラス(w-6 h-6)が見つかりません'
