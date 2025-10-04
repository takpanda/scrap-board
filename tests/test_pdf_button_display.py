"""
Test PDF button display in document_card template.

このテストは、PDFダウンロードボタンがURLの有無に関わらず正しく表示されることを確認します。
"""
import pytest
from jinja2 import Environment, FileSystemLoader
from datetime import datetime


@pytest.fixture
def jinja_env():
    """Jinja2環境をセットアップ"""
    env = Environment(loader=FileSystemLoader('app/templates'))
    
    # to_jstフィルタを登録
    def to_jst(value, fmt='%Y-%m-%d'):
        try:
            return value.strftime(fmt) if hasattr(value, 'strftime') else str(value)
        except:
            return str(value)
    
    env.filters['to_jst'] = to_jst
    return env


class MockDocument:
    """テスト用のドキュメントモックオブジェクト"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', '123')
        self.title = kwargs.get('title', 'Test Document')
        self.url = kwargs.get('url', None)
        self.pdf_path = kwargs.get('pdf_path', None)
        self.domain = kwargs.get('domain', None)
        self.source = kwargs.get('source', 'manual')
        self.thumbnail_url = kwargs.get('thumbnail_url', None)
        self.created_at = kwargs.get('created_at', datetime.now())
        self.updated_at = kwargs.get('updated_at', datetime.now())
        self.bookmark_created_at = kwargs.get('bookmark_created_at', None)
        self.short_summary = kwargs.get('short_summary', None)
        self.content_text = kwargs.get('content_text', 'Test content')
        self.classifications = kwargs.get('classifications', [])
        self.bookmarked = kwargs.get('bookmarked', False)
        self.bookmark_note = kwargs.get('bookmark_note', None)
        self.personalized_score = kwargs.get('personalized_score', None)
        self.personalized_components = kwargs.get('personalized_components', None)


@pytest.mark.unit
def test_pdf_button_shows_with_url_and_pdf(jinja_env):
    """URLとPDFの両方がある場合、両方のボタンが表示される"""
    template = jinja_env.get_template('partials/document_card.html')
    
    document = MockDocument(
        url='https://example.com/article',
        pdf_path='pdfs/test.pdf',
        domain='example.com'
    )
    
    html = template.render(
        document=document,
        category_class_map={},
        ns=type('obj', (object,), {'autostart_done': False})(),
        selected_tag=''
    )
    
    # URLボタンが存在することを確認（external-linkアイコンの存在で確認）
    assert 'external-link' in html
    
    # PDFボタンが存在することを確認
    assert 'file-down' in html
    assert f'/api/documents/{document.id}/pdf' in html


@pytest.mark.unit
def test_pdf_button_shows_without_url(jinja_env):
    """URLがなくPDFのみの場合、PDFボタンのみが表示される"""
    template = jinja_env.get_template('partials/document_card.html')
    
    document = MockDocument(
        url=None,  # URLなし
        pdf_path='pdfs/test.pdf',
        domain='example.com'
    )
    
    html = template.render(
        document=document,
        category_class_map={},
        ns=type('obj', (object,), {'autostart_done': False})(),
        selected_tag=''
    )
    
    # URLボタンが存在しないことを確認（external-linkアイコンで確認）
    assert 'external-link' not in html
    
    # PDFボタンが存在することを確認（これが修正の主要な検証ポイント）
    assert 'file-down' in html
    assert f'/api/documents/{document.id}/pdf' in html


@pytest.mark.unit
def test_no_buttons_without_url_and_pdf(jinja_env):
    """URLもPDFもない場合、どちらのボタンも表示されない"""
    template = jinja_env.get_template('partials/document_card.html')
    
    document = MockDocument(
        url=None,
        pdf_path=None,
        domain='example.com'
    )
    
    html = template.render(
        document=document,
        category_class_map={},
        ns=type('obj', (object,), {'autostart_done': False})(),
        selected_tag=''
    )
    
    # どちらのボタンも存在しないことを確認
    assert 'external-link' not in html
    assert 'file-down' not in html


@pytest.mark.unit
def test_details_button_shows_with_pdf_only(jinja_env):
    """PDFのみの場合でも詳細を見るボタンが表示される"""
    template = jinja_env.get_template('partials/document_card.html')
    
    document = MockDocument(
        url=None,
        pdf_path='pdfs/test.pdf',
        domain='example.com'
    )
    
    html = template.render(
        document=document,
        category_class_map={},
        ns=type('obj', (object,), {'autostart_done': False})(),
        selected_tag=''
    )
    
    # 詳細を見るボタンが存在することを確認
    assert '詳細を見る' in html
    assert f'/documents/{document.id}' in html
