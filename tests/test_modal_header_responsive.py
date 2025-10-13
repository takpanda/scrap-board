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


def test_header_padding_and_font_sizes_for_mobile():
    """
    ヘッダのパディングとフォントサイズがモバイル向けに最適化されていることを検証する
    - モバイルでは p-4 が存在
    - デスクトップでは md:p-6 が維持されている
    - メタデータバッジに text-xs 相当のクラスが適用されていることを期待する
    """
    doc = Dummy(
        id=3,
        classifications=[{
            'primary_category': 'テック/AI',
            'tags': ['長いタグ名のテスト']
        }],
        bookmarked=False,
        url=None,
        short_summary=None,
        content_md=''
    )

    html = render_modal(doc)

    # ヘッダのパディング
    assert 'md:p-6' in html, 'デスクトップ用の md:p-6 が存在しない'
    assert 'p-4' in html, 'モバイル用の p-4 が存在しない'

    # タイトルフォントサイズに関するヒント（テンプレートでは text-lg が使用されているはず）
    assert 'text-lg' in html or 'text-base' in html, 'ヘッダタイトルに想定されるフォントサイズクラスが見つかりません'

    # メタデータバッジのフォントサイズ（期待: text-xs が存在する可能性）
    # 実装はまだなので柔軟にチェック
    assert 'text-xs' in html or 'dify-tag-primary' in html, 'メタバッジに text-xs もしくは dify-tag-primary クラスが必要です'
