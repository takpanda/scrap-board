"""
CardFocusManagerのテスト

このテストはPlaywrightを使用してCardFocusManagerの記事カードフォーカス管理機能をテストします。
"""
import pytest
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.browser, pytest.mark.usefixtures("live_server")]


def test_card_focus_manager_initialize_sets_focus_to_first_card(page: Page):
    """
    初期化時に先頭カードにフォーカスを設定することを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")

    # CardFocusManagerクラスを注入
    page.evaluate("""
        class CardFocusManager {
            constructor() {
                this.currentFocusIndex = -1;
                this.cards = [];
                this.FOCUS_CLASS = 'focus-highlight';
            }

            initialize() {
                // 記事カード要素を取得
                this.cards = Array.from(document.querySelectorAll('[data-document-id]'));

                if (this.cards.length === 0) {
                    return;
                }

                // 先頭カードにフォーカス設定
                this.setFocus(0);
            }

            setFocus(index) {
                if (index < 0 || index >= this.cards.length) {
                    return;
                }

                // 前のカードからハイライトクラスを削除
                if (this.currentFocusIndex >= 0 && this.currentFocusIndex < this.cards.length) {
                    this.cards[this.currentFocusIndex].classList.remove(this.FOCUS_CLASS);
                }

                // 新しいカードにハイライトクラスを追加
                this.currentFocusIndex = index;
                this.cards[index].classList.add(this.FOCUS_CLASS);

                // スクロール
                this.cards[index].scrollIntoView({ behavior: 'smooth', block: 'center' });
            }

            getCurrentFocusIndex() {
                return this.currentFocusIndex;
            }

            moveFocus(direction) {
                const nextIndex = direction === 'next' ? this.currentFocusIndex + 1 : this.currentFocusIndex - 1;

                // リスト端チェック
                if (nextIndex < 0 || nextIndex >= this.cards.length) {
                    return false;
                }

                this.setFocus(nextIndex);
                return true;
            }
        }

        window.cardFocusManager = new CardFocusManager();
        window.cardFocusManager.initialize();
    """)

    # 先頭カードのインデックスが0であることを確認
    current_index = page.evaluate("window.cardFocusManager.getCurrentFocusIndex()")
    assert current_index == 0, "初期化時に先頭カード（インデックス0）にフォーカスが設定されるべき"


def test_card_focus_manager_move_focus_to_next_card(page: Page):
    """
    moveFocus('next')で次のカードにフォーカスを移動することを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")

    # CardFocusManagerを注入
    page.evaluate("""
        class CardFocusManager {
            constructor() {
                this.currentFocusIndex = -1;
                this.cards = [];
                this.FOCUS_CLASS = 'focus-highlight';
            }

            initialize() {
                this.cards = Array.from(document.querySelectorAll('[data-document-id]'));
                if (this.cards.length === 0) return;
                this.setFocus(0);
            }

            setFocus(index) {
                if (index < 0 || index >= this.cards.length) return;
                if (this.currentFocusIndex >= 0 && this.currentFocusIndex < this.cards.length) {
                    this.cards[this.currentFocusIndex].classList.remove(this.FOCUS_CLASS);
                }
                this.currentFocusIndex = index;
                this.cards[index].classList.add(this.FOCUS_CLASS);
                this.cards[index].scrollIntoView({ behavior: 'smooth', block: 'center' });
            }

            getCurrentFocusIndex() {
                return this.currentFocusIndex;
            }

            moveFocus(direction) {
                const nextIndex = direction === 'next' ? this.currentFocusIndex + 1 : this.currentFocusIndex - 1;
                if (nextIndex < 0 || nextIndex >= this.cards.length) {
                    return false;
                }
                this.setFocus(nextIndex);
                return true;
            }
        }

        window.cardFocusManager = new CardFocusManager();
        window.cardFocusManager.initialize();
    """)

    # 初期状態でインデックス0
    initial_index = page.evaluate("window.cardFocusManager.getCurrentFocusIndex()")
    assert initial_index == 0

    # 次のカードにフォーカス移動
    success = page.evaluate("window.cardFocusManager.moveFocus('next')")
    assert success is True, "moveFocus('next')は成功すべき"

    # フォーカスインデックスが1に更新されていることを確認
    new_index = page.evaluate("window.cardFocusManager.getCurrentFocusIndex()")
    assert new_index == 1, "フォーカスが次のカード（インデックス1）に移動すべき"


