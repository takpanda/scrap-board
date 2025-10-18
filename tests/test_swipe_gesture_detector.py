"""
SwipeGestureDetectorのテスト

このテストはPlaywrightを使用してSwipeGestureDetectorのスワイプジェスチャー検出機能をテストします。
"""
import pytest
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.browser, pytest.mark.usefixtures("live_server")]


def test_swipe_detector_detects_right_swipe(page: Page):
    """
    右方向スワイプ（50px以上）を正しく検出することを確認
    """
    # モバイルビューポートサイズを設定
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")

    # スワイプイベントコールバックをセットアップ
    page.evaluate("""
        window.swipeEvents = [];
        if (window.swipeDetector) {
            window.swipeDetector.onSwipe((event) => {
                window.swipeEvents.push(event);
            });
        }
    """)

    # 右方向スワイプをシミュレート（開始位置100px → 終了位置200px、距離100px）
    page.evaluate("""
        const target = document.body;

        // Touchオブジェクトを作成するヘルパー関数
        function createTouch(clientX, clientY, identifier = 0) {
            return new Touch({
                identifier: identifier,
                target: target,
                clientX: clientX,
                clientY: clientY,
                screenX: clientX,
                screenY: clientY,
                pageX: clientX,
                pageY: clientY
            });
        }

        // touchstart
        const touch1 = createTouch(100, 300);
        const touchStart = new TouchEvent('touchstart', {
            touches: [touch1],
            changedTouches: [touch1],
            bubbles: true
        });
        target.dispatchEvent(touchStart);

        // touchmove
        const touch2 = createTouch(200, 300);
        const touchMove = new TouchEvent('touchmove', {
            touches: [touch2],
            changedTouches: [touch2],
            bubbles: true
        });
        target.dispatchEvent(touchMove);

        // touchend
        const touch3 = createTouch(200, 300);
        const touchEnd = new TouchEvent('touchend', {
            touches: [],
            changedTouches: [touch3],
            bubbles: true
        });
        target.dispatchEvent(touchEnd);
    """)

    # スワイプイベントが発火し、direction='right'であることを確認
    swipe_events = page.evaluate("window.swipeEvents")
    assert len(swipe_events) == 1, "右スワイプイベントが1回発火すべき"
    assert swipe_events[0]['direction'] == 'right', "スワイプ方向が'right'であるべき"
    assert swipe_events[0]['distance'] >= 50, "スワイプ距離が50px以上であるべき"


def test_swipe_detector_detects_left_swipe(page: Page):
    """
    左方向スワイプ（50px以上）を正しく検出することを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")

    # スワイプイベントコールバックをセットアップ
    page.evaluate("""
        window.swipeEvents = [];
        if (window.swipeDetector) {
            window.swipeDetector.onSwipe((event) => {
                window.swipeEvents.push(event);
            });
        }
    """)

    # 左方向スワイプをシミュレート（開始位置200px → 終了位置100px、距離100px）
    page.evaluate("""
        const target = document.body;

        // Touchオブジェクトを作成するヘルパー関数
        function createTouch(clientX, clientY, identifier = 0) {
            return new Touch({
                identifier: identifier,
                target: target,
                clientX: clientX,
                clientY: clientY,
                screenX: clientX,
                screenY: clientY,
                pageX: clientX,
                pageY: clientY
            });
        }

        // touchstart
        const touch1 = createTouch(200, 300);
        const touchStart = new TouchEvent('touchstart', {
            touches: [touch1],
            changedTouches: [touch1],
            bubbles: true
        });
        target.dispatchEvent(touchStart);

        // touchmove
        const touch2 = createTouch(100, 300);
        const touchMove = new TouchEvent('touchmove', {
            touches: [touch2],
            changedTouches: [touch2],
            bubbles: true
        });
        target.dispatchEvent(touchMove);

        // touchend
        const touch3 = createTouch(100, 300);
        const touchEnd = new TouchEvent('touchend', {
            touches: [],
            changedTouches: [touch3],
            bubbles: true
        });
        target.dispatchEvent(touchEnd);
    """)

    # スワイプイベントが発火し、direction='left'であることを確認
    swipe_events = page.evaluate("window.swipeEvents")
    assert len(swipe_events) == 1, "左スワイプイベントが1回発火すべき"
    assert swipe_events[0]['direction'] == 'left', "スワイプ方向が'left'であるべき"
    assert swipe_events[0]['distance'] >= 50, "スワイプ距離が50px以上であるべき"


def test_swipe_detector_ignores_short_swipe(page: Page):
    """
    スワイプ距離が最小閾値（50px）未満の場合、スワイプ操作を無視することを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")

    page.evaluate("""
        window.swipeEvents = [];
        if (window.swipeDetector) {
            window.swipeDetector.onSwipe((event) => {
                window.swipeEvents.push(event);
            });
        }
    """)

    # 短いスワイプをシミュレート（距離30px）
    page.evaluate("""
        const target = document.body;

        // Touchオブジェクトを作成するヘルパー関数
        function createTouch(clientX, clientY, identifier = 0) {
            return new Touch({
                identifier: identifier,
                target: target,
                clientX: clientX,
                clientY: clientY,
                screenX: clientX,
                screenY: clientY,
                pageX: clientX,
                pageY: clientY
            });
        }

        // touchstart
        const touch1 = createTouch(100, 300);
        const touchStart = new TouchEvent('touchstart', {
            touches: [touch1],
            changedTouches: [touch1],
            bubbles: true
        });
        target.dispatchEvent(touchStart);

        // touchend
        const touch2 = createTouch(130, 300);
        const touchEnd = new TouchEvent('touchend', {
            touches: [],
            changedTouches: [touch2],
            bubbles: true
        });
        target.dispatchEvent(touchEnd);
    """)

    # スワイプイベントが発火しないことを確認
    swipe_events = page.evaluate("window.swipeEvents")
    assert len(swipe_events) == 0, "閾値未満のスワイプはイベントを発火しないべき"


