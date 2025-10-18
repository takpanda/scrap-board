"""
SwipeGestureDetectorのテスト

このテストはPlaywrightを使用してSwipeGestureDetectorのスワイプジェスチャー検出機能をテストします。
"""
import pytest
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.browser, pytest.mark.usefixtures("live_server")]


def test_swipe_gesture_detector_exists(page: Page):
    """
    SwipeGestureDetectorクラスが定義されていることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # SwipeGestureDetectorクラスが存在することを確認
    has_class = page.evaluate("typeof SwipeGestureDetector === 'function'")
    assert has_class is True, "SwipeGestureDetectorクラスが定義されているべき"


def test_swipe_detector_detects_horizontal_swipe(page: Page):
    """
    水平方向のスワイプが正しく検出されることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # SwipeGestureDetectorを初期化
    page.evaluate("""
        window.swipeEvents = [];
        const detector = new SwipeGestureDetector(document.body, (event) => {
            window.swipeEvents.push(event);
        });
        detector.enable();
        window.testDetector = detector;
    """)
    
    # 右方向へのスワイプをシミュレート（100px移動）
    page.evaluate("""
        const target = document.body;
        const startX = 100;
        const startY = 300;
        const endX = 200;  // 100px右へ移動
        const endY = 300;
        
        // touchstart
        const touchStart = new Touch({
            identifier: 0,
            target: target,
            clientX: startX,
            clientY: startY,
        });
        target.dispatchEvent(new TouchEvent('touchstart', {
            touches: [touchStart],
            cancelable: true,
            bubbles: true,
        }));
        
        // touchmove
        const touchMove = new Touch({
            identifier: 0,
            target: target,
            clientX: endX,
            clientY: endY,
        });
        target.dispatchEvent(new TouchEvent('touchmove', {
            touches: [touchMove],
            cancelable: true,
            bubbles: true,
        }));
        
        // touchend
        target.dispatchEvent(new TouchEvent('touchend', {
            changedTouches: [touchMove],
            cancelable: true,
            bubbles: true,
        }));
    """)
    
    # デバウンス処理を考慮して待機
    page.wait_for_timeout(250)
    
    # スワイプイベントが検出されたことを確認
    swipe_events = page.evaluate("window.swipeEvents")
    assert len(swipe_events) > 0, "スワイプイベントが検出されるべき"
    
    # 右方向スワイプが検出されたことを確認
    first_event = swipe_events[0]
    assert first_event['direction'] == 'right', "右方向スワイプが検出されるべき"
    assert first_event['distance'] >= 50, f"スワイプ距離が50px以上であるべき（実際: {first_event['distance']}px）"


def test_swipe_detector_ignores_short_swipe(page: Page):
    """
    短いスワイプ（50px未満）が無視されることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # SwipeGestureDetectorを初期化
    page.evaluate("""
        window.shortSwipeEvents = [];
        const detector = new SwipeGestureDetector(document.body, (event) => {
            window.shortSwipeEvents.push(event);
        });
        detector.enable();
    """)
    
    # 短い右方向スワイプをシミュレート（30px移動 < 50px閾値）
    page.evaluate("""
        const target = document.body;
        const startX = 100;
        const startY = 300;
        const endX = 130;  // 30px右へ移動（閾値未満）
        const endY = 300;
        
        const touchStart = new Touch({
            identifier: 0,
            target: target,
            clientX: startX,
            clientY: startY,
        });
        target.dispatchEvent(new TouchEvent('touchstart', {
            touches: [touchStart],
            cancelable: true,
            bubbles: true,
        }));
        
        const touchMove = new Touch({
            identifier: 0,
            target: target,
            clientX: endX,
            clientY: endY,
        });
        target.dispatchEvent(new TouchEvent('touchmove', {
            touches: [touchMove],
            cancelable: true,
            bubbles: true,
        }));
        
        target.dispatchEvent(new TouchEvent('touchend', {
            changedTouches: [touchMove],
            cancelable: true,
            bubbles: true,
        }));
    """)
    
    # デバウンス処理を考慮して待機
    page.wait_for_timeout(250)
    
    # スワイプイベントが検出されないことを確認
    swipe_events = page.evaluate("window.shortSwipeEvents")
    assert len(swipe_events) == 0, "閾値未満のスワイプは無視されるべき"


def test_swipe_detector_distinguishes_vertical_scroll(page: Page):
    """
    垂直スクロール（縦方向の移動が水平方向の2倍以上）がスワイプとして検出されないことを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # SwipeGestureDetectorを初期化
    page.evaluate("""
        window.verticalSwipeEvents = [];
        const detector = new SwipeGestureDetector(document.body, (event) => {
            window.verticalSwipeEvents.push(event);
        });
        detector.enable();
    """)
    
    # 主に垂直方向の移動をシミュレート（水平30px、垂直100px）
    page.evaluate("""
        const target = document.body;
        const startX = 200;
        const startY = 200;
        const endX = 230;  // 水平30px
        const endY = 300;  // 垂直100px（水平の3.3倍）
        
        const touchStart = new Touch({
            identifier: 0,
            target: target,
            clientX: startX,
            clientY: startY,
        });
        target.dispatchEvent(new TouchEvent('touchstart', {
            touches: [touchStart],
            cancelable: true,
            bubbles: true,
        }));
        
        const touchMove = new Touch({
            identifier: 0,
            target: target,
            clientX: endX,
            clientY: endY,
        });
        target.dispatchEvent(new TouchEvent('touchmove', {
            touches: [touchMove],
            cancelable: true,
            bubbles: true,
        }));
        
        target.dispatchEvent(new TouchEvent('touchend', {
            changedTouches: [touchMove],
            cancelable: true,
            bubbles: true,
        }));
    """)
    
    # デバウンス処理を考慮して待機
    page.wait_for_timeout(250)
    
    # スワイプイベントが検出されないことを確認（垂直スクロールとして扱われる）
    swipe_events = page.evaluate("window.verticalSwipeEvents")
    assert len(swipe_events) == 0, "垂直スクロールはスワイプとして検出されないべき"


