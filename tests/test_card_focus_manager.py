"""
CardFocusManagerのテスト

このテストはPlaywrightを使用してCardFocusManagerの記事カードフォーカス管理機能をテストします。
"""
import pytest
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.browser, pytest.mark.usefixtures("live_server")]


def test_card_focus_manager_exists(page: Page):
    """
    CardFocusManagerクラスが定義されていることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # CardFocusManagerクラスが存在することを確認
    has_class = page.evaluate("typeof CardFocusManager === 'function'")
    assert has_class is True, "CardFocusManagerクラスが定義されているべき"


def test_card_focus_manager_initializes_with_first_card(page: Page):
    """
    初期化時に先頭カードにフォーカスが設定されることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # テスト用のカードを作成
    page.evaluate("""
        const container = document.body;
        container.innerHTML = `
            <div class="document-card" data-document-id="1">Card 1</div>
            <div class="document-card" data-document-id="2">Card 2</div>
            <div class="document-card" data-document-id="3">Card 3</div>
        `;
    """)
    
    # CardFocusManagerを初期化
    result = page.evaluate("""
        const manager = new CardFocusManager();
        manager.initialize();
        
        // 先頭カードにフォーカスハイライトが付いているか確認
        const firstCard = document.querySelector('.document-card');
        firstCard.classList.contains('focus-highlight');
    """)
    
    assert result is True, "初期化時に先頭カードにフォーカスハイライトが設定されるべき"


def test_card_focus_manager_moves_focus_to_next(page: Page):
    """
    moveFocus('next')で次のカードにフォーカスが移動することを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # テスト用のカードを作成
    page.evaluate("""
        const container = document.body;
        container.innerHTML = `
            <div class="document-card" data-document-id="1">Card 1</div>
            <div class="document-card" data-document-id="2">Card 2</div>
            <div class="document-card" data-document-id="3">Card 3</div>
        `;
    """)
    
    # CardFocusManagerを初期化してフォーカス移動
    result = page.evaluate("""
        const manager = new CardFocusManager();
        manager.initialize();
        
        // 次のカードにフォーカス移動
        const moved = manager.moveFocus('next');
        
        // 2番目のカードにフォーカスハイライトが付いているか確認
        const secondCard = document.querySelectorAll('.document-card')[1];
        const hasFocus = secondCard.classList.contains('focus-highlight');
        
        // 1番目のカードからフォーカスが外れているか確認
        const firstCard = document.querySelectorAll('.document-card')[0];
        const firstHasNoFocus = !firstCard.classList.contains('focus-highlight');
        
        { moved, hasFocus, firstHasNoFocus };
    """)
    
    assert result['moved'] is True, "フォーカス移動が成功すべき"
    assert result['hasFocus'] is True, "2番目のカードにフォーカスハイライトが設定されるべき"
    assert result['firstHasNoFocus'] is True, "1番目のカードからフォーカスが外れるべき"


def test_card_focus_manager_moves_focus_to_prev(page: Page):
    """
    moveFocus('prev')で前のカードにフォーカスが移動することを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # テスト用のカードを作成
    page.evaluate("""
        const container = document.body;
        container.innerHTML = `
            <div class="document-card" data-document-id="1">Card 1</div>
            <div class="document-card" data-document-id="2">Card 2</div>
            <div class="document-card" data-document-id="3">Card 3</div>
        `;
    """)
    
    # CardFocusManagerを初期化して2番目に移動後、前に戻る
    result = page.evaluate("""
        const manager = new CardFocusManager();
        manager.initialize();
        
        // まず次のカードに移動
        manager.moveFocus('next');
        
        // 前のカードに戻る
        const moved = manager.moveFocus('prev');
        
        // 1番目のカードにフォーカスハイライトが戻っているか確認
        const firstCard = document.querySelectorAll('.document-card')[0];
        const hasFocus = firstCard.classList.contains('focus-highlight');
        
        { moved, hasFocus };
    """)
    
    assert result['moved'] is True, "フォーカス移動が成功すべき"
    assert result['hasFocus'] is True, "1番目のカードにフォーカスハイライトが戻るべき"


def test_card_focus_manager_returns_false_at_list_start(page: Page):
    """
    リスト先頭でprevを実行するとfalseが返ることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # テスト用のカードを作成
    page.evaluate("""
        const container = document.body;
        container.innerHTML = `
            <div class="document-card" data-document-id="1">Card 1</div>
            <div class="document-card" data-document-id="2">Card 2</div>
        `;
    """)
    
    # CardFocusManagerを初期化してリスト先頭でprev実行
    result = page.evaluate("""
        const manager = new CardFocusManager();
        manager.initialize();
        
        // リスト先頭で前に移動を試みる
        const moved = manager.moveFocus('prev');
        
        // 現在のフォーカスインデックスは0のまま
        const currentIndex = manager.getCurrentFocusIndex();
        
        { moved, currentIndex };
    """)
    
    assert result['moved'] is False, "リスト先頭ではフォーカス移動が失敗すべき"
    assert result['currentIndex'] == 0, "フォーカスインデックスは0のままであるべき"


def test_card_focus_manager_returns_false_at_list_end(page: Page):
    """
    リスト末尾でnextを実行するとfalseが返ることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # テスト用のカードを作成
    page.evaluate("""
        const container = document.body;
        container.innerHTML = `
            <div class="document-card" data-document-id="1">Card 1</div>
            <div class="document-card" data-document-id="2">Card 2</div>
        `;
    """)
    
    # CardFocusManagerを初期化してリスト末尾まで移動後、nextを実行
    result = page.evaluate("""
        const manager = new CardFocusManager();
        manager.initialize();
        
        // 末尾まで移動
        manager.moveFocus('next');
        
        // 末尾で次に移動を試みる
        const moved = manager.moveFocus('next');
        
        // 現在のフォーカスインデックスは1のまま（最後）
        const currentIndex = manager.getCurrentFocusIndex();
        
        { moved, currentIndex };
    """)
    
    assert result['moved'] is False, "リスト末尾ではフォーカス移動が失敗すべき"
    assert result['currentIndex'] == 1, "フォーカスインデックスは末尾のままであるべき"