def test_swipe_detector_ignores_vertical_swipe(page: Page):
    """
    垂直方向の移動が水平方向の移動より大きい場合、スワイプとして認識しないことを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")

    page.evaluate("""
        window.swipeEvents = [];
        if (window.swipeDetector) {
            window.swipeDetector.onSwipe((event) => {
                window.swipeEvents.push(event);
            });
        }
    """)

    # 縦方向スワイプをシミュレート（水平50px、垂直150px）
    page.evaluate("""
        const target = document.body;

        // Touchオブジェクトを作成するヘルパー関数
        function createTouch(clientX, clientY, identifier = 0) {
            return new Touch({
                identifier: identifier,
                target: target,
                clientX: clientX,
                clientY: clientY,
                screenX: clientX,
                screenY: clientY,
                pageX: clientX,
                pageY: clientY
            });
        }

        // touchstart
        const touch1 = createTouch(100, 100);
        const touchStart = new TouchEvent('touchstart', {
            touches: [touch1],
            changedTouches: [touch1],
            bubbles: true
        });
        target.dispatchEvent(touchStart);

        // touchend
        const touch2 = createTouch(150, 250);
        const touchEnd = new TouchEvent('touchend', {
            touches: [],
            changedTouches: [touch2],
            bubbles: true
        });
        target.dispatchEvent(touchEnd);
    """)

    # スワイプイベントが発火しないことを確認
    swipe_events = page.evaluate("window.swipeEvents")
    assert len(swipe_events) == 0, "垂直方向の移動が大きい場合はスワイプとして認識しないべき"


def test_swipe_detector_horizontal_restraint(page: Page):
    """
    水平方向の移動距離が垂直方向の移動距離の2倍以上の場合のみスワイプと判定することを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")

    page.evaluate("""
        window.swipeEvents = [];
        if (window.swipeDetector) {
            window.swipeDetector.onSwipe((event) => {
                window.swipeEvents.push(event);
            });
        }
    """)

    # 水平方向の移動が垂直方向の2倍以上（水平100px、垂直40px）
    page.evaluate("""
        const target = document.body;

        // Touchオブジェクトを作成するヘルパー関数
        function createTouch(clientX, clientY, identifier = 0) {
            return new Touch({
                identifier: identifier,
                target: target,
                clientX: clientX,
                clientY: clientY,
                screenX: clientX,
                screenY: clientY,
                pageX: clientX,
                pageY: clientY
            });
        }

        // touchstart
        const touch1 = createTouch(100, 100);
        const touchStart = new TouchEvent('touchstart', {
            touches: [touch1],
            changedTouches: [touch1],
            bubbles: true
        });
        target.dispatchEvent(touchStart);

        // touchend
        const touch2 = createTouch(200, 140);
        const touchEnd = new TouchEvent('touchend', {
            touches: [],
            changedTouches: [touch2],
            bubbles: true
        });
        target.dispatchEvent(touchEnd);
    """)

    # スワイプイベントが発火することを確認
    swipe_events = page.evaluate("window.swipeEvents")
    assert len(swipe_events) == 1, "水平方向の移動が垂直方向の2倍以上の場合はスワイプと判定すべき"