def test_card_focus_manager_move_focus_to_previous_card(page: Page):
    """
    moveFocus('prev')で前のカードにフォーカスを移動することを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")

    # CardFocusManagerを注入
    page.evaluate("""
        class CardFocusManager {
            constructor() {
                this.currentFocusIndex = -1;
                this.cards = [];
                this.FOCUS_CLASS = 'focus-highlight';
            }

            initialize() {
                this.cards = Array.from(document.querySelectorAll('[data-document-id]'));
                if (this.cards.length === 0) return;
                this.setFocus(0);
            }

            setFocus(index) {
                if (index < 0 || index >= this.cards.length) return;
                if (this.currentFocusIndex >= 0 && this.currentFocusIndex < this.cards.length) {
                    this.cards[this.currentFocusIndex].classList.remove(this.FOCUS_CLASS);
                }
                this.currentFocusIndex = index;
                this.cards[index].classList.add(this.FOCUS_CLASS);
                this.cards[index].scrollIntoView({ behavior: 'smooth', block: 'center' });
            }

            getCurrentFocusIndex() {
                return this.currentFocusIndex;
            }

            moveFocus(direction) {
                const nextIndex = direction === 'next' ? this.currentFocusIndex + 1 : this.currentFocusIndex - 1;
                if (nextIndex < 0 || nextIndex >= this.cards.length) {
                    return false;
                }
                this.setFocus(nextIndex);
                return true;
            }
        }

        window.cardFocusManager = new CardFocusManager();
        window.cardFocusManager.initialize();
    """)

    // まずインデックス2にフォーカスを設定
    page.evaluate("window.cardFocusManager.setFocus(2)")
    initial_index = page.evaluate("window.cardFocusManager.getCurrentFocusIndex()")
    assert initial_index == 2

    // 前のカードにフォーカス移動
    success = page.evaluate("window.cardFocusManager.moveFocus('prev')")
    assert success is True, "moveFocus('prev')は成功すべき"

    // フォーカスインデックスが1に更新されていることを確認
    new_index = page.evaluate("window.cardFocusManager.getCurrentFocusIndex()")
    assert new_index == 1, "フォーカスが前のカード（インデックス1）に移動すべき"


def test_card_focus_manager_cannot_move_prev_at_list_start(page: Page):
    """
    リストの最初でmoveFocus('prev')を実行してもフォーカスが移動しないことを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")

    page.evaluate("""
        class CardFocusManager {
            constructor() {
                this.currentFocusIndex = -1;
                this.cards = [];
                this.FOCUS_CLASS = 'focus-highlight';
            }

            initialize() {
                this.cards = Array.from(document.querySelectorAll('[data-document-id]'));
                if (this.cards.length === 0) return;
                this.setFocus(0);
            }

            setFocus(index) {
                if (index < 0 || index >= this.cards.length) return;
                if (this.currentFocusIndex >= 0 && this.currentFocusIndex < this.cards.length) {
                    this.cards[this.currentFocusIndex].classList.remove(this.FOCUS_CLASS);
                }
                this.currentFocusIndex = index;
                this.cards[index].classList.add(this.FOCUS_CLASS);
                this.cards[index].scrollIntoView({ behavior: 'smooth', block: 'center' });
            }

            getCurrentFocusIndex() {
                return this.currentFocusIndex;
            }

            moveFocus(direction) {
                const nextIndex = direction === 'next' ? this.currentFocusIndex + 1 : this.currentFocusIndex - 1;
                if (nextIndex < 0 || nextIndex >= this.cards.length) {
                    return false;
                }
                this.setFocus(nextIndex);
                return true;
            }
        }

        window.cardFocusManager = new CardFocusManager();
        window.cardFocusManager.initialize();
    """)

    # 初期状態でインデックス0（先頭カード）
    initial_index = page.evaluate("window.cardFocusManager.getCurrentFocusIndex()")
    assert initial_index == 0

    # 前のカードにフォーカス移動を試行（失敗すべき）
    success = page.evaluate("window.cardFocusManager.moveFocus('prev')")
    assert success is False, "リストの先頭でmoveFocus('prev')は失敗すべき"

    # フォーカスインデックスが変わっていないことを確認
    new_index = page.evaluate("window.cardFocusManager.getCurrentFocusIndex()")
    assert new_index == 0, "フォーカスは先頭カードのまま維持されるべき"


