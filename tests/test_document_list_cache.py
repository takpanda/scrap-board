"""
DocumentListCacheのテスト

このテストはPlaywrightを使用してDocumentListCacheの記事リストキャッシュ機能をテストします。
"""
import pytest
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.browser, pytest.mark.usefixtures("live_server")]


def test_document_list_cache_exists(page: Page):
    """
    DocumentListCacheクラスが定義されていることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # DocumentListCacheクラスが存在することを確認
    has_class = page.evaluate("typeof DocumentListCache === 'function'")
    assert has_class is True, "DocumentListCacheクラスが定義されているべき"


def test_document_list_cache_saves_and_retrieves_list(page: Page):
    """
    記事IDリストを保存して取得できることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # DocumentListCacheを初期化して記事IDリストを保存
    result = page.evaluate("""
        const cache = new DocumentListCache();
        const documentIds = [1, 2, 3, 4, 5];
        cache.saveDocumentList(documentIds);
        
        // 保存したリストが取得できることを確認
        cache.hasCachedList();
    """)
    
    assert result is True, "記事IDリストが保存されるべき"


def test_document_list_cache_get_next_document_id(page: Page):
    """
    次の記事IDを正しく取得できることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # 記事IDリストを保存して次の記事IDを取得
    result = page.evaluate("""
        const cache = new DocumentListCache();
        const documentIds = [10, 20, 30, 40, 50];
        cache.saveDocumentList(documentIds);
        
        // 現在の記事ID=20から次の記事ID取得
        cache.getAdjacentDocumentId(20, 'next');
    """)
    
    assert result == 30, f"次の記事ID=30を取得できるべき（実際: {result}）"


def test_document_list_cache_get_prev_document_id(page: Page):
    """
    前の記事IDを正しく取得できることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # 記事IDリストを保存して前の記事IDを取得
    result = page.evaluate("""
        const cache = new DocumentListCache();
        const documentIds = [10, 20, 30, 40, 50];
        cache.saveDocumentList(documentIds);
        
        // 現在の記事ID=30から前の記事ID取得
        cache.getAdjacentDocumentId(30, 'prev');
    """)
    
    assert result == 20, f"前の記事ID=20を取得できるべき（実際: {result}）"


def test_document_list_cache_returns_null_at_list_start(page: Page):
    """
    リスト先頭で前の記事IDを取得しようとするとnullが返ることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # リスト先頭の記事から前の記事IDを取得
    result = page.evaluate("""
        const cache = new DocumentListCache();
        const documentIds = [10, 20, 30];
        cache.saveDocumentList(documentIds);
        
        // リスト先頭（ID=10）から前の記事ID取得
        cache.getAdjacentDocumentId(10, 'prev');
    """)
    
    assert result is None, f"リスト先頭ではnullを返すべき（実際: {result}）"


def test_document_list_cache_returns_null_at_list_end(page: Page):
    """
    リスト末尾で次の記事IDを取得しようとするとnullが返ることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # リスト末尾の記事から次の記事IDを取得
    result = page.evaluate("""
        const cache = new DocumentListCache();
        const documentIds = [10, 20, 30];
        cache.saveDocumentList(documentIds);
        
        // リスト末尾（ID=30）から次の記事ID取得
        cache.getAdjacentDocumentId(30, 'next');
    """)
    
    assert result is None, f"リスト末尾ではnullを返すべき（実際: {result}）"


def test_document_list_cache_returns_null_for_nonexistent_id(page: Page):
    """
    リスト内に存在しない記事IDを指定するとnullが返ることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # 存在しない記事IDから隣接記事を取得
    result = page.evaluate("""
        const cache = new DocumentListCache();
        const documentIds = [10, 20, 30];
        cache.saveDocumentList(documentIds);
        
        // 存在しない記事ID=99から次の記事ID取得
        cache.getAdjacentDocumentId(99, 'next');
    """)
    
    assert result is None, f"存在しない記事IDではnullを返すべき（実際: {result}）"


def test_document_list_cache_saves_filter_params(page: Page):
    """
    フィルタパラメータもキャッシュに保存されることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # フィルタパラメータ付きで記事リストを保存
    result = page.evaluate("""
        const cache = new DocumentListCache();
        const documentIds = [1, 2, 3];
        const filterParams = {
            category: 'テック/AI',
            tag: 'LLM',
            query: 'GPT'
        };
        cache.saveDocumentList(documentIds, filterParams);
        
        // キャッシュが存在することを確認
        cache.hasCachedList();
    """)
    
    assert result is True, "フィルタパラメータ付きでキャッシュが保存されるべき"