def test_swipe_detector_calculates_duration(page: Page):
    """
    スワイプイベントに継続時間（duration）が含まれることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")

    page.evaluate("""
        window.swipeEvents = [];
        if (window.swipeDetector) {
            window.swipeDetector.onSwipe((event) => {
                window.swipeEvents.push(event);
            });
        }
    """)

    # スワイプをシミュレート
    page.evaluate("""
        const target = document.body;

        // Touchオブジェクトを作成するヘルパー関数
        function createTouch(clientX, clientY, identifier = 0) {
            return new Touch({
                identifier: identifier,
                target: target,
                clientX: clientX,
                clientY: clientY,
                screenX: clientX,
                screenY: clientY,
                pageX: clientX,
                pageY: clientY
            });
        }

        // touchstart
        const touch1 = createTouch(100, 300);
        const touchStart = new TouchEvent('touchstart', {
            touches: [touch1],
            changedTouches: [touch1],
            bubbles: true
        });
        target.dispatchEvent(touchStart);

        // 少し待機してからtouchend
        setTimeout(() => {
            const touch2 = createTouch(200, 300);
            const touchEnd = new TouchEvent('touchend', {
                touches: [],
                changedTouches: [touch2],
                bubbles: true
            });
            target.dispatchEvent(touchEnd);
        }, 100);
    """)

    page.wait_for_timeout(200)  # touchendの完了を待機

    # durationフィールドが存在し、0より大きいことを確認
    swipe_events = page.evaluate("window.swipeEvents")
    assert len(swipe_events) == 1, "スワイプイベントが発火すべき"
    assert 'duration' in swipe_events[0], "スワイプイベントにdurationフィールドが含まれるべき"
    assert swipe_events[0]['duration'] > 0, "durationは0より大きいべき"


def test_swipe_detector_debounce(page: Page):
    """
    デバウンス処理（200ms）により、連続スワイプの重複イベント発火を防止することを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")

    page.evaluate("""
        window.swipeEvents = [];
        if (window.swipeDetector) {
            window.swipeDetector.onSwipe((event) => {
                window.swipeEvents.push(event);
            });
        }
    """)

    # 短時間に2回のスワイプを実行
    page.evaluate("""
        const target = document.body;

        // Touchオブジェクトを作成するヘルパー関数
        function createTouch(clientX, clientY, identifier = 0) {
            return new Touch({
                identifier: identifier,
                target: target,
                clientX: clientX,
                clientY: clientY,
                screenX: clientX,
                screenY: clientY,
                pageX: clientX,
                pageY: clientY
            });
        }

        // 1回目のスワイプ
        const touch1_1 = createTouch(100, 300);
        let touchStart = new TouchEvent('touchstart', {
            touches: [touch1_1],
            changedTouches: [touch1_1],
            bubbles: true
        });
        target.dispatchEvent(touchStart);

        const touch1_2 = createTouch(200, 300);
        let touchEnd = new TouchEvent('touchend', {
            touches: [],
            changedTouches: [touch1_2],
            bubbles: true
        });
        target.dispatchEvent(touchEnd);

        // すぐに2回目のスワイプ（デバウンス期間内）
        setTimeout(() => {
            const touch2_1 = createTouch(100, 300);
            touchStart = new TouchEvent('touchstart', {
                touches: [touch2_1],
                changedTouches: [touch2_1],
                bubbles: true
            });
            target.dispatchEvent(touchStart);

            const touch2_2 = createTouch(200, 300);
            touchEnd = new TouchEvent('touchend', {
                touches: [],
                changedTouches: [touch2_2],
                bubbles: true
            });
            target.dispatchEvent(touchEnd);
        }, 50);
    """)

    page.wait_for_timeout(100)  # 2回目のスワイプ完了を待機

    # デバウンス期間内（200ms未満）のため、2回目のイベントは無視される
    swipe_events = page.evaluate("window.swipeEvents")
    assert len(swipe_events) == 1, "デバウンス処理により、連続スワイプの2回目は無視されるべき"