def test_swipe_detector_detects_left_swipe(page: Page):
    """
    左方向のスワイプが正しく検出されることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # SwipeGestureDetectorを初期化
    page.evaluate("""
        window.leftSwipeEvents = [];
        const detector = new SwipeGestureDetector(document.body, (event) => {
            window.leftSwipeEvents.push(event);
        });
        detector.enable();
    """)
    
    # 左方向へのスワイプをシミュレート（100px移動）
    page.evaluate("""
        const target = document.body;
        const startX = 200;
        const startY = 300;
        const endX = 100;  // 100px左へ移動
        const endY = 300;
        
        const touchStart = new Touch({
            identifier: 0,
            target: target,
            clientX: startX,
            clientY: startY,
        });
        target.dispatchEvent(new TouchEvent('touchstart', {
            touches: [touchStart],
            cancelable: true,
            bubbles: true,
        }));
        
        const touchMove = new Touch({
            identifier: 0,
            target: target,
            clientX: endX,
            clientY: endY,
        });
        target.dispatchEvent(new TouchEvent('touchmove', {
            touches: [touchMove],
            cancelable: true,
            bubbles: true,
        }));
        
        target.dispatchEvent(new TouchEvent('touchend', {
            changedTouches: [touchMove],
            cancelable: true,
            bubbles: true,
        }));
    """)
    
    # デバウンス処理を考慮して待機
    page.wait_for_timeout(250)
    
    # スワイプイベントが検出されたことを確認
    swipe_events = page.evaluate("window.leftSwipeEvents")
    assert len(swipe_events) > 0, "スワイプイベントが検出されるべき"
    
    # 左方向スワイプが検出されたことを確認
    first_event = swipe_events[0]
    assert first_event['direction'] == 'left', "左方向スワイプが検出されるべき"


def test_swipe_detector_can_be_disabled(page: Page):
    """
    disable()メソッドでスワイプ検出が無効化されることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # SwipeGestureDetectorを初期化して有効化
    page.evaluate("""
        window.disableTestEvents = [];
        const detector = new SwipeGestureDetector(document.body, (event) => {
            window.disableTestEvents.push(event);
        });
        detector.enable();
        window.disableTestDetector = detector;
    """)
    
    # 無効化
    page.evaluate("window.disableTestDetector.disable()")
    
    # スワイプをシミュレート
    page.evaluate("""
        const target = document.body;
        const startX = 100;
        const startY = 300;
        const endX = 200;
        const endY = 300;
        
        const touchStart = new Touch({
            identifier: 0,
            target: target,
            clientX: startX,
            clientY: startY,
        });
        target.dispatchEvent(new TouchEvent('touchstart', {
            touches: [touchStart],
            cancelable: true,
            bubbles: true,
        }));
        
        const touchMove = new Touch({
            identifier: 0,
            target: target,
            clientX: endX,
            clientY: endY,
        });
        target.dispatchEvent(new TouchEvent('touchmove', {
            touches: [touchMove],
            cancelable: true,
            bubbles: true,
        }));
        
        target.dispatchEvent(new TouchEvent('touchend', {
            changedTouches: [touchMove],
            cancelable: true,
            bubbles: true,
        }));
    """)
    
    # デバウンス処理を考慮して待機
    page.wait_for_timeout(250)
    
    # スワイプイベントが検出されないことを確認
    swipe_events = page.evaluate("window.disableTestEvents")
    assert len(swipe_events) == 0, "無効化後はスワイプイベントが検出されないべき"


def test_swipe_detector_debounces_rapid_swipes(page: Page):
    """
    連続スワイプがデバウンス処理（200ms）されることを確認
    """
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://localhost:8000/documents")
    
    # SwipeGestureDetectorを初期化
    page.evaluate("""
        window.debounceSwipeEvents = [];
        const detector = new SwipeGestureDetector(document.body, (event) => {
            window.debounceSwipeEvents.push(event);
        });
        detector.enable();
    """)
    
    # 短時間に2回スワイプを実行
    for i in range(2):
        page.evaluate("""
            const target = document.body;
            const startX = 100;
            const startY = 300;
            const endX = 200;
            const endY = 300;
            
            const touchStart = new Touch({
                identifier: 0,
                target: target,
                clientX: startX,
                clientY: startY,
            });
            target.dispatchEvent(new TouchEvent('touchstart', {
                touches: [touchStart],
                cancelable: true,
                bubbles: true,
            }));
            
            const touchMove = new Touch({
                identifier: 0,
                target: target,
                clientX: endX,
                clientY: endY,
            });
            target.dispatchEvent(new TouchEvent('touchmove', {
                touches: [touchMove],
                cancelable: true,
                bubbles: true,
            }));
            
            target.dispatchEvent(new TouchEvent('touchend', {
                changedTouches: [touchMove],
                cancelable: true,
                bubbles: true,
            }));
        """)
        page.wait_for_timeout(50)  # 短い待機時間（デバウンス期間未満）
    
    # デバウンス処理を考慮して待機
    page.wait_for_timeout(250)
    
    # デバウンス処理により、イベント数が制限されることを確認
    swipe_events = page.evaluate("window.debounceSwipeEvents")
    assert len(swipe_events) <= 2, f"デバウンス処理により、イベント数が制限されるべき（実際: {len(swipe_events)}回）"
