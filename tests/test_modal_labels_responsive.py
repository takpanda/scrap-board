import pytest
from jinja2 import Environment, FileSystemLoader


env = Environment(loader=FileSystemLoader('app/templates'))

def render_document(document):
    tmpl = env.get_template('partials/modal_content.html')
    return tmpl.render(document=document)


def make_sample_document():
    return {
        'id': 1,
        'title': 'テスト記事',
        'bookmarked': False,
        'url': 'https://example.com',
        'classifications': [
            {
                'primary_category': 'テック/AI',
                'tags': ['機械学習', 'LLM長いタグ名でオーバーフローを起こすかな']
            }
        ],
        'short_summary': '短い要約',
        'content_md': '本文のマークダウン'
    }


def test_tags_have_title_attribute_and_no_wrap_by_default():
    doc = make_sample_document()
    html = render_document(doc)

    # カテゴリの span は title 属性を持つべき（まだ持っていないためテストは失敗するはず）
    assert 'title="テック/AI"' in html, 'カテゴリに title 属性がない: レスポンシブ対応のテンプレート修正が必要'

    # 長いタグ名が text-overflow: ellipsis を期待するが、CSS はまだ適用されていないため、ここでは class 名の存在をチェック
    assert 'dify-tag-secondary' in html, 'タグ要素が見つかりません'