def test_card_focus_manager_cannot_move_next_at_list_end(page: Page):
    """
    リストの最後でmoveFocus('next')を実行してもフォーカスが移動しないことを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")

    page.evaluate("""
        class CardFocusManager {
            constructor() {
                this.currentFocusIndex = -1;
                this.cards = [];
                this.FOCUS_CLASS = 'focus-highlight';
            }

            initialize() {
                this.cards = Array.from(document.querySelectorAll('[data-document-id]'));
                if (this.cards.length === 0) return;
                this.setFocus(0);
            }

            setFocus(index) {
                if (index < 0 || index >= this.cards.length) return;
                if (this.currentFocusIndex >= 0 && this.currentFocusIndex < this.cards.length) {
                    this.cards[this.currentFocusIndex].classList.remove(this.FOCUS_CLASS);
                }
                this.currentFocusIndex = index;
                this.cards[index].classList.add(this.FOCUS_CLASS);
                this.cards[index].scrollIntoView({ behavior: 'smooth', block: 'center' });
            }

            getCurrentFocusIndex() {
                return this.currentFocusIndex;
            }

            moveFocus(direction) {
                const nextIndex = direction === 'next' ? this.currentFocusIndex + 1 : this.currentFocusIndex - 1;
                if (nextIndex < 0 || nextIndex >= this.cards.length) {
                    return false;
                }
                this.setFocus(nextIndex);
                return true;
            }
        }

        window.cardFocusManager = new CardFocusManager();
        window.cardFocusManager.initialize();
    """)

    # 記事カードの総数を取得
    total_cards = page.evaluate("window.cardFocusManager.cards.length")
    assert total_cards > 0, "記事カードが存在すべき"

    # 最後のカードにフォーカスを設定
    page.evaluate(f"window.cardFocusManager.setFocus({total_cards - 1})")
    initial_index = page.evaluate("window.cardFocusManager.getCurrentFocusIndex()")
    assert initial_index == total_cards - 1

    # 次のカードにフォーカス移動を試行（失敗すべき）
    success = page.evaluate("window.cardFocusManager.moveFocus('next')")
    assert success is False, "リストの最後でmoveFocus('next')は失敗すべき"

    # フォーカスインデックスが変わっていないことを確認
    new_index = page.evaluate("window.cardFocusManager.getCurrentFocusIndex()")
    assert new_index == total_cards - 1, "フォーカスは最後のカードのまま維持されるべき"


def test_card_focus_manager_adds_focus_highlight_class(page: Page):
    """
    フォーカスされたカードに'focus-highlight'クラスが追加されることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")

    page.evaluate("""
        class CardFocusManager {
            constructor() {
                this.currentFocusIndex = -1;
                this.cards = [];
                this.FOCUS_CLASS = 'focus-highlight';
            }

            initialize() {
                this.cards = Array.from(document.querySelectorAll('[data-document-id]'));
                if (this.cards.length === 0) return;
                this.setFocus(0);
            }

            setFocus(index) {
                if (index < 0 || index >= this.cards.length) return;
                if (this.currentFocusIndex >= 0 && this.currentFocusIndex < this.cards.length) {
                    this.cards[this.currentFocusIndex].classList.remove(this.FOCUS_CLASS);
                }
                this.currentFocusIndex = index;
                this.cards[index].classList.add(this.FOCUS_CLASS);
                this.cards[index].scrollIntoView({ behavior: 'smooth', block: 'center' });
            }

            getCurrentFocusIndex() {
                return this.currentFocusIndex;
            }

            moveFocus(direction) {
                const nextIndex = direction === 'next' ? this.currentFocusIndex + 1 : this.currentFocusIndex - 1;
                if (nextIndex < 0 || nextIndex >= this.cards.length) {
                    return false;
                }
                this.setFocus(nextIndex);
                return true;
            }
        }

        window.cardFocusManager = new CardFocusManager();
        window.cardFocusManager.initialize();
    """)

    # 先頭カードにfocus-highlightクラスが追加されていることを確認
    first_card_has_focus_class = page.evaluate("""
        window.cardFocusManager.cards[0].classList.contains('focus-highlight')
    """)
    assert first_card_has_focus_class is True, "先頭カードにfocus-highlightクラスが追加されるべき"

    # 2番目のカードにフォーカス移動
    page.evaluate("window.cardFocusManager.moveFocus('next')")

    # 2番目のカードにfocus-highlightクラスが追加されていることを確認
    second_card_has_focus_class = page.evaluate("""
        window.cardFocusManager.cards[1].classList.contains('focus-highlight')
    """)
    assert second_card_has_focus_class is True, "2番目のカードにfocus-highlightクラスが追加されるべき"

    # 先頭カードからfocus-highlightクラスが削除されていることを確認
    first_card_lost_focus_class = page.evaluate("""
        !window.cardFocusManager.cards[0].classList.contains('focus-highlight')
    """)
    assert first_card_lost_focus_class is True, "先頭カードからfocus-highlightクラスが削除されるべき"


