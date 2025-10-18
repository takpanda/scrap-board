/**
 * Mobile Swipe Navigation Module
 *
 * モバイル環境でのスワイプジェスチャーによる記事ナビゲーション機能を提供します。
 */

/**
 * ViewportDetector
 *
 * ビューポート幅を監視し、モバイル環境（768px未満）かデスクトップ環境（768px以上）かを判定します。
 */
class ViewportDetector {
  /**
   * コンストラクタ
   */
  constructor() {
    this.MOBILE_BREAKPOINT = 768; // Tailwind mdブレークポイント
    this.resizeCallback = null;
    this.resizeTimeoutId = null;
    this.DEBOUNCE_DELAY = 200; // デバウンス遅延時間（ミリ秒）
    this.lastIsMobileState = null; // 前回のモバイル判定状態
  }

  /**
   * モバイル環境判定
   *
   * @returns {boolean} ビューポート幅が768px未満の場合true、それ以外false
   */
  isMobile() {
    return window.innerWidth < this.MOBILE_BREAKPOINT;
  }

  /**
   * リサイズ監視開始
   *
   * ウィンドウリサイズ時にコールバックを発火します。
   * デバウンス処理（200ms）を適用し、連続発火を制御します。
   * モバイル⇔デスクトップ環境切り替え時のみコールバックを発火します。
   *
   * @param {Function} callback - (isMobile: boolean) => void 形式のコールバック関数
   */
  startMonitoring(callback) {
    this.resizeCallback = callback;
    this.lastIsMobileState = this.isMobile(); // 初期状態を記録

    // リサイズイベントリスナーを登録（デバウンス適用）
    this._handleResize = () => {
      // 既存のタイムアウトをクリア
      if (this.resizeTimeoutId) {
        clearTimeout(this.resizeTimeoutId);
      }

      // デバウンス: 200ms後にコールバック実行
      this.resizeTimeoutId = setTimeout(() => {
        const currentIsMobile = this.isMobile();

        // モバイル⇔デスクトップ切り替え時のみコールバック発火
        if (currentIsMobile !== this.lastIsMobileState) {
          this.lastIsMobileState = currentIsMobile;
          if (this.resizeCallback) {
            this.resizeCallback(currentIsMobile);
          }
        }
      }, this.DEBOUNCE_DELAY);
    };

    window.addEventListener('resize', this._handleResize);
  }

  /**
   * リサイズ監視停止
   *
   * リサイズイベントリスナーを解除し、タイムアウトをクリアします。
   */
  stopMonitoring() {
    if (this._handleResize) {
      window.removeEventListener('resize', this._handleResize);
    }

    if (this.resizeTimeoutId) {
      clearTimeout(this.resizeTimeoutId);
      this.resizeTimeoutId = null;
    }

    this.resizeCallback = null;
    this.lastIsMobileState = null;
  }
}

// グローバルスコープにViewportDetectorインスタンスを公開（テスト用）
window.viewportDetector = new ViewportDetector();

console.log('ViewportDetector initialized');
