"""
ViewportDetectorのテスト

このテストはPlaywrightを使用してViewportDetectorのモバイル環境判定機能をテストします。
"""
import pytest
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.browser, pytest.mark.usefixtures("live_server")]


def test_viewport_detector_identifies_mobile_viewport(page: Page):
    """
    モバイルビューポート（768px未満）を正しく判定することを確認
    """
    # モバイルビューポートサイズを設定（375px × 667px、iPhone SE相当）
    page.set_viewport_size({"width": 375, "height": 667})

    # テスト用ページに移動
    page.goto("http://localhost:8000/documents")

    # ViewportDetectorが初期化され、isMobile()がtrueを返すことを確認
    is_mobile = page.evaluate("window.viewportDetector && window.viewportDetector.isMobile()")
    assert is_mobile is True, "ビューポート幅375pxでisMobile()がtrueを返すべき"


def test_viewport_detector_identifies_desktop_viewport(page: Page):
    """
    デスクトップビューポート（768px以上）を正しく判定することを確認
    """
    # デスクトップビューポートサイズを設定（1024px × 768px）
    page.set_viewport_size({"width": 1024, "height": 768})

    # テスト用ページに移動
    page.goto("http://localhost:8000/documents")

    # ViewportDetectorが初期化され、isMobile()がfalseを返すことを確認
    is_mobile = page.evaluate("window.viewportDetector && window.viewportDetector.isMobile()")
    assert is_mobile is False, "ビューポート幅1024pxでisMobile()がfalseを返すべき"


def test_viewport_detector_boundary_at_768px(page: Page):
    """
    境界値（768px）でモバイル判定が正しく切り替わることを確認
    """
    # 境界値直下（767px）でモバイル判定
    page.set_viewport_size({"width": 767, "height": 1024})
    page.goto("http://localhost:8000/documents")
    is_mobile_767 = page.evaluate("window.viewportDetector && window.viewportDetector.isMobile()")
    assert is_mobile_767 is True, "ビューポート幅767pxでisMobile()がtrueを返すべき"

    # 境界値ちょうど（768px）でデスクトップ判定
    page.set_viewport_size({"width": 768, "height": 1024})
    page.goto("http://localhost:8000/documents")
    is_mobile_768 = page.evaluate("window.viewportDetector && window.viewportDetector.isMobile()")
    assert is_mobile_768 is False, "ビューポート幅768pxでisMobile()がfalseを返すべき"


def test_viewport_detector_resize_monitoring(page: Page):
    """
    ウィンドウリサイズ時にモバイル環境判定が動的に再実行されることを確認
    """
    # 初期状態: デスクトップサイズ
    page.set_viewport_size({"width": 1024, "height": 768})
    page.goto("http://localhost:8000/documents")

    # コールバック呼び出し回数をカウントする変数を用意
    page.evaluate("""
        window.resizeCallbackCount = 0;
        window.lastIsMobile = null;
        if (window.viewportDetector) {
            window.viewportDetector.startMonitoring((isMobile) => {
                window.resizeCallbackCount++;
                window.lastIsMobile = isMobile;
            });
        }
    """)

    # デスクトップ→モバイルにリサイズ
    page.set_viewport_size({"width": 375, "height": 667})
    page.wait_for_timeout(300)  # デバウンス処理（200ms）を考慮して待機

    # コールバックが発火し、isMobile=trueが渡されたことを確認
    callback_count = page.evaluate("window.resizeCallbackCount")
    last_is_mobile = page.evaluate("window.lastIsMobile")

    assert callback_count >= 1, "リサイズ時にコールバックが発火すべき"
    assert last_is_mobile is True, "モバイルサイズへのリサイズでisMobile=trueが渡されるべき"


def test_viewport_detector_debounce_on_resize(page: Page):
    """
    リサイズイベントがデバウンス処理（200ms）されることを確認
    """
    page.set_viewport_size({"width": 1024, "height": 768})
    page.goto("http://localhost:8000/documents")

    # コールバックカウンターを初期化
    page.evaluate("""
        window.debounceCallbackCount = 0;
        if (window.viewportDetector) {
            window.viewportDetector.startMonitoring(() => {
                window.debounceCallbackCount++;
            });
        }
    """)

    # 短時間に複数回リサイズを実行（デバウンスで統合されるべき）
    page.set_viewport_size({"width": 800, "height": 600})
    page.wait_for_timeout(50)
    page.set_viewport_size({"width": 600, "height": 800})
    page.wait_for_timeout(50)
    page.set_viewport_size({"width": 375, "height": 667})

    # デバウンス期間（200ms）を待機
    page.wait_for_timeout(300)

    # コールバック呼び出し回数が少ないことを確認（連続リサイズが統合される）
    callback_count = page.evaluate("window.debounceCallbackCount")
    assert callback_count <= 2, f"デバウンス処理により、コールバック呼び出しは少数であるべき（実際: {callback_count}回）"


def test_viewport_detector_stop_monitoring(page: Page):
    """
    stopMonitoring()でリサイズ監視が停止することを確認
    """
    page.set_viewport_size({"width": 1024, "height": 768})
    page.goto("http://localhost:8000/documents")

    # モニタリング開始
    page.evaluate("""
        window.stopCallbackCount = 0;
        if (window.viewportDetector) {
            window.viewportDetector.startMonitoring(() => {
                window.stopCallbackCount++;
            });
        }
    """)

    # リサイズしてコールバックが発火することを確認
    page.set_viewport_size({"width": 375, "height": 667})
    page.wait_for_timeout(300)
    initial_count = page.evaluate("window.stopCallbackCount")
    assert initial_count >= 1, "モニタリング中はコールバックが発火すべき"

    # モニタリング停止
    page.evaluate("window.viewportDetector && window.viewportDetector.stopMonitoring()")

    # 再度リサイズしても、コールバックが発火しないことを確認
    page.set_viewport_size({"width": 1024, "height": 768})
    page.wait_for_timeout(300)
    final_count = page.evaluate("window.stopCallbackCount")

    assert final_count == initial_count, f"stopMonitoring()後はコールバックが発火しないべき（initial: {initial_count}, final: {final_count}）"