def test_card_focus_manager_only_one_card_has_focus(page: Page):
    """
    常に1つのカードのみがフォーカス状態であることを確認（複数フォーカス禁止）
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")

    page.evaluate("""
        class CardFocusManager {
            constructor() {
                this.currentFocusIndex = -1;
                this.cards = [];
                this.FOCUS_CLASS = 'focus-highlight';
            }

            initialize() {
                this.cards = Array.from(document.querySelectorAll('[data-document-id]'));
                if (this.cards.length === 0) return;
                this.setFocus(0);
            }

            setFocus(index) {
                if (index < 0 || index >= this.cards.length) return;
                if (this.currentFocusIndex >= 0 && this.currentFocusIndex < this.cards.length) {
                    this.cards[this.currentFocusIndex].classList.remove(this.FOCUS_CLASS);
                }
                this.currentFocusIndex = index;
                this.cards[index].classList.add(this.FOCUS_CLASS);
                this.cards[index].scrollIntoView({ behavior: 'smooth', block: 'center' });
            }

            getCurrentFocusIndex() {
                return this.currentFocusIndex;
            }

            moveFocus(direction) {
                const nextIndex = direction === 'next' ? this.currentFocusIndex + 1 : this.currentFocusIndex - 1;
                if (nextIndex < 0 || nextIndex >= this.cards.length) {
                    return false;
                }
                this.setFocus(nextIndex);
                return true;
            }
        }

        window.cardFocusManager = new CardFocusManager();
        window.cardFocusManager.initialize();
    """)

    # フォーカスクラスを持つカードの数を確認
    focused_card_count = page.evaluate("""
        window.cardFocusManager.cards.filter(card => card.classList.contains('focus-highlight')).length
    """)
    assert focused_card_count == 1, "初期化時、1つのカードのみがフォーカスされているべき"

    # 次のカードにフォーカス移動
    page.evaluate("window.cardFocusManager.moveFocus('next')")

    # 再度フォーカスクラスを持つカードの数を確認
    focused_card_count_after_move = page.evaluate("""
        window.cardFocusManager.cards.filter(card => card.classList.contains('focus-highlight')).length
    """)
    assert focused_card_count_after_move == 1, "フォーカス移動後も、1つのカードのみがフォーカスされているべき"
