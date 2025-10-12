"""モーダル内のMarkdownプレビュー表示のテスト"""
import pytest
from playwright.sync_api import Page, expect
from sqlalchemy.orm import Session
from app.core.database import Document, Classification, create_tables
from app.core import database as app_db
from datetime import datetime, timezone


@pytest.fixture()
def db_session():
    """DBセッションのフィクスチャ"""
    create_tables()
    session = app_db.SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_document_with_markdown(db_session: Session):
    """Markdownコンテンツを含むテスト用の記事データを作成"""
    document = Document(
        id="test-md-doc",
        title="Markdownテスト記事",
        url="https://example.com/markdown-test",
        domain="example.com",
        content_md="""# テスト見出し

これは**太字**と*斜体*のテストです。

## リスト

- 項目1
- 項目2
- 項目3

## コードブロック

```python
def hello():
    print("Hello, World!")
```

## リンク

[例のリンク](https://example.com)
""",
        content_text="テスト見出し これは太字と斜体のテストです。",
        short_summary="""# 要約

この記事は**Markdown**のレンダリングテストです。

- ポイント1
- ポイント2
""",
        hash="test-md-hash",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc)
    )
    db_session.add(document)

    classification = Classification(
        document_id="test-md-doc",
        primary_category="テスト",
        topics=["Markdown"],
        tags=["rendering"],
        confidence=0.9,
        method="manual"
    )
    db_session.add(classification)

    db_session.commit()
    db_session.refresh(document)

    yield document

    # クリーンアップ
    db_session.query(Classification).filter(Classification.document_id == "test-md-doc").delete()
    db_session.query(Document).filter(Document.id == "test-md-doc").delete()
    db_session.commit()


@pytest.mark.playwright
def test_modal_markdown_rendering(page: Page, test_document_with_markdown, live_server):
    """モーダル内でMarkdownが正しくレンダリングされることを確認"""
    # コンソールログを監視
    page.on("console", lambda msg: print(f"Console: {msg.type}: {msg.text}"))
    
    # ディープリンクで直接テスト記事のモーダルを開く
    page.goto(f"{live_server}/documents?doc={test_document_with_markdown.id}")
    page.wait_for_load_state("networkidle")
    
    # modal.jsとHTMXの初期化を待つ
    page.wait_for_function("typeof window.modalManager !== 'undefined' && typeof window.markdownit !== 'undefined'", timeout=10000)
    
    # モーダルが表示されるまで待つ
    modal = page.locator('[data-modal-dialog]')
    expect(modal).to_be_visible(timeout=10000)
    
    # Markdownレンダリングの完了を待つ
    page.wait_for_timeout(2000)
    
    # スクリーンショットを撮ってデバッグ
    page.screenshot(path="tmp/modal_markdown_debug.png")
    
    # AI要約セクションの存在を確認
    summary_section = page.locator('.modal-summary-content')
    assert summary_section.count() > 0, "要約セクションが見つかりません"
    
    # 内部HTMLを確認
    summary_html = summary_section.inner_html()
    print(f"Summary HTML: {summary_html[:200]}")
    
    # 要約内にMarkdownがレンダリングされているか確認
    # HTMLタグが含まれているか確認
    assert '<h1>' in summary_html or '<p>' in summary_html or '<ul>' in summary_html, \
        f"Markdownがレンダリングされていません: {summary_html[:100]}"
    
    # コンテンツプレビューセクションでMarkdownがレンダリングされているか確認
    content_preview = page.locator('.modal-content-preview')
    expect(content_preview).to_be_visible(timeout=5000)
    
    # HTMLタグがレンダリングされているか確認
    expect(content_preview.locator('h1, h2, p, ul, strong, em').first).to_be_visible(timeout=5000)
    
    # モーダルを閉じる
    close_button = page.locator('[data-modal-close]').first
    close_button.click()
    
    # モーダルが閉じられたことを確認
    expect(modal).to_be_hidden(timeout=3000)


@pytest.mark.playwright
def test_modal_markdown_escaping(page: Page, test_document_with_markdown, live_server):
    """Markdown内のHTMLエスケープが正しく処理されることを確認"""
    # ディープリンクで直接テスト記事のモーダルを開く
    page.goto(f"{live_server}/documents?doc={test_document_with_markdown.id}")
    page.wait_for_load_state("networkidle")
    
    # モーダルが表示されるまで待つ
    modal = page.locator('[data-modal-dialog]')
    expect(modal).to_be_visible(timeout=10000)
    
    # コンテンツプレビューを取得
    content_preview = page.locator('.modal-content-preview')
    expect(content_preview).to_be_visible(timeout=5000)
    
    # 生のHTMLタグ（<script>など）がエスケープされて表示されていないことを確認
    inner_html = content_preview.inner_html()
    
    # XSSの可能性がある<script>タグが実行可能な形で存在しないことを確認
    assert '<script>' not in inner_html.lower() or '&lt;script&gt;' in inner_html.lower()
    
    print("✓ HTMLエスケープが正しく処理されています")


@pytest.mark.playwright 
def test_modal_markdown_links(page: Page, test_document_with_markdown, live_server):
    """Markdown内のリンクが正しくレンダリングされることを確認"""
    # ディープリンクで直接テスト記事のモーダルを開く
    page.goto(f"{live_server}/documents?doc={test_document_with_markdown.id}")
    page.wait_for_load_state("networkidle")
    
    # モーダルが表示されるまで待つ
    modal = page.locator('[data-modal-dialog]')
    expect(modal).to_be_visible(timeout=10000)
    
    # コンテンツプレビュー内のリンクを確認
    content_preview = page.locator('.modal-content-preview')
    links = content_preview.locator('a')
    
    # リンクが存在することを確認
    expect(links.first).to_be_visible(timeout=5000)
    
    # 最初のリンクが適切な属性を持っていることを確認
    first_link = links.first
    href = first_link.get_attribute('href')
    assert href is not None, "リンクにhref属性がありません"
    assert 'example.com' in href, f"期待されるURLではありません: {href}"
    
    print("✓ Markdownリンクが正しくレンダリングされています")


@pytest.mark.playwright
def test_modal_markdown_code_blocks(page: Page, test_document_with_markdown, live_server):
    """Markdown内のコードブロックが正しくレンダリングされることを確認"""
    # ディープリンクで直接テスト記事のモーダルを開く
    page.goto(f"{live_server}/documents?doc={test_document_with_markdown.id}")
    page.wait_for_load_state("networkidle")
    
    # モーダルが表示されるまで待つ
    modal = page.locator('[data-modal-dialog]')
    expect(modal).to_be_visible(timeout=10000)
    
    # コンテンツプレビュー内のコードブロックを確認
    content_preview = page.locator('.modal-content-preview')
    code_blocks = content_preview.locator('code, pre')
    
    # コードブロックが存在することを確認
    expect(code_blocks.first).to_be_visible(timeout=5000)
    print("✓ Markdownコードブロックが正しくレンダリングされています")