def test_card_focus_manager_scrolls_focused_card_into_view(page: Page):
    """
    フォーカス移動時にカードがビューポート内にスクロールされることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # テスト用のカードを多数作成（ビューポートを超える）
    page.evaluate("""
        const container = document.body;
        let html = '';
        for (let i = 1; i <= 10; i++) {
            html += `<div class="document-card" data-document-id="${i}" style="height: 200px; margin: 10px;">Card ${i}</div>`;
        }
        container.innerHTML = html;
    """)
    
    # CardFocusManagerを初期化して下方のカードにフォーカス移動
    page.evaluate("""
        const manager = new CardFocusManager();
        manager.initialize();
        
        // 5番目のカードまでフォーカス移動（ビューポート外）
        for (let i = 0; i < 4; i++) {
            manager.moveFocus('next');
        }
    """)
    
    # 5番目のカードがビューポート内に表示されているか確認
    is_visible = page.evaluate("""
        const fifthCard = document.querySelectorAll('.document-card')[4];
        const rect = fifthCard.getBoundingClientRect();
        
        // ビューポート内に一部でも表示されているか確認
        rect.top < window.innerHeight && rect.bottom > 0;
    """)
    
    assert is_visible is True, "フォーカスされたカードがビューポート内にスクロールされるべき"


def test_card_focus_manager_only_one_card_has_focus(page: Page):
    """
    常に1つのカードのみがフォーカス状態であることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # テスト用のカードを作成
    page.evaluate("""
        const container = document.body;
        container.innerHTML = `
            <div class="document-card" data-document-id="1">Card 1</div>
            <div class="document-card" data-document-id="2">Card 2</div>
            <div class="document-card" data-document-id="3">Card 3</div>
        `;
    """)
    
    # CardFocusManagerを初期化してフォーカス移動
    result = page.evaluate("""
        const manager = new CardFocusManager();
        manager.initialize();
        
        // 複数回フォーカス移動
        manager.moveFocus('next');
        manager.moveFocus('next');
        
        // フォーカスハイライトが付いているカードの数をカウント
        const focusedCards = document.querySelectorAll('.document-card.focus-highlight');
        focusedCards.length;
    """)
    
    assert result == 1, f"常に1つのカードのみがフォーカス状態であるべき（実際: {result}個）"


def test_card_focus_manager_get_current_focus_index(page: Page):
    """
    getCurrentFocusIndex()で現在のフォーカスインデックスが取得できることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # テスト用のカードを作成
    page.evaluate("""
        const container = document.body;
        container.innerHTML = `
            <div class="document-card" data-document-id="1">Card 1</div>
            <div class="document-card" data-document-id="2">Card 2</div>
            <div class="document-card" data-document-id="3">Card 3</div>
        `;
    """)
    
    # CardFocusManagerを初期化してフォーカス移動
    result = page.evaluate("""
        const manager = new CardFocusManager();
        manager.initialize();
        
        const initialIndex = manager.getCurrentFocusIndex();
        
        manager.moveFocus('next');
        const afterNextIndex = manager.getCurrentFocusIndex();
        
        manager.moveFocus('next');
        const afterSecondNextIndex = manager.getCurrentFocusIndex();
        
        { initialIndex, afterNextIndex, afterSecondNextIndex };
    """)
    
    assert result['initialIndex'] == 0, "初期フォーカスインデックスは0であるべき"
    assert result['afterNextIndex'] == 1, "1回移動後は1であるべき"
    assert result['afterSecondNextIndex'] == 2, "2回移動後は2であるべき"


def test_card_focus_manager_set_focus_by_index(page: Page):
    """
    setFocus(index)で指定インデックスのカードにフォーカスが設定できることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # テスト用のカードを作成
    page.evaluate("""
        const container = document.body;
        container.innerHTML = `
            <div class="document-card" data-document-id="1">Card 1</div>
            <div class="document-card" data-document-id="2">Card 2</div>
            <div class="document-card" data-document-id="3">Card 3</div>
        `;
    """)
    
    # CardFocusManagerを初期化して直接2番目のカードにフォーカス設定
    result = page.evaluate("""
        const manager = new CardFocusManager();
        manager.initialize();
        
        // 直接2番目（インデックス1）のカードにフォーカス設定
        manager.setFocus(1);
        
        // 2番目のカードにフォーカスハイライトが付いているか確認
        const secondCard = document.querySelectorAll('.document-card')[1];
        const hasFocus = secondCard.classList.contains('focus-highlight');
        
        // 現在のフォーカスインデックス
        const currentIndex = manager.getCurrentFocusIndex();
        
        { hasFocus, currentIndex };
    """)
    
    assert result['hasFocus'] is True, "指定インデックスのカードにフォーカスが設定されるべき"
    assert result['currentIndex'] == 1, "現在のフォーカスインデックスが更新されるべき"