def test_document_list_cache_can_be_cleared(page: Page):
    """
    clearCache()でキャッシュがクリアされることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # キャッシュを保存してクリア
    result = page.evaluate("""
        const cache = new DocumentListCache();
        const documentIds = [1, 2, 3];
        cache.saveDocumentList(documentIds);
        
        // クリア前はキャッシュが存在
        const beforeClear = cache.hasCachedList();
        
        // クリア実行
        cache.clearCache();
        
        // クリア後はキャッシュが存在しない
        const afterClear = cache.hasCachedList();
        
        { beforeClear, afterClear };
    """)
    
    assert result['beforeClear'] is True, "クリア前はキャッシュが存在すべき"
    assert result['afterClear'] is False, "クリア後はキャッシュが存在しないべき"


def test_document_list_cache_validates_empty_array(page: Page):
    """
    空の記事IDリストが拒否されることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # 空配列で保存を試みる
    error_message = page.evaluate("""
        const cache = new DocumentListCache();
        try {
            cache.saveDocumentList([]);
            null;  // エラーが発生しなかった場合
        } catch (error) {
            error.message;
        }
    """)
    
    assert error_message is not None, "空配列は拒否されるべき"
    assert "empty" in error_message.lower() or "空" in error_message, f"空配列エラーメッセージであるべき（実際: {error_message}）"


def test_document_list_cache_validates_duplicate_ids(page: Page):
    """
    重複した記事IDが拒否されることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # 重複IDを含む配列で保存を試みる
    error_message = page.evaluate("""
        const cache = new DocumentListCache();
        try {
            cache.saveDocumentList([1, 2, 3, 2, 4]);  // ID=2が重複
            null;  // エラーが発生しなかった場合
        } catch (error) {
            error.message;
        }
    """)
    
    assert error_message is not None, "重複IDは拒否されるべき"
    assert "duplicate" in error_message.lower() or "重複" in error_message, f"重複IDエラーメッセージであるべき（実際: {error_message}）"


def test_document_list_cache_validates_numeric_ids(page: Page):
    """
    数値型以外の記事IDが拒否されることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # 文字列IDを含む配列で保存を試みる
    error_message = page.evaluate("""
        const cache = new DocumentListCache();
        try {
            cache.saveDocumentList([1, "2", 3]);  // "2"が文字列
            null;  // エラーが発生しなかった場合
        } catch (error) {
            error.message;
        }
    """)
    
    assert error_message is not None, "非数値IDは拒否されるべき"
    assert "number" in error_message.lower() or "数値" in error_message, f"非数値IDエラーメッセージであるべき（実際: {error_message}）"


def test_document_list_cache_persists_across_page_reload(page: Page):
    """
    セッションストレージに保存されたキャッシュがページリロード後も取得できることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # 記事リストを保存
    page.evaluate("""
        const cache = new DocumentListCache();
        const documentIds = [100, 200, 300];
        cache.saveDocumentList(documentIds);
    """)
    
    # ページリロード
    page.reload()
    
    # リロード後もキャッシュが存在し、次の記事IDを取得できることを確認
    result = page.evaluate("""
        const cache = new DocumentListCache();
        
        // キャッシュが存在することを確認
        const hasCached = cache.hasCachedList();
        
        // 次の記事IDを取得
        const nextId = cache.getAdjacentDocumentId(200, 'next');
        
        { hasCached, nextId };
    """)
    
    assert result['hasCached'] is True, "リロード後もキャッシュが存在すべき"
    assert result['nextId'] == 300, f"リロード後も次の記事ID=300を取得できるべき（実際: {result['nextId']}）"