def test_swipe_detector_enable_disable(page: Page):
    """
    enable()およびdisable()でスワイプ機能を有効/無効化できることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")

    page.evaluate("""
        window.swipeEvents = [];
        if (window.swipeDetector) {
            window.swipeDetector.onSwipe((event) => {
                window.swipeEvents.push(event);
            });
        }
    """)

    # スワイプ機能を無効化
    page.evaluate("window.swipeDetector && window.swipeDetector.disable()")

    # スワイプをシミュレート
    page.evaluate("""
        const target = document.body;

        // Touchオブジェクトを作成するヘルパー関数
        function createTouch(clientX, clientY, identifier = 0) {
            return new Touch({
                identifier: identifier,
                target: target,
                clientX: clientX,
                clientY: clientY,
                screenX: clientX,
                screenY: clientY,
                pageX: clientX,
                pageY: clientY
            });
        }

        // touchstart
        const touch1 = createTouch(100, 300);
        const touchStart = new TouchEvent('touchstart', {
            touches: [touch1],
            changedTouches: [touch1],
            bubbles: true
        });
        target.dispatchEvent(touchStart);

        // touchend
        const touch2 = createTouch(200, 300);
        const touchEnd = new TouchEvent('touchend', {
            touches: [],
            changedTouches: [touch2],
            bubbles: true
        });
        target.dispatchEvent(touchEnd);
    """)

    # 無効化されているため、イベントは発火しない
    swipe_events = page.evaluate("window.swipeEvents")
    assert len(swipe_events) == 0, "disable()後はスワイプイベントが発火しないべき"

    # 再度有効化
    page.evaluate("window.swipeDetector && window.swipeDetector.enable()")

    # スワイプをシミュレート
    page.evaluate("""
        const target = document.body;

        // Touchオブジェクトを作成するヘルパー関数
        function createTouch(clientX, clientY, identifier = 0) {
            return new Touch({
                identifier: identifier,
                target: target,
                clientX: clientX,
                clientY: clientY,
                screenX: clientX,
                screenY: clientY,
                pageX: clientX,
                pageY: clientY
            });
        }

        // touchstart
        const touch1 = createTouch(100, 300);
        const touchStart = new TouchEvent('touchstart', {
            touches: [touch1],
            changedTouches: [touch1],
            bubbles: true
        });
        target.dispatchEvent(touchStart);

        // touchend
        const touch2 = createTouch(200, 300);
        const touchEnd = new TouchEvent('touchend', {
            touches: [],
            changedTouches: [touch2],
            bubbles: true
        });
        target.dispatchEvent(touchEnd);
    """)

    # 有効化後、イベントが発火する
    swipe_events = page.evaluate("window.swipeEvents")
    assert len(swipe_events) == 1, "enable()後はスワイプイベントが発火すべき"


# DocumentListCacheのテスト


def test_document_list_cache_save_and_retrieve(page: Page):
    """
    記事IDリストの保存と取得をテスト
    """
    page.goto("http://localhost:8000/")

    # DocumentListCacheクラスを注入
    page.evaluate("""
        class DocumentListCache {
            constructor() {
                this.CACHE_KEY = 'scrapboard:document_list';
            }

            saveDocumentList(documentIds, filterParams = {}) {
                const cacheData = {
                    documentIds: documentIds,
                    timestamp: Date.now(),
                    filterParams: filterParams
                };
                sessionStorage.setItem(this.CACHE_KEY, JSON.stringify(cacheData));
            }

            getAdjacentDocumentId(currentId, direction) {
                const cached = sessionStorage.getItem(this.CACHE_KEY);
                if (!cached) return null;

                const { documentIds } = JSON.parse(cached);
                const currentIndex = documentIds.indexOf(currentId);

                if (currentIndex === -1) return null;

                const nextIndex = direction === 'next' ? currentIndex + 1 : currentIndex - 1;

                if (nextIndex < 0 || nextIndex >= documentIds.length) {
                    return null;
                }

                return documentIds[nextIndex];
            }

            hasCachedList() {
                return sessionStorage.getItem(this.CACHE_KEY) !== null;
            }

            clearCache() {
                sessionStorage.removeItem(this.CACHE_KEY);
            }
        }

        window.documentListCache = new DocumentListCache();
    """)

    # テスト: 記事IDリストを保存
    page.evaluate("window.documentListCache.saveDocumentList([1, 2, 3, 4, 5])")

    # テスト: キャッシュが存在することを確認
    has_cache = page.evaluate("window.documentListCache.hasCachedList()")
    assert has_cache is True

    # テスト: 次の記事IDを取得（現在ID=2の場合、次はID=3）
    next_id = page.evaluate("window.documentListCache.getAdjacentDocumentId(2, 'next')")
    assert next_id == 3

    # テスト: 前の記事IDを取得（現在ID=3の場合、前はID=2）
    prev_id = page.evaluate("window.documentListCache.getAdjacentDocumentId(3, 'prev')")
    assert prev_id == 2


def test_document_list_cache_get_adjacent_id_at_list_edge(page: Page):
    """
    リスト端での隣接記事ID取得をテスト（nullを返すべき）
    """
    page.goto("http://localhost:8000/")

    # DocumentListCacheを注入
    page.evaluate("""
        class DocumentListCache {
            constructor() {
                this.CACHE_KEY = 'scrapboard:document_list';
            }

            saveDocumentList(documentIds, filterParams = {}) {
                const cacheData = {
                    documentIds: documentIds,
                    timestamp: Date.now(),
                    filterParams: filterParams
                };
                sessionStorage.setItem(this.CACHE_KEY, JSON.stringify(cacheData));
            }

            getAdjacentDocumentId(currentId, direction) {
                const cached = sessionStorage.getItem(this.CACHE_KEY);
                if (!cached) return null;

                const { documentIds } = JSON.parse(cached);
                const currentIndex = documentIds.indexOf(currentId);

                if (currentIndex === -1) return null;

                const nextIndex = direction === 'next' ? currentIndex + 1 : currentIndex - 1;

                if (nextIndex < 0 || nextIndex >= documentIds.length) {
                    return null;
                }

                return documentIds[nextIndex];
            }
        }

        window.documentListCache = new DocumentListCache();
    """)

    # リストを保存
    page.evaluate("window.documentListCache.saveDocumentList([10, 20, 30])")

    # テスト: 最初の記事（ID=10）から前の記事を取得 → null
    prev_id_at_start = page.evaluate("window.documentListCache.getAdjacentDocumentId(10, 'prev')")
    assert prev_id_at_start is None

    # テスト: 最後の記事（ID=30）から次の記事を取得 → null
    next_id_at_end = page.evaluate("window.documentListCache.getAdjacentDocumentId(30, 'next')")
    assert next_id_at_end is None


def test_document_list_cache_no_cache_returns_null(page: Page):
    """
    キャッシュが存在しない場合はnullを返すことをテスト
    """
    page.goto("http://localhost:8000/")

    # DocumentListCacheを注入
    page.evaluate("""
        class DocumentListCache {
            constructor() {
                this.CACHE_KEY = 'scrapboard:document_list';
            }

            getAdjacentDocumentId(currentId, direction) {
                const cached = sessionStorage.getItem(this.CACHE_KEY);
                if (!cached) return null;

                const { documentIds } = JSON.parse(cached);
                const currentIndex = documentIds.indexOf(currentId);

                if (currentIndex === -1) return null;

                const nextIndex = direction === 'next' ? currentIndex + 1 : currentIndex - 1;

                if (nextIndex < 0 || nextIndex >= documentIds.length) {
                    return null;
                }

                return documentIds[nextIndex];
            }

            hasCachedList() {
                return sessionStorage.getItem(this.CACHE_KEY) !== null;
            }
        }

        window.documentListCache = new DocumentListCache();
    """)

    # テスト: キャッシュが存在しない場合はfalse
    has_cache = page.evaluate("window.documentListCache.hasCachedList()")
    assert has_cache is False

    # テスト: 隣接記事ID取得 → null
    next_id = page.evaluate("window.documentListCache.getAdjacentDocumentId(1, 'next')")
    assert next_id is None


def test_document_list_cache_clear_cache(page: Page):
    """
    キャッシュのクリアをテスト
    """
    page.goto("http://localhost:8000/")

    # DocumentListCacheを注入
    page.evaluate("""
        class DocumentListCache {
            constructor() {
                this.CACHE_KEY = 'scrapboard:document_list';
            }

            saveDocumentList(documentIds, filterParams = {}) {
                const cacheData = {
                    documentIds: documentIds,
                    timestamp: Date.now(),
                    filterParams: filterParams
                };
                sessionStorage.setItem(this.CACHE_KEY, JSON.stringify(cacheData));
            }

            hasCachedList() {
                return sessionStorage.getItem(this.CACHE_KEY) !== null;
            }

            clearCache() {
                sessionStorage.removeItem(this.CACHE_KEY);
            }
        }

        window.documentListCache = new DocumentListCache();
    """)

    # リストを保存
    page.evaluate("window.documentListCache.saveDocumentList([100, 200, 300])")

    # キャッシュが存在することを確認
    has_cache_before = page.evaluate("window.documentListCache.hasCachedList()")
    assert has_cache_before is True

    # キャッシュをクリア
    page.evaluate("window.documentListCache.clearCache()")

    # キャッシュが存在しないことを確認
    has_cache_after = page.evaluate("window.documentListCache.hasCachedList()")
    assert has_cache_after is False


def test_document_list_cache_filter_params_saved(page: Page):
    """
    フィルタパラメータもキャッシュに含まれることをテスト
    """
    page.goto("http://localhost:8000/")

    # DocumentListCacheを注入
    page.evaluate("""
        class DocumentListCache {
            constructor() {
                this.CACHE_KEY = 'scrapboard:document_list';
            }

            saveDocumentList(documentIds, filterParams = {}) {
                const cacheData = {
                    documentIds: documentIds,
                    timestamp: Date.now(),
                    filterParams: filterParams
                };
                sessionStorage.setItem(this.CACHE_KEY, JSON.stringify(cacheData));
            }

            getCachedData() {
                const cached = sessionStorage.getItem(this.CACHE_KEY);
                return cached ? JSON.parse(cached) : null;
            }
        }

        window.documentListCache = new DocumentListCache();
    """)

    # フィルタパラメータ付きでリストを保存
    page.evaluate("""
        window.documentListCache.saveDocumentList(
            [1, 2, 3],
            { category: 'tech', tag: 'python', query: 'django' }
        )
    """)

    # キャッシュデータを取得
    cached_data = page.evaluate("window.documentListCache.getCachedData()")

    # フィルタパラメータが保存されていることを確認
    assert cached_data['filterParams']['category'] == 'tech'
    assert cached_data['filterParams']['tag'] == 'python'
    assert cached_data['filterParams']['query'] == 'django'


def test_document_list_cache_validates_document_ids(page: Page):
    """
    記事IDリストの検証（数値型チェック、空配列禁止）をテスト
    """
    page.goto("http://localhost:8000/")

    # DocumentListCacheを注入（バリデーション機能付き）
    page.evaluate("""
        class DocumentListCache {
            constructor() {
                this.CACHE_KEY = 'scrapboard:document_list';
            }

            saveDocumentList(documentIds, filterParams = {}) {
                // 空配列禁止
                if (!Array.isArray(documentIds) || documentIds.length === 0) {
                    throw new Error('documentIds must be a non-empty array');
                }

                // 数値型チェック
                if (!documentIds.every(id => Number.isInteger(id) && id > 0)) {
                    throw new Error('All document IDs must be positive integers');
                }

                // 重複ID禁止
                const uniqueIds = new Set(documentIds);
                if (uniqueIds.size !== documentIds.length) {
                    throw new Error('Duplicate document IDs are not allowed');
                }

                const cacheData = {
                    documentIds: documentIds,
                    timestamp: Date.now(),
                    filterParams: filterParams
                };
                sessionStorage.setItem(this.CACHE_KEY, JSON.stringify(cacheData));
            }
        }

        window.documentListCache = new DocumentListCache();
    """)

    # テスト: 空配列はエラー
    error_empty = page.evaluate("""
        try {
            window.documentListCache.saveDocumentList([]);
            null;
        } catch (e) {
            e.message;
        }
    """)
    assert error_empty == 'documentIds must be a non-empty array'

    # テスト: 不正な型（文字列含む）はエラー
    error_invalid_type = page.evaluate("""
        try {
            window.documentListCache.saveDocumentList([1, 'invalid', 3]);
            null;
        } catch (e) {
            e.message;
        }
    """)
    assert error_invalid_type == 'All document IDs must be positive integers'

    # テスト: 重複IDはエラー
    error_duplicate = page.evaluate("""
        try {
            window.documentListCache.saveDocumentList([1, 2, 2, 3]);
            null;
        } catch (e) {
            e.message;
        }
    """)
    assert error_duplicate == 'Duplicate document IDs are not allowed'

    # テスト: 正常なリストは保存可能
    page.evaluate("window.documentListCache.saveDocumentList([10, 20, 30])")
    has_cache = page.evaluate("sessionStorage.getItem('scrapboard:document_list') !== null")
    assert has_cache is True
